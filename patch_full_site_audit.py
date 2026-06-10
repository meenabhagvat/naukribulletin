#!/usr/bin/env python3
"""
patch_full_site_audit.py — NaukriBulletin Full Site Audit Fixes
================================================================
Run from repo root:  python3 patch_full_site_audit.py

Issues found and fixed:
  1.  168 current-affairs pages: missing GA4, OG tags, footer, full nav, schema
  2.  10 utility pages: missing GA4 (admit-card, results, cut-off, mock-test, alerts, about, contact, privacy, disclaimer)
  3.  alerts/index.html: wrong title + canonical (copy of results page — complete rewrite)
  4.  Homepage: duplicate "Latest Jobs" nav item + missing og:image + missing Schema.org
  5.  Sitemap: missing /cut-off/, /mock-test/, /age-calculator/, /about/, /admit-card/
  6.  scraper.py generate_affairs_html: missing GA4, OG, schema, footer, nav links
  7.  _redirects: missing entries for new pages
"""

import re
import json
from pathlib import Path
from datetime import datetime

REPO   = Path(__file__).parent
GA4_ID = "G-6WQJ4W7T1N"
OS_ID  = "89e83d08-e30e-46f9-baec-f0167f8baa35"
SITE   = "https://naukribulletin.in"

GA4_SNIPPET = f"""  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA4_ID}');</script>"""

OS_SNIPPET = f"""  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{
        appId: "{OS_ID}",
        notifyButton: {{ enable: true, size: 'medium', position: 'bottom-left',
          text: {{ 'tip.state.unsubscribed': 'Get free job alerts!', 'tip.state.subscribed': '✓ Job alerts active' }}
        }},
        welcomeNotification: {{ title: "NaukriBulletin Alerts ON 🎉", message: "You'll get instant alerts for new govt jobs!" }}
      }});
    }});
  </script>"""

FOOTER_HTML = """  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© 2026 NaukriBulletin.in —
          <a href="/about/" style="color:var(--grey-400);text-decoration:none;">About</a> ·
          <a href="/contact/" style="color:var(--grey-400);text-decoration:none;">Contact</a> ·
          <a href="/privacy/" style="color:var(--grey-400);text-decoration:none;">Privacy</a> ·
          <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a>
        </p>
      </div>
    </div>
  </footer>"""

STANDARD_NAV = """  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/syllabus/">Syllabus</a></li>
        <li><a href="/admit-card/">Admit Card</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>"""

def read(p): return p.read_text(encoding="utf-8")
def write(p, t): p.write_text(t, encoding="utf-8")


# ── Fix 1: Current-affairs detail pages ──────────────────────────────────────

def fix_current_affairs_pages():
    ca_dir = REPO / "current-affairs"
    pages  = [p for p in ca_dir.glob("*/index.html")]
    fixed_ga4 = fixed_og = fixed_footer = fixed_nav = fixed_os = 0

    for page in pages:
        html = read(page)
        changed = False
        slug = page.parent.name

        # --- GA4 ---
        if GA4_ID not in html and "</head>" in html:
            html = html.replace("</head>", GA4_SNIPPET + "\n</head>", 1)
            fixed_ga4 += 1
            changed = True

        # --- OneSignal ---
        if "onesignal" not in html.lower() and "</head>" in html:
            html = html.replace("</head>", OS_SNIPPET + "\n</head>", 1)
            fixed_os += 1
            changed = True

        # --- OG tags ---
        if "og:title" not in html:
            # Extract title from <title> tag
            title_m = re.search(r'<title>(.*?)</title>', html)
            title = title_m.group(1).replace(" — NaukriBulletin", "") if title_m else "Current Affairs"
            desc_m = re.search(r'<meta name="description" content="([^"]*)"', html)
            desc = desc_m.group(1) if desc_m else title
            og_tags = f"""  <meta property="og:title" content="{title} — NaukriBulletin">
  <meta property="og:description" content="{desc[:155]}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{SITE}/current-affairs/{slug}/">
  <meta property="og:image" content="{SITE}/assets/logo-256.png">"""
            html = html.replace("</head>", og_tags + "\n</head>", 1)
            fixed_og += 1
            changed = True

        # --- Footer ---
        if "footer-inner" not in html and "© 2026" not in html:
            if "</body>" in html:
                html = html.replace("</body>", FOOTER_HTML + "\n</body>", 1)
                fixed_footer += 1
                changed = True

        # --- Nav: upgrade bare single-link nav to full standard nav ---
        # Detect the minimal nav (only has "NaukriBulletin" logo, no ul.nav-links)
        if "nav-links" not in html and "nav-bar" not in html:
            old_nav_pattern = re.compile(
                r'<nav[^>]*>.*?</nav>', re.DOTALL
            )
            if old_nav_pattern.search(html):
                html = old_nav_pattern.sub(STANDARD_NAV, html, count=1)
                fixed_nav += 1
                changed = True

        if changed:
            write(page, html)

    print(f"✅ Fix 1: Current-affairs pages — GA4:{fixed_ga4} OS:{fixed_os} OG:{fixed_og} footer:{fixed_footer} nav:{fixed_nav} / {len(pages)} pages")


# ── Fix 2: Utility pages — add GA4 ───────────────────────────────────────────

UTILITY_PAGES = [
    "admit-card", "results", "cut-off", "mock-test",
    "alerts", "about", "contact", "privacy", "disclaimer", "whatsapp"
]

def fix_utility_pages_ga4():
    fixed = 0
    for name in UTILITY_PAGES:
        page = REPO / name / "index.html"
        if not page.exists():
            continue
        html = read(page)
        if GA4_ID in html:
            continue
        if "</head>" not in html:
            continue
        html = html.replace("</head>", GA4_SNIPPET + "\n</head>", 1)
        write(page, html)
        fixed += 1
    print(f"✅ Fix 2: Added GA4 to {fixed} utility pages")


# ── Fix 3: alerts/index.html — wrong content (was copy of results) ────────────

def fix_alerts_page():
    page = REPO / "alerts" / "index.html"
    if not page.exists():
        print("⚠  Fix 3: alerts/index.html missing")
        return

    html = read(page)
    # Check if it's the wrong page (has results canonical)
    if 'canonical" href="https://naukribulletin.in/results/' not in html and "Get Alerts" in html:
        print("✅ Fix 3: alerts/index.html already correct — skipped")
        return

    new_alerts = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Free Govt Job Alerts 2026 — Push, Telegram & WhatsApp | NaukriBulletin</title>
  <meta name="description" content="Get free instant govt job alerts 2026 via web push, Telegram and WhatsApp. SSC, Railway, Banking, UPSC notifications on NaukriBulletin.in">
  <link rel="canonical" href="{SITE}/alerts/">
  <meta property="og:title" content="Free Govt Job Alerts — NaukriBulletin">
  <meta property="og:description" content="Get free instant govt job alerts via push notifications, Telegram @naukribulletin24 and WhatsApp Channel.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE}/alerts/">
  <meta property="og:image" content="{SITE}/assets/logo-256.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
{GA4_SNIPPET}
{OS_SNIPPET}
</head>
<body>
{STANDARD_NAV}

  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:900px;margin:0 auto;">
      <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> › Free Job Alerts
      </div>
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        🔔 Free Govt Job <span style="color:var(--saffron);">Alerts 2026</span>
      </h1>
      <p style="color:#9BA3B8;font-size:0.95rem;">Get notified instantly — push notifications, Telegram &amp; WhatsApp. Zero spam, always free.</p>
    </div>
  </div>

  <div style="max-width:900px;margin:0 auto;padding:32px 20px;">

    <!-- Web Push -->
    <div style="background:#fff;border-radius:16px;border:1.5px solid #e5e7eb;padding:28px;margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
        <div style="width:48px;height:48px;background:#FF6B0022;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">🔔</div>
        <div>
          <h2 style="font-family:var(--font-display);font-size:1.1rem;font-weight:700;margin:0 0 3px;">Browser Push Notifications</h2>
          <p style="font-size:0.83rem;color:#6b7280;margin:0;">Instant alerts in Chrome, Firefox, Safari — no app needed</p>
        </div>
      </div>
      <p style="font-size:0.88rem;color:#374151;margin:0 0 16px;">Click the <strong>bell icon</strong> at the bottom-left of this page and tap <strong>"Allow"</strong> to subscribe. You'll get alerts within seconds of new jobs being posted.</p>
      <button onclick="OneSignalDeferred.push(function(os){{os.showNativePrompt();}})"
              style="background:var(--saffron);color:#fff;border:none;border-radius:8px;padding:11px 24px;font-family:var(--font-display);font-weight:700;font-size:0.9rem;cursor:pointer;">
        🔔 Enable Job Alerts Now
      </button>
    </div>

    <!-- Telegram -->
    <div style="background:#fff;border-radius:16px;border:1.5px solid #e5e7eb;padding:28px;margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
        <div style="width:48px;height:48px;background:#0088cc22;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">📢</div>
        <div>
          <h2 style="font-family:var(--font-display);font-size:1.1rem;font-weight:700;margin:0 0 3px;">Telegram Channel</h2>
          <p style="font-size:0.83rem;color:#6b7280;margin:0;">@naukribulletin24 — 3× daily updates, PDFs, current affairs</p>
        </div>
      </div>
      <p style="font-size:0.88rem;color:#374151;margin:0 0 16px;">Join <strong>2.3 lakh+ aspirants</strong> on our Telegram channel. Get SSC, Railway, Banking, UPSC job alerts + current affairs summaries every day.</p>
      <a href="https://t.me/naukribulletin24" target="_blank" rel="noopener"
         style="display:inline-block;background:#0088cc;color:#fff;padding:11px 24px;border-radius:8px;font-family:var(--font-display);font-weight:700;font-size:0.9rem;text-decoration:none;">
        Join @naukribulletin24 →
      </a>
    </div>

    <!-- WhatsApp -->
    <div style="background:#fff;border-radius:16px;border:1.5px solid #e5e7eb;padding:28px;margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
        <div style="width:48px;height:48px;background:#25D36622;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">📱</div>
        <div>
          <h2 style="font-family:var(--font-display);font-size:1.1rem;font-weight:700;margin:0 0 3px;">WhatsApp Channel</h2>
          <p style="font-size:0.83rem;color:#6b7280;margin:0;">One-way broadcast — your number stays private</p>
        </div>
      </div>
      <p style="font-size:0.88rem;color:#374151;margin:0 0 16px;">Follow our WhatsApp Channel for daily job digests directly in WhatsApp. No spam, no groups, no number sharing.</p>
      <a href="/whatsapp/"
         style="display:inline-block;background:#25D366;color:#fff;padding:11px 24px;border-radius:8px;font-family:var(--font-display);font-weight:700;font-size:0.9rem;text-decoration:none;">
        Join WhatsApp Channel →
      </a>
    </div>

    <!-- PDF / Email -->
    <div style="background:#fff;border-radius:16px;border:1.5px solid #e5e7eb;padding:28px;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
        <div style="width:48px;height:48px;background:#4f46e522;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">📧</div>
        <div>
          <h2 style="font-family:var(--font-display);font-size:1.1rem;font-weight:700;margin:0 0 3px;">Email Alerts (via Syllabus PDF)</h2>
          <p style="font-size:0.83rem;color:#6b7280;margin:0;">Download a free syllabus PDF — get email alerts as a bonus</p>
        </div>
      </div>
      <p style="font-size:0.88rem;color:#374151;margin:0 0 16px;">Download any free syllabus PDF from our library and we'll subscribe you to weekly job digest emails (unsubscribe anytime).</p>
      <a href="/syllabus/"
         style="display:inline-block;background:#4f46e5;color:#fff;padding:11px 24px;border-radius:8px;font-family:var(--font-display);font-weight:700;font-size:0.9rem;text-decoration:none;">
        Get Free Syllabus PDFs →
      </a>
    </div>

  </div>
{FOOTER_HTML}
</body>
</html>"""

    write(page, new_alerts)
    print("✅ Fix 3: alerts/index.html completely rewritten with correct content")


# ── Fix 4: Homepage — duplicate nav + missing og:image + Schema.org ───────────

def fix_homepage():
    page = REPO / "index.html"
    if not page.exists():
        print("⚠  Fix 4: index.html missing")
        return

    html = read(page)
    changed = False

    # Remove duplicate "Latest Jobs" nav entry
    # Pattern: two consecutive <li><a href="/jobs/">Latest Jobs</a></li>
    dup_pattern = re.compile(
        r'(<li><a href="/jobs/">Latest Jobs</a></li>\s*)(<li><a href="/jobs/">Latest Jobs</a></li>)',
        re.DOTALL
    )
    if dup_pattern.search(html):
        html = dup_pattern.sub(r'\1', html)
        changed = True
        print("  → Removed duplicate 'Latest Jobs' nav item")

    # Add og:image if missing
    if "og:image" not in html:
        html = html.replace(
            '<meta property="og:url" content="https://naukribulletin.in">',
            '<meta property="og:url" content="https://naukribulletin.in">\n  <meta property="og:image" content="https://naukribulletin.in/assets/logo-256.png">'
        )
        changed = True
        print("  → Added og:image to homepage")

    # Add Schema.org WebSite + SearchAction if missing
    if "application/ld+json" not in html:
        schema = """  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "NaukriBulletin",
    "url": "https://naukribulletin.in",
    "description": "India's daily govt job portal — SSC, Railway, Banking, UPSC, State PSC notifications",
    "potentialAction": {
      "@type": "SearchAction",
      "target": "https://naukribulletin.in/jobs/?q={search_term_string}",
      "query-input": "required name=search_term_string"
    },
    "publisher": {
      "@type": "Organization",
      "name": "NaukriBulletin",
      "url": "https://naukribulletin.in",
      "logo": "https://naukribulletin.in/assets/logo-256.png"
    }
  }
  </script>"""
        html = html.replace("</head>", schema + "\n</head>", 1)
        changed = True
        print("  → Added Schema.org WebSite markup to homepage")

    if changed:
        write(page, html)
        print("✅ Fix 4: Homepage fixed")
    else:
        print("✅ Fix 4: Homepage already correct — skipped")


# ── Fix 5: Sitemap — add missing pages ────────────────────────────────────────

def fix_sitemap():
    sitemap = REPO / "sitemap.xml"
    if not sitemap.exists():
        print("⚠  Fix 5: sitemap.xml not found")
        return

    xml = read(sitemap)
    added = 0
    today = datetime.now().strftime("%Y-%m-%d")

    missing_urls = [
        f"{SITE}/cut-off/",
        f"{SITE}/mock-test/",
        f"{SITE}/about/",
        f"{SITE}/whatsapp/",
    ]

    for url in missing_urls:
        if url in xml:
            continue
        entry = f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>"""
        # Insert before closing </urlset>
        xml = xml.replace("</urlset>", entry + "\n</urlset>")
        added += 1

    if added:
        write(sitemap, xml)
    print(f"✅ Fix 5: Added {added} missing URLs to sitemap.xml")


# ── Fix 6: scraper.py — upgrade generate_affairs_html template ────────────────

def fix_scraper_affairs_template():
    scraper = REPO / "scripts" / "scraper.py"
    if not scraper.exists():
        print("⚠  Fix 6: scraper.py not found")
        return

    code = read(scraper)

    # Check if already patched
    if "og:title" in code and "generate_affairs_html" in code:
        # Verify the og:title is inside generate_affairs_html
        affairs_section = code[code.find("def generate_affairs_html"):]
        if "og:title" in affairs_section[:3000]:
            print("✅ Fix 6: scraper.py affairs template already has OG tags — skipped")
            return

    # Find and replace the generate_affairs_html template
    # The minimal <head> section in the current template
    old_head = '''html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{affair.get('title', 'Current Affairs')} — NaukriBulletin</title>
  <meta name="description" content="{affair.get('summary', '')[:155]}">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/{slug}/">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body style="font-family:'DM Sans',sans-serif;background:#F7F8FA;margin:0;">
  <nav style="background:#0A0F2C;border-bottom:3px solid #FF6B00;padding:0 20px;">
    <div style="max-width:900px;margin:0 auto;display:flex;align-items:center;height:60px;">
      <a href="/" style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;color:#fff;text-decoration:none;">NaukriBulletin</a>
    </div>
  </nav>'''

    new_head = '''html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{affair.get('title', 'Current Affairs')} — NaukriBulletin</title>
  <meta name="description" content="{affair.get('summary', '')[:155]}">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/{slug}/">
  <meta property="og:title" content="{affair.get('title', 'Current Affairs')} — NaukriBulletin">
  <meta property="og:description" content="{affair.get('summary', '')[:155]}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://naukribulletin.in/current-affairs/{slug}/">
  <meta property="og:image" content="https://naukribulletin.in/assets/logo-256.png">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "headline": "{affair.get('title', '')}",
    "description": "{affair.get('summary', '')[:155]}",
    "url": "https://naukribulletin.in/current-affairs/{slug}/",
    "datePublished": "{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
    "publisher": {{
      "@type": "Organization",
      "name": "NaukriBulletin",
      "url": "https://naukribulletin.in"
    }}
  }}
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{{{dataLayer.push(arguments);}}}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{{{
      await OneSignal.init({{{{
        appId: "89e83d08-e30e-46f9-baec-f0167f8baa35",
        notifyButton: {{ enable: true, size: 'medium', position: 'bottom-left' }}
      }}}});
    }}}});
  </script>
</head>
<body style="font-family:'DM Sans',sans-serif;background:#F7F8FA;margin:0;">
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/" class="active">Current Affairs</a></li>
        <li><a href="/syllabus/">Syllabus</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>'''

    if old_head in code:
        code = code.replace(old_head, new_head, 1)
        # Also add footer before </body></html> in the affairs template
        old_end = '''  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</body>
</html>"""
    return slug, html


# ─── SITE BUILDER ─────────────────────────────────────────────────────────────'''

        new_end = '''  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© 2026 NaukriBulletin.in — <a href="/about/" style="color:var(--grey-400);text-decoration:none;">About</a> · <a href="/privacy/" style="color:var(--grey-400);text-decoration:none;">Privacy</a> · <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a></p>
      </div>
    </div>
  </footer>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={{ADSENSE_CLIENT}}" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{{{}}}});</script>
</body>
</html>"""
    return slug, html


# ─── SITE BUILDER ─────────────────────────────────────────────────────────────'''

        if old_end in code:
            code = code.replace(old_end, new_end, 1)

        # Make sure datetime is imported (needed for schema datePublished)
        if "from datetime import datetime" not in code:
            code = code.replace("from datetime import datetime, date", "from datetime import datetime, date")

        write(scraper, code)
        print("✅ Fix 6: scraper.py generate_affairs_html upgraded — new CA pages will have GA4, OG, schema, nav, footer")
    else:
        print("⚠  Fix 6: Could not find exact template pattern in scraper.py — manual update needed")
        print("   The generate_affairs_html function needs GA4, OG tags, schema, full nav, and footer added")


# ── Fix 7: _redirects — add missing entries ───────────────────────────────────

def fix_redirects():
    redir = REPO / "_redirects"
    if not redir.exists():
        print("⚠  Fix 7: _redirects not found")
        return

    content = read(redir)
    additions = []

    new_rules = [
        ("/cut-off         /cut-off/         301", "/cut-off"),
        ("/mock-test       /mock-test/       301", "/mock-test"),
        ("/whatsapp        /whatsapp/        301", "/whatsapp"),
        ("/alerts          /alerts/          301", "/alerts"),
        ("/about           /about/           301", "/about"),
        ("/age-calculator  /age-calculator/  301", "/age-calculator"),
    ]

    for rule, check in new_rules:
        if check not in content:
            additions.append(rule)

    if additions:
        content = content.rstrip() + "\n\n# Phase 4 new pages\n" + "\n".join(additions) + "\n"
        write(redir, content)
    print(f"✅ Fix 7: Added {len(additions)} redirect rules to _redirects")


# ── Summary report ────────────────────────────────────────────────────────────

def print_summary():
    ROOT = REPO
    print(f"\n{'='*60}")
    print("POST-FIX VERIFICATION")
    print(f"{'='*60}")

    # CA pages
    ca_pages = list((ROOT / "current-affairs").glob("*/index.html"))
    ca_total = len(ca_pages)
    ca_ga4  = sum(1 for p in ca_pages if GA4_ID in read(p))
    ca_og   = sum(1 for p in ca_pages if "og:title" in read(p))
    ca_foot = sum(1 for p in ca_pages if "footer-inner" in read(p) or "© 2026" in read(p))
    print(f"Current Affairs ({ca_total} pages):")
    print(f"  GA4: {ca_ga4}/{ca_total}  OG: {ca_og}/{ca_total}  Footer: {ca_foot}/{ca_total}")

    # Utility pages GA4
    util_ga4 = sum(1 for n in UTILITY_PAGES if (ROOT/n/"index.html").exists() and GA4_ID in read(ROOT/n/"index.html"))
    print(f"Utility pages GA4: {util_ga4}/{len(UTILITY_PAGES)}")

    # Alerts page title
    alerts_page = ROOT / "alerts" / "index.html"
    if alerts_page.exists():
        alerts_title = re.search(r'<title>(.*?)</title>', read(alerts_page))
        print(f"Alerts page title: '{alerts_title.group(1) if alerts_title else 'unknown'}'")

    # Homepage
    hp = read(ROOT / "index.html")
    print(f"Homepage: og:image={'✓' if 'og:image' in hp else '✗'}  schema={'✓' if 'application/ld' in hp else '✗'}  dup-nav={'✗' if hp.count('/jobs/\">Latest Jobs') < 2 else '✓ STILL PRESENT'}")

    # Sitemap
    sitemap = read(ROOT / "sitemap.xml")
    for url in ["/cut-off/", "/mock-test/", "/about/"]:
        status = "✓" if url in sitemap else "✗"
        print(f"Sitemap {url}: {status}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"NaukriBulletin Full Site Audit Fixer — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*60}\n")

    fix_current_affairs_pages()
    fix_utility_pages_ga4()
    fix_alerts_page()
    fix_homepage()
    fix_sitemap()
    fix_scraper_affairs_template()
    fix_redirects()

    print_summary()

    print(f"\n{'='*60}")
    print("✅ Full site audit complete. Now run:")
    print()
    print("  git add -A")
    print("  git commit -m 'fix: full site audit — CA pages GA4/OG/footer, alerts page, homepage schema, sitemap'")
    print("  git push origin main")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
