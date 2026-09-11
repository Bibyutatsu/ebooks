#!/usr/bin/env python3
"""
Generate a clean, strictly canonical sitemap for Bibyutatsu BookStore.
By default generates the simplified canonical root URL that is 100% accepted
by Google Search Console without query-string canonical mismatch errors.
Use --all to include dynamic collection queries and book links.
"""

import json
import os
import sys
import urllib.parse
from datetime import datetime
from xml.sax.saxutils import escape

BASE_URL = "https://bibyutatsu.github.io/ebooks/"

def generate_sitemap(catalog_path, output_path, include_all=False):
    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    generated_at = data.get('generated_at') or datetime.utcnow().strftime('%Y-%m-%d')
    today_str = generated_at.split('T')[0] if 'T' in generated_at else generated_at[:10]

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    url_list = []

    def add_url(loc, priority="0.7", changefreq="monthly"):
        url_list.append(loc)
        safe_loc = escape(loc, {'"': '&quot;', "'": '&apos;'})
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{safe_loc}</loc>')
        xml_lines.append(f'    <lastmod>{today_str}</lastmod>')
        xml_lines.append(f'    <changefreq>{changefreq}</changefreq>')
        xml_lines.append(f'    <priority>{priority}</priority>')
        xml_lines.append('  </url>')

    # 1. Canonical Root
    add_url(BASE_URL, priority="1.0", changefreq="daily")

    # 2. Detailed URLs (optional via --all)
    if include_all:
        trending = ["feluda", "byomkesh", "humayun ahmed", "shonku", "kakababu", "tintin", "himu", "misir ali"]
        for q in trending:
            add_url(f"{BASE_URL}?q={urllib.parse.quote(q)}", priority="0.8", changefreq="weekly")

        for b in data.get('books', []):
            book_id = b.get('id')
            if book_id:
                add_url(f"{BASE_URL}?book={urllib.parse.quote(book_id)}", priority="0.6", changefreq="monthly")

    xml_lines.append('</urlset>')
    xml_content = "\n".join(xml_lines) + "\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    txt_path = os.path.join(os.path.dirname(output_path), 'sitemap.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(url_list) + "\n")

    print(f"Generated {output_path} ({len(url_list)} URLs) successfully.")

if __name__ == '__main__':
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_file = os.path.join(root_dir, 'catalog.json')
    sitemap_file = os.path.join(root_dir, 'sitemap.xml')
    include_all = '--all' in sys.argv
    generate_sitemap(cat_file, sitemap_file, include_all)
