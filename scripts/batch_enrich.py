#!/usr/bin/env python3
"""
Batch enrichment script for NaukriBulletin
Runs once to enrich all existing CA pages with exam relevance blocks.
Safe to re-run — skips already-enriched pages.
"""
import os, re, json
from pathlib import Path
from datetime import datetime

SITE_ROOT = Path('/Users/meenabhagvat/Projects/naukri-bulletin')
CA_DIR = SITE_ROOT / 'current-affairs'
TODAY = datetime.now().strftime("%d %B %Y")
YR = datetime.now().year

# ── EXAM RELEVANCE KB ─────────────────────────────────────────────────────────
EXAM_KB = {
    "coral":              {"exams":["UPSC","SSC CGL"],"section":"Environment","why":"Coral reefs and marine biodiversity appear almost every year in UPSC Prelims GS1 Environment section."},
    "tiger":              {"exams":["UPSC","SSC CGL"],"section":"Environment","why":"Tiger reserves and Project Tiger are standard static GK for SSC CGL and UPSC."},
    "ramsar":             {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Environment","why":"Ramsar wetland sites in India appear in Banking, SSC and UPSC GK sections."},
    "national park":      {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Environment","why":"National parks and wildlife sanctuaries are standard GK for all competitive exams."},
    "climate":            {"exams":["UPSC"],"section":"Environment","why":"Climate policy and international agreements are core UPSC Prelims and Mains topics."},
    "forest":             {"exams":["UPSC","SSC CGL"],"section":"Environment","why":"Forest cover, deforestation and conservation are directly in UPSC Environment syllabus."},
    "pollution":          {"exams":["UPSC","SSC CGL"],"section":"Environment","why":"Air, water and soil pollution are asked in Science & Technology and Environment sections."},
    "election":           {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Polity","why":"Elections, ECI powers and electoral reforms are directly asked in Polity sections."},
    "supreme court":      {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"Supreme Court judgments and constitutional provisions are standard UPSC/SSC topics."},
    "parliament":         {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"Parliamentary procedures and bills are asked in Polity sections across exams."},
    "governor":           {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"Governor's role and constitutional powers appear in Polity questions."},
    "constitution":       {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"Constitutional amendments and provisions are core Polity topics."},
    "high court":         {"exams":["UPSC","SSC CGL"],"section":"Polity","why":"High Court jurisdiction and constitutional role appear in Polity sections."},
    "rbi":                {"exams":["IBPS PO","SBI PO","RBI Grade B","UPSC"],"section":"Banking","why":"RBI policies, rates and functions are the most asked topic in Banking exam GA sections."},
    "repo rate":          {"exams":["IBPS PO","SBI PO","RBI Grade B"],"section":"Banking","why":"Monetary policy and repo rate are asked in every Banking exam GA section."},
    "inflation":          {"exams":["IBPS PO","SBI PO","RBI Grade B"],"section":"Banking","why":"Inflation, WPI and CPI are standard Banking GA topics."},
    "bank":               {"exams":["IBPS PO","SBI PO","SBI Clerk"],"section":"Banking","why":"Banking sector news including mergers, policy and appointments is core Banking GA."},
    "gdp":                {"exams":["UPSC","IBPS PO"],"section":"Economy","why":"GDP growth and economic indicators are core topics for Banking and UPSC."},
    "budget":             {"exams":["UPSC","IBPS PO","SSC CGL"],"section":"Economy","why":"Union Budget is extensively covered in GA sections of all major exams."},
    "scheme":             {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Government Schemes","why":"Government schemes and their beneficiaries are asked in Welfare and Polity sections."},
    "mission":            {"exams":["UPSC","SSC CGL"],"section":"Government Schemes","why":"Government missions and flagship programmes appear in Current Affairs sections."},
    "yojana":             {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Government Schemes","why":"Central and state government schemes appear across all competitive exam GA sections."},
    "isro":               {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Science & Technology","why":"ISRO missions are among the most asked S&T questions across all exams."},
    "drdo":               {"exams":["UPSC","SSC CGL"],"section":"Science & Technology","why":"DRDO tests and defence technology are asked in Science & Technology sections."},
    "missile":            {"exams":["UPSC","SSC CGL"],"section":"Science & Technology","why":"Missile systems appear in Science & Technology GK."},
    "satellite":          {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Science & Technology","why":"Space missions and satellite launches are standard S&T current affairs."},
    "indian army":        {"exams":["UPSC","SSC CGL","CDS"],"section":"Defence","why":"Army exercises and appointments appear in Defence Affairs of UPSC and SSC."},
    "indian navy":        {"exams":["UPSC","SSC CGL","CDS"],"section":"Defence","why":"Naval exercises and acquisitions are standard Current Affairs for UPSC and SSC."},
    "air force":          {"exams":["UPSC","SSC CGL","CDS"],"section":"Defence","why":"IAF exercises, aircraft acquisitions and appointments appear in Defence Current Affairs."},
    "tunnel":             {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Infrastructure","why":"Major infrastructure projects appear in Geography and Current Affairs."},
    "highway":            {"exams":["UPSC","SSC CGL","RRB NTPC"],"section":"Infrastructure","why":"National highway projects are standard Current Affairs topics."},
    "railway":            {"exams":["RRB NTPC","RRB Group D","UPSC"],"section":"Infrastructure","why":"Railway projects are directly relevant for Railway exams and UPSC."},
    "airport":            {"exams":["UPSC","SSC CGL"],"section":"Infrastructure","why":"Airport development appears in Infrastructure Current Affairs."},
    "g20":                {"exams":["UPSC","IBPS PO","SSC CGL"],"section":"International Relations","why":"G20 summits and outcomes are covered in all competitive exam GA sections."},
    "india japan":        {"exams":["UPSC"],"section":"International Relations","why":"Bilateral relations and defence pacts are core UPSC Mains GS2 topics."},
    "india us":           {"exams":["UPSC"],"section":"International Relations","why":"India-US relations including defence and trade are standard UPSC current affairs."},
    "united nations":     {"exams":["UPSC","SSC CGL"],"section":"International Relations","why":"UN bodies and India's role are asked in International Relations sections."},
    "appointed":          {"exams":["UPSC","SSC CGL","IBPS PO","RRB NTPC"],"section":"Appointments","why":"Key appointments appear in GA sections of all exams."},
    "takes charge":       {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Appointments","why":"Senior appointments in govt, PSUs and defence are standard Current Affairs."},
    "award":              {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Awards","why":"National and international awards are standard Current Affairs."},
    "padma":              {"exams":["UPSC","SSC CGL"],"section":"Awards","why":"Padma awards announced annually are directly asked in GA sections."},
    "cancer":             {"exams":["UPSC"],"section":"Health & Science","why":"Health research and disease control are part of UPSC Mains GS3."},
    "vaccine":            {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"Health & Science","why":"Vaccine development and health policies appear in Science & Technology."},
    "aiims":              {"exams":["UPSC","SSC CGL"],"section":"Health","why":"AIIMS expansion and health policy are in Government Schemes and Welfare sections."},
}

SECTION_CONTEXT = {
    "Environment":        "India has 106 National Parks, 567 Wildlife Sanctuaries and 18 Biosphere Reserves. The Biological Diversity Act 2002 and Wildlife Protection Act 1972 are key laws. India is a signatory to CBD, CITES and the Paris Agreement.",
    "Polity":             "India's governance is based on the Constitution of India (1950). The Seventh Schedule distributes powers between Centre and States. Key constitutional bodies include the Election Commission, CAG, UPSC and Finance Commission.",
    "Banking":            "India's banking sector is regulated by the RBI (est. 1935). The RBI controls monetary policy through repo rate, reverse repo rate, CRR and SLR. India has 12 public sector banks after consolidation.",
    "Economy":            "India is the world's 5th largest economy by nominal GDP. The Union Budget and Economic Survey are key annual documents. India targets a $5 trillion economy. Key indices: WPI, CPI, IIP.",
    "Government Schemes": "Key flagship schemes: PM Awas Yojana, Ayushman Bharat (50 crore beneficiaries), PM Kisan (6000/year), Jal Jeevan Mission, MGNREGS, PM GatiShakti. Knowing scheme names, launch year and target beneficiaries is essential.",
    "Science & Technology": "India's S&T ecosystem: ISRO (space), DRDO (defence), CSIR (research), IITs (education). Major missions: Chandrayaan-3 (2023), Aditya-L1 (2023), Gaganyaan (upcoming). India is top 3 in global space economy.",
    "Defence":            "India's defence is coordinated by MoD. Key policy: Aatmanirbhar Bharat in defence production. India is moving from importer to exporter. Key organisations: DRDO, OFB, BEL, HAL, BDL.",
    "Infrastructure":     "India's NIP targets Rs 111 lakh crore investment by 2025. PM GatiShakti is the master plan for multimodal connectivity. Key projects: Bharatmala (highways), Sagarmala (ports), UDAN (aviation).",
    "International Relations": "India follows strategic autonomy. Member of QUAD, BRICS, SCO, G20, Commonwealth. India's foreign policy pillars: neighbourhood first, Act East, maritime security, development partnerships.",
    "Appointments":       "Constitutional office holders appointed by President. Key positions: Chief Justice of India, RBI Governor, Army/Navy/Air Force Chiefs, CEC, CAG. Their roles and powers are frequently asked.",
    "Awards":             "India's civilian awards: Bharat Ratna, Padma Vibhushan, Padma Bhushan, Padma Shri. Military: Param Vir Chakra, Vir Chakra. International: Nobel, Booker, Ramon Magsaysay for Indians.",
    "Health & Science":   "India's health research: ICMR, AIIMS (23 centres), NIMHANS. Ayushman Bharat covers 50 crore. Key health indices: MMR, IMR, TFR. India eliminated polio (2014) and is targeting elimination of TB by 2025.",
    "Health":             "India's National Health Policy 2017 targets UHC. Ayushman Bharat PM-JAY covers Rs 5 lakh/family/year. India has 23 AIIMS across the country.",
    "General Awareness":  "Current affairs from politics, economy, environment, science and culture appear across all competitive exam GA sections. Focus on events from the last 6 months before your exam.",
}

def get_relevance(title, summary):
    text = (title + " " + summary).lower()
    for keyword, info in EXAM_KB.items():
        if keyword in text:
            return info
    return {"exams":["UPSC","SSC CGL","IBPS PO"],"section":"General Awareness",
            "why":"Current affairs from all domains appear in the GA sections of SSC, Banking and UPSC exams."}

def build_rich_block(title, summary):
    rel = get_relevance(title, summary)
    exams_str = " · ".join(rel["exams"])
    exam_tags = "".join(
        f'<span style="background:rgba(255,107,0,.12);color:var(--saffron);padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;margin-right:6px;">{e}</span>'
        for e in rel["exams"]
    )
    context = SECTION_CONTEXT.get(rel["section"], SECTION_CONTEXT["General Awareness"])
    sentences = [s.strip() for s in re.split(r'[.!?]+', summary) if len(s.strip()) > 20]
    key_facts = sentences[:3] if sentences else [summary[:120]]
    kf_html = "".join(f'<li style="padding:6px 0;color:var(--grey-700);border-bottom:1px solid var(--border);font-size:.9rem;line-height:1.5;">{f}.</li>' for f in key_facts)

    return f'''<!-- NB-RICH-BLOCK -->
<div style="background:rgba(255,107,0,.06);border:1px solid rgba(255,107,0,.2);border-radius:12px;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:.72rem;font-weight:700;color:var(--saffron);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">📚 Exam Relevance — {rel["section"]}</div>
  <div style="margin-bottom:8px;">{exam_tags}</div>
  <div style="font-size:.85rem;color:var(--grey-700);line-height:1.5;">{rel["why"]}</div>
</div>
<h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0 0 10px;">What happened</h2>
<p style="color:var(--grey-700);line-height:1.8;font-size:.95rem;margin-bottom:20px;">{summary}</p>
<h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0 0 10px;">Key facts for exam</h2>
<ul style="margin:0 0 20px;padding-left:20px;">{kf_html}
  <li style="padding:6px 0;color:var(--grey-700);font-size:.9rem;">Section: <strong style="color:var(--white);">{rel["section"]}</strong> — relevant for <strong style="color:var(--white);">{exams_str}</strong>.</li>
</ul>
<h2 style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:var(--white);margin:0 0 10px;">Background & context</h2>
<p style="color:var(--grey-700);line-height:1.8;font-size:.95rem;margin-bottom:20px;">{context}</p>
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:20px;">
  <div style="font-size:.85rem;font-weight:700;color:var(--white);margin-bottom:6px;">🎯 Likely exam question pattern</div>
  <div style="font-size:.88rem;color:var(--grey-700);">Questions on this topic appear as MCQs asking about the organisation involved, the location, the policy name, or the year. Review the key facts above carefully.</div>
</div>
<!-- END-NB-RICH-BLOCK -->'''

# ── MAIN ENRICHMENT LOOP ──────────────────────────────────────────────────────
enriched = 0
skipped = 0
errors = 0

ca_pages = list(CA_DIR.iterdir())
total = len([p for p in ca_pages if p.is_dir()])
print(f"Found {total} CA pages to process...")

for i, page_dir in enumerate(sorted(ca_pages)):
    if not page_dir.is_dir():
        continue
    idx_file = page_dir / 'index.html'
    if not idx_file.exists():
        continue

    try:
        html = idx_file.read_text(encoding='utf-8', errors='ignore')

        # Skip if already enriched
        if 'NB-RICH-BLOCK' in html:
            skipped += 1
            continue

        # Skip non-article pages
        if 'logo-naukri' not in html:
            skipped += 1
            continue

        # Extract title and summary
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        title = re.sub(r'<[^>]+>', '', h1.group(1)).strip() if h1 else page_dir.name
        
        paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.S)
        summary = ''
        for p in paras:
            text = re.sub(r'<[^>]+>', '', p).strip()
            if len(text) > 30:
                summary = text
                break
        
        if not summary:
            summary = title

        # Build rich block
        rich = build_rich_block(title, summary)

        # Inject after <main> or after <h1>
        if '<main' in html:
            main_m = re.search(r'(<main[^>]*>)', html)
            if main_m:
                insert_pos = main_m.end()
                html = html[:insert_pos] + '\n  ' + rich + html[insert_pos:]
        else:
            # Inject after h1
            h1_end = re.search(r'</h1>', html)
            if h1_end:
                insert_pos = h1_end.end()
                html = html[:insert_pos] + '\n' + rich + html[insert_pos:]

        idx_file.write_text(html, encoding='utf-8')
        enriched += 1

        if enriched % 100 == 0:
            print(f"  Progress: {enriched} enriched, {i}/{total} processed...")

    except Exception as e:
        errors += 1

print(f"\nDone!")
print(f"  Enriched: {enriched} pages")
print(f"  Already done / skipped: {skipped}")
print(f"  Errors: {errors}")
