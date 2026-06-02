#!/usr/bin/env python3
"""
NaukriBulletin — Telegram Channel Notifier
Posts daily job digest to Telegram channel for organic traffic.
Reads real job pages from jobs/ directory instead of hardcoded data.
"""

import os
import re
import requests
from datetime import date
from pathlib import Path

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SITE_ROOT = Path(__file__).parent.parent
JOBS_DIR = SITE_ROOT / "jobs"
SITE_URL = "https://naukribulletin.in"


def send_message(text, parse_mode="HTML"):
    """Send a message to Telegram channel."""
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHANNEL_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False,
            },
            timeout=15
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM] Error: {e}")
        return False


def parse_job_page(job_dir):
    """Extract title, vacancies, last date, dept from a job index.html."""
    html_file = job_dir / "index.html"
    if not html_file.exists():
        return None

    html = html_file.read_text(encoding="utf-8", errors="ignore")

    # Title from <h1>
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else job_dir.name.replace("-", " ").title()

    # Vacancies badge: 👥 Vacancies: 451
    vac_match = re.search(r'Vacancies:\s*([\d,N/A]+)', html)
    vacancies = vac_match.group(1).strip() if vac_match else "N/A"

    # Last date badge: 📅 Last Date: ...
    ld_match = re.search(r'Last Date:\s*([^<\n"]{3,40}?)(?:<|"|\n|$)', html)
    last_date = ld_match.group(1).strip().rstrip('"').strip() if ld_match else "N/A"

    # Department from meta or badge
    dept_match = re.search(r'<span[^>]*>\s*🏛️\s*([^<]+)</span>', html)
    dept = dept_match.group(1).strip() if dept_match else ""

    slug = job_dir.name
    url = f"{SITE_URL}/jobs/{slug}/"

    return {
        "title": title[:70],
        "vacancies": vacancies,
        "last_date": last_date[:25],
        "dept": dept,
        "url": url,
    }


def get_recent_jobs(limit=5):
    """Get the most recently modified job directories."""
    if not JOBS_DIR.exists():
        return []

    job_dirs = [d for d in JOBS_DIR.iterdir() if d.is_dir()]
    # Sort by modification time, newest first
    job_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

    jobs = []
    for d in job_dirs[:limit * 2]:  # parse extra in case some fail
        job = parse_job_page(d)
        if job:
            jobs.append(job)
        if len(jobs) >= limit:
            break

    return jobs


def build_daily_digest():
    """Build today's job digest message from real scraped jobs."""
    today = date.today().strftime("%d %B %Y")
    jobs = get_recent_jobs(limit=5)

    lines = [
        f"🇮🇳 <b>NaukriBulletin Daily Digest</b>",
        f"📅 {today}",
        "",
        "<b>🔥 Today's Latest Government Job Notifications:</b>",
        "",
    ]

    if jobs:
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, job in enumerate(jobs):
            emoji = emojis[i] if i < len(emojis) else "🔹"
            lines.append(f"{emoji} <b>{job['title']}</b>")
            if job['vacancies'] and job['vacancies'] != "N/A":
                lines.append(f"   👥 {job['vacancies']} Vacancies")
            if job['last_date'] and job['last_date'] != "N/A":
                lines.append(f"   ⏰ Last Date: {job['last_date']}")
            lines.append(f"   🔗 {job['url']}")
            lines.append("")
    else:
        lines.append("🔍 Check latest jobs at naukribulletin.in")
        lines.append("")

    lines += [
        f"📚 All Jobs: <a href=\"{SITE_URL}/jobs/\">{SITE_URL}/jobs/</a>",
        "",
        "👆 Share with friends preparing for govt exams!",
        "🔔 Stay updated — forward this channel",
    ]

    return "\n".join(lines)


def notify():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[TELEGRAM] Missing BOT_TOKEN or CHANNEL_ID, skipping")
        return

    message = build_daily_digest()
    print("[TELEGRAM] Sending digest:\n", message[:500])
    success = send_message(message)

    if success:
        print("[TELEGRAM] ✅ Daily digest sent!")
    else:
        print("[TELEGRAM] ❌ Failed to send digest")


if __name__ == "__main__":
    notify()
