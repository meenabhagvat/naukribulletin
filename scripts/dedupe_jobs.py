#!/usr/bin/env python3
"""Merge duplicate job pages: pages pointing to the same advert-specific apply link
are one advert. Keep the best page, delete the rest, 301-redirect them to it."""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from scraper import _norm_link, _specific_link, SITE_ROOT

groups = {}
for f in sorted((SITE_ROOT / "jobs").glob("*/index.html")):
    h = f.read_text(errors="ignore")
    m = re.search(r'<a href="([^"]+)"[^>]*>\s*Apply Online', h)
    if not m or not m.group(1).startswith("http"):
        continue
    link = _norm_link(m.group(1))
    if _specific_link(link):
        groups.setdefault(link, []).append((f.parent, h))

redirects, removed = [], 0
for link, pages in groups.items():
    if len(pages) < 2:
        continue
    # best = has post-wise table, then longest page
    pages.sort(key=lambda x: ("Post-wise details" in x[1], len(x[1])), reverse=True)
    keep = pages[0][0].name
    for d, _ in pages[1:]:
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
        redirects += [f"/jobs/{d.name}/ /jobs/{keep}/ 301", f"/jobs/{d.name} /jobs/{keep}/ 301"]
        removed += 1
        print(f"[DEDUPE] /jobs/{d.name}/ -> /jobs/{keep}/")

if redirects:
    r = SITE_ROOT / "_redirects"
    existing = r.read_text() if r.exists() else ""
    new = [x for x in redirects if x not in existing]
    if new:
        r.write_text(existing.rstrip("\n") + "\n" + "\n".join(new) + "\n")
print(f"[DEDUPE] removed {removed} duplicate job pages")
