#!/usr/bin/env python3
"""
Patches scripts/scraper.py to add rebuild_syllabus() and call it automatically.
Run once from your repo root:  python3 patch_syllabus.py
"""

from pathlib import Path

SCRAPER = Path("scripts/scraper.py")

# ── The new function to inject ────────────────────────────────────────────────
NEW_FUNCTION = '''

def rebuild_syllabus():
    """
    Auto-generates syllabus/index.html by scanning all job pages.
    Groups them by exam category (SSC / Railway / Banking / UPSC / Defence / Police / Teaching / State).
    Called automatically after every scraper run.
    """
    from datetime import datetime

    jobs_dir  = SITE_ROOT / "jobs"
    out_path  = SITE_ROOT / "syllabus" / "index.html"
    yr        = datetime.now().year

    # Category config: tab_cat → display label, emoji, colour
    CATS = [
        ("ssc",      "SSC",         "📋", "#FF6B00"),
        ("railway",  "Railway",     "🚂", "#1565C0"),
        ("banking",  "Banking",     "🏦", "#2E7D32"),
        ("upsc",     "UPSC / IAS",  "🏛️", "#6A1B9A"),
        ("defence",  "Defence",     "🪖", "#BF360C"),
        ("police",   "Police",      "👮", "#37474F"),
        ("teaching", "Teaching",    "📚", "#00695C"),
        ("state",    "State PSC",   "🏢", "#283593"),
    ]
    cat_map = {c[0]: c for c in CATS}

    # Collect all jobs grouped by tab_cat
    grouped = {c[0]: [] for c in CATS}
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir():
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        meta = get_job_meta_from_html(idx)
        if not meta or not meta.get("title"):
            continue
        cat = meta.get("tab_cat", "state")
        if cat in grouped:
            grouped[cat].append(meta)

    total = sum(len(v) for v in grouped.values())
    print(f"[SYLLABUS] Rebuilding syllabus page with {total} jobs across {len(CATS)} categories")

    # ── Tab buttons ───────────────────────────────────────────────────────────
    tab_buttons = \\'\\n          \\'.join(
        f\\'<button class="stab{\\'  stab-active\\' if i==0 else \\'\\'}" \\'
        f\\'onclick="filterSyllabus(\\'{c[0]}\\',this)">{c[2]} {c[1]}</button>\\'
        for i, c in enumerate(CATS)
    )

    # ── Syllabus cards per category ───────────────────────────────────────────
    def make_section(cat_key):
        cfg = cat_map[cat_key]
        jobs = grouped[cat_key]
        if not jobs:
            return ""

        rows = ""
        for job in jobs[:40]:          # cap at 40 per category
            title     = job.get("title", "")
            slug      = job.get("slug", "")
            last_date = job.get("last_date", "N/A")
            vacancies = job.get("vacancies", "N/A")
            er        = job.get("exam_relevance", "")
            rows += f"""
              <a href="/jobs/{slug}/" class="syl-row" style="display:flex;align-items:center;gap:12px;
                 padding:12px 16px;border-bottom:1px solid var(--grey-200);text-decoration:none;
                 color:inherit;transition:background .1s;" onmouseover="this.style.background=\\'#fffbf5\\'"
                 onmouseout="this.style.background=\\'\\'" >
                <div style="flex:1;min-width:0;">
                  <div style="font-size:0.88rem;font-weight:600;color:var(--navy);
                       white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{title}</div>
                  <div style="font-size:0.75rem;color:var(--grey-400);margin-top:2px;">
                    {"📌 " + er if er else ""}
                  </div>
                </div>
                <div style="display:flex;gap:8px;flex-shrink:0;align-items:center;">
                  <span style="font-size:0.74rem;color:var(--grey-700);">👥 {vacancies}</span>
                  <span style="font-size:0.74rem;color:#E65100;font-weight:600;
                       white-space:nowrap;">⏰ {last_date}</span>
                  <span style="background:var(--navy);color:#fff;padding:4px 10px;
                       border-radius:6px;font-size:0.72rem;font-weight:600;">Syllabus →</span>
                </div>
              </a>"""

        return f"""
        <div class="scat" data-cat="{cat_key}" style="margin-bottom:24px;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="width:38px;height:38px;border-radius:9px;background:{cfg[3]}22;
                 display:flex;align-items:center;justify-content:center;font-size:1.1rem;">{cfg[2]}</div>
            <div>
              <div style="font-family:var(--font-display);font-size:1.05rem;font-weight:700;
                   color:var(--navy);">{cfg[1]} Syllabus {yr}</div>
              <div style="font-size:0.75rem;color:var(--grey-400);">{len(jobs)} active notifications</div>
            </div>
          </div>
          <div style="background:var(--white);border-radius:12px;border:1.5px solid var(--grey-200);
               overflow:hidden;">
            {rows}
            <div style="padding:10px 16px;background:#fafafa;text-align:center;">
              <a href="/jobs/{cat_key}/" style="font-size:0.8rem;color:var(--saffron);
                 font-weight:600;text-decoration:none;">View all {cfg[1]} jobs →</a>
            </div>
          </div>
        </div>"""

    sections_html = "\\n".join(make_section(c[0]) for c in CATS)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exam Syllabus {yr} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="Complete exam syllabus {yr} for SSC CGL, CHSL, Railway NTPC, SBI PO, UPSC, IBPS and 200+ govt exams. Updated daily at NaukriBulletin.in">
  <link rel="canonical" href="https://naukribulletin.in/syllabus/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{
        appId: "89e83d08-e30e-46f9-baec-f0167f8baa35",
        notifyButton: {{ enable: true, size: "medium", position: "bottom-left" }}
      }});
    }});
  </script>
  <style>
    .stab {{
      border: none; background: var(--grey-100); color: var(--grey-700);
      padding: 7px 16px; border-radius: 20px; font-size: 0.82rem;
      font-weight: 600; cursor: pointer; transition: all .15s; white-space: nowrap;
    }}
    .stab:hover {{ background: var(--saffron-pale); color: var(--saffron); }}
    .stab-active {{ background: var(--saffron) !important; color: #fff !important; }}
    .scat {{ transition: opacity .2s; }}
    .scat.hidden {{ display: none; }}
  </style>
</head>
<body>

  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/syllabus/" class="active">Syllabus</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>

  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="color:var(--grey-400);font-size:0.8rem;margin-bottom:8px;">
        <a href="/" style="color:var(--grey-400);text-decoration:none;">Home</a> › Syllabus
      </div>
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        📚 Exam <span style="color:var(--saffron);">Syllabus {yr}</span>
      </h1>
      <p style="color:var(--grey-400);font-size:0.95rem;">{total} active notifications — SSC · Railway · Banking · UPSC · Defence · State PSC</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:0 auto;padding:0 20px;">
    <div class="ad-slot ad-banner">Advertisement</div>
  </div>

  <div class="container">
    <div style="overflow-x:auto;padding-bottom:4px;margin-bottom:20px;">
      <div style="display:flex;gap:8px;min-width:max-content;">
        <button class="stab stab-active" onclick="filterSyllabus(\\'all\\',this)">🗂 All Exams</button>
        {tab_buttons}
      </div>
    </div>

    <div id="syl-sections">
      {sections_html}
    </div>

  </div>

  <footer style="background:var(--navy);color:var(--grey-400);padding:32px 20px;margin-top:48px;text-align:center;font-size:0.82rem;">
    <div style="max-width:1200px;margin:0 auto;">
      <p>© {yr} NaukriBulletin.in — Updated automatically 3× daily</p>
      <div style="margin-top:12px;display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
        <a href="/jobs/" style="color:var(--grey-400);text-decoration:none;">Latest Jobs</a>
        <a href="/current-affairs/" style="color:var(--grey-400);text-decoration:none;">Current Affairs</a>
        <a href="/age-calculator/" style="color:var(--grey-400);text-decoration:none;">Age Calculator</a>
        <a href="/answer-key/" style="color:var(--grey-400);text-decoration:none;">Answer Key</a>
      </div>
    </div>
  </footer>

  <script>
    function filterSyllabus(cat, btn) {{
      document.querySelectorAll('.stab').forEach(b => b.classList.remove('stab-active'));
      btn.classList.add('stab-active');
      document.querySelectorAll('.scat').forEach(s => {{
        if (cat === 'all' || s.dataset.cat === cat) {{
          s.classList.remove('hidden');
        }} else {{
          s.classList.add('hidden');
        }}
      }});
    }}
  </script>
</body>
</html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[SYLLABUS] ✅ Written syllabus/index.html ({total} jobs, {len(CATS)} categories)")

'''

# ── Patch 1: insert function before rebuild_jobs_listing ──────────────────────
ANCHOR_FUNCTION = "def rebuild_jobs_listing():"

# ── Patch 2: call rebuild_syllabus() after rebuild_affairs_listing() ─────────
ANCHOR_CALL = "    rebuild_affairs_listing()"
NEW_CALL    = "    rebuild_affairs_listing()\n    rebuild_syllabus()"


def patch():
    content = SCRAPER.read_text(encoding="utf-8")

    # Check already patched
    if "def rebuild_syllabus():" in content:
        print("✅ Already patched — rebuild_syllabus() already exists in scraper.py")
        return

    # Patch 1: inject function
    if ANCHOR_FUNCTION not in content:
        print(f"❌ Could not find '{ANCHOR_FUNCTION}' in scraper.py")
        return
    content = content.replace(ANCHOR_FUNCTION, NEW_FUNCTION + ANCHOR_FUNCTION, 1)

    # Patch 2: add call
    if ANCHOR_CALL not in content:
        print(f"❌ Could not find '{ANCHOR_CALL}' in scraper.py")
        return
    content = content.replace(ANCHOR_CALL, NEW_CALL, 1)

    SCRAPER.write_text(content, encoding="utf-8")
    print("✅ scraper.py patched — rebuild_syllabus() added and wired in")
    print("   Next scraper run will auto-generate syllabus/index.html")
    print("   To test now: python3 scripts/scraper.py")


if __name__ == "__main__":
    patch()
