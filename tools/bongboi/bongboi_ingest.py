"""
BongBoi Repository Ingestion Pipeline.
Extracts metadata, extracts/generates WebP covers, canonicalizes authors,
updates existing books missing EPUB, adds new classical books,
and prepares releases upload.
"""

import os
import re
import json
import io
import shutil
import zipfile
import hashlib
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, os.path.dirname(__file__))

from author_mapping import AUTHORS_DB, get_author_info, find_author_match, _ALIAS_INDEX
from series_mapping import detect_series
from transliteration import transliterate_text
from build_catalog import format_size, slugify

def norm(s: str) -> str:
    return unicodedata.normalize('NFC', s.strip())

def extract_epub_info(epub_path: Path) -> dict:
    info = {"title": "", "creator": "", "date": "", "subjects": [], "cover_bytes": None}
    try:
        with zipfile.ZipFile(epub_path, "r") as z:
            container = z.read("META-INF/container.xml")
            root = ET.fromstring(container)
            rootfile = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
            if rootfile is not None and "full-path" in rootfile.attrib:
                opf_path = rootfile.attrib["full-path"]
                opf_content = z.read(opf_path)
                opf_root = ET.fromstring(opf_content)
                t = opf_root.find(".//{http://purl.org/dc/elements/1.1/}title")
                c = opf_root.find(".//{http://purl.org/dc/elements/1.1/}creator")
                d = opf_root.find(".//{http://purl.org/dc/elements/1.1/}date")
                if t is not None and t.text:
                    info["title"] = t.text.strip()
                if c is not None and c.text:
                    info["creator"] = c.text.strip()
                if d is not None and d.text:
                    info["date"] = d.text.strip()[:4]
                for s in opf_root.findall(".//{http://purl.org/dc/elements/1.1/}subject"):
                    if s.text and s.text.strip():
                        info["subjects"].append(s.text.strip())

            # Look for cover image
            imgs = [n for n in z.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            good_imgs = []
            for img_name in imgs:
                low = img_name.lower()
                if any(bad in low for bad in ('accueil', 'segment', 'diamond', 'tear')):
                    continue
                file_size = z.getinfo(img_name).file_size
                if file_size > 5000:
                    good_imgs.append((img_name, file_size))

            if good_imgs:
                good_imgs.sort(key=lambda x: (1 if any(k in x[0].lower() for k in ('cover', 'page1', 'c6_lossy', 'c10_')) else 0, x[1]), reverse=True)
                chosen = good_imgs[0][0]
                data = z.read(chosen)
                try:
                    im = Image.open(io.BytesIO(data))
                    w, h = im.size
                    if w >= 120 and h >= 120:
                        info["cover_bytes"] = data
                except Exception:
                    pass
    except Exception as e:
        pass
    return info

def generate_cover_art(title: str, author: str, out_path: Path, width=300, height=450):
    palettes = [
        ((15, 23, 42), (30, 41, 59), (56, 189, 248)),
        ((19, 24, 39), (31, 41, 55), (251, 146, 60)),
        ((24, 24, 27), (39, 39, 42), (167, 139, 250)),
        ((17, 24, 39), (31, 41, 55), (52, 211, 153)),
        ((30, 27, 75), (49, 46, 129), (244, 114, 182)),
        ((20, 30, 45), (15, 60, 90), (250, 204, 21)),
    ]
    h = int(hashlib.md5(f"{title}{author}".encode('utf-8')).hexdigest()[:6], 16)
    bg1, bg2, accent = palettes[h % len(palettes)]

    img = Image.new('RGB', (width, height), bg1)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        factor = y / height
        r = int(bg1[0] * (1 - factor) + bg2[0] * factor)
        g = int(bg1[1] * (1 - factor) + bg2[1] * factor)
        b = int(bg1[2] * (1 - factor) + bg2[2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.rectangle([14, 14, width - 14, height - 14], outline=(accent[0], accent[1], accent[2]), width=1)
    draw.line([6, 0, 6, height], fill=(255, 255, 255, 40), width=2)

    font_path = '/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc'
    try:
        font_title = ImageFont.truetype(font_path, 22)
        font_author = ImageFont.truetype(font_path, 15)
        font_ornament = ImageFont.truetype(font_path, 13)
    except:
        font_title = font_author = font_ornament = ImageFont.load_default()

    draw.text((width / 2, 70), '✦ ✦ ✦', fill=accent, font=font_ornament, anchor='mm')
    
    # Wrap title if long
    words = title.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(' '.join(curr)) > 16:
            lines.append(' '.join(curr[:-1]) if len(curr) > 1 else w)
            curr = [w] if len(curr) > 1 else []
    if curr:
        lines.append(' '.join(curr))
    if not lines:
        lines = [title]

    start_y = height / 2 - (len(lines) * 16)
    for i, line in enumerate(lines):
        draw.text((width / 2, start_y + i * 30), line, fill=(245, 245, 245), font=font_title, anchor='mm')

    draw.text((width / 2, height - 70), author, fill=accent, font=font_author, anchor='mm')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, 'WEBP', quality=85)

print("Ingestion script helper ready.")
