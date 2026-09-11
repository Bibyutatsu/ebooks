# Bibyutatsu Ebooks Library 📚

[![GitHub Pages](https://img.shields.io/badge/Hosted%20On-GitHub%20Pages-blue?logo=github)](https://bibyutatsu.github.io/ebooks)
[![Books Count](https://img.shields.io/badge/Catalog-1%2C238%20Books-emerald)](https://bibyutatsu.github.io/ebooks)
[![Formats](https://img.shields.io/badge/Formats-EPUB%20%7C%20KFX%20%7C%20PDF%20%7C%20MOBI-purple)](https://bibyutatsu.github.io/ebooks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An open-access, modern digital library for 1,200+ Bengali literary classics, thrillers, sci-fi, and translations. Features instant client-side dual-script search (English romanized transliteration or বাংলা Unicode), author/genre filters, cover galleries, and direct multi-format downloads.

Live Endpoint: **[https://bibyutatsu.github.io/ebooks](https://bibyutatsu.github.io/ebooks)**

---

## 🌟 Key Features

- **Dual-Script Transliteration Search**: Search Bengali titles, characters, and authors effortlessly in English phonetics (`feluda`, `sonar kella`, `byomkesh`, `humayun ahmed`, `shonku`, `kakababu`) or native Bengali (`ফেলুদা`, `ব্যোমকেশ`, `হুমায়ূন আহমেদ`).
- **Typo-Tolerant Fuzzy Matching**: Built-in Levenshtein fuzzy matching handles spelling variations like `bomkesh`, `humayan`, or `atin babu`.
- **Multi-Format Support**: Direct downloads in `.epub`, Amazon Kindle `.kfx`, `.mobi`, and `.pdf`.
- **Optimized Cover Gallery**: 1,230+ covers converted into lightweight WebP thumbnails with skeleton loaders.
- **Glassmorphic Aesthetic**: Matches Bibhash's dev portfolio styling with dark/light mode toggle.
- **100% Free Hosting**: Hosted completely on GitHub Pages with downloads distributed via GitHub Releases CDN.

---

## 🛠️ Architecture & Tooling

```
ebooks/
├── index.html            # Main library web interface
├── style.css             # Glassmorphic CSS design system
├── app.js                # Search, filtering, and modal interaction logic
├── catalog.json          # Normalized catalog & pre-computed search index (~1,238 books)
├── assets/
│   └── covers/           # 1,230+ optimized WebP cover thumbnails (~25MB total)
├── tools/
│   ├── build_catalog.py  # Ingestion pipeline: extracts OPF metadata, converts covers, builds catalog.json
│   ├── transliteration.py# Bengali phonetic transliterator (Avro & ITRANS rules)
│   ├── author_mapping.py # Author canonicalization, English aliases, and genres
│   ├── series_mapping.py # Automatic character & series detector
│   ├── sync_releases.py  # Incremental GitHub Releases uploader for scalable book distribution
│   └── kindlebangla/     # Scraper & verification toolchain specialized for KindleBangla
│       ├── downloader.py          # Scrapes book links, covers, and media files
│       ├── verify_downloads.py    # Extracts .rar archives & validates downloads
│       ├── book_details_links.json# Sitemap index of book detail URLs
│       └── books_metadata.json    # Original ingested metadata dump
└── tests/
    └── verify_catalog.py # Automated test suite (schema integrity + 46 search benchmarks)
```

---

## 🛠️ KindleBangla Scraper Toolchain

Specialized scripts and metadata artifacts originally used to harvest and verify downloads from [KindleBangla](https://www.kindlebangla.com):

```bash
# 1. Scrape catalog and download book files
python3 tools/kindlebangla/downloader.py

# 2. Extract nested .rar archives and verify file integrity
python3 tools/kindlebangla/verify_downloads.py
```

---

## 🚀 Adding New Books in the Future

The ingestion pipeline is designed to be idempotent and scalable:

1. Place new book folders into your raw downloads directory:
   ```bash
   downloads/<Author>/<Title>/<Title - Author.epub>
   ```
2. Run the catalog builder:
   ```bash
   python3 tools/build_catalog.py --downloads ../downloads --output .
   ```
3. Run the verification test suite:
   ```bash
   python3 tests/verify_catalog.py ./catalog.json
   ```
4. Sync new assets to GitHub Releases:
   ```bash
   python3 tools/sync_releases.py --catalog ./catalog.json
   ```
5. Commit and push the updated `catalog.json` and cover assets:
   ```bash
   git add catalog.json assets/covers/
   git commit -m "feat: add new books to catalog"
   git push origin main
   ```

---

## 🧪 Verification & Test Suite

Run the automated verification suite:
```bash
python3 tests/verify_catalog.py ./catalog.json
```
Checks:
- Schema completeness for 100% of books
- Non-zero file sizes and valid formats
- 46 benchmark queries across iconic Bengali characters, authors, and world translations

---

## 🙏 Acknowledgements

Heartfelt thanks and gratitude to **[KindleBangla](https://www.kindlebangla.com)** and its community for digitizing, formatting, and preserving this rich collection of Bengali literature and making it freely accessible to readers worldwide.

