"""
Scalable Catalog Builder & Asset Optimizer.
Scans downloaded books, normalizes metadata, generates multi-format indices,
transliterates titles/authors for English searchability, converts covers to WebP,
and generates catalog.json.
"""

import os
import re
import json
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

import sys
sys.path.insert(0, os.path.dirname(__file__))

from author_mapping import get_author_info, find_author_match
from series_mapping import detect_series
from transliteration import transliterate_text, transliterate_word


def format_size(size_bytes: int) -> str:
    """Formats bytes into human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def slugify(text: str) -> str:
    """Creates a URL-safe lowercase ASCII slug."""
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')


def parse_opf(opf_path: str) -> dict:
    """Extracts Dublin Core metadata from a Calibre OPF file."""
    meta = {
        "title": "",
        "creator": "",
        "description": "",
        "date": "",
        "publisher": "",
        "calibre_id": "",
        "subjects": []
    }
    if not os.path.exists(opf_path):
        return meta

    try:
        tree = ET.parse(opf_path)
        root = tree.getroot()

        dc_title = root.find('.//{http://purl.org/dc/elements/1.1/}title')
        if dc_title is not None and dc_title.text:
            meta["title"] = dc_title.text.strip()

        dc_creator = root.find('.//{http://purl.org/dc/elements/1.1/}creator')
        if dc_creator is not None and dc_creator.text:
            meta["creator"] = dc_creator.text.strip()

        dc_desc = root.find('.//{http://purl.org/dc/elements/1.1/}description')
        if dc_desc is not None and dc_desc.text:
            # Strip HTML tags
            clean_desc = re.sub(r'<[^>]+>', ' ', dc_desc.text).strip()
            meta["description"] = clean_desc

        dc_date = root.find('.//{http://purl.org/dc/elements/1.1/}date')
        if dc_date is not None and dc_date.text:
            meta["date"] = dc_date.text[:4]

        dc_pub = root.find('.//{http://purl.org/dc/elements/1.1/}publisher')
        if dc_pub is not None and dc_pub.text:
            meta["publisher"] = dc_pub.text.strip()

        for s in root.findall('.//{http://purl.org/dc/elements/1.1/}subject'):
            if s.text and s.text.strip() not in ('Kindle Bangla', 'Ronys Kindle', ''):
                meta["subjects"].append(s.text.strip())
    except Exception:
        pass
    return meta


def get_epub_metadata(epub_path: str) -> dict:
    """Extracts title and creator from internal EPUB container."""
    meta = {"title": "", "creator": ""}
    if not os.path.exists(epub_path):
        return meta
    try:
        import zipfile
        with zipfile.ZipFile(epub_path, "r") as z:
            container = z.read("META-INF/container.xml")
            root = ET.fromstring(container)
            rootfile = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
            if rootfile is not None and "full-path" in rootfile.attrib:
                opf_path = rootfile.attrib["full-path"]
                opf_content = z.read(opf_path)
                opf_root = ET.fromstring(opf_content)
                t = opf_root.find(".//{http://purl.org/dc/elements/1.1/}title")
                c = opf_root.find(".//{http://purl.org/dc/elements/1.1/}creator")
                if t is not None and t.text:
                    meta["title"] = t.text.strip()
                if c is not None and c.text:
                    meta["creator"] = c.text.strip()
    except Exception:
        pass
    return meta


def resolve_book_metadata(
    book_folder: Path,
    files: list[str],
    suggested_author: str | None,
    suggested_title: str | None,
    opf_info: dict,
    epub_info: dict
) -> tuple[dict, str]:
    """
    Determines author information (standardized or unstandardized) and clean title.
    Handles 2-level author folders, 1-level direct book folders, Title - Author,
    Author - Title, and simple Title formats.
    """
    if suggested_author:
        # Standard 2-level directory: downloads/<Author>/<Title>/
        author_dir_name = suggested_author
        author_translit_variants = transliterate_text(author_dir_name)
        author_fallback_en = author_translit_variants[0] if author_translit_variants else author_dir_name
        author_info = get_author_info(author_dir_name, author_fallback_en)
        clean_title = suggested_title.strip() if suggested_title else book_folder.name.strip()
        return author_info, clean_title

    # Single-level direct book directory: downloads/<BookFolder>/
    meta_title = (opf_info.get("title") or epub_info.get("title") or "").strip()
    meta_creator = (opf_info.get("creator") or epub_info.get("creator") or "").strip()
    if meta_creator.lower() in ("unknown", "kindlebangla", "ronys kindle", "none", ""):
        meta_creator = ""

    # Find format files in folder
    format_files = [f for f in files if Path(f).suffix.lower() in ('.epub', '.kfx', '.mobi', '.pdf', '.docx', '.txt', '.azw3')]
    primary_stem = Path(format_files[0]).stem if format_files else book_folder.name
    primary_stem = re.sub(r'\[.*?\]|\(.*?\)', '', primary_stem).strip()

    candidate_author = None
    clean_title = None

    # Check for separator in filename
    delim = None
    for d in (' - ', ' – ', ' — ', '_-_'):
        if d in primary_stem:
            delim = d
            break

    if delim:
        parts = [p.strip() for p in primary_stem.split(delim, 1)]
        part_a, part_b = parts[0], parts[1]
        match_a = find_author_match(part_a)
        match_b = find_author_match(part_b)

        if match_a and not match_b:
            author_info = match_a
            clean_title = meta_title or part_b
            return author_info, clean_title
        elif match_b and not match_a:
            author_info = match_b
            clean_title = meta_title or part_a
            return author_info, clean_title
        elif match_a and match_b:
            if meta_title and (part_a in meta_title or meta_title in part_a):
                return match_b, part_a
            return match_a, part_b
        else:
            if meta_creator and (meta_creator.lower() in part_a.lower() or part_a.lower() in meta_creator.lower()):
                candidate_author = part_a
                clean_title = meta_title or part_b
            elif meta_creator and (meta_creator.lower() in part_b.lower() or part_b.lower() in meta_creator.lower()):
                candidate_author = part_b
                clean_title = meta_title or part_a
            elif book_folder.name.strip() == part_a:
                clean_title = part_a
                candidate_author = part_b
            elif book_folder.name.strip() == part_b:
                clean_title = part_b
                candidate_author = part_a
            else:
                clean_title = meta_title or part_a
                candidate_author = part_b
    else:
        clean_title = meta_title or primary_stem or book_folder.name.strip()
        if meta_creator:
            candidate_author = meta_creator
        else:
            folder_match = find_author_match(book_folder.name)
            if folder_match:
                return folder_match, clean_title
            stem_match = find_author_match(primary_stem)
            if stem_match:
                return stem_match, clean_title
            candidate_author = "Unknown"

    if candidate_author:
        matched = find_author_match(candidate_author)
        if matched:
            return matched, clean_title

    # Check if folder name itself is in AUTHORS_DB
    folder_match = find_author_match(book_folder.name)
    if folder_match:
        return folder_match, clean_title

    # Unstandardized author fallback
    author_cand_str = candidate_author or "Unknown"
    translit_cand = transliterate_text(author_cand_str)
    fallback_en = translit_cand[0] if translit_cand else author_cand_str
    author_info = get_author_info(author_cand_str, fallback_en)
    return author_info, clean_title


def optimize_cover(src_img: str, dest_webp: str, max_width=300, max_height=450):
    """Resizes and converts cover (JPG, PNG, WEBP) to compressed WebP."""
    if not os.path.exists(src_img):
        return False

    if os.path.exists(dest_webp) and os.path.getsize(dest_webp) > 0:
        return True

    try:
        os.makedirs(os.path.dirname(dest_webp), exist_ok=True)
        with Image.open(src_img) as img:
            img = img.convert('RGB')
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            img.save(dest_webp, 'WEBP', quality=78, method=6)
        return True
    except Exception as e:
        print(f"Failed to optimize cover {src_img}: {e}")
        return False


def build_catalog(downloads_dir: str, output_dir: str, skip_images: bool = False):
    """
    Main catalog building pipeline.
    """
    downloads_path = Path(downloads_dir)
    output_path = Path(output_dir)
    covers_dir = output_path / "assets" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning downloads directory: {downloads_path.resolve()}...")
    books = []
    author_counts = {}
    genre_counts = {}
    format_counts = {}

    # Load existing catalog.json if present to preserve exact book_ids and download_urls
    existing_books_by_path = {}
    catalog_file = output_path / "catalog.json"
    if catalog_file.exists():
        try:
            with open(catalog_file, "r", encoding="utf-8") as f:
                old_cat = json.load(f)
                for b in old_cat.get("books", []):
                    bid = b.get("id")
                    for f_key, f_info in b.get("formats", {}).items():
                        rp = f_info.get("relative_path")
                        if rp:
                            existing_books_by_path[rp] = {
                                "id": bid,
                                "title_en": b.get("title_en"),
                                "title_translit": b.get("title_translit"),
                                "download_url": f_info.get("download_url", "")
                            }
            print(f"Loaded {len(existing_books_by_path)} existing format paths from catalog.json.")
        except Exception as e:
            print(f"Warning: could not read existing catalog.json: {e}")

    # Collect all book items to process
    # Each item is (book_folder, suggested_author, suggested_title)
    book_items = []
    for entry_name in sorted(os.listdir(downloads_path)):
        if entry_name.startswith('.'):
            continue
        entry_path = downloads_path / entry_name
        if not entry_path.is_dir():
            continue

        subdirs = sorted([d for d in os.listdir(entry_path) if (entry_path / d).is_dir() and not d.startswith('.')])
        if subdirs:
            # Traditional Author directory containing book subdirectories
            for sub_d in subdirs:
                book_items.append((entry_path / sub_d, entry_name, sub_d))
        else:
            # Check if this directory directly contains ebook format files
            files = [f for f in os.listdir(entry_path) if not f.startswith('.')]
            has_formats = any(Path(f).suffix.lower() in ('.epub', '.kfx', '.mobi', '.pdf', '.docx', '.txt', '.azw3') for f in files)
            if has_formats:
                book_items.append((entry_path, None, entry_name))

    print(f"Identified {len(book_items)} total book directories to process.")

    book_idx = 0
    seen_book_ids = set()

    for book_folder, suggested_author, suggested_title in book_items:
        files = [f for f in os.listdir(book_folder) if not f.startswith('.')]

        # Collect formats
        formats = {}
        cover_src = None
        opf_src = None
        epub_src = None

        for f in files:
            ext = Path(f).suffix.lower()
            full_path = book_folder / f
            if ext in ('.epub', '.kfx', '.mobi', '.pdf', '.docx', '.txt', '.azw3'):
                fmt_key = ext.lstrip('.')
                file_size = os.path.getsize(full_path)
                formats[fmt_key] = {
                    "filename": f,
                    "relative_path": str(full_path.relative_to(downloads_path.parent)),
                    "size_bytes": file_size,
                    "size_formatted": format_size(file_size),
                    "download_url": ""  # populated from existing_books_by_path or synced with GitHub releases
                }
                format_counts[fmt_key] = format_counts.get(fmt_key, 0) + 1
                if ext == '.epub' and not epub_src:
                    epub_src = str(full_path)
            elif ext in ('.jpg', '.jpeg', '.png', '.webp') and ('cover' in f.lower() or not cover_src):
                cover_src = str(full_path)
            elif ext == '.opf':
                opf_src = str(full_path)

        if not formats:
            continue

        book_idx += 1

        # Check if any format file already exists in catalog.json
        existing_match = None
        for fmt_key, fmt_info in formats.items():
            rp = fmt_info.get("relative_path")
            if rp in existing_books_by_path:
                existing_match = existing_books_by_path[rp]
                break

        # OPF and EPUB metadata
        opf_info = parse_opf(opf_src) if opf_src else {}
        epub_info = get_epub_metadata(epub_src) if (epub_src and not opf_info.get("title")) else {}

        # Resolve author and title
        author_info, clean_title = resolve_book_metadata(
            book_folder,
            files,
            suggested_author,
            suggested_title,
            opf_info,
            epub_info
        )
        clean_author = author_info.get("canonical_bn", "Unknown")

        if existing_match and existing_match.get("id"):
            book_id = existing_match["id"]
            title_en_primary = existing_match.get("title_en") or clean_title
            title_translit = existing_match.get("title_translit") or transliterate_text(clean_title)
        else:
            # Bengali digits to ascii for slug preservation
            bn_digits = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}
            title_ascii_digits = "".join(bn_digits.get(c, c) for c in clean_title)

            # Title transliteration
            title_translit = transliterate_text(title_ascii_digits)
            title_en_primary = title_translit[0].title() if title_translit else clean_title

            # Book ID
            slug_base = f"{author_info['en']}-{title_en_primary}"
            book_id = slugify(slug_base)
            if not book_id:
                book_id = f"book-{book_idx}"

            # Guarantee uniqueness of book_id
            orig_book_id = book_id
            counter = 2
            while book_id in seen_book_ids:
                book_id = f"{orig_book_id}-{counter}"
                counter += 1

        seen_book_ids.add(book_id)

        # Preserve existing release download URLs if previously synced
        for fmt_key, fmt_info in formats.items():
            rp = fmt_info.get("relative_path")
            if rp in existing_books_by_path and existing_books_by_path[rp].get("download_url"):
                fmt_info["download_url"] = existing_books_by_path[rp]["download_url"]

        # Cover generation
        cover_dest = covers_dir / f"{book_id}.webp"
        has_cover = False
        if not skip_images and cover_src:
            has_cover = optimize_cover(cover_src, str(cover_dest))
        elif cover_dest.exists() and os.path.getsize(cover_dest) > 0:
            has_cover = True

        cover_web_path = f"assets/covers/{book_id}.webp" if has_cover else ""

        # Series detection
        series = detect_series(clean_title, clean_author)

        # Genre determination
        genres = set(author_info.get("default_genres", ["উপন্যাস ও সাহিত্য (General Fiction)"]))
        if series:
            if series["id"] in ("feluda", "byomkesh", "kakababu", "tin_goyenda", "sherlock", "kiriti", "shabor"):
                genres.add("থ্রিলার ও গোয়েন্দা (Mystery & Thriller)")
            elif series["id"] == "shonku":
                genres.add("সায়েন্স ফিকশন (Sci-Fi)")
            elif series["id"] in ("himu", "misir_ali", "shuvro"):
                genres.add("উপন্যাস (Novel)")
            elif series["id"] == "tintin":
                genres.add("কমিকস ও কিশোর সাহিত্য (Comics & Graphic)")

        if opf_info.get("subjects"):
            for s in opf_info["subjects"]:
                genres.add(s)

        genres_list = sorted(list(genres))

        # Build search tokens
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

        book_record = {
            "id": book_id,
            "title": clean_title,
            "title_en": title_en_primary,
            "title_translit": title_translit[:4],
            "author": clean_author,
            "author_en": author_info["en"],
            "author_aliases": author_info.get("aliases", []),
            "series": series,
            "genres": genres_list,
            "year": opf_info.get("date", ""),
            "description": opf_info.get("description", ""),
            "cover": cover_web_path,
            "formats": formats,
            "search_text": " ".join(search_tokens)
        }

        books.append(book_record)
        author_counts[clean_author] = author_counts.get(clean_author, 0) + 1
        for g in genres_list:
            genre_counts[g] = genre_counts.get(g, 0) + 1

    catalog = {
        "version": "1.0.0",
        "generated_at": "2026-09-11",
        "stats": {
            "total_books": len(books),
            "total_authors": len(author_counts),
            "formats": format_counts,
            "genres_count": len(genre_counts)
        },
        "top_authors": [{"author": k, "author_en": get_author_info(k)["en"], "count": v} for k, v in sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:30]],
        "genres": [{"genre": k, "count": v} for k, v in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)],
        "books": books
    }

    catalog_file = output_path / "catalog.json"
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\nCatalog build completed successfully!")
    print(f"Total Books: {len(books)}")
    print(f"Total Authors: {len(author_counts)}")
    print(f"Formats Available: {format_counts}")
    print(f"Catalog saved to: {catalog_file.resolve()}")
    return catalog


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build catalog from downloaded ebooks")
    parser.add_argument("--downloads", default="./downloads", help="Path to downloads folder")
    parser.add_argument("--output", default="./ebooks", help="Path to output website folder")
    parser.add_argument("--skip-images", action="store_true", help="Skip webp image generation")
    args = parser.parse_args()

    build_catalog(args.downloads, args.output, args.skip_images)
