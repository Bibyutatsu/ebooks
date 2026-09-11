"""
Catalog Transliteration Refresh & Enrichment Tool.
Updates title_en, title_translit, and search_text for all books in catalog.json
using the upgraded context-aware transliteration engine.
Preserves all IDs, covers, release URLs, series, and genres.
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from transliteration import transliterate_text

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = WORKSPACE_ROOT / "catalog.json"


def refresh_catalog():
    print(f"Reading {CATALOG_PATH}...")
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    books = data.get("books", [])
    print(f"Found {len(books)} books in catalog.")

    updated_count = 0

    for idx, book in enumerate(books):
        clean_title = book.get("title", "").strip()
        if not clean_title:
            continue

        # Generate fresh context-aware transliterations
        translit_variants = transliterate_text(clean_title)
        if not translit_variants:
            translit_variants = [book.get("title_en", clean_title).lower()]

        # Primary readable title
        primary_title_en = translit_variants[0].title()

        # Update fields
        book["title_en"] = primary_title_en
        # Keep up to 8 unique transliteration variations for display & search
        book["title_translit"] = translit_variants[:8]

        # Build fresh search tokens
        search_tokens = set()
        search_tokens.add(clean_title.lower())
        search_tokens.add(book.get("author", "").lower())
        search_tokens.add(book.get("author_en", "").lower())
        for a in book.get("author_aliases", []):
            search_tokens.add(a.lower())
        for t in book["title_translit"]:
            search_tokens.add(t.lower())
        series = book.get("series")
        if series and isinstance(series, dict):
            if series.get("name_bn"):
                search_tokens.add(series["name_bn"].lower())
            if series.get("name_en"):
                search_tokens.add(series["name_en"].lower())
        for g in book.get("genres", []):
            search_tokens.add(g.lower())

        book["search_text"] = " ".join(sorted(list(search_tokens)))
        updated_count += 1

    print(f"Updated transliteration metadata for {updated_count} books.")

    # Atomic write to catalog.json
    temp_path = CATALOG_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(temp_path, CATALOG_PATH)
    print(f"Successfully wrote updated catalog to {CATALOG_PATH}.")


if __name__ == "__main__":
    refresh_catalog()
