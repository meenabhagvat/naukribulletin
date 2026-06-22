#!/usr/bin/env python3
"""
mock_test_generator.py — NaukriBulletin Mock Test Framework

Two modes:

1. Manual generation:
   python3 mock_test_generator.py --exam "RRB NTPC" --slug rrb-ntpc --set 1

   Creates:
     mock-test/<slug>/index.html  (or set-N/index.html for set>1)
     mock-test/data/<slug>-set<N>.json  (skeleton with placeholder questions
       to be filled in / generated via AI before publishing)

2. Trending-exam auto mode:
   python3 mock_test_generator.py --auto

   Scans jobs/*/index.html (or a jobs metadata file) for the most recent /
   most frequently mentioned exam names, picks the top N trending exams that
   don't yet have a mock test page, and generates skeletons for each.

After generation, run an AI question-generation pass (see generate_questions())
to fill the skeleton JSON with real MCQs, then review before publishing.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # naukribulletin/ root
MOCK_DIR = ROOT / "mock-test"
DATA_DIR = MOCK_DIR / "data"
JOBS_DIR = ROOT / "jobs"

# Known exam keywords -> canonical (exam name, slug, sections template)
EXAM_CATALOG = {
    "ssc cgl":      ("SSC CGL",      "ssc-cgl",      "ssc"),
    "ssc chsl":     ("SSC CHSL",     "ssc-chsl",     "ssc"),
    "ssc mts":      ("SSC MTS",      "ssc-mts",      "ssc_basic"),
    "ssc gd":       ("SSC GD Constable", "ssc-gd",   "ssc_basic"),
    "rrb ntpc":     ("RRB NTPC",     "rrb-ntpc",     "railway"),
    "rrb group d":  ("RRB Group D",  "rrb-group-d",  "railway"),
    "rrb alp":      ("RRB ALP",      "rrb-alp",      "railway"),
    "rrb je":       ("RRB JE",       "rrb-je",       "railway"),
    "ibps po":      ("IBPS PO",      "ibps-po",      "banking"),
    "ibps clerk":   ("IBPS Clerk",   "ibps-clerk",   "banking"),
    "sbi po":       ("SBI PO",       "sbi-po",       "banking"),
    "sbi clerk":    ("SBI Clerk",    "sbi-clerk",    "banking"),
    "upsc":         ("UPSC Prelims", "upsc-prelims", "upsc"),
    "nda":          ("NDA",          "nda",          "defence"),
    "cds":          ("CDS",          "cds",          "defence"),
    "afcat":        ("AFCAT",        "afcat",        "defence"),
    "uppsc":        ("UPPSC PCS",    "uppsc-pcs",    "state_psc"),
    "bpsc":         ("BPSC",         "bpsc",         "state_psc"),
    "mppsc":        ("MPPSC",        "mppsc",        "state_psc"),
    "rpsc":         ("RPSC RAS",     "rpsc-ras",     "state_psc"),
    "tnpsc":        ("TNPSC",        "tnpsc",        "state_psc"),
}

# Section templates: list of (section name, number of questions)
SECTION_TEMPLATES = {
    "ssc": [
        ("General Intelligence & Reasoning", 7),
        ("General Awareness", 7),
        ("Quantitative Aptitude", 7),
        ("English Comprehension", 4),
    ],
    "ssc_basic": [
        ("General Intelligence & Reasoning", 8),
        ("General Awareness", 6),
        ("Numerical Aptitude", 6),
        ("English Language", 5),
    ],
    "railway": [
        ("Mathematics", 7),
        ("General Intelligence & Reasoning", 7),
        ("General Science", 6),
        ("General Awareness & Current Affairs", 5),
    ],
    "banking": [
        ("Quantitative Aptitude", 8),
        ("Reasoning Ability", 8),
        ("English Language", 6),
        ("General/Banking Awareness", 3),
    ],
    "upsc": [
        ("History", 5),
        ("Geography", 5),
        ("Polity & Governance", 5),
        ("Economy", 5),
        ("Current Affairs & Science", 5),
    ],
    "defence": [
        ("General Knowledge", 8),
        ("Mathematics", 8),
        ("English", 5),
        ("Reasoning", 4),
    ],
    "state_psc": [
        ("State & National Current Affairs", 6),
        ("History & Culture", 6),
        ("Geography", 5),
        ("Polity & Economy", 5),
        ("Reasoning & Aptitude", 3),
    ],
    "default": [
        ("General Awareness", 7),
        ("Reasoning", 6),
        ("Quantitative Aptitude", 6),
        ("English", 6),
    ],
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def placeholder_question(idx: int, section: str) -> dict:
    """Skeleton question — replace via generate_questions() before publishing."""
    return {
        "q": f"[PLACEHOLDER Q{idx}] Sample question for {section} — replace before publishing.",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": 0,
        "explanation": "Add explanation here."
    }


def build_skeleton(exam_name: str, slug: str, set_num: int, category: str) -> dict:
    sections_template = SECTION_TEMPLATES.get(category, SECTION_TEMPLATES["default"])
    sections = []
    qcounter = 1
    for sec_name, count in sections_template:
        questions = []
        for _ in range(count):
            questions.append(placeholder_question(qcounter, sec_name))
            qcounter += 1
        sections.append({"name": sec_name, "questions": questions})

    total_q = qcounter - 1
    duration = max(15, round(total_q * 0.8))  # ~0.8 min/question, min 15

    return {
        "id": f"{slug}-set{set_num}",
        "title": f"{exam_name} — Free Mock Test {set_num}",
        "exam": exam_name,
        "durationMinutes": duration,
        "sections": sections,
    }


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{exam_name} Free Mock Test {set_num} — Online Practice 2026 | NaukriBulletin</title>
  <meta name="description" content="Take {exam_name} free mock test {set_num} online. {total_q} questions with timer, instant scoring and detailed solutions.">
  <link rel="canonical" href="https://naukribulletin.in{canonical_path}">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap"></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <link rel="stylesheet" href="/mock-test/quiz-style.css">
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{ appId: "89e83d08-e30e-46f9-baec-f0167f8baa35",
        notifyButton: {{ enable: true, size: "medium", position: "bottom-left" }} }});
    }});
  </script>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/syllabus/">Syllabus</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>

  <div style="background:var(--navy);padding:32px 20px 24px;">
    <div style="max-width:900px;margin:0 auto;">
      <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:8px;">
        <a href="/" style="color:#9BA3B8;text-decoration:none;">Home</a> ›
        <a href="/mock-test/" style="color:#9BA3B8;text-decoration:none;">Mock Tests</a> › {exam_name}
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;color:#fff;margin-bottom:6px;">
        📋 {exam_name} — Free Mock Test {set_num}
      </h1>
      <p style="color:#9BA3B8;font-size:0.92rem;">{total_q} Questions · {duration} Minutes · Instant Result & Analysis</p>
    </div>
  </div>

  <div style="max-width:900px;margin:0 auto;padding:24px 20px;">

    <div id="qe-instructions" style="background:var(--card-bg);border:1.5px solid var(--grey-200);border-radius:12px;padding:20px;margin-bottom:20px;">
      <div style="font-weight:800;font-family:'Syne',sans-serif;color:var(--white);margin-bottom:10px;">📌 Instructions</div>
      <ul style="font-size:0.88rem;color:var(--grey-700);padding-left:20px;line-height:1.8;">
        <li>This test has {total_q} questions to be completed in {duration} minutes.</li>
        <li>Each correct answer gets +2 marks; each wrong answer gets −0.5 (negative marking).</li>
        <li>You can navigate between questions using the Question Palette.</li>
        <li>The test auto-submits when the timer reaches 0.</li>
        <li>Click "Start Test" below when ready.</li>
      </ul>
      <button id="qe-start-btn" class="qe-btn qe-btn-submit" style="margin-top:16px;max-width:200px;">▶ Start Test</button>
    </div>

    <div id="quiz-root" style="background:var(--card-bg);border-radius:12px;overflow:hidden;border:1.5px solid var(--grey-200);display:none;"></div>

    <div style="margin-top:28px;background:var(--card-bg);border:1.5px solid var(--grey-200);border-radius:12px;padding:20px;">
      <div style="font-weight:800;font-family:'Syne',sans-serif;color:var(--white);margin-bottom:12px;">More {exam_name} Mock Tests</div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        <a href="/mock-test/" style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--navy-soft);border-radius:8px;text-decoration:none;color:inherit;font-size:0.88rem;"><span>← Back to all Mock Tests</span></a>
      </div>
    </div>

    <div style="background:linear-gradient(135deg,#0A0F2C,#1d4ed8);border-radius:16px;padding:28px;text-align:center;margin-top:24px;">
      <div style="font-size:1.1rem;font-weight:800;color:#fff;margin-bottom:8px;">📲 Get Daily Practice Questions</div>
      <p style="color:#9BA3B8;margin-bottom:14px;font-size:0.9rem;">Join 50,000+ aspirants getting daily MCQs on Telegram</p>
      <a href="https://t.me/naukribulletin24" target="_blank" rel="noopener"
         style="display:inline-block;background:#FF6B00;color:#fff;padding:10px 28px;border-radius:8px;font-weight:700;text-decoration:none;">
        📲 Join @naukribulletin24
      </a>
    </div>

  </div>

  <footer style="background:var(--navy);color:#9BA3B8;padding:32px 20px;margin-top:48px;text-align:center;font-size:0.82rem;">
    <div style="max-width:1100px;margin:0 auto;">
      <p>© 2026 NaukriBulletin.in</p>
      <div style="margin-top:12px;display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
        <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;">Latest Jobs</a>
        <a href="/syllabus/" style="color:#9BA3B8;text-decoration:none;">Syllabus</a>
        <a href="/answer-key/" style="color:#9BA3B8;text-decoration:none;">Answer Keys</a>
        <a href="/cut-off/" style="color:#9BA3B8;text-decoration:none;">Cut Off</a>
        <a href="/age-calculator/" style="color:#9BA3B8;text-decoration:none;">Age Calculator</a>
      </div>
    </div>
  </footer>

  <script src="/mock-test/quiz-engine.js"></script>
  <script>
    document.getElementById('qe-start-btn').addEventListener('click', function () {{
      document.getElementById('qe-instructions').style.display = 'none';
      document.getElementById('quiz-root').style.display = 'block';
      fetch('/mock-test/data/{data_file}')
        .then(r => r.json())
        .then(data => NBQuiz.init('quiz-root', data))
        .catch(err => {{
          document.getElementById('quiz-root').innerHTML = '<p style="padding:20px;color:#d32f2f;">Failed to load test data. Please refresh and try again.</p>';
          console.error(err);
        }});
    }});
  </script>
</body>
</html>
"""


def generate_test(exam_name: str, slug: str, set_num: int, category: str, dry_run=False):
    skeleton = build_skeleton(exam_name, slug, set_num, category)
    total_q = sum(len(s["questions"]) for s in skeleton["sections"])
    duration = skeleton["durationMinutes"]

    data_file = f"{slug}-set{set_num}.json"
    page_dir = MOCK_DIR / slug if set_num == 1 else MOCK_DIR / slug / f"set-{set_num}"
    canonical_path = f"/mock-test/{slug}/" if set_num == 1 else f"/mock-test/{slug}/set-{set_num}/"

    html = PAGE_TEMPLATE.format(
        exam_name=exam_name,
        set_num=set_num,
        total_q=total_q,
        duration=duration,
        canonical_path=canonical_path,
        data_file=data_file,
    )

    if dry_run:
        print(f"Would create: {page_dir / 'index.html'}")
        print(f"Would create: {DATA_DIR / data_file}")
        return

    page_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    (page_dir / "index.html").write_text(html, encoding="utf-8")
    (DATA_DIR / data_file).write_text(json.dumps(skeleton, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✓ Created {page_dir / 'index.html'}")
    print(f"✓ Created {DATA_DIR / data_file} (skeleton — {total_q} placeholder questions)")
    print(f"  → Fill in real questions via generate_questions() / AI cascade, then review before publishing.")


def detect_trending_exams(top_n=3):
    """Scan job slugs for exam-name mentions and rank by frequency.
    Returns list of (exam_name, slug, category) not already in mock-test/."""
    if not JOBS_DIR.exists():
        print("jobs/ directory not found — cannot auto-detect.", file=sys.stderr)
        return []

    counts = Counter()
    for job_dir in JOBS_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        name = job_dir.name.lower().replace("-", " ")
        for keyword, (exam_name, exam_slug, category) in EXAM_CATALOG.items():
            if keyword in name:
                counts[keyword] += 1

    existing = {p.name for p in MOCK_DIR.iterdir() if p.is_dir()} if MOCK_DIR.exists() else set()

    results = []
    for keyword, count in counts.most_common():
        exam_name, exam_slug, category = EXAM_CATALOG[keyword]
        if exam_slug in existing:
            continue
        results.append((exam_name, exam_slug, category, count))
        if len(results) >= top_n:
            break

    return results


def main():
    parser = argparse.ArgumentParser(description="NaukriBulletin Mock Test Generator")
    parser.add_argument("--exam", help="Exam display name, e.g. 'RRB NTPC'")
    parser.add_argument("--slug", help="URL slug, e.g. 'rrb-ntpc'")
    parser.add_argument("--set", type=int, default=1, help="Set/version number (default 1)")
    parser.add_argument("--category", default=None,
                         help="Section template category: ssc, ssc_basic, railway, banking, upsc, defence, state_psc, default")
    parser.add_argument("--auto", action="store_true", help="Auto-detect trending exams from jobs/ and generate skeletons")
    parser.add_argument("--top", type=int, default=3, help="Number of trending exams to generate in --auto mode")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be generated without writing files")
    args = parser.parse_args()

    if args.auto:
        trending = detect_trending_exams(top_n=args.top)
        if not trending:
            print("No new trending exams found (or all already have mock tests).")
            return
        print(f"Trending exams without mock tests: {[t[0] for t in trending]}")
        for exam_name, slug, category, count in trending:
            print(f"\n--- {exam_name} (mentioned in {count} job posts) ---")
            generate_test(exam_name, slug, 1, category, dry_run=args.dry_run)
        return

    if not args.exam or not args.slug:
        parser.error("--exam and --slug are required unless --auto is used")

    category = args.category
    if category is None:
        for keyword, (ename, eslug, ecat) in EXAM_CATALOG.items():
            if eslug == args.slug:
                category = ecat
                break
        category = category or "default"

    generate_test(args.exam, args.slug, args.set, category, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
