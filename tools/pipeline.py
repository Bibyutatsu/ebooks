#!/usr/bin/env python3
"""
Unified Ebooks Pipeline CLI for Bibyutatsu BookStore.

Central orchestrator for:
- Building & normalizing catalog metadata
- Scalable graph analytics & multi-factor similarity calculations
- High-visibility static SEO page pre-rendering (books, authors, series)
- Search engine canonical sitemaps (sitemap.xml & sitemap.txt)
- End-to-end automated schema and SEO verification tests
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Ensure tools/core is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = Path(__file__).resolve().parent / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from analytics_engine import AnalyticsEngine
from page_generator import generate_all_pages
from sitemap_generator import generate_sitemap


def run_build_catalog(downloads_dir: str = "./downloads", skip_images: bool = True):
    """Executes catalog builder if downloads exist."""
    from build_catalog import build_catalog
    print("\n📦 [1/5] Running Catalog Builder...")
    catalog = build_catalog(downloads_dir, str(ROOT_DIR), skip_images=skip_images)
    return catalog


def run_analytics(catalog_path: str = None):
    """Computes relational analytics graph, author affinities, and related works."""
    cat_file = catalog_path or str(ROOT_DIR / "catalog.json")
    print(f"\n🧠 [2/5] Computing Analytics & Similarity Graph from {cat_file}...")
    start = time.time()
    engine = AnalyticsEngine(cat_file)
    summary, graph = engine.export_graph(str(ROOT_DIR / "analytics"))
    elapsed = time.time() - start
    print(f"✓ Analytics computed in {elapsed:.2f}s: {summary['total_books']} books, {summary['total_authors']} authors, {summary['total_series']} series.")
    return engine


def run_generate_pages(catalog_path: str = None):
    """Pre-renders static HTML pages for all books, authors, and series."""
    cat_file = catalog_path or str(ROOT_DIR / "catalog.json")
    print(f"\n🌐 [3/5] Pre-rendering Static SEO Landing Pages...")
    start = time.time()
    generate_all_pages(cat_file, str(ROOT_DIR))
    elapsed = time.time() - start
    print(f"✓ Page generation finished in {elapsed:.2f}s.")


def run_generate_sitemap(catalog_path: str = None):
    """Generates canonical sitemap.xml and sitemap.txt."""
    cat_file = catalog_path or str(ROOT_DIR / "catalog.json")
    print(f"\n🗺️  [4/5] Updating Search Engine Sitemaps...")
    url_count = generate_sitemap(cat_file, str(ROOT_DIR))
    print(f"✓ Sitemaps updated successfully with {url_count} URLs.")


def run_verification(catalog_path: str = None):
    """Runs catalog integrity and SEO verification suites."""
    cat_file = catalog_path or str(ROOT_DIR / "catalog.json")
    print(f"\n🧪 [5/5] Running Automated Verification Tests...")
    
    # Run verify_seo_pages
    verify_seo_script = ROOT_DIR / "tests" / "verify_seo_pages.py"
    if verify_seo_script.exists():
        import subprocess
        res = subprocess.run([sys.executable, str(verify_seo_script), cat_file], capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print(res.stderr)
            raise RuntimeError("SEO verification tests failed.")
    print("✓ All automated verification checks passed!")


def run_all(catalog_path: str = None):
    """Executes the full pipeline end-to-end."""
    print("=" * 60)
    print("🚀 BIBYUTATSU EBOOKS PIPELINE — FULL EXECUTION")
    print("=" * 60)
    start_total = time.time()

    cat_file = catalog_path or str(ROOT_DIR / "catalog.json")
    run_analytics(cat_file)
    run_generate_pages(cat_file)
    run_generate_sitemap(cat_file)
    run_verification(cat_file)

    total_elapsed = time.time() - start_total
    print("\n" + "=" * 60)
    print(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {total_elapsed:.2f} SECONDS!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Unified CLI Pipeline for Bibyutatsu BookStore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  all         Run end-to-end pipeline (analyze, pages, sitemap, verify)
  analyze     Compute similarity graph & author analytics
  pages       Pre-render static SEO landing pages (/book, /author, /series)
  sitemap     Update canonical sitemap.xml and sitemap.txt
  verify      Run automated verification test suite
  search      Test book similarity / search in terminal
        """
    )
    parser.add_argument("command", choices=["all", "build", "analyze", "pages", "sitemap", "verify", "search"], help="Pipeline command to execute")
    parser.add_argument("--catalog", default=str(ROOT_DIR / "catalog.json"), help="Path to catalog.json")
    parser.add_argument("--query", default="", help="Query for search command")

    args = parser.parse_args()

    if args.command == "all":
        run_all(args.catalog)
    elif args.command == "build":
        run_build_catalog()
    elif args.command == "analyze":
        run_analytics(args.catalog)
    elif args.command == "pages":
        run_generate_pages(args.catalog)
    elif args.command == "sitemap":
        run_generate_sitemap(args.catalog)
    elif args.command == "verify":
        run_verification(args.catalog)
    elif args.command == "search":
        engine = AnalyticsEngine(args.catalog)
        query = args.query.lower().strip()
        print(f"\nSearching for similar books matching '{query}'...")
        matches = [b for b in engine.books if query in b.get("search_text", "").lower()][:5]
        for m in matches:
            print(f"\n📖 {m['title']} ({m.get('title_en', '')}) - {m['author']}")
            related = engine.get_related_books(m["id"], limit=3)
            print("   Top Related Works:")
            for r in related:
                print(f"   -> {r['title']} ({r.get('title_en')}) [Score: {r['score']}]")


if __name__ == "__main__":
    main()
