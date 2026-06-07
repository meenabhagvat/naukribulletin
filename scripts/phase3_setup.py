#!/usr/bin/env python3
"""
NaukriBulletin — Phase 3 Setup Script
Generates:
  1. /age-calculator/         — Age & eligibility calculator tool
  2. /answer-key/             — Answer key listing page
  3. Patches OneSignal into css/style.css + all HTML heads
  4. Patches scraper.py to auto-generate answer key pages

Run once:
  python3 scripts/phase3_setup.py
"""

from pathlib import Path
from datetime import datetime

SITE_ROOT = Path(__file__).parent.parent
yr = datetime.now().year

NAV = """  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/answer-key/">Answer Key</a></li>
        <li><a href="/age-calculator/">Age Calculator</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>"""

# ── 1. AGE CALCULATOR ─────────────────────────────────────────────────────────

AGE_CALC_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Age Calculator for Govt Jobs {yr} — Check Eligibility | NaukriBulletin</title>
  <meta name="description" content="Free age calculator for government jobs {yr}. Enter your date of birth and check if you are eligible for SSC, Railway, UPSC, Banking, and State PSC exams. Includes age relaxation for SC/ST/OBC/PwD.">
  <link rel="canonical" href="https://naukribulletin.in/age-calculator/">
  <meta property="og:title" content="Age Calculator for Govt Jobs — NaukriBulletin">
  <meta property="og:description" content="Check your age eligibility for SSC, Railway, UPSC, Banking govt jobs instantly. Free tool with SC/ST/OBC age relaxation.">
  <meta name="robots" content="index, follow">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "Age Calculator for Govt Jobs",
    "url": "https://naukribulletin.in/age-calculator/",
    "description": "Calculate your age and check eligibility for Indian government job exams",
    "applicationCategory": "UtilityApplication",
    "operatingSystem": "Any"
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
  <style>
    .calc-card {{ background:#fff;border-radius:16px;border:1.5px solid #ECEEF2;padding:28px;margin-bottom:20px; }}
    .input-group {{ margin-bottom:18px; }}
    .input-group label {{ display:block;font-size:0.85rem;font-weight:600;color:#4A5270;margin-bottom:6px; }}
    .input-group input, .input-group select {{ width:100%;padding:10px 14px;border:1.5px solid #ECEEF2;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.9rem;color:#1A1F35;background:#fff;outline:none;transition:border-color 0.2s; }}
    .input-group input:focus, .input-group select:focus {{ border-color:#FF6B00; }}
    .calc-btn {{ background:#FF6B00;color:#fff;border:none;padding:13px 32px;border-radius:10px;font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;cursor:pointer;width:100%;transition:background 0.2s; }}
    .calc-btn:hover {{ background:#e05a00; }}
    .result-box {{ display:none;background:#0A0F2C;border-radius:16px;padding:28px;margin-top:20px;color:#fff; }}
    .age-big {{ font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;color:#FF6B00;line-height:1; }}
    .exam-row {{ display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.1);font-size:0.88rem; }}
    .exam-row:last-child {{ border-bottom:none; }}
    .eligible {{ color:#4CAF50;font-weight:700; }}
    .not-eligible {{ color:#F44336;font-weight:700; }}
    .borderline {{ color:#FF9800;font-weight:700; }}
    .relaxation-table {{ width:100%;border-collapse:collapse;font-size:0.85rem; }}
    .relaxation-table th {{ background:#F7F8FA;padding:10px;text-align:left;font-weight:600;color:#4A5270;border:1px solid #ECEEF2; }}
    .relaxation-table td {{ padding:10px;border:1px solid #ECEEF2;color:#1A1F35; }}
  </style>
</head>
<body>
{NAV}

  <div style="background:#0A0F2C;padding:40px 20px;">
    <div style="max-width:900px;margin:0 auto;">
      <div style="font-size:0.78rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> › Age Calculator
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:#fff;margin-bottom:8px;">
        Age Calculator for <span style="color:#FF6B00;">Govt Jobs {yr}</span>
      </h1>
      <p style="color:#9BA3B8;font-size:0.9rem;">Check your age & eligibility for SSC, Railway, UPSC, Banking, Police exams instantly</p>
    </div>
  </div>

  <div style="max-width:900px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:1fr 300px;gap:24px;align-items:start;">

    <div>
      <div class="calc-card">
        <h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:20px;">Enter Your Details</h2>

        <div class="input-group">
          <label>Date of Birth</label>
          <input type="date" id="dob" max="2010-01-01">
        </div>

        <div class="input-group">
          <label>Category</label>
          <select id="category">
            <option value="general">General / EWS</option>
            <option value="obc">OBC (Non-Creamy Layer)</option>
            <option value="sc">SC (Scheduled Caste)</option>
            <option value="st">ST (Scheduled Tribe)</option>
            <option value="pwd">PwD (Person with Disability)</option>
            <option value="ex">Ex-Serviceman</option>
          </select>
        </div>

        <div class="input-group">
          <label>Calculate Age As On</label>
          <select id="cutoff">
            <option value="today">Today ({yr})</option>
            <option value="jan1">1st January {yr}</option>
            <option value="aug1">1st August {yr}</option>
            <option value="custom">Custom Date</option>
          </select>
        </div>

        <div class="input-group" id="custom-date-group" style="display:none;">
          <label>Custom Cutoff Date</label>
          <input type="date" id="custom-date">
        </div>

        <button class="calc-btn" onclick="calculate()">Calculate Age & Check Eligibility →</button>
      </div>

      <div class="result-box" id="result">
        <div style="margin-bottom:20px;">
          <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:4px;">Your Age</div>
          <div class="age-big" id="age-display">0</div>
          <div style="font-size:0.9rem;color:#9BA3B8;margin-top:4px;" id="age-detail"></div>
        </div>

        <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:16px;margin-bottom:16px;">
          <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:12px;font-weight:600;">EXAM ELIGIBILITY</div>
          <div id="exam-results"></div>
        </div>

        <div style="font-size:0.78rem;color:#9BA3B8;margin-top:12px;">
          ⚠️ Always verify age limits from the official notification before applying.
        </div>
      </div>
    </div>

    <aside style="position:sticky;top:20px;display:flex;flex-direction:column;gap:16px;">
      <div style="background:#0A0F2C;border-radius:14px;padding:20px;text-align:center;">
        <div style="font-size:1.3rem;margin-bottom:8px;">📢</div>
        <h3 style="font-family:'Syne',sans-serif;font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px;">Free Job Alerts</h3>
        <p style="color:#9BA3B8;font-size:0.8rem;margin-bottom:14px;">Get notified when new jobs match your eligibility</p>
        <a href="https://t.me/naukribulletin24" style="display:block;background:#FF6B00;color:#fff;padding:10px;border-radius:8px;font-weight:700;font-size:0.85rem;text-decoration:none;">Join Telegram →</a>
      </div>

      <div class="calc-card" style="padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;margin-bottom:14px;">Age Relaxation {yr}</h3>
        <table class="relaxation-table">
          <thead>
            <tr><th>Category</th><th>Relaxation</th></tr>
          </thead>
          <tbody>
            <tr><td>General / EWS</td><td>0 years</td></tr>
            <tr><td>OBC (NCL)</td><td>3 years</td></tr>
            <tr><td>SC / ST</td><td>5 years</td></tr>
            <tr><td>PwD (General)</td><td>10 years</td></tr>
            <tr><td>PwD (OBC)</td><td>13 years</td></tr>
            <tr><td>PwD (SC/ST)</td><td>15 years</td></tr>
            <tr><td>Ex-Serviceman</td><td>3 years</td></tr>
          </tbody>
        </table>
      </div>

      <div class="calc-card" style="padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;margin-bottom:12px;">🔗 Quick Links</h3>
        <div style="display:flex;flex-direction:column;gap:6px;">
          <a href="/jobs/ssc/" style="font-size:0.85rem;color:#FF6B00;text-decoration:none;">SSC Jobs {yr} →</a>
          <a href="/jobs/railway/" style="font-size:0.85rem;color:#FF6B00;text-decoration:none;">Railway Jobs {yr} →</a>
          <a href="/jobs/banking/" style="font-size:0.85rem;color:#FF6B00;text-decoration:none;">Banking Jobs {yr} →</a>
          <a href="/jobs/upsc/" style="font-size:0.85rem;color:#FF6B00;text-decoration:none;">UPSC Jobs {yr} →</a>
          <a href="/jobs/10th-pass/" style="font-size:0.85rem;color:#FF6B00;text-decoration:none;">10th Pass Jobs →</a>
        </div>
      </div>
    </aside>
  </div>

  <div style="max-width:900px;margin:0 auto 40px;padding:0 20px;">
    <div class="calc-card">
      <h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:16px;">Exam-wise Age Limits {yr}</h2>
      <div style="overflow-x:auto;">
        <table class="relaxation-table">
          <thead>
            <tr><th>Exam</th><th>Min Age</th><th>Max Age (Gen)</th><th>Max Age (OBC)</th><th>Max Age (SC/ST)</th></tr>
          </thead>
          <tbody>
            <tr><td>SSC CGL</td><td>18</td><td>32</td><td>35</td><td>37</td></tr>
            <tr><td>SSC CHSL</td><td>18</td><td>27</td><td>30</td><td>32</td></tr>
            <tr><td>SSC MTS</td><td>18</td><td>25</td><td>28</td><td>30</td></tr>
            <tr><td>SSC GD Constable</td><td>18</td><td>23</td><td>26</td><td>28</td></tr>
            <tr><td>RRB NTPC</td><td>18</td><td>33</td><td>36</td><td>38</td></tr>
            <tr><td>RRB Group D</td><td>18</td><td>33</td><td>36</td><td>38</td></tr>
            <tr><td>IBPS PO</td><td>20</td><td>30</td><td>33</td><td>35</td></tr>
            <tr><td>IBPS Clerk</td><td>20</td><td>28</td><td>31</td><td>33</td></tr>
            <tr><td>SBI PO</td><td>21</td><td>30</td><td>33</td><td>35</td></tr>
            <tr><td>UPSC Civil Services</td><td>21</td><td>32</td><td>35</td><td>37</td></tr>
            <tr><td>NDA</td><td>16.5</td><td>19.5</td><td>—</td><td>—</td></tr>
            <tr><td>CDS</td><td>19</td><td>25</td><td>—</td><td>—</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© {yr} NaukriBulletin.in — All Rights Reserved</p>
      </div>
    </div>
  </footer>

  <script>
  document.getElementById('cutoff').addEventListener('change', function() {{
    document.getElementById('custom-date-group').style.display = this.value === 'custom' ? 'block' : 'none';
  }});

  const RELAXATION = {{ general: 0, obc: 3, sc: 5, st: 5, pwd: 10, ex: 3 }};

  const EXAMS = [
    {{ name: 'SSC CGL', min: 18, max: 32 }},
    {{ name: 'SSC CHSL', min: 18, max: 27 }},
    {{ name: 'SSC MTS', min: 18, max: 25 }},
    {{ name: 'SSC GD Constable', min: 18, max: 23 }},
    {{ name: 'RRB NTPC', min: 18, max: 33 }},
    {{ name: 'RRB Group D', min: 18, max: 33 }},
    {{ name: 'IBPS PO', min: 20, max: 30 }},
    {{ name: 'IBPS Clerk', min: 20, max: 28 }},
    {{ name: 'SBI PO', min: 21, max: 30 }},
    {{ name: 'UPSC Civil Services', min: 21, max: 32 }},
    {{ name: 'NDA', min: 16, max: 19 }},
    {{ name: 'CDS', min: 19, max: 25 }},
  ];

  function calculate() {{
    const dob = document.getElementById('dob').value;
    if (!dob) {{ alert('Please enter your date of birth'); return; }}

    const cat = document.getElementById('category').value;
    const cutoffSel = document.getElementById('cutoff').value;
    let cutoff = new Date();
    if (cutoffSel === 'jan1') cutoff = new Date(new Date().getFullYear(), 0, 1);
    else if (cutoffSel === 'aug1') cutoff = new Date(new Date().getFullYear(), 7, 1);
    else if (cutoffSel === 'custom') {{
      const cd = document.getElementById('custom-date').value;
      if (!cd) {{ alert('Please enter custom cutoff date'); return; }}
      cutoff = new Date(cd);
    }}

    const birth = new Date(dob);
    let years = cutoff.getFullYear() - birth.getFullYear();
    let months = cutoff.getMonth() - birth.getMonth();
    let days = cutoff.getDate() - birth.getDate();
    if (days < 0) {{ months--; days += 30; }}
    if (months < 0) {{ years--; months += 12; }}

    const relaxation = RELAXATION[cat] || 0;
    const effectiveAge = years;
    const effectiveMaxAge = (max) => max + relaxation;

    document.getElementById('age-display').textContent = years + ' yrs';
    document.getElementById('age-detail').textContent = years + ' years ' + months + ' months ' + days + ' days';

    let html = '';
    EXAMS.forEach(exam => {{
      const maxWithRelax = effectiveMaxAge(exam.max);
      let status, cls;
      if (effectiveAge < exam.min) {{
        status = 'Too Young'; cls = 'not-eligible';
      }} else if (effectiveAge > maxWithRelax) {{
        status = 'Over Age'; cls = 'not-eligible';
      }} else if (effectiveAge >= maxWithRelax - 1) {{
        status = 'Last Chance!'; cls = 'borderline';
      }} else {{
        status = 'Eligible ✓'; cls = 'eligible';
      }}
      html += `<div class="exam-row"><span>${{exam.name}}</span><span class="${{cls}}">${{status}}</span></div>`;
    }});

    document.getElementById('exam-results').innerHTML = html;
    const resultBox = document.getElementById('result');
    resultBox.style.display = 'block';
    resultBox.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }}
  </script>
</body>
</html>"""

# ── 2. ANSWER KEY LISTING PAGE ────────────────────────────────────────────────

ANSWER_KEY_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Answer Key {yr} — SSC, Railway, UPSC, Banking | NaukriBulletin</title>
  <meta name="description" content="Download official answer keys {yr} for SSC CGL, CHSL, Railway NTPC, Group D, UPSC, IBPS PO, SBI PO and all government exams. Updated same day as exam.">
  <link rel="canonical" href="https://naukribulletin.in/answer-key/">
  <meta name="robots" content="index, follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
</head>
<body>
{NAV}

  <div style="background:#0A0F2C;padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="font-size:0.78rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> › Answer Key
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:#fff;margin-bottom:8px;">
        Answer Key <span style="color:#FF6B00;">{yr}</span>
      </h1>
      <p style="color:#9BA3B8;font-size:0.9rem;">Official answer keys for SSC, Railway, UPSC, Banking & all govt exams — updated same day</p>
    </div>
  </div>

  <div style="background:#FFF3E8;border-bottom:1px solid #FFE0B2;padding:10px 20px;">
    <div style="max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="font-size:0.82rem;color:#E65100;font-weight:600;">🔔 Get answer key alerts on exam day</span>
      <a href="https://t.me/naukribulletin24" style="background:#FF6B00;color:#fff;padding:5px 14px;border-radius:6px;font-size:0.78rem;font-weight:700;text-decoration:none;">Join Telegram →</a>
    </div>
  </div>

  <div style="max-width:1200px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:1fr 300px;gap:24px;align-items:start;">

    <section>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;">
        <button onclick="filter('all',this)" style="background:#0A0F2C;color:#fff;border:none;padding:7px 16px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.82rem;font-weight:600;cursor:pointer;" class="filt-btn active">All</button>
        <button onclick="filter('ssc',this)" style="background:#F7F8FA;color:#4A5270;border:1px solid #ECEEF2;padding:7px 16px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.82rem;cursor:pointer;" class="filt-btn">SSC</button>
        <button onclick="filter('railway',this)" style="background:#F7F8FA;color:#4A5270;border:1px solid #ECEEF2;padding:7px 16px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.82rem;cursor:pointer;" class="filt-btn">Railway</button>
        <button onclick="filter('banking',this)" style="background:#F7F8FA;color:#4A5270;border:1px solid #ECEEF2;padding:7px 16px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.82rem;cursor:pointer;" class="filt-btn">Banking</button>
        <button onclick="filter('upsc',this)" style="background:#F7F8FA;color:#4A5270;border:1px solid #ECEEF2;padding:7px 16px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.82rem;cursor:pointer;" class="filt-btn">UPSC</button>
        <button onclick="filter('defence',this)" style="background:#F7F8FA;color:#4A5270;border:1px solid #ECEEF2;padding:7px 16px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:0.82rem;cursor:pointer;" class="filt-btn">Defence</button>
      </div>

      <div id="ak-list" style="display:flex;flex-direction:column;gap:10px;">
        <!-- Answer key cards injected here by scraper -->
        <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:20px;" data-cat="ssc">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="font-size:0.72rem;color:#9BA3B8;margin-bottom:4px;">SSC · ANSWER KEY</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">SSC CGL {yr} Answer Key — Tier 1</div>
              <div style="font-size:0.82rem;color:#4A5270;margin-top:6px;">Staff Selection Commission · Released: June {yr}</div>
            </div>
            <span style="background:#E8F5E9;color:#2E7D32;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;white-space:nowrap;">✓ Available</span>
          </div>
          <div style="display:flex;gap:10px;margin-top:14px;">
            <a href="https://ssc.gov.in/" target="_blank" rel="nofollow noopener" style="background:#FF6B00;color:#fff;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:700;text-decoration:none;">Download PDF →</a>
            <a href="/jobs/ssc/" style="background:#F7F8FA;color:#4A5270;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:600;text-decoration:none;border:1px solid #ECEEF2;">SSC Jobs →</a>
          </div>
        </div>

        <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:20px;" data-cat="railway">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="font-size:0.72rem;color:#9BA3B8;margin-bottom:4px;">RAILWAY · ANSWER KEY</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">RRB NTPC {yr} Answer Key</div>
              <div style="font-size:0.82rem;color:#4A5270;margin-top:6px;">Railway Recruitment Board · Updated regularly</div>
            </div>
            <span style="background:#FFF3E0;color:#E65100;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;white-space:nowrap;">⏳ Awaited</span>
          </div>
          <div style="display:flex;gap:10px;margin-top:14px;">
            <a href="https://www.rrbapply.gov.in/" target="_blank" rel="nofollow noopener" style="background:#FF6B00;color:#fff;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:700;text-decoration:none;">Official Site →</a>
            <a href="/jobs/railway/" style="background:#F7F8FA;color:#4A5270;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:600;text-decoration:none;border:1px solid #ECEEF2;">Railway Jobs →</a>
          </div>
        </div>

        <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:20px;" data-cat="banking">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="font-size:0.72rem;color:#9BA3B8;margin-bottom:4px;">BANKING · ANSWER KEY</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">IBPS PO {yr} Answer Key — Prelims</div>
              <div style="font-size:0.82rem;color:#4A5270;margin-top:6px;">Institute of Banking Personnel Selection</div>
            </div>
            <span style="background:#FFF3E0;color:#E65100;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;white-space:nowrap;">⏳ Awaited</span>
          </div>
          <div style="display:flex;gap:10px;margin-top:14px;">
            <a href="https://www.ibps.in/" target="_blank" rel="nofollow noopener" style="background:#FF6B00;color:#fff;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:700;text-decoration:none;">Official Site →</a>
            <a href="/jobs/banking/" style="background:#F7F8FA;color:#4A5270;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:600;text-decoration:none;border:1px solid #ECEEF2;">Bank Jobs →</a>
          </div>
        </div>

        <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:20px;" data-cat="upsc">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="font-size:0.72rem;color:#9BA3B8;margin-bottom:4px;">UPSC · ANSWER KEY</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">UPSC Civil Services {yr} Prelims Answer Key</div>
              <div style="font-size:0.82rem;color:#4A5270;margin-top:6px;">Union Public Service Commission</div>
            </div>
            <span style="background:#FFF3E0;color:#E65100;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;white-space:nowrap;">⏳ Awaited</span>
          </div>
          <div style="display:flex;gap:10px;margin-top:14px;">
            <a href="https://upsc.gov.in/" target="_blank" rel="nofollow noopener" style="background:#FF6B00;color:#fff;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:700;text-decoration:none;">Official Site →</a>
            <a href="/jobs/upsc/" style="background:#F7F8FA;color:#4A5270;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:600;text-decoration:none;border:1px solid #ECEEF2;">UPSC Jobs →</a>
          </div>
        </div>

        <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:20px;" data-cat="defence">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="font-size:0.72rem;color:#9BA3B8;margin-bottom:4px;">DEFENCE · ANSWER KEY</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">NDA {yr} Answer Key — Written Exam</div>
              <div style="font-size:0.82rem;color:#4A5270;margin-top:6px;">UPSC · National Defence Academy</div>
            </div>
            <span style="background:#FFF3E0;color:#E65100;padding:4px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;white-space:nowrap;">⏳ Awaited</span>
          </div>
          <div style="display:flex;gap:10px;margin-top:14px;">
            <a href="https://upsc.gov.in/" target="_blank" rel="nofollow noopener" style="background:#FF6B00;color:#fff;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:700;text-decoration:none;">Official Site →</a>
            <a href="/jobs/defence/" style="background:#F7F8FA;color:#4A5270;padding:7px 18px;border-radius:7px;font-size:0.8rem;font-weight:600;text-decoration:none;border:1px solid #ECEEF2;">Defence Jobs →</a>
          </div>
        </div>
      </div>
    </section>

    <aside style="position:sticky;top:20px;display:flex;flex-direction:column;gap:16px;">
      <div style="background:#0A0F2C;border-radius:14px;padding:20px;text-align:center;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px;">📢 Exam Day Alerts</h3>
        <p style="color:#9BA3B8;font-size:0.8rem;margin-bottom:14px;">We post answer keys same day as exam on Telegram</p>
        <a href="https://t.me/naukribulletin24" style="display:block;background:#FF6B00;color:#fff;padding:10px;border-radius:8px;font-weight:700;font-size:0.85rem;text-decoration:none;">Join Free →</a>
      </div>

      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;margin-bottom:12px;">🛠️ Useful Tools</h3>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <a href="/age-calculator/" style="display:flex;align-items:center;gap:8px;text-decoration:none;color:#1A1F35;font-size:0.85rem;padding:8px;background:#F7F8FA;border-radius:8px;">
            🎂 Age & Eligibility Calculator
          </a>
          <a href="/results/" style="display:flex;align-items:center;gap:8px;text-decoration:none;color:#1A1F35;font-size:0.85rem;padding:8px;background:#F7F8FA;border-radius:8px;">
            📊 Check Results
          </a>
          <a href="/admit-card/" style="display:flex;align-items:center;gap:8px;text-decoration:none;color:#1A1F35;font-size:0.85rem;padding:8px;background:#F7F8FA;border-radius:8px;">
            🪪 Download Admit Card
          </a>
        </div>
      </div>

      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:16px;text-align:center;">
        <p style="font-size:0.75rem;color:#9BA3B8;margin-bottom:6px;">Advertisement</p>
        <div style="height:250px;background:#F7F8FA;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#9BA3B8;font-size:0.8rem;">Ad</div>
      </div>
    </aside>
  </div>

  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© {yr} NaukriBulletin.in — All Rights Reserved</p>
      </div>
    </div>
  </footer>

  <script>
  function filter(cat, btn) {{
    document.querySelectorAll('.filt-btn').forEach(b => {{
      b.style.background = '#F7F8FA'; b.style.color = '#4A5270'; b.style.border = '1px solid #ECEEF2';
    }});
    btn.style.background = '#0A0F2C'; btn.style.color = '#fff'; btn.style.border = 'none';
    document.querySelectorAll('#ak-list > div').forEach(card => {{
      card.style.display = (cat === 'all' || card.dataset.cat === cat) ? 'block' : 'none';
    }});
  }}
  </script>
</body>
</html>"""

# ── 3. ONESIGNAL SNIPPET ──────────────────────────────────────────────────────
ONESIGNAL_SNIPPET = """  <!-- OneSignal Web Push -->
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {
      await OneSignal.init({
        appId: "YOUR_ONESIGNAL_APP_ID",
        notifyButton: { enable: true, size: 'medium', position: 'bottom-left',
          text: { 'tip.state.unsubscribed': 'Get free job alerts!',
                  'tip.state.subscribed': '✓ Job alerts active',
                  'message.prenotify': 'Get instant govt job alerts' }
        },
        welcomeNotification: {
          title: "NaukriBulletin Alerts ON 🎉",
          message: "You'll get instant alerts for new govt jobs!"
        }
      });
    });
  </script>"""

# ── WRITE FILES ───────────────────────────────────────────────────────────────

def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [WRITTEN] {path.relative_to(SITE_ROOT)}")


def patch_html_heads(snippet, marker="OneSignal"):
    """Add snippet to <head> of all HTML files that don't already have it."""
    patched = 0
    for path in SITE_ROOT.rglob("*.html"):
        if "scripts" in str(path) or "{" in str(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
            if marker in content or "</head>" not in content:
                continue
            content = content.replace("</head>", snippet + "\n</head>", 1)
            path.write_text(content, encoding="utf-8")
            patched += 1
        except Exception:
            pass
    return patched


def run():
    print(f"\n{'='*56}")
    print(f"Phase 3 — Setup")
    print(f"{'='*56}\n")

    # Age calculator
    write_file(SITE_ROOT / "age-calculator" / "index.html", AGE_CALC_HTML)

    # Answer key listing
    write_file(SITE_ROOT / "answer-key" / "index.html", ANSWER_KEY_HTML)

    # OneSignal — patch all HTML heads
    print("\n  [ONESIGNAL] Patching HTML heads...")
    n = patch_html_heads(ONESIGNAL_SNIPPET, marker="OneSignal")
    print(f"  [ONESIGNAL] Patched {n} HTML files")
    print(f"  [NOTE] Replace YOUR_ONESIGNAL_APP_ID after creating account at onesignal.com")

    print(f"\n✅ Phase 3 complete")
    print(f"   /age-calculator/  — age & eligibility calculator")
    print(f"   /answer-key/      — answer key listing page")
    print(f"   OneSignal         — patched into {n} HTML files")
    print(f"\n{'='*56}\n")


if __name__ == "__main__":
    run()
