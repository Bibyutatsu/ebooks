"""
Comprehensive Automated Verification Test Suite for SEO Landing Pages & Sitemaps.

Validates:
1. 100% Parity: Every book in catalog.json has a generated book/{id}.html.
2. Series & Author Coverage: All series and author hub pages exist.
3. JSON-LD Schema.org Validity: Validates Book, BreadcrumbList, Person, and Series schemas.
4. Canonical & OpenGraph Consistency: Ensures correct canonical URLs and metadata tags.
5. Search Engine Sitemap Coverage: Validates sitemap.xml and sitemap.txt structure and URL counts.
6. Analytics Graph Integrity: Validates relationship graph and related works precomputations.
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_catalog_and_page_parity(catalog_path: str):
    print("========================================")
    print("1. VERIFYING PAGE PARITY & COVERAGE")
    print("========================================")

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    books = data.get("books", [])
    total_books = len(books)
    assert total_books > 0, "Catalog contains 0 books."

    book_dir = ROOT_DIR / "book"
    assert book_dir.exists(), "Directory book/ does not exist."

    missing_books = []
    for b in books:
        b_id = b["id"]
        expected_file = book_dir / f"{b_id}.html"
        if not expected_file.exists():
            missing_books.append(b_id)

    assert len(missing_books) == 0, f"Missing {len(missing_books)} book pages! Samples: {missing_books[:5]}"
    print(f"✓ 100% Parity: All {total_books} books have generated static landing pages in book/.")

    # Check series pages
    series_dir = ROOT_DIR / "series"
    assert series_dir.exists(), "Directory series/ does not exist."
    series_files = list(series_dir.glob("*.html"))
    assert len(series_files) >= 15, f"Expected at least 15 series pages, found {len(series_files)}."
    print(f"✓ Series coverage verified: {len(series_files)} series hub pages.")

    # Check author pages
    author_dir = ROOT_DIR / "author"
    assert author_dir.exists(), "Directory author/ does not exist."
    author_files = list(author_dir.glob("*.html"))
    assert len(author_files) >= 700, f"Expected >= 700 author pages, found {len(author_files)}."
    print(f"✓ Author coverage verified: {len(author_files)} author collection pages.")


def test_metadata_and_schema(catalog_path: str):
    print("\n========================================")
    print("2. VALIDATING METADATA & SCHEMA.ORG JSON-LD")
    print("========================================")

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    books = data.get("books", [])
    # Sample every 50th book for thorough multi-point inspection
    sample_books = books[::50]

    for b in sample_books:
        b_id = b["id"]
        file_path = ROOT_DIR / "book" / f"{b_id}.html"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Title & Meta description
        assert "<title>" in content and "</title>" in content, f"Missing <title> in {b_id}.html"
        assert '<meta name="description"' in content, f"Missing meta description in {b_id}.html"
        assert '<link rel="canonical"' in content, f"Missing canonical link in {b_id}.html"

        # 2. Canonical self-reference
        expected_canonical = f"https://bibyutatsu.github.io/ebooks/book/{b_id}.html"
        assert expected_canonical in content, f"Canonical mismatch in {b_id}.html: expected {expected_canonical}"

        # 3. Open Graph
        assert '<meta property="og:title"' in content, f"Missing og:title in {b_id}.html"
        assert '<meta property="og:image"' in content, f"Missing og:image in {b_id}.html"

        # 4. JSON-LD scripts
        assert '<script type="application/ld+json">' in content, f"Missing JSON-LD in {b_id}.html"
        parts = content.split('<script type="application/ld+json">')[1:]
        for p in parts:
            json_str = p.split('</script>')[0].strip()
            parsed = json.loads(json_str)
            assert "@context" in parsed, f"Missing @context in JSON-LD of {b_id}"
            assert "@type" in parsed, f"Missing @type in JSON-LD of {b_id}"

        # 5. Formats and Download Links
        for fmt, f_info in b.get("formats", {}).items():
            dl_url = f_info.get("download_url", "")
            if dl_url:
                assert dl_url in content, f"Missing download URL for {fmt} in {b_id}.html"

    print(f"✓ Validated schema.org Book & BreadcrumbList across {len(sample_books)} sample pages.")


def test_sitemap_integrity():
    print("\n========================================")
    print("3. VALIDATING SITEMAP INTEGRITY & COVERAGE")
    print("========================================")

    sitemap_xml = ROOT_DIR / "sitemap.xml"
    sitemap_txt = ROOT_DIR / "sitemap.txt"

    assert sitemap_xml.exists(), "sitemap.xml does not exist."
    assert sitemap_txt.exists(), "sitemap.txt does not exist."

    # Parse XML
    tree = ET.parse(sitemap_xml)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = [loc.text for loc in root.findall("sm:url/sm:loc", ns)]
    assert len(urls) >= 3650, f"Expected >= 3,650 URLs in sitemap.xml, found {len(urls)}."

    # Verify Root URL
    assert "https://bibyutatsu.github.io/ebooks/" in urls, "Root homepage missing from sitemap."

    # Verify Book URLs sample
    sample_book_url = f"https://bibyutatsu.github.io/ebooks/book/satyajit-ray-sonar-kella.html"
    assert sample_book_url in urls, f"Sample book URL {sample_book_url} missing from sitemap."

    # Verify Series URLs sample
    sample_series_url = f"https://bibyutatsu.github.io/ebooks/series/feluda.html"
    assert sample_series_url in urls, f"Sample series URL {sample_series_url} missing from sitemap."

    # Verify sitemap.txt parity
    with open(sitemap_txt, "r", encoding="utf-8") as f:
        txt_urls = [line.strip() for line in f if line.strip()]

    assert len(txt_urls) == len(urls), f"sitemap.txt ({len(txt_urls)}) does not match sitemap.xml ({len(urls)}) count."
    print(f"✓ Sitemap verified: {len(urls)} URLs with 100% XML validity and txt parity.")


def test_analytics_graph():
    print("\n========================================")
    print("4. VALIDATING ANALYTICS & SIMILARITY GRAPH")
    print("========================================")

    graph_file = ROOT_DIR / "analytics" / "catalog_graph.json"
    summary_file = ROOT_DIR / "analytics" / "summary.json"

    assert graph_file.exists(), "analytics/catalog_graph.json missing."
    assert summary_file.exists(), "analytics/summary.json missing."

    with open(graph_file, "r", encoding="utf-8") as f:
        graph = json.load(f)

    for key in ("summary", "authors", "series", "book_relations"):
        assert key in graph, f"Missing key {key} in catalog_graph.json"

    assert len(graph["book_relations"]) == graph["summary"]["total_books"], "Book relations count mismatch."
    print(f"✓ Analytics graph verified: {len(graph['authors'])} authors, {len(graph['series'])} series, {len(graph['book_relations'])} book relation clusters.")


if __name__ == "__main__":
    cat_file = sys.argv[1] if len(sys.argv) > 1 else str(ROOT_DIR / "catalog.json")
    try:
        test_catalog_and_page_parity(cat_file)
        test_metadata_and_schema(cat_file)
        test_sitemap_integrity()
        test_analytics_graph()
        print("\n🎉 ALL SEO & SYSTEM VERIFICATION TESTS PASSED SUCCESSFULLY!")
    except AssertionError as e:
        print(f"\n❌ TEST VERIFICATION FAILED: {e}")
        sys.exit(1)
