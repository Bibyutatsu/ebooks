"""
Batch-resolves real authors for Bengali Wikisource works in catalog.json
by querying MediaWiki category metadata (বিষয়শ্রেণী:<লেখক> রচিত / অনূদিত / সম্পাদিত).
Regenerates authentic typographic covers and re-indexes search tokens.
"""

import sys, re, io, json, time, hashlib, unicodedata
from pathlib import Path
from urllib.parse import quote
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))

from author_mapping import get_author_info, find_author_match
from series_mapping import detect_series
from transliteration import transliterate_text
from build_catalog import slugify

WS_API = "https://bn.wikisource.org/w/api.php"
UA = "BibyutatsuEbooks/1.0 (+https://bibyutatsu.github.io/ebooks)"
COVERS_DIR = ROOT_DIR / "assets" / "covers"
CATALOG_PATH = ROOT_DIR / "catalog.json"
CACHE_PATH = ROOT_DIR / "tools" / "wikisource" / "resolved_authors.json"

def norm(s): return unicodedata.normalize("NFC", s.strip()) if s else ""
def norm_bn(s):
    s = s.replace("\u09af\u09bc", "\u09df").replace("\u09a1\u09bc", "\u09dc").replace("\u09a2\u09bc", "\u09dd")
    return s.strip().lower()

def generate_cover_image(title, author, out_path, width=300, height=450):
    palettes = [
        ((15,23,42),(30,41,59),(56,189,248)), ((19,24,39),(31,41,55),(251,146,60)),
        ((24,24,27),(39,39,42),(167,139,250)), ((17,24,39),(31,41,55),(52,211,153)),
        ((30,27,75),(49,46,129),(244,114,182)), ((20,30,45),(15,60,90),(250,204,21)),
        ((26,20,46),(45,30,80),(99,210,180)), ((39,25,55),(60,40,90),(255,200,80)),
    ]
    h = int(hashlib.md5(f"{title}{author}".encode()).hexdigest()[:6], 16)
    bg1, bg2, accent = palettes[h % len(palettes)]
    img = Image.new("RGB", (width, height), bg1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        f = y / height
        draw.line([(0,y),(width,y)], fill=(int(bg1[0]*(1-f)+bg2[0]*f), int(bg1[1]*(1-f)+bg2[1]*f), int(bg1[2]*(1-f)+bg2[2]*f)))
    draw.rectangle([14,14,width-14,height-14], outline=accent, width=1)
    draw.line([6,0,6,height], fill=(255,255,255,40), width=2)
    draw.rectangle([width-60, height-28, width-10, height-8], fill=(30,40,60), outline=accent, width=1)
    fp = "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc"
    try:
        ft = ImageFont.truetype(fp, 22); fa = ImageFont.truetype(fp, 15); fo = ImageFont.truetype(fp, 11)
    except:
        ft = fa = fo = ImageFont.load_default()
    draw.text((width/2, 70), "✦ উইকিসংকলন ✦", fill=accent, font=fo, anchor="mm")
    words = title.split(); lines, curr = [], []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 15:
            lines.append(" ".join(curr[:-1]) if len(curr)>1 else w); curr = [w] if len(curr)>1 else []
    if curr: lines.append(" ".join(curr))
    if not lines: lines = [title]
    sy = height/2 - len(lines)*16
    for i, line in enumerate(lines):
        draw.text((width/2, sy+i*30), line, fill=(245,245,245), font=ft, anchor="mm")
    draw.text((width/2, height-70), author, fill=accent, font=fa, anchor="mm")
    draw.text((width-35, height-18), "WS", fill=accent, font=fo, anchor="mm")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=82)

def fetch_categories_batch(wiki_titles):
    """Fetches categories for a list of wiki titles in chunks of 50."""
    mapping = {}
    chunk_size = 50
    for i in range(0, len(wiki_titles), chunk_size):
        chunk = wiki_titles[i:i + chunk_size]
        titles_param = "|".join([f"রচনা:{t}" if not t.startswith("রচনা:") else t for t in chunk])
        params = {
            "action": "query",
            "titles": titles_param,
            "prop": "categories",
            "cllimit": 500,
            "format": "json"
        }
        try:
            r = requests.post(WS_API, data=params, headers={"User-Agent": UA}, timeout=15)
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                t = p.get("title", "")
                pure_title = t.split(":", 1)[1] if ":" in t else t
                cats = [c["title"] for c in p.get("categories", [])]
                
                # Check for author category
                author_found = None
                for c in cats:
                    # e.g., 'বিষয়শ্রেণী:রবীন্দ্রনাথ ঠাকুর রচিত'
                    m = re.match(r"^বিষয়শ্রেণী:(.+?)\s+(রচিত|অনূদিত|সম্পাদিত)$", c)
                    if m:
                        author_found = m.group(1).strip()
                        break
                
                mapping[pure_title] = author_found
        except Exception as e:
            print(f"[WARN] Error fetching batch {i}: {e}")
        time.sleep(0.3)
    return mapping

def main():
    print(f"Loading catalog from {CATALOG_PATH}...")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    # Load cache if available
    cached_authors = {}
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                cached_authors = json.load(f)
            print(f"Loaded {len(cached_authors)} cached author attributions.")
        except Exception:
            pass

    ws_books = [b for b in catalog["books"] if b.get("source") == "wikisource"]
    print(f"Total Wikisource books in catalog: {len(ws_books)}")

    # Determine titles that need author lookup
    titles_to_query = []
    for b in ws_books:
        title = b["title"]
        if title not in cached_authors:
            titles_to_query.append(title)

    if titles_to_query:
        print(f"Querying MediaWiki category API for {len(titles_to_query)} titles...")
        new_authors = fetch_categories_batch(titles_to_query)
        cached_authors.update(new_authors)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cached_authors, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(cached_authors)} author attributions to cache.")

    # Track IDs to guarantee uniqueness
    seen_ids = set(b["id"] for b in catalog["books"] if b.get("source") != "wikisource")
    
    resolved_count = 0
    anonymous_count = 0
    covers_regenerated = 0

    for b in ws_books:
        clean_title = b["title"]
        raw_author = cached_authors.get(clean_title)

        if raw_author:
            # Match canonical author
            author_info = get_author_info(raw_author, raw_author)
            clean_author = author_info.get("canonical_bn", raw_author)
            author_en = author_info.get("en", "Author")
            author_aliases = author_info.get("aliases", [author_en])
            default_genres = author_info.get("default_genres", ["ক্লাসিক ও সাহিত্য (Classics)"])
            resolved_count += 1
        else:
            # Retain unknown if no category found
            clean_author = "অজ্ঞাত"
            author_en = "Anonymous"
            author_aliases = ["Anonymous", "Unknown Author", "Unknown"]
            default_genres = ["ক্লাসিক ও সাহিত্য (Classics)"]
            anonymous_count += 1

        # Calculate slugs and new unique ID
        title_translit = transliterate_text(clean_title)
        title_en = title_translit[0].title() if title_translit else clean_title
        base_id = slugify(f"{author_en}-{title_en}") or f"ws-{clean_title}"
        book_id = base_id
        counter = 2
        while book_id in seen_ids:
            book_id = f"{base_id}-{counter}"
            counter += 1
        seen_ids.add(book_id)

        # Remove old cover if ID changed
        old_cover = ROOT_DIR / b.get("cover", "")
        new_cover_file = COVERS_DIR / f"{book_id}.webp"
        
        # Regenerate cover with authentic author name
        generate_cover_image(clean_title, clean_author, new_cover_file)
        covers_regenerated += 1
        if old_cover != new_cover_file and old_cover.exists() and "anonymous-" in old_cover.name:
            try: old_cover.unlink()
            except Exception: pass

        # Update genres
        genres = set(default_genres)
        genres.add("বাংলা উইকিসংকলন (Wikisource)")
        genres_list = sorted(genres)

        # Build comprehensive search tokens
        search_tokens = {clean_title.lower(), clean_author.lower(), author_en.lower()}
        for a in author_aliases:
            search_tokens.add(a.lower())
        for t in title_translit[:4]:
            search_tokens.add(t.lower())
        series = detect_series(clean_title, clean_author)
        if series:
            search_tokens.update([series["name_bn"].lower(), series["name_en"].lower()])
        search_tokens.update(["wikisource", "উইকিসংকলন"])

        # Update book record
        b["id"] = book_id
        b["author"] = clean_author
        b["author_en"] = author_en
        b["author_aliases"] = author_aliases
        b["genres"] = genres_list
        b["series"] = series
        b["cover"] = f"assets/covers/{book_id}.webp"
        b["search_text"] = " ".join(search_tokens)

        # Ensure download URL format is valid ws-export epub-3
        if "epub" in b.get("formats", {}):
            b["formats"]["epub"]["filename"] = f"{slugify(clean_title) or 'book'}.epub"
            b["formats"]["epub"]["download_url"] = (
                f"https://ws-export.wmcloud.org/?lang=bn&page="
                f"{quote('রচনা')}:{quote(clean_title.replace(' ', '_'))}&format=epub-3"
            )

    # Recompute catalog statistics
    author_counts = {}
    format_counts = {}
    genre_counts = {}
    for b in catalog["books"]:
        author_counts[b["author"]] = author_counts.get(b["author"], 0) + 1
        for fmt in b.get("formats", {}):
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        for g in b.get("genres", []):
            genre_counts[g] = genre_counts.get(g, 0) + 1

    catalog["stats"] = {
        "total_books": len(catalog["books"]),
        "total_authors": len(author_counts),
        "formats": format_counts,
        "genres_count": len(genre_counts)
    }

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n--- Wikisource Author Resolution Complete ---")
    print(f"Total Wikisource works: {len(ws_books)}")
    print(f"Genuine Authors Resolved: {resolved_count}")
    print(f"Remaining Anonymous: {anonymous_count}")
    print(f"Covers Regenerated: {covers_regenerated}")
    print(f"Unique Authors in Catalog: {len(author_counts)}")
    print(f"Catalog stats: {catalog['stats']}")

if __name__ == "__main__":
    main()
