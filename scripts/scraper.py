#!/usr/bin/env python3
"""
NaukriBulletin — Automated Job Scraper & Site Generator
Uses Groq (free) with Gemini fallback to extract and format job data
Pushes generated HTML to GitHub → Cloudflare Pages auto-deploys
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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SITE_ROOT = Path(__file__).parent.parent  # root of your site repo

SOURCES = [
    # Central Govt
    {"url": "https://ssc.nic.in/SSCFileServer/PortalManagement/UploadedFiles/advtnoticesscnews.xml", "type": "rss", "dept": "SSC"},
    {"url": "https://www.rrbcdg.gov.in/", "type": "html", "dept": "Railway"},
    {"url": "https://www.ibps.in/", "type": "html", "dept": "Banking"},
    {"url": "https://upsc.gov.in/", "type": "html", "dept": "UPSC"},
    {"url": "https://joinindianarmy.nic.in/", "type": "html", "dept": "Army"},
    {"url": "https://www.ncs.gov.in/", "type": "html", "dept": "NCS"},
    # Employment News RSS
    {"url": "https://www.employmentnews.gov.in/RSS/EnglishRSS.xml", "type": "rss", "dept": "Employment News"},
    # PIB for current affairs
    {"url": "https://pib.gov.in/RSSNewRelease.aspx", "type": "rss", "dept": "PIB"},
    {"url": "https://newsonair.gov.in/rss.aspx", "type": "rss", "dept": "News on Air"},
]

GROQ_MODELS = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192"]
GEMINI_MODEL = "gemini-1.5-flash"

PROCESSED_FILE = SITE_ROOT / "scripts" / "processed.json"


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def load_processed():
    """Load set of already-processed item hashes."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(hashes):
    """Save set of processed item hashes."""
    PROCESSED_FILE.parent.mkdir(exist_ok=True)
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(hashes), f)


def make_hash(text):
    """Create a short hash for deduplication."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def make_slug(title):
    """Convert title to URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug[:60]


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

def scrape_rss(url, dept):
    """Fetch and parse RSS feed."""
    items = []
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "NaukriBulletin/1.0"})
        soup = BeautifulSoup(resp.content, "xml")
        for item in soup.find_all("item")[:20]:
            items.append({
                "title": item.find("title").get_text(strip=True) if item.find("title") else "",
                "description": item.find("description").get_text(strip=True) if item.find("description") else "",
                "link": item.find("link").get_text(strip=True) if item.find("link") else "",
                "pubDate": item.find("pubDate").get_text(strip=True) if item.find("pubDate") else "",
                "dept": dept,
                "source_url": url,
            })
    except Exception as e:
        print(f"[SCRAPER] RSS error {url}: {e}")
    return items


def scrape_html(url, dept):
    """Fetch and extract text from HTML page."""
    items = []
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "NaukriBulletin/1.0"})
        soup = BeautifulSoup(resp.content, "html.parser")
        # Remove scripts/styles
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        # Get text chunks that look like job notices
        text = soup.get_text(separator="\n")
        # Basic chunking — AI will clean up
        items.append({
            "title": f"Latest from {dept}",
            "description": text[:3000],  # first 3000 chars
            "link": url,
            "pubDate": str(date.today()),
            "dept": dept,
            "source_url": url,
        })
    except Exception as e:
        print(f"[SCRAPER] HTML error {url}: {e}")
    return items


# ─── AI FORMATTER ─────────────────────────────────────────────────────────────

JOB_PROMPT = """You are a govt job notification formatter for India.
Extract job details from the raw text below and return ONLY valid JSON, no other text.

Raw text: {raw_text}
Department hint: {dept}

Return this exact JSON structure (fill with "N/A" if not found):
{{
  "is_job_notification": true/false,
  "title": "Full job title",
  "department": "Full department name",
  "vacancies": "Number or N/A",
  "qualification": "Educational qualification required",
  "age_limit": "Age range e.g. 18-25 years",
  "last_date": "DD Month YYYY or N/A",
  "salary": "Salary range in rupees",
  "state": "All India or specific state",
  "category": "10th Pass / 12th Pass / Graduate / Post Graduate / Engineering",
  "apply_link": "Direct application URL",
  "summary": "2 simple sentences about this job in plain English",
  "meta_description": "SEO description under 155 characters",
  "exam_relevance": "Which exams this relates to e.g. SSC CGL, Railway NTPC",
  "slug": "url-friendly-slug-for-this-job"
}}"""


AFFAIRS_PROMPT = """You are a current affairs formatter for Indian competitive exam students.
Extract key news items from the raw text below and return ONLY valid JSON array, no other text.

Raw text: {raw_text}

Return a JSON array of news items (max 5), each with:
{{
  "title": "Clear news headline",
  "category": "Economy / Science & Tech / International / Sports / Awards / Government Schemes / Environment",
  "summary": "2-3 sentences explaining why this matters for exams",
  "key_facts": ["fact1", "fact2", "fact3"],
  "exam_relevance": "UPSC / SSC / Banking / All",
  "slug": "url-friendly-slug"
}}"""


def call_groq(prompt, model=None):
    """Call Groq API."""
    models = [model] if model else GROQ_MODELS
    for m in models:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": m,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.1,
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[GROQ] Error with {m}: {e}")
    return None


def call_gemini(prompt):
    """Call Gemini API as fallback."""
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[GEMINI] Error: {e}")
    return None


def extract_json(text):
    """Safely extract JSON from AI response."""
    if not text:
        return None
    # Strip markdown code fences
    text = re.sub(r'```json|```', '', text).strip()
    try:
        return json.loads(text)
    except:
        # Try to find JSON within the text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None


def format_with_ai(item, content_type="job"):
    """Format raw scraped item using Groq → Gemini fallback."""
    raw_text = f"{item.get('title', '')} {item.get('description', '')}"[:2000]
    dept = item.get("dept", "")

    if content_type == "job":
        prompt = JOB_PROMPT.format(raw_text=raw_text, dept=dept)
    else:
        prompt = AFFAIRS_PROMPT.format(raw_text=raw_text)

    # Try Groq first
    result = call_groq(prompt)
    if not result:
        print("[AI] Groq failed, trying Gemini fallback...")
        result = call_gemini(prompt)

    return extract_json(result)


# ─── HTML GENERATORS ──────────────────────────────────────────────────────────

def generate_job_html(job, template_path=None):
    """Generate a job detail HTML page."""
    slug = job.get("slug") or make_slug(job.get("title", "job"))
    today = datetime.now().strftime("%d %B %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{job.get('title', 'Govt Job')} — NaukriBulletin</title>
  <meta name="description" content="{job.get('meta_description', '')}">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;font-size:0.85rem;">← All Jobs</a>
    </div>
  </nav>

  <!-- Ad Banner -->
  <div style="max-width:900px;margin:20px auto;padding:0 20px;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="auto"></ins>
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

      <!-- Job Details Table -->
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

      <!-- Apply Button -->
      <div style="text-align:center;margin:32px 0;">
        <a href="{job.get('apply_link', '#')}" target="_blank" rel="nofollow noopener"
           style="background:#FF6B00;color:#fff;padding:14px 40px;border-radius:10px;font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;text-decoration:none;display:inline-block;">
          Apply Online →
        </a>
        <p style="margin-top:10px;font-size:0.78rem;color:#9BA3B8;">You will be redirected to the official website</p>
      </div>

      <!-- Ad -->
      <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="auto"></ins>

      <!-- Disclaimer -->
      <div style="background:#FFF3E8;border-left:4px solid #FF6B00;border-radius:0 8px 8px 0;padding:14px 18px;margin-top:24px;">
        <p style="font-size:0.8rem;color:#4A5270;">⚠️ <strong>Disclaimer:</strong> Always verify details from the official website before applying. NaukriBulletin is not responsible for any errors in the notification details.</p>
      </div>

      <p style="font-size:0.75rem;color:#9BA3B8;margin-top:12px;">Last updated: {today}</p>
    </article>
  </main>

  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</body>
</html>"""

    return slug, html


def generate_affairs_html(affair):
    """Generate a current affairs detail HTML page."""
    slug = affair.get("slug") or make_slug(affair.get("title", "news"))
    today = datetime.now().strftime("%d %B %Y")
    key_facts = affair.get("key_facts", [])
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

      <!-- Summary -->
      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:12px;">Summary</h2>
        <p style="color:#1A1F35;font-size:0.95rem;line-height:1.7;">{affair.get('summary', '')}</p>
      </div>

      <!-- Key Facts -->
      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:16px;">📌 Key Facts for Exam</h2>
        <ul style="list-style:none;padding:0;">
          {facts_html}
        </ul>
      </div>

      <!-- Ad -->
      <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-XXXXXXXXXX" data-ad-slot="XXXXXXXXXX" data-ad-format="auto"></ins>

    </article>
  </main>

  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</body>
</html>"""

    return slug, html


# ─── SITE BUILDER ─────────────────────────────────────────────────────────────

def save_page(slug, html, folder):
    """Save an HTML page to the site directory."""
    page_dir = SITE_ROOT / folder / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    output_file = page_dir / "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[SAVED] /{folder}/{slug}/index.html")
    return str(output_file)


def git_push(message="Auto: Daily update"):
    """Stage all changes and push to GitHub."""
    try:
        subprocess.run(["git", "add", "."], cwd=SITE_ROOT, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=SITE_ROOT, check=True)
        subprocess.run(["git", "push"], cwd=SITE_ROOT, check=True)
        print(f"[GIT] Pushed: {message}")
    except subprocess.CalledProcessError as e:
        print(f"[GIT] Push failed: {e}")


# ─── MAIN RUNNER ──────────────────────────────────────────────────────────────

def run():
    print(f"\n{'='*50}")
    print(f"NaukriBulletin Automation — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    processed = load_processed()
    new_pages = 0

    for source in SOURCES:
        print(f"\n[FETCH] {source['dept']} — {source['url']}")

        # Scrape
        if source["type"] == "rss":
            items = scrape_rss(source["url"], source["dept"])
        else:
            items = scrape_html(source["url"], source["dept"])

        print(f"  → Got {len(items)} items")

        for item in items:
            item_hash = make_hash(item.get("title", "") + item.get("description", "")[:100])

            # Skip already processed
            if item_hash in processed:
                continue

            # Determine content type
            is_news_source = source["dept"] in ["PIB", "News on Air"]
            content_type = "affairs" if is_news_source else "job"

            # Format with AI
            print(f"  → AI formatting: {item.get('title', '')[:60]}...")
            time.sleep(0.5)  # Rate limiting
            formatted = format_with_ai(item, content_type)

            if not formatted:
                print("  → AI failed, skipping")
                continue

            # Generate and save HTML
            if content_type == "job":
                # Handle both single job dict and list
                jobs = [formatted] if isinstance(formatted, dict) else formatted
                for job in jobs:
                    if not job.get("is_job_notification", True):
                        continue
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

    # Save processed hashes
    save_processed(processed)

    print(f"\n{'='*50}")
    print(f"✅ Done! Generated {new_pages} new pages")
    print(f"{'='*50}\n")

    # Push to GitHub (Cloudflare Pages auto-deploys)
    if new_pages > 0:
        today = date.today().strftime("%d %b %Y")
        git_push(f"Auto: {new_pages} new pages — {today}")
    else:
        print("[GIT] No new pages, skipping push")


if __name__ == "__main__":
    run()
