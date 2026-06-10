#!/usr/bin/env python3
"""
patch_zero_click_pages.py
Fixes 3 zero-click / high-impression job pages identified from Search Console data,
and adds a Related Jobs section to the CCRUM page (highest GA4 traffic, no internal links).

Changes made:
  1. DRDO SAG Paid Intern  — sharpens title + meta with vacancy count & deadline
  2. Assam University Teaching — adds vacancy count & deadline to title + meta
  3. GPSC AE 2026          — expands abbreviation + adds vacancy count & deadline
  4. CCRUM page            — injects "Related Jobs" section before </main>

Run from repo root:
    python3 patch_zero_click_pages.py
    git add -A
    git commit -m "seo: fix zero-click pages + add CCRUM related jobs"
    git push
"""

import re
from pathlib import Path

JOBS = Path("jobs")

# ── helpers ───────────────────────────────────────────────────────────────────

def read(slug: str) -> tuple[Path, str]:
    p = JOBS / slug / "index.html"
    return p, p.read_text(encoding="utf-8")

def write(p: Path, content: str):
    p.write_text(content, encoding="utf-8")

def set_title(content: str, new_title: str) -> str:
    return re.sub(
        r'<title>[^<]+</title>',
        f'<title>{new_title}</title>',
        content, count=1
    )

def set_meta(content: str, tag: str, new_val: str) -> str:
    """Replace content of a meta tag identified by name= or property=."""
    # name="description"
    content = re.sub(
        rf'(<meta\s+name="{tag}"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_val + m.group(2),
        content, count=1
    )
    # og: variants
    content = re.sub(
        rf'(<meta\s+property="{tag}"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_val + m.group(2),
        content, count=1
    )
    return content

def set_h1(content: str, new_h1: str) -> str:
    return re.sub(
        r'(<h1[^>]*>)[^<]*(</h1>)',
        lambda m: m.group(1) + new_h1 + m.group(2),
        content, count=1
    )

# ── related jobs HTML block ───────────────────────────────────────────────────

def related_jobs_html(jobs: list[dict]) -> str:
    """
    jobs: list of {slug, title, badge, badge_color}
    badge_color: 'orange' | 'green' | 'blue'
    """
    color_map = {
        'orange': ('rgba(255,107,0,0.12)', '#FF6B00'),
        'green':  ('rgba(19,136,8,0.12)',  '#1AA60A'),
        'blue':   ('rgba(55,138,221,0.12)','#185FA5'),
    }

    cards = ""
    for j in jobs:
        bg, fg = color_map.get(j.get('badge_color', 'blue'), color_map['blue'])
        cards += f"""
      <a href="/jobs/{j['slug']}/" style="display:block;background:#fff;border:1.5px solid #ECEEF2;border-radius:12px;padding:16px 18px;text-decoration:none;color:inherit;transition:border-color 0.15s;" onmouseover="this.style.borderColor='#378ADD'" onmouseout="this.style.borderColor='#ECEEF2'">
        <div style="font-size:0.75rem;font-weight:700;letter-spacing:0.04em;color:{fg};margin-bottom:6px;">
          <span style="background:{bg};padding:3px 8px;border-radius:4px;">{j['badge']}</span>
        </div>
        <div style="font-size:0.92rem;font-weight:600;color:#0A0F2C;line-height:1.35;">{j['title']}</div>
      </a>"""

    return f"""
  <section style="max-width:900px;margin:0 auto;padding:0 20px 32px;">
    <h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:#0A0F2C;margin:0 0 16px;">Related jobs you may like</h2>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;">
{cards}
    </div>
  </section>
"""


# ── 1. DRDO SAG Paid Intern ───────────────────────────────────────────────────
# Query: "drdo sag paid internship 2026" — 160 impressions, pos 7.7, 0 clicks
# Fix: Add vacancy count + deadline to title; use "Internship" not "Recruitment"

def fix_drdo_sag():
    slug = "drdo-sag-paid-intern-recruitment-2026"
    p, content = read(slug)

    new_title_tag  = "DRDO SAG Paid Internship 2026 — 40 Posts | Apply by 15 June — NaukriBulletin"
    new_h1         = "DRDO SAG Paid Internship 2026 — 40 Posts"
    new_meta_desc  = "DRDO SAG Paid Internship 2026: 40 openings for B.E./B.Tech, M.Tech/M.Sc graduates. Apply online before 15 June 2026 on the official DRDO SAG website."
    new_og_title   = "DRDO SAG Paid Internship 2026 — 40 Posts | Apply by 15 June"

    content = set_title(content, new_title_tag)
    content = set_h1(content, new_h1)
    content = set_meta(content, "description", new_meta_desc)
    content = re.sub(
        r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_og_title + m.group(2),
        content, count=1
    )
    write(p, content)
    print(f"✅  Fixed: {slug}")
    print(f"    Title → {new_title_tag[:70]}…")


# ── 2. Assam University Teaching ──────────────────────────────────────────────
# Impressions: 104, pos 5.8, 0 clicks
# Fix: Add post type, vacancy count, deadline — make it scannable in SERP

def fix_assam_university():
    slug = "assam-university-teaching-recruitment-2026"
    p, content = read(slug)

    new_title_tag  = "Assam University Teaching Recruitment 2026 — 123 Faculty Posts | Apply by 10 July — NaukriBulletin"
    new_h1         = "Assam University Teaching Recruitment 2026 — 123 Faculty Posts"
    new_meta_desc  = "Assam University invites applications for 123 teaching posts (Professor, Associate Professor, Assistant Professor). Eligibility: Masters + Ph.D. Last date 10 July 2026."
    new_og_title   = "Assam University Teaching Recruitment 2026 — 123 Faculty Posts | Apply by 10 July"

    content = set_title(content, new_title_tag)
    content = set_h1(content, new_h1)
    content = set_meta(content, "description", new_meta_desc)
    content = re.sub(
        r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_og_title + m.group(2),
        content, count=1
    )
    write(p, content)
    print(f"✅  Fixed: {slug}")
    print(f"    Title → {new_title_tag[:70]}…")


# ── 3. GPSC AE 2026 ──────────────────────────────────────────────────────────
# Impressions: 75, pos 5.6, 0 clicks
# Fix: Expand "AE" → "Assistant Engineer"; add state, count, deadline

def fix_gpsc_ae():
    slug = "gpsc-ae-recruitment-2026"
    p, content = read(slug)

    new_title_tag  = "GPSC Assistant Engineer Recruitment 2026 — 235 Posts | Apply by 19 June — NaukriBulletin"
    new_h1         = "GPSC Assistant Engineer Recruitment 2026 — 235 Posts"
    new_meta_desc  = "Gujarat PSC Assistant Engineer Recruitment 2026: 235 vacancies in Civil & Mechanical. Eligibility: B.Tech/B.E. Apply online at gpsc.gujarat.gov.in by 19 June 2026."
    new_og_title   = "GPSC Assistant Engineer Recruitment 2026 — 235 Posts | Apply by 19 June"

    content = set_title(content, new_title_tag)
    content = set_h1(content, new_h1)
    content = set_meta(content, "description", new_meta_desc)
    content = re.sub(
        r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
        lambda m: m.group(1) + new_og_title + m.group(2),
        content, count=1
    )
    write(p, content)
    print(f"✅  Fixed: {slug}")
    print(f"    Title → {new_title_tag[:70]}…")


# ── 4. CCRUM — add Related Jobs section ──────────────────────────────────────
# 236 GA4 views, 215 unique users, ~0 clicks to other pages → massive bounce
# Link to CSIR family + research/consultant jobs to retain the audience

def fix_ccrum_related_jobs():
    slug = "ccrum-consultant-scientific-writer-recruitment-2026"
    p, content = read(slug)

    related = [
        {
            "slug":  "csir-neeri-project-scientist-i-recruitment-2026",
            "title": "CSIR-NEERI Project Scientist-I Recruitment 2026",
            "badge": "CSIR · Research",
            "badge_color": "blue",
        },
        {
            "slug":  "csir-neeri-senior-project-associate-recruitment-2026",
            "title": "CSIR NEERI Senior Project Associate Recruitment 2026",
            "badge": "CSIR · Research",
            "badge_color": "blue",
        },
        {
            "slug":  "csir-npl-project-staff-recruitment-2026",
            "title": "CSIR NPL Project Staff Recruitment 2026",
            "badge": "CSIR · Research",
            "badge_color": "blue",
        },
        {
            "slug":  "jncasr-research-associate-recruitment-2026",
            "title": "JNCASR Research Associate Recruitment 2026",
            "badge": "Research · Graduate",
            "badge_color": "green",
        },
        {
            "slug":  "icmr-nihr-project-technical-support-iii-recruitment-2026",
            "title": "ICMR NIHR Project Technical Support-III Recruitment 2026",
            "badge": "ICMR · Research",
            "badge_color": "orange",
        },
        {
            "slug":  "csir-neeri-project-associate-i-recruitment-2026",
            "title": "CSIR-NEERI Project Associate-I Recruitment 2026",
            "badge": "CSIR · Research",
            "badge_color": "blue",
        },
    ]

    block = related_jobs_html(related)

    if "Related jobs you may like" in content:
        print(f"⏭   Skipped (already has related jobs): {slug}")
        return

    content = content.replace("</main>", block + "\n  </main>", 1)
    write(p, content)
    print(f"✅  Fixed: {slug}")
    print(f"    Added {len(related)} related job links")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if not JOBS.exists():
        raise SystemExit("❌  Run from repo root — 'jobs/' not found.")

    print("🔧  Patching zero-click pages + CCRUM related jobs…\n")
    fix_drdo_sag()
    fix_assam_university()
    fix_gpsc_ae()
    fix_ccrum_related_jobs()
    print()
    print("✅  Done.")
    print("   Next:  git add -A && git commit -m 'seo: fix zero-click pages + CCRUM related jobs' && git push")

if __name__ == "__main__":
    main()
