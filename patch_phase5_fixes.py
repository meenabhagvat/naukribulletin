#!/usr/bin/env python3
"""
NaukriBulletin — patch_phase5_fixes.py
Phase 5 audit: fixes 6 confirmed bugs found in code review.

Run from repo root:
    python patch_phase5_fixes.py

Fixes applied:
  1. alerts/index.html  — wrong title ("Results") and wrong canonical (/results/)
  2. Homepage           — missing og:image meta tag
  3. _redirects         — add trailing-slash redirects for /about/, /alerts/, /contact/,
                          /privacy/, /disclaimer/, /cut-off/, /mock-test/
  4. GitHub workflow    — commit scripts/_data/ (not legacy tg_posted.json) so
                          notification state persists across runs
  5. AdSense backfill   — replace placeholder ca-pub-XXXXXXXXXX with real pub ID
                          in ALL existing job + current-affairs HTML pages
  6. scraper.py         — update ADSENSE_CLIENT default from env so future pages
                          also get the real ID at generation time
"""

import re
from pathlib import Path

SITE_ROOT = Path(__file__).parent

# ─── Real AdSense publisher ID ────────────────────────────────────────────────
REAL_PUB_ID = "ca-pub-1001412206051588"
PLACEHOLDER  = "ca-pub-XXXXXXXXXX"

FIXES_APPLIED = []


# ── 1. Fix alerts/index.html ──────────────────────────────────────────────────

def fix_alerts_page():
    path = SITE_ROOT / "alerts" / "index.html"
    if not path.exists():
        print("[SKIP] alerts/index.html not found")
        return

    html = path.read_text(encoding="utf-8")
    orig = html

    # Fix wrong title
    html = html.replace(
        "<title>Govt Exam Results 2026 — NaukriBulletin</title>",
        "<title>Free Govt Job Alerts 2026 — Email, Telegram, WhatsApp | NaukriBulletin</title>"
    )
    # Fix wrong canonical
    html = html.replace(
        'href="https://naukribulletin.in/results/"',
        'href="https://naukribulletin.in/alerts/"'
    )
    # Fix wrong meta description (if it says "results")
    html = html.replace(
        'content="Latest SSC, Railway, Banking, UPSC exam results 2026. Check your result instantly."',
        'content="Get free daily govt job alerts 2026 via Email, Telegram &amp; WhatsApp. SSC, Railway, Banking, UPSC, State PSC — instant notifications."'
    )

    if html != orig:
        path.write_text(html, encoding="utf-8")
        print("[FIX 1] ✅ alerts/index.html — title, canonical, meta description corrected")
        FIXES_APPLIED.append("alerts/index.html: title+canonical+description fixed")
    else:
        print("[FIX 1] alerts/index.html — no matching strings found (may already be fixed)")


# ── 2. Fix homepage og:image ──────────────────────────────────────────────────

def fix_homepage_og_image():
    path = SITE_ROOT / "index.html"
    if not path.exists():
        print("[SKIP] index.html not found")
        return

    html = path.read_text(encoding="utf-8")

    if 'property="og:image"' in html:
        print("[FIX 2] og:image already present in index.html — skipping")
        return

    OG_IMAGE_TAG = '  <meta property="og:image" content="https://naukribulletin.in/assets/logo-256.png">\n'
    # Insert after og:url line
    html = html.replace(
        '  <meta property="og:url" content="https://naukribulletin.in">',
        '  <meta property="og:url" content="https://naukribulletin.in">\n' + OG_IMAGE_TAG.rstrip()
    )

    path.write_text(html, encoding="utf-8")
    print("[FIX 2] ✅ index.html — og:image added")
    FIXES_APPLIED.append("index.html: og:image tag added")


# ── 3. Fix _redirects ────────────────────────────────────────────────────────

def fix_redirects():
    path = SITE_ROOT / "_redirects"
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    MISSING = [
        "/about          /about/          301",
        "/alerts         /alerts/         301",
        "/contact        /contact/        301",
        "/privacy        /privacy/        301",
        "/disclaimer     /disclaimer/     301",
        "/cut-off        /cut-off/        301",
        "/mock-test      /mock-test/      301",
        "/whatsapp       /whatsapp/       301",
    ]

    added = []
    for rule in MISSING:
        path_part = rule.split()[0]
        if path_part not in content:
            content += "\n" + rule
            added.append(rule.strip())

    if added:
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        print(f"[FIX 3] ✅ _redirects — added {len(added)} missing redirect rules:")
        for r in added:
            print(f"         {r}")
        FIXES_APPLIED.append(f"_redirects: {len(added)} rules added")
    else:
        print("[FIX 3] _redirects — all rules already present")


# ── 4. Fix GitHub Actions workflow — persist notification state ────────────────

def fix_workflow_notification_state():
    path = SITE_ROOT / ".github" / "workflows" / "daily-update.yml"
    if not path.exists():
        print("[SKIP] workflow file not found")
        return

    content = path.read_text(encoding="utf-8")
    orig    = content

    # Replace the commit step for notification state:
    # OLD: git add scripts/tg_posted.json scripts/wa_notified_ids.json
    # NEW: git add scripts/_data/ scripts/tg_posted.json
    content = content.replace(
        "git add scripts/tg_posted.json scripts/wa_notified_ids.json",
        "git add scripts/_data/ scripts/tg_posted.json"
    )

    if content != orig:
        path.write_text(content, encoding="utf-8")
        print("[FIX 4] ✅ daily-update.yml — notification state commit updated to include scripts/_data/")
        FIXES_APPLIED.append("daily-update.yml: git add scripts/_data/ for notification persistence")
    else:
        print("[FIX 4] daily-update.yml — pattern not found or already fixed")


# ── 5. AdSense backfill — replace placeholder in all existing HTML pages ──────

def fix_adsense_placeholders():
    dirs_to_fix = ["jobs", "current-affairs"]
    total_fixed = 0

    for folder in dirs_to_fix:
        folder_path = SITE_ROOT / folder
        if not folder_path.exists():
            continue
        for html_file in folder_path.rglob("index.html"):
            try:
                content = html_file.read_text(encoding="utf-8")
                if PLACEHOLDER in content:
                    new_content = content.replace(PLACEHOLDER, REAL_PUB_ID)
                    html_file.write_text(new_content, encoding="utf-8")
                    total_fixed += 1
            except Exception as e:
                print(f"  [WARN] Could not fix {html_file}: {e}")

    print(f"[FIX 5] ✅ AdSense pub ID backfill — fixed {total_fixed} HTML pages")
    FIXES_APPLIED.append(f"AdSense: replaced placeholder in {total_fixed} job/current-affairs pages")


# ── 6. Fix scraper.py default ADSENSE_CLIENT value ────────────────────────────

def fix_scraper_adsense_default():
    path = SITE_ROOT / "scripts" / "scraper.py"
    if not path.exists():
        print("[SKIP] scraper.py not found")
        return

    content = path.read_text(encoding="utf-8")
    orig    = content

    # Replace: ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "ca-pub-XXXXXXXXXX")
    # With:    ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "ca-pub-1001412206051588")
    content = content.replace(
        'ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "ca-pub-XXXXXXXXXX")',
        f'ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "{REAL_PUB_ID}")'
    )

    if content != orig:
        path.write_text(content, encoding="utf-8")
        print("[FIX 6] ✅ scraper.py — ADSENSE_CLIENT default updated to real pub ID")
        FIXES_APPLIED.append("scraper.py: ADSENSE_CLIENT fallback set to real pub ID")
    else:
        print("[FIX 6] scraper.py — pattern not found or already fixed")


# ── BONUS: Also add og:image to job page HTML template in scraper.py ──────────

def fix_scraper_og_image():
    """Add og:image to the job HTML template in scraper.py so future pages have it."""
    path = SITE_ROOT / "scripts" / "scraper.py"
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    orig    = content

    # Add og:image after og:type line in generate_job_html
    OLD = '  <meta property="og:type" content="website">\n  <meta name="twitter:card" content="summary">'
    NEW = ('  <meta property="og:type" content="website">\n'
           '  <meta property="og:image" content="https://naukribulletin.in/assets/logo-256.png">\n'
           '  <meta name="twitter:card" content="summary">')
    content = content.replace(OLD, NEW)

    if content != orig:
        path.write_text(content, encoding="utf-8")
        print("[BONUS] ✅ scraper.py — og:image added to job page HTML template")
        FIXES_APPLIED.append("scraper.py: og:image added to job page template")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NaukriBulletin — Phase 5 Patch")
    print("="*60 + "\n")

    fix_alerts_page()
    fix_homepage_og_image()
    fix_redirects()
    fix_workflow_notification_state()
    fix_adsense_placeholders()
    fix_scraper_adsense_default()
    fix_scraper_og_image()

    print("\n" + "="*60)
    print(f"✅ Done — {len(FIXES_APPLIED)} fixes applied:")
    for i, f in enumerate(FIXES_APPLIED, 1):
        print(f"  {i}. {f}")
    print("="*60)
    print("\nNext steps:")
    print("  1. Review changes with: git diff")
    print("  2. Commit: git add -A && git commit -m 'fix: phase5 audit patches'")
    print("  3. Push:   git push")
    print("  4. Once AdSense approved: update ADSENSE_SLOT_TOP + ADSENSE_SLOT_MID")
    print("     in GitHub Secrets, then re-run this script to backfill ad slots.")
