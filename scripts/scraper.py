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
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "ca-pub-XXXXXXXXXX")
ADSENSE_SLOT_TOP = os.environ.get("ADSENSE_SLOT_TOP", "XXXXXXXXXX")
ADSENSE_SLOT_MID = os.environ.get("ADSENSE_SLOT_MID", "XXXXXXXXXX")
SITE_ROOT = Path(__file__).parent.parent  # root of your site repo

SOURCES = [
    # Job sources (verified working)
    {"url": "https://www.freejobalert.com/feed/", "type": "rss", "dept": "FreeJobAlert"},
    {"url": "https://www.sarkarinaukriblog.com/feeds/posts/default?alt=rss", "type": "rss", "dept": "Sarkari Naukri"},
    {"url": "https://www.indgovtjobs.in/feeds/posts/default?alt=rss", "type": "rss", "dept": "Govt Jobs"},
    {"url": "https://www.employmentnews.gov.in/feed/", "type": "rss", "dept": "Employment News"},
    {"url": "https://www.ncs.gov.in/rss-feed/jobs", "type": "rss", "dept": "NCS Jobs"},
    # Current affairs / news sources (verified working)
    {"url": "https://pib.gov.in/RSSNewRelease.aspx", "type": "rss", "dept": "PIB"},
    {"url": "https://newsonair.gov.in/rss.aspx", "type": "rss", "dept": "News on Air"},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "type": "rss", "dept": "The Hindu"},
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
  <!-- Google Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
  </script>
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
      <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_TOP}" data-ad-format="auto"></ins>

      <!-- Disclaimer -->
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

    # Always rebuild listing pages and sitemap (even if no new pages,
    # to keep counts and dates fresh)
    rebuild_jobs_listing()
    rebuild_affairs_listing()

    # Regenerate sitemap
    try:
        import importlib.util, sys
        sitemap_path = SITE_ROOT / "scripts" / "sitemap_gen.py"
        spec = importlib.util.spec_from_file_location("sitemap_gen", sitemap_path)
        sitemap_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sitemap_mod)
        sitemap_mod.run()
    except Exception as e:
        print(f"[SITEMAP] Error: {e}")

    # Push to GitHub (Cloudflare Pages auto-deploys)
    if new_pages > 0:
        today = date.today().strftime("%d %b %Y")
        git_push(f"Auto: {new_pages} new pages — {today}")
    else:
        # Still push listing + sitemap updates even if no new job pages
        git_push(f"Auto: Refresh listings & sitemap — {date.today().strftime('%d %b %Y')}")


# ─── LISTING PAGE REBUILDER ───────────────────────────────────────────────────

def get_job_meta_from_html(html_path):
    """Extract job metadata from a generated job detail page."""
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        from bs4 import BeautifulSoup
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
                key = cells[0].get_text(strip=True).lower()
                val = cells[1].get_text(strip=True)
                data[key] = val

        slug = html_path.parent.name
        last_date = data.get("last date", "N/A")
        vacancies = data.get("total vacancies", "N/A")
        salary = data.get("salary / pay scale", "N/A")
        location = data.get("location", "All India")
        qualification = data.get("qualification", "N/A")

        # Determine badge/category from qualification
        qual_lower = qualification.lower()
        if "engineer" in qual_lower or "b.tech" in qual_lower or "b.e" in qual_lower:
            category = "Engineering"
            cat_key = "engineering"
        elif "post graduate" in qual_lower or "master" in qual_lower or "mba" in qual_lower:
            category = "Post Graduate"
            cat_key = "state"
        elif "graduate" in qual_lower or "degree" in qual_lower or "b.sc" in qual_lower or "b.com" in qual_lower or "ba" in qual_lower:
            category = "Graduate"
            cat_key = "graduate"
        elif "12th" in qual_lower or "intermediate" in qual_lower or "hsc" in qual_lower:
            category = "12th Pass"
            cat_key = "12th"
        elif "10th" in qual_lower or "matriculation" in qual_lower or "ssc" in qual_lower:
            category = "10th Pass"
            cat_key = "10th"
        else:
            category = "Graduate"
            cat_key = "graduate"

        # Infer exam category from title/dept
        title_dept = (title + " " + dept).lower()
        if any(x in title_dept for x in ["ssc", "cgl", "chsl", "mts", "gd constable"]):
            tab_cat = "ssc"
        elif any(x in title_dept for x in ["railway", "rrb", "ntpc", "group d", "loco"]):
            tab_cat = "railway"
        elif any(x in title_dept for x in ["bank", "sbi", "ibps", "rbi", "nabard", "exim"]):
            tab_cat = "banking"
        elif any(x in title_dept for x in ["upsc", "ias", "ips", "civil service", "nda", "cds", "capf"]):
            tab_cat = "upsc"
        elif any(x in title_dept for x in ["army", "navy", "air force", "defence", "agniveer", "military"]):
            tab_cat = "defence"
        elif any(x in title_dept for x in ["police", "constable", "crpf", "bsf", "cisf", "itbp"]):
            tab_cat = "police"
        elif any(x in title_dept for x in ["teacher", "teaching", "professor", "lecturer", "kvs", "nvs"]):
            tab_cat = "teaching"
        else:
            tab_cat = "state"

        # Emoji icon by category
        emoji_map = {
            "ssc": "📋", "railway": "🚂", "banking": "🏦",
            "upsc": "🏛️", "defence": "🪖", "police": "👮",
            "teaching": "📚", "state": "🏢"
        }

        return {
            "slug": slug,
            "title": title,
            "dept": dept,
            "last_date": last_date,
            "vacancies": vacancies,
            "salary": salary,
            "location": location,
            "category": category,
            "tab_cat": tab_cat,
            "emoji": emoji_map.get(tab_cat, "📋"),
        }
    except Exception as e:
        print(f"[META] Error reading {html_path}: {e}")
        return None


def build_job_card(job):
    """Generate HTML for a single job card."""
    urgency_badge = ""
    ld = job.get("last_date", "N/A")
    if ld != "N/A":
        try:
            from datetime import datetime
            for fmt in ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    ld_date = datetime.strptime(ld, fmt).date()
                    days_left = (ld_date - date.today()).days
                    if days_left <= 7:
                        urgency_badge = '<span class="badge badge-urgent">🔥 URGENT</span>'
                    else:
                        urgency_badge = '<span class="badge badge-new">🟢 NEW</span>'
                    break
                except:
                    continue
        except:
            urgency_badge = '<span class="badge badge-new">🟢 NEW</span>'
    else:
        urgency_badge = '<span class="badge badge-new">🟢 NEW</span>'

    return f"""
          <a href="/jobs/{job['slug']}/" class="card fade-up" style="text-decoration:none; color:inherit; display:block; position:relative; overflow:hidden;" data-category="{job['tab_cat']}">
            <div style="position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--saffron);"></div>
            <div style="padding-left:12px;">
              <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:10px;">
                <div style="display:flex; gap:10px; align-items:flex-start; flex:1;">
                  <div style="width:42px; height:42px; border-radius:10px; background:var(--saffron-pale); display:flex; align-items:center; justify-content:center; font-size:1.1rem; flex-shrink:0;">{job['emoji']}</div>
                  <div>
                    <div style="font-size:0.72rem; color:var(--grey-400); font-weight:500; margin-bottom:2px;">{job['dept']}</div>
                    <div style="font-family:var(--font-display); font-size:1rem; font-weight:700; color:var(--navy);">{job['title']}</div>
                  </div>
                </div>
                <div style="display:flex; flex-direction:column; gap:4px; flex-shrink:0;">
                  {urgency_badge}
                  <span class="badge badge-category">{job['category']}</span>
                </div>
              </div>
              <div style="display:flex; gap:16px; flex-wrap:wrap;">
                <span style="font-size:0.8rem; color:var(--grey-700);">👥 {job['vacancies']}</span>
                <span style="font-size:0.8rem; color:var(--grey-700);">📍 {job['location']}</span>
                <span style="font-size:0.8rem; color:var(--grey-700);">💰 {job['salary']}</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; padding-top:12px; border-top:1px solid var(--grey-200);">
                <span style="font-size:0.8rem; color:#E65100; font-weight:600;">⏰ Last Date: {job['last_date']}</span>
                <span style="background:var(--navy); color:var(--white); padding:5px 14px; border-radius:6px; font-size:0.78rem; font-weight:600;">Apply Now →</span>
              </div>
            </div>
          </a>"""


def rebuild_jobs_listing():
    """Scan all job pages and rebuild /jobs/index.html dynamically."""
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

    print(f"[LISTING] Rebuilding jobs listing with {len(jobs)} jobs")

    cards_html = "\n".join(build_job_card(j) for j in jobs)
    count = len(jobs)
    today_year = datetime.now().year

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Latest Govt Jobs {today_year} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="All latest govt job notifications {today_year}. Browse SSC, Railway, Banking, UPSC, Defence, Police jobs. Daily updated, free alerts.">
  <link rel="canonical" href="https://naukribulletin.in/jobs/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <!-- Google Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
  </script>
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

  <div style="background:var(--navy); padding:40px 20px;">
    <div style="max-width:1200px; margin:0 auto;">
      <div style="color:var(--grey-400); font-size:0.8rem; margin-bottom:8px;">
        <a href="/" style="color:var(--grey-400); text-decoration:none;">Home</a> › Latest Jobs
      </div>
      <h1 style="font-family:var(--font-display); font-size:2rem; font-weight:800; color:var(--white); margin-bottom:8px;">
        Latest <span style="color:var(--saffron);">Govt Jobs {today_year}</span>
      </h1>
      <p style="color:var(--grey-400); font-size:0.95rem;">{count}+ active notifications — updated daily by AI</p>
    </div>
  </div>

  <div style="max-width:1200px; margin:0 auto; padding:0 20px;">
    <div class="ad-slot ad-banner">Advertisement</div>
  </div>

  <div class="container">
    <div class="two-col">
      <section>
        <div class="filter-tabs">
          <div class="tab active" onclick="filterJobs('all', this)">All</div>
          <div class="tab" onclick="filterJobs('ssc', this)">SSC</div>
          <div class="tab" onclick="filterJobs('railway', this)">Railway</div>
          <div class="tab" onclick="filterJobs('banking', this)">Banking</div>
          <div class="tab" onclick="filterJobs('upsc', this)">UPSC</div>
          <div class="tab" onclick="filterJobs('defence', this)">Defence</div>
          <div class="tab" onclick="filterJobs('police', this)">Police</div>
          <div class="tab" onclick="filterJobs('teaching', this)">Teaching</div>
          <div class="tab" onclick="filterJobs('state', this)">State PSC</div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <span style="font-size:0.85rem; color:var(--grey-700);">Showing <strong id="job-count">{count}</strong> jobs</span>
          <select id="sort-select" onchange="sortJobs(this.value)" style="font-family:var(--font-body); font-size:0.82rem; border:1.5px solid var(--grey-200); border-radius:6px; padding:5px 10px; background:var(--white); color:var(--text);">
            <option value="newest">Newest First</option>
            <option value="urgent">Last Date (Urgent)</option>
          </select>
        </div>
        <div id="jobs-list" style="display:flex; flex-direction:column; gap:12px;">
{cards_html}
        </div>
      </section>

      <aside class="sidebar">
        <div class="telegram-cta">
          <h3>📢 Free Job Alerts</h3>
          <p>Get daily alerts on Telegram</p>
          <a href="https://t.me/naukribulletin" class="telegram-btn">Join Channel →</a>
        </div>
        <div class="card">
          <div style="font-family:var(--font-display); font-size:1rem; font-weight:700; color:var(--navy); margin-bottom:14px;">🔍 Filter by Category</div>
          <select onchange="filterJobs(this.value, null)" style="width:100%; font-family:var(--font-body); font-size:0.85rem; border:1.5px solid var(--grey-200); border-radius:8px; padding:8px 12px; color:var(--text); background:var(--white);">
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
          <p>India's smartest govt job portal. AI-powered daily job alerts, current affairs and exam updates — always free.</p>
        </div>
        <div class="footer-col">
          <h4>Jobs by Dept</h4>
          <ul>
            <li><a href="/jobs/">SSC Jobs</a></li>
            <li><a href="/jobs/">Railway Jobs</a></li>
            <li><a href="/jobs/">Banking Jobs</a></li>
            <li><a href="/jobs/">UPSC Jobs</a></li>
            <li><a href="/jobs/">Defence Jobs</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Resources</h4>
          <ul>
            <li><a href="/results/">Results</a></li>
            <li><a href="/admit-card/">Admit Cards</a></li>
            <li><a href="/syllabus/">Syllabus</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Current Affairs</h4>
          <ul>
            <li><a href="/current-affairs/">Daily Updates</a></li>
            <li><a href="/current-affairs/">Economy</a></li>
            <li><a href="/current-affairs/">Science & Tech</a></li>
            <li><a href="/current-affairs/">International</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <p>© {today_year} NaukriBulletin.in — All Rights Reserved</p>
        <p>
          <a href="/privacy/" style="color:var(--grey-400); text-decoration:none; margin-right:16px;">Privacy Policy</a>
          <a href="/disclaimer/" style="color:var(--grey-400); text-decoration:none;">Disclaimer</a>
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
        if (category === 'all' || card.dataset.category === category) {{
          card.style.display = 'block';
          count++;
        }} else {{
          card.style.display = 'none';
        }}
      }});
      document.getElementById('job-count').textContent = count;
    }}

    function sortJobs(val) {{
      const list = document.getElementById('jobs-list');
      const cards = Array.from(list.querySelectorAll('a'));
      if (val === 'urgent') {{
        cards.sort((a, b) => {{
          const dateA = a.querySelector('span[style*="E65100"]')?.textContent || '';
          const dateB = b.querySelector('span[style*="E65100"]')?.textContent || '';
          return dateA.localeCompare(dateB);
        }});
        cards.forEach(c => list.appendChild(c));
      }}
    }}
  </script>
</body>
</html>"""

    output_path = SITE_ROOT / "jobs" / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ Rebuilt /jobs/index.html with {count} jobs")


def get_affairs_meta_from_html(html_path):
    """Extract current affairs metadata from a generated detail page."""
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        slug = html_path.parent.name

        # Extract category from the orange header div
        cat_div = soup.find(style=lambda s: s and "FF6B00" in str(s) and "letter-spacing" in str(s))
        category_raw = cat_div.get_text(strip=True) if cat_div else "General"
        # Strip date portion (e.g. "ECONOMY • 03 June 2026" -> "Economy")
        category = category_raw.split("•")[0].strip().title() if "•" in category_raw else category_raw.strip().title()

        # Extract exam relevance
        exam_tag = soup.find(style=lambda s: s and "FF8C33" in str(s))
        exam_rel = exam_tag.get_text(strip=True) if exam_tag else "All Exams"

        # Extract summary
        summary_p = soup.find("p", style=lambda s: s and "1.7" in str(s))
        summary = summary_p.get_text(strip=True)[:120] + "..." if summary_p else ""

        # Date from file modification time
        from datetime import datetime
        mtime = html_path.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%d %b")

        cat_lower = category.lower()
        cat_class_map = {
            "economy": "cat-economy",
            "science": "cat-science",
            "international": "cat-international",
            "sports": "cat-sports",
            "awards": "cat-awards",
            "government": "cat-government",
            "environment": "cat-environment",
        }
        cat_class = next((v for k, v in cat_class_map.items() if k in cat_lower), "cat-government")

        return {
            "slug": slug,
            "title": title,
            "category": category,
            "cat_class": cat_class,
            "exam_rel": exam_rel,
            "summary": summary,
            "date_str": date_str,
        }
    except Exception as e:
        print(f"[META] Error reading {html_path}: {e}")
        return None


def rebuild_affairs_listing():
    """Scan all current-affairs pages and rebuild /current-affairs/index.html."""
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

    print(f"[LISTING] Rebuilding current affairs listing with {len(items)} items")

    cards_html = ""
    for item in items:
        date_parts = item['date_str'].split(" ")
        day = date_parts[0] if date_parts else ""
        month = date_parts[1] if len(date_parts) > 1 else ""
        cards_html += f"""
          <a href="/current-affairs/{item['slug']}/" class="affairs-card fade-up" style="text-decoration:none; color:inherit;">
            <div style="background:var(--navy); border-radius:8px; padding:8px 10px; text-align:center; min-width:48px; color:var(--white); flex-shrink:0;">
              <div style="font-family:var(--font-display); font-size:1.2rem; font-weight:800; line-height:1;">{day}</div>
              <div style="font-size:0.65rem; opacity:0.7; text-transform:uppercase;">{month}</div>
            </div>
            <div style="flex:1; min-width:0;">
              <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:8px;">
                <span class="cat-pill {item['cat_class']}">{item['category'].upper()}</span>
                <span style="font-size:0.72rem; color:var(--grey-400);">📚 {item['exam_rel']}</span>
              </div>
              <div style="font-family:var(--font-display); font-size:0.95rem; font-weight:700; color:var(--navy); margin-bottom:6px; line-height:1.3;">{item['title']}</div>
              <p style="font-size:0.82rem; color:var(--grey-700); line-height:1.5; margin:0;">{item['summary']}</p>
            </div>
          </a>"""

    today_year = datetime.now().year
    count = len(items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Current Affairs {today_year} for UPSC, SSC, Banking | NaukriBulletin</title>
  <meta name="description" content="Daily current affairs {today_year} for UPSC, SSC, Railway, Banking exams. Economy, Science, International, Sports, Awards — AI-summarized exam-ready notes.">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <style>
    .affairs-card {{ background:var(--white); border-radius:12px; border:1.5px solid var(--grey-200); padding:20px; display:flex; gap:16px; text-decoration:none; color:inherit; transition:all 0.25s; }}
    .affairs-card:hover {{ border-color:var(--saffron); box-shadow:0 4px 20px rgba(255,107,0,0.1); transform:translateY(-1px); }}
    .cat-pill {{ font-size:0.68rem; font-weight:700; padding:3px 8px; border-radius:4px; letter-spacing:0.04em; white-space:nowrap; }}
    .cat-economy {{ background:#E8F5E9; color:#2E7D32; }}
    .cat-science {{ background:#E3F2FD; color:#1565C0; }}
    .cat-international {{ background:#F3E5F5; color:#6A1B9A; }}
    .cat-sports {{ background:#FFF3E0; color:#E65100; }}
    .cat-awards {{ background:#FCE4EC; color:#AD1457; }}
    .cat-government {{ background:#E0F2F1; color:#00695C; }}
    .cat-environment {{ background:#F1F8E9; color:#33691E; }}
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

  <div style="background:var(--navy); padding:40px 20px;">
    <div style="max-width:1200px; margin:0 auto;">
      <div style="color:var(--grey-400); font-size:0.8rem; margin-bottom:8px;">
        <a href="/" style="color:var(--grey-400); text-decoration:none;">Home</a> › Current Affairs
      </div>
      <h1 style="font-family:var(--font-display); font-size:2rem; font-weight:800; color:var(--white); margin-bottom:8px;">
        Daily <span style="color:var(--saffron);">Current Affairs {today_year}</span>
      </h1>
      <p style="color:var(--grey-400); font-size:0.95rem;">{count}+ articles — exam-ready summaries updated daily by AI</p>
    </div>
  </div>

  <div class="container">
    <div class="two-col">
      <section>
        <div style="display:flex; flex-direction:column; gap:12px;">
{cards_html}
        </div>
      </section>
      <aside class="sidebar">
        <div class="telegram-cta">
          <h3>📢 Free Alerts</h3>
          <p>Daily current affairs on Telegram</p>
          <a href="https://t.me/naukribulletin" class="telegram-btn">Join Channel →</a>
        </div>
        <div class="ad-slot ad-sidebar">Advertisement</div>
      </aside>
    </div>
  </div>

  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© {today_year} NaukriBulletin.in — All Rights Reserved</p>
      </div>
    </div>
  </footer>
</body>
</html>"""

    output_path = SITE_ROOT / "current-affairs" / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ Rebuilt /current-affairs/index.html with {count} items")


if __name__ == "__main__":
    run()
