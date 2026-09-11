# Bibyutatsu Ebooks Library 📚

[![GitHub Pages](https://img.shields.io/badge/Hosted%20On-GitHub%20Pages-blue?logo=github)](https://bibyutatsu.github.io/ebooks)
[![Books Count](https://img.shields.io/badge/Catalog-1%2C439%20Books-emerald)](https://bibyutatsu.github.io/ebooks)
[![Formats](https://img.shields.io/badge/Formats-EPUB%20%7C%20KFX%20%7C%20PDF%20%7C%20MOBI-purple)](https://bibyutatsu.github.io/ebooks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An open-access, modern digital library for 1,400+ Bengali literary classics, historical manuscripts, thrillers, sci-fi, and translations. Features instant client-side dual-script search (English romanized transliteration or বাংলা Unicode), author/genre filters, cover galleries, and direct multi-format downloads.

Live Endpoint: **[https://bibyutatsu.github.io/ebooks](https://bibyutatsu.github.io/ebooks)**

---

## 🌟 Key Features

- **Dual-Script Transliteration Search**: Search Bengali titles, characters, and authors effortlessly in English phonetics (`feluda`, `sonar kella`, `byomkesh`, `humayun ahmed`, `shonku`, `kakababu`, `vidyasagar`, `abanindranath`) or native Bengali (`ফেলুদা`, `ব্যোমকেশ`, `হুমায়ূন আহমেদ`, `ঈশ্বরচন্দ্র বিদ্যাসাগর`).
- **Typo-Tolerant Fuzzy Matching**: Built-in Levenshtein fuzzy matching handles spelling variations like `bomkesh`, `humayan`, or `atin babu`.
- **Multi-Format Support**: Direct downloads in `.epub`, Amazon Kindle `.kfx`, `.mobi`, and `.pdf`.
- **Optimized Cover Gallery**: 1,430+ covers converted into lightweight WebP thumbnails with skeleton loaders.
- **Glassmorphic Aesthetic**: Matches Bibhash's dev portfolio styling with dark/light mode toggle.
- **100% Free Hosting**: Hosted completely on GitHub Pages with downloads distributed via GitHub Releases CDN.

---

## 🛠️ Architecture & Tooling

```
ebooks/
├── index.html            # Main library web interface
├── style.css             # Glassmorphic CSS design system
├── app.js                # Search, filtering, and modal interaction logic
├── catalog.json          # Normalized catalog & pre-computed search index (~1,439 books)
├── assets/
│   └── covers/           # 1,430+ optimized WebP cover thumbnails (~28MB total)
├── tools/
│   ├── build_catalog.py  # Ingestion pipeline: extracts OPF metadata, converts covers, builds catalog.json
│   ├── transliteration.py# Bengali phonetic transliterator (Avro & ITRANS rules)
│   ├── author_mapping.py # Author canonicalization, English aliases, and genres (270+ authors)
│   ├── series_mapping.py # Automatic character & series detector
│   ├── sync_releases.py  # Incremental GitHub Releases uploader for scalable book distribution
│   ├── bongboi/          # Ingestion toolchain and metadata for out-of-copyright classical Bengali EPUBs
│   │   ├── sync_bongboi.py        # Ingestion script: cover generation/extraction & metadata indexing
│   │   └── books_metadata.json    # Dump of all 216 ingested BongBoi classical ebooks
│   └── kindlebangla/     # Scraper & verification toolchain specialized for KindleBangla
│       ├── downloader.py          # Scrapes book links, covers, and media files
│       ├── verify_downloads.py    # Extracts .rar archives & validates downloads
│       ├── book_details_links.json# Sitemap index of book detail URLs
│       └── books_metadata.json    # Original ingested metadata dump
└── tests/
    └── verify_catalog.py # Automated test suite (schema integrity + 53 search benchmarks)
```

---

## 🛠️ Ingestion Toolchains

### 1. BongBoi Repository Toolchain (`tools/bongboi/`)
Used to ingest, canonicalize, and extract/generate covers for out-of-copyright classical Bengali literature curated by [eedeidk/bongboi](https://github.com/eedeidk/bongboi):

```bash
# Ingest books, canonicalize authors, generate/extract WebP covers, and update catalog.json
python3 tools/bongboi/sync_bongboi.py
```

### 2. KindleBangla Scraper Toolchain (`tools/kindlebangla/`)
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
- Schema completeness for 100% of books (1,439 books across 271 authors)
- Non-zero file sizes and valid formats
- 53 benchmark queries across iconic Bengali characters, authors, classical pioneers, and world translations

---

## 🙏 Acknowledgements & Contributing Remarks

- **[BongBoi](https://github.com/eedeidk/bongboi)**: Tremendous gratitude to the creators and maintainers of the **[BongBoi](https://github.com/eedeidk/bongboi)** repository (and the associated [Telegram community](https://t.me/bongboi)) for curating, typesetting, and preserving rare, out-of-copyright Bengali historical manuscripts and literary treasures (including works by Ishwar Chandra Vidyasagar, Abanindranath Tagore, Michael Madhusudan Dutt, Begum Rokeya, Rakhaldas Bandyopadhyay, and many more).
- **[KindleBangla](https://www.kindlebangla.com)**: Heartfelt thanks and gratitude to KindleBangla and its community for digitizing, formatting, and preserving a vast contemporary and classic collection of Bengali literature and making it freely accessible to readers worldwide.

