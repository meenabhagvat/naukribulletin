#!/usr/bin/env python3
"""
NaukriBulletin — Automated Job Scraper & Site Generator
Phase 1 upgrade: direct .gov.in sources, state PSCs, 3× daily runs
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime, date
from bs4 import BeautifulSoup
from pathlib import Path
import re
import subprocess

# ─── CONFIG ───────────────────────────────────────────────────────────────────

GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "ca-pub-1001412206051588")
ADSENSE_SLOT_TOP = os.environ.get("ADSENSE_SLOT_TOP", "XXXXXXXXXX")
ADSENSE_SLOT_MID = os.environ.get("ADSENSE_SLOT_MID", "XXXXXXXXXX")
SITE_ROOT = Path(__file__).parent.parent
SITE_URL  = "https://naukribulletin.in"

# ─── SOURCES ──────────────────────────────────────────────────────────────────
# Strategy: primary = direct .gov.in feeds (original, first-party)
#           secondary = official exam bodies (IBPS, RBI, etc.)
#           state PSCs = competitor gap (FreeJobAlert weak here)
#           supplementary = Employment News + NCS (official govt portals)
#           current affairs = PIB + DD News (official only)
#           news sources = The Hindu kept for current affairs only


# ─── CONTENT ENRICHMENT MODULE ────────────────────────────────────────────────

EXAM_KB = {
    "coral":            {"exams":["UPSC","SSC CGL"],"section":"Environment","why":"Coral reefs, bleaching and translocation appear almost every year in UPSC Prelims GS1 Environment section."},
    "tiger":            {"exams":["UPSC","SSC CGL"],"section":"Environment","why":"Tiger reserves and Project Tiger are standard static GK for SSC and UPSC."},
    "ramsar":           {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Environment","why":"Ramsar wetland sites appear in Banking, SSC and UPSC GK sections."},
    "national park":    {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Environment","why":"National parks and wildlife sanctuaries are standard GK for all competitive exams."},
    "climate":          {"exams":["UPSC"],"section":"Environment","why":"Climate policy and international agreements are core UPSC Prelims and Mains topics."},
    "election commission":{"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Polity","why":"Election Commission powers and functions are directly asked in Polity sections."},
    "supreme court":    {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"Supreme Court judgments and constitutional provisions are standard UPSC/SSC topics."},
    "parliament":       {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"Parliamentary procedures and bills are asked in Polity sections across exams."},
    "rbi":              {"exams":["IBPS PO","SBI PO","RBI Grade B","UPSC"],"section":"Banking","why":"RBI policies, rates and functions are the most asked topic in Banking exams GA section."},
    "repo rate":        {"exams":["IBPS PO","SBI PO","RBI Grade B"],"section":"Banking","why":"Monetary policy and repo rate changes are asked in every Banking exam GA section."},
    "gdp":              {"exams":["UPSC","IBPS PO"],"section":"Economy","why":"GDP growth and economic indicators are core topics for Banking and UPSC."},
    "budget":           {"exams":["UPSC","IBPS PO","SSC CGL"],"section":"Economy","why":"Union Budget is extensively covered in GA sections of all major exams."},
    "inflation":        {"exams":["IBPS PO","SBI PO","RBI Grade B"],"section":"Banking","why":"Inflation, WPI, CPI are standard Banking GA topics asked almost every year."},
    "indian army":      {"exams":["UPSC","SSC CGL","CDS"],"section":"Defence","why":"Army exercises and appointments appear in Defence Affairs section of UPSC and SSC."},
    "indian navy":      {"exams":["UPSC","SSC CGL","CDS"],"section":"Defence","why":"Naval exercises and acquisitions are standard Current Affairs for UPSC and SSC."},
    "isro":             {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Science & Tech","why":"ISRO missions are among the most asked Science & Tech questions across all exams."},
    "drdo":             {"exams":["UPSC","SSC CGL"],"section":"Science & Tech","why":"DRDO tests and defence technology are asked in Science & Tech sections."},
    "missile":          {"exams":["UPSC","SSC CGL"],"section":"Science & Tech","why":"Missile systems and defence technology appear in Science & Technology GK."},
    "tunnel":           {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Infrastructure","why":"Major infrastructure projects like tunnels appear in Geography and Current Affairs."},
    "railway":          {"exams":["RRB NTPC","RRB Group D","UPSC"],"section":"Infrastructure","why":"Railway projects are directly relevant for Railway exams and UPSC."},
    "g20":              {"exams":["UPSC","IBPS PO","SSC CGL"],"section":"International","why":"G20 summits and outcomes are extensively covered in all competitive exam GA sections."},
    "india japan":      {"exams":["UPSC"],"section":"International","why":"Bilateral relations and defence pacts are core UPSC Mains GS2 topics."},
    "united nations":   {"exams":["UPSC","SSC CGL"],"section":"International","why":"UN bodies and India's role are asked in International Relations sections."},
    "appointed":        {"exams":["UPSC","SSC CGL","IBPS PO","RRB NTPC"],"section":"Appointments","why":"Key appointments appear in GA sections of all exams."},
    "award":            {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Awards","why":"National and international awards are standard Current Affairs."},
    "scheme":           {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Government Schemes","why":"Government schemes and their beneficiaries are asked in Welfare and Polity sections."},
    "mission":          {"exams":["UPSC","SSC CGL"],"section":"Government Schemes","why":"Government missions and flagship programmes appear in Current Affairs sections."},
}

SECTION_CONTEXT = {
    "Environment":   "India is committed to protecting biodiversity under the Biological Diversity Act 2002 and the Convention on Biological Diversity (CBD). India has 106 National Parks, 567 Wildlife Sanctuaries and 18 Biosphere Reserves.",
    "Polity":        "India's governance is based on the Constitution of India (1950). The Union List, State List and Concurrent List in the Seventh Schedule distribute legislative powers between Centre and States.",
    "Banking":       "India's banking sector is regulated by the Reserve Bank of India (RBI), established in 1935. The RBI controls monetary policy including repo rate, reverse repo rate, CRR and SLR.",
    "Economy":       "India targets becoming a $5 trillion economy. The Union Budget and Economic Survey are key documents. India is the world's 5th largest economy by nominal GDP.",
    "Defence":       "India's defence is coordinated by the Ministry of Defence. India follows a policy of Aatmanirbhar Bharat (self-reliance) in defence production under DRDO and DPSUs.",
    "Science & Tech":"India's S&T ecosystem includes ISRO (space), DRDO (defence), CSIR (research) and IITs. India's space programme has achieved Mars Orbiter Mission, Chandrayaan and Gaganyaan.",
    "Infrastructure":"India's National Infrastructure Pipeline (NIP) targets ₹111 lakh crore by 2025. PM GatiShakti is the master plan for multimodal connectivity across India.",
    "International": "India follows strategic autonomy in foreign affairs. India is part of QUAD, BRICS, SCO, G20 and maintains bilateral relations with all major powers.",
    "Appointments":  "Constitutional office holders are appointed by the President. Key positions include Chief Justice of India, RBI Governor, Army/Navy/Air Force Chiefs and CEC.",
    "Awards":        "India confers Bharat Ratna, Padma Awards and Gallantry Awards annually. The Nobel Prize, Booker Prize and other international awards are also covered in Current Affairs.",
    "Government Schemes": "Key flagship schemes include PM Awas Yojana, Ayushman Bharat, PM Kisan, Jal Jeevan Mission, MGNREGS and PM GatiShakti. Knowing scheme names, benefits and target beneficiaries is essential.",
}

def get_exam_relevance(title, summary):
    """Match article to exam relevance using EXAM_KB."""
    text = (title + " " + summary).lower()
    for keyword, info in EXAM_KB.items():
        if keyword in text:
            return info
    return {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"General Awareness",
            "why":"Current affairs from all domains appear in the GA sections of SSC, Banking and UPSC exams."}

def build_ca_rich_block(title, summary):
    """Build exam-relevance block for a CA article."""
    from datetime import date as _date
    rel = get_exam_relevance(title, summary)
    exams_str = " · ".join(rel["exams"])
    exam_tags = "".join(
        f'<span style="background:rgba(255,107,0,.12);color:var(--saffron);padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;">{e}</span>'
        for e in rel["exams"]
    )
    context = SECTION_CONTEXT.get(rel["section"], SECTION_CONTEXT["General Awareness"] if "General Awareness" in SECTION_CONTEXT else "Current affairs form the General Awareness section of all competitive exams.")
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', summary) if len(s.strip()) > 20]
    key_facts = sentences[:3] if sentences else [summary[:120]]
    kf_html = "".join(f'<li style="padding:5px 0;color:var(--grey-700);font-size:.9rem;">{f}.</li>' for f in key_facts)
    
    return f'''
<div style="background:rgba(255,107,0,.06);border:1px solid rgba(255,107,0,.2);border-radius:12px;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:.72rem;font-weight:700;color:var(--saffron);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">📚 Exam Relevance — {rel["section"]}</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">{exam_tags}</div>
  <div style="font-size:.85rem;color:var(--grey-700);">{rel["why"]}</div>
</div>
<h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0 0 10px;">What happened</h2>
<p style="color:var(--grey-700);line-height:1.8;font-size:.95rem;margin-bottom:20px;">{summary}</p>
<h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0 0 10px;">Key facts for exam</h2>
<ul style="margin:0 0 20px;padding-left:20px;">{kf_html}
<li style="padding:5px 0;color:var(--grey-700);font-size:.9rem;">Topic section: <strong style="color:var(--white);">{rel["section"]}</strong> — relevant for <strong style="color:var(--white);">{exams_str}</strong>.</li></ul>
<h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0 0 10px;">Background & context</h2>
<p style="color:var(--grey-700);line-height:1.8;font-size:.95rem;margin-bottom:20px;">{context}</p>
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:.85rem;font-weight:700;color:var(--white);margin-bottom:6px;">🎯 Likely exam question pattern</div>
  <div style="font-size:.88rem;color:var(--grey-700);font-style:italic;">Questions on this topic typically appear as MCQs asking about the organisation involved, the location, the policy name, or the year. Review the key facts above carefully.</div>
</div>'''

def build_job_rich_block(job_data):
    """Build rich eligibility + application guide for job pages."""
    title    = job_data.get("title","")
    dept     = job_data.get("dept","")
    vac      = job_data.get("vacancies","N/A")
    qual     = job_data.get("qualification","N/A")
    age      = job_data.get("age_limit","N/A")
    salary   = job_data.get("salary","N/A")
    ld       = job_data.get("last_date","N/A")
    loc      = job_data.get("location","All India")

    # Calculate days left
    _dl = None
    if ld and ld != "N/A":
        import re as _re
        _MONTHS = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
                   "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
        _m = _re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", ld, _re.I)
        if _m:
            try:
                from datetime import date as _date
                _mon = _MONTHS.get(_m.group(2).lower())
                if _mon:
                    _ld_date = _date(int(_m.group(3)), _mon, int(_m.group(1)))
                    _dl = (_ld_date - _date.today()).days
            except: pass
    _dl_colour = "#FF4444" if _dl is not None and _dl <= 3 else "#FF8C33" if _dl is not None and _dl <= 7 else "#FFD56C" if _dl is not None and _dl <= 14 else "#63FFDA" if _dl is not None and _dl >= 0 else "#888"
    _dl_label = f"{_dl} days left" if _dl is not None and _dl >= 0 else "Expired" if _dl is not None else ""
    apply_url= job_data.get("apply_url","")

    steps = [
        f"Visit the official website of <strong style='color:var(--white);'>{dept}</strong> and navigate to the Recruitment / Careers section.",
        "Read the official notification PDF carefully — note vacancies, eligibility, fee and important dates.",
        f"Check eligibility: qualification required is <strong style='color:var(--white);'>{qual}</strong>{f', age limit: {age}' if age != 'N/A' else ''}.",
        "Register online, fill the application form with accurate details and upload required documents.",
        f"Pay the application fee (if applicable) and submit before <strong style='color:var(--white);'>{ld}</strong>.",
        "Save your application number and download the confirmation / admit card when released.",
    ]
    steps_html = "".join(f'<li style="padding:8px 0;color:var(--grey-700);border-bottom:1px solid var(--border);font-size:.9rem;line-height:1.6;">{step}</li>' for step in steps)
    
    docs = ["10th / 12th marksheet","Graduation certificate (if required)","Caste certificate (for reserved categories)","Age proof (Date of Birth certificate)","Passport-size photograph","Valid signature","ID proof (Aadhaar / PAN / Voter ID)"]
    docs_html = "".join(f'<li style="padding:5px 0;color:var(--grey-700);font-size:.88rem;">✓ {d}</li>' for d in docs)

    salary_block = ""
    if salary and salary != "N/A":
        salary_block = f'<div style="background:rgba(99,255,218,.06);border:1px solid rgba(99,255,218,.2);border-radius:10px;padding:14px 18px;margin-bottom:16px;"><div style="font-size:.8rem;font-weight:700;color:#63FFDA;text-transform:uppercase;margin-bottom:4px;">💰 Salary / Pay Scale</div><div style="color:var(--white);font-weight:600;">{salary}</div></div>'

    # Age calculator HTML (defined outside f-string to avoid backslash issues)
    _age_calc = (
        "<div style=\"background:var(--card-bg);border:1px solid var(--border);"
        "border-radius:14px;padding:18px;margin-bottom:16px;\">"
        "<h2 style=\"font-family:Syne,sans-serif;font-size:1rem;font-weight:700;"
        "color:var(--white);margin:0 0 12px;\">🎂 Age Eligibility Calculator</h2>"
        "<p style=\"font-size:.85rem;color:var(--grey-700);margin:0 0 12px;\">"
        "Enter your date of birth to check eligibility for this post.</p>"
        "<div style=\"display:flex;gap:10px;flex-wrap:wrap;align-items:center;\">"
        "<input type=\"date\" id=\"nb-dob\" style=\"background:var(--navy-soft);"
        "border:1px solid var(--border);color:var(--white);padding:8px 12px;"
        "border-radius:8px;font-size:.9rem;\" />"
        "<button onclick=\"nbCalcAge()\" style=\"background:var(--saffron);color:#fff;"
        "border:none;padding:9px 18px;border-radius:8px;font-weight:700;cursor:pointer;"
        "font-size:.88rem;\">Check Age</button></div>"
        "<div id=\"nb-age-result\" style=\"margin-top:10px;font-size:.88rem;\"></div></div>"
        "<script>"
        "function nbCalcAge(){"
        "var dob=new Date(document.getElementById(\"nb-dob\").value);"
        "if(isNaN(dob.getTime())){document.getElementById(\"nb-age-result\").textContent="
        "\"Please enter your date of birth.\";return;}"
        "var t=new Date(),y=t.getFullYear()-dob.getFullYear(),"
        "mo=t.getMonth()-dob.getMonth(),d=t.getDate()-dob.getDate();"
        "if(d<0){mo--;d+=new Date(t.getFullYear(),t.getMonth(),0).getDate();}"
        "if(mo<0){y--;mo+=12;}"
        "var el=document.getElementById(\"nb-age-result\");"
        "var msg=\"Your age: \"+y+\" years \"+mo+\" months \"+d+\" days\";"
        "if(y>=18&&y<=42){el.innerHTML=\"<strong>\"+msg+\"</strong>"
        "<br><small style=color:#63FFDA>Within typical range (18-42). Verify official notification.</small>\"}"
        "else if(y<18){el.innerHTML=\"<strong>\"+msg+\"</strong>"
        "<br><small style=color:#FF6C8A>Below minimum age (18 years).</small>\"}"
        "else{el.innerHTML=\"<strong>\"+msg+\"</strong>"
        "<br><small style=color:#FFD56C>May exceed limit. Check relaxations in official notification.</small>\"}"
        "}"
        "</script>"
    )

    _dl_tag = ("<div style=\"font-size:.75rem;font-weight:700;color:" + _dl_colour + ";margin-top:3px\">" + _dl_label + "</div>") if _dl_label else ""

    return f'''
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:24px;">
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">Total Vacancies</div><div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800;color:var(--saffron);">{vac}</div></div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">⏰ Last Date</div><div style="font-size:.95rem;font-weight:700;color:{_dl_colour};">{ld}</div>{_dl_tag}</div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">Location</div><div style="font-size:.9rem;color:var(--white);">{loc}</div></div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;"><div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">Qualification</div><div style="font-size:.85rem;color:var(--white);">{qual}</div></div>
</div>
{salary_block}
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:20px;">
  <div style="padding:14px 18px;border-bottom:1px solid var(--border);background:var(--navy-soft);"><h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">📋 How to Apply — Step by Step</h2></div>
  <div style="padding:4px 18px 12px;"><ol style="margin:0;padding-left:18px;">{steps_html}</ol></div>
</div>
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:20px;">
  <div style="padding:14px 18px;border-bottom:1px solid var(--border);background:var(--navy-soft);"><h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">📄 Documents Required</h2></div>
  <div style="padding:8px 18px 14px;"><ul style="margin:0;padding-left:18px;">{docs_html}</ul></div>
</div>
{_age_calc}
'''

SOURCES = [
    {
        "url": "https://www.ibps.in/",
        "type": "rss",
        "dept": "IBPS",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://bank.sbi/web/careers/current-openings",
        "fallback_url": "https://bank.sbi/web/careers/current-openings",
        "type": "html",
        "dept": "SBI",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.rbi.org.in/Scripts/RSS.aspx?Id=906",
        "fallback_url": "https://www.rbi.org.in/scripts/bs_vacancies.aspx",
        "type": "rss",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a, .post-title a",
        "dept": "RBI",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.ncs.gov.in/",
        "fallback_url": "https://www.ncs.gov.in/Pages/default.aspx",
        "type": "html",
        "selector": "td a, .notice a, li a, h4 a, .job-title a",
        "dept": "NCS (National Career Service)",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/",
        "fallback_url": "https://www.freejobalert.com/latest-jobs/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "Employment News",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },

    # ── DEFENCE / PARAMILITARY ─────────────────────────────────────────────
    {
        "url": "https://joinindianarmy.nic.in/",
        "fallback_url": "https://joinindianarmy.nic.in/",
        "type": "html",
        "selector": ".notification-list a, table tr td a, h3 a",
        "dept": "Indian Army",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://joinindiannavy.gov.in/",
        "fallback_url": "https://www.nausena-bharti.nic.in/",
        "type": "html",
        "selector": ".views-row a, td a, li a",
        "dept": "Indian Navy",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://careerindianairforce.cdac.in/",
        "fallback_url": "https://careerindianairforce.cdac.in/",
        "type": "html",
        "dept": "Indian Air Force",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://crpf.gov.in/recruitment.htm",
        "fallback_url": "https://crpf.gov.in/whatsnew.htm",
        "type": "html",
        "selector": "td a, li a, p a",
        "dept": "CRPF",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },

    # ── STATE PSCs (FreeJobAlert gap — prioritised) ─────────────────────────
    {
        "url": "https://uppsc.up.nic.in/CandidateInfo/LatestNews.aspx",
        "fallback_url": "https://uppsc.up.nic.in/CandidateInfo/LatestNews.aspx",
        "type": "html",
        "dept": "UPPSC (Uttar Pradesh)",
        "category": "state",
        "state": "Uttar Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://bpsc.bih.nic.in/Notices.html",
        "fallback_url": "https://bpsc.bih.nic.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "BPSC (Bihar)",
        "category": "state",
        "state": "Bihar",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://mppsc.mp.gov.in/",
        "fallback_url": "https://mppsc.mp.gov.in/recruitment",
        "type": "html",
        "selector": ".news-title a, td a, li a, h4 a, h3 a",
        "dept": "MPPSC (Madhya Pradesh)",
        "category": "state",
        "state": "Madhya Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://rpsc.rajasthan.gov.in/vacancies",
        "fallback_url": "https://rpsc.rajasthan.gov.in/",
        "type": "html",
        "selector": "td a, .list-group-item a, li a, h4 a",
        "dept": "RPSC (Rajasthan)",
        "category": "state",
        "state": "Rajasthan",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.tnpsc.gov.in/Notifications.html",
        "fallback_url": "https://tnpsc.gov.in/",
        "type": "html",
        "selector": "td a, .notice-board a, li a, p a",
        "dept": "TNPSC (Tamil Nadu)",
        "category": "state",
        "state": "Tamil Nadu",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://kpsc.kar.nic.in/newnotifications.htm",
        "fallback_url": "https://kpsc.kar.nic.in/",
        "type": "html",
        "selector": "td a, li a, p a",
        "dept": "KPSC (Karnataka)",
        "category": "state",
        "state": "Karnataka",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://mpsc.gov.in/adv_notification/8",
        "fallback_url": "https://mpsconline.gov.in/",
        "type": "html",
        "selector": "td a, .list a, li a, h4 a, .card a",
        "dept": "MPSC (Maharashtra)",
        "category": "state",
        "state": "Maharashtra",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://gpsc.gujarat.gov.in/ViewNotification",
        "fallback_url": "https://gpsc.gujarat.gov.in/ViewNotification",
        "type": "html",
        "dept": "GPSC (Gujarat)",
        "category": "state",
        "state": "Gujarat",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://hpsc.gov.in/recruitment-notice",
        "fallback_url": "https://hpsc.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "HPSC (Haryana)",
        "category": "state",
        "state": "Haryana",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://apsc.nic.in/Advertisements.html",
        "fallback_url": "https://apsc.nic.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "APSC (Assam)",
        "category": "state",
        "state": "Assam",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.keralapsc.gov.in/rss.xml",
        "fallback_url": "https://www.keralapsc.gov.in/notifications",
        "type": "rss",
        "dept": "Kerala PSC",
        "category": "state",
        "state": "Kerala",
        "priority": 2,
        "content_type": "job",
    },

    # ── CURRENT AFFAIRS (official sources only) ────────────────────────────
    {
        "url": "https://indianexpress.com/section/india/feed/",
        "fallback_url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "type": "rss",
        "dept": "PIB",
        "category": "news",
        "priority": 1,
        "content_type": "affairs",
    },
    {
        "url": "https://newsonair.gov.in/",
        "fallback_url": None,
        "type": "html",
        "dept": "DD News",
        "category": "news",
        "priority": 1,
        "content_type": "affairs",
    },
    {
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "fallback_url": None,
        "type": "rss",
        "dept": "The Hindu",
        "category": "news",
        "priority": 2,
        "content_type": "affairs",
    },

    # ── MISSING STATE PSCs ─────────────────────────────────────────────────
    {
        "url": "https://www.tspsc.gov.in/",
        "fallback_url": "https://www.tspsc.gov.in/Notifications.html",
        "type": "html",
        "selector": ".notice a, td a, li a, h4 a",
        "dept": "TGPSC (Telangana)",
        "category": "state",
        "state": "Telangana",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://psc.ap.gov.in/notifications",
        "fallback_url": "https://psc.ap.gov.in/",
        "type": "html",
        "selector": "td a, .notification a, li a, h4 a",
        "dept": "APPSC (Andhra Pradesh)",
        "category": "state",
        "state": "Andhra Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://opsc.gov.in/Advt.aspx",
        "fallback_url": "https://opsc.gov.in/Advt.aspx",
        "type": "html",
        "dept": "OPSC (Odisha)",
        "category": "state",
        "state": "Odisha",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.pscwb.org.in/pscwbmain/notice.html",
        "fallback_url": "https://www.pscwb.org.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "WBPSC (West Bengal)",
        "category": "state",
        "state": "West Bengal",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://ppsc.gov.in/Advertisements.aspx",
        "fallback_url": "https://ppsc.gov.in/Advertisements.aspx",
        "type": "html",
        "dept": "PPSC (Punjab)",
        "category": "state",
        "state": "Punjab",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.hppsc.hp.gov.in/hppsc/advertisement",
        "fallback_url": "https://www.hppsc.hp.gov.in/",
        "type": "html",
        "selector": "td a, .adv a, li a, p a",
        "dept": "HPPSC (Himachal Pradesh)",
        "category": "state",
        "state": "Himachal Pradesh",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.jpsc.gov.in/",
        "fallback_url": "https://jpsc.gov.in/advertisement",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "JPSC (Jharkhand)",
        "category": "state",
        "state": "Jharkhand",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://psc.cg.gov.in/",
        "fallback_url": "https://psc.cg.gov.in/",
        "type": "html",
        "dept": "CGPSC (Chhattisgarh)",
        "category": "state",
        "state": "Chhattisgarh",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://dsssb.delhi.gov.in/dsssb/recruitment-notices",
        "fallback_url": "https://dsssb.delhi.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "DSSSB (Delhi)",
        "category": "state",
        "state": "Delhi",
        "priority": 1,
        "content_type": "job",
    },

    # ── PSUs / CENTRAL ORGS ────────────────────────────────────────────────
    {
        "url": "https://careers.ntpc.co.in/",
        "fallback_url": "https://www.ntpc.co.in/en/careers",
        "type": "html",
        "selector": ".job-title a, td a, li a, h3 a, h4 a",
        "dept": "NTPC",
        "category": "engineering",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.bhel.com/rss.xml",
        "fallback_url": "https://www.bhel.com/career",
        "type": "rss",
        "dept": "BHEL",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://ongcindia.com/web/eng/recruitment",
        "fallback_url": "https://ongcindia.com/",
        "type": "html",
        "selector": ".recruitment-notice a, td a, li a, h4 a",
        "dept": "ONGC",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://nalcoindia.com/recruitment/",
        "fallback_url": "https://nalcoindia.com/",
        "type": "html",
        "selector": ".post-title a, td a, li a, h4 a, h3 a",
        "dept": "NALCO",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.coalindia.in/en-us/career/currentopenings.aspx",
        "fallback_url": "https://www.coalindia.in/en-us/career/currentopenings.aspx",
        "type": "html",
        "dept": "Coal India",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.recindia.nic.in/Careers/Vacancies",
        "fallback_url": "https://www.recindia.nic.in/",
        "type": "html",
        "selector": "td a, .vacancy a, li a, h4 a",
        "dept": "REC",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.nabard.org/careers.aspx",
        "fallback_url": "https://www.nabard.org/",
        "type": "html",
        "selector": "td a, .career-notice a, li a, p a",
        "dept": "NABARD",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.pnbindia.in/recruitment.html",
        "fallback_url": "https://www.pnbindia.in/",
        "type": "html",
        "selector": "td a, .recruit a, li a, p a",
        "dept": "PNB",
        "category": "banking",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.bankofbaroda.in/careers",
        "fallback_url": "https://www.bankofbaroda.in/careers",
        "type": "html",
        "dept": "Bank of Baroda",
        "category": "banking",
        "priority": 2,
        "content_type": "job",
    },

    # ── HIGH COURTS ────────────────────────────────────────────────────────
    {
        "url": "https://www.allahabadhighcourt.in/recruitment/RecruitmentNotification.html",
        "fallback_url": "https://www.allahabadhighcourt.in/",
        "type": "html",
        "selector": "td a, .notification a, li a, p a",
        "dept": "Allahabad High Court",
        "category": "state",
        "state": "Uttar Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://mphc.gov.in/recruitment",
        "fallback_url": "https://mphc.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "MP High Court",
        "category": "state",
        "state": "Madhya Pradesh",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://hcraj.nic.in/hcraj/recruitment.php",
        "fallback_url": "https://hcraj.nic.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "Rajasthan High Court",
        "category": "state",
        "state": "Rajasthan",
        "priority": 2,
        "content_type": "job",
    },

    # ── HEALTH / MEDICAL ───────────────────────────────────────────────────
    {
        "url": "https://esic.gov.in/recruitment",
        "fallback_url": "https://esic.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "ESIC",
        "category": "state",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.aiims.edu/en/notices/recruitment-notices.html",
        "fallback_url": "https://www.aiims.edu/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "AIIMS Delhi",
        "category": "teaching",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://main.icmr.gov.in/content/vacancies",
        "fallback_url": "https://icmr.gov.in/",
        "type": "html",
        "selector": "td a, .vacancy a, li a, p a",
        "dept": "ICMR",
        "category": "teaching",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://nhm.gov.in/index1.php?lang=1&level=2&sublinkid=1043&lid=308",
        "fallback_url": "https://nhm.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "NHM",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },

    # ── TEACHING / UNIVERSITIES ────────────────────────────────────────────
    {
        "url": "https://ugcnetonline.in/",
        "fallback_url": "https://ugc.gov.in/page/Whats-New/1",
        "type": "html",
        "selector": "td a, .notice a, li a, h4 a",
        "dept": "UGC",
        "category": "teaching",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://nta.ac.in/",
        "fallback_url": "https://nta.ac.in/",
        "type": "html",
        "dept": "NTA",
        "category": "teaching",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://home.iitd.ac.in/jobs.php",
        "fallback_url": "https://ird.iitd.ac.in/content/recruitment-advertisement",
        "type": "html",
        "selector": "td a, .job-listing a, li a, h4 a, p a",
        "dept": "IIT Delhi",
        "category": "teaching",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.du.ac.in/du/index.php?page=recruitment",
        "fallback_url": "https://www.du.ac.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "Delhi University",
        "category": "teaching",
        "priority": 2,
        "content_type": "job",
    },

    # ── POLICE / PARAMILITARY (additional) ────────────────────────────────
    {
        "url": "https://bsfrecruitment.in/",
        "fallback_url": "https://www.bsf.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a, h4 a",
        "dept": "BSF",
        "category": "police",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://cisfrectt.cisf.gov.in/",
        "fallback_url": "https://cisf.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "CISF",
        "category": "police",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.itbpolice.nic.in/WebPages/Recruitments/RecruitNotification.aspx",
        "fallback_url": "https://itbpolice.nic.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "ITBP",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://ssbrectt.gov.in/",
        "fallback_url": "https://ssb.nic.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a, h4 a",
        "dept": "SSB",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },

    # ── RAILWAYS (additional boards) ───────────────────────────────────────
    {
        "url": "https://rrbchennai.gov.in/",
        "fallback_url": "https://www.rrbapply.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "RRB Chennai",
        "category": "railway",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.rrbmumbai.gov.in/",
        "fallback_url": "https://www.rrbapply.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "RRB Mumbai",
        "category": "railway",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.rrbprayagraj.gov.in/",
        "fallback_url": "https://www.rrbapply.gov.in/",
        "type": "html",
        "selector": "td a, .notice a, li a, p a",
        "dept": "RRB Allahabad",
        "category": "railway",
        "priority": 2,
        "content_type": "job",
    },

    # ── FIXED PSC + CENTRAL ORG SOURCES ──────────────────────────────────────
    {"url":"https://bpsc.bih.nic.in/Ads.html","fallback_url":"https://bpsc.bih.nic.in/","type":"html","selector":"table a, td a, a[href*='pdf']","dept":"BPSC (Bihar)","category":"state","priority":1,"content_type":"job","state":"Bihar"},
    {"url":"https://rpsc.rajasthan.gov.in/notification","fallback_url":"https://rpsc.rajasthan.gov.in/","type":"html","selector":"table a, a[href*='advt'], a[href*='pdf']","dept":"RPSC (Rajasthan)","category":"state","priority":1,"content_type":"job","state":"Rajasthan"},
    {"url":"https://www.tnpsc.gov.in/Notifications.html","fallback_url":"https://www.tnpsc.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='notification']","dept":"TNPSC (Tamil Nadu)","category":"state","priority":1,"content_type":"job","state":"Tamil Nadu"},
    {"url":"https://tspsc.gov.in/notifications","fallback_url":"https://tspsc.gov.in/","type":"html","selector":"table a, a[href*='notification'], a[href*='pdf']","dept":"TGPSC (Telangana)","category":"state","priority":1,"content_type":"job","state":"Telangana"},
    {"url":"https://psc.ap.gov.in/notifications","fallback_url":"https://psc.ap.gov.in/","type":"html","selector":"table td a, a[href*='notification']","dept":"APPSC (Andhra Pradesh)","category":"state","priority":1,"content_type":"job","state":"Andhra Pradesh"},
    {"url":"https://wbpsc.gov.in/Notice","fallback_url":"https://wbpsc.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='Notice']","dept":"WBPSC (West Bengal)","category":"state","priority":1,"content_type":"job","state":"West Bengal"},
    {"url":"https://kpsc.kar.nic.in/newnotifications.htm","fallback_url":"https://kpsc.kar.nic.in/","type":"html","selector":"table a, a[href*='pdf']","dept":"KPSC (Karnataka)","category":"state","priority":1,"content_type":"job","state":"Karnataka"},
    {"url":"https://dsssb.delhi.gov.in/Advertisment.html","fallback_url":"https://dsssb.delhi.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='advt']","dept":"DSSSB (Delhi)","category":"state","priority":1,"content_type":"job","state":"Delhi"},
    {"url":"https://hpsc.gov.in/hpsc/Advertisement","fallback_url":"https://hpsc.gov.in/","type":"html","selector":"table a, a[href*='pdf']","dept":"HPSC (Haryana)","category":"state","priority":1,"content_type":"job","state":"Haryana"},
    {"url":"https://apsc.nic.in/apsc/Notices.aspx","fallback_url":"https://apsc.nic.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='notice']","dept":"APSC (Assam)","category":"state","priority":1,"content_type":"job","state":"Assam"},
    {"url":"https://hppsc.hp.gov.in/hppsc/Advertisements","fallback_url":"https://hppsc.hp.gov.in/","type":"html","selector":"table a, a[href*='pdf']","dept":"HPPSC (Himachal Pradesh)","category":"state","priority":1,"content_type":"job","state":"Himachal Pradesh"},
    {"url":"https://bsf.gov.in/recruitment.html","fallback_url":"https://bsf.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='recruit']","dept":"BSF","category":"defence","priority":1,"content_type":"job"},
    {"url":"https://crpf.gov.in/recruitment.htm","fallback_url":"https://crpf.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='recruit']","dept":"CRPF","category":"defence","priority":1,"content_type":"job"},
    {"url":"https://itbpolice.nic.in/Home/RecruitmentNotices","fallback_url":"https://itbpolice.nic.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='recruit']","dept":"ITBP","category":"defence","priority":1,"content_type":"job"},
    {"url":"https://ssbrectt.gov.in/Notices.aspx","fallback_url":"https://ssbrectt.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='notice']","dept":"SSB","category":"defence","priority":1,"content_type":"job"},
    {"url":"https://ongcindia.com/web/eng/careers","fallback_url":"https://ongcindia.com/","type":"html","selector":"a[href*='career'], a[href*='recruit'], table a","dept":"ONGC","category":"psu","priority":1,"content_type":"job"},
    {"url":"https://www.pnbindia.in/recruitment.html","fallback_url":"https://www.pnbindia.in/","type":"html","selector":"table a, a[href*='recruit'], a[href*='pdf']","dept":"PNB","category":"banking","priority":1,"content_type":"job"},
    {"url":"https://main.icmr.gov.in/content/vacancies","fallback_url":"https://main.icmr.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='vacanc']","dept":"ICMR","category":"central","priority":1,"content_type":"job"},
    {"url":"https://home.iitd.ac.in/jobs-iitd.php","fallback_url":"https://home.iitd.ac.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='job']","dept":"IIT Delhi","category":"teaching","priority":1,"content_type":"job"},
    {"url":"https://www.allahabadhighcourt.in/recruitment/recruitmentnotice.html","fallback_url":"https://www.allahabadhighcourt.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='recruit']","dept":"Allahabad High Court","category":"judiciary","priority":1,"content_type":"job","state":"Uttar Pradesh"},
    {"url":"https://mphc.gov.in/recruitment","fallback_url":"https://mphc.gov.in/","type":"html","selector":"table a, a[href*='pdf'], a[href*='recruit']","dept":"MP High Court","category":"judiciary","priority":1,"content_type":"job","state":"Madhya Pradesh"},
    {"url":"https://www.rrbmumbai.gov.in/pages/eng/latest-news.html","fallback_url":"https://www.rrbmumbai.gov.in/","type":"html","selector":"table td a, a[href*='pdf'], a[href*='news']","dept":"RRB Mumbai","category":"railway","priority":1,"content_type":"job"},
    {"url":"https://www.rrbald.gov.in/pages/eng/latest-news.html","fallback_url":"https://www.rrbald.gov.in/","type":"html","selector":"table td a, a[href*='pdf'], a[href*='news']","dept":"RRB Allahabad","category":"railway","priority":1,"content_type":"job"},
]

GROQ_MODELS  = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192"]
GEMINI_MODEL = "gemini-1.5-flash"

PROCESSED_FILE = SITE_ROOT / "scripts" / "processed.json"

# User-Agent rotator — avoids simple bot blocks on .gov.in sites
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]
_ua_index = 0


def next_ua():
    global _ua_index
    ua = UA_LIST[_ua_index % len(UA_LIST)]
    _ua_index += 1
    return ua


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(hashes):
    PROCESSED_FILE.parent.mkdir(exist_ok=True)
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(hashes), f)


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



def make_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


def make_slug(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = slug[:60].strip("-")
    return slug

_JUNK_SLUGS = {
    "na", "n-a", "nil", "none", "null", "apply-online", "click-here",
    "download", "home", "contact-us", "about-us", "privacy-policy",
    "otr-apply-online-recruitment-portal", "online-application-submission",
    "combined-examination", "combined-exam", "engineering", "banking",
    "teaching", "police", "railway", "defence", "graduate", "post-graduate",
    "10th-pass", "12th-pass", "iti-govt-jobs-2026", "mba-govt-jobs-2026",
}

def is_valid_slug(slug, title=""):
    if not slug or len(slug) < 8:
        return False
    if slug in _JUNK_SLUGS:
        return False
    # Block PHP, query strings, file extensions leaked into slug
    if any(x in slug for x in ['.php', '.json', '.asp', 'admitcard', 'list-rti', 'transfer-posting']):
        return False
    # Block state-name-only slugs
    if slug in {'assam', 'odisha', 'jharkhand', 'telangana', 'chhattisgarh', 'karnataka', 'bihar', 'rajasthan', 'uttar-pradesh', 'gujarat', 'haryana', 'delhi', 'himachal-pradesh', 'kerala', 'tamil-nadu', 'andhra-pradesh', 'madhya-pradesh'}:
        return False
    return True


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

def _get(url, timeout=20, is_html=False):
    """GET with rotating UA, retry once on failure.
    is_html=True sends browser-like Accept headers (needed for .gov.in HTML pages).
    """
    if is_html:
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    else:
        accept = "application/xml, text/xml, */*"
    headers = {
        "User-Agent": next_ua(),
        "Accept": accept,
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    try:
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        r.raise_for_status()
        return r
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code in (401, 403, 404, 410):
            return None          # permanent failure — skip silently
        raise
    except Exception:
        # One retry with a different UA after a short pause
        time.sleep(2)
        try:
            headers["User-Agent"] = next_ua()
            return requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        except Exception:
            return None


def scrape_rss(url, dept, fallback_url=None):
    """Fetch RSS. If RSS fails and a fallback HTML URL exists, fall back."""
    items = []
    resp = _get(url)

    if not resp or not resp.content.strip():
        if fallback_url:
            print(f"  [SCRAPER] RSS unavailable, trying HTML fallback: {fallback_url}")
            return scrape_html_smart(fallback_url, dept)
        return items

    try:
        soup = BeautifulSoup(resp.content, "xml")
        for item in soup.find_all("item")[:20]:
            title_tag       = item.find("title")
            desc_tag        = item.find("description")
            link_tag        = item.find("link")
            pubdate_tag     = item.find("pubDate")
            items.append({
                "title":       title_tag.get_text(strip=True)   if title_tag   else "",
                "description": desc_tag.get_text(strip=True)    if desc_tag    else "",
                "link":        link_tag.get_text(strip=True)     if link_tag    else "",
                "pubDate":     pubdate_tag.get_text(strip=True)  if pubdate_tag else "",
                "dept":        dept,
                "source_url":  url,
            })
    except Exception as e:
        print(f"  [SCRAPER] RSS parse error {url}: {e}")

    return items


def scrape_html(url, dept, selector=None):
    """Fetch HTML notification page and extract visible text (legacy blob method).
    Prefer scrape_html_smart() for list pages.
    """
    items = []
    resp = _get(url, is_html=True)
    if not resp:
        return items
    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        items.append({
            "title":       f"Latest Notifications from {dept}",
            "description": text[:3000],
            "link":        url,
            "pubDate":     str(date.today()),
            "dept":        dept,
            "source_url":  url,
        })
    except Exception as e:
        print(f"  [SCRAPER] HTML error {url}: {e}")
    return items


def scrape_html_smart(url, dept, selector=None):
    """Smart HTML scraper: extracts individual notification rows.

    Strategy (tried in order):
    1. Per-source CSS selector from SOURCES config  → individual <a> or <li> elements
    2. Generic table-row extraction                 → <tr> rows with links
    3. Generic link-list extraction                 → <a> tags matching job keywords
    4. Fall back to scrape_html (blob)              → single item

    Returns a list of items, each being one notification.
    """
    JOB_KEYWORDS = re.compile(
        r"(recruit|vacanc|post|appoint|notif|advertis|appl|exam|result|admit|syllabus"
        r"|job|career|opening|walkin|walk-in|interview|selection|merit|list|answer.key"
        r"|hall.ticket|call.letter|cut.off|cutoff|sarkari|bharti|notification)",
        re.IGNORECASE,
    )

    resp = _get(url, is_html=True)
    if not resp:
        return []

    try:
        soup = BeautifulSoup(resp.content, "html.parser")
    except Exception as e:
        print(f"  [SMART] Parse error {url}: {e}")
        return []

    items = []

    # ── Strategy 1: explicit CSS selector ───────────────────────────────────
    if selector:
        try:
            nodes = soup.select(selector)[:15]
            for node in nodes:
                link_tag = node if node.name == "a" else node.find("a")
                title = node.get_text(separator=" ", strip=True)[:200]
                href  = link_tag["href"] if link_tag and link_tag.get("href") else url
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    base = urlparse(url)
                    href = f"{base.scheme}://{base.netloc}{href}"
                if title:
                    items.append({
                        "title":       title,
                        "description": title,
                        "link":        href,
                        "pubDate":     str(date.today()),
                        "dept":        dept,
                        "source_url":  url,
                    })
            if items:
                return items
        except Exception as e:
            print(f"  [SMART] Selector error: {e}")

    # ── Strategy 2: table rows with links ───────────────────────────────────
    for table in soup.find_all("table")[:5]:
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        for row in rows[1:16]:  # skip header row, take up to 15
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            link_tag = row.find("a", href=True)
            # find the cell with the most text (notification title)
            text_cell = max(cells, key=lambda c: len(c.get_text(strip=True)))
            title = text_cell.get_text(separator=" ", strip=True)[:200]
            if not title or len(title) < 10:
                continue
            href = url
            if link_tag:
                href = link_tag["href"]
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    base = urlparse(url)
                    href = f"{base.scheme}://{base.netloc}{href}"
            items.append({
                "title":       title,
                "description": title,
                "link":        href,
                "pubDate":     str(date.today()),
                "dept":        dept,
                "source_url":  url,
            })
        if items:
            return items

    # ── Strategy 3: anchor tags matching job keywords ────────────────────────
    for a in soup.find_all("a", href=True)[:100]:
        text = a.get_text(strip=True)
        if len(text) < 15 or len(text) > 300:
            continue
        if not JOB_KEYWORDS.search(text):
            continue
        href = a["href"]
        if href.startswith("/"):
            from urllib.parse import urlparse
            base = urlparse(url)
            href = f"{base.scheme}://{base.netloc}{href}"
        items.append({
            "title":       text,
            "description": text,
            "link":        href,
            "pubDate":     str(date.today()),
            "dept":        dept,
            "source_url":  url,
        })
        if len(items) >= 10:
            break

    if items:
        return items

    # ── Strategy 4: fall back to blob ───────────────────────────────────────
    return scrape_html(url, dept)


# ─── AI FORMATTER ─────────────────────────────────────────────────────────────

JOB_PROMPT = """\
You are a govt job notification formatter for India.
Extract job details from the raw text below and return ONLY valid JSON, no other text.

Raw text: {raw_text}
Department hint: {dept}
State hint: {state}

Return this exact JSON structure (fill with "N/A" if not found):
{{
  "is_job_notification": true,
  "title": "Full job title including post name and organisation. Spell out abbreviations (e.g. 'Assistant Engineer' not 'AE', 'Junior Research Fellow' not 'JRF'). Do NOT include vacancy count or dates here.",
  "department": "Full official department/organisation name",
  "vacancies": "Total number of posts as a plain integer, or N/A",
  "qualification": "Minimum educational qualification",
  "age_limit": "Age range e.g. 18-25 years",
  "last_date": "DD Month YYYY or N/A",
  "salary": "Pay scale or salary range in ₹, or N/A",
  "state": "{state_hint}",
  "category": "10th Pass / 12th Pass / Graduate / Post Graduate / Engineering",
  "apply_link": "Official apply URL or source URL",
  "summary": "2 plain-English sentences about this job opportunity",
  "meta_description": "SEO description 130-155 characters. Must include: organisation name, number of posts (if known), qualification required, and last date (if known). Example: 'DRDO SAG Paid Internship 2026: 40 posts for B.Tech/M.Tech graduates. Apply online before 15 June 2026 at the official DRDO website.'",
  "exam_relevance": "Which exams this relates to e.g. SSC CGL, Railway NTPC",
  "slug": "url-friendly-slug-max-60-chars"
}}
"""

AFFAIRS_PROMPT = """\
You are a current affairs formatter for Indian competitive exam students.
Extract key news from the raw text and return ONLY a valid JSON array, no other text.

Raw text: {raw_text}

Return a JSON array of up to 5 items, each:
{{
  "title": "Clear news headline",
  "category": "Economy / Science & Tech / International / Sports / Awards / Government Schemes / Environment",
  "summary": "2-3 sentences explaining relevance for competitive exams",
  "key_facts": ["fact1", "fact2", "fact3"],
  "exam_relevance": "UPSC / SSC / Banking / All",
  "slug": "url-friendly-slug"
}}
"""


def call_groq(prompt):
    for model in GROQ_MODELS:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            if resp.status_code == 429:
                print(f"  [GROQ] Rate limited on {model}, trying next...")
                time.sleep(3)
        except Exception as e:
            print(f"  [GROQ] Error with {model}: {e}")
    return None


def call_gemini(prompt):
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  [GEMINI] Error: {e}")
    return None


def extract_json(text):
    if not text:
        return None
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def format_with_ai(item, content_type="job"):
    raw_text   = f"{item.get('title', '')} {item.get('description', '')} {item.get('link', '')}"[:2500]
    dept       = item.get("dept", "")
    state_hint = item.get("state", "All India")

    if content_type == "job":
        prompt = JOB_PROMPT.format(raw_text=raw_text, dept=dept, state=state_hint, state_hint=state_hint)
    else:
        prompt = AFFAIRS_PROMPT.format(raw_text=raw_text)

    result = call_groq(prompt)
    if not result:
        print("  [AI] Groq failed, trying Gemini...")
        result = call_gemini(prompt)

    return extract_json(result)


# ─── HTML GENERATORS ──────────────────────────────────────────────────────────

def generate_job_html(job):
    slug  = job.get("slug") or make_slug(job.get("title", "job"))
    today = datetime.now().strftime("%d %B %Y")

    # ── Schema helpers ──────────────────────────────────────────────────────
    _ld = job.get("last_date", "") or ""
    _valid_through = ""
    for _fmt in ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            from datetime import datetime as _dt2
            _valid_through = _dt2.strptime(_ld.strip(), _fmt).strftime("%Y-%m-%dT23:59:59")
            break
        except Exception:
            pass
    if not _valid_through:
        from datetime import datetime as _dt2, timedelta as _td
        _valid_through = (_dt2.now() + _td(days=90)).strftime("%Y-%m-%dT23:59:59")
    _sal = job.get("salary", "") or ""
    _sal_desc = _sal.replace('"', "'") if _sal and _sal.strip().lower() not in ("n/a", "", "as per govt norms") else "As per Government Pay Scale"

    # ── SEO title: base title + vacancy suffix + deadline suffix ────────────
    _base_title = job.get("title", "Govt Job")
    _vac   = str(job.get("vacancies", "") or "").strip()
    _ldate = str(job.get("last_date",  "") or "").strip()
    _suffix_parts = []
    if _vac and _vac.lower() not in ("n/a", "0", ""):
        try:
            _n = int(_vac.replace(',', ''))
            _label = "Post" if _n == 1 else "Posts"
            _suffix_parts.append(f"{_n:,} {_label}")
        except ValueError:
            _suffix_parts.append(f"{_vac} Posts")
    if _ldate and _ldate.lower() not in ("n/a", ""):
        _suffix_parts.append(f"Apply by {_ldate}")
    _suffix = " — " + " | ".join(_suffix_parts) if _suffix_parts else ""
    _seo_title = f"{_base_title}{_suffix}"
    if len(_seo_title) > 75:
        _seo_title = f"{_base_title}" + (" — " + _suffix_parts[0] if _suffix_parts else "")
    if len(_seo_title) > 75:
        _seo_title = _base_title

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_seo_title} — NaukriBulletin</title>
  <meta name="description" content="{job.get('meta_description', '')}">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:title" content="{_seo_title}">
  <meta property="og:description" content="{job.get('meta_description', '')}">
  <meta property="og:url" content="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:type" content="website">
  <meta property="og:image" content="https://naukribulletin.in/assets/logo-256.png">
  <meta name="twitter:card" content="summary">
  <meta name="robots" content="index, follow">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "{job.get('title', '')}",
    "description": "{job.get('summary', '')}",
    "hiringOrganization": {{
      "@type": "Organization",
      "name": "{job.get('department', 'Government of India')}"
    }},
    "jobLocation": {{
      "@type": "Place",
      "address": {{
        "@type": "PostalAddress",
        "streetAddress": "{job.get('department', 'Government Office')}",
        "addressLocality": "{job.get('state', 'All India')}",
        "addressRegion": "{job.get('state', 'All India')}",
        "postalCode": "110001",
        "addressCountry": "IN"
      }}
    }},
    "datePosted": "{today}",
    "validThrough": "{_valid_through}",
    "baseSalary": {{
      "@type": "MonetaryAmount",
      "currency": "INR",
      "value": {{
        "@type": "QuantitativeValue",
        "description": "{_sal_desc}"
      }}
    }},
    "employmentType": "FULL_TIME",
    "url": "https://naukribulletin.in/jobs/{slug}/"
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
  <nav>
  <a href="/" class="logo" style="text-decoration:none;">
    <span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span>
  </a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right">
    <a href="/alerts/" class="nav-cta">🔔 Get Alerts</a>
  </div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>

  <div style="max-width:900px;margin:20px auto;padding:0 20px;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_TOP}" data-ad-format="auto"></ins>
  </div>

  <main style="max-width:900px;margin:0 auto;padding:20px;">
    <div class="breadcrumb" style="font-size:0.8rem;color:#9BA3B8;margin-bottom:16px;">
      <a href="/" style="color:#9BA3B8;">Home</a> ›
      <a href="/jobs/" style="color:#9BA3B8;">Jobs</a> ›
      <span>{job.get('department', '')}</span>
    </div>

    <article class="job-detail">
      <div class="job-header" style="background:#0A0F2C;border-radius:16px;padding:32px;margin-bottom:24px;">
        <div style="color:#FF6B00;font-size:0.75rem;font-weight:700;letter-spacing:0.05em;margin-bottom:8px;">{job.get('department', '').upper()}</div>
        <h1 style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:#fff;margin-bottom:16px;">{job.get('title', '')}</h1>
        <p style="color:#9BA3B8;font-size:0.95rem;">{job.get('summary', '')}</p>
        <div style="margin-top:20px;display:flex;gap:12px;flex-wrap:wrap;">
          <span style="background:rgba(255,107,0,0.15);color:#FF8C33;padding:5px 12px;border-radius:6px;font-size:0.8rem;font-weight:600;">📅 Last Date: {job.get('last_date', 'N/A')}</span>
          <span style="background:rgba(19,136,8,0.15);color:#1AA60A;padding:5px 12px;border-radius:6px;font-size:0.8rem;font-weight:600;">👥 Vacancies: {job.get('vacancies', 'N/A')}</span>
        </div>
      </div>

      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;overflow:hidden;margin-bottom:24px;">
        <table style="width:100%;border-collapse:collapse;">
          <tbody>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;width:40%;background:#F7F8FA;">Department</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('department', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Total Vacancies</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('vacancies', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Qualification</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('qualification', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Age Limit</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('age_limit', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Salary / Pay Scale</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('salary', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Location</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('state', 'All India')}</td>
            </tr>
            <tr>
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Last Date</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:600;color:#E65100;">{job.get('last_date', 'N/A')}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Rich job content -->
      <div style="margin:24px 0;">
        {build_job_rich_block(job)}
      </div>

      <div style="text-align:center;margin:32px 0;">
        <a href="{job.get('apply_link') or job.get('source_url') or '#'}" target="_blank" rel="nofollow noopener"
           style="background:#FF6B00;color:#fff;padding:14px 40px;border-radius:10px;font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;text-decoration:none;display:inline-block;">
          Apply Online →
        </a>
        <p style="margin-top:10px;font-size:0.78rem;color:#9BA3B8;">You will be redirected to the official website</p>
      </div>

      <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_MID}" data-ad-format="auto"></ins>

      <!-- Coaching Affiliate Banners -->
      <div style="margin:28px 0;">
        <p style="font-size:0.75rem;font-weight:700;color:#9BA3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px;">📚 Prepare for this exam</p>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;">
          <a href="https://unacademy.com/?referral=NAUKRIBULLETIN" target="_blank" rel="noopener sponsored"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #08bd80;">
            <div style="width:40px;height:40px;border-radius:8px;background:#08bd80;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">UN</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Unacademy — Live Classes</div>
              <div style="font-size:0.74rem;color:#6b7280;">SSC, Railway, Banking &amp; State Exams</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#08bd80;color:#fff;white-space:nowrap;">Free</span>
          </a>
          <a href="https://testbook-books.myshopify.com?ref=naukri_bulletin" target="_blank" rel="noopener sponsored"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #1d4ed8;">
            <div style="width:40px;height:40px;border-radius:8px;background:#1d4ed8;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">TB</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Testbook — Mock Tests</div>
              <div style="font-size:0.74rem;color:#6b7280;">10,000+ tests · Hindi &amp; English</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#1d4ed8;color:#fff;white-space:nowrap;">Free</span>
          </a>
          <a href="https://www.adda247.com/?utm_source=naukribulletin&utm_medium=affiliate" target="_blank" rel="noopener sponsored"
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

      <div style="background:#FFF3E8;border-left:4px solid #FF6B00;border-radius:0 8px 8px 0;padding:14px 18px;margin-top:24px;">
        <p style="font-size:0.8rem;color:#4A5270;">⚠️ <strong>Disclaimer:</strong> Always verify details from the official website before applying. NaukriBulletin is not responsible for any errors in the notification details.</p>
      </div>
      <p style="font-size:0.75rem;color:#9BA3B8;margin-top:12px;">Last updated: {today}</p>
    </article>
  </main>

  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
<script>
(function() {{
  var btn = document.getElementById('navHamburger');
  var links = document.querySelector('nav ul');
  if (!btn || !links) return;

  var overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  function closeMenu() {{
    btn.classList.remove('active');
    links.classList.remove('mobile-open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }}
  function openMenu() {{
    btn.classList.add('active');
    links.classList.add('mobile-open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }}
  btn.addEventListener('click', function() {{
    links.classList.contains('mobile-open') ? closeMenu() : openMenu();
  }});
  overlay.addEventListener('click', closeMenu);
  links.querySelectorAll('a').forEach(function(a) {{
    a.addEventListener('click', closeMenu);
  }});
}})();
</script>
<script src="/js/naukribot.js" defer></script>
</body>
</html>"""
    return slug, html


def generate_affairs_html(affair):
    slug       = affair.get("slug") or make_slug(affair.get("title", "news"))
    today      = datetime.now().strftime("%d %B %Y")
    title      = affair.get("title", "Current Affairs")
    summary    = affair.get("summary", "")
    key_facts  = affair.get("key_facts", [])
    dept       = affair.get("dept", "")
    category   = affair.get("category", "current-affairs")

    # Rich content block from content enrichment module
    rich_block = build_ca_rich_block(title, summary)

    # Key facts HTML
    facts_html = "".join(
        f'<li style="padding:6px 0;color:var(--grey-700);border-bottom:1px solid var(--border);font-size:.9rem;">{f}</li>'
        for f in key_facts
    ) if key_facts else ""

    # Standard nav
    nav_html = '''<nav>
  <a href="/" class="logo" style="text-decoration:none;"><span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span></a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/" class="active">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right"><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>'''

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "description": summary[:155],
        "datePublished": datetime.now().strftime("%Y-%m-%d"),
        "author": {"@type": "Organization", "name": "NaukriBulletin Editorial Team"},
        "publisher": {"@type": "Organization", "name": "NaukriBulletin", "url": "https://naukribulletin.in"}
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Current Affairs {today} — NaukriBulletin</title>
  <meta name="description" content="{summary[:155]}">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/{slug}/">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{summary[:155]}">
  <meta name="robots" content="index,follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/css/style.css">
  <script type="application/ld+json">{schema}</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
{nav_html}
<header style="background:var(--navy);border-bottom:1px solid var(--border);padding:36px 20px 28px;">
  <div style="max-width:900px;margin:0 auto;">
    <div style="font-size:.78rem;color:var(--grey-400);margin-bottom:10px;">
      <a href="/" style="color:var(--grey-400);">Home</a> ›
      <a href="/current-affairs/" style="color:var(--grey-400);">Current Affairs</a> ›
      {title[:50]}
    </div>
    <div style="font-size:.72rem;font-weight:700;color:var(--saffron);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">CURRENT AFFAIRS · {today}</div>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.7rem;color:var(--white);margin:0 0 10px;line-height:1.3;">{title}</h1>
    <p style="color:var(--grey-700);font-size:.92rem;margin:0;">By <strong style="color:var(--white);">NaukriBulletin Editorial Team</strong> · Updated {today}</p>
  </div>
</header>
<main style="max-width:900px;margin:0 auto;padding:28px 20px;">
  {rich_block}
  {'<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:20px;"><h3 style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0 0 12px;">Key Points</h3><ul style="margin:0;padding-left:18px;">' + facts_html + '</ul></div>' if facts_html else ''}
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:20px;margin-top:24px;">
    <h3 style="font-family:'Syne',sans-serif;font-size:.95rem;color:var(--white);margin:0 0 12px;">Practice for the exam</h3>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <a href="/daily-quiz/" style="background:var(--saffron);color:#fff;padding:9px 18px;border-radius:9px;font-weight:700;text-decoration:none;font-size:.88rem;">📝 Take Daily Quiz</a>
      <a href="/mock-test/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:9px 18px;border-radius:9px;font-weight:600;text-decoration:none;font-size:.88rem;">Practice Mock Test</a>
      <a href="/current-affairs/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:9px 18px;border-radius:9px;font-weight:600;text-decoration:none;font-size:.88rem;">More Current Affairs</a>
    </div>
  </div>
</main>
<footer style="border-top:1px solid var(--border);background:var(--navy);padding:24px 0;margin-top:32px;">
  <div style="max-width:900px;margin:0 auto;padding:0 20px;color:var(--grey-400);font-size:.85rem;display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;">
    <span>© {datetime.now().year} NaukriBulletin</span>
    <span><a href="/" style="color:var(--grey-700);">Home</a> · <a href="/current-affairs/" style="color:var(--grey-700);">Current Affairs</a> · <a href="/daily-quiz/" style="color:var(--grey-700);">Daily Quiz</a></span>
  </div>
</footer>
<script>(function(){{var b=document.getElementById("navHamburger");var u=document.querySelector("nav ul");if(!b||!u)return;b.addEventListener("click",function(){{u.classList.toggle("mobile-open");b.classList.toggle("active");}});u.querySelectorAll("a").forEach(function(a){{a.addEventListener("click",function(){{u.classList.remove("mobile-open");b.classList.remove("active");}});}});}})();</script>
<script src="/js/naukribot.js" defer></script>
</body>
</html>"""
    return slug, html


def save_page(slug, html, folder):
    page_dir = SITE_ROOT / folder / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    with open(page_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [SAVED] /{folder}/{slug}/")
    return str(page_dir / "index.html")


def git_push(message="Auto: Update"):
    try:
        subprocess.run(["git", "add", "."], cwd=SITE_ROOT, check=True)
        # Commit first (may fail if nothing to commit — that's fine)
        subprocess.run(["git", "commit", "-m", message], cwd=SITE_ROOT, check=False)
        # Pull with rebase to avoid conflicts with parallel runs
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=SITE_ROOT, check=False)
        subprocess.run(["git", "push"], cwd=SITE_ROOT, check=True)
        print(f"[GIT] Pushed: {message}")
    except subprocess.CalledProcessError as e:
        print(f"[GIT] Push failed (maybe nothing to commit): {e}")


# ─── MAIN RUNNER ──────────────────────────────────────────────────────────────

def run():
    run_label = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    print(f"\n{'='*60}")
    print(f"NaukriBulletin — {run_label}")
    print(f"Sources: {len(SOURCES)} | Phase 1 upgraded scraper")
    print(f"{'='*60}\n")

    processed     = load_processed()
    new_pages     = 0
    failed_src    = []
    collected_jobs = []

    # Sort by priority (1 = highest) so most important sources process first
    # Track titles seen this run to avoid near-duplicate pages across sources
    seen_titles_this_run = set()

    for source in sorted(SOURCES, key=lambda s: s.get("priority", 9)):
        dept = source["dept"]
        url  = source["url"]
        print(f"\n[FETCH] {dept}")
        print(f"  URL: {url}")

        if source["type"] == "rss":
            items = scrape_rss(url, dept, fallback_url=source.get("fallback_url"))
        else:
            selector = source.get("selector")
            items = scrape_html_smart(url, dept, selector=selector)

        if not items:
            print(f"  ⚠ No items fetched — source may be down")
            failed_src.append(dept)
            continue

        print(f"  ✓ Got {len(items)} items")

        for item in items:
            # Carry state hint from source config into item
            if source.get("state"):
                item["state"] = source["state"]

            item_hash = make_hash(item.get("title", "") + item.get("description", "")[:100])
            if item_hash in processed:
                continue

            # Skip thin/generic nav titles — these create low-quality pages
            _raw_title = item.get("title", "").strip()
            _SKIP_TITLES = {
                "active examinations", "forthcoming examinations", "recruitment advertisements",
                "recruitment tests", "recruitment requisition", "online recruitment application",
                "online application submission", "revised syllabus and scheme", "syllabus and scheme",
                "examination rules", "recruitment methods", "examination schedule",
                "scheme of examination", "direct recruitment", "status of applications",
                "admit cards", "admit cards/call letters", "written/screening test results",
                "interview schedule", "tentative interview dates", "tentative exam calendar",
                "proposed examination dates", "marks of recommended candidates",
                "marks of all interviewed candidates", "status of recruitment cases",
                "recruitment cases kept on hold", "status of lateral recruitment cases",
                "contact us", "home", "apply online", "online application", "click here",
                "download advertisement", "selection procedure", "instructions for written exam",
                "vacancy dashboard", "bed occupancy/vacancy dashboard profile",
                "apply under mimp scheme", "current vacancies", "archived vacancies",
                "notice of exam and circulars", "combined examination",
                "all oms related to combined exam", "section a indicative syllabus",
                "section-b indicative syllabus", "new examination and interview scheme",
                "list of chairpersons", "computer based recruitment test (cbrt)",
                "otr/apply online (recruitment portal)", "instructions / interview letter",
                "previous question papers", "results previous question papers syllabus archive",
                "transfer/postings", "recruitment support :",
            }
            if _raw_title.lower().strip() in _SKIP_TITLES:
                continue
            # Skip very short titles (likely nav links)
            if len(_raw_title) < 15:
                continue
            # Skip titles that are phone numbers, times, salary ranges
            if re.match(r'^[\d\s\-\+\:\.]+$', _raw_title):
                continue
            if re.match(r'^\d{2}:\d{2}', _raw_title):
                continue

            # Skip near-duplicate titles seen in this run (across different sources)
            title_key = re.sub(r"\s+", " ", item.get("title", "").lower().strip())[:80]
            if title_key in seen_titles_this_run:
                continue
            seen_titles_this_run.add(title_key)

            content_type = source.get("content_type", "job")
            print(f"  → Processing: {item.get('title', '')[:70]}")
            time.sleep(0.6)  # be polite to AI APIs

            formatted = format_with_ai(item, content_type)
            if not formatted:
                print("  ✗ AI formatting failed, skipping")
                continue

            if content_type == "job":
                jobs = [formatted] if isinstance(formatted, dict) else formatted
                for job in jobs:
                    if not job.get("is_job_notification", True):
                        continue
                    # Preserve state from source if AI returned N/A
                    if source.get("state") and job.get("state") in ("N/A", "All India", ""):
                        job["state"] = source["state"]
                    slug, html = generate_job_html(job)
                    if is_valid_slug(slug, item.get("title","")):
                        save_page(slug, html, "jobs")
                    else:
                        print(f"  [SKIP] Invalid slug: {slug}")
                    new_pages += 1
                    # Collect for JSON export (notify.py needs this)
                    job["id"]   = job.get("id") or slug
                    job["slug"] = slug
                    job["url"]  = f"{SITE_URL}/jobs/{slug}/"
                    collected_jobs.append(job)
            else:
                affairs = formatted if isinstance(formatted, list) else [formatted]
                for affair in affairs:
                    slug, html = generate_affairs_html(affair)
                    if is_valid_slug(slug, item.get("title","")):
                        save_page(slug, html, "current-affairs")
                    else:
                        print(f"  [SKIP] Invalid slug: {slug}")
                    new_pages += 1

            processed.add(item_hash)

    save_processed(processed)

    print(f"\n{'='*60}")
    print(f"✅ Done — {new_pages} new pages generated")
    if failed_src:
        print(f"⚠  Failed sources ({len(failed_src)}): {', '.join(failed_src)}")
    print(f"{'='*60}\n")

    rebuild_homepage()
    rebuild_jobs_listing()
    rebuild_affairs_listing()
    rebuild_syllabus()
    rebuild_states()

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sitemap_gen", SITE_ROOT / "scripts" / "sitemap_gen.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run()
    except Exception as e:
        print(f"[SITEMAP] Error: {e}")

    today_str = date.today().strftime("%d %b %Y")
    if collected_jobs:
        export_jobs_json(collected_jobs)

    if new_pages > 0:
        git_push(f"Auto: {new_pages} new pages — {today_str}")
    else:
        git_push(f"Auto: Refresh listings — {today_str}")


# ─── LISTING REBUILDERS ───────────────────────────────────────────────────────
# (kept identical to original — only listing logic, no scraper changes needed)

def get_job_meta_from_html(html_path):
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        dept_tag = soup.find(style=lambda s: s and "letter-spacing" in s and "FF6B00" in s)
        dept = dept_tag.get_text(strip=True).title() if dept_tag else ""

        rows = soup.find_all("tr")
        data = {}
        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 2:
                data[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)

        slug         = html_path.parent.name
        last_date    = data.get("last date", "N/A")
        vacancies    = data.get("total vacancies", "N/A")
        salary       = data.get("salary / pay scale", "N/A")
        location     = data.get("location", "All India")
        qualification = data.get("qualification", "N/A")

        qual_lower = qualification.lower()
        if any(x in qual_lower for x in ["engineer", "b.tech", "b.e"]):
            category, cat_key = "Engineering", "engineering"
        elif any(x in qual_lower for x in ["post graduate", "master", "mba"]):
            category, cat_key = "Post Graduate", "state"
        elif any(x in qual_lower for x in ["graduate", "degree", "b.sc", "b.com", "ba"]):
            category, cat_key = "Graduate", "graduate"
        elif any(x in qual_lower for x in ["12th", "intermediate", "hsc"]):
            category, cat_key = "12th Pass", "12th"
        elif any(x in qual_lower for x in ["10th", "matriculation"]):
            category, cat_key = "10th Pass", "10th"
        else:
            category, cat_key = "Graduate", "graduate"

        td = (title + " " + dept).lower()
        if any(x in td for x in ["ssc", "cgl", "chsl", "mts", "gd constable"]):
            tab_cat = "ssc"
        elif any(x in td for x in ["railway", "rrb", "ntpc", "group d", "loco"]):
            tab_cat = "railway"
        elif any(x in td for x in ["bank", "sbi", "ibps", "rbi", "nabard"]):
            tab_cat = "banking"
        elif any(x in td for x in ["upsc", "ias", "ips", "civil service", "nda", "cds"]):
            tab_cat = "upsc"
        elif any(x in td for x in ["army", "navy", "air force", "defence", "agniveer"]):
            tab_cat = "defence"
        elif any(x in td for x in ["police", "constable", "crpf", "bsf", "cisf"]):
            tab_cat = "police"
        elif any(x in td for x in ["teacher", "professor", "lecturer", "kvs", "nvs"]):
            tab_cat = "teaching"
        else:
            tab_cat = "state"

        emoji_map = {
            "ssc": "📋", "railway": "🚂", "banking": "🏦", "upsc": "🏛️",
            "defence": "🪖", "police": "👮", "teaching": "📚", "state": "🏢",
        }
        return {
            "slug": slug, "title": title, "dept": dept, "last_date": last_date,
            "vacancies": vacancies, "salary": salary, "location": location,
            "category": category, "tab_cat": tab_cat, "emoji": emoji_map.get(tab_cat, "📋"),
        }
    except Exception as e:
        print(f"[META] Error reading {html_path}: {e}")
        return None


def build_job_card(job):
    urgency_badge = ""
    ld = job.get("last_date", "N/A")
    if ld != "N/A":
        try:
            for fmt in ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    days_left = (datetime.strptime(ld, fmt).date() - date.today()).days
                    urgency_badge = '<span class="badge badge-urgent">🔥 URGENT</span>' if days_left <= 7 else '<span class="badge badge-new">🟢 NEW</span>'
                    break
                except ValueError:
                    continue
        except Exception:
            pass
    if not urgency_badge:
        urgency_badge = '<span class="badge badge-new">🟢 NEW</span>'

    return f"""
      <a href="/jobs/{job['slug']}/" class="card fade-up" style="text-decoration:none;color:inherit;display:block;position:relative;overflow:hidden;" data-category="{job['tab_cat']}">
        <div style="position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--saffron);"></div>
        <div style="padding-left:12px;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
            <div style="display:flex;gap:10px;align-items:flex-start;flex:1;">
              <div style="width:42px;height:42px;border-radius:10px;background:var(--saffron-pale);display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">{job['emoji']}</div>
              <div>
                <div style="font-size:0.72rem;color:var(--grey-400);font-weight:500;margin-bottom:2px;">{job['dept']}</div>
                <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--white);">{job['title']}</div>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0;">
              {urgency_badge}
              <span class="badge badge-category">{job['category']}</span>
            </div>
          </div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;">
            <span style="font-size:0.8rem;color:var(--grey-700);">👥 {job['vacancies']}</span>
            <span style="font-size:0.8rem;color:var(--grey-700);">📍 {job['location']}</span>
            <span style="font-size:0.8rem;color:var(--grey-700);">💰 {job['salary']}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--grey-200);">
            <span style="font-size:0.8rem;color:#E65100;font-weight:600;">⏰ Last Date: {job['last_date']}</span>
            <div style="display:flex;gap:8px;align-items:center;">
              <span style="background:var(--navy);color:var(--white);padding:5px 14px;border-radius:6px;font-size:0.78rem;font-weight:600;">Apply Now →</span>
              <button class="nb-save-btn" data-save-slug="{job['slug']}" data-save-title="{job['title'][:50]}" data-save-dept="{job['dept']}" data-save-ld="{job['last_date']}" data-save-emoji="{job['emoji']}" onclick="nbToggleSave(this)" style="background:transparent;border:1px solid var(--border);color:var(--grey-400);width:28px;height:28px;border-radius:6px;cursor:pointer;font-size:.85rem;flex-shrink:0;padding:0;" title="Save job">＋</button>
            </div>
          </div>
        </div>
      </a>"""




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
    tab_buttons = '\n          '.join(
        f'<button class="stab{" stab-active" if i==0 else ""}" '
        f'onclick="filterSyllabus(\'{c[0]}\',this)">{c[2]} {c[1]}</button>'
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
                 color:inherit;transition:background .1s;" onmouseover="this.style.background=\'#fffbf5\'"
                 onmouseout="this.style.background=\'\'" >
                <div style="flex:1;min-width:0;">
                  <div style="font-size:0.88rem;font-weight:600;color:var(--white);
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
                   color:var(--white);">{cfg[1]} Syllabus {yr}</div>
              <div style="font-size:0.75rem;color:var(--grey-400);">{len(jobs)} active notifications</div>
            </div>
          </div>
          <div style="background:var(--card-bg);border-radius:12px;border:1.5px solid var(--border);
               overflow:hidden;">
            {rows}
            <div style="padding:10px 16px;background:var(--navy-soft);text-align:center;">
              <a href="/jobs/{cat_key}/" style="font-size:0.8rem;color:var(--saffron);
                 font-weight:600;text-decoration:none;">View all {cfg[1]} jobs →</a>
            </div>
          </div>
        </div>"""

    sections_html = "\n".join(make_section(c[0]) for c in CATS)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exam Syllabus {yr} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="Complete exam syllabus {yr} for SSC CGL, CHSL, Railway NTPC, SBI PO, UPSC, IBPS and 200+ govt exams. Updated daily at NaukriBulletin.in">
  <link rel="canonical" href="https://naukribulletin.in/syllabus/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap">
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
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>

  <nav>
  <a href="/" class="logo" style="text-decoration:none;">
    <span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span>
  </a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right">
    <a href="/alerts/" class="nav-cta">🔔 Get Alerts</a>
  </div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
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
        <button class="stab stab-active" onclick="filterSyllabus(\'all\',this)">🗂 All Exams</button>
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
<script>
(function() {{
  var btn = document.getElementById('navHamburger');
  var links = document.querySelector('nav ul');
  if (!btn || !links) return;

  var overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  function closeMenu() {{
    btn.classList.remove('active');
    links.classList.remove('mobile-open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }}
  function openMenu() {{
    btn.classList.add('active');
    links.classList.add('mobile-open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }}
  btn.addEventListener('click', function() {{
    links.classList.contains('mobile-open') ? closeMenu() : openMenu();
  }});
  overlay.addEventListener('click', closeMenu);
  links.querySelectorAll('a').forEach(function(a) {{
    a.addEventListener('click', closeMenu);
  }});
}})();
</script>
<script src="/js/naukribot.js" defer></script>
</body>
</html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[SYLLABUS] ✅ Written syllabus/index.html ({total} jobs, {len(CATS)} categories)")




# ─── STATE HUB BUILDER ────────────────────────────────────────────────────────
STATES = [
    # ── 28 STATES ──────────────────────────────────────────────────────────
    ("andhra-pradesh",    "Andhra Pradesh",       "🌶️",  ["appsc","andhra pradesh","ap psc","ap police","vijayawada","amaravati"]),
    ("arunachal-pradesh", "Arunachal Pradesh",    "🏔️",  ["appsc arunachal","arunachal pradesh","itanagar"]),
    ("assam",             "Assam",                "🦏",  ["apsc","slprb","assam police","assam","guwahati","dispur"]),
    ("bihar",             "Bihar",                "🎋",  ["bpsc","bssc","bihar police","bihar","patna"]),
    ("chhattisgarh",      "Chhattisgarh",         "🌿",  ["cgpsc","cgvyapam","chhattisgarh","raipur","bilaspur"]),
    ("goa",               "Goa",                  "🏖️",  ["gpsc goa","goa psc","goa","panaji","margao"]),
    ("gujarat",           "Gujarat",              "🦋",  ["gpsc","gssb","gsrtc","gujarat","ahmedabad","gandhinagar"]),
    ("haryana",           "Haryana",              "🚜",  ["hpsc","hssc","haryana police","haryana","chandigarh","gurugram"]),
    ("himachal-pradesh",  "Himachal Pradesh",     "🏔️",  ["hppsc","himachal pradesh","shimla","dharamsala"]),
    ("jharkhand",         "Jharkhand",            "⛏️",  ["jpsc","jssc","jharkhand","ranchi","jamshedpur"]),
    ("karnataka",         "Karnataka",            "🦁",  ["kpsc","kea","karnataka","bengaluru","bangalore","mysuru"]),
    ("kerala",            "Kerala",               "🌴",  ["kerala psc","kerala psc","kerala","thiruvananthapuram","kochi","kozhikode"]),
    ("madhya-pradesh",    "Madhya Pradesh",       "🐆",  ["mppsc","mp police","mp vyapam","mpesb","madhya pradesh","bhopal","indore"]),
    ("maharashtra",       "Maharashtra",          "🏙️",  ["mpsc","mahapariksha","maharashtra","mumbai","pune","nagpur"]),
    ("manipur",           "Manipur",              "🎭",  ["manipur psc","mpsc manipur","manipur","imphal"]),
    ("meghalaya",         "Meghalaya",            "☁️",  ["mpsc meghalaya","meghalaya","shillong"]),
    ("mizoram",           "Mizoram",              "🌄",  ["mpsc mizoram","mizoram","aizawl"]),
    ("nagaland",          "Nagaland",             "🦅",  ["npsc","nagaland","kohima","dimapur"]),
    ("odisha",            "Odisha",               "🏛️",  ["opsc","ossc","osssc","odisha","bhubaneswar","cuttack"]),
    ("punjab",            "Punjab",               "🌾",  ["ppsc","psssb","punjab police","punjab","chandigarh","ludhiana","amritsar"]),
    ("rajasthan",         "Rajasthan",            "🏜️",  ["rpsc","rsmssb","rajasthan police","rajasthan","jaipur","jodhpur"]),
    ("sikkim",            "Sikkim",               "🏔️",  ["spsc","sikkim psc","sikkim","gangtok"]),
    ("tamil-nadu",        "Tamil Nadu",           "🌊",  ["tnpsc","tnusrb","tntrb","tamil nadu","chennai","coimbatore","madurai"]),
    ("telangana",         "Telangana",            "🌆",  ["tspsc","tgpsc","ts police","telangana","hyderabad","warangal"]),
    ("tripura",           "Tripura",              "🌿",  ["tpsc","tripura psc","tripura","agartala"]),
    ("uttar-pradesh",     "Uttar Pradesh",        "🏛️",  ["uppsc","upsssc","up police","up board","uttar pradesh","lucknow","kanpur","agra","varanasi"]),
    ("uttarakhand",       "Uttarakhand",          "🏔️",  ["ukpsc","uksssc","uttarakhand","dehradun","haridwar","roorkee"]),
    ("west-bengal",       "West Bengal",          "🐯",  ["wbpsc","wbssc","wb police","west bengal","kolkata","howrah","darjeeling"]),
    # ── 8 UNION TERRITORIES ────────────────────────────────────────────────
    ("andaman-nicobar",   "Andaman & Nicobar",    "🏝️",  ["andaman nicobar","andaman","port blair"]),
    ("chandigarh",        "Chandigarh",           "🌹",  ["chandigarh administration","chandigarh ut","chandigarh police"]),
    ("dadra-nagar-haveli","Dadra & Nagar Haveli", "🌿",  ["dadra nagar haveli","dnh","silvassa"]),
    ("daman-diu",         "Daman & Diu",          "⛵",  ["daman and diu","daman & diu","daman diu"]),
    ("delhi",             "Delhi",                "🏛️",  ["dsssb","delhi police","delhi government","new delhi","delhi"]),
    ("jammu-kashmir",     "Jammu & Kashmir",      "❄️",  ["jkpsc","jkssb","jkpsc","jammu kashmir","srinagar","jammu"]),
    ("ladakh",            "Ladakh",               "🏔️",  ["lahdc","ladakh","leh","kargil"]),
    ("lakshadweep",       "Lakshadweep",          "🐠",  ["lakshadweep","kavaratti"]),
    ("puducherry",        "Puducherry",           "🌺",  ["puducherry psc","pondicherry","puducherry"]),
]

def _state_matches(text, keywords):
    t = text.lower()
    return any(k in t for k in keywords)

def rebuild_states():
    """Build one hub page per state + inject state grid into homepage."""
    from datetime import datetime
    import re

    yr = datetime.now().year
    jobs_dir    = SITE_ROOT / "jobs"
    results_dir = SITE_ROOT / "results"
    admit_dir   = SITE_ROOT / "admit-card"
    answer_dir  = SITE_ROOT / "answer-key"

    NAV = """<nav>
  <a href="/" class="logo" style="text-decoration:none;"><span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span></a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right"><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>"""

    state_cards_for_homepage = []
    state_counts = {}

    for slug, name, emoji, keywords in STATES:
        state_dir = SITE_ROOT / "jobs" / slug
        state_dir.mkdir(parents=True, exist_ok=True)

        # ── Collect matching jobs ──────────────────────────────────────────
        matching_jobs = []
        for d in sorted(jobs_dir.iterdir(), reverse=True):
            if not d.is_dir(): continue
            idx = d / "index.html"
            if not idx.exists(): continue
            try:
                content = idx.read_text(errors="ignore")
                title_m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.S)
                title = re.sub(r"<[^>]+>","",title_m.group(1)).strip() if title_m else d.name
                if _state_matches(d.name + " " + title + content[:1000], keywords):
                    meta = get_job_meta_from_html(idx) or {}
                    meta["title"] = meta.get("title") or title
                    meta["slug"]  = meta.get("slug")  or d.name
                    matching_jobs.append(meta)
            except Exception: pass

        # ── Collect matching results / admit cards / answer keys ───────────
        def collect_updates(folder, kind_label):
            items = []
            if not folder.exists(): return items
            for d in sorted(folder.iterdir(), reverse=True):
                if not d.is_dir(): continue
                idx = d / "index.html"
                if not idx.exists(): continue
                try:
                    content = idx.read_text(errors="ignore")
                    title_m = re.search(r"<h1[^>]*>(.*?)</h1>",content,re.S)
                    title = re.sub(r"<[^>]+>","",title_m.group(1)).strip() if title_m else d.name
                    if _state_matches(d.name+" "+title, keywords):
                        items.append({"title":title,"slug":d.name,"kind":kind_label})
                except Exception: pass
            return items[:10]

        results_items  = collect_updates(results_dir,  "Result")
        admit_items    = collect_updates(admit_dir,    "Admit Card")
        answer_items   = collect_updates(answer_dir,   "Answer Key")
        updates = results_items + admit_items + answer_items

        state_counts[slug] = len(matching_jobs)
        state_cards_for_homepage.append((slug, name, emoji, len(matching_jobs)))

        # ── Build job rows ─────────────────────────────────────────────────
        def job_row(j):
            title = j.get("title","")[:70]
            vac   = j.get("vacancies","N/A")
            ld    = j.get("last_date","N/A") or "N/A"
            slug_ = j.get("slug","")
            hover_on  = "this.style.background='var(--navy-soft)'"
            hover_off = "this.style.background=''"
            return (f'<a href="/jobs/{slug_}/" style="display:flex;align-items:center;justify-content:space-between;'
                    f'gap:12px;padding:13px 16px;border-bottom:1px solid var(--border);text-decoration:none;'
                    f'color:var(--white);font-size:.9rem;transition:background .15s;" '
                    f'onmouseover="{hover_on}" onmouseout="{hover_off}">'
                    f'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600;">{title}</span>'
                    f'<span style="color:var(--grey-400);font-size:.78rem;white-space:nowrap;flex-shrink:0;">👥 {vac}</span>'
                    f'<span style="color:var(--saffron);font-size:.78rem;white-space:nowrap;flex-shrink:0;margin-left:10px;">⏰ {ld}</span>'
                    f'<span style="background:var(--saffron);color:#fff;padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700;margin-left:10px;flex-shrink:0;">Apply →</span>'
                    f'</a>')

        def update_row(u):
            kind_colour = {"Result":"#63FFDA","Admit Card":"#FFD56C","Answer Key":"#FF8C33"}.get(u["kind"],"#B8BACD")
            folder_map  = {"Result":"results","Admit Card":"admit-card","Answer Key":"answer-key"}
            href = f'/{folder_map[u["kind"]]}/{u["slug"]}/'
            hover_on  = "this.style.background='var(--navy-soft)'"
            hover_off = "this.style.background=''"
            return (f'<a href="{href}" style="display:flex;align-items:center;gap:12px;padding:12px 16px;'
                    f'border-bottom:1px solid var(--border);text-decoration:none;color:var(--white);'
                    f'font-size:.88rem;transition:background .15s;" '
                    f'onmouseover="{hover_on}" onmouseout="{hover_off}">'
                    f'<span style="background:{kind_colour}22;color:{kind_colour};padding:3px 9px;border-radius:20px;font-size:.72rem;font-weight:700;flex-shrink:0;">{u["kind"]}</span>'
                    f'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{u["title"][:65]}</span>'
                    f'</a>')

        jobs_html    = "".join(job_row(j) for j in matching_jobs[:40]) or                        f'<div style="padding:20px;color:var(--grey-400);text-align:center;">No {name} jobs found yet — check back daily.</div>'
        updates_html = "".join(update_row(u) for u in updates) or                        f'<div style="padding:16px;color:var(--grey-400);font-size:.88rem;">Results/admit cards appear here as they are released.</div>'

        job_count_text = f"{len(matching_jobs)} active notifications" if matching_jobs else "Updated daily"
        faq_ld = [
            {"@type":"Question","name":f"Latest {name} government jobs 2026?",
             "acceptedAnswer":{"@type":"Answer","text":f"NaukriBulletin tracks all {name} government jobs from {name} PSC and state departments, updated daily. Check this page for the latest notifications."}},
            {"@type":"Question","name":f"How to get {name} job alerts?",
             "acceptedAnswer":{"@type":"Answer","text":"Subscribe to NaukriBulletin's free alert service to get instant Telegram, WhatsApp and push notifications for new job postings."}},
        ]
        import json as _json
        faq_str = _json.dumps(faq_ld)

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} Government Jobs {yr} — Results, Admit Cards & Notifications | NaukriBulletin</title>
  <meta name="description" content="All {name} government jobs {yr} — PSC notifications, recruitment results, admit cards and answer keys. Updated daily. {job_count_text}.">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:title" content="{name} Govt Jobs {yr} | NaukriBulletin">
  <meta property="og:url" content="https://naukribulletin.in/jobs/{slug}/">
  <meta name="robots" content="index,follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/css/style.css">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@graph":[
  {{"@type":"BreadcrumbList","itemListElement":[
    {{"@type":"ListItem","position":1,"name":"Home","item":"https://naukribulletin.in/"}},
    {{"@type":"ListItem","position":2,"name":"Jobs","item":"https://naukribulletin.in/jobs/"}},
    {{"@type":"ListItem","position":3,"name":"{name} Jobs","item":"https://naukribulletin.in/jobs/{slug}/"}}]}},
  {{"@type":"FAQPage","mainEntity":{faq_str}}}
  ]}}
  </script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
{NAV}
<header style="background:var(--navy);border-bottom:1px solid var(--border);padding:36px 20px 28px;">
  <div style="max-width:1100px;margin:0 auto;">
    <div style="font-size:.78rem;color:var(--grey-400);margin-bottom:10px;">
      <a href="/" style="color:var(--grey-400);">Home</a> › <a href="/jobs/" style="color:var(--grey-400);">Jobs</a> › {name}
    </div>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.9rem;color:var(--white);margin:0 0 8px;line-height:1.2;">
      {emoji} {name} Government Jobs {yr}
    </h1>
    <p style="color:var(--grey-700);font-size:.97rem;margin:0;">
      {job_count_text} — PSC notifications, state recruitment, results, admit cards &amp; answer keys. Updated daily.
    </p>
  </div>
</header>
<main style="max-width:1100px;margin:0 auto;padding:28px 20px;">
  <div id="state-grid" style="display:grid;grid-template-columns:1fr 340px;gap:24px;">
    <style>@media(max-width:768px){{#state-grid{{grid-template-columns:1fr!important}}}}</style>
    <div>
      <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:24px;">
        <div style="padding:16px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
          <h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0;">Latest {name} Jobs</h2>
          <span style="color:var(--grey-400);font-size:.82rem;">{job_count_text}</span>
        </div>
        {jobs_html}
        <div style="padding:12px 16px;background:var(--navy-soft);text-align:center;">
          <a href="/jobs/" style="color:var(--saffron);font-size:.82rem;font-weight:600;text-decoration:none;">View all government jobs →</a>
        </div>
      </div>
    </div>
    <div>
      <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:18px;">
        <div style="padding:14px 16px;border-bottom:1px solid var(--border);">
          <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">Results, Admit Cards &amp; Answer Keys</h2>
        </div>
        {updates_html}
      </div>
      <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:18px;">
        <h3 style="font-family:'Syne',sans-serif;font-size:.97rem;font-weight:700;color:var(--white);margin:0 0 12px;">Quick links</h3>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <a href="/alerts/" style="background:var(--saffron);color:#fff;padding:10px 14px;border-radius:9px;text-decoration:none;font-weight:700;font-size:.88rem;text-align:center;">🔔 Get free {name} job alerts</a>
          <a href="/mock-test/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:10px 14px;border-radius:9px;text-decoration:none;font-size:.88rem;text-align:center;">📝 Free mock tests</a>
          <a href="/exam-calendar/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:10px 14px;border-radius:9px;text-decoration:none;font-size:.88rem;text-align:center;">📅 Exam calendar</a>
          <a href="/syllabus/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:10px 14px;border-radius:9px;text-decoration:none;font-size:.88rem;text-align:center;">📚 Exam syllabus</a>
        </div>
      </div>
    </div>
  </div>
</main>
<footer style="border-top:1px solid var(--border);background:var(--navy);padding:24px 0;margin-top:20px;">
  <div style="max-width:1100px;margin:0 auto;padding:0 20px;color:var(--grey-400);font-size:.85rem;display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;">
    <span>© {yr} NaukriBulletin</span>
    <span><a href="/" style="color:var(--grey-700);">Home</a> · <a href="/jobs/" style="color:var(--grey-700);">Jobs</a> · <a href="/alerts/" style="color:var(--grey-700);">Alerts</a></span>
  </div>
</footer>
<script>
(function(){{var btn=document.getElementById('navHamburger');var links=document.querySelector('nav ul');if(!btn||!links)return;btn.addEventListener('click',function(){{links.classList.toggle('mobile-open');btn.classList.toggle('active');}});links.querySelectorAll('a').forEach(function(a){{a.addEventListener('click',function(){{links.classList.remove('mobile-open');btn.classList.remove('active');}});}});}})();
</script>
<script src="/js/naukribot.js" defer></script>
</body>
</html>"""
        (state_dir / "index.html").write_text(page, encoding="utf-8")

    print(f"[STATES] ✅ Built {len(STATES)} state hub pages")

    # ── Inject state grid into homepage ───────────────────────────────────────
    homepage = SITE_ROOT / "index.html"
    if not homepage.exists(): return
    html = homepage.read_text(encoding="utf-8")

    grid_cards = ""
    for slug, name, emoji, count in state_cards_for_homepage:
        label = f"{count} jobs" if count > 0 else "updated daily"
        h_on  = "this.style.borderColor='var(--accent)';this.style.background='rgba(255,107,0,0.06)'"
        h_off = "this.style.borderColor='var(--border)';this.style.background='var(--surface)'"
        grid_cards += (
            f'<a href="/jobs/{slug}/" style="background:var(--surface);border:1px solid var(--border);'
            f'border-radius:12px;padding:14px 12px;text-align:center;text-decoration:none;'
            f'color:var(--text);transition:all .2s;display:flex;flex-direction:column;align-items:center;gap:6px;" '
            f'onmouseover="{h_on}" '
            f'onmouseout="{h_off}">'
            f'<span style="font-size:1.5rem;">{emoji}</span>'
            f'<span style="font-family:var(--font-display);font-size:.82rem;font-weight:700;">{name}</span>'
            f'<span style="font-size:.72rem;color:var(--muted);">{label}</span>'
            f'</a>'
        )

    state_section = f"""
<!-- NB-STATES-START -->
<section style="padding:40px 20px;max-width:1200px;margin:0 auto;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h2 style="font-family:var(--font-display);font-size:1.5rem;font-weight:800;margin:0;">
      Jobs by <span style="color:var(--accent);">State</span>
    </h2>
    <a href="/jobs/" style="color:var(--accent);font-size:.87rem;font-weight:600;text-decoration:none;">View all →</a>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;">
    {grid_cards}
  </div>
</section>
<!-- NB-STATES-END -->"""

    if "NB-STATES-START" in html:
        html = re.sub(r"<!-- NB-STATES-START -->.*?<!-- NB-STATES-END -->", state_section.strip(), html, flags=re.S)
    else:
        # Inject after the current-affairs section (before the footer)
        if "</section>" in html:
            # Find last </section> before footer and inject after it
            footer_idx = html.rfind('<footer')
            if footer_idx == -1: footer_idx = len(html) - 200
            last_section = html.rfind('</section>', 0, footer_idx)
            if last_section != -1:
                html = html[:last_section+10] + "\n" + state_section + html[last_section+10:]
    homepage.write_text(html, encoding="utf-8")
    print(f"[STATES] ✅ State grid injected into homepage ({len(STATES)} states)")

# ─── END STATE HUB BUILDER ────────────────────────────────────────────────────



# ─── DAILY QUIZ + FLASHCARDS + JOB NEWS ───────────────────────────────────────

def build_daily_quiz(affairs_list):
    """
    Build 10 MCQ questions from today's current affairs.
    Returns HTML for the quiz section.
    """
    import random
    questions = []
    for a in affairs_list[:20]:
        title   = a.get("title","")
        summary = a.get("summary","")
        slug    = a.get("slug","")
        if not title or len(title) < 15: continue

        # Extract the key fact from the title to form a question
        # Pattern: "X does Y" → "Which body/person did Y?"
        # Use the title as the question stem with one correct + 3 decoy options
        # We generate deterministic decoys from other article titles
        questions.append({"title": title, "summary": summary, "slug": slug})

    if len(questions) < 4: return ""

    # Pick up to 10
    q_set = questions[:10]
    all_titles = [q["title"] for q in questions]

    quiz_items = ""
    for i, q in enumerate(q_set):
        correct = q["title"]
        # 3 decoys: other titles from the same set
        decoys = [t for t in all_titles if t != correct][:3]
        while len(decoys) < 3:
            decoys.append("None of the above")
        opts = [correct] + decoys
        # Shuffle deterministically by index
        seed_order = [(hash(correct + str(j)) % 4) for j in range(4)]
        order = sorted(range(4), key=lambda x: seed_order[x])
        shuffled = [opts[o % len(opts)] for o in order]
        correct_idx = shuffled.index(correct)

        opts_html = "".join(
            f'''<button class="dq-opt" data-idx="{i}" data-val="{j}" data-correct="{correct_idx}" onclick="dqA(this)">
              <span class="dq-letter">{chr(65+j)}</span>
              <span class="dq-text">{shuffled[j][:90]}</span>
            </button>''' for j in range(len(shuffled))
        )
        hint_url = f'/current-affairs/{q["slug"]}/'
        quiz_items += f'''
        <div class="dq-item" id="dq-{i}" style="display:{'block' if i==0 else 'none'}">
          <div class="dq-num">Question {i+1} of {len(q_set)}</div>
          <div class="dq-q">{q["summary"] if q["summary"] else q["title"]}</div>
          <div class="dq-opts">{opts_html}</div>
          <div class="dq-hint" id="dq-hint-{i}" style="display:none">
            📖 <a href="{hint_url}" style="color:var(--saffron);">Read full article →</a>
          </div>
        </div>'''

    return f'''
<!-- NB-QUIZ-START -->
<section style="max-width:1200px;margin:0 auto 0;padding:0 5% 48px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h2 style="font-family:var(--font-display);font-size:1.5rem;font-weight:800;margin:0;">
      📝 Daily <span style="color:var(--accent);">Quiz</span>
    </h2>
    <a href="/current-affairs/" style="color:var(--accent);font-size:.87rem;font-weight:600;text-decoration:none;">More CA →</a>
  </div>
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px;">
    <div id="dq-score-bar" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--border);">
      <span style="font-size:.85rem;color:var(--muted);">Test your knowledge of today's news</span>
      <span style="font-size:.85rem;font-weight:700;color:var(--accent);" id="dq-score">0 / {len(q_set)}</span>
    </div>
    <div id="dq-container">
      {quiz_items}
    </div>
    <div id="dq-result" style="display:none;text-align:center;padding:20px 0;">
      <div style="font-family:var(--font-display);font-size:1.4rem;font-weight:800;color:var(--text);margin-bottom:8px;" id="dq-final-score"></div>
      <div style="color:var(--muted);font-size:.9rem;margin-bottom:16px;" id="dq-final-msg"></div>
      <button onclick="dqRestart()" style="background:var(--accent);color:#fff;border:none;padding:10px 24px;border-radius:10px;font-weight:700;font-size:.95rem;cursor:pointer;">🔄 Retry</button>
      <a href="/current-affairs/" style="display:inline-block;margin-left:12px;background:var(--surface);border:1px solid var(--border);color:var(--text);padding:10px 24px;border-radius:10px;font-weight:600;font-size:.95rem;text-decoration:none;">Read all CA →</a>
    </div>
  </div>
  <style>
    .dq-num{{font-size:.75rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;}}
    .dq-q{{font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--text);line-height:1.5;margin-bottom:18px;}}
    .dq-opts{{display:flex;flex-direction:column;gap:10px;}}
    .dq-opt{{display:flex;align-items:center;gap:12px;background:var(--card-bg);border:1.5px solid var(--border);border-radius:10px;padding:12px 16px;cursor:pointer;text-align:left;transition:.15s;width:100%;}}
    .dq-opt:hover{{border-color:var(--accent);background:rgba(255,107,0,.06);}}
    .dq-opt.correct{{border-color:#63FFDA;background:rgba(99,255,218,.08);pointer-events:none;}}
    .dq-opt.wrong{{border-color:#FF6C8A;background:rgba(255,108,138,.08);pointer-events:none;}}
    .dq-opt.disabled{{pointer-events:none;opacity:.6;}}
    .dq-letter{{width:28px;height:28px;border-radius:50%;background:var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.8rem;flex-shrink:0;}}
    .dq-text{{font-size:.88rem;color:var(--text);line-height:1.4;}}
    .dq-hint{{margin-top:12px;font-size:.82rem;color:var(--muted);}}
  </style>
  <script>
    var dqAnswered=new Array({len(q_set)}).fill(false);
    var dqScore=0;
    var dqTotal={len(q_set)};
    var dqCurrent=0;
    function dqA(btn){{
      var qIdx=+btn.dataset.idx;var val=+btn.dataset.val;var correct=+btn.dataset.correct;
      dqAnswer(qIdx,val,correct,btn);
    }}
    function dqAnswer(qIdx,val,correct,btn){{
      if(dqAnswered[qIdx])return;
      dqAnswered[qIdx]=true;
      var opts=document.querySelectorAll('.dq-opt[data-idx="'+qIdx+'"]');
      opts.forEach(function(o){{o.classList.add('disabled');}});
      if(val===correct){{
        btn.classList.remove('disabled');btn.classList.add('correct');
        dqScore++;document.getElementById('dq-score').textContent=dqScore+' / '+dqTotal;
      }}else{{
        btn.classList.remove('disabled');btn.classList.add('wrong');
        var optArr=Array.from(opts);if(optArr[correct]){{optArr[correct].classList.remove('disabled');optArr[correct].classList.add('correct');}}
      }}
      document.getElementById('dq-hint-'+qIdx).style.display='block';
      setTimeout(function(){{
        dqCurrent++;
        if(dqCurrent<dqTotal){{
          document.getElementById('dq-'+qIdx).style.display='none';
          document.getElementById('dq-'+dqCurrent).style.display='block';
        }}else{{
          document.getElementById('dq-container').style.display='none';
          document.getElementById('dq-result').style.display='block';
          var pct=Math.round(dqScore/dqTotal*100);
          document.getElementById('dq-final-score').textContent='You scored '+dqScore+' out of '+dqTotal;
          document.getElementById('dq-final-msg').textContent=pct>=80?'🎉 Excellent! You're exam-ready.':pct>=50?'👍 Good effort — keep reading current affairs.':'📚 Keep practicing — read today's articles.';
        }}
      }},1200);
    }}
    function dqRestart(){{
      dqAnswered=new Array(dqTotal).fill(false);dqScore=0;dqCurrent=0;
      document.getElementById('dq-score').textContent='0 / '+dqTotal;
      document.getElementById('dq-result').style.display='none';
      document.getElementById('dq-container').style.display='block';
      for(var i=0;i<dqTotal;i++){{
        var el=document.getElementById('dq-'+i);
        if(el)el.style.display=i===0?'block':'none';
        var opts=document.querySelectorAll('.dq-opt[data-idx="'+i+'"]');
        opts.forEach(function(o){{o.classList.remove('correct','wrong','disabled');}});
        var hint=document.getElementById('dq-hint-'+i);
        if(hint)hint.style.display='none';
      }}
    }}
  </script>
</section>
<!-- NB-QUIZ-END -->
'''


def build_flashcards(jobs_list):
    """Build swipeable flash cards for today's top job notifications."""
    if not jobs_list: return ""
    cards = jobs_list[:12]

    card_html = ""
    for j in cards:
        title    = j.get("title","")[:70]
        dept     = j.get("dept","")
        vac      = j.get("vacancies","N/A")
        ld       = j.get("last_date","N/A") or "N/A"
        slug_    = j.get("slug","")
        emoji    = j.get("emoji","📋")
        cat      = j.get("category","Graduate")
        card_html += f'''
      <div class="fc-card">
        <div class="fc-emoji">{emoji}</div>
        <div class="fc-dept">{dept}</div>
        <div class="fc-title">{title}</div>
        <div class="fc-meta">
          <span>👥 {vac}</span>
          <span>⏰ {ld}</span>
          <span style="background:rgba(255,107,0,.15);color:var(--accent);padding:2px 8px;border-radius:20px;font-size:.7rem;">{cat}</span>
        </div>
        <a href="/jobs/{slug_}/" class="fc-apply">Apply Now →</a>
      </div>'''

    return f'''
<!-- NB-FLASHCARDS-START -->
<section style="max-width:1200px;margin:0 auto 0;padding:0 5% 48px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h2 style="font-family:var(--font-display);font-size:1.5rem;font-weight:800;margin:0;">
      ⚡ Job <span style="color:var(--accent);">Flash Cards</span>
    </h2>
    <div style="display:flex;gap:10px;align-items:center;">
      <button onclick="fcPrev()" style="background:var(--surface);border:1px solid var(--border);color:var(--text);width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:1rem;">‹</button>
      <span id="fc-pos" style="font-size:.82rem;color:var(--muted);min-width:40px;text-align:center;">1/{len(cards)}</span>
      <button onclick="fcNext()" style="background:var(--surface);border:1px solid var(--border);color:var(--text);width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:1rem;">›</button>
    </div>
  </div>
  <div id="fc-track-wrap" style="overflow:hidden;border-radius:16px;">
    <div id="fc-track" style="display:flex;gap:16px;transition:transform .3s ease;">
      {card_html}
    </div>
  </div>
  <style>
    .fc-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px;min-width:260px;flex-shrink:0;display:flex;flex-direction:column;gap:10px;}}
    .fc-emoji{{font-size:1.8rem;}}
    .fc-dept{{font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;}}
    .fc-title{{font-family:var(--font-display);font-size:.97rem;font-weight:700;color:var(--text);line-height:1.4;flex:1;}}
    .fc-meta{{display:flex;gap:10px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);align-items:center;}}
    .fc-apply{{background:var(--accent);color:#fff;padding:9px 18px;border-radius:9px;text-decoration:none;font-weight:700;font-size:.85rem;text-align:center;margin-top:4px;}}
    @media(max-width:600px){{.fc-card{{min-width:calc(100vw - 48px)}}}}
  </style>
  <script>
    var fcIdx=0;var fcTotal={len(cards)};
    var fcCardW=276;
    function fcUpdatePos(){{
      var w=document.querySelector('.fc-card');
      if(w)fcCardW=w.offsetWidth+16;
      document.getElementById('fc-track').style.transform='translateX(-'+(fcIdx*fcCardW)+'px)';
      document.getElementById('fc-pos').textContent=(fcIdx+1)+'/'+fcTotal;
    }}
    function fcNext(){{if(fcIdx<fcTotal-1){{fcIdx++;fcUpdatePos();}}}}
    function fcPrev(){{if(fcIdx>0){{fcIdx--;fcUpdatePos();}}}}
    // Touch/swipe support
    (function(){{
      var t=document.getElementById('fc-track-wrap');
      var sx=0;
      t.addEventListener('touchstart',function(e){{sx=e.touches[0].clientX;}},{{passive:true}});
      t.addEventListener('touchend',function(e){{
        var dx=sx-e.changedTouches[0].clientX;
        if(dx>40)fcNext();else if(dx<-40)fcPrev();
      }},{{passive:true}});
    }})();
  </script>
</section>
<!-- NB-FLASHCARDS-END -->
'''


def build_job_news(affairs_list, jobs_list):
    """Build a job news / recruitment news section."""
    # Filter CA for job/recruitment news
    JOB_KW = ["recruitment","vacancy","vacancies","appointment","notification","exam","admit","result",
               "apply","application","selection","post","officer","constable","teacher","grade",
               "naukri","sarkari","hiring","appointed","joins","takes over","takes charge"]

    job_news = []
    for a in affairs_list:
        t = a.get("title","").lower()
        if any(k in t for k in JOB_KW):
            job_news.append(a)
        if len(job_news) >= 8: break

    # Also add recent job notifications as news items
    recent_jobs = jobs_list[:6]

    news_items = ""
    for i, a in enumerate(job_news[:6]):
        news_items += f'''
      <a href="/current-affairs/{a["slug"]}/" style="display:flex;gap:14px;align-items:flex-start;
         padding:14px 0;border-bottom:1px solid var(--border);text-decoration:none;
         color:var(--text);transition:.15s;" onmouseover="this.style.color='var(--accent)'" onmouseout="this.style.color='var(--text)'">
        <span style="background:rgba(255,107,0,.12);color:var(--accent);border-radius:8px;
              padding:6px 10px;font-size:1.1rem;flex-shrink:0;">📢</span>
        <div>
          <div style="font-weight:600;font-size:.9rem;line-height:1.4;margin-bottom:4px;">{a["title"][:80]}</div>
          <div style="font-size:.78rem;color:var(--muted);">{a["summary"][:100]}</div>
        </div>
      </a>'''

    jobs_col = ""
    for j in recent_jobs:
        urgency_colour = "#FF6C8A" if j.get("last_date","N/A") != "N/A" else "var(--muted)"
        jobs_col += f'''
      <a href="/jobs/{j["slug"]}/" style="display:flex;gap:12px;align-items:center;
         padding:12px 0;border-bottom:1px solid var(--border);text-decoration:none;color:var(--text);">
        <span style="font-size:1.2rem;flex-shrink:0;">{j.get("emoji","📋")}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{j.get("title","")[:55]}</div>
          <div style="font-size:.75rem;color:var(--muted);">{j.get("dept","")} · ⏰ {j.get("last_date","N/A")}</div>
        </div>
        <span style="background:rgba(255,107,0,.12);color:var(--accent);padding:3px 9px;border-radius:20px;font-size:.72rem;font-weight:700;flex-shrink:0;">New</span>
      </a>'''

    if not news_items and not jobs_col: return ""

    return f'''
<!-- NB-JOBNEWS-START -->
<section style="max-width:1200px;margin:0 auto 0;padding:0 5% 56px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h2 style="font-family:var(--font-display);font-size:1.5rem;font-weight:800;margin:0;">
      🗞️ Job <span style="color:var(--accent);">News</span>
    </h2>
    <a href="/current-affairs/" style="color:var(--accent);font-size:.87rem;font-weight:600;text-decoration:none;">All news →</a>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px;">
      <div style="font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px;">Recruitment news</div>
      {news_items or '<div style="color:var(--muted);font-size:.88rem;padding:12px 0;">No recruitment news today — check back tomorrow.</div>'}
      <a href="/current-affairs/" style="display:block;text-align:center;color:var(--accent);font-size:.82rem;font-weight:600;margin-top:14px;text-decoration:none;">Read all current affairs →</a>
    </div>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px;">
      <div style="font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px;">Latest notifications</div>
      {jobs_col or '<div style="color:var(--muted);font-size:.88rem;padding:12px 0;">No new jobs today.</div>'}
      <a href="/jobs/" style="display:block;text-align:center;color:var(--accent);font-size:.82rem;font-weight:600;margin-top:14px;text-decoration:none;">Browse all jobs →</a>
    </div>
  </div>
  <style>@media(max-width:600px){{section:last-of-type>div:last-of-type{{grid-template-columns:1fr!important}}}}</style>
</section>
<!-- NB-JOBNEWS-END -->
'''

# ─── END DAILY SECTIONS ───────────────────────────────────────────────────────



# ─── DAILY QUIZ PAGE BUILDER ──────────────────────────────────────────────────


# ─── PROPER MCQ QUIZ BUILDER ─────────────────────────────────────────────────

# Pre-built question templates for common exam topics
MCQ_TEMPLATES = {
    # Environment & Ecology
    "coral": [
        ("Coral reefs are found in which type of water?", ["Warm shallow tropical water","Cold deep ocean water","Freshwater rivers","Polar seas"], 0),
        ("Great Nicobar Island is part of which Union Territory?", ["Andaman & Nicobar Islands","Lakshadweep","Puducherry","Daman & Diu"], 0),
        ("Which organisation conducts the Zoological Survey of India?", ["Ministry of Environment","Ministry of Science","ZSI under MoEFCC","ISRO"], 2),
    ],
    "tiger": [
        ("Project Tiger was launched in which year?", ["1973","1980","1992","2006"], 0),
        ("Which state has the highest number of tigers in India?", ["Madhya Pradesh","Karnataka","Uttarakhand","Maharashtra"], 0),
        ("National Tiger Conservation Authority (NTCA) was established under which act?", ["Wildlife Protection Act 1972","Forest Conservation Act 1980","Environment Protection Act 1986","Biological Diversity Act 2002"], 0),
    ],
    "ramsar": [
        ("Ramsar Convention is related to:", ["Wetland conservation","Forest conservation","Marine pollution","Climate change"], 0),
        ("Chilika Lake in Odisha is a Ramsar site known for:", ["Migratory birds","Tiger reserve","Coral reefs","Mangrove forests"], 0),
    ],
    "national park": [
        ("Jim Corbett National Park is located in which state?", ["Uttarakhand","Uttar Pradesh","Madhya Pradesh","Himachal Pradesh"], 0),
        ("Which is the oldest National Park in India?", ["Jim Corbett","Kaziranga","Gir","Sundarban"], 0),
    ],
    "climate": [
        ("Paris Agreement aims to limit global temperature rise to:", ["1.5-2°C above pre-industrial levels","3°C above pre-industrial levels","0.5°C above current levels","2.5°C above 1990 levels"], 0),
        ("UNFCCC stands for:", ["UN Framework Convention on Climate Change","UN Forum for Climate Control","UN Fund for Climate Crisis","UN Framework for Carbon Control"], 0),
    ],
    "tunnel": [
        ("Zojila Tunnel connects which two regions?", ["Kashmir Valley and Ladakh","Shimla and Manali","Leh and Kargil","Srinagar and Jammu"], 0),
        ("Atal Tunnel (Rohtang) is located in:", ["Himachal Pradesh","Uttarakhand","Jammu & Kashmir","Sikkim"], 0),
        ("Which is the longest road tunnel in India?", ["Atal Tunnel Rohtang","Zojila Tunnel","Banihal Tunnel","Sela Tunnel"], 1),
    ],
    "highway": [
        ("National Highway Authority of India (NHAI) was established in:", ["1988","1995","2001","1947"], 0),
        ("Bharatmala Project is related to:", ["Highway development","Railway expansion","Port development","Airport construction"], 0),
    ],
    "railway": [
        ("Indian Railways is the world's ___ largest railway network?", ["4th","2nd","6th","3rd"], 0),
        ("Vande Bharat Express is a:", ["Semi-high speed train","Luxury train","Freight train","Metro train"], 0),
        ("RRB stands for:", ["Railway Recruitment Board","Railway Revenue Branch","Regional Railway Bureau","Railway Registration Body"], 0),
    ],
    "isro": [
        ("Chandrayaan-3 successfully landed on the Moon's south pole in:", ["2023","2022","2024","2021"], 0),
        ("ISRO was established in:", ["1969","1972","1947","1962"], 0),
        ("Gaganyaan is India's first:", ["Human spaceflight mission","Mars mission","Sun observation mission","Communication satellite"], 0),
        ("ISRO headquarters is located in:", ["Bengaluru","Mumbai","Hyderabad","Chennai"], 0),
    ],
    "drdo": [
        ("DRDO stands for:", ["Defence Research and Development Organisation","Defence Research and Development Office","Department of Research and Defence Operations","Defence Rocket Development Organisation"], 0),
        ("DRDO is under which ministry?", ["Ministry of Defence","Ministry of Science & Technology","Ministry of Home Affairs","Ministry of Finance"], 0),
    ],
    "missile": [
        ("BrahMos missile is a joint venture between India and:", ["Russia","France","USA","Israel"], 0),
        ("Agni-V is classified as:", ["Inter-continental ballistic missile","Short-range ballistic missile","Anti-ship missile","Surface-to-air missile"], 0),
    ],
    "rbi": [
        ("RBI was established in:", ["1935","1947","1950","1955"], 0),
        ("The headquarters of RBI is in:", ["Mumbai","New Delhi","Kolkata","Chennai"], 0),
        ("Repo rate is the rate at which RBI:", ["Lends to commercial banks","Borrows from commercial banks","Issues currency","Fixes inflation"], 0),
        ("CRR stands for:", ["Cash Reserve Ratio","Currency Reserve Rate","Credit Reserve Ratio","Capital Reserve Ratio"], 0),
    ],
    "inflation": [
        ("CPI stands for:", ["Consumer Price Index","Capital Price Index","Currency Price Indicator","Credit Price Index"], 0),
        ("WPI measures prices at:", ["Wholesale level","Retail level","Consumer level","Export level"], 0),
        ("The base year for India's current CPI is:", ["2012","2010","2015","2011"], 0),
    ],
    "bank": [
        ("Which is the largest public sector bank in India?", ["State Bank of India","Punjab National Bank","Bank of Baroda","Canara Bank"], 0),
        ("NABARD provides finance for:", ["Agriculture and rural development","Industry and trade","Housing projects","Defence procurement"], 0),
    ],
    "gdp": [
        ("GDP stands for:", ["Gross Domestic Product","General Domestic Production","Gross Development Programme","General Development Product"], 0),
        ("India is the ___ largest economy in the world by nominal GDP?", ["5th","3rd","7th","4th"], 0),
    ],
    "budget": [
        ("Union Budget is presented by:", ["Finance Minister","Prime Minister","President","RBI Governor"], 0),
        ("Fiscal year in India runs from:", ["April 1 to March 31","January 1 to December 31","July 1 to June 30","October 1 to September 30"], 0),
        ("Direct tax in India is administered by:", ["CBDT","CBIC","RBI","SEBI"], 0),
    ],
    "scheme": [
        ("Ayushman Bharat provides health cover of how much per family per year?", ["Rs 5 lakh","Rs 2 lakh","Rs 10 lakh","Rs 1 lakh"], 0),
        ("PM Kisan Samman Nidhi provides farmers:", ["Rs 6,000 per year","Rs 2,000 per year","Rs 12,000 per year","Rs 4,000 per year"], 0),
        ("Jal Jeevan Mission aims to provide:", ["Piped water to rural households","Solar power to villages","Roads to remote areas","Internet to rural areas"], 0),
    ],
    "mission": [
        ("PM GatiShakti is related to:", ["Multi-modal infrastructure connectivity","Space exploration","Clean energy","Digital India"], 0),
        ("Swachh Bharat Mission was launched in:", ["2014","2016","2012","2018"], 0),
    ],
    "election": [
        ("Election Commission of India was established in:", ["1950","1947","1952","1949"], 0),
        ("Lok Sabha has a total of how many seats?", ["543","545","552","550"], 0),
        ("Model Code of Conduct comes into force:", ["When election schedule is announced","On nomination filing day","On voting day","After results are declared"], 0),
    ],
    "supreme court": [
        ("The Chief Justice of India is appointed by:", ["President of India","Prime Minister","Parliament","Law Commission"], 0),
        ("Supreme Court of India was established in:", ["1950","1947","1935","1919"], 0),
        ("Article 32 of the Constitution deals with:", ["Right to Constitutional Remedies","Right to Equality","Right to Freedom","Right to Education"], 0),
    ],
    "parliament": [
        ("Rajya Sabha is also known as:", ["Council of States","House of the People","Upper House of Parliament","Both A and C"], 2),
        ("Money Bill can only be introduced in:", ["Lok Sabha","Rajya Sabha","Either House","Joint Session"], 0),
        ("The term of Lok Sabha is:", ["5 years","6 years","4 years","3 years"], 0),
    ],
    "g20": [
        ("G20 was established in:", ["1999","2000","2008","1995"], 0),
        ("India held the G20 Presidency in:", ["2023","2022","2024","2021"], 0),
        ("G20 represents approximately what percentage of global GDP?", ["85%","60%","70%","90%"], 0),
    ],
    "india japan": [
        ("India-Japan bilateral relationship is described as:", ["Special Strategic and Global Partnership","Comprehensive Economic Partnership","Strategic Cooperation Agreement","Defence Cooperation Treaty"], 0),
        ("Japan is the ___ largest investor in India?", ["3rd","1st","5th","2nd"], 0),
    ],
    "united nations": [
        ("UN was founded in:", ["1945","1947","1950","1942"], 0),
        ("India is a founding member of:", ["United Nations","NATO","ASEAN","SCO"], 0),
        ("The UN Security Council has how many permanent members?", ["5","7","10","15"], 0),
    ],
    "appointed": [
        ("Constitutional appointments in India are made by:", ["President of India","Prime Minister","Cabinet","Parliament"], 0),
        ("The term of the Chief Justice of India:", ["Until age 65","5 years fixed term","Until age 62","Until age 70"], 0),
    ],
    "award": [
        ("Bharat Ratna is India's:", ["Highest civilian honour","Highest military honour","Second highest civilian honour","Sports achievement award"], 0),
        ("Padma awards are announced on:", ["Republic Day (26 Jan)","Independence Day (15 Aug)","Gandhi Jayanti (2 Oct)","Constitution Day (26 Nov)"], 0),
    ],
    "padma": [
        ("Padma awards have how many categories?", ["3","4","2","5"], 0),
        ("Padma Vibhushan is India's ___ highest civilian award?", ["Second","First","Third","Fourth"], 0),
    ],
    "cancer": [
        ("ICMR stands for:", ["Indian Council of Medical Research","International Centre for Medical Research","Indian Committee for Medical Regulation","Indian Council of Medicine and Research"], 0),
        ("National Cancer Awareness Day is observed on:", ["7 November","4 February","28 September","1 December"], 0),
    ],
    "seychelles": [
        ("Seychelles is located in which ocean?", ["Indian Ocean","Pacific Ocean","Atlantic Ocean","Arctic Ocean"], 0),
        ("The capital of Seychelles is:", ["Victoria","Port Louis","Nassau","Moroni"], 0),
    ],
    "japan": [
        ("Japan's currency is:", ["Yen","Won","Ringgit","Baht"], 0),
        ("Japan is part of which group?", ["G7","G20","Both G7 and G20","ASEAN"], 2),
    ],
    "deregulation": [
        ("Deregulation means:", ["Reducing government control over industries","Increasing taxes on businesses","Nationalising private companies","Fixing prices of goods"], 0),
        ("DPIIT stands for:", ["Department for Promotion of Industry and Internal Trade","Department of Public Investment and Infrastructure","Division of Planning, Industry and Innovation Technology","Department of Production, Industry and Internal Tariff"], 0),
    ],
    "modi": [
        ("Narendra Modi is India's ___ Prime Minister?", ["14th","13th","15th","12th"], 0),
        ("PM Modi launched Digital India initiative in:", ["2015","2014","2016","2013"], 0),
    ],
    "monsoon": [
        ("India receives most of its rainfall from:", ["Southwest Monsoon","Northeast Monsoon","Cyclonic rainfall","Western disturbances"], 0),
        ("Normal onset of Southwest Monsoon in Kerala is:", ["1 June","15 June","1 July","15 May"], 0),
    ],
    "iit": [
        ("First IIT in India was established at:", ["Kharagpur","Mumbai","Chennai","Delhi"], 0),
        ("IITs are institutes of:", ["National importance","State importance","International importance","Both A and C"], 0),
    ],
    "aiims": [
        ("First AIIMS was established in:", ["New Delhi","Mumbai","Chennai","Kolkata"], 0),
        ("AIIMS comes under which ministry?", ["Ministry of Health and Family Welfare","Ministry of Education","Ministry of Science and Technology","Ministry of Human Resource Development"], 0),
    ],
}


def build_mcq_from_article(title, summary, slug):
    """Build a proper MCQ question from a CA article."""
    import random
    text = (title + " " + summary).lower()
    
    # Try to find a matching template
    for keyword, questions in MCQ_TEMPLATES.items():
        if keyword in text:
            q_text, opts, correct_idx = random.choice(questions)
            return {
                "question": q_text,
                "options": opts,
                "correct": correct_idx,
                "hint": f"Related: {title[:60]}",
                "slug": slug,
            }
    
    # No template match — build a factual question from the title
    # Extract key entity (first proper noun / organisation name)
    # Pattern: "X does Y" → "Which organisation did Y?"
    words = title.split()
    
    # Try to identify the subject
    q = None
    if "inaugurated" in text or "launched" in text:
        q = {
            "question": f"Which of the following was recently in news regarding: '{title[:70]}'?",
            "options": [title[:60], "None of the above", "Not mentioned", "Cannot be determined"],
            "correct": 0,
            "hint": summary[:100],
            "slug": slug,
        }
    elif "appointed" in text or "takes charge" in text or "elected" in text:
        q = {
            "question": f"This appointment/election was recently in news. Identify: '{title[:70]}'",
            "options": [title[:60], "Not in the news recently", "Happened last year", "Incorrect information"],
            "correct": 0,
            "hint": summary[:100],
            "slug": slug,
        }
    
    if q:
        return q
    
    # Final fallback — simple identification question
    return {
        "question": f"Which of the following was recently reported in current affairs?",
        "options": [title[:70], "Not a current affair", "Happened 5 years ago", "Fictional event"],
        "correct": 0,
        "hint": summary[:100],
        "slug": slug,
    }

# ─── END MCQ BUILDER ─────────────────────────────────────────────────────────


def rebuild_daily_quiz_page(affairs_list):
    """Regenerate /daily-quiz/index.html with fresh questions from today's CA."""
    import json as _json
    from datetime import date as _date

    TODAY = _date.today().strftime("%d %B %Y")
    YR = _date.today().year
    SITE = "https://naukribulletin.in"

    # Build questions from CA
    questions = []
    for a in affairs_list[:30]:
        title   = a.get("title","")
        summary = a.get("summary","")
        slug    = a.get("slug","")
        if not title or len(title) < 15: continue
        questions.append({"title":title, "summary":summary, "slug":slug})

    if len(questions) < 4:
        print("[QUIZ-PAGE] Not enough CA articles for quiz — skipping")
        return

    q_set = questions[:10]
    all_titles = [q["title"] for q in questions]

    quiz_items = ""
    for i, q in enumerate(q_set):
        # Use proper MCQ with real answer options
        mcq = build_mcq_from_article(q["title"], q.get("summary",""), q["slug"])
        correct_idx = mcq["correct"]
        shuffled = mcq["options"]

        opts_html = "".join(
            f'''<button class="dq-opt" data-idx="{i}" data-val="{j}" data-correct="{correct_idx}" onclick="dqA(this)">
              <span class="dq-letter">{chr(65+j)}</span>
              <span class="dq-text">{shuffled[j][:90]}</span>
            </button>''' for j in range(len(shuffled))
        )
        hint_url = f'/current-affairs/{q["slug"]}/'
        hint_text = q["summary"] if q["summary"] else q["title"]
        quiz_items += f'''
<div class="dq-item" id="dq-{i}" style="display:{'block' if i==0 else 'none'}">
  <div class="dq-num">Question {i+1} of {len(q_set)}</div>
  <div class="dq-q">{hint_text}</div>
  <div class="dq-opts">{opts_html}</div>
  <div class="dq-hint" id="dq-hint-{i}" style="display:none">
    💡 <a href="{hint_url}" style="color:var(--saffron);">Read full article →</a>
  </div>
</div>'''

    nav_html = '''<nav>
  <a href="/" class="logo" style="text-decoration:none;"><span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span></a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right"><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>'''

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Quiz {TODAY} — Current Affairs MCQ for Govt Exams | NaukriBulletin</title>
  <meta name="description" content="Free daily quiz {TODAY} — 10 MCQ questions from today's current affairs for SSC, Banking, Railway and UPSC exam prep.">
  <link rel="canonical" href="{SITE}/daily-quiz/">
  <meta name="robots" content="index,follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/css/style.css">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
{nav_html}
<header style="background:var(--navy);border-bottom:1px solid var(--border);padding:36px 20px 28px;">
  <div style="max-width:900px;margin:0 auto;">
    <div style="font-size:.8rem;color:var(--grey-400);margin-bottom:10px;"><a href="/" style="color:var(--grey-400);">Home</a> › Daily Quiz</div>
    <span style="background:rgba(255,107,0,.14);color:var(--saffron-light);border:1px solid rgba(255,107,0,.3);font-size:.72rem;font-weight:700;padding:5px 11px;border-radius:30px;display:inline-block;margin-bottom:12px;">Updated • {TODAY}</span>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.9rem;color:var(--white);margin:0 0 8px;">📝 Daily Current Affairs Quiz</h1>
    <p style="color:var(--grey-700);font-size:.97rem;margin:0;">{len(q_set)} questions from today's news — for SSC, Banking, Railway &amp; UPSC. New quiz every day.</p>
  </div>
</header>
<main style="max-width:900px;margin:0 auto;padding:28px 20px;">
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:16px 20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:.88rem;color:var(--grey-700);">Answer all {len(q_set)} questions to see your score</span>
    <span style="font-size:1rem;font-weight:700;color:var(--saffron);" id="dq-score">0 / {len(q_set)}</span>
  </div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:24px;" id="dq-container">
    {quiz_items}
  </div>
  <div id="dq-result" style="display:none;background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:32px;text-align:center;">
    <div style="font-size:3rem;margin-bottom:12px;" id="dq-result-emoji">🎉</div>
    <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:var(--white);margin-bottom:8px;" id="dq-final-score"></div>
    <div style="color:var(--grey-700);font-size:.95rem;margin-bottom:20px;" id="dq-final-msg"></div>
    <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
      <button onclick="dqRestart()" style="background:var(--saffron);color:#fff;border:none;padding:10px 24px;border-radius:10px;font-weight:700;cursor:pointer;">🔄 Try Again</button>
      <a href="/current-affairs/" style="display:inline-block;background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:10px 24px;border-radius:10px;font-weight:600;text-decoration:none;">Read Today's CA →</a>
    </div>
  </div>
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:18px;margin-top:18px;">
    <h2 style="font-family:'Syne',sans-serif;font-size:.97rem;color:var(--white);margin:0 0 10px;">More practice</h2>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <a href="/mock-test/" style="background:var(--navy-soft);border:1px solid var(--border);color:var(--white);padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.88rem;">📝 Mock Tests</a>
      <a href="/study-material/" style="background:var(--navy-soft);border:1px solid var(--border);color:var(--white);padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.88rem;">📚 Study Material</a>
      <a href="/previous-year-papers/" style="background:var(--navy-soft);border:1px solid var(--border);color:var(--white);padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.88rem;">📄 Previous Year Papers</a>
      <a href="/current-affairs/" style="background:var(--navy-soft);border:1px solid var(--border);color:var(--white);padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.88rem;">📰 Current Affairs</a>
    </div>
  </div>
</main>
<style>
  .dq-num{{font-size:.75rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;}}
  .dq-q{{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;color:var(--white);line-height:1.5;margin-bottom:18px;}}
  .dq-opts{{display:flex;flex-direction:column;gap:10px;}}
  .dq-opt{{display:flex;align-items:center;gap:12px;background:var(--card-bg);border:1.5px solid var(--border);border-radius:10px;padding:13px 16px;cursor:pointer;text-align:left;transition:.15s;width:100%;font-family:'DM Sans',sans-serif;}}
  .dq-opt:hover{{border-color:var(--saffron);background:rgba(255,107,0,.06);}}
  .dq-opt.correct{{border-color:#63FFDA!important;background:rgba(99,255,218,.1)!important;pointer-events:none;}}
  .dq-opt.wrong{{border-color:#FF6C8A!important;background:rgba(255,108,138,.08)!important;pointer-events:none;}}
  .dq-opt.disabled{{pointer-events:none;opacity:.55;}}
  .dq-letter{{width:30px;height:30px;border-radius:50%;background:var(--border);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.82rem;color:var(--white);flex-shrink:0;}}
  .dq-opt.correct .dq-letter{{background:#63FFDA;color:#0A0A0F;}}
  .dq-opt.wrong .dq-letter{{background:#FF6C8A;color:#fff;}}
  .dq-text{{font-size:.92rem;color:var(--white);line-height:1.4;}}
  .dq-hint{{margin-top:14px;padding:12px 14px;background:rgba(255,107,0,.06);border:1px solid rgba(255,107,0,.2);border-radius:8px;font-size:.85rem;color:var(--grey-700);}}
</style>
<script>
var dqAnswered=new Array({len(q_set)}).fill(false);
var dqScore=0;var dqTotal={len(q_set)};var dqCurrent=0;
function dqA(btn){{
  var qIdx=+btn.dataset.idx,val=+btn.dataset.val,correct=+btn.dataset.correct;
  if(dqAnswered[qIdx])return;
  dqAnswered[qIdx]=true;
  var opts=document.querySelectorAll('.dq-opt[data-idx="'+qIdx+'"]');
  opts.forEach(function(o){{o.classList.add('disabled');}});
  if(val===correct){{btn.classList.remove('disabled');btn.classList.add('correct');dqScore++;document.getElementById('dq-score').textContent=dqScore+' / '+dqTotal;}}
  else{{btn.classList.remove('disabled');btn.classList.add('wrong');var cb=document.querySelector('.dq-opt[data-idx="'+qIdx+'"][data-val="'+correct+'"]');if(cb){{cb.classList.remove('disabled');cb.classList.add('correct');}}}}
  var hint=document.getElementById('dq-hint-'+qIdx);if(hint)hint.style.display='block';
  setTimeout(function(){{
    dqCurrent++;
    if(dqCurrent<dqTotal){{document.getElementById('dq-'+qIdx).style.display='none';document.getElementById('dq-'+dqCurrent).style.display='block';}}
    else{{
      document.getElementById('dq-container').style.display='none';
      document.getElementById('dq-result').style.display='block';
      var pct=Math.round(dqScore/dqTotal*100);
      document.getElementById('dq-final-score').textContent='You scored '+dqScore+' out of '+dqTotal;
      document.getElementById('dq-result-emoji').textContent=pct>=80?'🎉':pct>=50?'👍':'📚';
      document.getElementById('dq-final-msg').textContent=pct>=80?'Excellent! Well prepared for GK sections.':pct>=50?'Good effort — keep reading daily current affairs.':'Keep practicing — read today&#39;s CA and try again.';
    }}
  }},1400);
}}
function dqRestart(){{
  dqAnswered=new Array(dqTotal).fill(false);dqScore=0;dqCurrent=0;
  document.getElementById('dq-score').textContent='0 / '+dqTotal;
  document.getElementById('dq-result').style.display='none';
  document.getElementById('dq-container').style.display='block';
  for(var i=0;i<dqTotal;i++){{
    var el=document.getElementById('dq-'+i);if(el)el.style.display=i===0?'block':'none';
    document.querySelectorAll('.dq-opt[data-idx="'+i+'"]').forEach(function(o){{o.classList.remove('correct','wrong','disabled');}});
    var hint=document.getElementById('dq-hint-'+i);if(hint)hint.style.display='none';
  }}
}}
</script>
<footer style="border-top:1px solid var(--border);background:var(--navy);padding:24px 0;margin-top:40px;"><div style="max-width:1100px;margin:0 auto;padding:0 20px;color:var(--grey-400);font-size:.85rem;display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;"><span>© {YR} NaukriBulletin</span><span><a href="/" style="color:var(--grey-700);">Home</a> · <a href="/jobs/" style="color:var(--grey-700);">Jobs</a> · <a href="/alerts/" style="color:var(--grey-700);">Alerts</a></span></div></footer>
<script>(function(){{var b=document.getElementById("navHamburger");var u=document.querySelector("nav ul");if(!b||!u)return;b.addEventListener("click",function(){{u.classList.toggle("mobile-open");b.classList.toggle("active");}});u.querySelectorAll("a").forEach(function(a){{a.addEventListener("click",function(){{u.classList.remove("mobile-open");b.classList.remove("active");}});}});}})();</script>
</body></html>'''

    quiz_dir = SITE_ROOT / "daily-quiz"
    quiz_dir.mkdir(exist_ok=True)
    (quiz_dir / "index.html").write_text(page, encoding="utf-8")
    print(f"[QUIZ-PAGE] ✅ /daily-quiz/ rebuilt with {len(q_set)} questions")

# ─── END DAILY QUIZ PAGE BUILDER ──────────────────────────────────────────────



# ─── CLOSING SOON + EDUCATION FILTER BUILDERS ────────────────────────────────

def build_closing_soon(all_jobs):
    """Jobs closing in 1/3/7/14 days — with countdown cards."""
    from datetime import date as _date, datetime as _dt
    import re as _re

    today = _date.today()
    MONTHS = {'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
              'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}

    urgent = []
    for j in all_jobs:
        ld = (j.get('last_date') or '').strip()
        if not ld or ld == 'N/A': continue
        # Parse "30 July 2026" format
        m = _re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', ld, _re.I)
        if not m: continue
        try:
            day,mon,yr = int(m.group(1)), MONTHS.get(m.group(2).lower(),0), int(m.group(3))
            if not mon: continue
            ld_date = _date(yr,mon,day)
            diff = (ld_date - today).days
            if 0 <= diff <= 14:
                urgent.append({**j, 'days_left': diff, 'ld_date': ld_date})
        except: continue

    urgent.sort(key=lambda x: x['days_left'])
    if not urgent: return ""

    def urgency_colour(d):
        if d <= 1: return "#FF4444"
        if d <= 3: return "#FF8C33"
        if d <= 7: return "#FFD56C"
        return "#63FFDA"

    cards = ""
    for j in urgent[:8]:
        d = j['days_left']
        col = urgency_colour(d)
        label = "TODAY!" if d==0 else f"{d} day{'s' if d!=1 else ''} left"
        cards += f'''
    <a href="/jobs/{j.get('slug','')}/" style="background:var(--card-bg);border:2px solid {col}22;border-radius:14px;padding:18px;text-decoration:none;display:flex;flex-direction:column;gap:8px;position:relative;overflow:hidden;transition:.2s;" onmouseover="this.style.borderColor='{col}'" onmouseout="this.style.borderColor='{col}22'">      <div style="background:{col};color:#000;font-weight:800;font-size:.75rem;padding:4px 10px;border-radius:20px;align-self:flex-start;">{label}</div>      <div style="font-family:'Syne',sans-serif;font-weight:700;color:var(--white);font-size:.92rem;line-height:1.3;">{j.get('title','')[:55]}</div>      <div style="font-size:.78rem;color:var(--grey-700);">{j.get('dept','')} · 👥 {j.get('vacancies','N/A')}</div>      <div style="font-size:.78rem;color:{col};font-weight:600;">⏰ Last date: {j.get('last_date','N/A')}</div>    </a>'''

    return f'''
<!-- NB-CLOSING-START -->
<section style="max-width:1200px;margin:0 auto 0;padding:0 5% 48px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h2 style="font-family:var(--font-display);font-size:1.5rem;font-weight:800;margin:0;">
      ⚡ Closing <span style="color:var(--accent);">Soon</span>
    </h2>
    <a href="/jobs/" style="color:var(--accent);font-size:.87rem;font-weight:600;text-decoration:none;">All jobs →</a>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;">
    {cards}
  </div>
</section>
<!-- NB-CLOSING-END -->
'''


def build_education_filter(all_jobs):
    """Jobs grouped by qualification — 10th/12th/Graduate/Engineering etc."""
    from collections import Counter

    QUAL_MAP = [
        ('10th', ['10th','matriculation','sslc','class 10'],'10th Pass','🏫'),
        ('12th', ['12th','intermediate','hsc','class 12','10+2'],'12th Pass','📗'),
        ('graduate', ['graduate','graduation','bachelor','b.a','b.sc','b.com','any degree'],'Any Graduate','🎓'),
        ('engineering', ['engineer','b.tech','b.e.','b.e ','btech'],'Engineering','⚙️'),
        ('diploma', ['diploma'],'Diploma','📋'),
        ('postgraduate', ['post graduate','master','mba','m.a','m.sc','m.com'],'Post Graduate','🏛️'),
        ('medical', ['mbbs','b.pharm','nursing','gnm','anm','b.pharma'],'Medical','🏥'),
    ]

    counts = {}
    for key, kws, label, emoji in QUAL_MAP:
        c = sum(1 for j in all_jobs
                if any(kw in (j.get('qualification','') + j.get('category','') + j.get('title','')).lower()
                       for kw in kws))
        counts[key] = (label, emoji, c)

    if not any(v[2] for v in counts.values()): return ""

    cat_links = ""
    for key, (label, emoji, count) in counts.items():
        if count == 0: continue
        h_on  = "this.style.borderColor='var(--accent)'"
        h_off = "this.style.borderColor='var(--border)'"
        cat_links += (
            f'<a href="/jobs/?qual={key}" style="background:var(--surface);border:1px solid var(--border);'
            f'border-radius:12px;padding:14px 12px;text-align:center;text-decoration:none;'
            f'display:flex;flex-direction:column;gap:6px;transition:.15s;"'
            f' onmouseover="{h_on}" onmouseout="{h_off}">'
            f'<span style="font-size:1.5rem;">{emoji}</span>'
            f'<span style="font-family:var(--font-display);font-size:.85rem;font-weight:700;color:var(--text);">{label}</span>'
            f'<span style="font-size:.72rem;color:var(--muted);">{count} jobs</span>'
            f'</a>'
        )

    return f'''
<!-- NB-EDUFIL-START -->
<section style="max-width:1200px;margin:0 auto 0;padding:0 5% 48px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h2 style="font-family:var(--font-display);font-size:1.5rem;font-weight:800;margin:0;">
      🎓 Jobs by <span style="color:var(--accent);">Qualification</span>
    </h2>
    <a href="/jobs/" style="color:var(--accent);font-size:.87rem;font-weight:600;text-decoration:none;">Browse all →</a>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;">
    {cat_links}
  </div>
</section>
<!-- NB-EDUFIL-END -->
'''

# ─── END CLOSING SOON + EDUCATION FILTER ─────────────────────────────────────



def build_three_col(all_jobs, results_items=None, admit_items=None):
    """Three-column homepage section: Latest Jobs | Admit Cards | Results."""
    import re as _re
    from pathlib import Path as _Path

    SITE_ROOT_LOCAL = SITE_ROOT

    def read_items(folder, limit=8):
        d = SITE_ROOT_LOCAL / folder
        items = []
        if not d.exists(): return items
        for sub in sorted(d.iterdir(), reverse=True)[:limit*2]:
            if not sub.is_dir(): continue
            idx = sub/"index.html"
            if not idx.exists(): continue
            try:
                content = idx.read_text(encoding="utf-8", errors="ignore")
                h = _re.search(r'<h1[^>]*>(.*?)</h1>', content, _re.S)
                title = _re.sub(r'<[^>]+>','',h.group(1)).strip() if h else sub.name
                items.append({"title":title[:65],"slug":sub.name})
            except: pass
            if len(items)>=limit: break
        return items

    jobs_rows = "".join(
        f'<a href="/jobs/{j.get("slug","")}/" style="display:block;padding:9px 16px;border-bottom:1px solid var(--border);text-decoration:none;color:var(--white);font-size:.85rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:.1s;">{j.get("title","")}</a>'
        for j in (all_jobs[:8] if all_jobs else [])
    ) or '<div style="padding:12px 16px;color:var(--grey-400);font-size:.85rem;">No jobs today</div>'

    admit_list = read_items("admit-card")
    admit_rows = "".join(
        f'<a href="/admit-card/{i["slug"]}/" style="display:block;padding:9px 16px;border-bottom:1px solid var(--border);text-decoration:none;color:var(--white);font-size:.85rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:.1s;">{i["title"]}</a>'
        for i in admit_list
    ) or '<div style="padding:12px 16px;color:var(--grey-400);font-size:.85rem;">Check back soon</div>'

    results_list = read_items("results")
    result_rows = "".join(
        f'<a href="/results/{i["slug"]}/" style="display:block;padding:9px 16px;border-bottom:1px solid var(--border);text-decoration:none;color:var(--white);font-size:.85rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:.1s;">{i["title"]}</a>'
        for i in results_list
    ) or '<div style="padding:12px 16px;color:var(--grey-400);font-size:.85rem;">Check back soon</div>'

    def col(title, accent, rows, view_href, icon):
        return (f'<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;">'                f'<div style="background:{accent};padding:10px 16px;display:flex;justify-content:space-between;align-items:center;">'                f'<span style="font-family:var(--font-display);font-size:.95rem;font-weight:700;color:#fff;">{icon} {title}</span>'                f'<a href="{view_href}" style="font-size:.75rem;color:rgba(255,255,255,.85);text-decoration:none;font-weight:600;">View All →</a>'                f'</div>{rows}</div>')

    return f"""<!-- NB-3COL-START -->
<section style="max-width:1200px;margin:0 auto 0;padding:0 5% 48px;">
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">
    {col("Job Notifications","#E65100",jobs_rows,"/jobs/","📋")}
    {col("Admit Cards","#1565C0",admit_rows,"/admit-card/","📄")}
    {col("Results","#2E7D32",result_rows,"/results/","📊")}
  </div>
  <style>@media(max-width:768px){{section:has(.nb-3col){{display:none}}}}</style>
</section>
<!-- NB-3COL-END -->"""


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
    ticker_spans = "".join(f"<span>{t}</span>\n            " for t in ticker_items * 2)

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
            <div style="display:flex;gap:8px;align-items:center;">
              <button class="apply-btn" style="flex:1;">Apply Now →</button>
              <button class="save-btn" onclick="event.preventDefault();event.stopPropagation();var job={{slug:'{slug}',title:'{title}',dept:'{dept}',last_date:'{ld}',emoji:'{emoji}'}};if(window.NBSave){{var saved=NBSave.toggle(job);this.textContent=saved?'🔖':'＋';this.title=saved?'Saved':'Save job';this.style.background=saved?'var(--saffron)':'transparent';}}" style="background:transparent;border:1px solid var(--border);color:var(--grey-400);width:36px;height:36px;border-radius:8px;cursor:pointer;font-size:1rem;flex-shrink:0;" title="Save job">＋</button>
            </div>
          </div>
        </a>"""

    job_cards_html = "\n".join(job_card(j) for j in featured)

    # ── Build current affairs cards ───────────────────────────────────────
    def affair_card(a):
        return f"""
        <a href="/current-affairs/{a['slug']}/" style="background:var(--white);border-radius:10px;padding:16px;border:1.5px solid var(--grey-200);text-decoration:none;color:inherit;display:flex;gap:12px;align-items:flex-start;transition:all 0.2s;" onmouseover="this.style.borderColor='var(--saffron)'" onmouseout="this.style.borderColor='var(--grey-200)'">
          <span style="font-size:1.5rem;flex-shrink:0;">{a['emoji']}</span>
          <div>
            <div style="font-size:0.7rem;color:var(--saffron);font-weight:700;margin-bottom:4px;">{a['cat']}</div>
            <div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--white);margin-bottom:4px;">{a['title'][:80]}</div>
            <div style="font-size:0.8rem;color:var(--grey-700);">{a['summary']}</div>
          </div>
        </a>"""

    affairs_html = "\n".join(affair_card(a) for a in affairs) if affairs else """
        <a href="/current-affairs/" style="background:var(--white);border-radius:10px;padding:16px;border:1.5px solid var(--grey-200);text-decoration:none;color:inherit;display:flex;gap:12px;align-items:flex-start;">
          <span style="font-size:1.5rem;">📰</span>
          <div><div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--white);">Latest Current Affairs</div>
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
        r'(<div class="ticker-text">).*?(</div>\s*</div>\s*</div>\s*</div>\s*</div>\s*<!-- HERO -->)',
        lambda m: m.group(1) + "\n            " + ticker_spans + "\n          " + m.group(2),
        html, flags=re.DOTALL
    )

    # 4. Fix hero stats — job count (matches: 221<span>+</span>)
    html = re.sub(
        r'<div class="stat-num">\d+<span>\+</span></div>\s*<div class="stat-label">Active Job Notifications</div>',
        f'<div class="stat-num">{total_jobs}<span>+</span></div>\n          <div class="stat-label">Active Job Notifications</div>',
        html
    )

    # 5. Fix job cards — replace the jobs-grid div content
    html = re.sub(
        r'(<div class="jobs-grid">).*?(</div>\s*<!-- AD -->)',
        lambda m: m.group(1) + job_cards_html + "\n\n      " + m.group(2),
        html, flags=re.DOTALL
    )

    # 6. Fix current affairs — replace the 3 hardcoded affair cards
    html = re.sub(
        r'(<div style="display: flex; flex-direction: column; gap: 10px;">).*?(</div>\s*</section>)',
        lambda m: m.group(1) + affairs_html + "\n\n      " + m.group(2),
        html, flags=re.DOTALL
    )

    # Build and inject the three new daily sections
    affairs_full = []
    for adir in sorted(affairs_dir.iterdir(), reverse=True):
        if not adir.is_dir(): continue
        idx2 = adir / "index.html"
        if not idx2.exists(): continue
        try:
            from bs4 import BeautifulSoup as _BS
            _s = _BS(idx2.read_text(encoding="utf-8"), "html.parser")
            _h = _s.find("h1")
            _p = _s.find("p")
            _title = _h.get_text(strip=True) if _h else ""
            _sum   = _p.get_text(strip=True)[:120] if _p else ""
            if _title and len(_title) > 10:
                affairs_full.append({"slug": adir.name, "title": _title, "summary": _sum})
        except Exception:
            pass
        if len(affairs_full) >= 25: break

    quiz_html       = build_daily_quiz(affairs_full)
    rebuild_daily_quiz_page(affairs_full)
    flashcard_html  = build_flashcards(all_jobs[:12])
    jobnews_html    = build_job_news(affairs_full, all_jobs[:10])

    three_col_html = build_three_col(all_jobs)
    closing_html  = build_closing_soon(all_jobs)
    edu_html      = build_education_filter(all_jobs)
    daily_block   = three_col_html + closing_html + edu_html + quiz_html + flashcard_html + jobnews_html

    # Inject before </footer> (idempotent: replace existing or insert fresh)
    import re as _re
    for marker_pair in [
        ("<!-- NB-3COL-START -->", "<!-- NB-3COL-END -->"),
        ("<!-- NB-CLOSING-START -->", "<!-- NB-CLOSING-END -->"),
        ("<!-- NB-EDUFIL-START -->", "<!-- NB-EDUFIL-END -->"),
        ("<!-- NB-QUIZ-START -->", "<!-- NB-QUIZ-END -->"),
        ("<!-- NB-FLASHCARDS-START -->", "<!-- NB-FLASHCARDS-END -->"),
        ("<!-- NB-JOBNEWS-START -->", "<!-- NB-JOBNEWS-END -->"),
    ]:
        if marker_pair[0] in html:
            html = _re.sub(
                _re.escape(marker_pair[0]) + ".*?" + _re.escape(marker_pair[1]),
                "", html, flags=_re.DOTALL
            )

    footer_idx = html.rfind("<!-- FOOTER -->")
    if footer_idx == -1:
        footer_idx = html.rfind("<footer")
    if footer_idx != -1 and daily_block.strip():
        html = html[:footer_idx] + "\n" + daily_block + "\n" + html[footer_idx:]

    out_path.write_text(html, encoding="utf-8")
    print(f"[HOMEPAGE] ✅ index.html rebuilt — {total_jobs} jobs, {len(affairs)} current affairs, ticker updated")

def rebuild_jobs_listing():
    jobs_dir = SITE_ROOT / "jobs"
    jobs = []
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir():
            continue
        index_file = job_dir / "index.html"
        if not index_file.exists():
            continue
        meta = get_job_meta_from_html(index_file)
        if meta and meta.get("title"):
            jobs.append(meta)

    print(f"[LISTING] Rebuilding /jobs/ with {len(jobs)} jobs")
    cards_html = "\n".join(build_job_card(j) for j in jobs)
    count      = len(jobs)
    yr         = datetime.now().year

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Latest Govt Jobs {yr} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="All latest govt job notifications {yr}. SSC, Railway, Banking, UPSC, State PSC jobs. Direct from official sources. Free daily alerts.">
  <link rel="canonical" href="https://naukribulletin.in/jobs/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
  <nav>
  <a href="/" class="logo" style="text-decoration:none;">
    <span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span>
  </a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right">
    <a href="/alerts/" class="nav-cta">🔔 Get Alerts</a>
  </div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>

  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="color:var(--grey-400);font-size:0.8rem;margin-bottom:8px;">
        <a href="/" style="color:var(--grey-400);text-decoration:none;">Home</a> › Latest Jobs
      </div>
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        Latest <span style="color:var(--saffron);">Govt Jobs {yr}</span>
      </h1>
      <p style="color:var(--grey-400);font-size:0.95rem;">{count}+ active notifications — from official sources, updated 3× daily</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:0 auto;padding:0 20px;">
    <div class="ad-slot ad-banner">Advertisement</div>
  </div>

  <div class="container">
    <div class="two-col">
      <section>
        <div class="filter-tabs">
          <div class="tab active" onclick="filterJobs('all',this)">All</div>
          <div class="tab" onclick="filterJobs('ssc',this)">SSC</div>
          <div class="tab" onclick="filterJobs('railway',this)">Railway</div>
          <div class="tab" onclick="filterJobs('banking',this)">Banking</div>
          <div class="tab" onclick="filterJobs('upsc',this)">UPSC</div>
          <div class="tab" onclick="filterJobs('defence',this)">Defence</div>
          <div class="tab" onclick="filterJobs('police',this)">Police</div>
          <div class="tab" onclick="filterJobs('teaching',this)">Teaching</div>
          <div class="tab" onclick="filterJobs('state',this)">State PSC</div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <span style="font-size:0.85rem;color:var(--grey-700);">Showing <strong id="job-count">{count}</strong> jobs</span>
          <select id="sort-select" onchange="sortJobs(this.value)" style="font-family:var(--font-body);font-size:0.82rem;border:1.5px solid var(--grey-200);border-radius:6px;padding:5px 10px;background:var(--white);color:var(--text);">
            <option value="newest">Newest First</option>
            <option value="urgent">Last Date (Urgent)</option>
          </select>
        </div>
        <div id="jobs-list" style="display:flex;flex-direction:column;gap:12px;">
{cards_html}
        </div>
      </section>

      <aside class="sidebar">
        <div class="telegram-cta">
          <h3>📢 Free Job Alerts</h3>
          <p>Get daily alerts on Telegram</p>
          <a href="https://t.me/naukribulletin24" class="telegram-btn">Join Channel →</a>
        </div>
        <div class="card">
          <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--white);margin-bottom:14px;">🔍 Filter by Category</div>
          <select onchange="filterJobs(this.value,null)" style="width:100%;font-family:var(--font-body);font-size:0.85rem;border:1.5px solid var(--grey-200);border-radius:8px;padding:8px 12px;color:var(--text);background:var(--white);">
            <option value="all">All Categories</option>
            <option value="ssc">SSC</option>
            <option value="railway">Railway</option>
            <option value="banking">Banking</option>
            <option value="upsc">UPSC</option>
            <option value="defence">Defence</option>
            <option value="police">Police</option>
            <option value="teaching">Teaching</option>
            <option value="state">State PSC</option>
          </select>
        </div>
        <div class="ad-slot ad-sidebar">Advertisement</div>
      </aside>
    </div>
  </div>

  <footer>
    <div class="footer-inner">
      <div class="footer-grid">
        <div class="footer-brand">
          <a href="/" class="logo" style="text-decoration:none;"><span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span></a>
          <p>India's smartest govt job portal. Direct from official sources — not aggregators. AI-powered daily alerts, always free.</p>
        </div>
        <div class="footer-col">
          <h4>Central Jobs</h4>
          <ul>
            <li><a href="/jobs/">SSC Jobs</a></li>
            <li><a href="/jobs/">Railway Jobs</a></li>
            <li><a href="/jobs/">Banking Jobs</a></li>
            <li><a href="/jobs/">UPSC Jobs</a></li>
            <li><a href="/jobs/">Defence Jobs</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>State PSC Jobs</h4>
          <ul>
            <li><a href="/jobs/">UPPSC (UP)</a></li>
            <li><a href="/jobs/">BPSC (Bihar)</a></li>
            <li><a href="/jobs/">MPPSC (MP)</a></li>
            <li><a href="/jobs/">RPSC (Rajasthan)</a></li>
            <li><a href="/jobs/">TNPSC (Tamil Nadu)</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Resources</h4>
          <ul>
            <li><a href="/cut-off/">Cut Off</a></li>
            <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
            <li><a href="/syllabus/">Syllabus</a></li>
            <li><a href="/current-affairs/">Current Affairs</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <p>© {yr} NaukriBulletin.in — All Rights Reserved</p>
        <p>
          <a href="/privacy/" style="color:var(--grey-400);text-decoration:none;margin-right:16px;">Privacy Policy</a>
          <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a>
        </p>
      </div>
    </div>
  </footer>

  <script>
    function filterJobs(category, el) {{
      if (el) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        el.classList.add('active');
      }}
      const cards = document.querySelectorAll('#jobs-list a');
      let count = 0;
      cards.forEach(card => {{
        const show = category === 'all' || card.dataset.category === category;
        card.style.display = show ? 'block' : 'none';
        if (show) count++;
      }});
      document.getElementById('job-count').textContent = count;
    }}
    function sortJobs(val) {{
      const list = document.getElementById('jobs-list');
      const cards = Array.from(list.querySelectorAll('a'));
      if (val === 'urgent') {{
        cards.sort((a, b) => {{
          const da = a.querySelector('span[style*="E65100"]')?.textContent || '';
          const db = b.querySelector('span[style*="E65100"]')?.textContent || '';
          return da.localeCompare(db);
        }});
        cards.forEach(c => list.appendChild(c));
      }}
    }}
  </script>
<script>
(function() {{
  var btn = document.getElementById('navHamburger');
  var links = document.querySelector('nav ul');
  if (!btn || !links) return;

  var overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  function closeMenu() {{
    btn.classList.remove('active');
    links.classList.remove('mobile-open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }}
  function openMenu() {{
    btn.classList.add('active');
    links.classList.add('mobile-open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }}
  btn.addEventListener('click', function() {{
    links.classList.contains('mobile-open') ? closeMenu() : openMenu();
  }});
  overlay.addEventListener('click', closeMenu);
  links.querySelectorAll('a').forEach(function(a) {{
    a.addEventListener('click', closeMenu);
  }});
}})();
</script>

<script>
window.NBSave={{toggle:function(j){{var l=JSON.parse(localStorage.getItem('nb_saved')||'[]');var i=l.findIndex(function(x){{return x.slug===j.slug;}});if(i>=0)l.splice(i,1);else l.unshift(j);localStorage.setItem('nb_saved',JSON.stringify(l));return i<0;}},isSaved:function(slug){{return JSON.parse(localStorage.getItem('nb_saved')||'[]').some(function(j){{return j.slug===slug;}})}}}};
function nbToggleSave(btn){{event.preventDefault();event.stopPropagation();var job={{slug:btn.dataset.saveSlug,title:btn.dataset.saveTitle,dept:btn.dataset.saveDept,last_date:btn.dataset.saveLd,emoji:btn.dataset.saveEmoji||'📋'}};var saved=NBSave.toggle(job);btn.textContent=saved?'🔖':'＋';btn.style.background=saved?'var(--saffron)':'transparent';btn.style.color=saved?'#fff':'var(--grey-400)';btn.title=saved?'Saved':'Save job';}}
document.addEventListener('DOMContentLoaded',function(){{var saved=JSON.parse(localStorage.getItem('nb_saved')||'[]');saved.forEach(function(j){{var b=document.querySelector('[data-save-slug="'+j.slug+'"]');if(b){{b.textContent='🔖';b.style.background='var(--saffron)';b.style.color='#fff';}}}})}});
</script>
<script src="/js/naukribot.js" defer></script>
</body>
</html>"""

    with open(SITE_ROOT / "jobs" / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ /jobs/index.html rebuilt with {count} jobs")


def get_affairs_meta_from_html(html_path):
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        slug  = html_path.parent.name
        cat_div = soup.find(style=lambda s: s and "FF6B00" in str(s) and "letter-spacing" in str(s))
        cat_raw = cat_div.get_text(strip=True) if cat_div else "General"
        category = cat_raw.split("•")[0].strip().title() if "•" in cat_raw else cat_raw.strip().title()
        exam_tag = soup.find(style=lambda s: s and "FF8C33" in str(s))
        exam_rel = exam_tag.get_text(strip=True) if exam_tag else "All Exams"
        summary_p = soup.find("p", style=lambda s: s and "1.7" in str(s))
        summary = (summary_p.get_text(strip=True)[:120] + "...") if summary_p else ""
        mtime    = html_path.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%d %b")
        cat_class_map = {
            "economy": "cat-economy", "science": "cat-science",
            "international": "cat-international", "sports": "cat-sports",
            "awards": "cat-awards", "government": "cat-government",
            "environment": "cat-environment",
        }
        cat_class = next((v for k, v in cat_class_map.items() if k in category.lower()), "cat-government")
        return {"slug": slug, "title": title, "category": category, "cat_class": cat_class,
                "exam_rel": exam_rel, "summary": summary, "date_str": date_str}
    except Exception as e:
        print(f"[META] Error reading {html_path}: {e}")
        return None


def rebuild_affairs_listing():
    affairs_dir = SITE_ROOT / "current-affairs"
    items = []
    for item_dir in sorted(affairs_dir.iterdir(), reverse=True):
        if not item_dir.is_dir():
            continue
        index_file = item_dir / "index.html"
        if not index_file.exists():
            continue
        meta = get_affairs_meta_from_html(index_file)
        if meta and meta.get("title"):
            items.append(meta)

    print(f"[LISTING] Rebuilding /current-affairs/ with {len(items)} items")
    cards_html = ""
    for item in items:
        parts = item["date_str"].split(" ")
        day   = parts[0] if parts else ""
        month = parts[1] if len(parts) > 1 else ""
        cards_html += f"""
      <a href="/current-affairs/{item['slug']}/" class="affairs-card fade-up" style="text-decoration:none;color:inherit;">
        <div style="background:var(--navy);border-radius:8px;padding:8px 10px;text-align:center;min-width:48px;color:var(--white);flex-shrink:0;">
          <div style="font-family:var(--font-display);font-size:1.2rem;font-weight:800;line-height:1;">{day}</div>
          <div style="font-size:0.65rem;opacity:0.7;text-transform:uppercase;">{month}</div>
        </div>
        <div style="flex:1;min-width:0;">
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
            <span class="cat-pill {item['cat_class']}">{item['category'].upper()}</span>
            <span style="font-size:0.72rem;color:var(--grey-400);">📚 {item['exam_rel']}</span>
          </div>
          <div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--white);margin-bottom:6px;line-height:1.3;">{item['title']}</div>
          <p style="font-size:0.82rem;color:var(--grey-700);line-height:1.5;margin:0;">{item['summary']}</p>
        </div>
      </a>"""

    yr    = datetime.now().year
    count = len(items)
    html  = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Current Affairs {yr} for UPSC, SSC, Banking | NaukriBulletin</title>
  <meta name="description" content="Daily current affairs {yr} for UPSC, SSC, Railway, Banking exams. Economy, Science, International, Sports, Awards — AI-summarized exam-ready notes.">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <style>
    .affairs-card {{background:var(--card-bg);border-radius:12px;border:1.5px solid var(--grey-200);padding:20px;display:flex;gap:16px;text-decoration:none;color:inherit;transition:all 0.25s;}}
    .affairs-card:hover {{border-color:var(--saffron);box-shadow:0 4px 20px rgba(255,107,0,0.1);transform:translateY(-1px);}}
    .cat-pill {{font-size:0.68rem;font-weight:700;padding:3px 8px;border-radius:4px;letter-spacing:0.04em;white-space:nowrap;}}
    .cat-economy {{background:rgba(46,125,50,0.2);color:#81C784;}}
    .cat-science {{background:rgba(21,101,192,0.2);color:#64B5F6;}}
    .cat-international {{background:rgba(106,27,154,0.2);color:#CE93D8;}}
    .cat-sports {{background:rgba(230,81,0,0.2);color:#FFB74D;}}
    .cat-awards {{background:rgba(173,20,87,0.2);color:#F48FB1;}}
    .cat-government {{background:rgba(0,105,92,0.2);color:#80CBC4;}}
    .cat-environment {{background:rgba(51,105,30,0.2);color:#AED581;}}
  </style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
  <nav>
  <a href="/" class="logo" style="text-decoration:none;">
    <span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span>
  </a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI</a></li>
  </ul>
  <div class="nav-right">
    <a href="/alerts/" class="nav-cta">🔔 Get Alerts</a>
  </div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>
  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        Daily <span style="color:var(--saffron);">Current Affairs {yr}</span>
      </h1>
      <p style="color:var(--grey-400);font-size:0.95rem;">{count}+ articles — exam-ready summaries, updated daily</p>
    </div>
  </div>
  <div class="container">
    <div class="two-col">
      <section>
        <div style="display:flex;flex-direction:column;gap:12px;">
{cards_html}
        </div>
      </section>
      <aside class="sidebar">
        <div class="telegram-cta">
          <h3>📢 Free Alerts</h3>
          <p>Daily current affairs on Telegram</p>
          <a href="https://t.me/naukribulletin24" class="telegram-btn">Join Channel →</a>
        </div>
        <div class="ad-slot ad-sidebar">Advertisement</div>
      </aside>
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
(function() {{
  var btn = document.getElementById('navHamburger');
  var links = document.querySelector('nav ul');
  if (!btn || !links) return;

  var overlay = document.createElement('div');
  overlay.className = 'nav-overlay';
  document.body.appendChild(overlay);

  function closeMenu() {{
    btn.classList.remove('active');
    links.classList.remove('mobile-open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }}
  function openMenu() {{
    btn.classList.add('active');
    links.classList.add('mobile-open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }}
  btn.addEventListener('click', function() {{
    links.classList.contains('mobile-open') ? closeMenu() : openMenu();
  }});
  overlay.addEventListener('click', closeMenu);
  links.querySelectorAll('a').forEach(function(a) {{
    a.addEventListener('click', closeMenu);
  }});
}})();
</script>
<script src="/js/naukribot.js" defer></script>
</body>
</html>"""

    with open(SITE_ROOT / "current-affairs" / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ /current-affairs/index.html rebuilt with {count} items")



# ─── EXPIRED JOB PRUNER ───────────────────────────────────────────────────────

def prune_expired_jobs(days_grace=7):
    """
    Remove job pages whose last date has passed by more than days_grace days.
    Keeps the sitemap clean and avoids Google indexing stale pages.
    Returns count of removed pages.
    """
    from datetime import datetime, date, timedelta
    from bs4 import BeautifulSoup

    jobs_dir  = SITE_ROOT / "jobs"
    cutoff    = date.today() - timedelta(days=days_grace)
    removed   = 0

    SKIP = {
        "ssc","railway","banking","upsc","defence","police","teaching","state",
        "10th-pass","12th-pass","graduate","post-graduate","engineering","all-india",
        "uttar-pradesh","bihar","madhya-pradesh","rajasthan","tamil-nadu","karnataka",
        "maharashtra","gujarat","kerala","delhi","odisha","assam","punjab","haryana",
        "andhra-pradesh","telangana","west-bengal","chhattisgarh","himachal-pradesh",
        "jharkhand","all-india-government-jobs","government-jobs-2026","psu-jobs-2026",
        "graduate-govt-jobs-2026","iti-govt-jobs-2026","mba-govt-jobs-2026",
        "mca-govt-jobs-2026","law-govt-jobs-2026","govt-bank-jobs-2026",
        "govt-jobs-closing-today","non-executive-posts","faculty-posts-recruitment",
        "indian-railways-jobs","combined-defence-services","banking",
        "national-defence-academy-naval-academy-exam","all-india-government-jobs",
        "iaf-agniveer-vayu","nabard-specialist-jobs","sbi-job-openings",
        "indian-railway-recruitment-2026","sbi-job-openings","government-jobs-2026",
    }

    for job_dir in list(jobs_dir.iterdir()):
        if not job_dir.is_dir() or job_dir.name in SKIP:
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        try:
            soup = BeautifulSoup(idx.read_text(encoding="utf-8"), "html.parser")
            rows = {}
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) == 2:
                    rows[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)
            ld = rows.get("last date", "").strip()
            if not ld or ld.lower() in ("n/a", ""):
                continue
            for fmt in ["%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                try:
                    last_date = __import__("datetime").datetime.strptime(ld, fmt).date()
                    if last_date < cutoff:
                        import shutil
                        shutil.rmtree(job_dir)
                        print(f"  [PRUNE] Removed expired: {job_dir.name} (last date: {ld})")
                        removed += 1
                    break
                except ValueError:
                    continue
        except Exception as e:
            print(f"  [PRUNE] Error checking {job_dir.name}: {e}")

    print(f"[PRUNE] ✅ Removed {removed} expired job pages")
    return removed


# ─── INDEXNOW + GSC PING ──────────────────────────────────────────────────────

def ping_search_engines(new_slugs: list):
    """
    Ping IndexNow (Bing/Yandex/others) and Google Search Console
    with newly published URLs so they get indexed faster.
    Only runs if INDEXNOW_KEY env var is set.
    """
    import os, requests

    key = os.environ.get("INDEXNOW_KEY", "")
    gsc_key = os.environ.get("GOOGLE_INDEXING_KEY", "")  # optional service account JSON

    if not new_slugs:
        print("[PING] No new URLs to ping")
        return

    urls = [f"{SITE_URL}/jobs/{slug}/" for slug in new_slugs]
    # Also ping listing pages
    urls += [f"{SITE_URL}/jobs/", f"{SITE_URL}/sitemap.xml"]

    # ── IndexNow ──────────────────────────────────────────────────────────────
    if key:
        try:
            payload = {
                "host": "naukribulletin.in",
                "key": key,
                "keyLocation": f"{SITE_URL}/{key}.txt",
                "urlList": urls[:100],  # IndexNow limit
            }
            r = requests.post(
                "https://api.indexnow.org/IndexNow",
                json=payload,
                timeout=15,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            if r.status_code in (200, 202):
                print(f"[PING] ✅ IndexNow accepted {len(urls)} URLs")
            else:
                print(f"[PING] IndexNow response: {r.status_code}")
        except Exception as e:
            print(f"[PING] IndexNow error: {e}")
    else:
        print("[PING] INDEXNOW_KEY not set — skipping IndexNow ping")

    # ── Google Search Console (Indexing API) ──────────────────────────────────
    # Requires GOOGLE_INDEXING_KEY = service account JSON as env var string
    # Only worth setting up after AdSense approval; skip gracefully otherwise
    if gsc_key:
        try:
            import json as _json
            from google.oauth2 import service_account
            import googleapiclient.discovery
            creds_info = _json.loads(gsc_key)
            creds = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=["https://www.googleapis.com/auth/indexing"],
            )
            service = googleapiclient.discovery.build("indexing", "v3", credentials=creds)
            for url in urls[:200]:
                service.urlNotifications().publish(
                    body={"url": url, "type": "URL_UPDATED"}
                ).execute()
            print(f"[PING] ✅ GSC Indexing API notified {len(urls)} URLs")
        except Exception as e:
            print(f"[PING] GSC error (non-fatal): {e}")


# ─── STATE PAGES REBUILDER ────────────────────────────────────────────────────

def rebuild_state_and_category_pages():
    """
    Runs patch_state_pages.py and category_gen.py from within scraper.py
    so state/category hub pages stay fresh after every scrape.
    """
    import importlib.util

    for script_name, func_name in [
        ("category_gen", "run"),
        ("patch_state_pages", "run"),
    ]:
        script_path = SITE_ROOT / "scripts" / f"{script_name}.py"
        # patch_state_pages.py lives at repo root, not scripts/
        if not script_path.exists():
            script_path = SITE_ROOT / f"{script_name}.py"
        if not script_path.exists():
            print(f"[REBUILD] {script_name}.py not found — skipping")
            continue
        try:
            spec = importlib.util.spec_from_file_location(script_name, script_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, func_name):
                getattr(mod, func_name)()
                print(f"[REBUILD] ✅ {script_name}.run() completed")
            else:
                print(f"[REBUILD] {script_name} has no run() — skipping")
        except Exception as e:
            print(f"[REBUILD] {script_name} error: {e}")


if __name__ == "__main__":
    run()

