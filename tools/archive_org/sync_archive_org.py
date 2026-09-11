"""
Internet Archive Bengali Ebook Ingestion Pipeline.

Queries the Internet Archive for public domain Bengali texts and creates
catalog entries with verified direct file download links and authentic scanned covers.

Usage:
    # Ingest next batch of items into catalog:
    python3 tools/archive_org/sync_archive_org.py --catalog ./catalog.json --limit 1000
"""

import sys, re, io, json, time, unicodedata
from pathlib import Path
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))

from author_mapping import get_author_info, find_author_match
from series_mapping import detect_series
from transliteration import transliterate_text
from build_catalog import slugify

SOURCE_TAG = "archive_org"
IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_DOWNLOAD_BASE = "https://archive.org/download"
IA_DETAILS_BASE = "https://archive.org/details"
UA = "BibyutatsuEbooks/1.0 (+https://bibyutatsu.github.io/ebooks)"

def norm(s): return unicodedata.normalize("NFC", s.strip()) if s else ""
def norm_bn(s):
    s = s.replace("\u09af\u09bc", "\u09df").replace("\u09a1\u09bc", "\u09dc").replace("\u09a2\u09bc", "\u09dd")
    return s.strip().lower()

def format_bytes(sz):
    if not sz: return "0 B"
    sz = float(sz)
    for u in ["B", "KB", "MB", "GB"]:
        if sz < 1024: return f"{sz:.1f} {u}"
        sz /= 1024
    return f"{sz:.1f} GB"

def http_get(url, retries=3, timeout=30):
    ua = {"User-Agent": UA}
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=ua, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    return b""

def fetch_ia_files_and_thumb(identifier):
    """Fetches exact downloadable files and thumb from IA _files.xml directly."""
    xml_url = f"{IA_DOWNLOAD_BASE}/{identifier}/{identifier}_files.xml"
    epubs, pdfs = [], []
    thumb_name = "__ia_thumb.jpg"
    try:
        raw = http_get(xml_url, timeout=10)
        if raw:
            root = ET.fromstring(raw)
            for f in root.findall("file"):
                name = f.attrib.get("name", "")
                fmt = f.findtext("format", "") or ""
                sz = int(f.findtext("size", "0") or 0)
                if name.endswith("__ia_thumb.jpg") or "Item Tile" in fmt:
                    thumb_name = name
                if name.endswith("_files.xml") or name.endswith("_meta.xml") or name.endswith("_chocr.html.gz") or name.endswith("_archive.torrent"):
                    continue
                if fmt == "EPUB" or name.lower().endswith(".epub"):
                    epubs.append({"name": name, "size": sz, "format": "epub"})
                elif (fmt in ["Text PDF", "Image Container PDF", "PDF"] or name.lower().endswith(".pdf")) and sz > 50000:
                    pdfs.append({"name": name, "size": sz, "format": "pdf"})
    except Exception:
        pass

    chosen = epubs[0] if epubs else (pdfs[0] if pdfs else None)
    return chosen, thumb_name

def save_authentic_cover(identifier, thumb_name, out_path):
    """Fetches genuine scanned cover and saves as optimized WebP."""
    try:
        thumb_url = f"{IA_DOWNLOAD_BASE}/{identifier}/{quote(thumb_name)}"
        raw = http_get(thumb_url, timeout=10)
        if not raw:
            raw = http_get(f"https://archive.org/services/img/{identifier}", timeout=10)
        if raw and len(raw) > 500:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail((300, 450), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (300, 450), (18, 24, 38))
            x_off = (300 - img.width) // 2
            y_off = (450 - img.height) // 2
            canvas.paste(img, (x_off, y_off))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(out_path, "WEBP", quality=82)
            return True
    except Exception:
        pass
    return False

def query_archive_org(limit=1000):
    """Searches IA for Bengali texts sorted by downloads."""
    q = "collection:booksbylanguage_bengali AND mediatype:texts AND NOT access-restricted-item:true"
    params = {
        "q": q,
        "fl[]": ["identifier", "title", "creator", "date", "subject", "format"],
        "sort[]": "downloads desc",
        "output": "json",
        "rows": "100",
        "page": 1,
    }

    all_items = []
    page = 1
    while len(all_items) < limit:
        params["page"] = page
        url = IA_SEARCH_URL + "?" + urlencode(params, doseq=True)
        try:
            raw = http_get(url, timeout=30)
            data = json.loads(raw)
        except Exception as e:
            print(f"[WARN] IA search error: {e}")
            break

        docs = data.get("response", {}).get("docs", [])
        if not docs:
            break
        all_items.extend(docs)
        page += 1
        time.sleep(0.5)

    return all_items[:limit]

def process_ia_doc(doc, covers_dir, seen_ids):
    ident = doc.get("identifier")
    if not ident:
        return None

    raw_title = norm(doc.get("title", ""))
    if not raw_title:
        return None

    # Resolve direct downloadable file
    chosen_file, thumb_name = fetch_ia_files_and_thumb(ident)
    if not chosen_file:
        return None

    # Parse creator/author
    creator = doc.get("creator", "")
    if isinstance(creator, list):
        creator = creator[0] if creator else ""
    creator = norm(creator)

    author_match = find_author_match(creator) if creator else None
    if author_match:
        clean_author = author_match["canonical_bn"]
        author_en = author_match["en"]
        author_aliases = author_match.get("aliases", [author_en])
        default_genres = author_match.get("default_genres", ["ক্লাসিক ও সাহিত্য (Classics)"])
    elif creator:
        # Fallback to normalized creator
        info = get_author_info(creator, creator)
        clean_author = info["canonical_bn"]
        author_en = info["en"]
        author_aliases = info.get("aliases", [author_en])
        default_genres = info.get("default_genres", ["ক্লাসিক ও সাহিত্য (Classics)"])
    else:
        clean_author = "অজ্ঞাত"
        author_en = "Anonymous"
        author_aliases = ["Anonymous", "Unknown Author", "Unknown"]
        default_genres = ["ক্লাসিক ও সাহিত্য (Classics)"]

    # Slugify ID
    title_translit = transliterate_text(raw_title)
    title_en = title_translit[0].title() if title_translit else raw_title
    base_id = slugify(f"{author_en}-{title_en}") or f"ia-{ident}"
    book_id = base_id
    counter = 2
    while book_id in seen_ids:
        book_id = f"{base_id}-{counter}"
        counter += 1
    seen_ids.add(book_id)

    # Save real scanned cover
    cov_path = covers_dir / f"{book_id}.webp"
    has_cover = save_authentic_cover(ident, thumb_name, cov_path)
    if not has_cover:
        # Generate canvas placeholder if IA thumbnail unavailable
        try:
            canvas = Image.new("RGB", (300, 450), (18, 24, 38))
            cov_path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(cov_path, "WEBP", quality=82)
            has_cover = True
        except Exception:
            pass

    file_name = chosen_file["name"]
    file_size = chosen_file["size"]
    fmt_key = chosen_file["format"]
    dl_url = f"{IA_DOWNLOAD_BASE}/{ident}/{quote(file_name)}"
    page_url = f"{IA_DETAILS_BASE}/{ident}"

    fmt_entry = {
        "filename": file_name,
        "relative_path": "",
        "size_bytes": file_size,
        "size_formatted": format_bytes(file_size),
        "download_url": dl_url,
        "source_page_url": page_url,
        "source": SOURCE_TAG
    }

    genres = set(default_genres)
    genres.add("ইন্টারনেট আর্কাইভ (Internet Archive)")
    genres_list = sorted(genres)

    series = detect_series(raw_title, clean_author)
    search_tokens = {raw_title.lower(), clean_author.lower(), author_en.lower()}
    for a in author_aliases:
        search_tokens.add(a.lower())
    for t in title_translit[:4]:
        search_tokens.add(t.lower())
    if series:
        search_tokens.update([series["name_bn"].lower(), series["name_en"].lower()])
    search_tokens.update(["archive.org", "internet archive", "ইন্টারনেট আর্কাইভ"])

    return {
        "id": book_id,
        "title": raw_title,
        "title_en": title_en,
        "title_translit": title_translit[:4],
        "author": clean_author,
        "author_en": author_en,
        "author_aliases": author_aliases,
        "series": series,
        "genres": genres_list,
        "year": str(doc.get("date", "")).strip()[:4],
        "description": f"ইন্টারনেট আর্কাইভ থেকে সংগৃহীত। Identifier: {ident}",
        "cover": f"assets/covers/{book_id}.webp",
        "formats": {fmt_key: fmt_entry},
        "search_text": " ".join(search_tokens),
        "source": SOURCE_TAG,
        "ia_ident": ident
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="./catalog.json")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    covers_dir = ROOT_DIR / "assets" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading catalog from {catalog_path}...")
    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)

    # Collect existing identifiers and IDs
    existing_ia_idents = set()
    seen_ids = set()
    for b in catalog["books"]:
        seen_ids.add(b["id"])
        desc = b.get("description", "")
        if "Identifier: " in desc:
            existing_ia_idents.add(desc.split("Identifier: ")[1].strip())
        for fmt, info in b.get("formats", {}).items():
            u = info.get("source_page_url", "")
            if "details/" in u:
                existing_ia_idents.add(u.split("details/")[1].strip())

    print(f"Catalog currently has {len(catalog['books'])} books ({len(existing_ia_idents)} IA identifiers).")
    print(f"Querying Internet Archive for {args.limit} candidates...")

    docs = query_archive_org(limit=args.limit)
    new_docs = [d for d in docs if d.get("identifier") not in existing_ia_idents]
    print(f"Fetched {len(docs)} total docs from IA; {len(new_docs)} are new candidates to inspect.")

    new_books = []
    skipped_count = 0
    done_count = 0

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(process_ia_doc, doc, covers_dir, seen_ids): doc.get("identifier") for doc in new_docs}
        for f in as_completed(futures):
            res = f.result()
            done_count += 1
            if res:
                new_books.append(res)
            else:
                skipped_count += 1
            if done_count % 50 == 0 or done_count == len(new_docs):
                print(f"Processed {done_count}/{len(new_docs)} IA candidates (Valid new: {len(new_books)}, Skipped: {skipped_count})...", flush=True)

    if new_books:
        # Strip internal tracking field before saving
        for b in new_books:
            b.pop("ia_ident", None)
            catalog["books"].append(b)

        # Recompute catalog statistics
        author_counts = {}
        format_counts = {}
        genre_counts = {}
        for b in catalog["books"]:
            author_counts[b["author"]] = author_counts.get(b["author"], 0) + 1
            for fmt in b.get("formats", {}):
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            for g in b.get("genres", []):
                genre_counts[g] = genre_counts.get(g, 0) + 1

        catalog["stats"] = {
            "total_books": len(catalog["books"]),
            "total_authors": len(author_counts),
            "formats": format_counts,
            "genres_count": len(genre_counts)
        }

        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)

    print("\n--- Internet Archive Ingestion Summary ---")
    print(f"New verified books ingested: {len(new_books)}")
    print(f"Candidates skipped (no downloadable binary): {skipped_count}")
    print(f"New catalog total books: {len(catalog['books'])}")
    print(f"New catalog total authors: {catalog['stats']['total_authors']}")
    print(f"New format breakdown: {catalog['stats']['formats']}")

if __name__ == "__main__":
    main()
