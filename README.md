# Bibyutatsu Ebooks Library 📚

[![GitHub Pages](https://img.shields.io/badge/Hosted%20On-GitHub%20Pages-blue?logo=github)](https://bibyutatsu.github.io/ebooks)
[![Books Count](https://img.shields.io/badge/Catalog-2%2C907%20Books-emerald)](https://bibyutatsu.github.io/ebooks)
[![Formats](https://img.shields.io/badge/Formats-EPUB%20%7C%20KFX%20%7C%20PDF%20%7C%20MOBI-purple)](https://bibyutatsu.github.io/ebooks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An open-access, modern digital library for 2,900+ Bengali literary classics, historical manuscripts, thrillers, sci-fi, philosophical works, and translations. Features instant client-side dual-script search (English romanized transliteration or বাংলা Unicode), author/genre filters, cover galleries, and direct multi-format downloads.

Live Endpoint: **[https://bibyutatsu.github.io/ebooks](https://bibyutatsu.github.io/ebooks)**

---

## 🌟 Key Features

- **Dual-Script Transliteration Search**: Search Bengali titles, characters, and authors effortlessly in English phonetics (`feluda`, `sonar kella`, `byomkesh`, `humayun ahmed`, `shonku`, `kakababu`, `vidyasagar`, `abanindranath`, `rabindranath`, `nazrul`) or native Bengali (`ফেলুদা`, `ব্যোমকেশ`, `হুমায়ূন আহমেদ`, `ঈশ্বরচন্দ্র বিদ্যাসাগর`, `রবীন্দ্রনাথ ঠাকুর`).
- **Typo-Tolerant Fuzzy Matching**: Built-in Levenshtein fuzzy matching handles spelling variations like `bomkesh`, `humayan`, or `atin babu`.
- **Multi-Format Support**: Direct downloads in `.epub`, Amazon Kindle `.kfx`, `.mobi`, and `.pdf`.
- **Optimized Cover Gallery**: 2,900+ covers converted into lightweight WebP thumbnails with skeleton loaders.
- **Glassmorphic Aesthetic**: Matches Bibhash's dev portfolio styling with dark/light mode toggle.
- **100% Free Hosting**: Hosted completely on GitHub Pages with downloads distributed via GitHub Releases CDN and direct upstream preservation mirrors.

---

## 🛠️ Architecture & Tooling

```
ebooks/
├── index.html            # Main library web interface
├── style.css             # Glassmorphic CSS design system
├── app.js                # Search, filtering, and modal interaction logic
├── catalog.json          # Normalized catalog & pre-computed search index (~2,907 books)
├── assets/
│   └── covers/           # 2,900+ optimized WebP cover thumbnails
├── tools/
│   ├── build_catalog.py  # Ingestion pipeline: extracts OPF metadata, converts covers, builds catalog.json
│   ├── transliteration.py# Bengali phonetic transliterator (Avro & ITRANS rules)
│   ├── author_mapping.py # Author canonicalization, English aliases, and genres (420+ authors)
│   ├── series_mapping.py # Automatic character & series detector
│   ├── sync_releases.py  # Incremental GitHub Releases uploader for scalable book distribution
│   ├── eboipotro/        # OPDS Atom ingestion pipeline for curated Bengali EPUBs
│   │   └── sync_eboipotro.py
│   ├── wikisource/       # MediaWiki category harvester & ws-export dynamic EPUB pipeline
│   │   ├── sync_wikisource.py
│   │   └── works_list.json
│   ├── archive_org/      # Internet Archive Bengali public domain text harvester
│   │   ├── sync_archive_org.py
│   │   └── ia_catalog.json
│   ├── bongboi/          # Ingestion toolchain for classical Bengali EPUBs
│   │   ├── sync_bongboi.py
│   │   └── books_metadata.json
│   └── kindlebangla/     # Scraper & verification toolchain specialized for KindleBangla
│       ├── downloader.py
│       ├── verify_downloads.py
│       ├── book_details_links.json
│       └── books_metadata.json
└── tests/
    └── verify_catalog.py # Automated test suite (schema integrity + 53 search benchmarks)
```

---

## 🛠️ Ingestion Toolchains

### 1. Eboipotro Toolchain (`tools/eboipotro/`)
Harvests curated Bengali EPUBs from the [eboipotro/eboipotro.github.io](https://eboipotro.github.io) OPDS feed with direct GitHub raw downloads and embedded metadata extraction:
```bash
python3 tools/eboipotro/sync_eboipotro.py --catalog ./catalog.json
```

### 2. Bengali Wikisource Toolchain (`tools/wikisource/`)
Discovers out-of-copyright classical Bengali texts from [bn.wikisource.org](https://bn.wikisource.org) and links directly to Wikimedia Cloud on-demand `ws-export` EPUB engines:
```bash
python3 tools/wikisource/sync_wikisource.py --enumerate-only
python3 tools/wikisource/sync_wikisource.py --catalog ./catalog.json
```

### 3. Internet Archive Toolchain (`tools/archive_org/`)
Queries the [Internet Archive](https://archive.org) for digitized historical and public domain Bengali texts, preserving original IA download and item detail URLs:
```bash
python3 tools/archive_org/sync_archive_org.py --fetch-only --limit 500
python3 tools/archive_org/sync_archive_org.py --catalog ./catalog.json
```

### 4. BongBoi Repository Toolchain (`tools/bongboi/`)
Ingests classical out-of-copyright Bengali literature curated by [eedeidk/bongboi](https://github.com/eedeidk/bongboi):
```bash
python3 tools/bongboi/sync_bongboi.py
```

### 5. KindleBangla Scraper Toolchain (`tools/kindlebangla/`)
Specialized scripts used to harvest and verify Kindle-formatted Bengali ebooks from [KindleBangla](https://www.kindlebangla.com):
```bash
python3 tools/kindlebangla/downloader.py
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
- Schema completeness for 100% of books (3,736 books across 1,005 authors)
- Non-zero file sizes and valid format specifications
- 53 benchmark queries across iconic Bengali characters, authors, classical pioneers, and world translations

---

## 🙏 Acknowledgements & Contributing Remarks

- **[Eboipotro (ই-বইপত্র)](https://eboipotro.github.io)**: Sincere gratitude to the Eboipotro team for their open-source OPDS catalog and meticulously formatted Bengali digital EPUB publications.
- **[Bengali Wikisource (উইকিসংকলন)](https://bn.wikisource.org)**: Tremendous appreciation to the Wikimedia and Bengali Wikisource volunteers for their tireless efforts in digitizing and transcribing thousands of public domain Bengali literary texts.
- **[Internet Archive](https://archive.org)**: Deep thanks to the Internet Archive for providing open digital preservation and access to historical Bengali texts, manuscripts, and literature.
- **[BongBoi](https://github.com/eedeidk/bongboi)**: Tremendous gratitude to the creators and maintainers of the **[BongBoi](https://github.com/eedeidk/bongboi)** repository (and the associated [Telegram community](https://t.me/bongboi)) for curating, typesetting, and preserving rare, out-of-copyright Bengali historical manuscripts and literary treasures.
- **[KindleBangla](https://www.kindlebangla.com)**: Heartfelt thanks and gratitude to KindleBangla and its community for digitizing, formatting, and preserving a vast contemporary and classic collection of Bengali literature and making it freely accessible to readers worldwide.
