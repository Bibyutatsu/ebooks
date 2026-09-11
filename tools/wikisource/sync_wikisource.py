"""
Bengali Wikisource Ingestion Pipeline.

Two-phase approach:
  Phase 1: Enumerate works from bn.wikisource.org via MediaWiki categorymembers API.
           Saves list to tools/wikisource/works_list.json.
  Phase 2: For each work, create a catalog entry with a direct ws-export EPUB link
           as the download_url (no re-hosting required). Generates typographic covers.

Usage:
    # Enumerate works (run once):
    python3 tools/wikisource/sync_wikisource.py --enumerate-only --limit 2000

    # Ingest from saved works_list.json:
    python3 tools/wikisource/sync_wikisource.py --catalog ./catalog.json

    # Filter to specific authors:
    python3 tools/wikisource/sync_wikisource.py --authors "রবীন্দ্রনাথ ঠাকুর,কাজী নজরুল ইসলাম"
"""

import sys, re, io, json, time, hashlib, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from author_mapping import get_author_info, find_author_match
from series_mapping import detect_series
from transliteration import transliterate_text
from build_catalog import slugify

SOURCE_TAG = "wikisource"
WS_API = "https://bn.wikisource.org/w/api.php"
WS_EXPORT_BASE = "https://ws-export.wmcloud.org/"
WORKS_LIST_PATH = Path(__file__).parent / "works_list.json"
UA = "BibyutatsuEbooks/1.0 (+https://bibyutatsu.github.io/ebooks)"

def norm(s): return unicodedata.normalize("NFC", s.strip())
def norm_bn(s):
    s = s.replace("\u09af\u09bc", "\u09df").replace("\u09a1\u09bc", "\u09dc").replace("\u09a2\u09bc", "\u09dd")
    return s.strip().lower()

def http_get(url, retries=3, timeout=30):
    ua = {"User-Agent": "BibyutatsuEbooks/1.0 (+https://bibyutatsu.github.io/ebooks)"}
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=ua, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    return b""

def generate_cover_image(title, author, out_path, width=300, height=450):
    palettes = [
        ((15,23,42),(30,41,59),(56,189,248)), ((19,24,39),(31,41,55),(251,146,60)),
        ((24,24,27),(39,39,42),(167,139,250)), ((17,24,39),(31,41,55),(52,211,153)),
        ((30,27,75),(49,46,129),(244,114,182)), ((20,30,45),(15,60,90),(250,204,21)),
        ((26,20,46),(45,30,80),(99,210,180)), ((39,25,55),(60,40,90),(255,200,80)),
    ]
    h = int(hashlib.md5(f"{title}{author}".encode()).hexdigest()[:6], 16)
    bg1, bg2, accent = palettes[h % len(palettes)]
    img = Image.new("RGB", (width, height), bg1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        f = y / height
        draw.line([(0,y),(width,y)], fill=(int(bg1[0]*(1-f)+bg2[0]*f), int(bg1[1]*(1-f)+bg2[1]*f), int(bg1[2]*(1-f)+bg2[2]*f)))
    draw.rectangle([14,14,width-14,height-14], outline=accent, width=1)
    draw.line([6,0,6,height], fill=(255,255,255,40), width=2)
    # Small Wikisource badge
    draw.rectangle([width-60, height-28, width-10, height-8], fill=(30,40,60), outline=accent, width=1)
    fp = "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc"
    try:
        ft = ImageFont.truetype(fp, 22); fa = ImageFont.truetype(fp, 15); fo = ImageFont.truetype(fp, 11)
    except:
        ft = fa = fo = ImageFont.load_default()
    draw.text((width/2, 70), "✦ উইকিসংকলন ✦", fill=accent, font=fo, anchor="mm")
    words = title.split(); lines, curr = [], []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 15:
            lines.append(" ".join(curr[:-1]) if len(curr)>1 else w); curr = [w] if len(curr)>1 else []
    if curr: lines.append(" ".join(curr))
    if not lines: lines = [title]
    sy = height/2 - len(lines)*16
    for i, line in enumerate(lines):
        draw.text((width/2, sy+i*30), line, fill=(245,245,245), font=ft, anchor="mm")
    draw.text((width/2, height-70), author, fill=accent, font=fa, anchor="mm")
    draw.text((width-35, height-18), "WS", fill=accent, font=fo, anchor="mm")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=82)

# ------------------------------------------------------------------
# Phase 1: Enumerate works from Wikisource
# ------------------------------------------------------------------
def enumerate_works(limit=2000, category="রচনা"):
    """Walk bn.wikisource.org Category:রচনা and collect all page titles."""
    print(f"Enumerating Wikisource category: {category} (limit={limit})")
    works = []
    params = {
        "action": "query", "list": "categorymembers",
        "cmtitle": f"Category:{category}", "cmlimit": "500",
        "cmtype": "page", "format": "json",
    }
    cmcontinue = None
    while len(works) < limit:
        url = WS_API + "?" + "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        if cmcontinue:
            url += f"&cmcontinue={quote(cmcontinue)}"
        try:
            raw = http_get(url, timeout=30)
            data = json.loads(raw)
        except Exception as e:
            print(f"[WARN] API error: {e}"); break
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            title = m["title"]
            # Strip "রচনা:" prefix if present
            if ":" in title:
                title = title.split(":", 1)[1]
            works.append({"wiki_title": title, "page_id": m["pageid"]})
        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break
        time.sleep(0.5)

    print(f"Enumerated {len(works)} works.")
    return works[:limit]

def build_ws_export_url(title):
    """Direct ws-export EPUB link for a Bengali Wikisource title."""
    clean = title.replace(" ", "_")
    if not clean.startswith("রচনা:"):
        clean = f"রচনা:{clean}"
    ns_part, name_part = clean.split(":", 1)
    encoded_page = f"{quote(ns_part)}:{quote(name_part)}"
    return f"{WS_EXPORT_BASE}?lang=bn&page={encoded_page}&format=epub-3"

# ------------------------------------------------------------------
# Phase 2: Ingest into catalog (direct-link, no re-hosting)
# ------------------------------------------------------------------
def ingest_wikisource(catalog_path, covers_dir, authors_filter=None, limit=None, dry_run=False):
    catalog_file = Path(catalog_path)
    covers_path = Path(covers_dir)
    covers_path.mkdir(parents=True, exist_ok=True)

    if not WORKS_LIST_PATH.exists():
        print("works_list.json not found. Run with --enumerate-only first.")
        sys.exit(1)

    with open(WORKS_LIST_PATH, encoding="utf-8") as f:
        works = json.load(f)
    print(f"Loaded {len(works)} works from works_list.json")

    with open(catalog_file, encoding="utf-8") as f:
        catalog = json.load(f)

    existing_books = catalog["books"]
    book_by_at, book_by_t = {}, {}
    book_by_id = {b["id"]: b for b in existing_books}
    for b in existing_books:
        k = (norm_bn(b["author"]), norm_bn(b["title"]))
        book_by_at[k] = b
        book_by_t.setdefault(norm_bn(b["title"]), b)
    seen_ids = set(book_by_id)

    if limit:
        works = works[:limit]

    new_books, meta_dump = [], []
    new_count, updated, skipped, gen_cov = 0, 0, 0, 0

    cache_file = Path(__file__).parent / "resolved_authors.json"
    cached_authors = {}
    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                cached_authors = json.load(f)
        except Exception:
            pass

    for i, work in enumerate(works):
        wiki_title = work["wiki_title"]

        # Try to extract author from wiki_title or category cache
        parts = wiki_title.split("/")
        if len(parts) >= 2:
            raw_author = norm(parts[0])
            raw_title = norm("/".join(parts[1:]))
        else:
            raw_author = work.get("author", "") or cached_authors.get(wiki_title, "")
            raw_title = norm(wiki_title)

        if not raw_title:
            continue

        # Author filter
        if authors_filter:
            matched_filter = any(norm_bn(af) in norm_bn(raw_author) for af in authors_filter)
            if not matched_filter:
                continue

        print(f"[{i+1}/{len(works)}] {raw_author or '?'} — {raw_title}", end=" ", flush=True)

        am = find_author_match(raw_author) if raw_author else None
        if am:
            clean_author, author_info = am["canonical_bn"], am
        elif raw_author:
            trans = transliterate_text(raw_author)
            author_info = get_author_info(raw_author, trans[0] if trans else raw_author)
            clean_author = author_info["canonical_bn"]
        else:
            author_info = get_author_info("Unknown", "Unknown")
            clean_author = "অজ্ঞাত"

        clean_title = raw_title
        a_key, t_key = norm_bn(clean_author), norm_bn(clean_title)
        matched = book_by_at.get((a_key, t_key))
        if not matched:
            cand = book_by_t.get(t_key)
            if cand and norm_bn(cand["author"]) == a_key: matched = cand

        # Direct ws-export link (no download needed)
        export_url = build_ws_export_url(f"{raw_author}/{raw_title}" if raw_author else raw_title)
        clean_title_wiki = wiki_title if wiki_title.startswith("রচনা:") else f"রচনা:{wiki_title}"
        ns_p, name_p = clean_title_wiki.split(":", 1)
        ws_page_url = f"https://bn.wikisource.org/wiki/{quote(ns_p)}:{quote(name_p.replace(' ','_'))}"

        fmt_entry = {
            "filename": f"{slugify(raw_title) or 'ws-book'}.epub",
            "relative_path": "",
            "size_bytes": 0, "size_formatted": "~",
            "download_url": export_url,
            "source_page_url": ws_page_url,
            "source": SOURCE_TAG,
        }

        if matched:
            if "epub" not in matched["formats"]:
                print("→ updating")
                matched["formats"]["epub"] = fmt_entry
                updated += 1
                if not matched.get("cover"):
                    cov_file = covers_path / f"{matched['id']}.webp"
                    generate_cover_image(matched["title"], matched["author"], cov_file)
                    matched["cover"] = f"assets/covers/{matched['id']}.webp"
                    gen_cov += 1
            else:
                print("→ dup, skip"); skipped += 1
            continue

        # New book
        print("→ new")
        genres = set(author_info.get("default_genres", ["ক্লাসিক ও সাহিত্য (Classics)"]))
        genres.add("বাংলা উইকিসংকলন (Wikisource)")
        genres_list = sorted(genres)
        title_translit = transliterate_text(clean_title)
        title_en = title_translit[0].title() if title_translit else clean_title
        book_id = slugify(f"{author_info['en']}-{title_en}") or f"ws-{len(new_books)+1}"
        orig_id = book_id; counter = 2
        while book_id in seen_ids:
            book_id = f"{orig_id}-{counter}"; counter += 1
        seen_ids.add(book_id)

        cov_file = covers_path / f"{book_id}.webp"
        generate_cover_image(clean_title, clean_author, cov_file)
        gen_cov += 1

        series = detect_series(clean_title, clean_author)
        search_tokens = {clean_title.lower(), clean_author.lower(), author_info["en"].lower()}
        for a in author_info.get("aliases", []): search_tokens.add(a.lower())
        for t in title_translit[:4]: search_tokens.add(t.lower())
        if series: search_tokens.update([series["name_bn"].lower(), series["name_en"].lower()])
        search_tokens.update(["wikisource", "উইকিসংকলন"])

        nb = {
            "id": book_id, "title": clean_title, "title_en": title_en,
            "title_translit": title_translit[:4], "author": clean_author,
            "author_en": author_info["en"], "author_aliases": author_info.get("aliases",[]),
            "series": series, "genres": genres_list, "year": "",
            "description": f"বাংলা উইকিসংকলন থেকে সংগৃহীত। মূল পাতা: {ws_page_url}",
            "cover": f"assets/covers/{book_id}.webp",
            "formats": {"epub": fmt_entry},
            "search_text": " ".join(search_tokens),
            "source": SOURCE_TAG,
        }
        new_books.append(nb); new_count += 1
        book_by_at[(a_key, t_key)] = nb
        book_by_t.setdefault(t_key, nb)
        meta_dump.append({"wiki_title": wiki_title, "book_id": book_id, "status": "new"})

    if dry_run:
        print(f"\n[DRY RUN] new={new_count} updated={updated} skipped={skipped}"); return

    all_books = existing_books + new_books
    ac, gc, fc = {}, {}, {}
    for b in all_books:
        ac[b["author"]] = ac.get(b["author"], 0) + 1
        for g in b["genres"]: gc[g] = gc.get(g, 0) + 1
        for fmt in b["formats"]: fc[fmt] = fc.get(fmt, 0) + 1

    catalog["books"] = all_books
    catalog["stats"] = {"total_books": len(all_books), "total_authors": len(ac), "formats": fc, "genres_count": len(gc)}
    catalog["top_authors"] = [{"author": k, "author_en": get_author_info(k)["en"], "count": v}
                               for k, v in sorted(ac.items(), key=lambda x: x[1], reverse=True)[:30]]
    catalog["genres"] = [{"genre": k, "count": v} for k, v in sorted(gc.items(), key=lambda x: x[1], reverse=True)]

    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    meta_path = Path(__file__).parent / "books_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_dump, f, ensure_ascii=False, indent=2)

    print(f"\n--- Wikisource Summary ---")
    print(f"New: {new_count}  Updated: {updated}  Skipped: {skipped}  Covers generated: {gen_cov}")
    print(f"Total books: {len(all_books)}  Authors: {len(ac)}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", "-c", default="./catalog.json")
    p.add_argument("--covers-dir", default="./assets/covers")
    p.add_argument("--enumerate-only", action="store_true", help="Only enumerate + save works_list.json")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--authors", default=None, help="Comma-separated Bengali author name filter")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    authors_filter = [x.strip() for x in a.authors.split(",")] if a.authors else None

    if a.enumerate_only or not WORKS_LIST_PATH.exists():
        works = enumerate_works(limit=a.limit or 2000)
        with open(WORKS_LIST_PATH, "w", encoding="utf-8") as f:
            json.dump(works, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(works)} works to {WORKS_LIST_PATH}")
        if a.enumerate_only:
            sys.exit(0)

    ingest_wikisource(a.catalog, a.covers_dir, authors_filter=authors_filter, limit=a.limit, dry_run=a.dry_run)
