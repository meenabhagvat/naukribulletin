#!/usr/bin/env python3
"""
NaukriBulletin — Phase 2: Category & State Page Generator
Run once after scraper to build SEO landing pages.
Also call from scraper.py at end of run() to keep pages fresh.

Pages generated:
  /jobs/ssc/           /jobs/railway/       /jobs/banking/
  /jobs/upsc/          /jobs/defence/       /jobs/police/
  /jobs/teaching/      /jobs/engineering/   /jobs/10th-pass/
  /jobs/12th-pass/     /jobs/graduate/
  /jobs/uttar-pradesh/ /jobs/bihar/         /jobs/madhya-pradesh/
  /jobs/rajasthan/     /jobs/tamil-nadu/    /jobs/karnataka/
  /jobs/maharashtra/   /jobs/gujarat/       /jobs/kerala/
  /jobs/all-india/
"""

import os
import re
from pathlib import Path
from datetime import datetime, date
from bs4 import BeautifulSoup

SITE_ROOT = Path(__file__).parent.parent

# ── CATEGORY DEFINITIONS ──────────────────────────────────────────────────────

CATEGORIES = [
    {
        "key": "ssc",
        "slug": "ssc",
        "title": "SSC Jobs",
        "heading": "SSC Recruitment 2026",
        "description": "Latest Staff Selection Commission (SSC) job notifications 2026. SSC CGL, CHSL, MTS, GD Constable, CPO, JE and more. Direct from SSC official website.",
        "meta": "Latest SSC jobs 2026 — CGL, CHSL, MTS, GD Constable notifications. Apply online for Staff Selection Commission recruitment. Updated daily.",
        "keywords": ["ssc", "cgl", "chsl", "mts", "gd constable", "staff selection", "ssc cpo", "ssc je"],
        "emoji": "📋",
        "color": "#1565C0",
        "bg": "#E3F2FD",
        "match_type": "tab_cat",
    },
    {
        "key": "railway",
        "slug": "railway",
        "title": "Railway Jobs",
        "heading": "Railway Recruitment 2026",
        "description": "Latest Indian Railways and RRB job notifications 2026. RRB NTPC, Group D, ALP, Technician, RPF and more. Apply for railway jobs directly.",
        "meta": "Latest railway jobs 2026 — RRB NTPC, Group D, ALP, Technician notifications. Apply online for Indian Railways recruitment. Updated 3× daily.",
        "keywords": ["railway", "rrb", "ntpc", "group d", "alp", "loco", "rpf", "rrc", "technician"],
        "emoji": "🚂",
        "color": "#1B5E20",
        "bg": "#E8F5E9",
        "match_type": "tab_cat",
    },
    {
        "key": "banking",
        "slug": "banking",
        "title": "Bank Jobs",
        "heading": "Banking Recruitment 2026",
        "description": "Latest bank job notifications 2026. IBPS PO, Clerk, SBI PO, RBI Grade B, NABARD and more. Apply for government bank jobs.",
        "meta": "Latest bank jobs 2026 — IBPS PO, SBI PO, RBI Grade B notifications. Apply online for banking recruitment. Free daily job alerts.",
        "keywords": ["bank", "ibps", "sbi", "rbi", "nabard", "po", "clerk", "banking"],
        "emoji": "🏦",
        "color": "#4A148C",
        "bg": "#F3E5F5",
        "match_type": "tab_cat",
    },
    {
        "key": "upsc",
        "slug": "upsc",
        "title": "UPSC Jobs",
        "heading": "UPSC Recruitment 2026",
        "description": "Latest UPSC job notifications 2026. Civil Services IAS, IPS, IFS, NDA, CDS, CAPF, ESE and more. Apply for Union Public Service Commission exams.",
        "meta": "Latest UPSC jobs 2026 — IAS, IPS, NDA, CDS notifications. Apply online for Union Public Service Commission recruitment. Updated daily.",
        "keywords": ["upsc", "ias", "ips", "ifs", "civil service", "nda", "cds", "capf", "ese"],
        "emoji": "🏛️",
        "color": "#B71C1C",
        "bg": "#FFEBEE",
        "match_type": "tab_cat",
    },
    {
        "key": "defence",
        "slug": "defence",
        "title": "Defence Jobs",
        "heading": "Defence Recruitment 2026",
        "description": "Latest Indian Army, Navy, Air Force and paramilitary job notifications 2026. Agniveer, Officer, Technical and other defence recruitment.",
        "meta": "Latest defence jobs 2026 — Army, Navy, Air Force, Agniveer notifications. Apply online for Indian defence recruitment. Updated daily.",
        "keywords": ["army", "navy", "air force", "defence", "agniveer", "military", "armed forces"],
        "emoji": "🪖",
        "color": "#1A237E",
        "bg": "#E8EAF6",
        "match_type": "tab_cat",
    },
    {
        "key": "police",
        "slug": "police",
        "title": "Police Jobs",
        "heading": "Police Recruitment 2026",
        "description": "Latest police and paramilitary job notifications 2026. CRPF, BSF, CISF, ITBP, SSB Constable, SI recruitment. Apply online.",
        "meta": "Latest police jobs 2026 — CRPF, BSF, CISF, Constable, SI notifications. Apply for police recruitment 2026. Updated daily.",
        "keywords": ["police", "constable", "crpf", "bsf", "cisf", "itbp", "ssb", "si", "inspector"],
        "emoji": "👮",
        "color": "#004D40",
        "bg": "#E0F2F1",
        "match_type": "tab_cat",
    },
    {
        "key": "teaching",
        "slug": "teaching",
        "title": "Teaching Jobs",
        "heading": "Teaching Recruitment 2026",
        "description": "Latest teacher and professor job notifications 2026. KVS, NVS, DSSSB Teacher, TGT, PGT, Lecturer, Professor recruitment.",
        "meta": "Latest teaching jobs 2026 — KVS, NVS, TGT, PGT, Professor notifications. Apply for teacher recruitment 2026. Updated daily.",
        "keywords": ["teacher", "professor", "lecturer", "kvs", "nvs", "tgt", "pgt", "teaching", "faculty"],
        "emoji": "📚",
        "color": "#E65100",
        "bg": "#FFF3E0",
        "match_type": "tab_cat",
    },
    {
        "key": "10th-pass",
        "slug": "10th-pass",
        "title": "10th Pass Jobs",
        "heading": "10th Pass Govt Jobs 2026",
        "description": "Latest government job notifications for 10th pass candidates 2026. Apply for Constable, Peon, Driver, MTS and other matriculation-level govt jobs.",
        "meta": "Govt jobs for 10th pass 2026 — Constable, MTS, Peon, Driver notifications. Apply online for 10th pass government recruitment. Updated daily.",
        "keywords": ["10th", "matriculation", "mts", "constable", "peon", "driver", "helper", "10th pass"],
        "emoji": "🎓",
        "color": "#37474F",
        "bg": "#ECEFF1",
        "match_type": "qualification",
        "qual_key": "10th Pass",
    },
    {
        "key": "12th-pass",
        "slug": "12th-pass",
        "title": "12th Pass Jobs",
        "heading": "12th Pass Govt Jobs 2026",
        "description": "Latest government job notifications for 12th pass / Intermediate candidates 2026. SSC CHSL, Railway Group D, Stenographer and more.",
        "meta": "Govt jobs for 12th pass 2026 — SSC CHSL, Railway, Stenographer notifications. Apply online for 12th pass government recruitment. Updated daily.",
        "keywords": ["12th", "intermediate", "hsc", "stenographer", "chsl", "12th pass"],
        "emoji": "📝",
        "color": "#0277BD",
        "bg": "#E1F5FE",
        "match_type": "qualification",
        "qual_key": "12th Pass",
    },
    {
        "key": "graduate",
        "slug": "graduate",
        "title": "Graduate Jobs",
        "heading": "Graduate Govt Jobs 2026",
        "description": "Latest government job notifications for graduate / degree holders 2026. SSC CGL, IBPS PO, UPSC, State PSC and more graduate-level jobs.",
        "meta": "Govt jobs for graduates 2026 — SSC CGL, IBPS PO, State PSC notifications. Apply online for graduate government recruitment. Updated daily.",
        "keywords": ["graduate", "degree", "b.sc", "b.com", "ba", "graduation"],
        "emoji": "🏫",
        "color": "#558B2F",
        "bg": "#F1F8E9",
        "match_type": "qualification",
        "qual_key": "Graduate",
    },
]

STATE_PAGES = [
    {"key": "all-india", "slug": "all-india", "title": "All India Jobs", "heading": "All India Govt Jobs 2026",
     "description": "Central government jobs open to candidates from all states across India 2026.", "state_match": "All India",
     "meta": "All India central government jobs 2026. Apply for SSC, Railway, UPSC, Banking and other central govt recruitment. Updated daily.", "emoji": "🇮🇳"},
    {"key": "uttar-pradesh", "slug": "uttar-pradesh", "title": "UP Govt Jobs", "heading": "Uttar Pradesh Govt Jobs 2026",
     "description": "Latest government job notifications from Uttar Pradesh 2026. UPPSC, UP Police, UP TET and more state government jobs.",
     "meta": "UP govt jobs 2026 — UPPSC, UP Police, UP TET notifications. Apply online for Uttar Pradesh government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Uttar Pradesh"},
    {"key": "bihar", "slug": "bihar", "title": "Bihar Govt Jobs", "heading": "Bihar Govt Jobs 2026",
     "description": "Latest government job notifications from Bihar 2026. BPSC, Bihar Police, BSSC and more state government jobs.",
     "meta": "Bihar govt jobs 2026 — BPSC, Bihar Police, BSSC notifications. Apply online for Bihar government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Bihar"},
    {"key": "madhya-pradesh", "slug": "madhya-pradesh", "title": "MP Govt Jobs", "heading": "Madhya Pradesh Govt Jobs 2026",
     "description": "Latest government job notifications from Madhya Pradesh 2026. MPPSC, MP Police, Vyapam and more.",
     "meta": "MP govt jobs 2026 — MPPSC, MP Police, Vyapam notifications. Apply online for Madhya Pradesh government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Madhya Pradesh"},
    {"key": "rajasthan", "slug": "rajasthan", "title": "Rajasthan Govt Jobs", "heading": "Rajasthan Govt Jobs 2026",
     "description": "Latest government job notifications from Rajasthan 2026. RPSC, Rajasthan Police, RSMSSB and more.",
     "meta": "Rajasthan govt jobs 2026 — RPSC, Rajasthan Police, RSMSSB notifications. Apply online for Rajasthan government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Rajasthan"},
    {"key": "tamil-nadu", "slug": "tamil-nadu", "title": "TN Govt Jobs", "heading": "Tamil Nadu Govt Jobs 2026",
     "description": "Latest government job notifications from Tamil Nadu 2026. TNPSC, TN Police, TNUSRB and more.",
     "meta": "Tamil Nadu govt jobs 2026 — TNPSC, TN Police, TNUSRB notifications. Apply online for Tamil Nadu government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Tamil Nadu"},
    {"key": "karnataka", "slug": "karnataka", "title": "Karnataka Govt Jobs", "heading": "Karnataka Govt Jobs 2026",
     "description": "Latest government job notifications from Karnataka 2026. KPSC, Karnataka Police, KSSB and more.",
     "meta": "Karnataka govt jobs 2026 — KPSC, Karnataka Police notifications. Apply online for Karnataka government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Karnataka"},
    {"key": "maharashtra", "slug": "maharashtra", "title": "Maharashtra Govt Jobs", "heading": "Maharashtra Govt Jobs 2026",
     "description": "Latest government job notifications from Maharashtra 2026. MPSC, Maharashtra Police, MH SSC Board and more.",
     "meta": "Maharashtra govt jobs 2026 — MPSC, Maharashtra Police notifications. Apply online for Maharashtra government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Maharashtra"},
    {"key": "gujarat", "slug": "gujarat", "title": "Gujarat Govt Jobs", "heading": "Gujarat Govt Jobs 2026",
     "description": "Latest government job notifications from Gujarat 2026. GPSC, Gujarat Police, GSSSB and more.",
     "meta": "Gujarat govt jobs 2026 — GPSC, Gujarat Police, GSSSB notifications. Apply online for Gujarat government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Gujarat"},
    {"key": "kerala", "slug": "kerala", "title": "Kerala Govt Jobs", "heading": "Kerala Govt Jobs 2026",
     "description": "Latest government job notifications from Kerala 2026. Kerala PSC, Kerala Police and more.",
     "meta": "Kerala govt jobs 2026 — Kerala PSC notifications. Apply online for Kerala government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Kerala"},
    {"key": "odisha", "slug": "odisha", "title": "Odisha Govt Jobs", "heading": "Odisha Govt Jobs 2026",
     "description": "Latest government job notifications from Odisha 2026. Odisha PSC, Odisha Police, OPSC and more state government jobs.",
     "meta": "Odisha govt jobs 2026 — OPSC, Odisha Police notifications. Apply online for Odisha government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Odisha"},
    {"key": "delhi", "slug": "delhi", "title": "Delhi Govt Jobs", "heading": "Delhi Govt Jobs 2026",
     "description": "Latest government job notifications from Delhi 2026. DSSSB, Delhi Police, Delhi High Court and more.",
     "meta": "Delhi govt jobs 2026 — DSSSB, Delhi Police notifications. Apply online for Delhi government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Delhi"},
    {"key": "assam", "slug": "assam", "title": "Assam Govt Jobs", "heading": "Assam Govt Jobs 2026",
     "description": "Latest government job notifications from Assam 2026. APSC, Assam Police, SSA Assam and more state government jobs.",
     "meta": "Assam govt jobs 2026 — APSC, Assam Police notifications. Apply online for Assam government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Assam"},
    {"key": "chhattisgarh", "slug": "chhattisgarh", "title": "CG Govt Jobs", "heading": "Chhattisgarh Govt Jobs 2026",
     "description": "Latest government job notifications from Chhattisgarh 2026. CGPSC, CG Vyapam, CG Police and more state government jobs.",
     "meta": "Chhattisgarh govt jobs 2026 — CGPSC, CG Vyapam notifications. Apply online for CG government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Chhattisgarh"},
    {"key": "punjab", "slug": "punjab", "title": "Punjab Govt Jobs", "heading": "Punjab Govt Jobs 2026",
     "description": "Latest government job notifications from Punjab 2026. PPSC, Punjab Police, PSSSB and more state government jobs.",
     "meta": "Punjab govt jobs 2026 — PPSC, Punjab Police notifications. Apply online for Punjab government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Punjab"},
    {"key": "haryana", "slug": "haryana", "title": "Haryana Govt Jobs", "heading": "Haryana Govt Jobs 2026",
     "description": "Latest government job notifications from Haryana 2026. HPSC, Haryana Police, HSSC and more state government jobs.",
     "meta": "Haryana govt jobs 2026 — HPSC, HSSC notifications. Apply online for Haryana government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Haryana"},
    {"key": "andhra-pradesh", "slug": "andhra-pradesh", "title": "AP Govt Jobs", "heading": "Andhra Pradesh Govt Jobs 2026",
     "description": "Latest government job notifications from Andhra Pradesh 2026. APPSC, AP Police, AP TET and more state government jobs.",
     "meta": "Andhra Pradesh govt jobs 2026 — APPSC, AP Police notifications. Apply online for AP government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Andhra Pradesh"},
    {"key": "telangana", "slug": "telangana", "title": "Telangana Govt Jobs", "heading": "Telangana Govt Jobs 2026",
     "description": "Latest government job notifications from Telangana 2026. TGPSC, Telangana Police, TSPSC and more state government jobs.",
     "meta": "Telangana govt jobs 2026 — TGPSC, Telangana Police notifications. Apply online for Telangana government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Telangana"},
    {"key": "west-bengal", "slug": "west-bengal", "title": "WB Govt Jobs", "heading": "West Bengal Govt Jobs 2026",
     "description": "Latest government job notifications from West Bengal 2026. WBPSC, WB Police, WBSSC and more state government jobs.",
     "meta": "West Bengal govt jobs 2026 — WBPSC, WB Police notifications. Apply online for WB government recruitment. Updated daily.", "emoji": "🏢", "state_match": "West Bengal"},
    {"key": "himachal-pradesh", "slug": "himachal-pradesh", "title": "HP Govt Jobs", "heading": "Himachal Pradesh Govt Jobs 2026",
     "description": "Latest government job notifications from Himachal Pradesh 2026. HPPSC, HP Police, HP TET and more state government jobs.",
     "meta": "Himachal Pradesh govt jobs 2026 — HPPSC notifications. Apply online for HP government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Himachal Pradesh"},
    {"key": "jharkhand", "slug": "jharkhand", "title": "Jharkhand Govt Jobs", "heading": "Jharkhand Govt Jobs 2026",
     "description": "Latest government job notifications from Jharkhand 2026. JPSC, Jharkhand Police, JSSC and more state government jobs.",
     "meta": "Jharkhand govt jobs 2026 — JPSC, JSSC notifications. Apply online for Jharkhand government recruitment. Updated daily.", "emoji": "🏢", "state_match": "Jharkhand"},
    {"key": "post-graduate", "slug": "post-graduate", "title": "Post Graduate Jobs", "heading": "Post Graduate Govt Jobs 2026",
     "description": "Government jobs for post graduate candidates 2026. MBA, M.Tech, MSc, MA, MCA and PhD holders. Central and state govt recruitment.",
     "meta": "Post graduate govt jobs 2026 — MBA, M.Tech, MSc, MA holders. Apply online for PG level government recruitment. Updated daily.", "emoji": "🎓", "state_match": ""},
]

# ── READ JOB METADATA FROM EXISTING PAGES ─────────────────────────────────────

def read_all_jobs():
    jobs_dir = SITE_ROOT / "jobs"
    jobs = []
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir():
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        try:
            with open(idx, encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
            if not title or title == "Latest Govt Jobs":
                continue

            # dept — orange label above h1
            dept_el = soup.find(style=lambda s: s and "letter-spacing" in str(s) and "FF6B00" in str(s))
            dept = dept_el.get_text(strip=True).title() if dept_el else ""

            # table rows
            rows = soup.find_all("tr")
            data = {}
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 2:
                    data[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)

            slug         = job_dir.name
            last_date    = data.get("last date", "N/A")
            vacancies    = data.get("total vacancies", "N/A")
            salary       = data.get("salary / pay scale", "N/A")
            location     = data.get("location", "All India")
            qualification = data.get("qualification", "")

            # derive tab_cat
            td = (title + " " + dept).lower()
            if any(x in td for x in ["ssc", "cgl", "chsl", "mts", " gd ", "cpo", "stenographer"]):
                tab_cat = "ssc"
            elif any(x in td for x in ["railway", "rrb", "ntpc", "group d", "alp", "loco", "rpf", "rrc"]):
                tab_cat = "railway"
            elif any(x in td for x in ["bank", "sbi", "ibps", "rbi", "nabard", "po ", "clerk"]):
                tab_cat = "banking"
            elif any(x in td for x in ["upsc", "ias", "ips", "civil service", "nda", "cds", "capf"]):
                tab_cat = "upsc"
            elif any(x in td for x in ["army", "navy", "air force", "defence", "agniveer", "afcat"]):
                tab_cat = "defence"
            elif any(x in td for x in ["police", "constable", "crpf", "bsf", "cisf", "itbp"]):
                tab_cat = "police"
            elif any(x in td for x in ["teacher", "professor", "lecturer", "kvs", "nvs", "tgt", "pgt", "faculty"]):
                tab_cat = "teaching"
            else:
                tab_cat = "state"

            # derive qualification bucket
            ql = qualification.lower()
            if any(x in ql for x in ["engineer", "b.tech", "b.e.", "diploma"]):
                qual_bucket = "Graduate"
            elif any(x in ql for x in ["post graduate", "master", "mba", "m.sc"]):
                qual_bucket = "Graduate"
            elif any(x in ql for x in ["graduate", "degree", "b.sc", "b.com", " ba ", "graduation"]):
                qual_bucket = "Graduate"
            elif any(x in ql for x in ["12th", "intermediate", "hsc", "class 12"]):
                qual_bucket = "12th Pass"
            elif any(x in ql for x in ["10th", "matriculation", "ssc", "class 10"]):
                qual_bucket = "10th Pass"
            else:
                qual_bucket = "Graduate"

            jobs.append({
                "slug": slug,
                "title": title,
                "dept": dept,
                "tab_cat": tab_cat,
                "qual_bucket": qual_bucket,
                "last_date": last_date,
                "vacancies": vacancies,
                "salary": salary,
                "location": location,
            })
        except Exception as e:
            pass
    return jobs


# ── HTML COMPONENTS ───────────────────────────────────────────────────────────

NAV = """  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/" class="active">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/results/">Results</a></li>
        <li><a href="/admit-card/">Admit Card</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>"""

FOOTER = lambda yr: f"""  <footer>
    <div class="footer-inner">
      <div class="footer-grid">
        <div class="footer-brand">
          <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
          <p>India's govt job portal. Direct from official sources. AI-powered daily alerts, always free.</p>
        </div>
        <div class="footer-col">
          <h4>By Category</h4>
          <ul>
            <li><a href="/jobs/ssc/">SSC Jobs</a></li>
            <li><a href="/jobs/railway/">Railway Jobs</a></li>
            <li><a href="/jobs/banking/">Bank Jobs</a></li>
            <li><a href="/jobs/upsc/">UPSC Jobs</a></li>
            <li><a href="/jobs/10th-pass/">10th Pass Jobs</a></li>
            <li><a href="/jobs/graduate/">Graduate Jobs</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>By State</h4>
          <ul>
            <li><a href="/jobs/uttar-pradesh/">UP Jobs</a></li>
            <li><a href="/jobs/bihar/">Bihar Jobs</a></li>
            <li><a href="/jobs/madhya-pradesh/">MP Jobs</a></li>
            <li><a href="/jobs/rajasthan/">Rajasthan Jobs</a></li>
            <li><a href="/jobs/tamil-nadu/">Tamil Nadu Jobs</a></li>
            <li><a href="/jobs/maharashtra/">Maharashtra Jobs</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Resources</h4>
          <ul>
            <li><a href="/results/">Results</a></li>
            <li><a href="/admit-card/">Admit Cards</a></li>
            <li><a href="/current-affairs/">Current Affairs</a></li>
            <li><a href="/syllabus/">Syllabus</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <p>© {yr} NaukriBulletin.in — All Rights Reserved</p>
        <p><a href="/privacy/" style="color:var(--grey-400);text-decoration:none;margin-right:16px;">Privacy Policy</a>
           <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a></p>
      </div>
    </div>
  </footer>"""


def job_card(job):
    ld = job.get("last_date", "N/A")
    badge = '<span style="background:#FFEBEE;color:#C62828;padding:3px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;">🔥 URGENT</span>'
    try:
        for fmt in ["%d %B %Y", "%d %b %Y", "%Y-%m-%d"]:
            try:
                days = (datetime.strptime(ld, fmt).date() - date.today()).days
                if days > 7:
                    badge = '<span style="background:#E8F5E9;color:#2E7D32;padding:3px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;">🟢 OPEN</span>'
                break
            except ValueError:
                continue
    except Exception:
        badge = '<span style="background:#E8F5E9;color:#2E7D32;padding:3px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;">🟢 OPEN</span>'

    return f"""      <a href="/jobs/{job['slug']}/" style="display:block;background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:18px 20px;text-decoration:none;color:inherit;transition:all 0.2s;" onmouseover="this.style.borderColor='#FF6B00';this.style.boxShadow='0 4px 20px rgba(255,107,0,0.1)'" onmouseout="this.style.borderColor='#ECEEF2';this.style.boxShadow='none'">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:10px;">
          <div>
            <div style="font-size:0.72rem;color:#9BA3B8;margin-bottom:3px;">{job.get('dept','')}</div>
            <div style="font-family:'Syne',sans-serif;font-size:0.98rem;font-weight:700;color:#1A1F35;line-height:1.3;">{job['title']}</div>
          </div>
          {badge}
        </div>
        <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:10px;">
          <span style="font-size:0.8rem;color:#4A5270;">👥 {job['vacancies']}</span>
          <span style="font-size:0.8rem;color:#4A5270;">📍 {job['location']}</span>
          <span style="font-size:0.8rem;color:#4A5270;">💰 {job['salary']}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid #F0F1F5;">
          <span style="font-size:0.8rem;color:#E65100;font-weight:600;">⏰ Last Date: {ld}</span>
          <span style="background:#0A0F2C;color:#fff;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;">Apply →</span>
        </div>
      </a>"""


# ── PAGE BUILDER ──────────────────────────────────────────────────────────────

def build_category_page(cat, jobs):
    yr = datetime.now().year
    slug = cat["slug"]

    # filter jobs for this category
    if cat.get("match_type") == "tab_cat":
        filtered = [j for j in jobs if j["tab_cat"] == cat["key"]]
    elif cat.get("match_type") == "qualification":
        filtered = [j for j in jobs if j["qual_bucket"] == cat["qual_key"]]
    else:
        filtered = jobs

    count = len(filtered)
    cards = "\n".join(job_card(j) for j in filtered) if filtered else \
        '<p style="color:#9BA3B8;text-align:center;padding:40px;">No jobs currently. Check back soon — updated 3× daily.</p>'

    # sidebar: related categories
    related_links = ""
    for c in CATEGORIES[:6]:
        if c["slug"] != slug:
            related_links += f'<li><a href="/jobs/{c["slug"]}/" style="color:#4A5270;text-decoration:none;font-size:0.85rem;display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F0F1F5;">{c["emoji"]} {c["title"]} <span style="color:#9BA3B8;">→</span></a></li>'

    state_links = ""
    for s in STATE_PAGES[:6]:
        state_links += f'<li><a href="/jobs/{s["slug"]}/" style="color:#4A5270;text-decoration:none;font-size:0.85rem;display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F0F1F5;">🏢 {s["title"]} <span style="color:#9BA3B8;">→</span></a></li>'

    # breadcrumb label
    breadcrumb_label = cat["title"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{cat['heading']} — {count}+ Vacancies | NaukriBulletin</title>
  <meta name="description" content="{cat['meta']}">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:title" content="{cat['heading']} — NaukriBulletin">
  <meta property="og:description" content="{cat['meta']}">
  <meta property="og:url" content="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:type" content="website">
  <meta name="robots" content="index, follow">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "{cat['heading']}",
    "description": "{cat['description']}",
    "url": "https://naukribulletin.in/jobs/{slug}/",
    "numberOfItems": {count},
    "publisher": {{
      "@type": "Organization",
      "name": "NaukriBulletin",
      "url": "https://naukribulletin.in"
    }}
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
</head>
<body>
{NAV}

  <div style="background:var(--navy,#0A0F2C);padding:40px 20px 36px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="font-size:0.78rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> ›
        <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;">Jobs</a> ›
        <span>{breadcrumb_label}</span>
      </div>
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
        <div style="width:52px;height:52px;border-radius:14px;background:rgba(255,107,0,0.15);display:flex;align-items:center;justify-content:center;font-size:1.5rem;">{cat['emoji']}</div>
        <div>
          <h1 style="font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:#fff;margin:0 0 4px;">{cat['heading']}</h1>
          <p style="color:#9BA3B8;font-size:0.9rem;margin:0;">{count} active notifications · updated 3× daily</p>
        </div>
      </div>
      <p style="color:#9BA3B8;font-size:0.9rem;max-width:680px;margin:0;">{cat['description']}</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:0 auto;padding:0 20px;">
    <div style="background:#FFF3E8;border-radius:0 0 12px 12px;padding:10px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
      <span style="font-size:0.82rem;color:#E65100;font-weight:600;">🔔 Get instant alerts for {cat['title']}</span>
      <a href="https://t.me/naukribulletin24" style="background:#FF6B00;color:#fff;padding:6px 16px;border-radius:6px;font-size:0.8rem;font-weight:700;text-decoration:none;">Join Telegram →</a>
    </div>
  </div>

  <div style="max-width:1200px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:1fr 300px;gap:24px;align-items:start;">

    <section>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">
          Showing <span style="color:#FF6B00;">{count}</span> {cat['title']} notifications
        </h2>
        <span style="font-size:0.78rem;color:#9BA3B8;">Last updated: {date.today().strftime('%d %b %Y')}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
{cards}
      </div>
    </section>

    <aside style="position:sticky;top:20px;display:flex;flex-direction:column;gap:16px;">

      <div style="background:#0A0F2C;border-radius:14px;padding:20px;text-align:center;">
        <div style="font-size:1.3rem;margin-bottom:8px;">📢</div>
        <h3 style="font-family:'Syne',sans-serif;font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px;">Free Job Alerts</h3>
        <p style="color:#9BA3B8;font-size:0.8rem;margin-bottom:14px;">Get notified instantly on Telegram when new {cat['title']} are posted</p>
        <a href="https://t.me/naukribulletin24" style="display:block;background:#FF6B00;color:#fff;padding:10px;border-radius:8px;font-weight:700;font-size:0.85rem;text-decoration:none;">Join Free Channel →</a>
      </div>

      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;color:#1A1F35;margin-bottom:12px;">📂 More Categories</h3>
        <ul style="list-style:none;padding:0;margin:0;">
          {related_links}
        </ul>
      </div>

      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;color:#1A1F35;margin-bottom:12px;">🗺️ Jobs by State</h3>
        <ul style="list-style:none;padding:0;margin:0;">
          {state_links}
        </ul>
      </div>

      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:16px;text-align:center;">
        <p style="font-size:0.75rem;color:#9BA3B8;margin-bottom:6px;">Advertisement</p>
        <div style="height:250px;background:#F7F8FA;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#9BA3B8;font-size:0.8rem;">Ad</div>
      </div>

    </aside>
  </div>

{FOOTER(yr)}

</body>
</html>"""
    return html


def build_state_page(state_cfg, jobs):
    yr    = datetime.now().year
    slug  = state_cfg["slug"]
    sm    = state_cfg.get("state_match", "")

    if sm == "All India":
        filtered = [j for j in jobs if j["location"] in ("All India", "N/A", "")]
    else:
        filtered = [j for j in jobs if sm.lower() in j["location"].lower() or sm.lower() in j["title"].lower() or sm.lower() in j["dept"].lower()]

    count = len(filtered)
    cards = "\n".join(job_card(j) for j in filtered) if filtered else \
        '<p style="color:#9BA3B8;text-align:center;padding:40px;">No state-specific jobs currently. Check All India jobs below.</p>'

    cat_links = ""
    for c in CATEGORIES[:8]:
        cat_links += f'<li><a href="/jobs/{c["slug"]}/" style="color:#4A5270;text-decoration:none;font-size:0.85rem;display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F0F1F5;">{c["emoji"]} {c["title"]} <span style="color:#9BA3B8;">→</span></a></li>'

    other_states = ""
    for s in STATE_PAGES:
        if s["slug"] != slug:
            other_states += f'<li><a href="/jobs/{s["slug"]}/" style="color:#4A5270;text-decoration:none;font-size:0.85rem;display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F0F1F5;">🏢 {s["title"]} <span style="color:#9BA3B8;">→</span></a></li>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{state_cfg['heading']} — {count}+ Vacancies | NaukriBulletin</title>
  <meta name="description" content="{state_cfg['meta']}">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta name="robots" content="index, follow">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "{state_cfg['heading']}",
    "description": "{state_cfg['description']}",
    "url": "https://naukribulletin.in/jobs/{slug}/",
    "numberOfItems": {count}
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
{NAV}

  <div style="background:var(--navy,#0A0F2C);padding:40px 20px 36px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="font-size:0.78rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> ›
        <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;">Jobs</a> ›
        <span>{state_cfg['title']}</span>
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:#fff;margin:0 0 8px;">{state_cfg['heading']}</h1>
      <p style="color:#9BA3B8;font-size:0.9rem;max-width:680px;">{state_cfg['description']}</p>
      <p style="color:#9BA3B8;font-size:0.85rem;margin-top:6px;">{count} active notifications · updated 3× daily</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:24px auto;padding:0 20px;display:grid;grid-template-columns:1fr 300px;gap:24px;align-items:start;">

    <section>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#1A1F35;">
          Showing <span style="color:#FF6B00;">{count}</span> jobs
        </h2>
        <span style="font-size:0.78rem;color:#9BA3B8;">Updated: {date.today().strftime('%d %b %Y')}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
{cards}
      </div>
      <div style="margin-top:24px;background:#FFF3E8;border-radius:12px;padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.95rem;font-weight:700;margin-bottom:8px;">Also check All India Jobs</h3>
        <p style="font-size:0.85rem;color:#4A5270;margin-bottom:12px;">Central government jobs are open to candidates from all states including {sm}.</p>
        <a href="/jobs/all-india/" style="background:#FF6B00;color:#fff;padding:8px 20px;border-radius:8px;font-weight:700;font-size:0.85rem;text-decoration:none;display:inline-block;">View All India Jobs →</a>
      </div>
    </section>

    <aside style="position:sticky;top:20px;display:flex;flex-direction:column;gap:16px;">
      <div style="background:#0A0F2C;border-radius:14px;padding:20px;text-align:center;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px;">📢 Free Alerts</h3>
        <p style="color:#9BA3B8;font-size:0.8rem;margin-bottom:14px;">Get notified for {state_cfg['title']} on Telegram</p>
        <a href="https://t.me/naukribulletin24" style="display:block;background:#FF6B00;color:#fff;padding:10px;border-radius:8px;font-weight:700;font-size:0.85rem;text-decoration:none;">Join Free →</a>
      </div>
      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;margin-bottom:12px;">📂 By Category</h3>
        <ul style="list-style:none;padding:0;margin:0;">{cat_links}</ul>
      </div>
      <div style="background:#fff;border-radius:14px;border:1.5px solid #ECEEF2;padding:20px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;margin-bottom:12px;">🗺️ Other States</h3>
        <ul style="list-style:none;padding:0;margin:0;">{other_states}</ul>
      </div>
    </aside>
  </div>

{FOOTER(yr)}
</body>
</html>"""
    return html


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run():
    print(f"\n{'='*56}")
    print(f"Phase 2 — Category & State Page Generator")
    print(f"{'='*56}\n")

    jobs = read_all_jobs()
    print(f"[READ] {len(jobs)} jobs loaded from /jobs/\n")

    total = 0

    # Category pages
    for cat in CATEGORIES:
        page_dir = SITE_ROOT / "jobs" / cat["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        html = build_category_page(cat, jobs)
        with open(page_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html)
        filtered_count = len([j for j in jobs if
            (cat.get("match_type") == "tab_cat" and j["tab_cat"] == cat["key"]) or
            (cat.get("match_type") == "qualification" and j["qual_bucket"] == cat.get("qual_key",""))
        ])
        print(f"  [CAT] /jobs/{cat['slug']}/ — {filtered_count} jobs")
        total += 1

    print()

    # State pages
    for state in STATE_PAGES:
        page_dir = SITE_ROOT / "jobs" / state["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        html = build_state_page(state, jobs)
        with open(page_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html)
        sm = state.get("state_match", "")
        if sm == "All India":
            fc = len([j for j in jobs if j["location"] in ("All India", "N/A", "")])
        else:
            fc = len([j for j in jobs if sm.lower() in j["location"].lower() or sm.lower() in j["title"].lower() or sm.lower() in j["dept"].lower()])
        print(f"  [STATE] /jobs/{state['slug']}/ — {fc} jobs")
        total += 1

    print(f"\n✅ {total} category/state pages generated")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    run()
