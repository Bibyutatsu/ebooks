"""Backward compatibility shim forwarding to tools/core/sync_releases.py."""
import sys
import os

_CORE_DIR = os.path.join(os.path.dirname(__file__), "core")
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from sync_releases import *
