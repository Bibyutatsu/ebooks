"""
Eboipotro (ই-বইপত্র) OPDS Ingestion Pipeline.

Fetches all 246 books from https://eboipotro.github.io/opds/by_name.atom,
downloads EPUBs from direct GitHub raw URLs, extracts metadata, deduplicates
against existing catalog, and updates catalog.json.

Usage:
    python3 tools/eboipotro/sync_eboipotro.py [--catalog ./catalog.json]
        [--covers-dir ./assets/covers] [--download-dir /tmp/eboipotro]
        [--dry-run]
"""

import os, sys, re, io, json, time, zipfile, hashlib, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from author_mapping import get_author_info, find_author_match
from series_mapping import detect_series
from transliteration import transliterate_text
from build_catalog import format_size, slugify

OPDS_URL = "https://eboipotro.github.io/opds/by_name.atom"
EBOIPOTRO_BASE = "https://eboipotro.github.io"
SOURCE_TAG = "eboipotro"
ATOM_NS = "http://www.w3.org/2005/Atom"

GENRE_FROM_PATH = {
    "নাটক": "নাটক (Drama)",
    "কবিতা": "কবিতা (Poetry)",
    "গল্প": "ছোটগল্প (Short Stories)",
    "উপন্যাস": "উপন্যাস (Novel)",
    "প্রবন্ধ": "প্রবন্ধ (Essays)",
    "ছোটগল্প": "ছোটগল্প (Short Stories)",
    "আত্মজীবনী": "আত্মজীবনী ও স্মৃতিকথা (Memoir)",
}

def norm(s): return unicodedata.normalize("NFC", s.strip())
def norm_bn(s):
    s = s.replace("\u09af\u09bc", "\u09df").replace("\u09a1\u09bc", "\u09dc").replace("\u09a2\u09bc", "\u09dd")
    return s.strip().lower()

def is_english_text(s):
    letters = [c for c in s if c.isalpha()]
    if not letters: return False
    ascii_count = sum(1 for c in letters if ord(c) < 128)
    return ascii_count / len(letters) > 0.6

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

def extract_cover_from_epub_bytes(epub_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(epub_bytes)) as z:
            imgs = [(n, z.getinfo(n).file_size) for n in z.namelist()
                    if n.lower().endswith((".jpg",".jpeg",".png",".webp"))
                    and z.getinfo(n).file_size > 5000
                    and not any(bad in n.lower() for bad in ("accueil","segment","diamond","tear"))]
            if imgs:
                imgs.sort(key=lambda x: (1 if any(k in x[0].lower() for k in ("cover","page1")) else 0, x[1]), reverse=True)
                data = z.read(imgs[0][0])
                im = Image.open(io.BytesIO(data))
                if im.size[0] >= 120 and im.size[1] >= 120:
                    return data
    except Exception:
        pass
    return None

def generate_cover_image(title, author, out_path, width=300, height=450):
    palettes = [
        ((15,23,42),(30,41,59),(56,189,248)), ((19,24,39),(31,41,55),(251,146,60)),
        ((24,24,27),(39,39,42),(167,139,250)), ((17,24,39),(31,41,55),(52,211,153)),
        ((30,27,75),(49,46,129),(244,114,182)), ((20,30,45),(15,60,90),(250,204,21)),
        ((26,20,46),(45,30,80),(99,210,180)),
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
    fp = "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc"
    try:
        ft = ImageFont.truetype(fp, 22); fa = ImageFont.truetype(fp, 15); fo = ImageFont.truetype(fp, 13)
    except:
        ft = fa = fo = ImageFont.load_default()
    draw.text((width/2, 70), "✦ ✦ ✦", fill=accent, font=fo, anchor="mm")
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=82)

def save_cover_webp(cover_bytes, out_path, max_w=300, max_h=450):
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
        im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        im.save(out_path, "WEBP", quality=78)
        return True
    except:
        return False

def fetch_opds_cover(img_url):
    if not img_url: return None
    if img_url.startswith("/"): img_url = EBOIPOTRO_BASE + img_url
    try:
        data = http_get(img_url, retries=2, timeout=15)
        im = Image.open(io.BytesIO(data))
        if im.size[0] >= 100 and im.size[1] >= 100: return data
    except:
        pass
    return None

def parse_opds(url):
    print(f"Fetching OPDS feed: {url}")
    raw = http_get(url, timeout=60)
    root = ET.fromstring(raw)
    ns = {"atom": ATOM_NS}
    entries = []
    for entry in root.findall(".//atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        author_el = entry.find(".//atom:author/atom:name", ns)
        summary_el = entry.find("atom:summary", ns)
        title = (title_el.text or "").strip() if title_el is not None else ""
        author = (author_el.text or "").strip() if author_el is not None else ""
        summary = (summary_el.text or "").strip() if summary_el is not None else ""
        epub_url, img_url = "", ""
        for link in entry.findall("atom:link", ns):
            rel, href = link.get("rel",""), link.get("href","")
            if "acquisition" in rel: epub_url = href
            elif "opds-spec.org/image" in rel and "thumbnail" not in rel: img_url = href
        genre_hint = ""
        if epub_url:
            for seg, genre in GENRE_FROM_PATH.items():
                if f"/{seg}/" in epub_url: genre_hint = genre; break
        if epub_url:
            entries.append({"title": title, "author": author, "summary": summary,
                            "epub_url": epub_url, "img_url": img_url,
                            "genre_hint": genre_hint, "is_english": is_english_text(title)})
    print(f"Parsed {len(entries)} entries.")
    return entries

def ingest_eboipotro(catalog_path, covers_dir, download_dir, dry_run=False):
    catalog_file = Path(catalog_path)
    covers_path = Path(covers_dir)
    dl_path = Path(download_dir)
    dl_path.mkdir(parents=True, exist_ok=True)
    covers_path.mkdir(parents=True, exist_ok=True)

    with open(catalog_file, encoding="utf-8") as f:
        catalog = json.load(f)

    existing_books = catalog["books"]
    book_by_id = {b["id"]: b for b in existing_books}
    book_by_at, book_by_t = {}, {}
    for b in existing_books:
        k = (norm_bn(b["author"]), norm_bn(b["title"]))
        book_by_at[k] = b
        book_by_t.setdefault(norm_bn(b["title"]), b)
    seen_ids = set(book_by_id)

    entries = parse_opds(OPDS_URL)
    updated, new_count, skipped, ext_cov, gen_cov = 0, 0, 0, 0, 0
    new_books, meta_dump = [], []

    for i, entry in enumerate(entries):
        raw_title = norm(entry["title"])
        raw_author = norm(entry["author"])
        epub_url = entry["epub_url"]
        img_url = entry["img_url"]
        is_english = entry["is_english"]
        genre_hint = entry["genre_hint"]

        print(f"[{i+1}/{len(entries)}] {raw_author} — {raw_title}", end=" ", flush=True)

        am = find_author_match(raw_author)
        if am:
            clean_author, author_info = am["canonical_bn"], am
        else:
            trans = transliterate_text(raw_author)
            author_info = get_author_info(raw_author, trans[0] if trans else raw_author)
            clean_author = author_info["canonical_bn"]

        clean_title = raw_title
        genres = set(author_info.get("default_genres", ["ক্লাসিক ও সাহিত্য (Classics)"]))
        if genre_hint: genres.add(genre_hint)
        if is_english: genres.add("English Translation")

        a_key, t_key = norm_bn(clean_author), norm_bn(clean_title)
        matched = book_by_at.get((a_key, t_key))
        if not matched:
            cand = book_by_t.get(t_key)
            if cand and norm_bn(cand["author"]) == a_key: matched = cand

        epub_filename = epub_url.split("/")[-1]
        fmt_entry = {
            "filename": epub_filename,
            "relative_path": f"downloads/{clean_author}/{clean_title}/{epub_filename}",
            "size_bytes": 0, "size_formatted": "",
            "download_url": epub_url, "source": SOURCE_TAG,
        }

        if matched:
            if "epub" not in matched["formats"]:
                print("→ updating")
                matched["formats"]["epub"] = fmt_entry
                updated += 1
                if not matched.get("cover"):
                    cov_file = covers_path / f"{matched['id']}.webp"
                    cb = fetch_opds_cover(img_url)
                    if cb and save_cover_webp(cb, cov_file):
                        matched["cover"] = f"assets/covers/{matched['id']}.webp"; ext_cov += 1
                    else:
                        generate_cover_image(matched["title"], matched["author"], cov_file)
                        matched["cover"] = f"assets/covers/{matched['id']}.webp"; gen_cov += 1
            else:
                print("→ dup, skip"); skipped += 1
            meta_dump.append({**entry, "status": "updated" if "epub" in matched["formats"] else "skipped"})
            continue

        # New book — download epub
        print("→ new")
        epub_bytes = b""
        internal_title, internal_date = "", ""
        try:
            epub_bytes = http_get(epub_url, retries=3, timeout=60)
            fmt_entry["size_bytes"] = len(epub_bytes)
            fmt_entry["size_formatted"] = format_size(len(epub_bytes))
            with zipfile.ZipFile(io.BytesIO(epub_bytes)) as z:
                container = z.read("META-INF/container.xml")
                cr = ET.fromstring(container)
                rf = cr.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
                if rf is not None:
                    opf = ET.fromstring(z.read(rf.attrib["full-path"]))
                    te = opf.find(".//{http://purl.org/dc/elements/1.1/}title")
                    de = opf.find(".//{http://purl.org/dc/elements/1.1/}date")
                    ce = opf.find(".//{http://purl.org/dc/elements/1.1/}creator")
                    if te is not None and te.text: internal_title = te.text.strip()
                    if de is not None and de.text: internal_date = de.text.strip()[:4]
                    if ce is not None and ce.text:
                        am2 = find_author_match(ce.text.strip())
                        if am2: clean_author, author_info = am2["canonical_bn"], am2
                    for se in opf.findall(".//{http://purl.org/dc/elements/1.1/}subject"):
                        if se.text: genres.add(se.text.strip())
        except Exception as ex:
            print(f"  [WARN] {ex}")

        if internal_title and len(internal_title) > 1:
            clean_title = norm(internal_title)

        genres_list = sorted(genres)
        title_translit = transliterate_text(clean_title)
        title_en = title_translit[0].title() if title_translit else clean_title
        book_id = slugify(f"{author_info['en']}-{title_en}") or f"eboipotro-{len(new_books)+1}"
        orig_id = book_id; counter = 2
        while book_id in seen_ids:
            book_id = f"{orig_id}-{counter}"; counter += 1
        seen_ids.add(book_id)

        # Cover
        cov_file = covers_path / f"{book_id}.webp"
        got = False
        cb = fetch_opds_cover(img_url)
        if cb and save_cover_webp(cb, cov_file): ext_cov += 1; got = True
        if not got and epub_bytes:
            cb2 = extract_cover_from_epub_bytes(epub_bytes)
            if cb2 and save_cover_webp(cb2, cov_file): ext_cov += 1; got = True
        if not got:
            generate_cover_image(clean_title, clean_author, cov_file); gen_cov += 1

        series = detect_series(clean_title, clean_author)
        search_tokens = {clean_title.lower(), clean_author.lower(), author_info["en"].lower()}
        for a in author_info.get("aliases", []): search_tokens.add(a.lower())
        for t in title_translit[:4]: search_tokens.add(t.lower())
        if series: search_tokens.update([series["name_bn"].lower(), series["name_en"].lower()])
        for g in genres_list: search_tokens.add(g.lower())

        nb = {
            "id": book_id, "title": clean_title, "title_en": title_en,
            "title_translit": title_translit[:4], "author": clean_author,
            "author_en": author_info["en"], "author_aliases": author_info.get("aliases",[]),
            "series": series, "genres": genres_list, "year": internal_date or "",
            "description": entry["summary"], "cover": f"assets/covers/{book_id}.webp",
            "formats": {"epub": fmt_entry}, "search_text": " ".join(search_tokens),
            "source": SOURCE_TAG,
        }
        new_books.append(nb); new_count += 1
        book_by_at[(norm_bn(clean_author), norm_bn(clean_title))] = nb
        book_by_t.setdefault(norm_bn(clean_title), nb)
        meta_dump.append({**entry, "book_id": book_id, "status": "new"})

    if dry_run:
        print(f"\n[DRY RUN] new={new_count} updated={updated} skipped={skipped}")
        return

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

    print(f"\n--- Eboipotro Summary ---")
    print(f"New: {new_count}  Updated: {updated}  Skipped: {skipped}")
    print(f"Covers extracted: {ext_cov}  Generated: {gen_cov}")
    print(f"Total books: {len(all_books)}  Authors: {len(ac)}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", "-c", default="./catalog.json")
    p.add_argument("--covers-dir", default="./assets/covers")
    p.add_argument("--download-dir", default="/tmp/eboipotro")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    ingest_eboipotro(a.catalog, a.covers_dir, a.download_dir, a.dry_run)
