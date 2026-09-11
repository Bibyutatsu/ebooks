"""
Lightning-fast XML resolution of exact filenames, direct download links,
and authentic scanned covers for Internet Archive books in catalog.json.
"""

import sys, os, io, json, time
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def format_bytes(sz):
    if not sz: return "0 B"
    sz = float(sz)
    for u in ["B", "KB", "MB", "GB"]:
        if sz < 1024: return f"{sz:.1f} {u}"
        sz /= 1024
    return f"{sz:.1f} GB"

def process_book(book, covers_dir):
    book_id = book["id"]
    desc = book.get("description", "")
    ident = None
    if "Identifier: " in desc:
        ident = desc.split("Identifier: ")[1].strip()
    if not ident:
        for fmt, info in book.get("formats", {}).items():
            url = info.get("source_page_url", "")
            if "details/" in url:
                ident = url.split("details/")[1].strip()
                break

    if not ident:
        return {"id": book_id, "status": "no_ident"}

    ua = {"User-Agent": "BibyutatsuEbooks/1.0 (+https://bibyutatsu.github.io/ebooks)"}
    xml_url = f"https://archive.org/download/{ident}/{ident}_files.xml"

    # 1. Fetch _files.xml directly from download cluster
    epubs = []
    pdfs = []
    has_thumb = False
    thumb_name = "__ia_thumb.jpg"

    try:
        r = requests.get(xml_url, headers=ua, timeout=8)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for f in root.findall("file"):
                name = f.attrib.get("name", "")
                fmt = f.findtext("format", "") or ""
                sz = int(f.findtext("size", "0") or 0)
                
                if name.endswith("__ia_thumb.jpg") or "Item Tile" in fmt:
                    has_thumb = True
                    thumb_name = name
                
                # Exclude metadata and raw ocr files
                if name.endswith("_files.xml") or name.endswith("_meta.xml") or name.endswith("_chocr.html.gz") or name.endswith("_archive.torrent"):
                    continue
                
                if fmt == "EPUB" or name.lower().endswith(".epub"):
                    epubs.append({"name": name, "size": sz, "format": "epub"})
                elif (fmt in ["Text PDF", "Image Container PDF", "PDF"] or name.lower().endswith(".pdf")) and sz > 50000:
                    pdfs.append({"name": name, "size": sz, "format": "pdf"})
    except Exception as e:
        return {"id": book_id, "status": "fetch_error", "error": str(e)}

    # Prioritize EPUB, then PDF
    chosen = epubs[0] if epubs else (pdfs[0] if pdfs else None)
    if not chosen:
        return {"id": book_id, "status": "no_downloadable_file"}

    fmt_key = chosen["format"]
    file_name = chosen["name"]
    file_size = chosen["size"]
    dl_url = f"https://archive.org/download/{ident}/{quote(file_name)}"
    page_url = f"https://archive.org/details/{ident}"

    # 2. Fetch authentic scanned cover
    cover_updated = False
    cov_path = covers_dir / f"{book_id}.webp"
    try:
        thumb_url = f"https://archive.org/download/{ident}/{quote(thumb_name)}"
        ir = requests.get(thumb_url, headers=ua, timeout=8)
        if ir.status_code != 200:
            # Fallback to service img endpoint
            ir = requests.get(f"https://archive.org/services/img/{ident}", headers=ua, timeout=8)
        
        if ir.status_code == 200 and len(ir.content) > 500:
            img = Image.open(io.BytesIO(ir.content)).convert("RGB")
            # Preserve aspect ratio in 300x450 card
            img.thumbnail((300, 450), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (300, 450), (18, 24, 38))
            x_off = (300 - img.width) // 2
            y_off = (450 - img.height) // 2
            canvas.paste(img, (x_off, y_off))
            canvas.save(cov_path, "WEBP", quality=82)
            cover_updated = True
    except Exception:
        pass

    fmt_entry = {
        "filename": file_name,
        "relative_path": "",
        "size_bytes": file_size,
        "size_formatted": format_bytes(file_size),
        "download_url": dl_url,
        "source_page_url": page_url,
        "source": "archive_org"
    }

    return {
        "id": book_id,
        "status": "ok",
        "fmt_key": fmt_key,
        "fmt_entry": fmt_entry,
        "cover_updated": cover_updated
    }

def main():
    catalog_path = Path("catalog.json")
    covers_dir = Path("assets/covers")
    covers_dir.mkdir(parents=True, exist_ok=True)

    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)

    ia_books = [b for b in catalog["books"] if b.get("source") == "archive_org"]
    print(f"Resolving {len(ia_books)} Internet Archive books via XML cluster...")

    results = {}
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(process_book, b, covers_dir): b["id"] for b in ia_books}
        done_count = 0
        for f in as_completed(futures):
            res = f.result()
            results[res["id"]] = res
            done_count += 1
            if done_count % 50 == 0 or done_count == len(ia_books):
                print(f"Processed {done_count}/{len(ia_books)} items...", flush=True)

    new_books = []
    removed_count = 0
    ok_count = 0
    covers_replaced = 0

    for b in catalog["books"]:
        if b.get("source") != "archive_org":
            new_books.append(b)
            continue

        res = results.get(b["id"])
        if not res or res["status"] != "ok":
            removed_count += 1
            continue

        b["formats"] = {res["fmt_key"]: res["fmt_entry"]}
        if res.get("cover_updated"):
            covers_replaced += 1
            b["cover"] = f"assets/covers/{b['id']}.webp"
        new_books.append(b)
        ok_count += 1

    catalog["books"] = new_books

    format_counts = {}
    for b in new_books:
        for fmt in b.get("formats", {}):
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

    catalog["stats"]["total_books"] = len(new_books)
    catalog["stats"]["formats"] = format_counts

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print("\n--- Internet Archive Resolution Complete ---", flush=True)
    print(f"Valid books kept with verified direct downloads: {ok_count}", flush=True)
    print(f"Real covers fetched & converted: {covers_replaced}", flush=True)
    print(f"Non-downloadable / website redirect items removed: {removed_count}", flush=True)
    print(f"New total catalog size: {len(new_books)} books", flush=True)
    print(f"Formats breakdown: {format_counts}", flush=True)

if __name__ == "__main__":
    main()
