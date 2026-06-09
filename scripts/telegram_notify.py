#!/usr/bin/env python3
"""
NaukriBulletin — telegram_notify.py  (Phase 4 upgrade)
-------------------------------------------------------
Sends new job notifications to:
  1. Telegram channel  @naukribulletin24
  2. OneSignal web push  (App ID: 89e83d08-e30e-46f9-baec-f0167f8baa35)
  3. (optional) Brevo email broadcast

Environment variables required (set in GitHub Actions secrets):
  TELEGRAM_BOT_TOKEN   — bot token from @BotFather
  TELEGRAM_CHANNEL_ID  — e.g. @naukribulletin24 or numeric -100xxxxx
  ONESIGNAL_APP_ID     — 89e83d08-e30e-46f9-baec-f0167f8baa35
  ONESIGNAL_REST_KEY   — REST API key from OneSignal dashboard → Settings → Keys
  BREVO_API_KEY        — optional, for email broadcast
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN     = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL   = os.environ.get("TELEGRAM_CHANNEL_ID", "@naukribulletin24")
ONESIGNAL_APP_ID   = os.environ.get("ONESIGNAL_APP_ID",   "89e83d08-e30e-46f9-baec-f0167f8baa35")
ONESIGNAL_REST_KEY = os.environ.get("ONESIGNAL_REST_KEY", "")
BREVO_API_KEY      = os.environ.get("BREVO_API_KEY",       "")
SITE_URL           = "https://naukribulletin.in"

# Path to the scraped jobs JSON (adjust to match your repo structure)
JOBS_JSON_PATH = Path(__file__).parent / "_data" / "jobs.json"
SENT_IDS_PATH  = Path(__file__).parent / "_data" / "notified_ids.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_new_jobs(jobs: list, sent_ids: set) -> list:
    """Return jobs that haven't been notified yet."""
    new = [j for j in jobs if j.get("id") and j["id"] not in sent_ids]
    # Sort by post_date descending, newest first
    new.sort(key=lambda j: j.get("post_date", ""), reverse=True)
    return new


# ── Telegram ──────────────────────────────────────────────────────────────────

def format_telegram_message(job: dict) -> str:
    title    = job.get("title", "New Job")
    org      = job.get("organization", "")
    deadline = job.get("last_date", "")
    posts    = job.get("total_posts", "")
    url      = job.get("url") or f"{SITE_URL}/jobs/{job.get('slug', '')}"
    category = job.get("category", "")
    state    = job.get("state", "")

    lines = [f"🔔 *{escape_md(title)}*"]
    if org:       lines.append(f"🏢 {escape_md(org)}")
    if posts:     lines.append(f"📋 Posts: *{escape_md(str(posts))}*")
    if deadline:  lines.append(f"⏰ Last Date: *{escape_md(deadline)}*")
    if category:  lines.append(f"📌 {escape_md(category)}")
    if state:     lines.append(f"📍 {escape_md(state)}")
    lines.append(f"")
    lines.append(f"[👉 View Details & Apply]({url})")
    lines.append(f"")
    lines.append(f"_@naukribulletin24_")
    return "\n".join(lines)


def escape_md(text: str) -> str:
    """Escape MarkdownV2 special chars for Telegram."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def send_telegram(job: dict) -> bool:
    if not TELEGRAM_TOKEN:
        print("[Telegram] No token — skipping")
        return False

    msg = format_telegram_message(job)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHANNEL,
        "text":       msg,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"[Telegram] ✓ Sent: {job.get('title')}")
            return True
        else:
            print(f"[Telegram] ✗ {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"[Telegram] ✗ Exception: {e}")
        return False


# ── OneSignal Web Push ────────────────────────────────────────────────────────

def send_onesignal_push(job: dict) -> bool:
    """
    Send a web push to ALL subscribed users via OneSignal REST API.
    Docs: https://documentation.onesignal.com/reference/create-notification
    """
    if not ONESIGNAL_REST_KEY:
        print("[OneSignal] No REST key — skipping")
        return False

    title    = job.get("title", "New Govt Job")
    org      = job.get("organization", "")
    deadline = job.get("last_date", "")
    url      = job.get("url") or f"{SITE_URL}/jobs/{job.get('slug', '')}"

    # Build subtitle
    subtitle_parts = []
    if org:      subtitle_parts.append(org)
    if deadline: subtitle_parts.append(f"Last: {deadline}")
    subtitle = " · ".join(subtitle_parts) if subtitle_parts else "NaukriBulletin.in"

    # Category-based segment targeting (optional — falls back to All)
    category = job.get("category", "").lower()
    segment_map = {
        "ssc":        "SSC",
        "railway":    "Railway",
        "banking":    "Banking",
        "police":     "Police",
        "teaching":   "Teaching",
        "defence":    "Defence",
    }
    segment = segment_map.get(category, "All")

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        # Target: all subscribers (or specific segment if you create them in dashboard)
        "included_segments": ["All"],
        "headings":  {"en": title[:64]},
        "contents":  {"en": subtitle[:128]},
        "url":       url,
        "web_push_topic": f"job-{category}" if category else "job-general",
        # Small icon shown in notification (must be https)
        "chrome_web_icon":  f"{SITE_URL}/assets/images/nb-icon-192.png",
        "chrome_web_badge": f"{SITE_URL}/assets/images/nb-badge-72.png",
        # Collapse key — replaces old push with same category (prevents flooding)
        "collapse_id": f"nb-{category}" if category else "nb-general",
        # TTL 12 hours
        "ttl": 43200,
        # Track for analytics
        "data": {
            "job_id":   job.get("id", ""),
            "category": category,
        }
    }

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Basic {ONESIGNAL_REST_KEY}",
    }

    try:
        r = requests.post(
            "https://onesignal.com/api/v1/notifications",
            json=payload, headers=headers, timeout=15
        )
        data = r.json()
        if r.status_code == 200 and data.get("id"):
            print(f"[OneSignal] ✓ Push sent: {data['id']} | {title[:50]}")
            return True
        else:
            print(f"[OneSignal] ✗ {r.status_code}: {json.dumps(data)[:300]}")
            return False
    except Exception as e:
        print(f"[OneSignal] ✗ Exception: {e}")
        return False


# ── Brevo email broadcast (optional) ─────────────────────────────────────────

def send_brevo_campaign(jobs: list) -> bool:
    """
    Optionally trigger a transactional Brevo email to 'Syllabus Downloads' list.
    Uses template ID 1 (configure in Brevo dashboard).
    Only fires if 3+ new jobs found (avoid spam for single jobs).
    """
    if not BREVO_API_KEY or len(jobs) < 3:
        return False

    job_html = "".join(
        f'<li><a href="{j.get("url","#")}">{j.get("title","")}</a>'
        f' — {j.get("organization","")}'
        f' | Last: {j.get("last_date","—")}</li>'
        for j in jobs[:10]
    )

    payload = {
        "sender":    {"name": "NaukriBulletin", "email": "alerts@naukribulletin.in"},
        "to":        [{"email": "naukribulletin24@gmail.com"}],  # replace with list send
        "subject":   f"🔔 {len(jobs)} New Govt Jobs — {datetime.now().strftime('%d %b %Y')}",
        "htmlContent": f"""
          <h2>New Government Jobs Today</h2>
          <ul>{job_html}</ul>
          <p><a href="{SITE_URL}">View all jobs at NaukriBulletin.in</a></p>
          <p style="font-size:12px;color:#999">
            You're receiving this because you downloaded a syllabus PDF.
            <a href="{{{{unsubscribe}}}}">Unsubscribe</a>
          </p>
        """
    }

    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 201:
            print(f"[Brevo] ✓ Email sent for {len(jobs)} jobs")
            return True
        else:
            print(f"[Brevo] ✗ {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"[Brevo] ✗ Exception: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*55}")
    print(f"NaukriBulletin Notifier — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*55}")

    # Load scraped jobs
    jobs = load_json(JOBS_JSON_PATH, [])
    if not jobs:
        print("[Main] No jobs found in jobs.json — exiting")
        return

    # Load already-notified IDs
    sent_data = load_json(SENT_IDS_PATH, {"ids": [], "last_run": ""})
    sent_ids  = set(sent_data.get("ids", []))

    print(f"[Main] Total jobs: {len(jobs)} | Already notified: {len(sent_ids)}")

    new_jobs = get_new_jobs(jobs, sent_ids)
    print(f"[Main] New jobs to notify: {len(new_jobs)}")

    if not new_jobs:
        print("[Main] Nothing new — done")
        return

    # Cap at 5 notifications per run (avoid flooding)
    batch = new_jobs[:5]
    newly_sent_ids = []

    for i, job in enumerate(batch):
        job_id = job["id"]
        print(f"\n[{i+1}/{len(batch)}] {job.get('title','?')} ({job_id})")

        tg_ok = send_telegram(job)
        # Small delay between Telegram messages to avoid rate limiting
        if i < len(batch) - 1:
            time.sleep(1.5)

        # OneSignal: only send push for first job per run (avoid notification fatigue)
        # Change to: `if True:` to push all new jobs
        if i == 0:
            send_onesignal_push(job)

        if tg_ok:
            newly_sent_ids.append(job_id)

    # Brevo batch email (optional, for 3+ new jobs)
    send_brevo_campaign(new_jobs)

    # Persist notified IDs (keep last 5000 to prevent file bloat)
    all_ids = list(sent_ids) + newly_sent_ids
    all_ids = all_ids[-5000:]

    save_json(SENT_IDS_PATH, {
        "ids":      all_ids,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "last_batch_count": len(newly_sent_ids)
    })

    print(f"\n[Main] Done. Notified {len(newly_sent_ids)} jobs this run.")


if __name__ == "__main__":
    main()
