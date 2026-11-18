"""Free translation engine: text is read on the phone (Tesseract.js), translated with free Google web translation. No AI credit."""
import asyncio
import io
import logging
import os
import re

import httpx
from urllib.parse import urlencode
import numpy as np
import wordninja
from scipy import ndimage
from PIL import Image

from translator import _apply, has_letters, dedupe
from cleaner import bubble_region

logger = logging.getLogger(__name__)
WATERMARK = re.compile(r"(\.\s?(org|com|net|co|id|io)\b|scans?\b|manga\w*\.|toon|\bnet\b|discord|reset-?scan)", re.I)
GT_URL = "https://clients5.google.com/translate_a/t"
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"


def words_to_lines(words: list[dict]) -> list[dict]:
    """Join OCR words that sit on the same text row into lines."""
    ws = []
    for w in words:
        t = str(w.get("text", "")).strip().replace("|", "I")
        t = re.sub(r"^1$", "I", t)
        alpha = sum(c.isalpha() for c in t)
        if not t or alpha < 0.6 * len(t.strip(".,!?…'\"“”-")) or float(w.get("conf", 100)) < 45:
            continue
        ws.append({**w, "text": t})
    ws.sort(key=lambda w: (w["y0"], w["x0"]))
    lines: list[dict] = []
    for w in ws:
        h = w["y1"] - w["y0"]
        best = None
        for ln in lines:
            ov = min(ln["y1"], w["y1"]) - max(ln["y0"], w["y0"])
            gap = w["x0"] - ln["x1"]
            if ov > 0.5 * min(h, ln["y1"] - ln["y0"]) and -h < gap < 1.6 * h:
                best = ln
                break
        if best:
            best["text"] += " " + str(w["text"]).strip()
            best.update(x1=max(best["x1"], w["x1"]), y0=min(best["y0"], w["y0"]), y1=max(best["y1"], w["y1"]))
        else:
            lines.append({"x0": w["x0"], "x1": w["x1"], "y0": w["y0"], "y1": w["y1"], "text": str(w["text"]).strip()})
    return [ln for ln in lines if re.search(r"[A-Za-z]{2,}", ln["text"]) and not WATERMARK.search(ln["text"])
            and sum(c.isalpha() for c in ln["text"]) >= 0.5 * len(ln["text"].replace(" ", ""))
            and _real_words(ln["text"]) >= 1]


_VOCAB = wordninja.DEFAULT_LANGUAGE_MODEL._wordcost


def _real_words(text: str) -> int:
    """How many tokens are actual English words (drops OCR noise like 'Tn', 'Ree')."""
    return sum(1 for t in re.findall(r"[A-Za-z']+", text.lower()) if len(t) >= 2 and _VOCAB.get(t, 99) < 12)


def _split_chunk(chunk: str, keep: set[str]) -> str:
    if len(chunk) <= 3 or chunk.lower() in keep:
        return chunk.lower()
    if "-" in chunk:
        parts = chunk.split("-")
        return "-".join(p.lower() if len(p) <= 6 else _split_chunk(p, keep) for p in parts)
    return " ".join(wordninja.split(chunk.lower())) or chunk.lower()


def respace(line: str, keep: set[str]) -> str:
    """Comic lettering often loses spaces in OCR: 'BUTNOMATTER' -> 'but no matter'."""
    out = []
    line = re.sub(r"([,!?;:]|\.(?!\.))(?=[A-Za-z])", r"\1 ", line)
    for tok in line.split():
        m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z'’\-]*[A-Za-z]|[A-Za-z])([^A-Za-z]*)$", tok)
        if not m:
            out.append(tok.lower())
            continue
        pre, word, post = m.groups()
        word = word.replace("’", "'")
        if "'" in word:
            head, _, tail = word.partition("'")
            w = _split_chunk(head, keep)
            last = w.split(" ")[-1]
            tm = re.match(r"^(t|s|ll|re|ve|d|m)(.*)$", tail.lower())
            suffix, rest = (tm.group(1), tm.group(2)) if tm else (tail.lower(), "")
            rest = f" {_split_chunk(rest, keep)}" if rest else ""
            out.append(f"{pre}{w[: len(w) - len(last)]}{last}'{suffix}{rest}{post}")
        else:
            out.append(f"{pre}{_split_chunk(word, keep)}{post}")
    return " ".join(out)


def sentence_case(t: str, names: dict[str, str]) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"([,!?]|\.(?!\.))(?=[A-Za-z])", r"\1 ", t)
    t = re.sub(r"\bi\b", "I", t)
    t = re.sub(r"\bi'(m|ll|ve|d)\b", lambda m: "I'" + m.group(1), t)
    t = re.sub(r"(^|[.!?…]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    for low, proper in names.items():
        t = re.sub(rf"\b{re.escape(low)}\b", proper, t, flags=re.I)
    return t


def group_blocks(lines: list[dict]) -> list[dict]:
    blocks = []
    for ln in sorted(lines, key=lambda l: (l["y0"], l["x0"])):
        lh = ln["y1"] - ln["y0"]
        cx = (ln["x0"] + ln["x1"]) / 2
        target = None
        for b in blocks:
            gap = ln["y0"] - b["y1"]
            bcx = (b["x0"] + b["x1"]) / 2
            overlap = min(b["x1"], ln["x1"]) - max(b["x0"], ln["x0"])
            if -lh * 0.5 < gap < lh * 0.9 and overlap > 0 and abs(cx - bcx) < 0.45 * max(b["x1"] - b["x0"], ln["x1"] - ln["x0"]):
                target = b
                break
        if target:
            target.update(x0=min(target["x0"], ln["x0"]), x1=max(target["x1"], ln["x1"]), y1=max(target["y1"], ln["y1"]))
            target["lines"].append(ln["text"])
        else:
            blocks.append({**ln, "lines": [ln["text"]]})
    return blocks


async def _google(c: httpx.AsyncClient, chunk: list[str]) -> list[str]:
    r = await c.post(GT_URL, params={"client": "dict-chrome-ex", "sl": "en", "tl": "id"},
                     content=urlencode([("q", t) for t in chunk]),
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    res = [x[0] if isinstance(x, list) else x for x in r.json()]
    if len(res) != len(chunk):
        raise ValueError("count mismatch")
    return [str(x) for x in res]


async def _libre(c: httpx.AsyncClient, chunk: list[str]) -> list[str]:
    """Own translation server (LibreTranslate), only when LIBRETRANSLATE_URL is set."""
    base = os.environ.get("LIBRETRANSLATE_URL")
    if not base:
        raise ValueError("no LibreTranslate server configured")
    r = await c.post(f"{base.rstrip('/')}/translate", timeout=120,
                     json={"q": chunk, "source": "en", "target": "id", "format": "text"})
    r.raise_for_status()
    res = r.json()["translatedText"]
    if len(res) != len(chunk):
        raise ValueError("count mismatch")
    return [str(x) for x in res]


async def _mymemory(c: httpx.AsyncClient, chunk: list[str]) -> list[str]:
    out = []
    for t in chunk:
        try:
            j = (await c.get("https://api.mymemory.translated.net/get", params={"q": t, "langpair": "en|id"})).json()
            ok = int(j.get("responseStatus", 0)) == 200
            out.append(j["responseData"]["translatedText"] if ok else "")
        except Exception:
            out.append("")
    if not any(out):
        raise ValueError("MyMemory gave nothing")
    return out


ENGINES = {"google": _google, "libre": _libre, "mymemory": _mymemory}


async def gtranslate(texts: list[str]) -> list[str]:
    """Free translators tried in order (TRANSLATE_ORDER), next one takes over when one fails."""
    order = [e.strip() for e in os.environ.get("TRANSLATE_ORDER", "google,libre,mymemory").split(",") if e.strip() in ENGINES]
    out: list[str] = []
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": UA}) as c:
        for i in range(0, len(texts), 30):
            chunk = texts[i:i + 30]
            res = None
            for name in order:
                try:
                    res = await ENGINES[name](c, chunk)
                    break
                except Exception as exc:
                    logger.warning("translator %s failed: %s", name, exc)
            out += res or [""] * len(chunk)
    return out


SHORT_OK = {"no", "ah", "oh", "eh", "hm", "ha", "uh", "ok", "so", "me", "we", "he", "go", "hi", "ow", "us", "huh", "hah"}


def casual(t: str) -> str:
    """Webtoon dialogue reads better informal: Saya/Anda -> aku/kamu."""
    t = re.sub(r"\bAnda\b", "kamu", t, flags=re.I)
    t = re.sub(r"\bsaya\b", "aku", t, flags=re.I)
    t = re.sub(r"\bkamu sekalian\b", "kalian", t)
    return re.sub(r"(^|[.!?…]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)


async def _blocks_to_raw(blocks: list[dict], glossary: list[dict]) -> list[dict]:
    keep = {g["en"].lower() for g in glossary} | {p.lower() for g in glossary for p in g["en"].split("-")}
    names = {g["en"].lower(): g["id"] for g in glossary}
    texts, kept = [], []
    for b in blocks:
        joined = ""
        for ln in b["lines"]:
            ln = respace(ln, keep)
            joined = joined[:-1] + ln if joined.endswith("-") else f"{joined} {ln}".strip()
        letters = sum(c.isalpha() for c in joined)
        if WATERMARK.search(joined) or (letters < 3 and joined.lower().strip(".!?, ") not in SHORT_OK):
            continue
        texts.append(sentence_case(joined, names))
        kept.append(b)
    trans = await gtranslate(texts)
    if texts and not any(trans):
        raise RuntimeError("free translator unavailable")
    raw = []
    for b, en, idt in zip(kept, texts, trans):
        idt = casual(sentence_case(idt, names)) if idt else ""
        if not idt:
            continue
        box = [b["x0"], b["y0"], b["x1"], b["y1"]]
        raw.append({"t": box, "b": box, "shape": "ellipse", "en": en, "id": idt[0].upper() + idt[1:]})
    return raw


def _encode(arr: np.ndarray) -> bytes:
    out = io.BytesIO()
    Image.fromarray(arr).save(out, "WEBP", quality=88)
    return out.getvalue()


async def free_translate_image(data: bytes, glossary: list[dict] | None = None, words: list[dict] | None = None) -> dict:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = im.size
    raw = await _blocks_to_raw(group_blocks(words_to_lines(words or [])), glossary or [])
    arr = np.array(im)
    bubbles = dedupe(_apply(arr, raw, W, H))
    bubbles.sort(key=lambda bb: (round(bb["y"], 1), bb["x"]))
    return {"width": W, "height": H, "bubbles": bubbles, "names": [], "cleaned": _encode(arr), "partial": False}


async def free_extra(cleaned_bytes: bytes, words: list[dict], glossary: list[dict] | None = None) -> dict:
    """Leftover English found on the cleaned page (second check or a tap) gets translated too."""
    im = Image.open(io.BytesIO(cleaned_bytes)).convert("RGB")
    W, H = im.size
    arr = np.array(im)
    lines = [ln for ln in words_to_lines(words) if has_letters(arr, [ln["x0"], ln["y0"], ln["x1"], ln["y1"]])]
    raw = await _blocks_to_raw(group_blocks(lines), glossary or [])
    bubbles = _apply(arr, raw, W, H)
    return {"bubbles": bubbles, "cleaned": _encode(arr), "names": []}


def find_regions(data: bytes, words: list[dict], cleaned: bool = False) -> list[list[float]]:
    """Turn page-level OCR words into whole-bubble boxes for a sharper second read."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(im)
    lines = words_to_lines(words)
    if cleaned:
        lines = [ln for ln in lines if has_letters(arr, [ln["x0"], ln["y0"], ln["x1"], ln["y1"]])]
    boxes = []
    for b in group_blocks(lines):
        r = bubble_region(arr, [b["x0"], b["y0"], b["x1"], b["y1"]])
        if r:
            boxes.append(r)
    merged: list[list[float]] = []
    for r in sorted(boxes, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True):
        hit = next((m for m in merged if min(m[2], r[2]) - max(m[0], r[0]) > 0 and min(m[3], r[3]) - max(m[1], r[1]) > 0), None)
        if hit:
            hit[:] = [min(hit[0], r[0]), min(hit[1], r[1]), max(hit[2], r[2]), max(hit[3], r[3])]
        else:
            merged.append(list(r))
    return sorted(merged, key=lambda r: (r[1], r[0]))


def clean_ocr(text: str) -> str:
    """Drop OCR noise tokens ('=', 'N77', '_N') and fix look-alikes (1S -> IS)."""
    text = text.replace("|", "I").replace("—", " ").replace("_", " ")
    out = []
    for tok in text.split():
        tok = re.sub(r"(?<=[A-Za-z])1|1(?=[A-Za-z])", "I", tok)
        tok = re.sub(r"(?<=[A-Za-z])0|0(?=[A-Za-z])", "O", tok)
        letters = sum(c.isalpha() for c in tok)
        core = re.sub(r"[^A-Za-z']", "", tok).lower()
        if letters == 0 and not re.fullmatch(r"[.!?…]+", tok):
            continue
        if letters and letters < 0.6 * len(tok.strip(".,!?…'\"“”()-")):
            continue
        if letters and len(core) <= 2 and core not in SHORT_OK | {"i", "a", "an", "at", "be", "by", "do", "if", "in", "is", "it", "my", "of", "on", "or", "to", "up"}:
            continue
        out.append(tok)
    return " ".join(out).strip()


async def regions_to_raw(regions: list[dict], glossary: list[dict]) -> list[dict]:
    """regions: [{box:[x0,y0,x1,y1], text:"..."}] read bubble-by-bubble on the phone.
    When the phone already translated them (id given, translator v1/v2/v3) they are used as they are."""
    if regions and all(r.get("id") for r in regions):
        return [{"t": r["box"], "b": r["box"], "shape": "ellipse", "en": str(r.get("text", "")), "id": str(r["id"])}
                for r in regions]
    blocks, seen = [], set()
    for r in regions:
        txt = clean_ocr(str(r.get("text", "")))
        # white-on-dark boxes can be artwork highlights: ask for real sentences there
        need = 2 if r.get("inv") and len(txt.split()) > 1 else 1
        if not txt or txt.lower() in seen or _real_words(txt) < need:
            continue
        seen.add(txt.lower())
        x0, y0, x1, y1 = r["box"]
        blocks.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "lines": [txt]})
    return await _blocks_to_raw(blocks, glossary)


async def free_translate_regions(data: bytes, regions: list[dict], glossary: list[dict] | None = None, base: bool = True) -> dict:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    W, H = im.size
    arr = np.array(im)
    raw = await regions_to_raw(regions, glossary or [])
    bubbles = dedupe(_apply(arr, raw, W, H))
    bubbles.sort(key=lambda bb: (round(bb["y"], 1), bb["x"]))
    return {"width": W, "height": H, "bubbles": bubbles, "names": [], "cleaned": _encode(arr), "partial": False}


def text_candidates(data: bytes, y_range: tuple[float, float] | None = None) -> list[list[float]]:
    """Find lettering with plain image processing (no OCR, no AI).
    Dark letters on light bubbles, plus white narration on dark boxes (those boxes end with a 1 = read inverted)."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(im)
    gray = np.asarray(im.convert("L"), dtype=np.int16)
    H, W = gray.shape
    y0r, y1r = (0, H) if not y_range else (max(0, int(y_range[0])), min(H, int(y_range[1])))
    g = gray[y0r:y1r]
    normal = _detect(arr, g, g < 110, g > 195, y0r)
    # white lettering is bright AND colourless (skin, sky or pink stone are not)
    white = (arr[y0r:y1r].min(axis=2) > 160) & (g > 185)
    inverted = [b + [1.0] for b in _cluster(_detect(arr, g, white, g < 90, y0r, strict=True))
                if b[2] - b[0] >= 30 and b[3] - b[1] >= 12 and not any(_overlap(b, n) > 0.3 for n in normal)]
    return sorted(normal + inverted, key=lambda r: (r[1], r[0]))


def _cluster(boxes: list[list[float]]) -> list[list[float]]:
    """White narration sits on open dark areas (no bubble outline): join words into lines, lines into blocks."""
    lines: list[list[float]] = []
    for b in sorted(boxes, key=lambda b: (b[1], b[0])):
        h = b[3] - b[1]
        ln = next((l for l in lines if min(l[3], b[3]) - max(l[1], b[1]) > 0.5 * min(h, l[3] - l[1])
                   and -h < max(b[0] - l[2], l[0] - b[2]) < 2.2 * h), None)
        if ln:
            ln[:] = [min(ln[0], b[0]), min(ln[1], b[1]), max(ln[2], b[2]), max(ln[3], b[3])]
        else:
            lines.append(list(b[:4]))
    lines = [l for l in lines if l[2] - l[0] >= 0.9 * (l[3] - l[1]) and l[3] - l[1] >= 8]
    blocks = group_blocks([{"x0": l[0], "y0": l[1], "x1": l[2], "y1": l[3], "text": ""} for l in lines])
    out = sorted(([b["x0"], b["y0"], b["x1"], b["y1"]] for b in blocks), key=lambda r: (r[1], r[0]))
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(out):
            j = next((j for j in range(i + 1, len(out)) if _overlap(a, out[j]) > 0.2), None)
            if j is not None:
                b = out.pop(j)
                a[:] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                changed = True
                break
    return out


def _overlap(a: list[float], b: list[float]) -> float:
    inter = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return inter / max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def _detect(arr: np.ndarray, g: np.ndarray, dark: np.ndarray, plain_px: np.ndarray, y0r: int,
            strict: bool = False) -> list[list[float]]:
    """dark = letter pixels, plain_px = background pixels (swapped for white-on-dark text)."""
    lab, _ = ndimage.label(dark, structure=np.ones((3, 3)))
    letters = np.zeros_like(dark)
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None:
            continue
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 7 <= h <= 70 and 2 <= w <= 110:
            comp = lab[sl] == i + 1
            fill = comp.mean()
            if 0.08 < fill < 0.9 or (fill >= 0.9 and w <= 0.4 * h):  # thin strokes: l, I, i
                letters[sl] |= comp
    grown = ndimage.binary_dilation(letters, structure=np.ones((7, 13)))
    blab, _ = ndimage.label(grown)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(blab)):
        if sl is None:
            continue
        by0, by1, bx0, bx1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if bx1 - bx0 < 22 or by1 - by0 < 10:
            continue
        inside = letters[by0:by1, bx0:bx1] & (blab[by0:by1, bx0:bx1] == i + 1)
        clab, n = ndimage.label(inside, structure=np.ones((3, 3)))
        plain = float(plain_px[by0:by1, bx0:bx1].mean())
        if n < 3 or plain < 0.45:
            continue
        if strict and not _looks_like_text(clab):
            continue
        # each text line asks which bubble it lives in, so two touching bubbles stay separate
        sub, _ = ndimage.label(ndimage.binary_dilation(inside, structure=np.ones((3, 11))) & grown[by0:by1, bx0:bx1])
        for ssl in ndimage.find_objects(sub):
            if ssl is None:
                continue
            ys, xs = np.where(inside[ssl])
            if not len(ys):
                continue
            box = [float(bx0 + ssl[1].start + xs.min()), float(y0r + by0 + ssl[0].start + ys.min()),
                   float(bx0 + ssl[1].start + xs.max() + 1), float(y0r + by0 + ssl[0].start + ys.max() + 1)]
            r = bubble_region(arr, box)
            boxes.append(r or box)
    merged: list[list[float]] = []
    area = lambda r: max(1.0, (r[2] - r[0]) * (r[3] - r[1]))
    for r in sorted(boxes, key=area, reverse=True):
        hit = next((m for m in merged if _overlap(m, r) > 0.5), None)
        if hit:
            hit[:] = [min(hit[0], r[0]), min(hit[1], r[1]), max(hit[2], r[2]), max(hit[3], r[3])]
        else:
            merged.append(list(r))
    out = []
    for r in merged:
        out += _split_gaps(letters, r, y0r)
    return out


def _looks_like_text(clab: np.ndarray) -> bool:
    """Bright specks in dark artwork (sparkles, eye shine) vs. a real row of letters:
    letters share a similar height and sit next to each other on a line."""
    objs = [s for s in ndimage.find_objects(clab) if s is not None]
    hs = np.array([s[0].stop - s[0].start for s in objs], dtype=float)
    if len(objs) < 3:
        return False
    med = float(np.median(hs))
    similar = hs[(hs > 0.55 * med) & (hs < 1.6 * med)]
    return len(similar) >= 3 and len(similar) >= 0.6 * len(hs)


def _split_gaps(letters: np.ndarray, r: list[float], y_off: int) -> list[list[float]]:
    """Split a box where its text has a tall empty gap (two bubbles that touch)."""
    x0, y0, x1, y1 = int(r[0]), int(r[1]) - y_off, int(r[2]), int(r[3]) - y_off
    sub = letters[max(0, y0):max(0, y1), max(0, x0):x1]
    if sub.size == 0:
        return [r]
    rows = sub.any(axis=1)
    runs, start = [], None
    for i, v in enumerate(rows):
        if v and start is None:
            start = i
        if not v and start is not None:
            runs.append((start, i)); start = None
    if start is not None:
        runs.append((start, len(rows)))
    if len(runs) < 2:
        return [r]
    lh = float(np.median([b - a for a, b in runs]))
    parts, cur = [], [runs[0]]
    for a, b in runs[1:]:
        if a - cur[-1][1] > 2.2 * lh:
            parts.append(cur); cur = []
        cur.append((a, b))
    parts.append(cur)
    if len(parts) == 1:
        return [r]
    res = []
    for p in parts:
        pa, pb = p[0][0], p[-1][1]
        cols = np.where(sub[pa:pb].any(axis=0))[0]
        res.append([float(max(0, x0) + cols.min()), float(max(0, y0) + pa + y_off),
                    float(max(0, x0) + cols.max() + 1), float(max(0, y0) + pb + y_off)])
    return res
