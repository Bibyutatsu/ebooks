# Walkthrough: Bibyutatsu Ebooks Library Architecture & Deployment

The free, search-first Bengali digital library has been built, tested, and deployed to **[https://bibyutatsu.github.io/ebooks](https://bibyutatsu.github.io/ebooks)**.

---

## 🚀 Live Endpoints & Repositories

- **Live Web Application**: [https://bibyutatsu.github.io/ebooks](https://bibyutatsu.github.io/ebooks)
- **GitHub Repository**: [https://github.com/Bibyutatsu/ebooks](https://github.com/Bibyutatsu/ebooks)
- **Local Project Path**: `ebooks/`

---

## 📦 What Was Delivered

### 1. Ingestion & Metadata Normalization Pipeline
- **Script**: [`tools/build_catalog.py`](tools/build_catalog.py)
- **Processed**: Scanned all 178 author directories and normalized **1,238 distinct books**.
- **Multi-Format Indexing**: Indexed 1,119 EPUBs, 1,102 Kindle KFX, 9 TXT, 6 MOBI, and 1 PDF.
- **Cover Image Optimization**: Batch compressed 1,231 `.jpg` covers into modern `.webp` thumbnails (`assets/covers/`), reducing the cover assets payload from 73 MB to **25 MB**.
- **Metadata Output**: Schema-validated, compact [`catalog.json`](catalog.json) (2.4 MB) containing precomputed search tokens, genres, series, authors, and format sizes.

### 2. Dual-Script Transliteration & Character Intelligence
- **Transliteration Engine**: [`tools/transliteration.py`](tools/transliteration.py) converts Bengali Unicode to Avro/ITRANS phonetic Romanizations with inherent vowel permutations (`o`/`a`), conjunct resolution, and numeral mapping.
- **Author Mapping**: [`tools/author_mapping.py`](tools/author_mapping.py) standardizes all 173 authors with English aliases, canonical Bengali names, and default genres.
- **Iconic Series Detector**: [`tools/series_mapping.py`](tools/series_mapping.py) automatically identifies and tags prominent Bengali literary characters:
  - Feluda (ফেলুদা), Byomkesh Bakshi (ব্যোমকেশ), Prof. Shonku (শঙ্কু), Kakababu (কাকাবাবু), Masud Rana (মাসুদ রানা), Tin Goyenda (তিন গোয়েন্দা), Tenida (টেনিদা), Ghanada (ঘনাদা), Rijuda (রিজুদা), Himu (হিমু), Misir Ali (মিসির আলি), Shuvro (শুভ্র), Tintin (টিনটিন), Sherlock Holmes (শার্লক), Kiriti Roy (কিরীটী), Shabor (শবর).

### 3. Verification Layer & Test Suite
- **Test Runner**: [`tests/verify_catalog.py`](tests/verify_catalog.py)
- **Integrity Checks**: Validates schema completeness, non-zero file sizes, format fields, and uniqueness of all 1,238 book IDs.
- **Search Benchmarks**: Validates **46 curated query test cases** across English transliterations, typos/colloquial spellings, and Bengali Unicode with Levenshtein distance $\le 2$:
  - `feluda` $\rightarrow$ 56 matches
  - `byomkesh` / `bomkesh` $\rightarrow$ 30 matches
  - `humayun ahmed` / `humayan` $\rightarrow$ 211 matches
  - `satyajit ray` / `roy` $\rightarrow$ 56 matches
  - `chander pahar` $\rightarrow$ 24 matches
  - `sharadindu banerjee` $\rightarrow$ 29 matches
  - `sunil ganguly` $\rightarrow$ 34 matches
  - `tin goyenda` $\rightarrow$ 8 matches
  - `masud rana` $\rightarrow$ 37 matches
  - `agatha christie` $\rightarrow$ 19 matches
  - `jules verne` $\rightarrow$ 18 matches
  - **Benchmark Score**: **46/46 Passed (100.0% Recall)**.

### 4. High-Performance Glassmorphic Web App
- **HTML/CSS/JS**: [`index.html`](index.html), [`style.css`](style.css), [`app.js`](app.js)
- **Design System**: Matches Bibhash's dev portfolio styling with dark/light mode toggle, glowing ambient mesh, and Google Fonts (`Outfit`, `Inter`, `Hind Siliguri`).
- **Interactive UI**:
  - Instant dual-script search with clear button and quick-tag suggestion chips.
  - Interactive genre filter pills with live counts.
  - Multi-format filter pills (`All`, `EPUB`, `Kindle KFX`, `PDF`, `MOBI`).
  - Searchable author dropdown with book count badges.
  - Responsive book grid with lazy-loaded WebP covers, series tags, and format badges.
  - Book Detail Modal with high-res cover, synopsis, author bio link, format download cards, and reader guide.
  - URL parameter synchronization (`?q=feluda&genre=thriller`).

### 5. Scalable Free Hosting & CDN Releases
- **Frontend**: Hosted for free on GitHub Pages at `https://bibyutatsu.github.io/ebooks/`.
- **Distribution Tool**: [`tools/sync_releases.py`](tools/sync_releases.py) incrementally uploads book assets to GitHub Releases (`v1.0-batch-01`, etc.) using clean ASCII slugs, bypassing Git repository bloat and GitHub Pages bandwidth limits.
- **Verified Direct CDN Download**: Tested asset `humayun-ahmed-rupa.epub` on GitHub Release `v1.0-batch-01` returning `HTTP/2 200` directly from `release-assets.githubusercontent.com`.

---

## 📋 Verification Results Summary

| Verification Suite | Target | Status | Result |
| :--- | :--- | :--- | :--- |
| **Catalog Schema & Integrity** | 1,238 books, 173 authors | **PASSED** | 100% compliant, 0 duplicates |
| **Transliteration & Fuzzy Benchmarks** | 46 English & Bengali queries | **PASSED** | 46/46 passed (100% recall) |
| **Web Server Routes** | `index.html`, `style.css`, `app.js`, `catalog.json` | **PASSED** | `HTTP/2 200 OK` on live GitHub Pages |
| **Direct CDN Asset Download** | Release asset download URL | **PASSED** | `HTTP/2 200 OK` (signed GitHub CDN) |

---

## 🔄 Future Scaling Workflow

When new books are added in the future:
```bash
# 1. Rebuild catalog and convert new covers
python3 tools/build_catalog.py --downloads ../downloads --output .

# 2. Run verification suite
python3 tests/verify_catalog.py ./catalog.json

# 3. Upload new assets to GitHub Releases
python3 tools/sync_releases.py --catalog ./catalog.json

# 4. Push updated catalog
git add catalog.json assets/covers/
git commit -m "feat: sync new books to catalog"
git push origin main
```
