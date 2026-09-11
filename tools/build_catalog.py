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

from author_mapping import get_author_info
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


def optimize_cover(src_jpg: str, dest_webp: str, max_width=300, max_height=450):
    """Resizes and converts cover to compressed WebP."""
    if not os.path.exists(src_jpg):
        return False

    if os.path.exists(dest_webp) and os.path.getsize(dest_webp) > 0:
        return True

    try:
        os.makedirs(os.path.dirname(dest_webp), exist_ok=True)
        with Image.open(src_jpg) as img:
            img = img.convert('RGB')
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            img.save(dest_webp, 'WEBP', quality=78, method=6)
        return True
    except Exception as e:
        print(f"Failed to optimize cover {src_jpg}: {e}")
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

    # Read existing metadata if available
    metadata_file = downloads_path.parent / "books_metadata.json"
    legacy_meta = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                legacy_meta = json.load(f)
        except Exception:
            pass

    author_dirs = sorted([d for d in os.listdir(downloads_path) if (downloads_path / d).is_dir() and not d.startswith('.')])
    print(f"Found {len(author_dirs)} author directories.")

    book_idx = 0
    seen_book_ids = set()
    for author_dir_name in author_dirs:
        author_folder = downloads_path / author_dir_name
        title_dirs = sorted([d for d in os.listdir(author_folder) if (author_folder / d).is_dir() and not d.startswith('.')])

        # Author info
        author_translit_variants = transliterate_text(author_dir_name)
        author_fallback_en = author_translit_variants[0] if author_translit_variants else author_dir_name
        author_info = get_author_info(author_dir_name, author_fallback_en)

        for title_dir_name in title_dirs:
            book_folder = author_folder / title_dir_name
            files = [f for f in os.listdir(book_folder) if not f.startswith('.')]

            # Collect formats
            formats = {}
            cover_src = None
            opf_src = None

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
                        "download_url": ""  # populated when synced with GitHub releases
                    }
                    format_counts[fmt_key] = format_counts.get(fmt_key, 0) + 1
                elif ext in ('.jpg', '.jpeg', '.png') and ('cover' in f.lower() or not cover_src):
                    cover_src = str(full_path)
                elif ext == '.opf':
                    opf_src = str(full_path)

            if not formats:
                continue

            book_idx += 1
            # Metadata extraction
            clean_title = title_dir_name.strip()
            clean_author = author_info.get("canonical_bn", author_dir_name.strip())

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

            # Cover generation
            cover_dest = covers_dir / f"{book_id}.webp"
            has_cover = False
            if not skip_images and cover_src:
                has_cover = optimize_cover(cover_src, str(cover_dest))
            elif cover_dest.exists():
                has_cover = True

            cover_web_path = f"assets/covers/{book_id}.webp" if has_cover else ""

            # OPF info
            opf_info = parse_opf(opf_src) if opf_src else {}

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
