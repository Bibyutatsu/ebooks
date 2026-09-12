"""
High-Performance Static Page Generator for Bibyutatsu BookStore.

Pre-renders:
1. /book/{id}.html (2,935 individual book landing pages with rich schema.org/Book,
   dual-script SEO titles, direct 0ms download links, related books, and interactive app CTA).
2. /author/{slug}.html (Author collection pages with bibliographies, similar authors, and schema.org/Person).
3. /series/{slug}.html (15 Series hub pages with reading order, covers, and schema.org/Series).

Design: Modern dark aesthetic matching style.css (OKLCH gradients, glassmorphism, responsive grid).
"""

import os
import re
import html
import json
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import sys
sys.path.insert(0, os.path.dirname(__file__))

from analytics_engine import AnalyticsEngine, slugify

BASE_URL = "https://bibyutatsu.github.io/ebooks/"


def escape_txt(text: str) -> str:
    """Safely escapes text for HTML insertion."""
    return html.escape(str(text or ""), quote=True)


def get_format_color(fmt: str) -> str:
    fmt_colors = {
        "epub": "#00ccff",
        "kfx": "#f59e0b",
        "pdf": "#ef4444",
        "mobi": "#a855f7",
        "txt": "#10b981",
        "docx": "#3b82f6",
        "azw3": "#eab308"
    }
    return fmt_colors.get(fmt.lower(), "#828cc8")


SHARED_CSS = """
:root {
  --bg: #06060f;
  --surface: #0d0d1e;
  --surface-2: #131326;
  --surface-hover: #1c1c36;
  --accent: #00ccff;
  --accent-2: #8a2be2;
  --text: #c2c7df;
  --text-muted: #626685;
  --border: rgba(130, 140, 200, 0.12);
  --border-hover: rgba(130, 140, 200, 0.32);
  --heading: #eaecf8;
  --radius: 12px;
  --radius-lg: 18px;
  --shadow: 0 10px 30px -10px rgba(0,0,0,0.6);
  --glow: 0 0 24px rgba(0, 204, 255, 0.18);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', 'Hind Siliguri', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
a { color: var(--accent); text-decoration: none; transition: 0.2s ease; }
a:hover { color: #5ce1e6; }
.container { width: 100%; max-width: 1160px; margin: 0 auto; padding: 0 20px; }

/* Header */
.site-header {
  background: rgba(6, 6, 15, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 14px 0;
}
.header-inner { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.15rem; color: var(--heading); }
.brand-icon { font-size: 1.4rem; }
.header-nav { display: flex; align-items: center; gap: 12px; }
.nav-btn {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 8px 14px;
  border-radius: var(--radius);
  font-size: 0.85rem;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}
.nav-btn:hover { background: var(--surface-hover); border-color: var(--accent); color: var(--heading); }
.nav-btn.primary { background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%); color: #fff; border: none; }
.nav-btn.primary:hover { opacity: 0.92; box-shadow: var(--glow); }

/* Breadcrumbs */
.breadcrumbs {
  padding: 18px 0 10px;
  font-size: 0.85rem;
  color: var(--text-muted);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.breadcrumbs span { color: var(--text); }

/* Hero / Main Book Layout */
.book-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 40px;
  padding: 30px 0 50px;
  align-items: start;
}
@media (max-width: 820px) {
  .book-layout { grid-template-columns: 1fr; gap: 28px; }
}

/* Cover Wrapper */
.cover-wrapper {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  box-shadow: var(--shadow);
}
.book-cover {
  width: 100%;
  max-width: 260px;
  aspect-ratio: 10 / 15;
  object-fit: cover;
  border-radius: 8px;
  box-shadow: 0 14px 28px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255,255,255,0.06);
}
.cover-placeholder {
  width: 100%;
  max-width: 260px;
  aspect-ratio: 10 / 15;
  border-radius: 8px;
  background: linear-gradient(135deg, #181830 0%, #0a0a16 100%);
  border: 1px dashed var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
  color: var(--text-muted);
}

/* Book Meta Details */
.book-details { display: flex; flex-direction: column; gap: 20px; }
.book-title {
  font-size: 2.1rem;
  font-weight: 800;
  color: var(--heading);
  line-height: 1.25;
}
.book-title-en {
  font-size: 1.15rem;
  color: var(--text-muted);
  font-weight: 500;
  margin-top: 4px;
}
.book-author-line {
  font-size: 1.05rem;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}
.author-link { font-weight: 600; color: var(--accent); }
.badges-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.badge {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
}
.badge.series-badge {
  background: rgba(138, 43, 226, 0.15);
  border-color: rgba(138, 43, 226, 0.4);
  color: #c084fc;
}
.badge.series-badge:hover { background: rgba(138, 43, 226, 0.25); }

/* Download Section */
.download-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.download-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--heading);
  display: flex;
  align-items: center;
  gap: 8px;
}
.download-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 12px;
}
.download-btn {
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: 12px 16px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--heading);
  font-weight: 600;
  transition: all 0.2s ease;
}
.download-btn:hover {
  background: var(--surface-hover);
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 204, 255, 0.15);
}
.dl-left { display: flex; align-items: center; gap: 10px; }
.fmt-tag {
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
  padding: 3px 6px;
  border-radius: 4px;
}
.dl-size { font-size: 0.78rem; color: var(--text-muted); font-weight: 400; }
.dl-icon { font-size: 1.1rem; color: var(--text-muted); }
.download-btn:hover .dl-icon { color: var(--accent); }

/* App CTA */
.app-cta {
  background: linear-gradient(135deg, rgba(0, 204, 255, 0.08) 0%, rgba(138, 43, 226, 0.08) 100%);
  border: 1px dashed rgba(0, 204, 255, 0.35);
  border-radius: var(--radius);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.app-cta-text { font-size: 0.9rem; color: var(--text); }
.app-cta-text strong { color: var(--heading); }

/* Info Table */
.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.info-table th, .info-table td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
.info-table th { color: var(--text-muted); font-weight: 500; width: 130px; }
.info-table td { color: var(--heading); }

/* Related Books Section */
.related-section {
  padding: 40px 0 60px;
  border-top: 1px solid var(--border);
  margin-top: 20px;
}
.section-heading {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--heading);
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.related-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 18px;
}
.mini-book-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
}
.mini-book-card:hover {
  background: var(--surface-hover);
  border-color: var(--border-hover);
  transform: translateY(-3px);
  box-shadow: var(--shadow);
}
.mini-cover {
  width: 100%;
  aspect-ratio: 10 / 14;
  object-fit: cover;
  border-radius: 6px;
  background: var(--surface-2);
}
.mini-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--heading);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.mini-author { font-size: 0.75rem; color: var(--text-muted); }

/* Footer */
.site-footer {
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding: 30px 0;
  margin-top: auto;
  font-size: 0.85rem;
  color: var(--text-muted);
  text-align: center;
}
.footer-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 18px;
  margin-bottom: 12px;
}
"""

GA_SCRIPT = """
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-W9EW0QE84W"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-W9EW0QE84W');
  </script>
"""


def render_book_page(book: dict, related_books: list[dict], author_slug: str = "", root_rel: str = "../") -> str:
    """Renders a complete, self-contained SEO landing page for a book."""
    b_id = book["id"]
    title_bn = escape_txt(book.get("title", ""))
    title_en = escape_txt(book.get("title_en", ""))
    author_bn = escape_txt(book.get("author", ""))
    author_en = escape_txt(book.get("author_en", author_bn))
    if not author_slug:
        author_slug = slugify(book.get("author_en") or book.get("author"), max_len=50)

    series_obj = book.get("series")
    series_name_bn = escape_txt(series_obj.get("name_bn", "")) if series_obj and isinstance(series_obj, dict) else ""
    series_name_en = escape_txt(series_obj.get("name_en", "")) if series_obj and isinstance(series_obj, dict) else ""
    series_slug = slugify(series_obj.get("id")) if series_obj and isinstance(series_obj, dict) else ""

    genres = [escape_txt(g) for g in book.get("genres", [])]
    genre_str = ", ".join(genres)
    year = escape_txt(book.get("year", ""))
    cover_path = book.get("cover", "")
    cover_url_abs = f"{BASE_URL}{cover_path}" if cover_path else f"{BASE_URL}assets/og-preview.png"
    canonical_url = f"{BASE_URL}book/{b_id}.html"

    formats = book.get("formats", {})
    format_names = [f.upper() for f in formats.keys()]
    format_str = ", ".join(format_names)

    # SEO Title & Description
    page_title = f"{title_bn} ({title_en}) - {author_bn} | Free Bengali Ebook Download"
    meta_desc = f"Download {title_bn} ({title_en}) by {author_bn} ({author_en}) free in {format_str}. {genre_str} Bengali literature digital edition on Bibyutatsu BookStore."
    if len(meta_desc) > 160:
        meta_desc = meta_desc[:157] + "..."

    # Formats buttons HTML
    dl_buttons_html = []
    total_size = 0
    for fmt, f_info in formats.items():
        dl_url = f_info.get("download_url", "")
        f_size = f_info.get("size_formatted", "")
        filename = f_info.get("filename", "")
        total_size += f_info.get("size_bytes", 0)
        fmt_color = get_format_color(fmt)
        dl_buttons_html.append(f"""
          <a href="{escape_txt(dl_url)}" class="download-btn" download="{escape_txt(filename)}" target="_blank" rel="noopener">
            <div class="dl-left">
              <span class="fmt-tag" style="background: {fmt_color}22; color: {fmt_color}; border: 1px solid {fmt_color}44;">{fmt.upper()}</span>
              <div>
                <div>Download {fmt.upper()}</div>
                <div class="dl-size">{escape_txt(f_size)}</div>
              </div>
            </div>
            <span class="dl-icon">⬇</span>
          </a>
        """)

    # Related books HTML
    related_html = []
    for r in related_books:
        r_title = escape_txt(r["title"])
        r_author = escape_txt(r["author"])
        r_cover = r.get("cover")
        r_cover_img = f'<img src="{root_rel}{r_cover}" alt="{r_title}" class="mini-cover" loading="lazy" />' if r_cover else '<div class="mini-cover" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:0.7rem;">No Cover</div>'
        related_html.append(f"""
          <a href="{root_rel}book/{r['id']}.html" class="mini-book-card">
            {r_cover_img}
            <div class="mini-title">{r_title}</div>
            <div class="mini-author">{r_author}</div>
          </a>
        """)

    # Series link HTML
    series_html = ""
    if series_name_bn:
        series_html = f"""
          <a href="{root_rel}series/{series_slug}.html" class="badge series-badge">
            ⚡ {series_name_bn} ({series_name_en}) Series
          </a>
        """

    # Schema JSON-LD
    schema_book = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": book.get("title", ""),
        "alternateName": book.get("title_en", ""),
        "author": {
            "@type": "Person",
            "name": book.get("author", ""),
            "alternateName": book.get("author_en", "")
        },
        "inLanguage": "bn",
        "bookFormat": "https://schema.org/EBook",
        "image": cover_url_abs,
        "isAccessibleForFree": True,
        "genre": book.get("genres", []),
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock"
        },
        "url": canonical_url
    }

    schema_breadcrumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": BASE_URL
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": book.get("author", "Author"),
                "item": f"{BASE_URL}author/{author_slug}.html"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": book.get("title", "Book"),
                "item": canonical_url
            }
        ]
    }

    json_ld_scripts = f"""
    <script type="application/ld+json">
    {json.dumps(schema_book, ensure_ascii=False, indent=2)}
    </script>
    <script type="application/ld+json">
    {json.dumps(schema_breadcrumbs, ensure_ascii=False, indent=2)}
    </script>
    """

    cover_img_html = f'<img src="{root_rel}{cover_path}" alt="{title_bn} - {author_bn}" class="book-cover" fetchpriority="high" />' if cover_path else f'<div class="cover-placeholder"><div>📖</div><div style="margin-top:10px;font-weight:600;">{title_bn}</div></div>'

    html_out = f"""<!DOCTYPE html>
<html lang="bn" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_txt(page_title)}</title>
  <meta name="description" content="{escape_txt(meta_desc)}">
  <meta name="keywords" content="{title_bn}, {title_en}, {author_bn}, {author_en}, bengali ebook, bangla boi download, free epub, kindle kfx, pdf, {genre_str}">
  <meta name="author" content="{author_bn}">
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">

  <!-- Canonical URL -->
  <link rel="canonical" href="{canonical_url}">

  <!-- Open Graph -->
  <meta property="og:site_name" content="Bibyutatsu BookStore">
  <meta property="og:title" content="{title_bn} ({title_en}) - {author_bn}">
  <meta property="og:description" content="{escape_txt(meta_desc)}">
  <meta property="og:type" content="book">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image" content="{cover_url_abs}">

  <!-- Twitter Cards -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title_bn} - {author_bn}">
  <meta name="twitter:description" content="{escape_txt(meta_desc)}">
  <meta name="twitter:image" content="{cover_url_abs}">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

  {json_ld_scripts}
  {GA_SCRIPT}

  <style>
    {SHARED_CSS}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="{root_rel}" class="brand">
        <span class="brand-icon">📚</span>
        <span>Bibyutatsu BookStore</span>
      </a>
      <nav class="header-nav">
        <a href="{root_rel}" class="nav-btn">← Back to Full Library (2,900+ Books)</a>
        <a href="{root_rel}?book={b_id}" class="nav-btn primary">Open in Web App ⚡</a>
      </nav>
    </div>
  </header>

  <main class="container">
    <div class="breadcrumbs">
      <a href="{root_rel}">Home</a> /
      <a href="{root_rel}author/{author_slug}.html">{author_bn}</a> /
      {f'<a href="{root_rel}series/{series_slug}.html">{series_name_bn}</a> /' if series_name_bn else ''}
      <span>{title_bn}</span>
    </div>

    <article class="book-layout">
      <div class="cover-wrapper">
        {cover_img_html}
        <div class="badges-row" style="justify-content:center;">
          {f'<span class="badge">Published: {year}</span>' if year else ''}
          <span class="badge" style="color:var(--accent);">✓ Free Open-Access</span>
        </div>
      </div>

      <div class="book-details">
        <div>
          <h1 class="book-title">{title_bn}</h1>
          <div class="book-title-en">{title_en}</div>
        </div>

        <div class="book-author-line">
          <span>Author:</span>
          <a href="{root_rel}author/{author_slug}.html" class="author-link">{author_bn} ({author_en})</a>
        </div>

        <div class="badges-row">
          {series_html}
          {"".join(f'<span class="badge">{g}</span>' for g in genres)}
        </div>

        <div class="download-box">
          <div class="download-title">
            <span>📥 Direct Free Download Links</span>
          </div>
          <div class="download-grid">
            {"".join(dl_buttons_html)}
          </div>
        </div>

        <div class="app-cta">
          <div class="app-cta-text">
            <strong>Prefer to read in our interactive reader?</strong>
            <div>Search, filter, and stream 2,900+ books with our rich dual-script storefront.</div>
          </div>
          <a href="{root_rel}?book={b_id}" class="nav-btn primary">Open in BookStore App →</a>
        </div>

        <table class="info-table">
          <tbody>
            <tr>
              <th>Language</th>
              <td>Bengali (বাংলা)</td>
            </tr>
            <tr>
              <th>Available In</th>
              <td>{format_str}</td>
            </tr>
            <tr>
              <th>Access</th>
              <td>100% Free & Open (Digital Preservation)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    {f'''
    <section class="related-section">
      <h2 class="section-heading"><span>📚</span> Related Books & Recommendations</h2>
      <div class="related-grid">
        {"".join(related_html)}
      </div>
    </section>
    ''' if related_html else ''}
  </main>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-links">
        <a href="{root_rel}">Home</a>
        <a href="{root_rel}author/{author_slug}.html">{author_bn} Books</a>
        <a href="https://github.com/Bibyutatsu/ebooks" target="_blank" rel="noopener">GitHub Repository</a>
      </div>
      <div>Bibyutatsu BookStore — Dedicated to preserving and sharing Bengali digital literature.</div>
    </div>
  </footer>
</body>
</html>
"""
    return html_out


def render_author_page(author_info: dict, books: list[dict], root_rel: str = "../") -> str:
    """Renders a comprehensive author collection landing page."""
    slug = author_info["slug"]
    name_bn = escape_txt(author_info["name_bn"])
    name_en = escape_txt(author_info["name_en"])
    aliases = [escape_txt(a) for a in author_info.get("aliases", [])]
    total_books = author_info["total_books"]
    canonical_url = f"{BASE_URL}author/{slug}.html"

    page_title = f"{name_bn} ({name_en}) Ebooks Download | Bibyutatsu BookStore"
    meta_desc = f"Free high-speed download of {total_books} Bengali ebooks by {name_bn} ({name_en}) in EPUB, Kindle KFX, MOBI & PDF formats."

    # Books grid HTML
    cards_html = []
    for b in books:
        b_id = b["id"]
        b_title = escape_txt(b["title"])
        b_cover = b.get("cover")
        b_cover_img = f'<img src="{root_rel}{b_cover}" alt="{b_title}" class="mini-cover" loading="lazy" />' if b_cover else '<div class="mini-cover" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:0.75rem;">No Cover</div>'
        fmts = "".join(f'<span class="badge" style="font-size:0.65rem;padding:2px 5px;">{f.upper()}</span>' for f in b.get("formats", {}).keys())
        cards_html.append(f"""
          <a href="{root_rel}book/{b_id}.html" class="mini-book-card">
            {b_cover_img}
            <div class="mini-title">{b_title}</div>
            <div class="badges-row" style="margin-top:auto;">{fmts}</div>
          </a>
        """)

    # Similar authors HTML
    similar_html = []
    for sa in author_info.get("similar_authors", []):
        sa_bn = escape_txt(sa["name_bn"])
        sa_en = escape_txt(sa["name_en"])
        sa_slug = sa["slug"]
        sa_cnt = sa["books_count"]
        similar_html.append(f"""
          <a href="{root_rel}author/{sa_slug}.html" class="badge" style="padding:6px 12px;font-size:0.85rem;">
            {sa_bn} ({sa_en}) · {sa_cnt} books
          </a>
        """)

    schema_person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": author_info["name_bn"],
        "alternateName": author_info["name_en"],
        "url": canonical_url
    }

    schema_collection = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"Ebooks by {author_info['name_bn']}",
        "url": canonical_url,
        "description": meta_desc
    }

    json_ld = f"""
    <script type="application/ld+json">
    {json.dumps(schema_person, ensure_ascii=False, indent=2)}
    </script>
    <script type="application/ld+json">
    {json.dumps(schema_collection, ensure_ascii=False, indent=2)}
    </script>
    """

    return f"""<!DOCTYPE html>
<html lang="bn" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_txt(page_title)}</title>
  <meta name="description" content="{escape_txt(meta_desc)}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:site_name" content="Bibyutatsu BookStore">
  <meta property="og:title" content="{name_bn} ({name_en}) Ebooks">
  <meta property="og:description" content="{escape_txt(meta_desc)}">
  <meta property="og:type" content="profile">
  <meta property="og:url" content="{canonical_url}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  {json_ld}
  {GA_SCRIPT}
  <style>{SHARED_CSS}</style>
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="{root_rel}" class="brand">
        <span class="brand-icon">📚</span>
        <span>Bibyutatsu BookStore</span>
      </a>
      <nav class="header-nav">
        <a href="{root_rel}" class="nav-btn">← Back to Full Library</a>
      </nav>
    </div>
  </header>

  <main class="container" style="padding-top: 30px; padding-bottom: 60px;">
    <div class="breadcrumbs">
      <a href="{root_rel}">Home</a> /
      <span>Authors</span> /
      <span>{name_bn}</span>
    </div>

    <div style="margin-bottom: 30px; padding: 24px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);">
      <h1 style="font-size: 2.2rem; color: var(--heading); margin-bottom: 6px;">{name_bn}</h1>
      <div style="font-size: 1.1rem; color: var(--text-muted); margin-bottom: 14px;">{name_en}</div>
      <div class="badges-row">
        <span class="badge" style="background: var(--accent)22; color: var(--accent); border-color: var(--accent)44; font-weight: 700;">
          {total_books} Books Available
        </span>
        {f'<span class="badge">Aliases: {", ".join(aliases)}</span>' if aliases else ''}
      </div>
      {f'''
      <div style="margin-top: 18px;">
        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Similar Authors:</div>
        <div class="badges-row">{"".join(similar_html)}</div>
      </div>
      ''' if similar_html else ''}
    </div>

    <h2 class="section-heading"><span>📖</span> Available Books ({total_books})</h2>
    <div class="related-grid" style="grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));">
      {"".join(cards_html)}
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <div>Bibyutatsu BookStore — Free open-access Bengali literature digital library.</div>
    </div>
  </footer>
</body>
</html>
"""


def render_series_page(series_info: dict, books: list[dict], root_rel: str = "../") -> str:
    """Renders a series hub page with canonical reading order."""
    slug = series_info["slug"]
    name_bn = escape_txt(series_info["name_bn"])
    name_en = escape_txt(series_info["name_en"])
    author_bn = escape_txt(series_info.get("author", ""))
    author_en = escape_txt(series_info.get("author_en", ""))
    total_books = series_info["total_books"]
    canonical_url = f"{BASE_URL}series/{slug}.html"

    page_title = f"{name_bn} ({name_en}) Series Ebooks Download | Bibyutatsu BookStore"
    meta_desc = f"Complete reading order and free downloads for {total_books} books in the {name_bn} ({name_en}) series by {author_bn} in EPUB, Kindle KFX, MOBI & PDF."

    cards_html = []
    for idx, b in enumerate(books, start=1):
        b_id = b["id"]
        b_title = escape_txt(b["title"])
        b_cover = b.get("cover")
        b_cover_img = f'<img src="{root_rel}{b_cover}" alt="{b_title}" class="mini-cover" loading="lazy" />' if b_cover else '<div class="mini-cover" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:0.75rem;">No Cover</div>'
        fmts = "".join(f'<span class="badge" style="font-size:0.65rem;padding:2px 5px;">{f.upper()}</span>' for f in b.get("formats", {}).keys())
        cards_html.append(f"""
          <a href="{root_rel}book/{b_id}.html" class="mini-book-card">
            <div style="font-size:0.75rem;font-weight:700;color:var(--accent);">#{idx}</div>
            {b_cover_img}
            <div class="mini-title">{b_title}</div>
            <div class="badges-row" style="margin-top:auto;">{fmts}</div>
          </a>
        """)

    schema_series = {
        "@context": "https://schema.org",
        "@type": "Series",
        "name": series_info["name_bn"],
        "alternateName": series_info["name_en"],
        "author": {
            "@type": "Person",
            "name": series_info.get("author", "")
        },
        "url": canonical_url
    }

    json_ld = f"""
    <script type="application/ld+json">
    {json.dumps(schema_series, ensure_ascii=False, indent=2)}
    </script>
    """

    return f"""<!DOCTYPE html>
<html lang="bn" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_txt(page_title)}</title>
  <meta name="description" content="{escape_txt(meta_desc)}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:site_name" content="Bibyutatsu BookStore">
  <meta property="og:title" content="{name_bn} ({name_en}) Series">
  <meta property="og:description" content="{escape_txt(meta_desc)}">
  <meta property="og:type" content="books.series">
  <meta property="og:url" content="{canonical_url}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  {json_ld}
  {GA_SCRIPT}
  <style>{SHARED_CSS}</style>
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="{root_rel}" class="brand">
        <span class="brand-icon">📚</span>
        <span>Bibyutatsu BookStore</span>
      </a>
      <nav class="header-nav">
        <a href="{root_rel}" class="nav-btn">← Back to Full Library</a>
      </nav>
    </div>
  </header>

  <main class="container" style="padding-top: 30px; padding-bottom: 60px;">
    <div class="breadcrumbs">
      <a href="{root_rel}">Home</a> /
      <span>Series</span> /
      <span>{name_bn}</span>
    </div>

    <div style="margin-bottom: 30px; padding: 24px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);">
      <h1 style="font-size: 2.2rem; color: var(--heading); margin-bottom: 6px;">{name_bn} Series</h1>
      <div style="font-size: 1.1rem; color: var(--text-muted); margin-bottom: 14px;">{name_en} · By {author_bn} ({author_en})</div>
      <div class="badges-row">
        <span class="badge series-badge" style="font-weight: 700;">
          ⚡ {total_books} Books in Series
        </span>
      </div>
    </div>

    <h2 class="section-heading"><span>📚</span> Canonical Reading Order ({total_books} Books)</h2>
    <div class="related-grid" style="grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));">
      {"".join(cards_html)}
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <div>Bibyutatsu BookStore — Dedicated to preserving Bengali literature.</div>
    </div>
  </footer>
</body>
</html>
"""


def generate_all_pages(catalog_path: str, output_root: str):
    """
    Main entrypoint:
    Generates all /book/*.html, /author/*.html, and /series/*.html files.
    """
    out_root = Path(output_root)
    book_dir = out_root / "book"
    author_dir = out_root / "author"
    series_dir = out_root / "series"

    book_dir.mkdir(parents=True, exist_ok=True)
    author_dir.mkdir(parents=True, exist_ok=True)
    series_dir.mkdir(parents=True, exist_ok=True)

    print(f"Initializing Analytics & Similarity Engine for {catalog_path}...")
    engine = AnalyticsEngine(catalog_path)
    engine.export_graph(out_root / "analytics")

    books = engine.books
    authors_data = engine.compute_author_analytics()
    series_data = engine.compute_series_analytics()

    # 1. Generate Book Pages
    print(f"Generating {len(books)} static book pages in {book_dir}...")
    for b in books:
        b_id = b["id"]
        rel = engine.get_related_books(b_id, limit=6)
        a_slug = engine.author_slugs.get(b.get("author"), slugify(b.get("author"), max_len=50))
        html_content = render_book_page(b, rel, author_slug=a_slug, root_rel="../")
        page_file = book_dir / f"{b_id}.html"
        with open(page_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"✓ Generated {len(books)} book pages successfully.")

    # 2. Generate Author Pages (for all authors with at least 1 book)
    print(f"Generating {len(authors_data)} static author pages in {author_dir}...")
    for slug, a_info in authors_data.items():
        author_books = [engine.books_by_id[bid] for bid in a_info["book_ids"] if bid in engine.books_by_id]
        html_content = render_author_page(a_info, author_books, root_rel="../")
        page_file = author_dir / f"{slug}.html"
        with open(page_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"✓ Generated {len(authors_data)} author pages successfully.")

    # 3. Generate Series Pages
    print(f"Generating {len(series_data)} static series pages in {series_dir}...")
    for s_id, s_info in series_data.items():
        s_books = [engine.books_by_id[bid] for bid in s_info["book_ids"] if bid in engine.books_by_id]
        html_content = render_series_page(s_info, s_books, root_rel="../")
        page_file = series_dir / f"{s_info['slug']}.html"
        with open(page_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"✓ Generated {len(series_data)} series pages successfully.")
    print(f"🎉 Total static SEO landing pages generated: {len(books) + len(authors_data) + len(series_data)}")


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent.parent
    cat_file = root_dir / "catalog.json"
    generate_all_pages(str(cat_file), str(root_dir))
