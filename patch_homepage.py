#!/usr/bin/env python3
"""
Patches scripts/scraper.py to add rebuild_homepage() which fixes:
  1. Stale 2025 homepage job cards → real scraped jobs
  2. Stale 2025 current affairs → real scraped articles
  3. Stale ticker → real job titles
  4. Hardcoded 2025 in meta keywords → current year
  5. Footer © 2025 → current year
  6. Duplicate job slugs (deduplication in rebuild_jobs_listing)

Run from repo root: python3 patch_homepage.py
"""
from pathlib import Path

SCRAPER = Path("scripts/scraper.py")

NEW_FUNCTION = '''

def rebuild_homepage():
    """
    Regenerates index.html with real scraped jobs and current affairs.
    Fixes: stale 2025 content, fake ticker, fake hero stats, fake current affairs.
    """
    from datetime import datetime, date

    yr       = datetime.now().year
    out_path = SITE_ROOT / "index.html"

    jobs_dir    = SITE_ROOT / "jobs"
    affairs_dir = SITE_ROOT / "current-affairs"

    # ── Collect real jobs ──────────────────────────────────────────────────
    SKIP = {"ssc","railway","banking","upsc","defence","police","teaching","state",
            "10th-pass","12th-pass","graduate","all-india","uttar-pradesh","bihar",
            "madhya-pradesh","rajasthan","tamil-nadu","karnataka","maharashtra",
            "gujarat","kerala","engineering","all-india-government-jobs",
            "government-jobs-2026","psu-jobs-2026","graduate-govt-jobs-2026",
            "iti-govt-jobs-2026","mba-govt-jobs-2026","mca-govt-jobs-2026",
            "law-govt-jobs-2026","govt-bank-jobs-2026","govt-jobs-closing-today",
            "non-executive-posts","faculty-posts-recruitment"}

    all_jobs = []
    seen_titles = set()
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir() or job_dir.name in SKIP:
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        meta = get_job_meta_from_html(idx)
        if not meta or not meta.get("title"):
            continue
        # Deduplicate by normalised title
        norm = meta["title"].lower().strip()[:60]
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        all_jobs.append(meta)

    # Take top 8 newest for homepage (prioritise ones with known vacancy count)
    def sort_key(j):
        v = j.get("vacancies","N/A")
        has_vac = 0 if v in ("N/A","","0") else 1
        return (has_vac, j.get("slug",""))
    featured = sorted(all_jobs, key=sort_key, reverse=True)[:8]

    total_jobs      = len(all_jobs)
    total_vacancies = 0
    for j in all_jobs:
        v = j.get("vacancies","N/A")
        try:
            total_vacancies += int(str(v).replace(",","").replace("+","").strip())
        except Exception:
            pass

    # ── Collect real current affairs ──────────────────────────────────────
    CAT_EMOJI = {
        "economy":"📈","science & tech":"🚀","international":"🌍",
        "sports":"🏆","awards":"🏅","government schemes":"🏛️",
        "environment":"🌿","politics":"🗳️","default":"📰"
    }
    affairs = []
    for adir in sorted(affairs_dir.iterdir(), reverse=True):
        if not adir.is_dir():
            continue
        idx = adir / "index.html"
        if not idx.exists():
            continue
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(idx.read_text(encoding="utf-8"), "html.parser")
            h1   = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
            if not title or len(title) < 10:
                continue
            cat_el = soup.find(class_="affair-category") or soup.find("span", string=lambda s: s and s.isupper() and len(s)<30)
            cat    = cat_el.get_text(strip=True).lower() if cat_el else "default"
            summary_el = soup.find("p")
            summary = summary_el.get_text(strip=True)[:120] if summary_el else ""
            affairs.append({
                "slug":    adir.name,
                "title":   title,
                "cat":     cat.upper() if cat != "default" else "CURRENT AFFAIRS",
                "emoji":   CAT_EMOJI.get(cat, "📰"),
                "summary": summary,
            })
        except Exception:
            continue
        if len(affairs) >= 4:
            break

    # ── Build ticker from real job titles ────────────────────────────────
    ticker_items = []
    for j in all_jobs[:12]:
        t = j.get("title","")
        v = j.get("vacancies","")
        ld = j.get("last_date","")
        line = t[:55]
        if v and v != "N/A":   line += f" — {v} Vacancies"
        if ld and ld != "N/A": line += f" | Last: {ld}"
        ticker_items.append(line)
    # Duplicate for seamless scroll
    ticker_spans = "".join(f"<span>{t}</span>\\n            " for t in ticker_items * 2)

    # ── Build job cards ───────────────────────────────────────────────────
    def job_card(job):
        title    = job.get("title","")
        dept     = job.get("dept","")
        slug     = job.get("slug","")
        vac      = job.get("vacancies","N/A")
        loc      = job.get("location","All India") or "All India"
        sal      = job.get("salary","N/A") or "N/A"
        cat      = job.get("category","Graduate") or "Graduate"
        ld       = job.get("last_date","N/A") or "N/A"
        emoji    = job.get("emoji","📋")
        tab_cat  = job.get("tab_cat","state")

        try:
            urgent = False
            for fmt in ["%d %B %Y","%d %b %Y","%Y-%m-%d","%d/%m/%Y","%d-%m-%Y"]:
                try:
                    days = (datetime.strptime(ld, fmt).date() - date.today()).days
                    urgent = days <= 7
                    break
                except ValueError:
                    continue
        except Exception:
            urgent = False

        badge = '<span class="badge badge-urgent">🔥 URGENT</span>' if urgent else '<span class="badge badge-new">🟢 NEW</span>'
        deadline_label = "Last Date to Apply" if ld != "N/A" else "Apply Now"
        deadline_val   = f"⏰ {ld}" if ld != "N/A" else "→ Open"

        sal_display = sal if sal and sal != "N/A" else "As per govt norms"

        return f"""
        <a href="/jobs/{slug}/" class="job-card fade-up" data-category="{tab_cat}">
          <div class="job-card-top">
            <div class="job-dept">
              <div class="dept-icon">{emoji}</div>
              <div>
                <div class="dept-name">{dept}</div>
                <div class="job-title">{title}</div>
              </div>
            </div>
            <div class="job-badges">
              {badge}
              <span class="badge badge-category">{cat}</span>
            </div>
          </div>
          <div class="job-meta">
            <div class="meta-item"><span class="meta-icon">👥</span> {vac} Vacancies</div>
            <div class="meta-item"><span class="meta-icon">📍</span> {loc}</div>
            <div class="meta-item"><span class="meta-icon">💰</span> {sal_display}</div>
          </div>
          <div class="job-deadline">
            <div>
              <div class="deadline-text">{deadline_label}</div>
              <div class="deadline-date">{deadline_val}</div>
            </div>
            <button class="apply-btn">Apply Now →</button>
          </div>
        </a>"""

    job_cards_html = "\\n".join(job_card(j) for j in featured)

    # ── Build current affairs cards ───────────────────────────────────────
    def affair_card(a):
        return f"""
        <a href="/current-affairs/{a['slug']}/" style="background:var(--white);border-radius:10px;padding:16px;border:1.5px solid var(--grey-200);text-decoration:none;color:inherit;display:flex;gap:12px;align-items:flex-start;transition:all 0.2s;" onmouseover="this.style.borderColor='var(--saffron)'" onmouseout="this.style.borderColor='var(--grey-200)'">
          <span style="font-size:1.5rem;flex-shrink:0;">{a['emoji']}</span>
          <div>
            <div style="font-size:0.7rem;color:var(--saffron);font-weight:700;margin-bottom:4px;">{a['cat']}</div>
            <div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--navy);margin-bottom:4px;">{a['title'][:80]}</div>
            <div style="font-size:0.8rem;color:var(--grey-700);">{a['summary']}</div>
          </div>
        </a>"""

    affairs_html = "\\n".join(affair_card(a) for a in affairs) if affairs else """
        <a href="/current-affairs/" style="background:var(--white);border-radius:10px;padding:16px;border:1.5px solid var(--grey-200);text-decoration:none;color:inherit;display:flex;gap:12px;align-items:flex-start;">
          <span style="font-size:1.5rem;">📰</span>
          <div><div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--navy);">Latest Current Affairs</div>
          <div style="font-size:0.8rem;color:var(--grey-700);">Updated daily for SSC, Banking, UPSC exams.</div></div>
        </a>"""

    vac_display  = f"{total_vacancies:,}+" if total_vacancies > 0 else "50,000+"
    jobs_display = f"{total_jobs}+"

    # ── Read existing index.html and do surgical replacements ─────────────
    html = out_path.read_text(encoding="utf-8")

    # 1. Fix meta keywords year
    html = html.replace("govt job 2025", f"govt job {yr}")

    # 2. Fix footer copyright year
    html = html.replace("© 2025 NaukriBulletin", f"© {yr} NaukriBulletin")

    # 3. Fix ticker — replace entire ticker-text div content
    import re
    html = re.sub(
        r'(<div class="ticker-text">).*?(</div>\\s*</div>\\s*</div>\\s*</div>\\s*</div>\\s*<!-- HERO -->)',
        lambda m: m.group(1) + "\\n            " + ticker_spans + "\\n          " + m.group(2),
        html, flags=re.DOTALL
    )

    # 4. Fix hero stats
    html = re.sub(r'<div class="stat-num">1[,\\d]+<span>\\+</span></div>\\s*<div class="stat-label">Active Job Notifications</div>',
        f'<div class="stat-num">{jobs_display}<span></span></div>\\n          <div class="stat-label">Active Job Notifications</div>', html)
    html = re.sub(r'<div class="stat-num">[\\d,]+<span>\\+</span></div>\\s*<div class="stat-label">Total Vacancies</div>',
        f'<div class="stat-num">{vac_display}<span></span></div>\\n          <div class="stat-label">Total Vacancies</div>', html)

    # 5. Fix job cards — replace the jobs-grid div content
    html = re.sub(
        r'(<div class="jobs-grid">).*?(</div>\\s*<!-- AD -->)',
        lambda m: m.group(1) + job_cards_html + "\\n\\n      " + m.group(2),
        html, flags=re.DOTALL
    )

    # 6. Fix current affairs — replace the 3 hardcoded affair cards
    html = re.sub(
        r'(<div style="display: flex; flex-direction: column; gap: 10px;">).*?(</div>\\s*</section>)',
        lambda m: m.group(1) + affairs_html + "\\n\\n      " + m.group(2),
        html, flags=re.DOTALL
    )

    out_path.write_text(html, encoding="utf-8")
    print(f"[HOMEPAGE] ✅ index.html rebuilt — {total_jobs} jobs, {len(affairs)} current affairs, ticker updated")

'''

ANCHOR_FUNCTION = "def rebuild_jobs_listing():"
ANCHOR_CALL     = "    rebuild_jobs_listing()"
NEW_CALL        = "    rebuild_homepage()\n    rebuild_jobs_listing()"


def dedupe_patch():
    """Also patch rebuild_jobs_listing to deduplicate by title."""
    content = SCRAPER.read_text(encoding="utf-8")
    old = '''    print(f"[LISTING] Rebuilding /jobs/ with {len(jobs)} jobs")'''
    new = '''    # Deduplicate by normalised title
    seen = set()
    deduped = []
    for j in jobs:
        key = j.get("title","").lower().strip()[:60]
        if key and key not in seen:
            seen.add(key)
            deduped.append(j)
    jobs = deduped
    print(f"[LISTING] Rebuilding /jobs/ with {len(jobs)} jobs (deduped)")'''
    if old in content and "Deduplicate by normalised title" not in content:
        content = content.replace(old, new, 1)
        SCRAPER.write_text(content, encoding="utf-8")
        print("✅ Deduplication patch applied to rebuild_jobs_listing()")
    else:
        print("⚠  Dedup patch skipped (already applied or anchor not found)")
    return content


def patch():
    content = SCRAPER.read_text(encoding="utf-8")

    if "def rebuild_homepage():" in content:
        print("✅ rebuild_homepage() already exists — skipping function injection")
    else:
        if ANCHOR_FUNCTION not in content:
            print(f"❌ Cannot find '{ANCHOR_FUNCTION}' in scraper.py")
            return
        content = content.replace(ANCHOR_FUNCTION, NEW_FUNCTION + ANCHOR_FUNCTION, 1)
        print("✅ rebuild_homepage() function injected")

    if "rebuild_homepage()" not in content:
        if ANCHOR_CALL not in content:
            print(f"❌ Cannot find '{ANCHOR_CALL}' to wire up call")
            return
        content = content.replace(ANCHOR_CALL, NEW_CALL, 1)
        print("✅ rebuild_homepage() wired into main run")
    else:
        print("✅ rebuild_homepage() call already present")

    SCRAPER.write_text(content, encoding="utf-8")
    dedupe_patch()
    print("\n✅ All patches applied. Run: python3 scripts/scraper.py")


if __name__ == "__main__":
    patch()
