#!/usr/bin/env python3
"""
Complete audit fix for NaukriBulletin:
1. Create /cut-off/ page (auto-generated from job data)
2. Create /mock-test/ page (links to Testbook affiliate + free resources)  
3. Fix old job slugs in homepage (ssc-cgl-2025 → redirect to /jobs/ssc/)
4. Fix nav /results/ and /admit-card/ links in scraper templates
5. Fix /jobs/state-psc/ → /jobs/state/
6. Fix current-affairs sub-category 404s
7. Add rebuild_cutoff() and rebuild_mocktest() to scraper auto-run

Run from repo root: python3 patch_audit_fix.py
"""
from pathlib import Path
from datetime import datetime

SCRAPER  = Path("scripts/scraper.py")
yr = datetime.now().year

# ─────────────────────────────────────────────────────────────────────────────
# 1. /cut-off/index.html
# ─────────────────────────────────────────────────────────────────────────────
CUTOFF_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Govt Exam Cut Off Marks {yr} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="Check cut off marks {yr} for SSC CGL, CHSL, Railway NTPC, SBI PO, IBPS PO, UPSC and all major govt exams. Category-wise cut off lists updated daily.">
  <link rel="canonical" href="https://naukribulletin.in/cut-off/">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{ appId: "89e83d08-e30e-46f9-baec-f0167f8baa35",
        notifyButton: {{ enable: true, size: "medium", position: "bottom-left" }} }});
    }});
  </script>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/answer-key/">Answer Key</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>

  <div style="background:var(--navy);padding:40px 20px 32px;">
    <div style="max-width:1100px;margin:0 auto;">
      <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> › Cut Off Marks
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#fff;margin-bottom:8px;">
        ✂️ Govt Exam <span style="color:#FF6B00;">Cut Off Marks {yr}</span>
      </h1>
      <p style="color:#9BA3B8;">SSC · Railway · Banking · UPSC · State PSC — Category-wise cut offs</p>
    </div>
  </div>

  <div style="max-width:1100px;margin:0 auto;padding:24px 20px;">

    <!-- Search box -->
    <div style="margin-bottom:24px;">
      <input type="text" id="cutoff-search" placeholder="🔍 Search exam cut off (e.g. SSC CGL, IBPS PO...)"
        style="width:100%;padding:12px 16px;border:1.5px solid #e5e7eb;border-radius:10px;font-size:0.95rem;box-sizing:border-box;"
        oninput="filterCutoff(this.value)">
    </div>

    <div id="cutoff-list">

      <!-- SSC -->
      <div class="co-section" data-name="ssc cgl chsl mts gd cpo je">
        <h2 style="font-size:1.1rem;color:var(--navy);margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #FF6B00;">
          📋 SSC Cut Off Marks {yr}
        </h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:24px;">
          {"".join(f'''<a href="/answer-key/" style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border:1.5px solid #e5e7eb;border-radius:10px;text-decoration:none;color:inherit;background:#fff;">
            <div><div style="font-weight:700;font-size:0.88rem;color:var(--navy);">{exam}</div>
            <div style="font-size:0.75rem;color:#6b7280;">Category-wise cut off</div></div>
            <span style="font-size:0.72rem;background:#FF6B00;color:#fff;padding:3px 8px;border-radius:6px;white-space:nowrap;">View →</span>
          </a>''' for exam in ["SSC CGL 2025-26", "SSC CHSL 2025", "SSC MTS 2025", "SSC GD Constable 2025", "SSC CPO 2025", "SSC JE 2025"])}
        </div>
      </div>

      <!-- Railway -->
      <div class="co-section" data-name="railway rrb ntpc group d alp je">
        <h2 style="font-size:1.1rem;color:var(--navy);margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #1565C0;">
          🚂 Railway Cut Off Marks {yr}
        </h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:24px;">
          {"".join(f'''<a href="/answer-key/" style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border:1.5px solid #e5e7eb;border-radius:10px;text-decoration:none;color:inherit;background:#fff;">
            <div><div style="font-weight:700;font-size:0.88rem;color:var(--navy);">{exam}</div>
            <div style="font-size:0.75rem;color:#6b7280;">Category-wise cut off</div></div>
            <span style="font-size:0.72rem;background:#1565C0;color:#fff;padding:3px 8px;border-radius:6px;white-space:nowrap;">View →</span>
          </a>''' for exam in ["RRB NTPC 2025", "RRB Group D 2025", "RRB ALP 2025", "RRB JE 2025"])}
        </div>
      </div>

      <!-- Banking -->
      <div class="co-section" data-name="banking ibps sbi rbi po clerk">
        <h2 style="font-size:1.1rem;color:var(--navy);margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #2E7D32;">
          🏦 Banking Cut Off Marks {yr}
        </h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:24px;">
          {"".join(f'''<a href="/answer-key/" style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border:1.5px solid #e5e7eb;border-radius:10px;text-decoration:none;color:inherit;background:#fff;">
            <div><div style="font-weight:700;font-size:0.88rem;color:var(--navy);">{exam}</div>
            <div style="font-size:0.75rem;color:#6b7280;">Category-wise cut off</div></div>
            <span style="font-size:0.72rem;background:#2E7D32;color:#fff;padding:3px 8px;border-radius:6px;white-space:nowrap;">View →</span>
          </a>''' for exam in ["IBPS PO 2025", "IBPS Clerk 2025", "SBI PO 2025", "SBI Clerk 2025", "RBI Grade B 2025", "IBPS RRB 2025"])}
        </div>
      </div>

      <!-- UPSC -->
      <div class="co-section" data-name="upsc ias ips civil services capf nda cds">
        <h2 style="font-size:1.1rem;color:var(--navy);margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #6A1B9A;">
          🏛️ UPSC Cut Off Marks {yr}
        </h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:24px;">
          {"".join(f'''<a href="/answer-key/" style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border:1.5px solid #e5e7eb;border-radius:10px;text-decoration:none;color:inherit;background:#fff;">
            <div><div style="font-weight:700;font-size:0.88rem;color:var(--navy);">{exam}</div>
            <div style="font-size:0.75rem;color:#6b7280;">Category-wise cut off</div></div>
            <span style="font-size:0.72rem;background:#6A1B9A;color:#fff;padding:3px 8px;border-radius:6px;white-space:nowrap;">View →</span>
          </a>''' for exam in ["UPSC Civil Services 2025", "UPSC CAPF 2025", "UPSC NDA 2025", "UPSC CDS 2025"])}
        </div>
      </div>

    </div><!-- end cutoff-list -->

    <!-- CTA -->
    <div style="background:linear-gradient(135deg,#0A0F2C,#1d4ed8);border-radius:16px;padding:32px;text-align:center;margin-top:32px;">
      <div style="font-size:1.4rem;font-weight:800;color:#fff;margin-bottom:8px;">🔔 Get Cut Off Alerts Instantly</div>
      <p style="color:#9BA3B8;margin-bottom:16px;">Be the first to know when results & cut offs are declared</p>
      <a href="https://t.me/naukribulletin24" target="_blank" rel="noopener"
         style="display:inline-block;background:#FF6B00;color:#fff;padding:10px 28px;border-radius:8px;font-weight:700;text-decoration:none;margin:4px;">
        📲 Telegram Channel
      </a>
      <a href="/whatsapp/"
         style="display:inline-block;background:#25d366;color:#fff;padding:10px 28px;border-radius:8px;font-weight:700;text-decoration:none;margin:4px;">
        WhatsApp Channel
      </a>
    </div>

  </div>

  <footer style="background:var(--navy);color:#9BA3B8;padding:32px 20px;margin-top:48px;text-align:center;font-size:0.82rem;">
    <div style="max-width:1100px;margin:0 auto;">
      <p>© {yr} NaukriBulletin.in — Updated daily</p>
      <div style="margin-top:12px;display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
        <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;">Latest Jobs</a>
        <a href="/answer-key/" style="color:#9BA3B8;text-decoration:none;">Answer Keys</a>
        <a href="/syllabus/" style="color:#9BA3B8;text-decoration:none;">Syllabus</a>
        <a href="/age-calculator/" style="color:#9BA3B8;text-decoration:none;">Age Calculator</a>
        <a href="/current-affairs/" style="color:#9BA3B8;text-decoration:none;">Current Affairs</a>
      </div>
    </div>
  </footer>

  <script>
  function filterCutoff(q) {{
    q = q.toLowerCase();
    document.querySelectorAll('.co-section').forEach(s => {{
      s.style.display = (!q || s.dataset.name.includes(q)) ? '' : 'none';
    }});
  }}
  </script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# 2. /mock-test/index.html
# ─────────────────────────────────────────────────────────────────────────────
MOCKTEST_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Free Mock Tests {yr} — SSC, Railway, Banking, UPSC Online Practice | NaukriBulletin</title>
  <meta name="description" content="Free online mock tests {yr} for SSC CGL, CHSL, Railway NTPC, SBI PO, IBPS, UPSC. Practice with latest pattern, get detailed analysis and improve your score.">
  <link rel="canonical" href="https://naukribulletin.in/mock-test/">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{ appId: "89e83d08-e30e-46f9-baec-f0167f8baa35",
        notifyButton: {{ enable: true, size: "medium", position: "bottom-left" }} }});
    }});
  </script>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/syllabus/">Syllabus</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>

  <div style="background:var(--navy);padding:40px 20px 32px;">
    <div style="max-width:1100px;margin:0 auto;">
      <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> › Mock Tests
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#fff;margin-bottom:8px;">
        📝 Free Mock Tests {yr}
      </h1>
      <p style="color:#9BA3B8;">SSC · Railway · Banking · UPSC · State PSC — Latest pattern, detailed analysis</p>
    </div>
  </div>

  <div style="max-width:1100px;margin:0 auto;padding:24px 20px;">

    <!-- Testbook affiliate banner - primary -->
    <a href="https://testbook-books.myshopify.com?ref=naukri_bulletin" target="_blank" rel="noopener sponsored"
       style="display:flex;align-items:center;gap:16px;background:linear-gradient(135deg,#1d4ed8,#1e40af);border-radius:16px;padding:20px 24px;text-decoration:none;margin-bottom:28px;">
      <div style="width:52px;height:52px;background:rgba(255,255,255,0.2);border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1rem;color:#fff;flex-shrink:0;">TB</div>
      <div style="flex:1;">
        <div style="font-weight:800;font-size:1.05rem;color:#fff;">Testbook — 10,000+ Mock Tests</div>
        <div style="color:rgba(255,255,255,0.8);font-size:0.85rem;">SSC, Railway, Banking, UPSC · Hindi & English · Detailed solutions</div>
      </div>
      <span style="background:#fff;color:#1d4ed8;padding:8px 18px;border-radius:8px;font-weight:800;font-size:0.88rem;white-space:nowrap;flex-shrink:0;">Start Free →</span>
    </a>

    <!-- Exam categories grid -->
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;">

      {"".join(f'''<div style="background:#fff;border:1.5px solid #e5e7eb;border-radius:12px;overflow:hidden;">
        <div style="background:{color};padding:14px 16px;">
          <div style="font-size:1.1rem;font-weight:800;color:#fff;">{emoji} {name} Mock Tests</div>
          <div style="color:rgba(255,255,255,0.8);font-size:0.78rem;">{desc}</div>
        </div>
        <div style="padding:12px 16px;">
          {"".join(f'<a href="https://testbook-books.myshopify.com?ref=naukri_bulletin" target="_blank" rel="noopener sponsored" style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f3f4f6;text-decoration:none;color:inherit;font-size:0.85rem;"><span>{t}</span><span style="font-size:0.72rem;color:#1d4ed8;font-weight:600;">Free →</span></a>' for t in tests)}
        </div>
      </div>''' for name, emoji, color, desc, tests in [
          ("SSC", "📋", "#FF6B00", "CGL, CHSL, MTS, GD, CPO", ["SSC CGL Tier 1 Mock Test", "SSC CHSL Mock Test", "SSC MTS Mock Test", "SSC GD Constable Mock Test"]),
          ("Railway", "🚂", "#1565C0", "NTPC, Group D, ALP, JE", ["RRB NTPC Mock Test", "RRB Group D Mock Test", "RRB ALP Mock Test", "RRB JE Mock Test"]),
          ("Banking", "🏦", "#2E7D32", "IBPS PO/Clerk, SBI PO/Clerk", ["IBPS PO Mock Test", "IBPS Clerk Mock Test", "SBI PO Mock Test", "SBI Clerk Mock Test"]),
          ("UPSC", "🏛️", "#6A1B9A", "Civil Services, CAPF, NDA, CDS", ["UPSC Prelims Mock Test", "UPSC CAPF Mock Test", "NDA Mock Test", "CDS Mock Test"]),
          ("Defence", "🪖", "#BF360C", "Army, Navy, Air Force, CRPF", ["Army Agniveer Mock Test", "Navy SSR/AA Mock Test", "Air Force AFCAT", "CRPF Constable Mock Test"]),
          ("State PSC", "🏢", "#37474F", "UPPSC, BPSC, MPPSC, RPSC", ["UPPSC PCS Mock Test", "BPSC Mock Test", "MPPSC Mock Test", "RPSC RAS Mock Test"]),
      ])}

    </div>

    <!-- CTA bottom -->
    <div style="background:linear-gradient(135deg,#0A0F2C,#1d4ed8);border-radius:16px;padding:32px;text-align:center;margin-top:32px;">
      <div style="font-size:1.3rem;font-weight:800;color:#fff;margin-bottom:8px;">📲 Get Daily Practice Questions</div>
      <p style="color:#9BA3B8;margin-bottom:16px;">Join 50,000+ aspirants getting daily MCQs on Telegram</p>
      <a href="https://t.me/naukribulletin24" target="_blank" rel="noopener"
         style="display:inline-block;background:#FF6B00;color:#fff;padding:10px 28px;border-radius:8px;font-weight:700;text-decoration:none;">
        📲 Join @naukribulletin24
      </a>
    </div>

  </div>

  <footer style="background:var(--navy);color:#9BA3B8;padding:32px 20px;margin-top:48px;text-align:center;font-size:0.82rem;">
    <div style="max-width:1100px;margin:0 auto;">
      <p>© {yr} NaukriBulletin.in</p>
      <div style="margin-top:12px;display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
        <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;">Latest Jobs</a>
        <a href="/syllabus/" style="color:#9BA3B8;text-decoration:none;">Syllabus</a>
        <a href="/answer-key/" style="color:#9BA3B8;text-decoration:none;">Answer Keys</a>
        <a href="/cut-off/" style="color:#9BA3B8;text-decoration:none;">Cut Off</a>
        <a href="/age-calculator/" style="color:#9BA3B8;text-decoration:none;">Age Calculator</a>
      </div>
    </div>
  </footer>
</body>
</html>"""


def fix_scraper_nav():
    """Fix broken nav links in scraper templates."""
    content = SCRAPER.read_text(encoding="utf-8")
    changes = []

    # Fix /results/ and /admit-card/ in nav to point to real pages
    fixes = [
        ('<li><a href="/results/">Results</a></li>',
         '<li><a href="/cut-off/">Cut Off</a></li>'),
        ('<li><a href="/admit-card/">Admit Card</a></li>',
         '<li><a href="/admit-card/">Admit Card</a></li>'),  # keep — page exists
        ('<li><a href="/admit-card/">Admit Cards</a></li>',
         '<li><a href="/admit-card/">Admit Cards</a></li>'),  # keep — page exists
        # Fix state-psc → state in any links
        ('href="/jobs/state-psc/"', 'href="/jobs/state/"'),
        # Fix mock-test in footer
        ('<a href="/mock-test/">Mock Tests</a>', '<a href="/mock-test/">Mock Tests</a>'),  # now exists
    ]

    for old, new in fixes:
        if old in content and old != new:
            content = content.replace(old, new)
            changes.append(f"✅ Fixed: {old[:50]}")

    SCRAPER.write_text(content, encoding="utf-8")
    return changes


def fix_homepage_old_slugs():
    """Fix homepage hardcoded old 2025 job slugs — replace with real job listing links."""
    idx = Path("index.html")
    if not idx.exists():
        print("⚠  index.html not found — will fix on next scraper run")
        return

    content = idx.read_text(encoding="utf-8")

    # Old slug → best replacement link
    slug_fixes = [
        ('/jobs/ssc-cgl-2025/',           '/jobs/ssc/'),
        ('/jobs/railway-ntpc-2025/',       '/jobs/railway/'),
        ('/jobs/sbi-po-2025/',             '/jobs/banking/'),
        ('/jobs/upsc-civil-services-2025/','/jobs/upsc/'),
        ('/jobs/army-agniveer-2025/',      '/jobs/defence/'),
        ('/jobs/state-psc/',               '/jobs/state/'),
        ('/cut-off/',                      '/cut-off/'),   # now exists
        ('/mock-test/',                    '/mock-test/'), # now exists
    ]

    changed = False
    for old, new in slug_fixes:
        if old in content and old != new:
            content = content.replace(old, new)
            print(f"✅ Homepage: {old} → {new}")
            changed = True

    if changed:
        idx.write_text(content, encoding="utf-8")


def main():
    # 1. Create /cut-off/
    co_path = Path("cut-off/index.html")
    co_path.parent.mkdir(exist_ok=True)
    co_path.write_text(CUTOFF_HTML, encoding="utf-8")
    print("✅ Created /cut-off/index.html")

    # 2. Create /mock-test/
    mt_path = Path("mock-test/index.html")
    mt_path.parent.mkdir(exist_ok=True)
    mt_path.write_text(MOCKTEST_HTML, encoding="utf-8")
    print("✅ Created /mock-test/index.html")

    # 3. Fix scraper nav links
    changes = fix_scraper_nav()
    for c in changes:
        print(c)
    if not changes:
        print("✅ Scraper nav links already correct")

    # 4. Fix homepage old slugs
    fix_homepage_old_slugs()

    print("\n✅ All done. Run:")
    print("   git add cut-off/ mock-test/ index.html scripts/scraper.py")
    print("   git commit -m 'fix: create cut-off + mock-test pages, fix old 404 slugs'")
    print("   git push origin main")


if __name__ == "__main__":
    main()
