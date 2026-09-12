"""
Prunes the 801 Wikisource metadata hub stubs from catalog.json
and removes their generated cover images from assets/covers/.
Recalculates stats, top_authors, and genres for the cleaned catalog.
"""

import sys, json
from pathlib import Path
from collections import Counter

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))
from author_mapping import get_author_info

CATALOG_PATH = ROOT_DIR / "catalog.json"
COVERS_DIR = ROOT_DIR / "assets" / "covers"

def prune_wikisource(dry_run=False):
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    books = catalog["books"]
    ws_books = [b for b in books if b.get("source") == "wikisource"]
    retained_books = [b for b in books if b.get("source") != "wikisource"]

    print(f"Original books count: {len(books)}")
    print(f"Wikisource stub books to prune: {len(ws_books)}")
    print(f"Retained genuine books: {len(retained_books)}")

    # Check covers to delete
    retained_covers = set(b.get("cover") for b in retained_books if b.get("cover"))
    ws_covers = [b.get("cover") for b in ws_books if b.get("cover")]
    
    deleted_covers_count = 0
    for cp in ws_covers:
        if cp and cp not in retained_covers:
            p = ROOT_DIR / cp
            if p.exists():
                if not dry_run:
                    try:
                        p.unlink()
                        deleted_covers_count += 1
                    except Exception as e:
                        print(f"Error deleting {p}: {e}")
                else:
                    deleted_covers_count += 1

    print(f"Cover files deleted: {deleted_covers_count}")

    # Recalculate stats, top_authors, and genres
    author_counts = Counter()
    author_en_map = {}
    genre_counts = Counter()
    format_counts = Counter()

    for b in retained_books:
        auth = b.get("author", "অজ্ঞাত")
        auth_en = b.get("author_en", "")
        author_counts[auth] += 1
        if auth not in author_en_map or (not author_en_map[auth] and auth_en):
            author_en_map[auth] = auth_en

        for g in b.get("genres", []):
            if g != "বাংলা উইকিসংকলন (Wikisource)":
                genre_counts[g] += 1
        
        # Also clean up genre list on book if it had Wikisource genre
        if "genres" in b:
            b["genres"] = [g for g in b["genres"] if g != "বাংলা উইকিসংকলন (Wikisource)"]

        for fmt in b.get("formats", {}):
            format_counts[fmt] += 1

    top_authors = []
    for auth, count in author_counts.most_common(30):
        en_name = author_en_map.get(auth) or get_author_info(auth).get("en", "Unknown")
        top_authors.append({
            "author": auth,
            "author_en": en_name,
            "count": count
        })

    genres = [{"genre": g, "count": c} for g, c in genre_counts.most_common()]

    new_catalog = {
        "version": catalog.get("version", "1.0.0"),
        "generated_at": catalog.get("generated_at", "2026-09-11"),
        "stats": {
            "total_books": len(retained_books),
            "total_authors": len(author_counts),
            "formats": dict(format_counts),
            "genres_count": len(genre_counts)
        },
        "top_authors": top_authors,
        "genres": genres,
        "books": retained_books
    }

    print("\nNew Catalog Summary:")
    print(f"  Total Books: {len(retained_books)}")
    print(f"  Total Authors: {len(author_counts)}")
    print(f"  Formats: {dict(format_counts)}")
    print(f"  Genres Count: {len(genre_counts)}")
    print(f"  Top 3 Authors: {top_authors[:3]}")

    if not dry_run:
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(new_catalog, f, ensure_ascii=False, indent=2)
        print("catalog.json successfully updated and saved!")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    prune_wikisource(dry_run=dry_run)
