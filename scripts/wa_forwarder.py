#!/usr/bin/env python3
"""
wa_forwarder.py — Reads messages forwarded to Telegram bot, parses job alerts,
generates NaukriBulletin job pages automatically.

Run by CI every 6 hours. Also runnable manually.

Setup:
  GitHub secrets needed:
    WA_BOT_TOKEN   — Telegram bot token from @BotFather
    WA_CHAT_ID     — Your Telegram user ID from @userinfobot
"""

import os, re, json, sys, time, unicodedata
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

SITE_ROOT  = Path(__file__).parent.parent
JOBS_DIR   = SITE_ROOT / 'jobs'
STATE_FILE = SITE_ROOT / 'scripts' / '_data' / 'wa_last_update_id.json'
TODAY      = datetime.now().strftime("%d %B %Y")
YR         = datetime.now().year

BOT_TOKEN = os.environ.get('WA_BOT_TOKEN', '')
CHAT_ID   = os.environ.get('WA_CHAT_ID', '')

def tg_api(method, params=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    if params:
        url += '?' + '&'.join(f"{k}={v}" for k,v in params.items())
    try:
        req = Request(url, headers={'User-Agent': 'NaukriBot/1.0'})
        resp = urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        print(f"Telegram API error: {e}")
        return None

def get_last_update_id():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())['last_update_id']
        except: pass
    return 0

def save_last_update_id(uid):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps({'last_update_id': uid}))

def make_slug(title):
    s = unicodedata.normalize('NFKD', title.lower())
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s).strip('-')
    return re.sub(r'-+', '-', s)[:80]


# ── Official website mapping ──────────────────────────────────────────────────
OFFICIAL_SITES = {
    'nirdpr':        'https://nird.org.in/',
    'panchayati raj':'https://panchayat.gov.in/',
    'drdo':          'https://drdo.gov.in/careers',
    'isro':          'https://www.isro.gov.in/Careers.html',
    'upsc':          'https://upsconline.nic.in/',
    'ssc':           'https://ssc.gov.in/',
    'ibps':          'https://www.ibps.in/',
    'sbi ':          'https://bank.sbi/web/careers',
    'rbi ':          'https://www.rbi.org.in/Scripts/Vacancies.aspx',
    'nbe ':          'https://natboard.edu.in/',
    'aiims':         'https://www.aiims.edu/en/notices/recruitment-notices.html',
    'icmr':          'https://main.icmr.gov.in/content/vacancies',
    'nclt':          'https://nclt.gov.in/recruitment',
    'mppsc':         'https://mppsc.mp.gov.in/',
    'bpsc':          'https://bpsc.bih.nic.in/',
    'rpsc':          'https://rpsc.rajasthan.gov.in/',
    'tnpsc':         'https://www.tnpsc.gov.in/',
    'kpsc':          'https://kpsc.kar.nic.in/',
    'air force':     'https://careerindianairforce.cdac.in/',
    'indian navy':   'https://www.joinindiannavy.gov.in/',
    'indian army':   'https://joinindianarmy.nic.in/',
    'cisf':          'https://cisfrectt.cisf.gov.in/',
    'crpf':          'https://crpf.gov.in/recruitment.htm',
    'bsf ':          'https://bsf.gov.in/recruitment.html',
    'itbp':          'https://itbpolice.nic.in/',
    'agniveer':      'https://agnipathvayu.cdac.in/',
    'railways':      'https://indianrailways.gov.in/',
    'rrb ':          'https://www.rrbapply.gov.in/',
    'rrb ntpc':      'https://www.rrbapply.gov.in/',
    'high court':    'https://districts.ecourts.gov.in/',
    'district court':'https://districts.ecourts.gov.in/',
    'nabard':        'https://nabard.org/recruitment.aspx',
    'ongc':          'https://ongcindia.com/web/eng/careers',
    'ntpc':          'https://careers.ntpc.co.in/',
    'pnb ':          'https://www.pnbindia.in/recruitment.html',
    'iit ':          'https://www.iitd.ac.in/jobs-iitd.php',
    'nit ':          'https://www.nitdelhi.ac.in/careers/',
    'du ':           'https://www.du.ac.in/',
    'university':    '',  # too generic
}

def find_official_url(title, source_url):
    """Return official apply URL or source URL with is_aggregator flag."""
    tl = title.lower()
    for keyword, official_url in OFFICIAL_SITES.items():
        if keyword in tl and official_url:
            return official_url, False
    if any(x in source_url for x in ['.gov.in','.nic.in','.edu.in','.ac.in']):
        return source_url, False
    return source_url, True  # is aggregator

def _extract_and_append(block, title, jobs):
    skip = ['whatsapp','telegram','channel','mpcareer.in','freejobalert.com',
            'job alert','our websites','join us']
    if any(k in title.lower() for k in skip): return
    start_date = last_date = ''
    for pattern, attr in [
        (r'Start\s*Date\s*[-:]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})', 'start'),
        (r'(?:Last Date|\U0001F4C5)[^:\n]*[:]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})', 'last'),
        (r'Last\s*Date\s*[-:]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})', 'last'),
    ]:
        m = re.search(pattern, block, re.I)
        if m:
            try:
                d = datetime.strptime(m.group(1).replace('-','/'), '%d/%m/%Y')
                if attr == 'start': start_date = d.strftime('%d %B %Y')
                else: last_date = d.strftime('%d %B %Y')
            except:
                if attr == 'start': start_date = m.group(1)
                else: last_date = m.group(1)
    url_m = re.search(r'(?:Direct Link|link)\s*[-:]\s*(https?://\S+)', block, re.I)
    if not url_m: url_m = re.search(r'(https?://(?!whatsapp|t\.me)\S+)', block)
    source_url = url_m.group(1).rstrip('.,)\n') if url_m else ''
    official_url, is_aggregator = find_official_url(title, source_url)

    qualification = ''

    salary = ''

    vac_m = re.search(r'(?:Vacancy|\U0001F4CC)[^:\n]*:?\s*(\d[\d,]+)', block, re.I)
    if not vac_m: vac_m = re.search(r'(\d[\d,]+)\s*(?:Post|Vacanc|Seat)', block, re.I)
    vacancies = vac_m.group(1) if vac_m else 'Various'
    tl = title.lower()
    if any(x in tl for x in ['ssc','staff selection']): cat = 'SSC'
    elif any(x in tl for x in ['railway','rrb','rail']): cat = 'Railway'
    elif any(x in tl for x in ['bank','ibps','sbi','rbi']): cat = 'Banking'
    elif any(x in tl for x in ['upsc','ias','civil service']): cat = 'UPSC'
    elif any(x in tl for x in ['police','crpf','bsf','cisf','itbp','ssb']): cat = 'Defence'
    elif any(x in tl for x in ['air force','army','navy','nda','pharmacist','agniveer']): cat = 'Defence'
    elif any(x in tl for x in ['teacher','tgt','pgt','ctet']): cat = 'Teaching'
    elif any(x in tl for x in ['psc','mppsc','uppsc','bpsc','rpsc']): cat = 'State PSC'
    else: cat = 'Central Govt'
    dept = re.sub(r'Recruitment\s*\d{4}.*$', '', title, flags=re.I).strip()
    dept = re.sub(r'\s*[-\u2013]\s*(NIRDPR|Vacancy|Notification).*$', '', dept, flags=re.I).strip() or title[:40]
    jobs.append({
        'title': title, 'slug': make_slug(title), 'dept': dept, 'category': cat,
        'start_date': start_date, 'last_date': last_date,
        'source_url': source_url, 'official_url': official_url, 'is_aggregator': is_aggregator, 'vacancies': vacancies,
        'qualification': qualification, 'salary': salary,
        'urgent': bool(re.search(r'last date soon|urgent|closing soon', block, re.I)),
    })

def parse_job_message(text):
    """Parse MPCareer and FreeJobAlert WhatsApp formats."""
    jobs = []

    # Format 1: MPCareer — blocks separated by ----, titles in *bold*
    for block in re.split(r'-{3,}', text):
        block = block.strip()
        if len(block) < 20: continue
        clean = re.sub(r'[\U0001F000-\U0001FFFF\u200d\u2640\u2642\uFE0F\uF000-\uF8FF]+', '', block).strip()
        m = re.search(r'\*([^\*\n]{10,100})\*', clean) or re.search(r'\*([^\*\n]{10,100})\*', block)
        if not m: continue
        title = m.group(1).strip()
        if any(k in title.lower() for k in ['whatsapp','channel','mpcareer','direct link','government job']): continue
        if len(title) < 10: continue
        _extract_and_append(block, title, jobs)

    # Format 2: FreeJobAlert — title on first line, emoji fields
    for block in re.split(r'\n\n(?=[A-Z])', text):
        block = block.strip()
        if len(block) < 30: continue
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines: continue
        title = re.sub(r'^[\U0001F000-\U0001FFFF\u200d\u2640\u2642\uFE0F\s]+', '', lines[0]).strip()
        if not any(x in title.lower() for x in ['recruit','vacanc','post','notif','apprentice']): continue
        if len(title) < 10 or len(title) > 120: continue
        if not re.search(r'(?:Last Date|Vacancy|\U0001F4C5|\U0001F4CC)', block, re.I): continue
        if any(j['slug'] == make_slug(title) for j in jobs): continue
        _extract_and_append(block, title, jobs)

    return jobs


def generate_page(job):
    title = job['title']
    dept  = job['dept']
    ld    = job['last_date'] or 'Check official notification'
    sd    = job['start_date'] or TODAY
    vac   = job['vacancies']
    src   = job.get('official_url') or job['source_url']
    is_agg = job.get('is_aggregator', False)
    cat   = job['category']
    slug  = job['slug']
    ub    = '<span style="background:#FF4444;color:#fff;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;">🔥 URGENT</span>' if job['urgent'] else ''

    steps_html = ''.join(
        f'<li style="padding:9px 0;color:var(--grey-700);border-bottom:1px solid var(--border);font-size:.9rem;line-height:1.6;">{s}</li>'
        for s in [
            f'Visit the official website of <strong style="color:var(--white);">{dept}</strong> and go to Recruitment section.',
            'Download and read the official notification PDF carefully.',
            'Check eligibility — qualification, age limit and category.',
            'Register on the portal with valid email and mobile number.',
            'Fill the application form accurately with all details.',
            f'Pay fee (if applicable) and submit before <strong style="color:var(--white);">{ld}</strong>.',
            'Save your application number and take a printout.',
        ]
    )
    docs_html = ''.join(
        f'<li style="padding:5px 0;color:var(--grey-700);font-size:.88rem;">✓ {d}</li>'
        for d in ['10th/12th marksheet','Graduation certificate (if required)',
                  'Caste certificate (SC/ST/OBC)','Date of birth proof',
                  'Passport photo + signature','Valid photo ID (Aadhaar/PAN/Voter ID)']
    )
    schema = json.dumps({
        "@context":"https://schema.org","@type":"JobPosting",
        "title":title,"datePosted":datetime.now().strftime("%Y-%m-%d"),
        "validThrough":ld,"description":f"{title}. Last date: {ld}. Vacancies: {vac}.",
        "hiringOrganization":{"@type":"Organization","name":dept},
        "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress","addressCountry":"IN"}}
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — NaukriBulletin</title>
  <meta name="description" content="{title}. Last date {ld}. {vac} vacancies. Full details, eligibility and application steps.">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta name="robots" content="index,follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
  <script type="application/ld+json">{schema}</script>
</head>
<body>
<nav>
  <a href="/" class="logo" style="text-decoration:none;"><span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span></a>
  <ul id="navLinks">
    <li><a href="/jobs/" class="active">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI 🤖</a></li>
  </ul>
  <div class="nav-right"><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>
<header style="background:var(--navy);border-bottom:1px solid var(--border);padding:32px 20px 24px;">
  <div style="max-width:900px;margin:0 auto;">
    <div style="font-size:.78rem;color:var(--grey-400);margin-bottom:10px;">
      <a href="/" style="color:var(--grey-400);">Home</a> › <a href="/jobs/" style="color:var(--grey-400);">Jobs</a> › {title[:50]}
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
      <span style="background:rgba(255,107,0,.15);color:var(--saffron);padding:3px 12px;border-radius:20px;font-size:.75rem;font-weight:700;">{cat.upper()}</span>
      {ub}
    </div>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;color:var(--white);margin:0 0 8px;line-height:1.3;">{title}</h1>
    <p style="color:var(--grey-700);font-size:.9rem;margin:0;">Source: {dept} · Updated {TODAY}</p>
  </div>
</header>
<main style="max-width:900px;margin:0 auto;padding:28px 20px;">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:24px;">
    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">👥 Vacancies</div><div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800;color:var(--saffron);">{vac}</div></div>
    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">⏰ Last Date</div><div style="font-size:.9rem;font-weight:700;color:#FF6C8A;">{ld}</div></div>
    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">📅 Start Date</div><div style="font-size:.9rem;color:var(--white);">{sd}</div></div>
    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">📍 Location</div><div style="font-size:.9rem;color:var(--white);">All India</div></div>
    {"".join([f'<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">🎓 Qualification</div><div style="font-size:.88rem;color:var(--white);">{job["qualification"]}</div></div>' if job.get("qualification") else "", f'<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">💰 Salary</div><div style="font-size:.88rem;color:#63FFDA;">{job["salary"]}</div></div>' if job.get("salary") else ""])}
  </div>
  <div style="text-align:center;margin-bottom:28px;">
    <a href="{src}" target="_blank" rel="nofollow noopener" style="background:linear-gradient(135deg,#FF6B00,#FF8C33);color:#fff;padding:14px 40px;border-radius:12px;font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;text-decoration:none;display:inline-block;">Apply Now →</a>
    {"" if not is_agg else '<p style="margin-top:6px;font-size:.78rem;color:#FFD56C;">⚠️ Also check the <a href="' + job.get("source_url","") + '" target="_blank" rel="nofollow" style="color:#FFD56C;">source page</a> for the direct official link.</p>'}
    <p style="margin-top:8px;font-size:.78rem;color:var(--grey-400);">Apply only on official govt portals. Verify all details before applying.</p>
  </div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:20px;">
    <div style="padding:14px 18px;border-bottom:1px solid var(--border);background:var(--navy-soft);"><h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">📋 How to Apply — Step by Step</h2></div>
    <div style="padding:4px 18px 12px;"><ol style="margin:0;padding-left:18px;">{steps_html}</ol></div>
  </div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:20px;">
    <div style="padding:14px 18px;border-bottom:1px solid var(--border);background:var(--navy-soft);"><h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">📄 Documents Required</h2></div>
    <div style="padding:8px 18px 14px;"><ul style="margin:0;padding-left:18px;">{docs_html}</ul></div>
  </div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:20px;">
    <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0 0 12px;">🎂 Age Eligibility Calculator</h2>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
      <input type="date" id="nb-dob" style="background:var(--navy-soft);border:1px solid var(--border);color:var(--white);padding:8px 12px;border-radius:8px;font-size:.9rem;" />
      <button onclick="nbCalcAge()" style="background:var(--saffron);color:#fff;border:none;padding:9px 18px;border-radius:8px;font-weight:700;cursor:pointer;font-size:.88rem;">Check Age</button>
    </div>
    <div id="nb-age-result" style="margin-top:10px;font-size:.88rem;"></div>
  </div>
  <div style="background:rgba(255,107,0,.06);border:1px solid rgba(255,107,0,.2);border-radius:12px;padding:14px 18px;margin-bottom:20px;">
    <div style="font-size:.82rem;font-weight:700;color:var(--saffron);margin-bottom:6px;">⚠️ Important</div>
    <div style="font-size:.85rem;color:var(--grey-700);line-height:1.6;">Always verify on the official website before applying. NaukriBulletin provides information only.</div>
  </div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:24px;">
    <a href="/jobs/" style="background:var(--saffron);color:#fff;padding:9px 18px;border-radius:9px;font-weight:700;text-decoration:none;font-size:.88rem;">Browse All Jobs</a>
    <a href="/daily-quiz/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:9px 18px;border-radius:9px;font-weight:600;text-decoration:none;font-size:.88rem;">Today's Quiz</a>
    <a href="/ask-ai/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:9px 18px;border-radius:9px;font-weight:600;text-decoration:none;font-size:.88rem;">Ask NaukriBot</a>
  </div>
</main>
<footer style="border-top:1px solid var(--border);background:var(--navy);padding:24px 0;margin-top:32px;">
  <div style="max-width:900px;margin:0 auto;padding:0 20px;color:var(--grey-400);font-size:.85rem;display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;">
    <span>© {YR} NaukriBulletin</span>
    <span><a href="/" style="color:var(--grey-700);">Home</a> · <a href="/jobs/" style="color:var(--grey-700);">Jobs</a> · <a href="/ask-ai/" style="color:var(--grey-700);">Ask AI</a></span>
  </div>
</footer>
<script>
function nbCalcAge(){{var dob=new Date(document.getElementById("nb-dob").value);if(isNaN(dob.getTime())){{document.getElementById("nb-age-result").textContent="Please enter your date of birth.";return;}}var t=new Date(),y=t.getFullYear()-dob.getFullYear(),mo=t.getMonth()-dob.getMonth(),d=t.getDate()-dob.getDate();if(d<0){{mo--;d+=new Date(t.getFullYear(),t.getMonth(),0).getDate();}}if(mo<0){{y--;mo+=12;}}var el=document.getElementById("nb-age-result");var msg="Your age: "+y+" years "+mo+" months "+d+" days";if(y>=18&&y<=42){{el.innerHTML="<strong>"+msg+"</strong><br><small style=color:#63FFDA>Within typical range. Verify in official notification.</small>";}}else if(y<18){{el.innerHTML="<strong>"+msg+"</strong><br><small style=color:#FF6C8A>Below minimum age (18 years).</small>";}}else{{el.innerHTML="<strong>"+msg+"</strong><br><small style=color:#FFD56C>May exceed limit. Check relaxations.</small>";}}}}
</script>
<script src="/js/naukribot.js" defer></script>
<script>(function(){{var b=document.getElementById("navHamburger");var u=document.querySelector("nav ul");if(!b||!u)return;b.addEventListener("click",function(){{u.classList.toggle("mobile-open");b.classList.toggle("active");}});u.querySelectorAll("a").forEach(function(a){{a.addEventListener("click",function(){{u.classList.remove("mobile-open");b.classList.remove("active");}});}});}})();</script>
</body>
</html>'''

def main():
    if not BOT_TOKEN:
        print("❌ WA_BOT_TOKEN not set")
        sys.exit(1)

    last_id = get_last_update_id()
    print(f"Fetching updates after ID {last_id}...")

    result = tg_api('getUpdates', {
        'offset': last_id + 1,
        'limit': 100,
        'timeout': 5,
        'allowed_updates': 'message'
    })

    if not result or not result.get('ok'):
        print("❌ Failed to fetch Telegram updates")
        sys.exit(0)

    updates = result.get('result', [])
    print(f"Got {len(updates)} new messages")

    if not updates:
        print("No new messages")
        sys.exit(0)

    total_jobs = 0
    total_pages = 0

    for update in updates:
        uid = update['update_id']
        msg = update.get('message', {})
        text = msg.get('text', '') or msg.get('caption', '')
        from_id = str(msg.get('from', {}).get('id', ''))

        if not text or len(text) < 30:
            continue

        # Debug: show what we received
        print(f"  Msg from_id={from_id}, CHAT_ID={CHAT_ID}, text_len={len(text)}")
        print(f"  Preview: {repr(text[:80])}")

        # Only process messages from authorized user (skip if CHAT_ID set and doesn't match)
        if CHAT_ID and from_id != str(CHAT_ID):
            print(f"  ⏭ Skipped (from_id {from_id} != CHAT_ID {CHAT_ID})")
            continue

        # Check if it looks like a job alert
        if not any(x in text for x in ['*', 'Recruitment', 'Vacancy', 'Last Date', 'recruit']):
            continue

        jobs = parse_job_message(text)
        total_jobs += len(jobs)

        for job in jobs:
            page_dir = JOBS_DIR / job['slug']
            if page_dir.exists():
                print(f"  ⏭  Skip (exists): {job['title'][:50]}")
                continue
            # Also check for similar slugs (partial match on first 40 chars)
            slug_prefix = job['slug'][:40]
            similar = [p for p in JOBS_DIR.iterdir() if p.is_dir() and p.name.startswith(slug_prefix[:25])]
            if similar:
                print(f"  ⏭  Skip (similar exists): {job['title'][:50]} → {similar[0].name}")
                continue

            page_dir.mkdir(parents=True, exist_ok=True)
            html = generate_page(job)
            (page_dir / 'index.html').write_text(html, encoding='utf-8')
            print(f"  ✅ Created: {job['title'][:60]}")
            total_pages += 1

        save_last_update_id(uid)

    print(f"\n✅ Done — {total_jobs} jobs parsed, {total_pages} new pages created")

if __name__ == '__main__':
    main()
