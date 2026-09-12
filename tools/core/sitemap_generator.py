"""
Comprehensive Sitemap Generator for Bibyutatsu BookStore.

Generates:
1. sitemap.xml: High-priority search engine sitemap containing:
   - Canonical Root Homepage (priority: 1.0)
   - Series Landing Pages (priority: 0.9)
   - Author Hub Pages (priority: 0.8)
   - All 2,935+ Book Landing Pages (priority: 0.7)
2. sitemap.txt: Line-delimited canonical URL list for alternative crawlers.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape

BASE_URL = "https://bibyutatsu.github.io/ebooks/"


def generate_sitemap(catalog_path: str, output_root: str):
    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    out_root = Path(output_root)
    sitemap_xml_path = out_root / "sitemap.xml"
    sitemap_txt_path = out_root / "sitemap.txt"

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    generated_at = data.get('generated_at')
    if generated_at:
        today_str = generated_at.split('T')[0] if 'T' in generated_at else generated_at[:10]

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    url_list = []

    def add_entry(loc: str, priority: str = "0.7", changefreq: str = "monthly"):
        url_list.append(loc)
        safe_loc = escape(loc, {'"': '&quot;', "'": '&apos;'})
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{safe_loc}</loc>')
        xml_lines.append(f'    <lastmod>{today_str}</lastmod>')
        xml_lines.append(f'    <changefreq>{changefreq}</changefreq>')
        xml_lines.append(f'    <priority>{priority}</priority>')
        xml_lines.append('  </url>')

    # 1. Canonical Root
    add_entry(BASE_URL, priority="1.0", changefreq="daily")

    # 2. Series Hub Pages
    series_dir = out_root / "series"
    if series_dir.exists():
        for s_file in sorted(series_dir.glob("*.html")):
            if s_file.name == "index.html":
                add_entry(f"{BASE_URL}series/", priority="0.95", changefreq="weekly")
            else:
                add_entry(f"{BASE_URL}series/{s_file.name}", priority="0.9", changefreq="weekly")

    # 3. Author Hub Pages
    author_dir = out_root / "author"
    if author_dir.exists():
        for a_file in sorted(author_dir.glob("*.html")):
            if a_file.name == "index.html":
                add_entry(f"{BASE_URL}author/", priority="0.9", changefreq="weekly")
            else:
                add_entry(f"{BASE_URL}author/{a_file.name}", priority="0.8", changefreq="weekly")

    # 4. Individual Book Landing Pages
    book_dir = out_root / "book"
    if book_dir.exists():
        for b_file in sorted(book_dir.glob("*.html")):
            add_entry(f"{BASE_URL}book/{b_file.name}", priority="0.7", changefreq="monthly")

    xml_lines.append('</urlset>')
    xml_content = "\n".join(xml_lines) + "\n"

    with open(sitemap_xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    with open(sitemap_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(url_list) + "\n")

    print(f"✓ Generated {sitemap_xml_path} and {sitemap_txt_path} ({len(url_list)} canonical URLs).")
    return len(url_list)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    cat = root / "catalog.json"
    generate_sitemap(str(cat), str(root))
