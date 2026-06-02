# NaukriBulletin 🇮🇳

India's AI-powered govt job notification portal — fully automated, zero hosting cost.

## Stack
- **Hosting**: Cloudflare Pages (free)
- **Domain**: Namecheap .in
- **Automation**: GitHub Actions (free)
- **AI**: Groq API (free) + Gemini fallback (free)
- **Total cost**: ~₹700/year (domain only)

---

## Project Structure

```
naukribulletin/
├── index.html                  # Homepage
├── jobs/
│   └── index.html              # Jobs listing page
│   └── [slug]/index.html       # Auto-generated job detail pages
├── current-affairs/
│   └── index.html              # CA listing page
│   └── [slug]/index.html       # Auto-generated CA detail pages
├── results/
│   └── index.html
├── admit-card/
│   └── index.html
├── css/
│   └── style.css               # Global styles
├── scripts/
│   ├── scraper.py              # Main automation script
│   ├── sitemap_gen.py          # Sitemap generator
│   ├── telegram_notify.py      # Telegram channel notifier
│   ├── requirements.txt
│   └── processed.json          # Tracks processed items (auto-created)
├── .github/
│   └── workflows/
│       └── daily-update.yml    # Runs scraper daily via GitHub Actions
├── sitemap.xml                 # Auto-generated
├── robots.txt                  # Auto-generated
├── _redirects                  # Cloudflare Pages redirects
└── 404.html                    # Custom error page
```

---

## Setup Guide

### Step 1 — Domain & Cloudflare
1. Buy domain on Namecheap (e.g. `naukribulletin.in`) — ~₹700/year
2. Add site to Cloudflare (free plan)
3. Update nameservers on Namecheap → Cloudflare ones
4. In Cloudflare Pages: Connect GitHub repo → set build as "None" (static site)

### Step 2 — GitHub Repo
```bash
git init
git add .
git commit -m "Initial site"
git remote add origin https://github.com/YOUR_USERNAME/naukribulletin
git push -u origin main
```

### Step 3 — GitHub Secrets
Go to repo → Settings → Secrets → Actions, add:
- `GROQ_API_KEY` — from console.groq.com (free)
- `GEMINI_API_KEY` — from aistudio.google.com (free)
- `TELEGRAM_BOT_TOKEN` — from @BotFather on Telegram
- `TELEGRAM_CHANNEL_ID` — your channel ID (e.g. @naukribulletin)

### Step 4 — AdSense
1. Apply at adsense.google.com after ~20-30 pages indexed
2. Replace `ca-pub-XXXXXXXXXX` and slot IDs in HTML files
3. One approval covers all auto-generated pages

### Step 5 — Telegram Channel
1. Create channel on Telegram (e.g. @NaukriBulletinOfficial)
2. Add your bot as admin
3. Update `TELEGRAM_CHANNEL_ID` in secrets

---

## Automation Flow

```
Daily 6:30 AM IST
        ↓
GitHub Actions triggers scraper.py
        ↓
Scrapes 9+ govt sources (RSS + HTML)
        ↓
Groq AI extracts structured job data
        ↓
Gemini fallback if Groq fails
        ↓
HTML pages generated from templates
        ↓
Git commit + push to GitHub
        ↓
Cloudflare Pages auto-deploys (2-3 min)
        ↓
Telegram digest sent to channel
        ↓
Sitemap updated for Google crawling
```

---

## Revenue Milestones

| Monthly Pageviews | Estimated Revenue |
|---|---|
| 50,000 | ₹5,000 – ₹8,000 |
| 2,00,000 | ₹20,000 – ₹35,000 |
| 5,00,000 | ₹50,000 – ₹80,000 |
| 10,00,000 | ₹1,00,000 – ₹1,80,000 |

Additional streams: Telegram sponsorships, coaching institute ads, PDF downloads.

---

## SEO Strategy

- Each job gets its own URL: `/jobs/ssc-cgl-2025/`
- Long-tail keywords auto-targeted: "SSC CGL 2025 UP vacancy graduate"
- Sitemap auto-regenerated after every update
- 50-100 new indexed pages per day

---

## Adding New Sources

Edit `SOURCES` list in `scripts/scraper.py`:

```python
{"url": "https://new-source.gov.in/rss.xml", "type": "rss", "dept": "Department Name"},
```

---

## Local Testing

```bash
cd scripts
pip install -r requirements.txt
export GROQ_API_KEY="your_key_here"
export GEMINI_API_KEY="your_key_here"
python scraper.py
```

---

## License
MIT — feel free to use and modify.
