"""
BongBoi Repository Sync & Ingestion Pipeline.
Extracts metadata, canonicalizes authors, extracts embedded or generates
high-fidelity typographic covers, adds missing EPUB formats to existing books,
and creates new entries for classical works.
"""

import os
import sys
import re
import json
import io
import shutil
import zipfile
import hashlib
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add parent tools directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from author_mapping import get_author_info, find_author_match, AUTHORS_DB
from series_mapping import detect_series
from transliteration import transliterate_text
from build_catalog import format_size, slugify

def norm(s: str) -> str:
    return unicodedata.normalize('NFC', s.strip())

def norm_bn(s: str) -> str:
    s = s.replace('\u09af\u09bc', '\u09df')
    s = s.replace('\u09a1\u09bc', '\u09dc')
    s = s.replace('\u09a2\u09bc', '\u09dd')
    return s.strip().lower()

def extract_cover_bytes(epub_path: Path) -> bytes | None:
    try:
        with zipfile.ZipFile(epub_path, "r") as z:
            imgs = [n for n in z.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            good_imgs = []
            for img_name in imgs:
                low = img_name.lower()
                if any(bad in low for bad in ('accueil', 'segment', 'diamond', 'tear')):
                    continue
                info = z.getinfo(img_name)
                if info.file_size > 5000:
                    good_imgs.append((img_name, info.file_size))

            if good_imgs:
                good_imgs.sort(key=lambda x: (1 if any(k in x[0].lower() for k in ('cover', 'page1', 'c6_lossy', 'c10_')) else 0, x[1]), reverse=True)
                chosen = good_imgs[0][0]
                data = z.read(chosen)
                im = Image.open(io.BytesIO(data))
                w, h = im.size
                if w >= 120 and h >= 120:
                    return data
    except Exception:
        pass
    return None

def generate_cover_image(title: str, author: str, out_path: Path, width=300, height=450):
    palettes = [
        ((15, 23, 42), (30, 41, 59), (56, 189, 248)),
        ((19, 24, 39), (31, 41, 55), (251, 146, 60)),
        ((24, 24, 27), (39, 39, 42), (167, 139, 250)),
        ((17, 24, 39), (31, 41, 55), (52, 211, 153)),
        ((30, 27, 75), (49, 46, 129), (244, 114, 182)),
        ((20, 30, 45), (15, 60, 90), (250, 204, 21)),
    ]
    h = int(hashlib.md5(f"{title}{author}".encode('utf-8')).hexdigest()[:6], 16)
    bg1, bg2, accent = palettes[h % len(palettes)]

    img = Image.new('RGB', (width, height), bg1)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        factor = y / height
        r = int(bg1[0] * (1 - factor) + bg2[0] * factor)
        g = int(bg1[1] * (1 - factor) + bg2[1] * factor)
        b = int(bg1[2] * (1 - factor) + bg2[2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.rectangle([14, 14, width - 14, height - 14], outline=(accent[0], accent[1], accent[2]), width=1)
    draw.line([6, 0, 6, height], fill=(255, 255, 255, 40), width=2)

    font_path = '/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc'
    try:
        font_title = ImageFont.truetype(font_path, 22)
        font_author = ImageFont.truetype(font_path, 15)
        font_ornament = ImageFont.truetype(font_path, 13)
    except:
        font_title = font_author = font_ornament = ImageFont.load_default()

    draw.text((width / 2, 70), '✦ ✦ ✦', fill=accent, font=font_ornament, anchor='mm')

    # Word wrapping for title
    words = title.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(' '.join(curr)) > 15:
            lines.append(' '.join(curr[:-1]) if len(curr) > 1 else w)
            curr = [w] if len(curr) > 1 else []
    if curr:
        lines.append(' '.join(curr))
    if not lines:
        lines = [title]

    start_y = height / 2 - (len(lines) * 16)
    for i, line in enumerate(lines):
        draw.text((width / 2, start_y + i * 30), line, fill=(245, 245, 245), font=font_title, anchor='mm')

    draw.text((width / 2, height - 70), author, fill=accent, font=font_author, anchor='mm')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, 'WEBP', quality=82)

def save_cover_webp(cover_bytes: bytes, out_path: Path, max_w=300, max_h=450):
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(io.BytesIO(cover_bytes))
        im = im.convert('RGB')
        im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        im.save(out_path, 'WEBP', quality=78)
        return True
    except Exception as e:
        return False

def ingest_bongboi(bongboi_dir: str, catalog_path: str, covers_dir: str):
    bongboi_path = Path(bongboi_dir)
    catalog_file = Path(catalog_path)
    covers_path = Path(covers_dir)
    covers_path.mkdir(parents=True, exist_ok=True)

    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    existing_books = catalog["books"]
    
    # Map existing books by ID and by normalized (author, title)
    book_by_id = {b["id"]: b for b in existing_books}
    book_by_author_title = {}
    book_by_title = {}

    for b in existing_books:
        a_norm = norm_bn(b["author"])
        t_norm = norm_bn(b["title"])
        book_by_author_title[(a_norm, t_norm)] = b
        if t_norm not in book_by_title:
            book_by_title[t_norm] = b

    seen_ids = set(book_by_id.keys())

    # Get all EPUB files from bongboi
    epub_files = sorted([p for p in bongboi_path.glob('**/*.epub') if p.is_file()])
    print(f"Total EPUB files found in BongBoi: {len(epub_files)}")

    updated_existing_count = 0
    new_books_count = 0
    extracted_covers = 0
    generated_covers = 0

    new_books_list = []

    for ep in epub_files:
        parent_author = ep.parent.name if ep.parent != bongboi_path else ''
        filename = ep.stem
        match = re.match(r'^(.*?)\s*[-–—]\s*(.*?)(?:\s*\(([০-৯0-9]+)\))?$', filename)
        if match:
            fn_author, fn_title, fn_year = match.group(1).strip(), match.group(2).strip(), match.group(3)
        else:
            fn_author = parent_author
            fn_title = filename
            fn_year = None

        raw_author = fn_author or parent_author or 'Unknown'
        raw_title = re.sub(r'[\s—-]+প্রচ্ছদ$', '', fn_title).strip()
        
        # Read internal metadata if available
        meta_title = ""
        meta_creator = ""
        meta_date = ""
        meta_subjects = []
        try:
            with zipfile.ZipFile(ep) as z:
                container = z.read("META-INF/container.xml")
                root = ET.fromstring(container)
                rootfile = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
                if rootfile is not None:
                    opf_data = z.read(rootfile.attrib["full-path"])
                    opf = ET.fromstring(opf_data)
                    t = opf.find(".//{http://purl.org/dc/elements/1.1/}title")
                    c = opf.find(".//{http://purl.org/dc/elements/1.1/}creator")
                    d = opf.find(".//{http://purl.org/dc/elements/1.1/}date")
                    if t is not None and t.text: meta_title = t.text.strip()
                    if c is not None and c.text: meta_creator = c.text.strip()
                    if d is not None and d.text: meta_date = d.text.strip()[:4]
                    for s in opf.findall(".//{http://purl.org/dc/elements/1.1/}subject"):
                        if s.text and s.text.strip():
                            meta_subjects.append(s.text.strip())
        except Exception:
            pass

        # Standardize Author
        author_match = find_author_match(raw_author) or (find_author_match(meta_creator) if meta_creator else None)
        if author_match:
            clean_author = author_match["canonical_bn"]
            author_info = author_match
        else:
            trans_cand = transliterate_text(raw_author)
            author_info = get_author_info(raw_author, trans_cand[0] if trans_cand else raw_author)
            clean_author = author_info["canonical_bn"]

        clean_title = raw_title
        file_size = ep.stat().st_size
        rel_path = f"downloads/{clean_author}/{clean_title}/{ep.name}"

        fmt_entry = {
            "filename": ep.name,
            "relative_path": rel_path,
            "size_bytes": file_size,
            "size_formatted": format_size(file_size),
            "download_url": ""  # populated by release sync
        }

        # Check if matching existing book
        a_key = norm_bn(clean_author)
        t_key = norm_bn(clean_title)

        matched_book = book_by_author_title.get((a_key, t_key))
        if not matched_book and t_key in book_by_title:
            cand = book_by_title[t_key]
            # Check if authors match reasonably or if same person
            if norm_bn(cand["author"]) == a_key:
                matched_book = cand

        if matched_book:
            # Check if EPUB format already exists
            if "epub" not in matched_book["formats"]:
                matched_book["formats"]["epub"] = fmt_entry
                updated_existing_count += 1
                # Check cover
                if not matched_book.get("cover"):
                    cover_file = covers_path / f"{matched_book['id']}.webp"
                    c_bytes = extract_cover_bytes(ep)
                    if c_bytes and save_cover_webp(c_bytes, cover_file):
                        matched_book["cover"] = f"assets/covers/{matched_book['id']}.webp"
                        extracted_covers += 1
                    else:
                        generate_cover_image(matched_book["title"], matched_book["author"], cover_file)
                        matched_book["cover"] = f"assets/covers/{matched_book['id']}.webp"
                        generated_covers += 1
                continue
            else:
                # Already has EPUB format; nothing to add
                continue

        # Brand new book entry
        bn_digits = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}
        title_ascii = "".join(bn_digits.get(c, c) for c in clean_title)
        title_translit = transliterate_text(title_ascii)
        title_en_primary = title_translit[0].title() if title_translit else clean_title

        slug_base = f"{author_info['en']}-{title_en_primary}"
        book_id = slugify(slug_base)
        if not book_id:
            book_id = f"bongboi-{len(new_books_list) + 1}"

        orig_id = book_id
        counter = 2
        while book_id in seen_ids:
            book_id = f"{orig_id}-{counter}"
            counter += 1
        seen_ids.add(book_id)

        # Handle Cover
        cover_file = covers_path / f"{book_id}.webp"
        c_bytes = extract_cover_bytes(ep)
        if c_bytes and save_cover_webp(c_bytes, cover_file):
            extracted_covers += 1
        else:
            generate_cover_image(clean_title, clean_author, cover_file)
            generated_covers += 1
        cover_path_str = f"assets/covers/{book_id}.webp"

        # Series & Genres
        series = detect_series(clean_title, clean_author)
        genres = set(author_info.get("default_genres", ["ক্লাসিক ও সাহিত্য (Classics)"]))
        if series:
            if series["id"] in ("feluda", "byomkesh", "kakababu", "tin_goyenda", "sherlock", "kiriti", "shabor"):
                genres.add("থ্রিলার ও গোয়েন্দা (Mystery & Thriller)")
            elif series["id"] == "shonku":
                genres.add("সায়েন্স ফিকশন (Sci-Fi)")
            elif series["id"] in ("himu", "misir_ali", "shuvro"):
                genres.add("উপন্যাস (Novel)")
        for s in meta_subjects:
            genres.add(s)

        genres_list = sorted(list(genres))

        # Search tokens
        search_tokens = set()
        search_tokens.add(clean_title.lower())
        search_tokens.add(clean_author.lower())
        search_tokens.add(author_info["en"].lower())
        for a in author_info.get("aliases", []):
            search_tokens.add(a.lower())
        for t in title_translit[:4]:
            search_tokens.add(t.lower())
        if series:
            search_tokens.add(series["name_bn"].lower())
            search_tokens.add(series["name_en"].lower())
        for g in genres_list:
            search_tokens.add(g.lower())

        pub_year = fn_year or meta_date or ""

        new_book = {
            "id": book_id,
            "title": clean_title,
            "title_en": title_en_primary,
            "title_translit": title_translit[:4],
            "author": clean_author,
            "author_en": author_info["en"],
            "author_aliases": author_info.get("aliases", []),
            "series": series,
            "genres": genres_list,
            "year": pub_year,
            "description": "",
            "cover": cover_path_str,
            "formats": {
                "epub": fmt_entry
            },
            "search_text": " ".join(search_tokens)
        }

        new_books_list.append(new_book)
        new_books_count += 1

    # Merge into catalog
    all_books = existing_books + new_books_list

    # Recalculate stats, top_authors, genres
    author_counts = {}
    genre_counts = {}
    format_counts = {}

    for b in all_books:
        a = b["author"]
        author_counts[a] = author_counts.get(a, 0) + 1
        for g in b["genres"]:
            genre_counts[g] = genre_counts.get(g, 0) + 1
        for f in b["formats"]:
            format_counts[f] = format_counts.get(f, 0) + 1

    catalog["books"] = all_books
    catalog["stats"] = {
        "total_books": len(all_books),
        "total_authors": len(author_counts),
        "formats": format_counts,
        "genres_count": len(genre_counts)
    }
    catalog["top_authors"] = [
        {"author": k, "author_en": get_author_info(k)["en"], "count": v}
        for k, v in sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:30]
    ]
    catalog["genres"] = [
        {"genre": k, "count": v}
        for k, v in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print("\n--- BongBoi Ingestion Summary ---")
    print(f"Updated existing books with EPUB: {updated_existing_count}")
    print(f"Added brand new books: {new_books_count}")
    print(f"Extracted original covers: {extracted_covers}")
    print(f"Generated typographic covers: {generated_covers}")
    print(f"Total books in library: {len(all_books)}")
    print(f"Total authors: {len(author_counts)}")
    print(f"Formats: {format_counts}")
    print(f"Catalog updated at: {catalog_file.resolve()}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest BongBoi repository EPUBs into library catalog")
    parser.add_argument("--input", "-i", default="/tmp/bongboi", help="Path to BongBoi repository directory")
    parser.add_argument("--catalog", "-c", default="./catalog.json", help="Path to catalog.json")
    parser.add_argument("--covers-dir", default="./assets/covers", help="Path to covers directory")
    args = parser.parse_args()

    ingest_bongboi(
        bongboi_dir=args.input,
        catalog_path=args.catalog,
        covers_dir=args.covers_dir
    )
