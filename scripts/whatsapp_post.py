#!/usr/bin/env python3
"""
NaukriBulletin — whatsapp_post.py
----------------------------------
Auto-posts new jobs to WhatsApp Channel via WhatsApp Business Cloud API
(Meta) — free tier supports unlimited messages to your own channel.

HOW TO SET UP (one-time):
  1. Go to https://developers.facebook.com/ → Create App → Business
  2. Add "WhatsApp" product → select or create a Business Account
  3. In WhatsApp → API Setup, copy:
       - Phone Number ID  → WA_PHONE_NUMBER_ID
       - Temporary token  → WA_ACCESS_TOKEN  (generate Permanent token below)
  4. Generate Permanent Token:
       - Business Settings → System Users → Add System User (Admin)
       - Generate Token → select whatsapp_business_messaging permission
       - Copy token → WA_ACCESS_TOKEN
  5. Create a WhatsApp Channel (not group):
       - Open WhatsApp → New Channel → follow prompts
       - Get Channel ID from the URL or API (see get_channel_id() below)
       - Set WA_CHANNEL_ID
  6. Add all 5 secrets to GitHub Actions → Settings → Secrets:
       WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN, WA_CHANNEL_ID,
       WA_BUSINESS_ACCOUNT_ID (from API Setup page)

NOTES:
  - WhatsApp Channels are broadcast-only (subscribers can't reply)
  - No per-message cost for channels (unlike regular WA Business API)
  - Supports text + image messages
  - Rate limit: ~80 msgs/sec but keep it sane (max 10/day for channels)

Environment variables:
  WA_PHONE_NUMBER_ID      — numeric ID, e.g. 123456789012345
  WA_ACCESS_TOKEN         — permanent system user token
  WA_CHANNEL_ID           — channel's phone number or ID
  WA_BUSINESS_ACCOUNT_ID  — WABA ID
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
WA_PHONE_NUMBER_ID     = os.environ.get("WA_PHONE_NUMBER_ID", "")
WA_ACCESS_TOKEN        = os.environ.get("WA_ACCESS_TOKEN", "")
WA_CHANNEL_ID          = os.environ.get("WA_CHANNEL_ID", "")   # your channel recipient id
WA_BUSINESS_ACCOUNT_ID = os.environ.get("WA_BUSINESS_ACCOUNT_ID", "")
SITE_URL               = "https://naukribulletin.in"

JOBS_JSON_PATH     = Path(__file__).parent / "_data" / "jobs.json"
WA_SENT_IDS_PATH   = Path(__file__).parent / "_data" / "wa_notified_ids.json"

WA_API_VERSION = "v19.0"
WA_API_BASE    = f"https://graph.facebook.com/{WA_API_VERSION}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path, default):
    if path.exists():
        try:   return json.loads(path.read_text(encoding="utf-8"))
        except: return default
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def headers():
    return {
        "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
        "Content-Type":  "application/json",
    }


# ── Message formatting ────────────────────────────────────────────────────────

EMOJI_MAP = {
    "ssc":       "📋",
    "railway":   "🚂",
    "banking":   "🏦",
    "police":    "👮",
    "teaching":  "📚",
    "defence":   "🛡️",
    "state-psc": "🏛️",
    "court":     "⚖️",
    "psu":       "🏭",
}


def format_wa_message(job: dict) -> str:
    """Format a WhatsApp channel message (plain text, emoji-rich)."""
    title    = job.get("title", "New Govt Job")
    org      = job.get("organization", "")
    posts    = job.get("total_posts", "")
    deadline = job.get("last_date", "")
    category = job.get("category", "").lower()
    state    = job.get("state", "")
    url      = job.get("url") or f"{SITE_URL}/jobs/{job.get('slug', '')}"

    emoji = EMOJI_MAP.get(category, "🔔")

    lines = [
        f"{emoji} *{title}*",
        "",
    ]
    if org:       lines.append(f"🏢 *Organization:* {org}")
    if posts:     lines.append(f"📌 *Vacancies:* {posts}")
    if state:     lines.append(f"📍 *State:* {state}")
    if deadline:  lines.append(f"⏳ *Last Date:* {deadline}")
    lines += [
        "",
        f"🔗 {url}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📲 *NaukriBulletin.in*",
        f"Daily Govt Job Alerts",
    ]
    return "\n".join(lines)


# ── WhatsApp API calls ────────────────────────────────────────────────────────

def send_wa_text(message: str, recipient_id: str) -> bool:
    """Send a text message to a WhatsApp Channel or number."""
    if not WA_PHONE_NUMBER_ID or not WA_ACCESS_TOKEN:
        print("[WhatsApp] Missing credentials — skipping")
        return False

    url = f"{WA_API_BASE}/{WA_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                recipient_id,
        "type":              "text",
        "text": {
            "preview_url": True,
            "body": message
        }
    }

    try:
        r = requests.post(url, json=payload, headers=headers(), timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("messages"):
            mid = data["messages"][0].get("id", "?")
            print(f"[WhatsApp] ✓ Sent (msg_id={mid})")
            return True
        else:
            print(f"[WhatsApp] ✗ {r.status_code}: {json.dumps(data)[:300]}")
            return False
    except Exception as e:
        print(f"[WhatsApp] ✗ Exception: {e}")
        return False


def send_wa_image(image_url: str, caption: str, recipient_id: str) -> bool:
    """Send an image message with caption (useful for notification cards)."""
    if not WA_PHONE_NUMBER_ID or not WA_ACCESS_TOKEN:
        return False

    url = f"{WA_API_BASE}/{WA_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                recipient_id,
        "type":              "image",
        "image": {
            "link":    image_url,
            "caption": caption[:1024]
        }
    }

    try:
        r = requests.post(url, json=payload, headers=headers(), timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f"[WhatsApp Image] ✗ {e}")
        return False


def get_channel_id() -> str:
    """
    Helper: fetch your WhatsApp Business Account phone numbers.
    Run once to discover your channel's recipient ID.
    """
    url = f"{WA_API_BASE}/{WA_BUSINESS_ACCOUNT_ID}/phone_numbers"
    try:
        r = requests.get(url, headers=headers(), timeout=10)
        data = r.json()
        print(json.dumps(data, indent=2))
        return data
    except Exception as e:
        print(f"[WhatsApp] get_channel_id error: {e}")
        return {}


# ── Daily digest formatter ────────────────────────────────────────────────────

def format_daily_digest(jobs: list) -> str:
    """Format a digest of multiple jobs for morning/evening broadcast."""
    today = datetime.now().strftime("%d %B %Y")
    lines = [
        f"🔔 *Today's Govt Jobs — {today}*",
        f"({len(jobs)} new vacancies)",
        "",
    ]

    for i, job in enumerate(jobs[:8], 1):
        title    = job.get("title", "")[:50]
        deadline = job.get("last_date", "N/A")
        url      = job.get("url") or f"{SITE_URL}/jobs/{job.get('slug', '')}"
        lines.append(f"{i}. *{title}*")
        lines.append(f"   ⏳ {deadline} | {url}")
        lines.append("")

    if len(jobs) > 8:
        lines.append(f"_+ {len(jobs)-8} more jobs..._")
        lines.append("")

    lines += [
        f"🌐 {SITE_URL}",
        "━━━━━━━━━━━━━━━━━━━━",
        "📲 Subscribe: NaukriBulletin.in",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*55}")
    print(f"NaukriBulletin WhatsApp Poster — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*55}")

    if not WA_CHANNEL_ID:
        print("[Main] WA_CHANNEL_ID not set. Run get_channel_id() first.")
        print("       Or set WA_CHANNEL_ID in GitHub Secrets.")
        return

    # Load scraped jobs
    jobs = load_json(JOBS_JSON_PATH, [])
    if not jobs:
        print("[Main] No jobs found — exiting")
        return

    # Load sent IDs
    sent_data = load_json(WA_SENT_IDS_PATH, {"ids": [], "last_run": ""})
    sent_ids  = set(sent_data.get("ids", []))

    new_jobs = [j for j in jobs if j.get("id") and j["id"] not in sent_ids]
    new_jobs.sort(key=lambda j: j.get("post_date", ""), reverse=True)

    print(f"[Main] New jobs for WhatsApp: {len(new_jobs)}")

    if not new_jobs:
        print("[Main] Nothing new — done")
        return

    newly_sent = []

    # Strategy: if 1-2 new jobs, send individual; if 3+, send digest
    if len(new_jobs) <= 2:
        for job in new_jobs[:2]:
            msg = format_wa_message(job)
            ok  = send_wa_text(msg, WA_CHANNEL_ID)
            if ok:
                newly_sent.append(job["id"])
            time.sleep(2)
    else:
        # Send a digest for all new jobs
        digest = format_daily_digest(new_jobs)
        ok = send_wa_text(digest, WA_CHANNEL_ID)
        if ok:
            newly_sent.extend([j["id"] for j in new_jobs])

    # Save sent IDs
    all_ids = list(sent_ids) + newly_sent
    save_json(WA_SENT_IDS_PATH, {
        "ids":       all_ids[-5000:],
        "last_run":  datetime.now(timezone.utc).isoformat(),
        "last_count": len(newly_sent)
    })

    print(f"[Main] Done. Posted {len(newly_sent)} job IDs to WhatsApp.")


if __name__ == "__main__":
    # Uncomment to discover your channel ID:
    # get_channel_id()
    main()
