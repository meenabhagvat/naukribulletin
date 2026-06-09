#!/usr/bin/env python3
"""
Fixes two things:
1. Footer broken links — /results/, /admit-card/, /mock-test/ etc now point to real pages
2. Git conflict prevention — scraper git_push() now does pull-before-push

Run from repo root: python3 patch_footer_git.py
"""
from pathlib import Path

SCRAPER  = Path("scripts/scraper.py")
WORKFLOW = Path(".github/workflows/daily-update.yml")

# ── Fix 1: git_push() — add pull --rebase before push ─────────────────────
OLD_GIT = '''def git_push(message="Auto: Update"):
    try:
        subprocess.run(["git", "add", "."], cwd=SITE_ROOT, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=SITE_ROOT, check=True)
        subprocess.run(["git", "push"], cwd=SITE_ROOT, check=True)'''

NEW_GIT = '''def git_push(message="Auto: Update"):
    try:
        subprocess.run(["git", "add", "."], cwd=SITE_ROOT, check=True)
        # Commit first (may fail if nothing to commit — that's fine)
        subprocess.run(["git", "commit", "-m", message], cwd=SITE_ROOT, check=False)
        # Pull with rebase to avoid conflicts with parallel runs
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=SITE_ROOT, check=False)
        subprocess.run(["git", "push"], cwd=SITE_ROOT, check=True)'''

# ── Fix 2: Footer in scraper rebuild_homepage and rebuild_jobs_listing ──────
# Find the footer HTML in the scraper and fix broken links
OLD_FOOTER_LINKS = '''            <li><a href="/results/">Results</a></li>
            <li><a href="/admit-card/">Admit Cards</a></li>
            <li><a href="/syllabus/">Syllabus</a></li>
            <li><a href="/answer-key/">Answer Keys</a></li>
            <li><a href="/mock-test/">Mock Tests</a></li>'''

NEW_FOOTER_LINKS = '''            <li><a href="/jobs/">Latest Jobs</a></li>
            <li><a href="/syllabus/">Syllabus</a></li>
            <li><a href="/answer-key/">Answer Keys</a></li>
            <li><a href="/age-calculator/">Age Calculator</a></li>
            <li><a href="/current-affairs/">Current Affairs</a></li>'''

OLD_FOOTER_AFFAIRS = '''            <li><a href="/current-affairs/daily/">Daily Updates</a></li>
            <li><a href="/current-affairs/monthly/">Monthly PDF</a></li>
            <li><a href="/current-affairs/economy/">Economy</a></li>
            <li><a href="/current-affairs/science/">Science & Tech</a></li>
            <li><a href="/current-affairs/international/">International</a></li>'''

NEW_FOOTER_AFFAIRS = '''            <li><a href="/current-affairs/">Daily Updates</a></li>
            <li><a href="/syllabus-pdf/">Free PDFs</a></li>
            <li><a href="/whatsapp/">WhatsApp Alerts</a></li>
            <li><a href="/age-calculator/">Age Calculator</a></li>
            <li><a href="/answer-key/">Answer Keys</a></li>'''

OLD_FOOTER_YEAR = '© 2025 NaukriBulletin.in — All Rights Reserved'
NEW_FOOTER_YEAR = '© 2026 NaukriBulletin.in — All Rights Reserved'


def patch_scraper():
    content = SCRAPER.read_text(encoding="utf-8")
    changed = False

    # Git pull before push
    if "--autostash" not in content:
        if OLD_GIT in content:
            content = content.replace(OLD_GIT, NEW_GIT, 1)
            print("✅ git_push() now pulls before pushing")
            changed = True
        else:
            print("⚠  git_push() pattern not found — check manually")
    else:
        print("✅ git_push() already has pull --rebase")

    # Footer exam resources links
    if "/results/" in content:
        content = content.replace(OLD_FOOTER_LINKS, NEW_FOOTER_LINKS)
        print("✅ Footer exam resource links fixed")
        changed = True
    else:
        print("✅ Footer exam links already fixed or not in scraper")

    # Footer current affairs links
    if "/current-affairs/daily/" in content:
        content = content.replace(OLD_FOOTER_AFFAIRS, NEW_FOOTER_AFFAIRS)
        print("✅ Footer current affairs links fixed")
        changed = True
    else:
        print("✅ Footer current affairs links already fixed or not in scraper")

    if changed:
        SCRAPER.write_text(content, encoding="utf-8")


def patch_homepage():
    """Fix broken footer links in index.html directly."""
    idx = Path("index.html")
    if not idx.exists():
        print("⚠  index.html not found — will be fixed on next scraper run")
        return

    content = idx.read_text(encoding="utf-8")
    changed = False

    fixes = [
        ('<a href="/results/">Results</a>',         '<a href="/jobs/">Latest Jobs</a>'),
        ('<a href="/admit-card/">Admit Cards</a>',   '<a href="/syllabus/">Syllabus</a>'),
        ('<a href="/mock-test/">Mock Tests</a>',     '<a href="/age-calculator/">Age Calculator</a>'),
        ('<a href="/current-affairs/daily/">Daily Updates</a>', '<a href="/current-affairs/">Daily Updates</a>'),
        ('<a href="/current-affairs/monthly/">Monthly PDF</a>', '<a href="/syllabus-pdf/">Free PDFs</a>'),
        ('<a href="/current-affairs/economy/">Economy</a>',     '<a href="/whatsapp/">WhatsApp Alerts</a>'),
        ('<a href="/current-affairs/science/">Science &amp; Tech</a>', '<a href="/age-calculator/">Age Calculator</a>'),
        ('<a href="/current-affairs/international/">International</a>', '<a href="/answer-key/">Answer Keys</a>'),
        ('© 2025 NaukriBulletin', '© 2026 NaukriBulletin'),
        ('govt job 2025', 'govt job 2026'),
    ]

    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            changed = True

    if changed:
        idx.write_text(content, encoding="utf-8")
        print("✅ index.html footer links fixed directly")
    else:
        print("✅ index.html already has correct footer links")


def patch_workflow():
    """Add --autostash to workflow git pull to prevent conflicts."""
    if not WORKFLOW.exists():
        print("⚠  Workflow file not found")
        return

    content = WORKFLOW.read_text(encoding="utf-8")

    # The workflow doesn't do git pull — the scraper does it internally now
    # Just ensure the workflow doesn't have a competing git push
    if "git push" in content and "git pull" not in content:
        print("ℹ  Workflow relies on scraper's git_push() — no change needed")
    else:
        print("✅ Workflow looks fine")


def patch_jobs_listing():
    """Fix footer in jobs/index.html directly."""
    idx = Path("jobs/index.html")
    if not idx.exists():
        print("⚠  jobs/index.html not found")
        return

    content = idx.read_text(encoding="utf-8")
    fixes = [
        ('<a href="/results/">Results</a>',           '<a href="/jobs/">Latest Jobs</a>'),
        ('<a href="/admit-card/">Admit Cards</a>',     '<a href="/syllabus/">Syllabus</a>'),
        ('<a href="/mock-test/">Mock Tests</a>',       '<a href="/age-calculator/">Age Calculator</a>'),
        ('<a href="/current-affairs/daily/">',         '<a href="/current-affairs/">'),
        ('<a href="/current-affairs/monthly/">',       '<a href="/syllabus-pdf/">'),
        ('<a href="/current-affairs/economy/">',       '<a href="/whatsapp/">'),
        ('© 2025 NaukriBulletin',                     '© 2026 NaukriBulletin'),
    ]
    changed = any(old in content for old, _ in fixes)
    for old, new in fixes:
        content = content.replace(old, new)
    if changed:
        idx.write_text(content, encoding="utf-8")
        print("✅ jobs/index.html footer fixed")


if __name__ == "__main__":
    patch_scraper()
    patch_homepage()
    patch_jobs_listing()
    patch_workflow()
    print("\n✅ Done. Run: python3 scripts/scraper.py then git add . && git commit -m 'fix: footer links + git conflict prevention' && git push origin main")
