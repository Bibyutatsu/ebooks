#!/usr/bin/env python3
"""
Generate a strictly RFC 3986 and Google-compliant XML sitemap (sitemap.xml) for Bibyutatsu BookStore.
Ensures:
- 100% ASCII-safe URL encoding for all queries, author names, genres, and book IDs
- Canonical Google Sitemaps 0.9 XML namespace without external XSD schema locks
- Valid XML character escaping
"""

import json
import os
import urllib.parse
from datetime import datetime
from xml.sax.saxutils import escape

BASE_URL = "https://bibyutatsu.github.io/ebooks/"

TRENDING_SEARCHES = [
    "feluda",
    "byomkesh",
    "humayun ahmed",
    "shonku",
    "kakababu",
    "tintin",
    "masud rana",
    "himu",
    "misir ali",
    "tenida",
    "satyajit ray",
    "rabindranath tagore",
    "sukumar ray",
    "sharadindu"
]

def generate_sitemap(catalog_path, output_path):
    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    books = data.get('books', [])
    generated_at = data.get('generated_at') or datetime.utcnow().strftime('%Y-%m-%d')
    if 'T' in generated_at:
        today_str = generated_at.split('T')[0]
    else:
        today_str = generated_at[:10]

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    url_list = []

    def add_url(loc, priority="0.7", changefreq="monthly", lastmod=today_str):
        # Strict ASCII check
        try:
            loc.encode('ascii')
        except UnicodeEncodeError as e:
            raise ValueError(f"Non-ASCII character in URL: {loc}") from e

        url_list.append(loc)

        # Escape XML entities (especially '&' to '&amp;', quotes to &quot;)
        safe_loc = escape(loc, {'"': '&quot;', "'": '&apos;'})
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{safe_loc}</loc>')
        xml_lines.append(f'    <lastmod>{lastmod}</lastmod>')
        xml_lines.append(f'    <changefreq>{changefreq}</changefreq>')
        xml_lines.append(f'    <priority>{priority}</priority>')
        xml_lines.append('  </url>')

    # 1. Homepage Root
    add_url(BASE_URL, priority="1.0", changefreq="daily")

    # 2. Trending searches
    for query in TRENDING_SEARCHES:
        param = urllib.parse.quote(query)
        add_url(f"{BASE_URL}?q={param}", priority="0.85", changefreq="weekly")

    # 3. Authors & Genres extraction
    author_counts = {}
    genre_set = set()

    for b in books:
        auth = b.get('author')
        if auth and auth != 'Unknown':
            author_counts[auth] = author_counts.get(auth, 0) + 1
        for g in b.get('genres', []):
            if g:
                genre_set.add(g)

    # Sort authors by volume, take top authors with >= 2 books
    top_authors = [auth for auth, count in sorted(author_counts.items(), key=lambda x: -x[1]) if count >= 2]
    for auth in top_authors:
        param = urllib.parse.quote(auth)
        add_url(f"{BASE_URL}?author={param}", priority="0.8", changefreq="weekly")

    # Genres
    for g in sorted(genre_set):
        param = urllib.parse.quote(g)
        add_url(f"{BASE_URL}?genre={param}", priority="0.8", changefreq="weekly")

    # 4. Individual Books (every single book URL safely percent-encoded)
    for b in books:
        book_id = b.get('id')
        if not book_id:
            continue
        param = urllib.parse.quote(book_id)
        book_url = f"{BASE_URL}?book={param}"
        add_url(book_url, priority="0.7", changefreq="monthly")

    xml_lines.append('</urlset>')
    xml_content = "\n".join(xml_lines) + "\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    # Also generate sitemap.txt as a fallback for Google Search Console
    txt_path = os.path.join(os.path.dirname(output_path), 'sitemap.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(url_list) + "\n")

    total_urls = len(books) + len(TRENDING_SEARCHES) + len(top_authors) + len(genre_set) + 1
    print(f"Generated {output_path} and {txt_path} with {total_urls} URLs successfully (100% RFC 3986 ASCII compliant).")

if __name__ == '__main__':
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_file = os.path.join(root_dir, 'catalog.json')
    sitemap_file = os.path.join(root_dir, 'sitemap.xml')
    generate_sitemap(cat_file, sitemap_file)
