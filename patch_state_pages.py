#!/usr/bin/env python3
"""
NaukriBulletin — patch_state_pages.py
Generates SEO landing pages for:
  - Every state:         /jobs/kerala/, /jobs/uttar-pradesh/, etc.
  - Every qualification: /jobs/graduate/, /jobs/10th-pass/, etc.
  - Extra hub pages:     /jobs/all-india/, /jobs/psu-jobs-2026/, etc.

Run from repo root:
    python3 patch_state_pages.py

These pages capture high-volume searches like:
  "Kerala govt jobs 2026"          — 40,000+ monthly searches
  "UP sarkari naukri 2026"         — 80,000+ monthly searches
  "10th pass govt job 2026"        — 50,000+ monthly searches
  "graduate govt jobs 2026"        — 60,000+ monthly searches
"""

import re
from pathlib import Path
from datetime import datetime, date
from bs4 import BeautifulSoup

SITE_ROOT = Path(__file__).parent
SITE_URL  = "https://naukribulletin.in"
YR        = datetime.now().year

# ─── Pages to skip when scanning for real job pages ───────────────────────────
SKIP_SLUGS = {
    "ssc","railway","banking","upsc","defence","police","teaching","state",
    "10th-pass","12th-pass","graduate","post-graduate","engineering","all-india",
    "uttar-pradesh","bihar","madhya-pradesh","rajasthan","tamil-nadu","karnataka",
    "maharashtra","gujarat","kerala","delhi","odisha","assam","punjab","haryana",
    "andhra-pradesh","telangana","west-bengal","chhattisgarh","himachal-pradesh",
    "all-india-government-jobs","government-jobs-2026","psu-jobs-2026",
    "graduate-govt-jobs-2026","iti-govt-jobs-2026","mba-govt-jobs-2026",
    "mca-govt-jobs-2026","law-govt-jobs-2026","govt-bank-jobs-2026",
    "govt-jobs-closing-today","non-executive-posts","faculty-posts-recruitment",
    "indian-railways-jobs","combined-defence-services","banking",
    "national-defence-academy-naval-academy-exam","all-india-government-jobs",
    "driver-cum-mechanic-light-motor-vehicle","non-executive-posts",
    "pharmacist-gr-ii-homoeo","iaf-agniveer-vayu","nabard-specialist-jobs",
    "sbi-job-openings","indian-railway-recruitment-2026",
}

# ─── State config: search slug → display name, search terms ───────────────────
STATES = [
    ("kerala",           "Kerala",           ["Kerala PSC", "Kerala", "KPSC"]),
    ("uttar-pradesh",    "Uttar Pradesh",     ["Uttar Pradesh", "UP", "UPPSC", "Lucknow"]),
    ("gujarat",          "Gujarat",           ["Gujarat", "GPSC", "GSSSB", "GSRTC"]),
    ("odisha",           "Odisha",            ["Odisha", "Odisha PSC"]),
    ("delhi",            "Delhi",             ["Delhi", "DSSSB", "New Delhi"]),
    ("maharashtra",      "Maharashtra",       ["Maharashtra", "MPSC", "Mumbai"]),
    ("tamil-nadu",       "Tamil Nadu",        ["Tamil Nadu", "TNPSC"]),
    ("assam",            "Assam",             ["Assam", "APSC"]),
    ("chhattisgarh",     "Chhattisgarh",      ["Chhattisgarh", "CG Vyapam", "CGPSC"]),
    ("punjab",           "Punjab",            ["Punjab", "PPSC", "PSSSB"]),
    ("haryana",          "Haryana",           ["Haryana", "HPSC"]),
    ("andhra-pradesh",   "Andhra Pradesh",    ["Andhra Pradesh", "APPSC", "TGPSC"]),
    ("telangana",        "Telangana",         ["Telangana", "TGPSC"]),
    ("rajasthan",        "Rajasthan",         ["Rajasthan", "RPSC"]),
    ("west-bengal",      "West Bengal",       ["West Bengal", "WBPSC"]),
    ("himachal-pradesh", "Himachal Pradesh",  ["Himachal Pradesh", "HPPSC", "HP"]),
    ("bihar",            "Bihar",             ["Bihar", "BPSC"]),
    ("madhya-pradesh",   "Madhya Pradesh",    ["Madhya Pradesh", "MPPSC", "MP"]),
    ("karnataka",        "Karnataka",         ["Karnataka", "KPSC", "KSP"]),
    ("jharkhand",        "Jharkhand",         ["Jharkhand", "JPSC"]),
]

# ─── Qualification config ─────────────────────────────────────────────────────
QUALS = [
    ("10th-pass",     "10th Pass",     "Matriculation / 10th pass",
     ["10th", "matriculation", "sslc", "class 10", "high school"]),
    ("12th-pass",     "12th Pass",     "Intermediate / 12th pass",
     ["12th", "intermediate", "hsc", "plus two", "class 12", "higher secondary"]),
    ("graduate",      "Graduate",      "Any degree (BA / B.Sc / B.Com / BBA)",
     ["graduate", "degree", "b.sc", "b.com", "ba ", "bba", "bachelor", "graduation"]),
    ("engineering",   "Engineering",   "B.Tech / B.E / Diploma in Engineering",
     ["engineer", "b.tech", "b.e", "diploma in", "mechanical", "electrical", "civil",
      "computer science", "it ", "electronics"]),
    ("post-graduate", "Post Graduate", "Masters / MBA / M.Tech / PhD",
     ["post graduate", "master", "mba", "m.tech", "m.sc", "m.com", "phd", "pg "]),
]

PAGES_WRITTEN = []


# ─── Helper: read job metadata from HTML ─────────────────────────────────────

def get_job_meta(html_path):
    try:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        h1   = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title or len(title) < 5:
            return None

        rows = soup.find_all("tr")
        data = {}
        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 2:
                data[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)

        dept_tag = soup.find(style=lambda s: s and "letter-spacing" in s and "FF6B00" in s)
        dept     = dept_tag.get_text(strip=True).title() if dept_tag else ""

        return {
            "slug":       html_path.parent.name,
            "title":      title,
            "dept":       dept,
            "last_date":  data.get("last date", "N/A"),
            "vacancies":  data.get("total vacancies", "N/A"),
            "salary":     data.get("salary / pay scale", "N/A"),
            "location":   data.get("location", "All India"),
            "qual":       data.get("qualification", ""),
        }
    except Exception:
        return None


def all_jobs():
    jobs_dir = SITE_ROOT / "jobs"
    out = []
    seen = set()
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir() or job_dir.name in SKIP_SLUGS:
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        meta = get_job_meta(idx)
        if meta and meta["title"] and meta["slug"] not in seen:
            seen.add(meta["slug"])
            out.append(meta)
    return out


# ─── HTML generator for listing pages ────────────────────────────────────────

NAV = f"""  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/" class="active">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>"""

FOOTER = f"""  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© {YR} NaukriBulletin.in — All Rights Reserved</p>
        <p>
          <a href="/privacy/" style="color:var(--grey-400);text-decoration:none;margin-right:16px;">Privacy Policy</a>
          <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a>
        </p>
      </div>
    </div>
  </footer>"""

GA = """  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>"""


def urgency_badge(last_date):
    try:
        for fmt in ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                days = (datetime.strptime(last_date, fmt).date() - date.today()).days
                if days <= 7:
                    return '<span style="background:#FFF3E8;color:#E65100;padding:3px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;">🔥 URGENT</span>'
                return '<span style="background:#E8F5E9;color:#2E7D32;padding:3px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;">🟢 NEW</span>'
            except ValueError:
                continue
    except Exception:
        pass
    return '<span style="background:#E8F5E9;color:#2E7D32;padding:3px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;">🟢 NEW</span>'


def job_card_html(job):
    badge = urgency_badge(job["last_date"])
    sal   = job["salary"] if job["salary"] not in ("N/A", "", None) else "As per govt norms"
    return f"""
      <a href="/jobs/{job['slug']}/" style="display:block;background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:18px 20px;text-decoration:none;color:inherit;transition:border-color 0.2s;" onmouseover="this.style.borderColor='#FF6B00'" onmouseout="this.style.borderColor='#ECEEF2'">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:10px;">
          <div>
            <div style="font-size:0.72rem;color:#9BA3B8;font-weight:500;margin-bottom:3px;">{job['dept']}</div>
            <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#0A0F2C;line-height:1.3;">{job['title']}</div>
          </div>
          {badge}
        </div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;">
          <span style="font-size:0.8rem;color:#4A5270;">👥 {job['vacancies']}</span>
          <span style="font-size:0.8rem;color:#4A5270;">📍 {job['location']}</span>
          <span style="font-size:0.8rem;color:#4A5270;">💰 {sal}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid #ECEEF2;">
          <span style="font-size:0.8rem;color:#E65100;font-weight:600;">⏰ Last Date: {job['last_date']}</span>
          <span style="background:#0A0F2C;color:#fff;padding:5px 14px;border-radius:6px;font-size:0.78rem;font-weight:600;">Apply →</span>
        </div>
      </a>"""


def schema_breadcrumb(name, slug):
    return f"""  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},
      {{"@type":"ListItem","position":2,"name":"Jobs","item":"{SITE_URL}/jobs/"}},
      {{"@type":"ListItem","position":3,"name":"{name}","item":"{SITE_URL}/jobs/{slug}/"}}
    ]
  }}
  </script>"""


def write_page(slug, title, description, h1_text, subtitle, jobs, keywords=""):
    cards = "\n".join(job_card_html(j) for j in jobs)
    count = len(jobs)
    page  = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="keywords" content="{keywords}">
  <link rel="canonical" href="{SITE_URL}/jobs/{slug}/">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{SITE_URL}/jobs/{slug}/">
  <meta property="og:type" content="website">
  <meta property="og:image" content="{SITE_URL}/assets/logo-256.png">
  <meta name="robots" content="index, follow">
{schema_breadcrumb(h1_text, slug)}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <link rel="icon" type="image/png" href="/favicon.png">
{GA}
</head>
<body>
{NAV}

  <div style="background:#0A0F2C;padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="color:#9BA3B8;font-size:0.8rem;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> ›
        <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;">Jobs</a> ›
        <span>{h1_text}</span>
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#fff;margin-bottom:8px;">
        {h1_text}
      </h1>
      <p style="color:#9BA3B8;font-size:0.95rem;">{subtitle}</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:32px auto;padding:0 20px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <span style="font-size:0.85rem;color:#4A5270;"><strong>{count}</strong> active job notifications</span>
      <a href="/alerts/" style="background:#FF6B00;color:#fff;padding:8px 16px;border-radius:8px;font-size:0.82rem;font-weight:600;text-decoration:none;">🔔 Get Free Alerts</a>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px;">
{cards}
    </div>
    <div style="margin-top:32px;background:#FFF3E8;border-radius:12px;padding:20px 24px;">
      <h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#0A0F2C;margin-bottom:8px;">{h1_text} — How to Apply</h2>
      <p style="font-size:0.88rem;color:#4A5270;line-height:1.7;">
        Click on any job above to see full details including eligibility, salary, last date, and the official apply link.
        All jobs are sourced directly from official government websites. Subscribe to our
        <a href="https://t.me/naukribulletin24" style="color:#FF6B00;">Telegram channel</a>
        for instant alerts.
      </p>
    </div>
    <div style="margin-top:24px;text-align:center;">
      <a href="/jobs/" style="color:#FF6B00;font-size:0.88rem;font-weight:600;text-decoration:none;">← View all government jobs</a>
    </div>
  </div>

{FOOTER}
</body>
</html>"""

    out_dir  = SITE_ROOT / "jobs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    PAGES_WRITTEN.append(f"/jobs/{slug}/  ({count} jobs)")
    print(f"  [WRITTEN] /jobs/{slug}/ — {count} jobs")


# ─── Generate state pages ─────────────────────────────────────────────────────

def generate_state_pages(jobs):
    print("\n[STATE PAGES]")
    for slug, name, keywords in STATES:
        kw_lower = [k.lower() for k in keywords]
        matched  = [
            j for j in jobs
            if any(k in (j["location"] or "").lower() or
                   k in (j["title"] or "").lower() or
                   k in (j["dept"] or "").lower()
                   for k in kw_lower)
        ]
        # Always write the page even if 0 jobs — it will auto-fill as scraper runs
        write_page(
            slug      = slug,
            title     = f"{name} Govt Jobs {YR} — Sarkari Naukri {name} | NaukriBulletin",
            description = f"Latest {name} government jobs {YR}. {name} PSC, state dept & central govt vacancies. Check eligibility, last date & apply online at NaukriBulletin.in",
            h1_text   = f"{name} Govt Jobs {YR}",
            subtitle  = f"{len(matched)} active notifications — {name} PSC, state departments & central govt",
            jobs      = matched,
            keywords  = f"{name.lower()} govt job, {name.lower()} sarkari naukri, {name.lower()} psc, {name.lower()} government vacancy {YR}",
        )


# ─── Generate qualification pages ─────────────────────────────────────────────

def generate_qual_pages(jobs):
    print("\n[QUALIFICATION PAGES]")
    for slug, label, full_label, keywords in QUALS:
        kw_lower = [k.lower() for k in keywords]
        matched  = [
            j for j in jobs
            if any(k in (j["qual"] or "").lower() or
                   k in (j["title"] or "").lower()
                   for k in kw_lower)
        ]
        write_page(
            slug      = slug,
            title     = f"{label} Govt Jobs {YR} — {full_label} Sarkari Naukri | NaukriBulletin",
            description = f"Latest government jobs {YR} for {full_label} candidates. SSC, Railway, Banking, PSC vacancies. Check eligibility, last date & apply online.",
            h1_text   = f"{label} Govt Jobs {YR}",
            subtitle  = f"{len(matched)} active notifications for {full_label} candidates",
            jobs      = matched,
            keywords  = f"{label.lower()} govt job {YR}, {label.lower()} sarkari naukri, government job for {label.lower()}, {label.lower()} pass vacancy",
        )


# ─── Generate extra hub pages ─────────────────────────────────────────────────

def generate_hub_pages(jobs):
    print("\n[HUB PAGES]")

    # All India (central govt jobs)
    central_keywords = ["ssc", "upsc", "rrb", "railway", "ibps", "sbi", "rbi",
                        "drdo", "isro", "aiims", "esic", "bsnl", "ntpc", "ongc",
                        "coal india", "bhel", "sail", "hal", "bpcl", "indian",
                        "central", "national", "all india"]
    central = [j for j in jobs if any(k in (j["dept"] or j["title"] or "").lower() for k in central_keywords)]
    write_page(
        slug="all-india-government-jobs",
        title=f"All India Govt Jobs {YR} — Central Government Vacancies | NaukriBulletin",
        description=f"All India central government jobs {YR}. SSC, Railway, UPSC, Banking, Defence, PSU vacancies. Latest notifications from official sources.",
        h1_text=f"All India Govt Jobs {YR}",
        subtitle=f"{len(central)} central government notifications — SSC, Railway, UPSC, Banking, Defence",
        jobs=central,
        keywords=f"all india govt job {YR}, central government jobs, sarkari naukri all india, central govt vacancy",
    )

    # PSU jobs
    psu_kw = ["ntpc", "ongc", "bhel", "sail", "hal", "bpcl", "hpcl", "iocl",
              "coal india", "power", "nlc", "gail", "bsnl", "mtnl", "rites",
              "irctc", "rvnl", "railtel", "nfl", "rcfl", "hll", "mecon"]
    psu = [j for j in jobs if any(k in (j["dept"] or j["title"] or "").lower() for k in psu_kw)]
    write_page(
        slug="psu-jobs-2026",
        title=f"PSU Jobs {YR} — Public Sector Undertaking Vacancies | NaukriBulletin",
        description=f"Latest PSU jobs {YR}. NTPC, ONGC, BHEL, SAIL, HAL, BPCL and more. Direct recruitment notifications from official PSU websites.",
        h1_text=f"PSU Jobs {YR}",
        subtitle=f"{len(psu)} Public Sector Undertaking vacancies — NTPC, ONGC, BHEL, SAIL and more",
        jobs=psu,
        keywords=f"PSU jobs {YR}, public sector jobs, PSU vacancy, NTPC jobs, ONGC jobs, BHEL recruitment",
    )

    # Govt jobs closing today / this week
    urgent_jobs = []
    for j in jobs:
        ld = j.get("last_date", "N/A")
        if ld == "N/A":
            continue
        for fmt in ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                days = (datetime.strptime(ld, fmt).date() - date.today()).days
                if 0 <= days <= 7:
                    urgent_jobs.append(j)
                break
            except ValueError:
                continue
    write_page(
        slug="govt-jobs-closing-today",
        title=f"Govt Jobs Last Date Today & This Week {YR} | NaukriBulletin",
        description=f"Government jobs with last date today or closing this week {YR}. Don't miss the deadline — apply now for SSC, Railway, Banking, State PSC vacancies.",
        h1_text="Govt Jobs Closing This Week",
        subtitle=f"{len(urgent_jobs)} vacancies closing within 7 days — apply before the deadline",
        jobs=urgent_jobs,
        keywords=f"govt job last date today, government job deadline this week, sarkari naukri last date {YR}",
    )


# ─── Update sitemap with new pages ────────────────────────────────────────────

def update_sitemap():
    sitemap_path = SITE_ROOT / "sitemap.xml"
    if not sitemap_path.exists():
        print("[SITEMAP] sitemap.xml not found — skipping")
        return

    content  = sitemap_path.read_text(encoding="utf-8")
    today    = date.today().isoformat()
    added    = 0

    for line in PAGES_WRITTEN:
        slug_part = line.split("/jobs/")[1].split("/")[0]
        url       = f"{SITE_URL}/jobs/{slug_part}/"
        if url in content:
            continue
        entry = f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>"""
        content = content.replace("</urlset>", entry + "\n</urlset>")
        added += 1

    sitemap_path.write_text(content, encoding="utf-8")
    print(f"[SITEMAP] Added {added} new URLs to sitemap.xml")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NaukriBulletin — State & Qualification Page Generator")
    print("="*60)

    print("\nScanning existing job pages...")
    jobs = all_jobs()
    print(f"Found {len(jobs)} real job pages to work with")

    generate_state_pages(jobs)
    generate_qual_pages(jobs)
    generate_hub_pages(jobs)
    update_sitemap()

    print("\n" + "="*60)
    print(f"✅ Done — {len(PAGES_WRITTEN)} pages written:")
    for p in PAGES_WRITTEN:
        print(f"  {p}")
    print("="*60)
    print("\nNext steps:")
    print("  git add -A")
    print("  git commit -m 'feat: add state + qualification landing pages'")
    print("  git push")
    print("\nThen submit sitemap in Google Search Console:")
    print("  https://search.google.com/search-console")
