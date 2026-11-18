import asyncio
import base64
import io
import json
import logging
import os
import re
import uuid

import numpy as np
from PIL import Image
try:  # optional AI engine; the free engine never needs it (self-hosted copies run without it)
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
except ImportError:
    LlmChat = None

from cleaner import clean_bubble

logger = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    """All AI calls failed (e.g. key budget exhausted)."""

LLM_SEM = asyncio.Semaphore(12)
MODEL = ("gemini", "gemini-3-flash-preview")
TARGET_H, MIN_H, MAX_H = 1300, 800, 1900

SYSTEM = ("You are an expert manhwa/manga scanlation translator from English to Indonesian. "
          "You detect text bubbles precisely and translate naturally, keeping character names unchanged.")

PROMPT = """Look at this comic image segment. Find every speech bubble, thought bubble, narration/caption box and floating dialogue text that contains English words.
IGNORE: website watermarks/URLs (e.g. *.com, *.org), scanlator credits/ads, and big stylised sound effects drawn as artwork.
For each text block return an object:
- "box_2d": [ymin, xmin, ymax, xmax] normalized 0-1000, tightly enclosing ALL the text lines of that bubble (every word, nothing left outside)
- "bubble_2d": [ymin, xmin, ymax, xmax] normalized 0-1000 of the INSIDE of the bubble/box border (exclude the tail and spikes). For floating text without a bubble, repeat box_2d.
- "shape": "ellipse" (round speech/thought bubble), "cloud" (spiky/fluffy bubble), "rect" (rectangular caption box) or "none" (text directly over artwork)
- "en": the original English text exactly
- "id": a natural, casual, fluent Indonesian translation as an Indonesian webtoon reader expects (pick aku/kau/kamu/Anda fittingly). Normal sentence case, not ALL CAPS. Keep '...', '!' and '?'.
Also list proper nouns (character names, places, techniques, titles) you saw.
Some bubbles may be EMPTY (already erased) - never invent text for empty bubbles; only report letters you can actually see.
{glossary}Return ONLY JSON (no markdown): {{"items": [...], "names": ["Bi-Yeong", ...]}}"""


def glossary_text(glossary: list[dict]) -> str:
    if not glossary:
        return ""
    rows = "\n".join(f'- "{g["en"]}" -> "{g["id"]}"' for g in glossary[:120])
    return f"GLOSSARY - always write these names/terms exactly like this in Indonesian:\n{rows}\n"


def split_rows(gray: np.ndarray) -> list[tuple[int, int]]:
    h = gray.shape[0]
    if h <= MAX_H:
        return [(0, h)]
    row_rng = gray.max(axis=1) - gray.min(axis=1)
    cuts, y = [], 0
    while h - y > MAX_H:
        lo, hi = y + MIN_H, min(y + MAX_H, h - MIN_H // 2)
        window = row_rng[lo:hi]
        clean = np.where(window < 18)[0]
        if len(clean):
            cut = lo + int(clean[np.argmin(np.abs(clean - (TARGET_H - MIN_H)))])
        else:
            cut = lo + int(np.argmin(window))
        cuts.append((y, cut))
        y = cut
    cuts.append((y, h))
    return cuts


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    m = re.search(r"[\[{].*[\]}]", t, re.S)
    return json.loads(m.group(0)) if m else []


async def _chat(text: str, b64: str | None = None) -> str:
    if LlmChat is None or not os.environ.get("EMERGENT_LLM_KEY"):
        raise LLMUnavailable("AI engine is not installed on this server")
    async with LLM_SEM:
        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=str(uuid.uuid4()),
                       system_message=SYSTEM).with_model(*MODEL)
        files = [ImageContent(image_base64=b64)] if b64 else None
        return await chat.send_message(UserMessage(text=text, file_contents=files) if files else UserMessage(text=text))


async def ask_llm(seg: Image.Image, gloss: str) -> dict:
    w, h = seg.size
    img = seg if w <= 1000 else seg.resize((1000, int(h * 1000 / w)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode()
    err = ""
    for attempt in range(3):
        try:
            data = parse_json(await _chat(PROMPT.format(glossary=gloss), b64))
            if isinstance(data, list):
                return {"items": data, "names": [], "ok": True}
            return {"items": data.get("items") or [], "names": data.get("names") or [], "ok": True}
        except Exception as exc:
            err = str(exc)
            logger.warning("llm segment failed (attempt %s): %s", attempt + 1, exc)
            if "budget" in err.lower():
                break
            await asyncio.sleep(1.5 * (attempt + 1))
    return {"items": [], "names": [], "ok": False, "error": err}


def has_ink(seg: Image.Image) -> bool:
    g = np.asarray(seg.convert("L"), dtype=np.float32)
    return float(g.std()) > 6


def merge_split(raw: list) -> list:
    """Join a bubble cut in two by a segment boundary (bottom of one segment + top of the next)."""
    out, used = [], set()
    for i, a in enumerate(raw):
        if i in used:
            continue
        if a["bottom"]:
            for j, b in enumerate(raw):
                ov = min(a["t"][2], b["t"][2]) - max(a["t"][0], b["t"][0])
                small = min(a["t"][2] - a["t"][0], b["t"][2] - b["t"][0])
                if j not in used and j != i and b["seg"] == a["seg"] + 1 and b["top"] and ov > 0.3 * small:
                    used.add(j)
                    u = lambda p, q: [min(p[0], q[0]), min(p[1], q[1]), max(p[2], q[2]), max(p[3], q[3])]
                    a = {**a, "t": u(a["t"], b["t"]), "b": u(a["b"], b["b"]), "en": f"{a['en']} {b['en']}",
                         "id": f"{a['id']} {b['id']}", "bottom": b["bottom"], "merged": True}
                    break
        out.append(a)
    return out


async def retranslate_merged(raw: list, gloss: str) -> None:
    merged = [r for r in raw if r.get("merged")]
    if not merged:
        return
    lines = "\n".join(f"{i + 1}. {r['en']}" for i, r in enumerate(merged))
    try:
        out = parse_json(await _chat(
            f"{gloss}Translate each numbered manhwa dialogue line into natural casual Indonesian (sentence case). "
            f"Return ONLY a JSON array of strings in the same order.\n{lines}"))
        for r, t in zip(merged, out):
            if isinstance(t, str) and t.strip():
                r["id"] = t.strip()
    except Exception as exc:
        logger.warning("retranslate failed: %s", exc)


def _px(box, a, sh, W):
    y0, x0, y1, x1 = [float(v) for v in box]
    return [x0 / 1000 * W, a + y0 / 1000 * sh, x1 / 1000 * W, a + y1 / 1000 * sh]


def _collect(res_items, a, sh, W, si, raw):
    for it in res_items:
        try:
            t = _px(it["box_2d"], a, sh, W)
            bb = _px(it.get("bubble_2d") or it["box_2d"], a, sh, W)
            tid = str(it.get("id", "")).strip()
        except Exception:
            continue
        if not tid:
            continue
        raw.append({"seg": si, "t": t, "b": bb, "shape": str(it.get("shape", "ellipse")),
                    "en": str(it.get("en", "")).strip(), "id": tid,
                    "top": float(it["box_2d"][0]) < 40, "bottom": float(it["box_2d"][2]) > 960})


def _apply(arr, raw, W, H) -> list:
    bubbles = []
    for r in raw:
        p = clean_bubble(arr, r["t"], r["b"], r["shape"])
        if not p:
            continue
        bubbles.append({"x": p["x0"] / W * 100, "y": p["y0"] / H * 100, "w": (p["x1"] - p["x0"]) / W * 100,
                        "h": (p["y1"] - p["y0"]) / H * 100, "en": r["en"], "id": r["id"],
                        "bg": p["bg"], "fg": p["fg"], "mode": p["mode"], "shape": r["shape"],
                        "fs": p["font_px"] / W * 100})
    return bubbles


def dedupe(new: list[dict], existing: list[dict] = ()) -> list[dict]:
    """Drop bubbles whose centre falls inside one we already have."""
    keep: list[dict] = []
    for b in new:
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        if any(e["x"] <= cx <= e["x"] + e["w"] and e["y"] <= cy <= e["y"] + e["h"] for e in list(existing) + keep):
            continue
        keep.append(b)
    return keep


def _raise_if_down(results):
    if results and not any(r["ok"] for r in results):
        err = results[0].get("error", "")
        raise LLMUnavailable("budget" if "budget" in err.lower() else err[:200])


async def translate_image(data: bytes, glossary: list[dict] | None = None) -> dict:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = im.size
    gray = np.asarray(im.convert("L"), dtype=np.float32)
    segs = split_rows(gray)
    gloss = glossary_text(glossary or [])
    results = await asyncio.gather(*(ask_llm(im.crop((0, a, W, b)), gloss) for a, b in segs))
    _raise_if_down(results)
    raw, names = [], []
    for si, ((a, b), res) in enumerate(zip(segs, results)):
        names += [n for n in res["names"] if isinstance(n, str)]
        _collect(res["items"], a, b - a, W, si, raw)
    raw = [r for r in merge_split(raw) if re.search(r"[A-Za-z]", r["en"] + r["id"])]
    await retranslate_merged(raw, gloss)

    arr = np.array(im)
    bubbles = dedupe(_apply(arr, raw, W, H))

    bubbles.sort(key=lambda bb: (round(bb["y"], 1), bb["x"]))
    out = io.BytesIO()
    Image.fromarray(arr).save(out, "WEBP", quality=88)
    failed = sum(1 for r in results if not r["ok"])
    return {"width": W, "height": H, "bubbles": bubbles, "names": sorted(set(names)),
            "cleaned": out.getvalue(), "partial": failed > 0}


async def verify_image(cleaned_bytes: bytes, glossary: list[dict] | None = None) -> dict:
    """Second look at the cleaned page: translate any English that the first pass missed."""
    im = Image.open(io.BytesIO(cleaned_bytes)).convert("RGB")
    W, H = im.size
    segs = split_rows(np.asarray(im.convert("L"), dtype=np.float32))
    gloss = glossary_text(glossary or [])
    check = [(si, a, b) for si, (a, b) in enumerate(segs) if has_ink(im.crop((0, a, W, b)))]
    again = await asyncio.gather(*(ask_llm(im.crop((0, a, W, b)), gloss) for _, a, b in check))
    extra = []
    for (si, a, b), res in zip(check, again):
        _collect(res["items"], a, b - a, W, si, extra)
    arr = np.array(im)
    extra = [r for r in extra if re.search(r"[A-Za-z]{2,}", r["en"]) and has_letters(arr, r["t"])]
    bubbles = _apply(arr, extra, W, H)
    out = io.BytesIO()
    Image.fromarray(arr).save(out, "WEBP", quality=88)
    return {"bubbles": bubbles, "cleaned": out.getvalue(), "ok": any(r["ok"] for r in again) or not check}


def has_letters(arr: np.ndarray, box) -> bool:
    """True when the box really still contains lettering (guards against AI guessing text in erased bubbles)."""
    H, W = arr.shape[:2]
    x0, y0, x1, y1 = int(max(0, box[0])), int(max(0, box[1])), int(min(W, box[2])), int(min(H, box[3]))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return False
    reg = arr[y0:y1, x0:x1].astype(np.int16)
    flat = reg.reshape(-1, 3)
    q = (flat // 16).astype(np.int32)
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    bg = flat[keys == np.bincount(keys).argmax()].mean(axis=0)
    d = np.abs(reg - bg).max(axis=2)
    ink = d > 90
    share = float(ink.mean())
    plain = float((d < 40).mean())
    rows = ink.mean(axis=1) > 0.02
    return 0.03 < share < 0.45 and plain > 0.5 and rows.mean() > 0.25


async def translate_point(data: bytes, y_pct: float, glossary: list[dict] | None = None) -> dict:
    """Translate whatever English is still left around a tapped spot of an (already cleaned) page."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = im.size
    cy = int(y_pct / 100 * H)
    a, b = max(0, cy - 650), min(H, cy + 650)
    gloss = glossary_text(glossary or [])
    res = await ask_llm(im.crop((0, a, W, b)), gloss)
    _raise_if_down([res])
    raw = []
    _collect(res["items"], a, b - a, W, 0, raw)
    arr = np.array(im)
    raw = [r for r in raw if re.search(r"[A-Za-z]{2,}", r["en"]) and has_letters(arr, r["t"])]
    bubbles = _apply(arr, raw, W, H)
    out = io.BytesIO()
    Image.fromarray(arr).save(out, "WEBP", quality=88)
    return {"bubbles": bubbles, "cleaned": out.getvalue(), "names": [n for n in res["names"] if isinstance(n, str)]}
