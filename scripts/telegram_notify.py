#!/usr/bin/env python3
"""
NaukriBulletin — Telegram Notifier
Posts top 5 latest individual job notifications to channel
"""

import os
import json
import requests
from datetime import date
from pathlib import Path

BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SITE_ROOT  = Path(__file__).parent.parent
PROCESSED  = SITE_ROOT / "scripts" / "tg_posted.json"


def load_posted():
    if PROCESSED.exists():
        with open(PROCESSED) as f:
            return set(json.load(f))
    return set()


def save_posted(slugs):
    with open(PROCESSED, "w") as f:
        json.dump(list(slugs), f)


def get_latest_jobs(limit=5):
    jobs_dir = SITE_ROOT / "jobs"
    jobs = []
    skip = {"ssc","railway","banking","upsc","defence","police","teaching",
            "10th-pass","12th-pass","graduate","all-india","uttar-pradesh",
            "bihar","madhya-pradesh","rajasthan","tamil-nadu","karnataka",
            "maharashtra","gujarat","kerala","engineering"}

    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir() or job_dir.name in skip:
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        try:
            from bs4 import BeautifulSoup
            with open(idx, encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
            if not title:
                continue

            rows = soup.find_all("tr")
            data = {}
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 2:
                    data[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)

            jobs.append({
                "slug":      job_dir.name,
                "title":     title,
                "dept":      data.get("department", ""),
                "vacancies": data.get("total vacancies", "N/A"),
                "last_date": data.get("last date", "N/A"),
                "salary":    data.get("salary / pay scale", "N/A"),
                "location":  data.get("location", "All India"),
            })
        except Exception:
            continue

    return jobs[:limit]


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id":    CHANNEL_ID,
        "text":       text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }, timeout=15)
    return resp.status_code == 200


def run():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[TELEGRAM] Missing BOT_TOKEN or CHANNEL_ID, skipping")
        return

    posted  = load_posted()
    jobs    = get_latest_jobs(10)
    new_jobs = [j for j in jobs if j["slug"] not in posted]

    if not new_jobs:
        print("[TELEGRAM] No new jobs to post")
        return

    today = date.today().strftime("%d %B %Y")

    # Build digest message
    lines = [f"🇮🇳 <b>NaukriBulletin — {today}</b>\n📢 Latest Govt Job Alerts:\n"]

    for i, job in enumerate(new_jobs[:5], 1):
        lines.append(f"{i}️⃣ <b>{job['title']}</b>")
        if job['dept']:
            lines.append(f"   🏢 {job['dept']}")
        if job['vacancies'] != "N/A":
            lines.append(f"   👥 {job['vacancies']} Vacancies")
        if job['last_date'] != "N/A":
            lines.append(f"   ⏰ Last Date: {job['last_date']}")
        if job['salary'] != "N/A":
            lines.append(f"   💰 {job['salary']}")
        lines.append(f"   🔗 https://naukribulletin.in/jobs/{job['slug']}/")
        lines.append("")

    lines.append("📌 All Jobs: https://naukribulletin.in/jobs/")
    lines.append("🔔 Share with friends preparing for govt exams!")

    message = "\n".join(lines)
    print(f"[TELEGRAM] Posting {len(new_jobs[:5])} new jobs...")

    if send_message(message):
        for job in new_jobs[:5]:
            posted.add(job["slug"])
        save_posted(posted)
        print(f"[TELEGRAM] ✅ Posted successfully to {CHANNEL_ID}")
    else:
        print(f"[TELEGRAM] ❌ Failed to post")


if __name__ == "__main__":
    run()
