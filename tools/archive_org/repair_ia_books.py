"""
Repair script for Archive.org items in catalog.json.
Identifies any books with files < 50KB (broken OCR stubs or tiny fragments),
fetches the item's _files.xml, and replaces them with authentic full-text EPUBs
or scanned PDFs. If no valid file > 50KB exists, the item is removed.
"""

import sys, json, time, re, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = ROOT_DIR / "catalog.json"
IA_DOWNLOAD_BASE = "https://archive.org/download"
UA = "BibyutatsuEbooks/1.0 (+https://bibyutatsu.github.io/ebooks)"

def format_bytes(sz):
    if not sz: return "0 B"
    sz = float(sz)
    for u in ["B", "KB", "MB", "GB"]:
        if sz < 1024: return f"{sz:.1f} {u}"
        sz /= 1024
    return f"{sz:.1f} GB"

def http_get(url, retries=3, timeout=15):
    headers = {"User-Agent": UA}
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
            else:
                return b""
    return b""

def repair_ia_books(dry_run=False):
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    books = catalog["books"]
    repaired_count = 0
    removed_count = 0
    books_to_keep = []

    print(f"Scanning {len(books)} books in catalog...")

    for b in books:
        if b.get("source") != "archive_org":
            books_to_keep.append(b)
            continue

        formats = b.get("formats", {})
        is_small = any(finfo.get("size_bytes", 0) < 50000 for finfo in formats.values())
        if not is_small:
            books_to_keep.append(b)
            continue

        # Extract identifier
        first_fmt = list(formats.keys())[0]
        dl_url = formats[first_fmt].get("download_url", "")
        m = re.search(r"archive\.org/download/([^/]+)/", dl_url)
        if not m:
            print(f"[WARN] Cannot parse identifier from {dl_url}")
            books_to_keep.append(b)
            continue

        identifier = m.group(1)
        xml_url = f"{IA_DOWNLOAD_BASE}/{identifier}/{identifier}_files.xml"
        raw_xml = http_get(xml_url)
        if not raw_xml:
            print(f"[WARN] Could not fetch XML for {identifier}")
            # If completely unresolvable and < 15KB, remove
            if any(finfo.get("size_bytes", 0) < 15000 for finfo in formats.values()):
                print(f"  -> Pruning broken unresolvable item: {b['id']}")
                removed_count += 1
                continue
            books_to_keep.append(b)
            continue

        epubs, pdfs = [], []
        try:
            root = ET.fromstring(raw_xml)
            for f_elem in root.findall("file"):
                name = f_elem.attrib.get("name", "")
                fmt = f_elem.findtext("format", "") or ""
                sz = int(f_elem.findtext("size", "0") or 0)
                if name.endswith("_files.xml") or name.endswith("_meta.xml") or name.endswith("_chocr.html.gz") or name.endswith("_archive.torrent"):
                    continue
                if (fmt == "EPUB" or name.lower().endswith(".epub")) and sz > 50000:
                    epubs.append({"name": name, "size": sz, "format": "epub"})
                elif (fmt in ["Text PDF", "Image Container PDF", "PDF"] or name.lower().endswith(".pdf")) and sz > 50000:
                    pdfs.append({"name": name, "size": sz, "format": "pdf"})
        except Exception as e:
            print(f"[ERROR] Parsing XML for {identifier}: {e}")
            books_to_keep.append(b)
            continue

        chosen = epubs[0] if epubs else (pdfs[0] if pdfs else None)
        if chosen:
            new_fmt = chosen["format"]
            new_filename = chosen["name"].split("/")[-1]
            new_dl_url = f"{IA_DOWNLOAD_BASE}/{identifier}/{quote(chosen['name'])}"
            old_fmt = first_fmt
            old_size = formats[first_fmt].get("size_bytes", 0)
            
            b["formats"] = {
                new_fmt: {
                    "filename": new_filename,
                    "relative_path": "",
                    "size_bytes": chosen["size"],
                    "size_formatted": format_bytes(chosen["size"]),
                    "download_url": new_dl_url,
                    "source": "archive_org",
                }
            }
            print(f"[REPAIRED] {b['id']} ({b['title']}): {old_fmt} ({format_bytes(old_size)}) -> {new_fmt} ({format_bytes(chosen['size'])})")
            repaired_count += 1
            books_to_keep.append(b)
        else:
            print(f"[PRUNED] {b['id']} ({b['title']}) - no alternate file > 50KB found on IA.")
            removed_count += 1

    print(f"\nSummary:")
    print(f"  Repaired: {repaired_count}")
    print(f"  Pruned (no valid files): {removed_count}")
    print(f"  Total kept: {len(books_to_keep)}")

    if not dry_run and (repaired_count > 0 or removed_count > 0):
        catalog["books"] = books_to_keep
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print("Updated catalog.json successfully.")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    repair_ia_books(dry_run=dry_run)
