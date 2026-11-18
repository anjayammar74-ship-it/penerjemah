import asyncio
import base64
import mimetypes
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import re
from typing import Annotated, Literal, Optional
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pymongo import ASCENDING, IndexModel
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from scraper import fetch_html, parse_chapter, parse_series, fetch_image, series_key, UA as UA_RELAY  # noqa: E402
import httpx  # noqa: E402
from translator import translate_image, translate_point, verify_image, dedupe, LLMUnavailable  # noqa: E402
from free_engine import free_translate_image, free_extra, free_translate_regions, text_candidates  # noqa: E402

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

INDEXES: dict[str, list[IndexModel]] = {
    "chapters": [IndexModel([("url", ASCENDING)], name="url", unique=True)],
    "translations": [IndexModel([("img_url", ASCENDING)], name="img_url", unique=True)],
    "cleaned": [IndexModel([("img_url", ASCENDING)], name="img_url", unique=True)],
    "series": [IndexModel([("url", ASCENDING)], name="url", unique=True)],
    "glossary": [IndexModel([("key", ASCENDING)], name="key", unique=True)],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)


PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc: dict):
        return cls.model_validate(doc)

    def to_mongo(self) -> dict:
        return self.model_dump(exclude={"id"})


class Chapter(BaseDocument):
    url: str
    title: str
    prev_url: Optional[str] = None
    next_url: Optional[str] = None
    series_url: Optional[str] = None
    series_key: Optional[str] = None
    images: list[str]
    fetched_at: str


class Bubble(BaseModel):
    x: float
    y: float
    w: float
    h: float
    en: str
    id: str
    bg: str
    fg: str
    mode: str = "patch"
    shape: str = "ellipse"
    fs: Optional[float] = None


class Translation(BaseDocument):
    img_url: str
    width: int
    height: int
    bubbles: list[Bubble]
    created_at: str
    updated_at: Optional[str] = None
    partial: bool = False
    verified: bool = False
    v: int = 1


TR_VERSION = 3


class Term(BaseModel):
    en: str
    id: str


class Glossary(BaseDocument):
    key: str
    terms: list[Term] = []
    updated_at: Optional[str] = None


class GlossaryUpdate(BaseModel):
    terms: list[Term]


class SeriesChapter(BaseModel):
    num: str
    url: Optional[str] = None
    date: str = ""
    locked: bool = False


class Series(BaseDocument):
    url: str
    title: str
    cover: Optional[str] = None
    synopsis: str = ""
    series_key: str
    chapters: list[SeriesChapter]
    fetched_at: str


class ChapterRequest(BaseModel):
    url: str


class PointRequest(BaseModel):
    img_url: str
    chapter_url: Optional[str] = None
    x: float
    y: float
    engine: Literal["free", "ai"] = "free"


class TranslateRequest(BaseModel):
    img_url: str
    chapter_url: Optional[str] = None
    force: bool = False
    engine: Literal["free", "ai"] = "free"
    words: Optional[list[dict]] = None
    regions: Optional[list[dict]] = None


class WordsRequest(BaseModel):
    img_url: str
    chapter_url: Optional[str] = None
    words: Optional[list[dict]] = None
    regions: Optional[list[dict]] = None
    final: bool = False


class RegionsRequest(BaseModel):
    img_url: str
    chapter_url: Optional[str] = None
    cleaned: bool = False
    y0: Optional[float] = None
    y1: Optional[float] = None


class BubbleEdit(BaseModel):
    img_url: str
    engine: Literal["free", "ai"] = "free"
    index: int
    id: str


def ck(img_url: str, engine: str) -> str:
    """Storage key: each engine keeps its own translation + cleaned image."""
    return img_url if engine == "ai" else f"free12|{img_url}"


def _out(doc: dict, engine: str) -> dict:
    d = Translation.from_mongo(doc).model_dump(exclude={"id"})
    d["engine"] = engine
    return d


app = FastAPI()
api = APIRouter(prefix="/api")
_inflight: dict[str, asyncio.Task] = {}


def _validate_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if " " in url or "." not in url:
        raise HTTPException(400, "Link tidak valid")
    return url


@api.get("/")
async def root():
    return {"message": "Balona API"}


@api.post("/chapter")
async def get_chapter(req: ChapterRequest):
    url = _validate_url(req.url)
    cached = await db.chapters.find_one({"url": url})
    if cached and cached.get("images") and cached.get("series_key"):
        return Chapter.from_mongo(cached).model_dump(exclude={"id"})
    try:
        info = parse_chapter(url, await fetch_html(url))
    except Exception as exc:
        logger.warning("chapter fetch failed %s: %s", url, exc)
        raise HTTPException(502, "Halaman tidak bisa dibuka. Pastikan link chapter benar.")
    if not info["images"]:
        raise HTTPException(422, "Tidak menemukan gambar komik di halaman ini.")
    ch = Chapter(**info, fetched_at=datetime.now(timezone.utc).isoformat())
    await db.chapters.update_one({"url": url}, {"$set": ch.to_mongo()}, upsert=True)
    return ch.model_dump(exclude={"id"})


@api.get("/img")
async def proxy_image(u: str = Query(...), ref: Optional[str] = None):
    if not u.startswith(("http://", "https://")):
        raise HTTPException(400, "bad url")
    try:
        data, ctype = await fetch_image(u, ref)
    except Exception:
        raise HTTPException(502, "Gambar gagal dimuat")
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "public, max-age=604800"})


async def _glossary(key: Optional[str]) -> list[dict]:
    if not key:
        return []
    doc = await db.glossary.find_one({"key": key})
    return [t.model_dump() for t in Glossary.from_mongo(doc).terms] if doc else []


async def _learn_names(key: Optional[str], names: list[str]) -> None:
    if not key or not names:
        return
    terms = await _glossary(key)
    known = {t["en"].lower() for t in terms}
    new = [{"en": n, "id": n} for n in names if n.strip() and n.lower() not in known and len(n) < 40]
    if new:
        g = Glossary(key=key, terms=terms + new, updated_at=datetime.now(timezone.utc).isoformat())
        await db.glossary.update_one({"key": key}, {"$set": g.to_mongo()}, upsert=True)


async def _do_translate(img_url: str, ref: Optional[str], engine: str, words: Optional[list[dict]] = None,
                        regions: Optional[list[dict]] = None) -> dict:
    data, _ = await fetch_image(img_url, ref)
    key = series_key(ref) if ref else None
    if engine == "ai":
        result = await translate_image(data, await _glossary(key))
    elif regions is not None:
        result = await free_translate_regions(data, regions, await _glossary(key))
    else:
        result = await free_translate_image(data, await _glossary(key), words)
    cleaned = result.pop("cleaned")
    names = result.pop("names")
    sk = ck(img_url, engine)
    await db.cleaned.update_one({"img_url": sk}, {"$set": {"img_url": sk, "data": cleaned}}, upsert=True)
    now = datetime.now(timezone.utc).isoformat()
    tr = Translation(img_url=sk, created_at=now, updated_at=now, v=TR_VERSION, **result)
    await db.translations.update_one({"img_url": sk}, {"$set": tr.to_mongo()}, upsert=True)
    await _learn_names(key, names)
    if engine == "ai":
        asyncio.create_task(_verify(img_url, key))
    out = tr.model_dump(exclude={"id"})
    out["engine"] = engine
    return out


async def _merge_extra(sk: str, bubbles: list[dict], cleaned: bytes, **flags) -> int:
    doc = await db.translations.find_one({"img_url": sk})
    if not doc:
        return 0
    tr = Translation.from_mongo(doc)
    bubbles = dedupe(bubbles, [b.model_dump() for b in tr.bubbles])
    if bubbles:
        await db.cleaned.update_one({"img_url": sk}, {"$set": {"img_url": sk, "data": cleaned}}, upsert=True)
        tr.bubbles = sorted(tr.bubbles + [Bubble(**b) for b in bubbles], key=lambda b: (round(b.y, 1), b.x))
    for k, val in flags.items():
        setattr(tr, k, val)
    tr.updated_at = datetime.now(timezone.utc).isoformat()
    await db.translations.update_one({"img_url": sk}, {"$set": tr.to_mongo()})
    return len(bubbles)


_verifying: set[str] = set()


async def _verify(img_url: str, key: Optional[str]) -> None:
    sk = ck(img_url, "ai")
    if sk in _verifying:
        return
    _verifying.add(sk)
    try:
        for _ in range(60):  # second look runs only when no page is waiting for its first translation
            if not _inflight:
                break
            await asyncio.sleep(2)
        cl = await db.cleaned.find_one({"img_url": sk})
        res = await verify_image(bytes(cl["data"]), await _glossary(key))
        n = await _merge_extra(sk, res["bubbles"], res["cleaned"], verified=True)
        logger.info("verify %s: +%s bubbles", img_url[-40:], n)
    except Exception as exc:
        logger.warning("verify failed: %s", exc)
        await _merge_extra(sk, [], b"", verified=True)
    finally:
        _verifying.discard(sk)


@api.get("/translation")
async def get_translation(u: str = Query(...), engine: Literal["free", "ai"] = "free"):
    doc = await db.translations.find_one({"img_url": ck(u, engine), "v": TR_VERSION})
    if not doc:
        raise HTTPException(404, "Belum ada")
    return _out(doc, engine)


@api.post("/translate")
async def translate(req: TranslateRequest):
    if not req.img_url.startswith(("http://", "https://")):
        raise HTTPException(400, "bad url")
    sk = ck(req.img_url, req.engine)
    if not req.force:
        cached = await db.translations.find_one({"img_url": sk, "v": TR_VERSION, "partial": {"$ne": True}})
        if cached:
            if req.engine == "ai" and not cached.get("verified") and sk not in _verifying:
                asyncio.create_task(_verify(req.img_url, series_key(req.chapter_url) if req.chapter_url else None))
            return _out(cached, req.engine)
    task = _inflight.get(sk)
    if not task and req.engine == "free" and req.words is None and req.regions is None:
        data, _ = await fetch_image(req.img_url, req.chapter_url)
        return {"status": "need_ocr", "regions": await asyncio.to_thread(text_candidates, data)}
    if not task:
        task = asyncio.create_task(_do_translate(req.img_url, req.chapter_url, req.engine, req.words, req.regions))
        _inflight[sk] = task
        task.add_done_callback(lambda _t: _inflight.pop(sk, None))
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=45)
    except asyncio.TimeoutError:
        return {"status": "pending"}
    except LLMUnavailable as exc:
        raise _llm_http(exc)
    except Exception as exc:
        logger.exception("translate failed: %s", exc)
        raise HTTPException(502, "Terjemahan gagal, coba lagi.")


def _llm_http(exc: LLMUnavailable) -> HTTPException:
    if str(exc) == "budget":
        return HTTPException(402, "Saldo AI habis. Pilih mesin Gratis di pengaturan (T), atau isi ulang Universal Key.")
    return HTTPException(503, "Layanan AI sedang sibuk. Coba lagi sebentar.")


@api.post("/translate-point")
async def translate_at_point(req: PointRequest):
    if not req.img_url.startswith(("http://", "https://")):
        raise HTTPException(400, "bad url")
    sk = ck(req.img_url, req.engine)
    doc = await db.translations.find_one({"img_url": sk, "v": TR_VERSION})
    if not doc:
        raise HTTPException(409, "Halaman belum diterjemahkan.")
    cl = await db.cleaned.find_one({"img_url": sk})
    data = bytes(cl["data"]) if cl else (await fetch_image(req.img_url, req.chapter_url))[0]
    key = series_key(req.chapter_url) if req.chapter_url else None
    try:
        res = await translate_point(data, req.y, await _glossary(key))
    except LLMUnavailable as exc:
        raise _llm_http(exc)
    except Exception as exc:
        logger.warning("point translate failed: %s", exc)
        raise HTTPException(502, "Gagal menerjemahkan bagian ini.")
    added = 0
    if res["bubbles"]:
        added = await _merge_extra(sk, res["bubbles"], res["cleaned"])
        await _learn_names(key, res["names"])
    out = _out(await db.translations.find_one({"img_url": sk}), req.engine)
    out["added"] = added
    return out


@api.post("/translate-words")
async def translate_words(req: WordsRequest):
    """Free engine: the phone read leftover text (second check or a tap); translate and add it."""
    sk = ck(req.img_url, "free")
    doc = await db.translations.find_one({"img_url": sk, "v": TR_VERSION})
    cl = await db.cleaned.find_one({"img_url": sk})
    if not doc or not cl:
        raise HTTPException(409, "Halaman belum diterjemahkan.")
    key = series_key(req.chapter_url) if req.chapter_url else None
    try:
        if req.regions is not None:
            res = await free_translate_regions(bytes(cl["data"]), req.regions, await _glossary(key))
        else:
            res = await free_extra(bytes(cl["data"]), req.words or [], await _glossary(key))
    except Exception as exc:
        logger.warning("free extra failed: %s", exc)
        raise HTTPException(502, "Penerjemah gratis sedang sibuk, coba lagi.")
    flags = {"verified": True} if req.final else {}
    added = await _merge_extra(sk, res["bubbles"], res["cleaned"], **flags)
    out = _out(await db.translations.find_one({"img_url": sk}), "free")
    out["added"] = added
    return out


@api.post("/free/regions")
async def free_regions(req: RegionsRequest):
    """Boxes that look like lettering; the phone then reads each one up close."""
    _validate_url(req.img_url)
    if req.cleaned:
        cl = await db.cleaned.find_one({"img_url": ck(req.img_url, "free")})
        if not cl:
            raise HTTPException(409, "Halaman belum diterjemahkan.")
        data = bytes(cl["data"])
    else:
        data, _ = await fetch_image(req.img_url, req.chapter_url)
    rng = (req.y0, req.y1) if req.y0 is not None and req.y1 is not None else None
    boxes = await asyncio.to_thread(text_candidates, data, rng)
    return {"regions": boxes}


@api.put("/bubble")
async def edit_bubble(req: BubbleEdit):
    sk = ck(req.img_url, req.engine)
    doc = await db.translations.find_one({"img_url": sk})
    if not doc:
        raise HTTPException(404, "Terjemahan tidak ditemukan")
    tr = Translation.from_mongo(doc)
    if not 0 <= req.index < len(tr.bubbles) or not req.id.strip():
        raise HTTPException(400, "Balon tidak valid")
    tr.bubbles[req.index].id = req.id.strip()
    tr.updated_at = datetime.now(timezone.utc).isoformat()
    await db.translations.update_one({"img_url": sk}, {"$set": tr.to_mongo()})
    return _out(tr.model_dump(), req.engine)


@api.get("/clean")
async def cleaned_image(u: str = Query(...), engine: Literal["free", "ai"] = "free"):
    doc = await db.cleaned.find_one({"img_url": ck(u, engine)})
    if not doc:
        raise HTTPException(404, "Belum diterjemahkan")
    return Response(content=bytes(doc["data"]), media_type="image/webp",
                    headers={"Cache-Control": "public, max-age=86400"})


@api.post("/series")
async def get_series(req: ChapterRequest):
    url = _validate_url(req.url)
    if re.search(r"-chapter-[\d.-]+/?$", url):
        ch = await get_chapter(ChapterRequest(url=url))
        if not ch.get("series_url"):
            raise HTTPException(422, "Halaman serial tidak ditemukan.")
        url = ch["series_url"]
    cached = await db.series.find_one({"url": url})
    if cached and datetime.fromisoformat(cached["fetched_at"]) > datetime.now(timezone.utc) - timedelta(minutes=30):
        return Series.from_mongo(cached).model_dump(exclude={"id"})
    try:
        info = parse_series(url, await fetch_html(url))
    except Exception as exc:
        logger.warning("series fetch failed %s: %s", url, exc)
        raise HTTPException(502, "Halaman serial tidak bisa dibuka.")
    if not info["chapters"]:
        raise HTTPException(422, "Daftar chapter tidak ditemukan.")
    se = Series(**info, fetched_at=datetime.now(timezone.utc).isoformat())
    await db.series.update_one({"url": url}, {"$set": se.to_mongo()}, upsert=True)
    return se.model_dump(exclude={"id"})


@api.get("/glossaries")
async def all_glossaries():
    """Every series' character-name list, for the backup file."""
    docs = await db.glossary.find({}, {"_id": 0, "key": 1, "terms": 1}).to_list(5000)
    return {"items": [{"key": d["key"], "terms": d.get("terms") or []} for d in docs if d.get("key")]}


@api.get("/glossary")
async def get_glossary(key: str = Query(...)):
    return {"key": key, "terms": await _glossary(key)}


@api.put("/glossary")
async def put_glossary(body: GlossaryUpdate, key: str = Query(...)):
    seen, terms = set(), []
    for t in body.terms:
        en, idt = t.en.strip(), t.id.strip()
        if en and en.lower() not in seen:
            seen.add(en.lower())
            terms.append(Term(en=en, id=idt or en))
    g = Glossary(key=key, terms=terms, updated_at=datetime.now(timezone.utc).isoformat())
    await db.glossary.update_one({"key": key}, {"$set": g.to_mongo()}, upsert=True)
    return {"key": key, "terms": [t.model_dump() for t in terms]}


class RelayRequest(BaseModel):
    url: str
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = {}
    body: Optional[str] = None
    binary: bool = False


@api.post("/relay")
async def relay(req: RelayRequest):
    """Test-only stand-in for the APK's native network (browser CORS). Off unless LOCAL_TEST_RELAY=1."""
    if os.environ.get("LOCAL_TEST_RELAY") != "1":
        raise HTTPException(404, "Not found")
    _validate_url(req.url)
    headers = {"User-Agent": UA_RELAY, **req.headers}
    async with httpx.AsyncClient(follow_redirects=True, timeout=60, headers=headers) as c:
        r = await c.request(req.method, req.url, content=req.body)
    data = base64.b64encode(r.content).decode() if req.binary else r.text
    return {"status": r.status_code, "data": data, "ctype": r.headers.get("content-type", "").split(";")[0]}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True,
                   allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
                   allow_methods=["*"], allow_headers=["*"])

# Self-hosted copy: the built app sits in backend/web, so one program serves app + API on one address.
WEB_DIR = (ROOT_DIR / "web").resolve()
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/wasm", ".wasm")
if WEB_DIR.is_dir():
    @app.get("/{path:path}", include_in_schema=False)
    async def web_app(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        f = (WEB_DIR / path).resolve()
        if path and f.is_file() and WEB_DIR in f.parents:
            return FileResponse(f)
        return FileResponse(WEB_DIR / "index.html")


@app.on_event("startup")
async def start_index_build():
    app.state.index_task = asyncio.create_task(ensure_indexes())


@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()
