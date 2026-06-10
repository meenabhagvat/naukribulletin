#!/usr/bin/env python3
"""
patch_meta_descriptions.py
Audits all job pages for thin meta descriptions (<120 chars) and
rewrites them using data already present in the HTML.

Run from the repo root:
    python3 patch_meta_descriptions.py

After running:
    git add -A
    git commit -m "seo: fix thin meta descriptions across all job pages"
    git push
"""

import os
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("Install beautifulsoup4 first:  pip install beautifulsoup4")


# ── config ────────────────────────────────────────────────────────────────────
JOBS_DIR   = Path("jobs")
MIN_LEN    = 120          # below this is "thin"
MAX_LEN    = 155          # hard cap for Google preview
DRY_RUN    = False        # set True to preview changes without writing files
# ─────────────────────────────────────────────────────────────────────────────


def extract_page_data(soup: BeautifulSoup) -> dict:
    """Pull key fields from the rendered HTML table + header paragraph."""
    data = {
        "title":       "",
        "department":  "",
        "vacancies":   "",
        "qualification": "",
        "last_date":   "",
        "salary":      "",
        "intro_para":  "",
    }

    # <title> tag
    title_tag = soup.find("title")
    if title_tag:
        raw = title_tag.get_text(strip=True)
        data["title"] = raw.replace(" — NaukriBulletin", "").replace(" | NaukriBulletin", "").strip()

    # <h1>
    h1 = soup.find("h1")
    if h1:
        data["h1"] = h1.get_text(strip=True)

    # Table rows  key → value
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) == 2:
            key = tds[0].get_text(strip=True).lower()
            val = tds[1].get_text(strip=True)
            if "department" in key or "organisation" in key or "organization" in key:
                data["department"] = val
            elif "vacanc" in key:
                data["vacancies"] = val
            elif "qualification" in key or "education" in key:
                data["qualification"] = val
            elif "last date" in key or "apply by" in key:
                data["last_date"] = val
            elif "salary" in key or "pay scale" in key or "stipend" in key:
                data["salary"] = val

    # Intro paragraph (the grey subtitle under h1)
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 50:
            data["intro_para"] = text
            break

    # Vacancy / last-date badges (fallback)
    if not data["vacancies"] or data["vacancies"] == "N/A":
        badge = soup.find(string=re.compile(r"👥 Vacancies:"))
        if badge:
            m = re.search(r"Vacancies:\s*(\S+)", badge)
            if m:
                data["vacancies"] = m.group(1)

    if not data["last_date"] or data["last_date"] == "N/A":
        badge = soup.find(string=re.compile(r"📅 Last Date:"))
        if badge:
            m = re.search(r"Last Date:\s*(.+)", badge)
            if m:
                data["last_date"] = m.group(1).strip()

    return data


def build_meta_description(d: dict) -> str:
    """
    Construct a rich, ≤155-char meta description from extracted fields.
    Priority: intro para → constructed sentence → title fallback.
    """
    title   = d.get("h1") or d.get("title", "")
    dept    = d.get("department", "")
    vac     = d.get("vacancies", "")
    qual    = d.get("qualification", "")
    ldate   = d.get("last_date", "")
    intro   = d.get("intro_para", "")
    salary  = d.get("salary", "")

    def trim(s: str, limit: int = MAX_LEN) -> str:
        s = s.strip()
        if len(s) <= limit:
            return s
        return s[:limit - 1].rsplit(" ", 1)[0] + "…"

    # ── Option 1: intro paragraph is already good ──────────────────────────
    if len(intro) >= MIN_LEN:
        return trim(intro)

    # ── Option 2: build from structured fields ─────────────────────────────
    parts = []
    if intro and len(intro) > 30:
        parts.append(intro.rstrip(".") + ".")
    else:
        if dept and dept.lower() not in title.lower():
            parts.append(f"{dept} has released recruitment notification 2026.")
        elif title:
            parts.append(title.rstrip(".") + ".")

    # add vacancy count
    if vac and vac not in ("N/A", "", "0"):
        try:
            int_vac = int(vac.replace(",", ""))
            parts.append(f"{int_vac:,} vacancies.")
        except ValueError:
            parts.append(f"{vac} vacancies.")

    # add qualification
    if qual and qual not in ("N/A", ""):
        parts.append(f"Eligibility: {qual}.")

    # add salary
    if salary and salary not in ("N/A", ""):
        parts.append(f"Pay: {salary}.")

    # add last date
    if ldate and ldate not in ("N/A", ""):
        parts.append(f"Apply by {ldate}.")

    # add CTA
    parts.append("Apply now at NaukriBulletin.in")

    candidate = " ".join(parts)

    # If still too short, expand with title
    if len(candidate) < MIN_LEN and title:
        candidate = f"{title}. " + " ".join(parts[1:]) if parts else candidate

    return trim(candidate)


def fix_page(html_path: Path) -> tuple[bool, str, str]:
    """
    Returns (changed, old_desc, new_desc).
    Writes the file in-place unless DRY_RUN.
    """
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Find existing meta description
    meta_tag = soup.find("meta", attrs={"name": "description"})
    og_tag   = soup.find("meta", property="og:description")

    if not meta_tag:
        return False, "", ""

    old_desc = meta_tag.get("content", "")
    if len(old_desc) >= MIN_LEN:
        return False, old_desc, old_desc   # already fine

    page_data = extract_page_data(soup)
    new_desc  = build_meta_description(page_data)

    if new_desc == old_desc or len(new_desc) < 40:
        return False, old_desc, new_desc   # nothing useful to replace

    if DRY_RUN:
        return True, old_desc, new_desc

    # Replace content attribute using regex (preserves formatting)
    new_content = re.sub(
        r'(<meta\s+name="description"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_desc + m.group(2),
        content,
        count=1,
    )

    # Also update og:description if present
    if 'property="og:description"' in new_content:
        new_content = re.sub(
            r'(<meta\s+property="og:description"\s+content=")[^"]*(")',
            lambda m: m.group(1) + new_desc + m.group(2),
            new_content,
            count=1,
        )
    elif 'og:description' in new_content:
        # different attribute order
        new_content = re.sub(
            r'(<meta\s+content=")[^"]*("\s+property="og:description")',
            lambda m: m.group(1) + new_desc + m.group(2),
            new_content,
            count=1,
        )

    html_path.write_text(new_content, encoding="utf-8")
    return True, old_desc, new_desc


def main():
    if not JOBS_DIR.exists():
        raise SystemExit(f"❌  Run this script from the repo root. '{JOBS_DIR}' not found.")

    pages = sorted(JOBS_DIR.glob("*/index.html"))
    print(f"🔍  Scanning {len(pages)} job pages …\n")

    fixed   = []
    skipped = 0
    errors  = []

    for path in pages:
        try:
            changed, old, new = fix_page(path)
            if changed:
                fixed.append((path, old, new))
            else:
                skipped += 1
        except Exception as e:
            errors.append((path, str(e)))

    # ── Report ──────────────────────────────────────────────────────────────
    action = "Would fix" if DRY_RUN else "Fixed"
    print(f"{'='*70}")
    print(f"{action}: {len(fixed)} pages   |  Already OK: {skipped}   |  Errors: {len(errors)}")
    print(f"{'='*70}\n")

    if fixed:
        print(f"{'SLUG':<50}  {'OLD':>6}  {'NEW':>6}")
        print("-" * 70)
        for path, old, new in fixed:
            slug = path.parent.name
            print(f"{slug:<50}  {len(old):>5}c  {len(new):>5}c")
        print()

    if errors:
        print("⚠️  Errors:")
        for path, err in errors:
            print(f"  {path}: {err}")

    if DRY_RUN:
        print("ℹ️  DRY_RUN=True — no files were modified.\n")
    else:
        print(f"✅  Done. {len(fixed)} pages updated.")
        print("   Next step:  git add -A && git commit -m 'seo: fix thin meta descriptions' && git push\n")


if __name__ == "__main__":
    main()
