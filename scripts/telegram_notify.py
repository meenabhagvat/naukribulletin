#!/usr/bin/env python3
"""
NaukriBulletin — Telegram Channel Notifier
Posts daily job digest to Telegram channel for organic traffic
"""

import os
import json
import requests
from datetime import date
from pathlib import Path

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SITE_ROOT = Path(__file__).parent.parent
PROCESSED_FILE = SITE_ROOT / "scripts" / "processed.json"


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


def build_daily_digest():
    """Build today's job digest message."""
    today = date.today().strftime("%d %B %Y")
    
    # Hardcoded sample — in production, read from today's generated jobs
    message = f"""🇮🇳 <b>NaukriBulletin Daily Digest</b>
📅 {today}

<b>🔥 Today's Top Job Notifications:</b>

1️⃣ <b>SSC CGL 2025</b>
   👥 17,727 Vacancies | 🎓 Graduate
   ⏰ Last Date: 20 June 2025
   🔗 naukribulletin.in/jobs/ssc-cgl-2025/

2️⃣ <b>RRB NTPC 2025</b>
   👥 11,558 Vacancies | 🎓 12th Pass
   ⏰ Last Date: 10 June 2025
   🔗 naukribulletin.in/jobs/railway-ntpc-2025/

3️⃣ <b>SBI PO 2025</b>
   👥 2,000 Vacancies | 🎓 Graduate
   ⏰ Last Date: 15 June 2025
   🔗 naukribulletin.in/jobs/sbi-po-2025/

<b>📰 Today's Current Affairs (Exam Important):</b>
• India GDP grows 7.8% in Q4 FY25
• ISRO launches NVS-02 Navigation Satellite
• India elected to UN Security Council

📚 Full details: <a href="https://naukribulletin.in">naukribulletin.in</a>

👆 Share with friends preparing for govt exams!
🔔 Stay updated — forward this channel"""

    return message


def notify():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("[TELEGRAM] Missing BOT_TOKEN or CHANNEL_ID, skipping")
        return

    message = build_daily_digest()
    success = send_message(message)
    
    if success:
        print("[TELEGRAM] ✅ Daily digest sent!")
    else:
        print("[TELEGRAM] ❌ Failed to send digest")


if __name__ == "__main__":
    notify()
