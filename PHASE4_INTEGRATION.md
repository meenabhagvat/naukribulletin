# NaukriBulletin Phase 4 — Integration Guide

## Files in this package

```
phase4/
├── _includes/
│   └── affiliate_banners.html      → Coaching affiliate banners
├── .github/workflows/
│   └── scrape-notify.yml           → Updated GitHub Actions (Telegram + OneSignal + WA)
├── telegram_notify.py              → Upgraded notifier (OneSignal + Brevo added)
├── whatsapp_post.py                → New: WhatsApp Channel auto-poster
├── syllabus-pdf/
│   └── index.html                  → PDF download page with Brevo email gate
└── whatsapp/
    └── index.html                  → WhatsApp Channel landing page
```

---

## Step 1 — Affiliate Banners

**Copy file:**
```
_includes/affiliate_banners.html  →  _includes/affiliate_banners.html
```

**Add to job detail pages** (`_layouts/job.html` or wherever job content renders):
```html
<!-- After job description, before comments -->
{% include affiliate_banners.html %}
```

**Get real affiliate links (replace placeholders):**
- **Unacademy:** https://affiliate.unacademy.com — register, get your ref link
- **Testbook:** https://testbook.com/affiliate — partner portal
- **Adda247:** https://www.adda247.com/affiliate — apply as publisher

Revenue: ₹100–500 per signup. With 290+ job pages and high purchase intent, expect 5–15 signups/day at scale.

---

## Step 2 — PDF Syllabus Downloads + Brevo Email Gate

**Copy file:**
```
syllabus-pdf/index.html  →  syllabus-pdf/index.html
```

**Add to `_config.yml`:**
```yaml
brevo_api_key: "YOUR_BREVO_V3_API_KEY"
```

Or better — inject via GitHub Actions as an env var and use a Liquid variable set in the build step.

**Brevo setup (free tier = 300 emails/day, unlimited contacts):**
1. Sign up at brevo.com (free)
2. API Keys → Generate v3 key
3. Lists → Create "Syllabus Downloads" list → note the ID (put as `listIds: [YOUR_ID]`)
4. Create PDF files and place at `/assets/pdf/` in your repo

**Create actual PDFs:**
Upload the official PDFs to `/assets/pdf/` directory:
```
assets/pdf/ssc-cgl-syllabus-2025.pdf
assets/pdf/rrb-ntpc-syllabus-2025.pdf
```
(Download official PDFs from ssc.gov.in / indianrailways.gov.in)

---

## Step 3 — OneSignal Auto-Push (telegram_notify.py upgrade)

**Copy file:**
```
telegram_notify.py  →  telegram_notify.py  (REPLACE existing file)
```

**Get REST API key from OneSignal:**
1. OneSignal Dashboard → Your App → Settings → Keys & IDs
2. Copy **REST API Key** (not App ID)

**Add GitHub Secret:**
```
ONESIGNAL_REST_KEY = <your REST API key>
```
(ONESIGNAL_APP_ID is already in your code — add it as secret too for cleanliness)

**The notifier now:**
- Sends Telegram message for each new job (same as before)
- Sends OneSignal push for the FIRST new job per run (prevents notification fatigue)
- Optionally fires Brevo email digest if 3+ new jobs found
- Saves notified IDs to `_data/notified_ids.json` to avoid duplicates

---

## Step 4 — WhatsApp Channel

### One-time setup:

1. **Create WhatsApp Channel:**
   - Open WhatsApp → Updates tab → `+` → New Channel
   - Name: `NaukriBulletin` | Description: Daily Govt Job Alerts
   - Get your **Channel Invite Link** (share link)

2. **Meta Developer App:**
   - Go to developers.facebook.com → Create App → Business
   - Add WhatsApp product
   - Copy: Phone Number ID, create Permanent Token (System User)
   - Note: WABA ID (WhatsApp Business Account ID)

3. **Add GitHub Secrets:**
   ```
   WA_PHONE_NUMBER_ID      = 123456789012345
   WA_ACCESS_TOKEN         = EAAxxxxxxx...
   WA_CHANNEL_ID           = <channel recipient phone number>
   WA_BUSINESS_ACCOUNT_ID  = 987654321098765
   ```

4. **Find Channel ID:**
   Run once locally:
   ```bash
   WA_PHONE_NUMBER_ID=xxx WA_ACCESS_TOKEN=xxx WA_BUSINESS_ACCOUNT_ID=xxx \
   python -c "from whatsapp_post import get_channel_id; get_channel_id()"
   ```

5. **Update invite link** in `whatsapp/index.html`:
   Replace `https://whatsapp.com/channel/0029VaNaukriBulletin` with your real link

**Copy files:**
```
whatsapp_post.py     →  whatsapp_post.py
whatsapp/index.html  →  whatsapp/index.html
```

---

## Step 5 — Deploy GitHub Actions

**Copy file:**
```
.github/workflows/scrape-notify.yml  →  .github/workflows/scrape-notify.yml
(REPLACE your existing workflow file)
```

This new workflow:
- Runs scraper 3× daily (same as before)
- Commits scraped data
- Runs `telegram_notify.py` (Telegram + OneSignal + Brevo)
- Runs `whatsapp_post.py` (WhatsApp Channel)
- Commits notification state files

---

## Revenue Summary

| Channel | Mechanism | Expected Revenue |
|---------|-----------|-----------------|
| Unacademy affiliate | Job page banners | ₹150–400/signup |
| Testbook affiliate | Job page banners | ₹100–300/signup |
| Adda247 affiliate | Job page banners | ₹100–500/signup |
| Email list (Brevo) | PDF gate signups | Long-term asset for future campaigns |
| WhatsApp Channel | Channel followers | Trust/traffic, monetize with affiliate links in posts |

**Target:** 290 job pages × affiliate banners = passive income even at 0.5% CTR

---

## Quick deploy commands

```bash
# From your repo root
cp phase4/_includes/affiliate_banners.html _includes/
cp phase4/telegram_notify.py .
cp phase4/whatsapp_post.py .
cp phase4/.github/workflows/scrape-notify.yml .github/workflows/
mkdir -p syllabus-pdf && cp phase4/syllabus-pdf/index.html syllabus-pdf/
mkdir -p whatsapp && cp phase4/whatsapp/index.html whatsapp/

# Add affiliate_banners include to job layout
# Add secrets to GitHub

git add . && git commit -m "feat: Phase 4 revenue — affiliate banners, PDF gate, OneSignal push, WhatsApp"
git push
```
