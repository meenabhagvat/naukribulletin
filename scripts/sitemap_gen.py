#!/usr/bin/env python3
"""
NaukriBulletin — Auto Sitemap Generator
Scans all HTML pages and generates sitemap.xml for SEO
Run after scraper.py or include in GitHub Actions workflow
"""

import os
from pathlib import Path
from datetime import date

SITE_ROOT = Path(__file__).parent.parent
SITE_URL = "https://naukribulletin.in"
TODAY = date.today().isoformat()

PRIORITY_MAP = {
    "": "1.0",           # Homepage
    "jobs": "0.9",
    "current-affairs": "0.9",
    "results": "0.8",
    "admit-card": "0.8",
    "syllabus": "0.7",
    "answer-key": "0.7",
    "mock-test": "0.6",
}

CHANGEFREQ_MAP = {
    "": "daily",
    "jobs": "daily",
    "current-affairs": "daily",
    "results": "weekly",
    "admit-card": "weekly",
    "syllabus": "monthly",
}


def get_all_pages():
    """Walk site directory and collect all index.html paths."""
    pages = []
    for path in SITE_ROOT.rglob("index.html"):
        # Skip scripts folder
        if "scripts" in str(path) or ".github" in str(path):
            continue
        # Get relative URL
        rel = path.parent.relative_to(SITE_ROOT)
        url_path = str(rel).replace("\\", "/")
        if url_path == ".":
            url_path = ""
        # Get top-level folder for priority
        top_folder = url_path.split("/")[0] if url_path else ""
        priority = PRIORITY_MAP.get(top_folder, "0.6")
        changefreq = CHANGEFREQ_MAP.get(top_folder, "weekly")
        pages.append({
            "url": f"{SITE_URL}/{url_path}/".rstrip("/") + "/",
            "priority": priority,
            "changefreq": changefreq,
            "lastmod": TODAY,
        })
    return pages


def generate_sitemap(pages):
    """Generate sitemap.xml content."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for page in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{page['url']}</loc>")
        lines.append(f"    <lastmod>{page['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
        lines.append(f"    <priority>{page['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def generate_robots_txt():
    """Generate robots.txt."""
    return f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml

# Block irrelevant crawlers
User-agent: SemrushBot
Disallow: /
User-agent: AhrefsBot
Disallow: /
"""


def run():
    pages = get_all_pages()
    print(f"[SITEMAP] Found {len(pages)} pages")

    # Write sitemap.xml
    sitemap_path = SITE_ROOT / "sitemap.xml"
    with open(sitemap_path, "w") as f:
        f.write(generate_sitemap(pages))
    print(f"[SITEMAP] Written: sitemap.xml")

    # Write robots.txt
    robots_path = SITE_ROOT / "robots.txt"
    with open(robots_path, "w") as f:
        f.write(generate_robots_txt())
    print(f"[SITEMAP] Written: robots.txt")


if __name__ == "__main__":
    run()
