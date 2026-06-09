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
ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "ca-pub-XXXXXXXXXX")
ADSENSE_SLOT_TOP = os.environ.get("ADSENSE_SLOT_TOP", "XXXXXXXXXX")
ADSENSE_SLOT_MID = os.environ.get("ADSENSE_SLOT_MID", "XXXXXXXXXX")
SITE_ROOT = Path(__file__).parent.parent

# ─── SOURCES ──────────────────────────────────────────────────────────────────
# Strategy: primary = direct .gov.in feeds (original, first-party)
#           secondary = official exam bodies (IBPS, RBI, etc.)
#           state PSCs = competitor gap (FreeJobAlert weak here)
#           supplementary = Employment News + NCS (official govt portals)
#           current affairs = PIB + DD News (official only)
#           news sources = The Hindu kept for current affairs only

SOURCES = [

    # ── CENTRAL / NATIONAL ─────────────────────────────────────────────────
    {
        "url": "https://ssc.gov.in/rss-feed",
        "fallback_url": "https://ssc.gov.in/",
        "type": "rss",
        "dept": "SSC",
        "category": "ssc",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.indianrailways.gov.in/railwayboard/uploads/rss/announcements_rss.xml",
        "fallback_url": "https://www.rrbapply.gov.in/",
        "type": "rss",
        "dept": "Indian Railways",
        "category": "railway",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://upsc.gov.in/rss.xml",
        "fallback_url": "https://upsc.gov.in/examinations/active-examinations",
        "type": "rss",
        "dept": "UPSC",
        "category": "upsc",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.ibps.in/feed/",
        "fallback_url": "https://www.ibps.in/",
        "type": "rss",
        "dept": "IBPS",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.sbi.co.in/web/careers/careers.rss",
        "fallback_url": "https://bank.sbi/web/careers/current-openings",
        "type": "rss",
        "dept": "SBI",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://opportunities.rbi.org.in/Scripts/Rss.aspx",
        "fallback_url": "https://opportunities.rbi.org.in/Scripts/Opportunities.aspx",
        "type": "rss",
        "dept": "RBI",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.ncs.gov.in/rss-feed/jobs",
        "fallback_url": None,
        "type": "rss",
        "dept": "NCS (National Career Service)",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.employmentnews.gov.in/feed/",
        "fallback_url": None,
        "type": "rss",
        "dept": "Employment News",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },

    # ── DEFENCE / PARAMILITARY ─────────────────────────────────────────────
    {
        "url": "https://joinindianarmy.nic.in/rss.xml",
        "fallback_url": "https://joinindianarmy.nic.in/",
        "type": "rss",
        "dept": "Indian Army",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.indiannavy.nic.in/rss.xml",
        "fallback_url": "https://www.indiannavy.nic.in/content/sailor-recruitment",
        "type": "rss",
        "dept": "Indian Navy",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://afcat.cdac.in/AFCAT/rss",
        "fallback_url": "https://careerindianairforce.cdac.in/",
        "type": "rss",
        "dept": "Indian Air Force",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.crpf.gov.in/rss.xml",
        "fallback_url": "https://www.crpf.gov.in/recruitment.htm",
        "type": "html",
        "dept": "CRPF",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },

    # ── STATE PSCs (FreeJobAlert gap — prioritised) ─────────────────────────
    {
        "url": "https://uppsc.up.nic.in/rss.xml",
        "fallback_url": "https://uppsc.up.nic.in/CandidateInfo/LatestNews.aspx",
        "type": "rss",
        "dept": "UPPSC (Uttar Pradesh)",
        "category": "state",
        "state": "Uttar Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.bpsc.bih.nic.in/rss.xml",
        "fallback_url": "https://www.bpsc.bih.nic.in/Notices.aspx",
        "type": "rss",
        "dept": "BPSC (Bihar)",
        "category": "state",
        "state": "Bihar",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://mppsc.mp.gov.in/rss.xml",
        "fallback_url": "https://mppsc.mp.gov.in/",
        "type": "rss",
        "dept": "MPPSC (Madhya Pradesh)",
        "category": "state",
        "state": "Madhya Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://rpsc.rajasthan.gov.in/rss.xml",
        "fallback_url": "https://rpsc.rajasthan.gov.in/LatestNotification",
        "type": "rss",
        "dept": "RPSC (Rajasthan)",
        "category": "state",
        "state": "Rajasthan",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.tnpsc.gov.in/rss.xml",
        "fallback_url": "https://www.tnpsc.gov.in/notifications.html",
        "type": "rss",
        "dept": "TNPSC (Tamil Nadu)",
        "category": "state",
        "state": "Tamil Nadu",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://kpsc.kar.nic.in/rss.xml",
        "fallback_url": "https://kpsc.kar.nic.in/NewNotifications.aspx",
        "type": "rss",
        "dept": "KPSC (Karnataka)",
        "category": "state",
        "state": "Karnataka",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.mpsc.gov.in/rss.xml",
        "fallback_url": "https://www.mpsc.gov.in/en/advertisements",
        "type": "rss",
        "dept": "MPSC (Maharashtra)",
        "category": "state",
        "state": "Maharashtra",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://gpsc.gujarat.gov.in/rss.xml",
        "fallback_url": "https://gpsc.gujarat.gov.in/ViewNotification",
        "type": "rss",
        "dept": "GPSC (Gujarat)",
        "category": "state",
        "state": "Gujarat",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://hpsc.gov.in/rss.xml",
        "fallback_url": "https://hpsc.gov.in/Advertisements.aspx",
        "type": "rss",
        "dept": "HPSC (Haryana)",
        "category": "state",
        "state": "Haryana",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://apsc.nic.in/rss.xml",
        "fallback_url": "https://apsc.nic.in/notification",
        "type": "rss",
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
        "url": "https://pib.gov.in/RSSNewRelease.aspx",
        "fallback_url": None,
        "type": "rss",
        "dept": "PIB",
        "category": "news",
        "priority": 1,
        "content_type": "affairs",
    },
    {
        "url": "https://newsonair.gov.in/rss.aspx",
        "fallback_url": None,
        "type": "rss",
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
]

GROQ_MODELS  = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192"]
GEMINI_MODEL = "gemini-1.5-flash"

PROCESSED_FILE = SITE_ROOT / "scripts" / "processed.json"

# User-Agent rotator — avoids simple bot blocks on .gov.in sites
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "NaukriBulletin/2.0 (+https://naukribulletin.in/)",
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


def make_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


def make_slug(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug[:60]


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

def _get(url, timeout=20):
    """GET with rotating UA, retry once on failure."""
    headers = {"User-Agent": next_ua(), "Accept": "application/xml, text/xml, */*"}
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        return r
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (403, 404, 410):
            return None          # permanent failure — skip silently
        raise
    except Exception:
        # One retry with a different UA after a short pause
        time.sleep(2)
        try:
            headers["User-Agent"] = next_ua()
            return requests.get(url, timeout=timeout, headers=headers)
        except Exception:
            return None


def scrape_rss(url, dept, fallback_url=None):
    """Fetch RSS. If RSS fails and a fallback HTML URL exists, fall back."""
    items = []
    resp = _get(url)

    if not resp or not resp.content.strip():
        if fallback_url:
            print(f"  [SCRAPER] RSS unavailable, trying HTML fallback: {fallback_url}")
            return scrape_html(fallback_url, dept)
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


def scrape_html(url, dept):
    """Fetch HTML notification page and extract visible text."""
    items = []
    resp = _get(url)
    if not resp:
        return items
    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        # Clean up excessive blank lines
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
  "title": "Full job title including post name",
  "department": "Full official department/organisation name",
  "vacancies": "Total number of posts, or N/A",
  "qualification": "Minimum educational qualification",
  "age_limit": "Age range e.g. 18-25 years",
  "last_date": "DD Month YYYY or N/A",
  "salary": "Pay scale or salary range in ₹",
  "state": "{state_hint}",
  "category": "10th Pass / 12th Pass / Graduate / Post Graduate / Engineering",
  "apply_link": "Official apply URL or source URL",
  "summary": "2 plain-English sentences about this job opportunity",
  "meta_description": "SEO description under 155 characters",
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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{job.get('title', 'Govt Job')} — NaukriBulletin</title>
  <meta name="description" content="{job.get('meta_description', '')}">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:title" content="{job.get('title', 'Govt Job')}">
  <meta property="og:description" content="{job.get('meta_description', '')}">
  <meta property="og:url" content="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:type" content="website">
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
        "addressCountry": "IN",
        "addressRegion": "{job.get('state', 'All India')}"
      }}
    }},
    "datePosted": "{today}",
    "validThrough": "{job.get('last_date', '')}",
    "employmentType": "FULL_TIME",
    "url": "https://naukribulletin.in/jobs/{slug}/"
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;font-size:0.85rem;">← All Jobs</a>
    </div>
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
          <a href="https://testbook.com/?utm_source=naukribulletin&utm_medium=affiliate" target="_blank" rel="noopener sponsored"
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
</body>
</html>"""
    return slug, html


def generate_affairs_html(affair):
    slug       = affair.get("slug") or make_slug(affair.get("title", "news"))
    today      = datetime.now().strftime("%d %B %Y")
    key_facts  = affair.get("key_facts", [])
    facts_html = "".join([f"<li style='margin-bottom:8px;font-size:0.9rem;'>{f}</li>" for f in key_facts])

    html = f"""<!DOCTYPE html>
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
  </nav>

  <main style="max-width:900px;margin:0 auto;padding:32px 20px;">
    <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:16px;">
      <a href="/" style="color:#9BA3B8;">Home</a> ›
      <a href="/current-affairs/" style="color:#9BA3B8;">Current Affairs</a> ›
      <span>{affair.get('category', '')}</span>
    </div>
    <article>
      <div style="background:#0A0F2C;border-radius:16px;padding:32px;margin-bottom:24px;">
        <div style="color:#FF6B00;font-size:0.75rem;font-weight:700;letter-spacing:0.05em;margin-bottom:8px;">{affair.get('category', '').upper()} • {today}</div>
        <h1 style="font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;color:#fff;line-height:1.2;margin-bottom:12px;">{affair.get('title', '')}</h1>
        <div style="color:#9BA3B8;font-size:0.75rem;">Exam Relevance: <strong style="color:#FF8C33;">{affair.get('exam_relevance', 'All Exams')}</strong></div>
      </div>
      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:12px;">Summary</h2>
        <p style="color:#1A1F35;font-size:0.95rem;line-height:1.7;">{affair.get('summary', '')}</p>
      </div>
      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:16px;">📌 Key Facts for Exam</h2>
        <ul style="list-style:none;padding:0;">{facts_html}</ul>
      </div>
      <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_TOP}" data-ad-format="auto"></ins>
    </article>
  </main>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</body>
</html>"""
    return slug, html


# ─── SITE BUILDER ─────────────────────────────────────────────────────────────

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
        subprocess.run(["git", "commit", "-m", message], cwd=SITE_ROOT, check=True)
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

    processed  = load_processed()
    new_pages  = 0
    failed_src = []

    # Sort by priority (1 = highest) so most important sources process first
    for source in sorted(SOURCES, key=lambda s: s.get("priority", 9)):
        dept = source["dept"]
        url  = source["url"]
        print(f"\n[FETCH] {dept}")
        print(f"  URL: {url}")

        if source["type"] == "rss":
            items = scrape_rss(url, dept, fallback_url=source.get("fallback_url"))
        else:
            items = scrape_html(url, dept)

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
                    save_page(slug, html, "jobs")
                    new_pages += 1
            else:
                affairs = formatted if isinstance(formatted, list) else [formatted]
                for affair in affairs:
                    slug, html = generate_affairs_html(affair)
                    save_page(slug, html, "current-affairs")
                    new_pages += 1

            processed.add(item_hash)

    save_processed(processed)

    print(f"\n{'='*60}")
    print(f"✅ Done — {new_pages} new pages generated")
    if failed_src:
        print(f"⚠  Failed sources ({len(failed_src)}): {', '.join(failed_src)}")
    print(f"{'='*60}\n")

    rebuild_jobs_listing()
    rebuild_affairs_listing()
    rebuild_syllabus()

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
                <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--navy);">{job['title']}</div>
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
            <span style="background:var(--navy);color:var(--white);padding:5px 14px;border-radius:6px;font-size:0.78rem;font-weight:600;">Apply Now →</span>
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
    tab_buttons = \'\n          \'.join(
        f\'<button class="stab{\'  stab-active\' if i==0 else \'\'}" \'
        f\'onclick="filterSyllabus(\'{c[0]}\',this)">{c[2]} {c[1]}</button>\'
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
</body>
</html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[SYLLABUS] ✅ Written syllabus/index.html ({total} jobs, {len(CATS)} categories)")

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
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
</head>
<body>
  <nav class="nav-bar">
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
          <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--navy);margin-bottom:14px;">🔍 Filter by Category</div>
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
          <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
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
            <li><a href="/results/">Results</a></li>
            <li><a href="/admit-card/">Admit Cards</a></li>
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
          <div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--navy);margin-bottom:6px;line-height:1.3;">{item['title']}</div>
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
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <style>
    .affairs-card {{background:var(--white);border-radius:12px;border:1.5px solid var(--grey-200);padding:20px;display:flex;gap:16px;text-decoration:none;color:inherit;transition:all 0.25s;}}
    .affairs-card:hover {{border-color:var(--saffron);box-shadow:0 4px 20px rgba(255,107,0,0.1);transform:translateY(-1px);}}
    .cat-pill {{font-size:0.68rem;font-weight:700;padding:3px 8px;border-radius:4px;letter-spacing:0.04em;white-space:nowrap;}}
    .cat-economy {{background:#E8F5E9;color:#2E7D32;}}
    .cat-science {{background:#E3F2FD;color:#1565C0;}}
    .cat-international {{background:#F3E5F5;color:#6A1B9A;}}
    .cat-sports {{background:#FFF3E0;color:#E65100;}}
    .cat-awards {{background:#FCE4EC;color:#AD1457;}}
    .cat-government {{background:#E0F2F1;color:#00695C;}}
    .cat-environment {{background:#F1F8E9;color:#33691E;}}
  </style>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/" class="active">Current Affairs</a></li>
        <li><a href="/results/">Results</a></li>
        <li><a href="/admit-card/">Admit Card</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
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
</body>
</html>"""

    with open(SITE_ROOT / "current-affairs" / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ /current-affairs/index.html rebuilt with {count} items")


if __name__ == "__main__":
    run()

