#!/usr/bin/env python3
"""
Sitemap generator entrypoint for Bibyutatsu BookStore.
Delegates to tools/core/sitemap_generator.py.
"""

import os
import sys
from pathlib import Path

_CORE_DIR = os.path.join(os.path.dirname(__file__), "core")
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from sitemap_generator import generate_sitemap

if __name__ == '__main__':
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_file = os.path.join(root_dir, 'catalog.json')
    generate_sitemap(cat_file, root_dir)

