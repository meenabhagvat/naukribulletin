#!/usr/bin/env python3
"""
NaukriBulletin — patch_state_pages.py
Now a thin wrapper around category_gen.run().
All state/qualification/hub page logic lives in scripts/category_gen.py.

Run from repo root:
    python3 patch_state_pages.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "category_gen",
    Path(__file__).parent / "scripts" / "category_gen.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.run()
