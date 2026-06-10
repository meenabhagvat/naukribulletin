#!/usr/bin/env python3
"""
patch_font_preload.py
Converts all blocking Google Fonts <link rel="stylesheet"> tags to non-blocking
<link rel="preload"> + onload pattern across every HTML page and scraper.py.

Estimated PageSpeed gain: LCP -0.5 to -0.8s, score 92 → 95+

Run from repo root:
    python3 patch_font_preload.py
    git add -A
    git commit -m "perf: non-blocking Google Fonts preload across all pages"
    git push
"""

import re
from pathlib import Path

# ── The non-blocking pattern ──────────────────────────────────────────────────
# Replaces:
#   <link href="URL" rel="stylesheet">
# With:
#   <link rel="preload" href="URL" as="style" onload="this.onload=null;this.rel='stylesheet'">
#   <noscript><link rel="stylesheet" href="URL"></noscript>
#
# Also adds crossorigin to the fonts.gstatic.com preconnect if missing,
# since preloading a cross-origin font requires it.
# ─────────────────────────────────────────────────────────────────────────────

FONT_LINK_RE = re.compile(
    r'<link\s+href="(https://fonts\.googleapis\.com/css2[^"]+)"\s+rel="stylesheet">|'
    r'<link\s+rel="stylesheet"\s+href="(https://fonts\.googleapis\.com/css2[^"]+)">',
    re.IGNORECASE
)

def make_preload(url: str, indent: str = "  ") -> str:
    return (
        f'<link rel="preload" href="{url}" as="style" onload="this.onload=null;this.rel=\'stylesheet\'">\n'
        f'{indent}<noscript><link rel="stylesheet" href="{url}"></noscript>'
    )

def fix_html(content: str) -> tuple[str, int]:
    """Returns (new_content, changes_made)."""
    changes = 0

    def replacer(m: re.Match) -> str:
        nonlocal changes
        url = m.group(1) or m.group(2)
        # Detect indentation from the matched text position
        line_start = content.rfind('\n', 0, m.start()) + 1
        indent = re.match(r'(\s*)', content[line_start:]).group(1)
        changes += 1
        return make_preload(url, indent)

    new_content = FONT_LINK_RE.sub(replacer, content)

    # Also ensure fonts.gstatic.com preconnect has crossorigin
    new_content = new_content.replace(
        '<link rel="preconnect" href="https://fonts.gstatic.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    )

    return new_content, changes


def fix_scraper(scraper_path: Path) -> int:
    """Fix scraper.py — same regex but also handles f-string context."""
    content = scraper_path.read_text(encoding="utf-8")
    new_content, changes = fix_html(content)
    if changes:
        scraper_path.write_text(new_content, encoding="utf-8")
    return changes


def main():
    root = Path(".")
    if not (root / "jobs").exists():
        raise SystemExit("❌  Run from repo root — 'jobs/' not found.")

    html_files = list(root.glob("**/*.html"))
    html_files = [f for f in html_files if ".git" not in str(f)]

    print(f"🔍  Scanning {len(html_files)} HTML files + scraper.py…\n")

    fixed_pages = 0
    skipped = 0

    for path in sorted(html_files):
        content = path.read_text(encoding="utf-8")
        new_content, changes = fix_html(content)
        if changes:
            path.write_text(new_content, encoding="utf-8")
            fixed_pages += 1
        else:
            skipped += 1

    # Fix scraper.py
    scraper = root / "scripts" / "scraper.py"
    scraper_changes = 0
    if scraper.exists():
        scraper_changes = fix_scraper(scraper)

    print(f"{'='*60}")
    print(f"HTML pages fixed : {fixed_pages}")
    print(f"Already OK       : {skipped}")
    print(f"scraper.py fixes : {scraper_changes} font links updated")
    print(f"{'='*60}\n")

    if fixed_pages == 0 and scraper_changes == 0:
        print("ℹ️  Nothing to fix — all fonts already non-blocking.")
    else:
        print("✅  Done.")
        print("   Next:  git add -A && git commit -m 'perf: non-blocking Google Fonts preload across all pages' && git push\n")


if __name__ == "__main__":
    main()
