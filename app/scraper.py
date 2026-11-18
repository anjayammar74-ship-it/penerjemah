import hashlib
import html as htmllib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")
CACHE_DIR = Path(tempfile.gettempdir()) / "balona_img_cache"  # works on Linux, Windows and Android
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def origin_of(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"


async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers={"User-Agent": UA}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


def _clean_title(raw: str) -> str:
    t = htmllib.unescape(raw).strip()
    return re.split(r"\s[–\-|]\s(?=[^–\-|]*$)", t)[0].strip() if " – " in t or " | " in t else t


def parse_chapter(url: str, page: str) -> dict:
    m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    title = _clean_title(m.group(1)) if m else url
    images, prev_url, next_url = [], None, None

    m = re.search(r"ts_reader\.run\((\{.*?\})\);", page, re.S)
    if m:
        data = json.loads(m.group(1))
        srcs = data.get("sources") or []
        if srcs:
            images = srcs[0].get("images") or []
        prev_url = data.get("prevUrl") or None
        next_url = data.get("nextUrl") or None

    if not images:
        area = re.search(r'id=["\']readerarea["\'].*?>(.*?)</div>', page, re.S)
        block = area.group(1) if area else page
        for tag in re.findall(r"<img[^>]+>", block):
            src = re.search(r'(?:data-src|data-lazy-src|src)=["\']([^"\']+)["\']', tag)
            if src and re.search(r"\.(jpe?g|png|webp)", src.group(1), re.I):
                images.append(urljoin(url, src.group(1).strip()))
        if not area:
            images = [i for i in images if "/uploads/" in i and not re.search(r"-\d+x\d+\.", i)]

    if not next_url:
        n = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*(?:rel=["\']next["\']|class=["\'][^"\']*next)', page)
        next_url = urljoin(url, n.group(1)) if n else None
    if not prev_url:
        p = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*(?:rel=["\']prev["\']|class=["\'][^"\']*prev)', page)
        prev_url = urljoin(url, p.group(1)) if p else None

    series_url = None
    m = re.search(r'class="allc"[^>]*>.*?<a href="([^"]+)"', page, re.S)
    if m:
        series_url = m.group(1)
    else:
        crumbs = re.findall(r'itemprop="item" href="([^"]+)"', page)
        series_url = crumbs[-2] if len(crumbs) >= 3 else None

    return {"url": url, "title": title, "prev_url": prev_url, "next_url": next_url,
            "series_url": series_url, "series_key": series_key(url),
            "images": [htmllib.unescape(i) for i in images]}


def series_key(url: str) -> str:
    p = urlparse(url)
    path = p.path.strip("/")
    m = re.match(r"(.+?)-chapter-[\d.-]+$", path.split("/")[-1])
    slug = m.group(1) if m else path.split("/")[-1]
    return f"{p.netloc}:{slug}"


def parse_series(url: str, page: str) -> dict:
    m = re.search(r'<h1 class="entry-title"[^>]*>(.*?)</h1>', page, re.S)
    title = htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
    if not title:
        t = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
        title = _clean_title(t.group(1)) if t else url
    cover = None
    c = re.search(r'<div class="thumb"[^>]*>\s*<img[^>]+src="([^"]+)"', page, re.S)
    if c:
        cover = c.group(1)
    syn = re.search(r'<div class="entry-content entry-content-single"[^>]*>(.*?)</div>', page, re.S)
    synopsis = htmllib.unescape(re.sub(r"<[^>]+>", " ", syn.group(1))).strip() if syn else ""
    synopsis = re.sub(r"\s+", " ", synopsis)[:600]
    chapters = []
    for num, body in re.findall(r'<li data-num="([^"]*)">(.*?)</li>', page, re.S):
        h = re.search(r'href="([^"]+)"', body)
        d = re.search(r'class="chapterdate">([^<]*)', body)
        chapters.append({"num": num.strip(), "url": h.group(1) if h else None,
                         "date": d.group(1).strip() if d else "",
                         "locked": h is None or "lockedChapterModal" in body})
    if not chapters:
        seen = set()
        for href in re.findall(r'href="([^"]+-chapter-[\d.-]+/?)"', page):
            if href not in seen:
                seen.add(href)
                n = re.search(r"chapter-([\d.-]+)", href)
                chapters.append({"num": n.group(1) if n else "", "url": urljoin(url, href), "date": "", "locked": False})
    first = next((ch["url"] for ch in chapters if ch["url"]), url)
    return {"url": url, "title": title, "cover": cover, "synopsis": synopsis,
            "series_key": series_key(first), "chapters": chapters}


def _cache_path(img_url: str) -> Path:
    return CACHE_DIR / hashlib.sha256(img_url.encode()).hexdigest()


async def fetch_image(img_url: str, referer: str | None = None) -> tuple[bytes, str]:
    path = _cache_path(img_url)
    if path.exists():
        data = path.read_bytes()
        return data, path.with_suffix(".type").read_text() if path.with_suffix(".type").exists() else "image/jpeg"
    headers = {"User-Agent": UA, "Referer": referer or origin_of(img_url)}
    async with httpx.AsyncClient(follow_redirects=True, timeout=60, headers=headers) as c:
        r = await c.get(img_url)
        r.raise_for_status()
    ctype = r.headers.get("content-type", "image/jpeg").split(";")[0]
    path.write_bytes(r.content)
    path.with_suffix(".type").write_text(ctype)
    return r.content, ctype
