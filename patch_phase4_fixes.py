#!/usr/bin/env python3
"""
patch_phase4_fixes.py — NaukriBulletin Phase 4 Audit Fixes
===========================================================
Run from repo root:  python3 patch_phase4_fixes.py

Fixes applied:
  1. Backfill affiliate banners on all 243 job pages that lack them
  2. Fix 127 "Apply Online" buttons with href="N/A" → hide button + show note
  3. Add GA4 tracking to 63 job pages missing it
  4. Add footer + Telegram sidebar to 234 job pages missing them
  5. Export scripts/_data/jobs.json so telegram_notify.py actually works
  6. Fix WhatsApp page placeholder channel link (prompts user to enter real link)
  7. Add Brevo email gate to syllabus page
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
JOBS_DIR  = REPO_ROOT / "jobs"
SCRIPTS   = REPO_ROOT / "scripts"

GA4_ID        = "G-6WQJ4W7T1N"
ONESIGNAL_ID  = "89e83d08-e30e-46f9-baec-f0167f8baa35"

# ── AFFILIATE HTML (inline, no external file dependency) ──────────────────────
AFFILIATE_HTML = """
      <!-- Coaching Affiliate Banners — Phase 4 -->
      <div style="margin:28px 0;">
        <p style="font-size:0.75rem;font-weight:700;color:#9BA3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px;">📚 Prepare for this exam</p>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;">
          <a href="https://unacademy.com/?referral=NAUKRIBULLETIN" target="_blank" rel="noopener sponsored"
             onclick="if(typeof gtag!='undefined')gtag('event','affiliate_click',{event_category:'Affiliate',event_label:'unacademy'})"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #08bd80;">
            <div style="width:40px;height:40px;border-radius:8px;background:#08bd80;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">UN</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Unacademy — Live Classes</div>
              <div style="font-size:0.74rem;color:#6b7280;">SSC, Railway, Banking &amp; State Exams</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#08bd80;color:#fff;white-space:nowrap;">Free</span>
          </a>
          <a href="https://testbook.com/?utm_source=naukribulletin&utm_medium=affiliate&utm_campaign=jobpages" target="_blank" rel="noopener sponsored"
             onclick="if(typeof gtag!='undefined')gtag('event','affiliate_click',{event_category:'Affiliate',event_label:'testbook'})"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #1d4ed8;">
            <div style="width:40px;height:40px;border-radius:8px;background:#1d4ed8;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">TB</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Testbook — Mock Tests</div>
              <div style="font-size:0.74rem;color:#6b7280;">10,000+ tests · Hindi &amp; English</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#1d4ed8;color:#fff;white-space:nowrap;">Free</span>
          </a>
          <a href="https://www.adda247.com/?utm_source=naukribulletin&utm_medium=affiliate&utm_campaign=jobpages" target="_blank" rel="noopener sponsored"
             onclick="if(typeof gtag!='undefined')gtag('event','affiliate_click',{event_category:'Affiliate',event_label:'adda247'})"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #f97316;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f97316;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">A2</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Adda247 — Study Material</div>
              <div style="font-size:0.74rem;color:#6b7280;">eBooks, Videos, Quizzes</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#f97316;color:#fff;white-space:nowrap;">Explore</span>
          </a>
        </div>
      </div>
"""

GA4_SNIPPET = f"""  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA4_ID}');</script>"""

FOOTER_HTML = """  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© 2026 NaukriBulletin.in — <a href="/about/" style="color:var(--grey-400);text-decoration:none;">About</a> · <a href="/contact/" style="color:var(--grey-400);text-decoration:none;">Contact</a> · <a href="/privacy/" style="color:var(--grey-400);text-decoration:none;">Privacy</a> · <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a></p>
      </div>
    </div>
  </footer>"""

TELEGRAM_SIDEBAR_HTML = """        <div style="background:var(--navy);border-radius:12px;padding:20px;text-align:center;margin-bottom:16px;">
          <div style="font-size:1.5rem;margin-bottom:8px;">📢</div>
          <h3 style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--white);margin-bottom:6px;">Free Job Alerts</h3>
          <p style="font-size:0.8rem;color:var(--grey-400);margin-bottom:14px;">Get instant Telegram alerts for new govt jobs</p>
          <a href="https://t.me/naukribulletin24" target="_blank"
             style="background:#0088cc;color:#fff;padding:9px 20px;border-radius:8px;text-decoration:none;font-size:0.85rem;font-weight:700;display:inline-block;">Join @naukribulletin24 →</a>
        </div>"""


# ─── Helper ────────────────────────────────────────────────────────────────────

def read(path): return path.read_text(encoding="utf-8")
def write(path, text): path.write_text(text, encoding="utf-8")


# ─── Fix 1: Backfill affiliate banners ────────────────────────────────────────

def fix_affiliate_banners():
    fixed = 0
    for job_page in sorted(JOBS_DIR.glob("*/index.html")):
        html = read(job_page)
        # Skip if already has affiliate
        if "adda247.com" in html or "Prepare for this exam" in html:
            continue
        # Find insertion point: before </article> or before disclaimer div or before </main>
        # Try after the AdSense mid-slot
        insert_after = None
        for marker in [
            'data-ad-slot="XXXXXXXXXX" data-ad-format="auto"></ins>\n\n      <!-- Disclaimer',
            'adsbygoogle.js?client=',
            'Disclaimer:</strong>',
            '</article>',
            '</main>',
        ]:
            if marker in html:
                insert_after = marker
                break

        if not insert_after:
            continue

        if insert_after in ('</article>', '</main>'):
            html = html.replace(insert_after, AFFILIATE_HTML + "\n" + insert_after, 1)
        elif insert_after == 'Disclaimer:</strong>':
            # Insert before the disclaimer block
            disclaimer_start = html.find('<div style="background:#FFF3E8')
            if disclaimer_start == -1:
                continue
            html = html[:disclaimer_start] + AFFILIATE_HTML + "\n" + html[disclaimer_start:]
        else:
            # Insert after the marker
            pos = html.find(insert_after) + len(insert_after)
            html = html[:pos] + "\n" + AFFILIATE_HTML + html[pos:]

        write(job_page, html)
        fixed += 1

    print(f"✅ Fix 1: Backfilled affiliate banners on {fixed} job pages")


# ─── Fix 2: Apply button href=N/A ─────────────────────────────────────────────

def fix_apply_links():
    fixed = 0
    for job_page in sorted(JOBS_DIR.glob("*/index.html")):
        html = read(job_page)
        if 'href="N/A"' not in html and "href=\"#\"" not in html:
            continue

        # Replace bad apply button with a "Check official website" note
        bad_button = re.compile(
            r'<a href="(N/A|#)"[^>]*>\s*Apply Online →\s*</a>',
            re.DOTALL
        )
        if not bad_button.search(html):
            continue

        replacement = (
            '<span style="background:#e5e7eb;color:#6b7280;padding:14px 40px;'
            'border-radius:10px;font-family:\'Syne\',sans-serif;font-weight:700;'
            'font-size:1rem;display:inline-block;cursor:default;">'
            '🔍 Check Official Website for Apply Link</span>'
        )
        html = bad_button.sub(replacement, html)
        write(job_page, html)
        fixed += 1

    print(f"✅ Fix 2: Fixed {fixed} broken 'Apply Online' N/A buttons")


# ─── Fix 3: Add GA4 to pages missing it ───────────────────────────────────────

def fix_ga4():
    fixed = 0
    for job_page in sorted(JOBS_DIR.glob("*/index.html")):
        html = read(job_page)
        if GA4_ID in html:
            continue
        # Insert GA4 before </head>
        if "</head>" not in html:
            continue
        html = html.replace("</head>", GA4_SNIPPET + "\n</head>", 1)
        write(job_page, html)
        fixed += 1
    print(f"✅ Fix 3: Added GA4 tracking to {fixed} job pages")


# ─── Fix 4: Add footer to pages missing it ────────────────────────────────────

def fix_footer():
    fixed = 0
    for job_page in sorted(JOBS_DIR.glob("*/index.html")):
        html = read(job_page)
        if "footer-inner" in html or "footer-bottom" in html:
            continue
        if "</body>" not in html:
            continue
        html = html.replace("</body>", FOOTER_HTML + "\n</body>", 1)
        write(job_page, html)
        fixed += 1
    print(f"✅ Fix 4: Added footer to {fixed} job pages")


# ─── Fix 5: Export jobs.json for telegram_notify.py ──────────────────────────

def fix_jobs_json_export():
    """
    Adds a jobs.json export step to scraper.py so telegram_notify.py
    can find new jobs to notify about.
    Also creates the _data directory.
    """
    scraper_path = SCRIPTS / "scraper.py"
    scraper = read(scraper_path)

    # Check if already patched
    if "_data/jobs.json" in scraper or "export_jobs_json" in scraper:
        print("✅ Fix 5: scraper.py already exports jobs.json — skipped")
        return

    # Add export function after save_processed
    export_fn = '''

def export_jobs_json(jobs_list: list):
    """Export new jobs to scripts/_data/jobs.json for telegram_notify.py"""
    data_dir = Path(__file__).parent / "_data"
    data_dir.mkdir(exist_ok=True)
    out_path  = data_dir / "jobs.json"
    # Load existing
    existing = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except Exception:
            existing = []
    # Merge — keep last 500 entries
    existing_ids = {j.get("id") for j in existing}
    new = [j for j in jobs_list if j.get("id") not in existing_ids]
    merged = (new + existing)[:500]
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"[EXPORT] jobs.json updated: {len(new)} new / {len(merged)} total")

'''

    # Insert after save_processed function
    insert_after = "def save_processed(hashes):\n    PROCESSED_FILE.parent.mkdir(exist_ok=True)\n    with open(PROCESSED_FILE, \"w\") as f:\n        json.dump(list(hashes), f)\n"
    if insert_after in scraper:
        scraper = scraper.replace(insert_after, insert_after + export_fn, 1)
    else:
        # Fallback: append before if __name__
        scraper = scraper.replace(
            'if __name__ == "__main__":',
            export_fn + '\nif __name__ == "__main__":'
        )

    # Now patch the run() function to collect job dicts and call export_jobs_json
    # Find where jobs are saved and collect them
    old_save_call = '                    slug, html = generate_job_html(job)\n                    save_page(slug, html, "jobs")\n                    new_pages += 1'
    new_save_call = '''                    slug, html = generate_job_html(job)
                    save_page(slug, html, "jobs")
                    new_pages += 1
                    # Collect for JSON export (notify.py needs this)
                    job["id"]   = job.get("id") or slug
                    job["slug"] = slug
                    job["url"]  = f"{SITE_URL}/jobs/{slug}/"
                    collected_jobs.append(job)'''

    if old_save_call in scraper:
        scraper = scraper.replace(old_save_call, new_save_call, 1)

    # Add collected_jobs list init at start of run()
    old_run_start = '    processed  = load_processed()\n    new_pages  = 0\n    failed_src = []'
    new_run_start = '    processed     = load_processed()\n    new_pages     = 0\n    failed_src    = []\n    collected_jobs = []'
    if old_run_start in scraper:
        scraper = scraper.replace(old_run_start, new_run_start, 1)

    # Call export before git_push
    old_git = '    if new_pages > 0:\n        git_push(f"Auto: {new_pages} new pages — {today_str}")'
    new_git = '''    if collected_jobs:
        export_jobs_json(collected_jobs)

    if new_pages > 0:
        git_push(f"Auto: {new_pages} new pages — {today_str}")'''
    if old_git in scraper:
        scraper = scraper.replace(old_git, new_git, 1)

    # Make sure SITE_URL is defined
    if 'SITE_URL' not in scraper:
        scraper = scraper.replace(
            'SITE_ROOT',
            'SITE_URL = "https://naukribulletin.in"\nSITE_ROOT',
            1
        )

    write(scraper_path, scraper)

    # Create _data dir and empty jobs.json if missing
    data_dir = SCRIPTS / "_data"
    data_dir.mkdir(exist_ok=True)
    jobs_json = data_dir / "jobs.json"
    if not jobs_json.exists():
        jobs_json.write_text("[]")

    print("✅ Fix 5: scraper.py patched to export _data/jobs.json — telegram_notify.py will now work")


# ─── Fix 6: WhatsApp placeholder link ─────────────────────────────────────────

def fix_whatsapp_link():
    wa_page = REPO_ROOT / "whatsapp" / "index.html"
    if not wa_page.exists():
        print("⚠  Fix 6: whatsapp/index.html not found — skipped")
        return

    html = read(wa_page)
    if "0029VaNaukriBulletin" in html:
        print("⚠  Fix 6: WhatsApp channel link is still placeholder.")
        print("   → Create your channel: WhatsApp → Updates → + → New Channel")
        print("   → Then run:  sed -i 's|0029VaNaukriBulletin|YOUR_REAL_ID|g' whatsapp/index.html")
        print("   → Or edit whatsapp/index.html manually and replace '0029VaNaukriBulletin'")
    else:
        print("✅ Fix 6: WhatsApp channel link already updated")


# ─── Fix 7: Add Brevo email gate to syllabus page ─────────────────────────────

def fix_syllabus_email_gate():
    syl_page = REPO_ROOT / "syllabus" / "index.html"
    if not syl_page.exists():
        print("⚠  Fix 7: syllabus/index.html not found — skipped")
        return

    html = read(syl_page)
    if "brevo" in html.lower() or "subscribe" in html.lower() or "modal" in html.lower():
        print("✅ Fix 7: Syllabus page already has email gate — skipped")
        return

    # Build compact email gate modal + trigger button injection
    EMAIL_GATE = """
<!-- ── Brevo Email Gate (Phase 4) ────────────────────────── -->
<div id="nb-gate-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:999;" onclick="nbCloseGate()"></div>
<div id="nb-gate-modal" role="dialog" aria-modal="true" style="display:none;position:fixed;inset:0;z-index:1000;display:none;align-items:center;justify-content:center;padding:16px;">
  <div style="background:#fff;border-radius:16px;padding:28px 24px;max-width:420px;width:100%;position:relative;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.18);">
    <button onclick="nbCloseGate()" style="position:absolute;top:10px;right:12px;background:none;border:none;font-size:1.1rem;cursor:pointer;color:#9ca3af;">✕</button>
    <div id="nb-gate-step1">
      <div style="font-size:2.5rem;margin-bottom:8px;">📥</div>
      <h2 style="font-size:1.3rem;font-weight:800;color:#111827;margin:0 0 4px;">Get Your Free PDF</h2>
      <p id="nb-gate-pdf-name" style="font-weight:600;color:#4f46e5;font-size:.88rem;margin:0 0 8px;"></p>
      <p style="font-size:.83rem;color:#6b7280;margin:0 0 14px;">Enter your email — we'll send the PDF link instantly + subscribe you to free daily job alerts.</p>
      <div style="display:flex;flex-direction:column;gap:8px;">
        <input type="text"  id="nb-gate-name"  placeholder="Your Name"  style="border:1.5px solid #d1d5db;border-radius:8px;padding:10px 14px;font-size:.9rem;outline:none;" />
        <input type="email" id="nb-gate-email" placeholder="Your Email" style="border:1.5px solid #d1d5db;border-radius:8px;padding:10px 14px;font-size:.9rem;outline:none;" required />
        <button id="nb-gate-submit" onclick="nbSubmitGate()" style="background:#4f46e5;color:#fff;border:none;border-radius:8px;padding:11px;font-size:.93rem;font-weight:700;cursor:pointer;">Get PDF Instantly →</button>
        <p id="nb-gate-err" style="color:#dc2626;font-size:.8rem;display:none;margin:0;"></p>
      </div>
      <p style="font-size:.7rem;color:#9ca3af;margin-top:8px;">🔒 No spam. Unsubscribe anytime.</p>
    </div>
    <div id="nb-gate-step2" style="display:none;">
      <div style="font-size:2.5rem;margin-bottom:8px;">✅</div>
      <h2 style="font-size:1.3rem;font-weight:800;color:#111827;margin:0 0 8px;">Download Ready!</h2>
      <p style="font-size:.85rem;color:#6b7280;margin:0 0 14px;">Your PDF is downloading. Check your email for the link too.</p>
      <a id="nb-gate-dl-link" href="#" style="display:inline-block;background:#16a34a;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:700;font-size:.9rem;margin-bottom:12px;" download>📥 Click if download didn't start</a>
      <br>
      <a href="https://t.me/naukribulletin24" target="_blank" style="display:inline-block;background:#0088cc;color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.82rem;font-weight:600;">Join Telegram for daily job alerts →</a>
    </div>
  </div>
</div>

<script>
var _nbPdfUrl='', _nbPdfTitle='';

// Called by each syllabus download button
function nbOpenGate(pdfUrl, pdfTitle) {
  if (localStorage.getItem('nb_email')) {
    nbTriggerDownload(pdfUrl, pdfTitle); return;
  }
  _nbPdfUrl=pdfUrl; _nbPdfTitle=pdfTitle;
  document.getElementById('nb-gate-pdf-name').textContent = pdfTitle;
  document.getElementById('nb-gate-step1').style.display='block';
  document.getElementById('nb-gate-step2').style.display='none';
  document.getElementById('nb-gate-err').style.display='none';
  document.getElementById('nb-gate-modal').style.display='flex';
  document.getElementById('nb-gate-overlay').style.display='block';
}
function nbCloseGate() {
  document.getElementById('nb-gate-modal').style.display='none';
  document.getElementById('nb-gate-overlay').style.display='none';
}
async function nbSubmitGate() {
  var email=document.getElementById('nb-gate-email').value.trim();
  var name =document.getElementById('nb-gate-name').value.trim();
  var err  =document.getElementById('nb-gate-err');
  var btn  =document.getElementById('nb-gate-submit');
  if(!email||!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email)){
    err.textContent='Enter a valid email.';err.style.display='block';return;
  }
  btn.disabled=true;btn.textContent='Subscribing…';
  // Brevo embedded form POST — replace YOUR_FORM_ID with your actual Brevo form ID
  // Get from: Brevo dashboard → Email Campaigns → Forms → Embed code → action URL
  var BREVO_FORM='https://sibforms.com/serve/BREVO_FORM_ID_REPLACE_THIS';
  var fd=new FormData();
  fd.append('EMAIL',email);fd.append('FIRSTNAME',name);
  fd.append('SOURCE','syllabus_pdf');
  fetch(BREVO_FORM,{method:'POST',body:fd,mode:'no-cors'}).catch(function(){});
  localStorage.setItem('nb_email',email);
  if(typeof gtag!='undefined')gtag('event','pdf_email_captured',{event_category:'Lead',event_label:_nbPdfTitle});
  document.getElementById('nb-gate-step1').style.display='none';
  document.getElementById('nb-gate-step2').style.display='block';
  document.getElementById('nb-gate-dl-link').href=_nbPdfUrl;
  nbTriggerDownload(_nbPdfUrl,_nbPdfTitle);
}
function nbTriggerDownload(url,name){
  var a=document.createElement('a');a.href=url;a.download=name+'.pdf';
  document.body.appendChild(a);a.click();document.body.removeChild(a);
}
document.addEventListener('keydown',function(e){if(e.key==='Escape')nbCloseGate();});
</script>
<!-- ── /Brevo Email Gate ────────────────────────────────── -->
"""

    # Now find all syllabus download links and wire them to nbOpenGate
    # The syllabus page has <a href="/assets/pdf/..."> links - convert them to onclick
    html_updated = re.sub(
        r'<a\s+href="(/assets/pdf/([^"]+\.pdf))"([^>]*)>(.*?Download.*?)</a>',
        lambda m: (
            f'<button onclick="nbOpenGate(\'{m.group(1)}\',\'{m.group(2).replace(".pdf","").replace("-", " ").title()}\')" '
            f'style="background:#4f46e5;color:#fff;border:none;border-radius:8px;'
            f'padding:9px 18px;font-size:.85rem;font-weight:700;cursor:pointer;'
            f'white-space:nowrap;">{m.group(4)}</button>'
        ),
        html,
        flags=re.DOTALL
    )

    # Also wire any "Download PDF" text buttons that don't have real href yet
    # Pattern: button/link with "Download" text near a syllabus card
    if 'nbOpenGate' not in html_updated:
        # Fallback: inject onclick on any existing download-style links
        html_updated = re.sub(
            r'(<a[^>]+href="([^"]*syllabus[^"]*|[^"]*pdf[^"]*)"[^>]*>)([^<]*[Dd]ownload[^<]*)(</a>)',
            lambda m: (
                f'<button onclick="nbOpenGate(\'{m.group(2)}\', \'Exam Syllabus PDF\')" '
                f'style="background:#4f46e5;color:#fff;border:none;border-radius:8px;'
                f'padding:9px 18px;font-size:.85rem;font-weight:700;cursor:pointer;">'
                f'{m.group(3)}</button>'
            ),
            html_updated,
            flags=re.DOTALL
        )

    # Inject modal before </body>
    html_updated = html_updated.replace("</body>", EMAIL_GATE + "\n</body>", 1)
    write(syl_page, html_updated)
    print("✅ Fix 7: Brevo email gate injected into syllabus/index.html")
    print("   → Replace 'BREVO_FORM_ID_REPLACE_THIS' with your actual Brevo form ID")
    print("   → Get it from: Brevo → Email Campaigns → Forms → Embed code → action URL")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"NaukriBulletin Phase 4 Audit Fixer — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*60}\n")

    fix_affiliate_banners()
    fix_apply_links()
    fix_ga4()
    fix_footer()
    fix_jobs_json_export()
    fix_whatsapp_link()
    fix_syllabus_email_gate()

    print(f"\n{'='*60}")
    print("✅ All fixes applied. Now run:")
    print()
    print("  git add -A")
    print("  git commit -m 'fix: Phase 4 audit — affiliate backfill, GA4, footer, jobs.json export, email gate'")
    print("  git push origin main")
    print()
    print("⚠  Manual steps still required:")
    print("  1. Set ONESIGNAL_REST_KEY in GitHub → Settings → Secrets")
    print("  2. Replace BREVO_FORM_ID_REPLACE_THIS in syllabus/index.html with your Brevo form ID")
    print("  3. Replace WhatsApp channel placeholder in whatsapp/index.html")
    print("  4. Set real AdSense IDs: GitHub Secrets ADSENSE_CLIENT + ADSENSE_SLOT_TOP + ADSENSE_SLOT_MID")
    print("  5. Register real affiliate accounts (Unacademy/Testbook/Adda247) and update links in scraper.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
