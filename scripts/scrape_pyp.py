#!/usr/bin/env python3
"""
NaukriBulletin — Previous Year Papers Automation Script
========================================================
Scrapes official exam websites & aggregators for PYQ paper links,
then writes /previous-year-papers/pyp-data.json for the frontend to consume.

Run this via cron (e.g., daily at 2 AM):
    0 2 * * * /usr/bin/python3 /path/to/naukri-bulletin/scripts/scrape_pyp.py

Requirements:
    pip install requests beautifulsoup4 lxml

Output:
    naukri-bulletin/previous-year-papers/pyp-data.json
"""

import json
import re
import logging
import time
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent.parent / "previous-year-papers"
OUTPUT_FILE = OUTPUT_DIR / "pyp-data.json"
LOG_FILE = OUTPUT_DIR / "scrape_pyp.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}
REQUEST_TIMEOUT = 15   # seconds
DELAY_BETWEEN = 2      # polite delay between requests (seconds)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def fetch(url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL and return BeautifulSoup, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        log.warning(f"Fetch failed: {url} — {exc}")
        return None


def make_paper(title, year, shift="–", qs=100, mins=90, solved=True,
               pdf_url="#", source="Official"):
    """Return a standard paper dict for the frontend."""
    return {
        "title": title,
        "year": str(year),
        "shift": shift,
        "qs": qs,
        "mins": mins,
        "solved": solved,
        "pdf": pdf_url,
        "source": source,
        "added": date.today().isoformat(),
    }


def deduplicate(papers: list[dict]) -> list[dict]:
    """Remove duplicate papers by (title, year, shift)."""
    seen = set()
    out = []
    for p in papers:
        key = (p["title"].lower(), p["year"], p["shift"].lower())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


# ──────────────────────────────────────────────
# SCRAPER FUNCTIONS — one per exam category
# ──────────────────────────────────────────────

def scrape_ssc() -> list[dict]:
    """
    Scrape SSC official site (ssc.gov.in) for PYQ PDFs.
    SSC publishes question papers on their 'Notices' / 'Previous Papers' page.
    """
    papers = []
    url = "https://ssc.gov.in/portal/previous-papers"
    soup = fetch(url)
    time.sleep(DELAY_BETWEEN)

    if soup:
        # SSC lists papers as links inside notice sections
        links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
        for a in links:
            text = a.get_text(strip=True)
            href = a.get("href", "")
            if not href.startswith("http"):
                href = "https://ssc.gov.in" + href

            year_m = re.search(r"20(2[0-9]|1[5-9])", text)
            year = year_m.group() if year_m else "2024"

            # Classify by exam name
            title = None
            text_l = text.lower()
            if "cgl" in text_l:
                title = "SSC CGL"
            elif "chsl" in text_l:
                title = "SSC CHSL"
            elif "mts" in text_l:
                title = "SSC MTS"
            elif "gd" in text_l:
                title = "SSC GD Constable"
            elif "cpo" in text_l:
                title = "SSC CPO"
            elif "je" in text_l:
                title = "SSC JE"

            if title:
                shift_m = re.search(r"shift[- ]?(\d+)", text_l)
                shift = f"Shift {shift_m.group(1)}" if shift_m else "All Shifts"
                papers.append(make_paper(title, year, shift,
                                         pdf_url=href, source="SSC Official"))
        log.info(f"SSC: scraped {len(papers)} papers from official site")

    # Fallback: always ensure recent years are present
    fallback = [
        make_paper("SSC CGL Tier 1", 2024, "Shift 1", 100, 60, True,
                   "https://ssc.gov.in/", "SSC Official"),
        make_paper("SSC CGL Tier 1", 2024, "Shift 2", 100, 60, True,
                   "https://ssc.gov.in/", "SSC Official"),
        make_paper("SSC CGL Tier 1", 2023, "All Shifts", 100, 60, True,
                   "https://ssc.gov.in/", "SSC Official"),
        make_paper("SSC CHSL Tier 1", 2024, "Shift 1", 100, 60, True,
                   "https://ssc.gov.in/", "SSC Official"),
        make_paper("SSC MTS Paper 1", 2024, "All Shifts", 90, 90, True,
                   "https://ssc.gov.in/", "SSC Official"),
        make_paper("SSC GD Constable", 2024, "All Shifts", 80, 60, True,
                   "https://ssc.gov.in/", "SSC Official"),
        make_paper("SSC CPO Paper 1", 2023, "All Shifts", 200, 120, True,
                   "https://ssc.gov.in/", "SSC Official"),
    ]
    papers = papers + fallback
    return deduplicate(papers)


def scrape_railway() -> list[dict]:
    """Scrape RRB official regional sites for PYQ PDFs."""
    papers = []
    # RRBs publish papers on regional sites; try the CEN notice pages
    rrb_urls = [
        ("https://rrbchennai.gov.in/", "RRB Chennai"),
        ("https://www.rrbmumbai.gov.in/", "RRB Mumbai"),
    ]
    for url, src in rrb_urls:
        soup = fetch(url)
        time.sleep(DELAY_BETWEEN)
        if soup:
            for a in soup.find_all("a", href=re.compile(r"question|paper|pyq", re.I)):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = url.rstrip("/") + "/" + href.lstrip("/")
                text = a.get_text(strip=True).lower()
                year_m = re.search(r"20(2[0-9]|1[5-9])", text)
                year = year_m.group() if year_m else "2024"
                if "ntpc" in text:
                    papers.append(make_paper("RRB NTPC CBT 1", year,
                                             pdf_url=href, source=src))
                elif "group d" in text or "groupd" in text:
                    papers.append(make_paper("RRB Group D", year,
                                             pdf_url=href, source=src))

    log.info(f"Railway: scraped {len(papers)} papers (+ fallback)")
    fallback = [
        make_paper("RRB NTPC CBT 1", 2024, "Shift 1", 100, 90, True,
                   "https://indianrailways.gov.in/", "RRB Official"),
        make_paper("RRB NTPC CBT 1", 2024, "Shift 2", 100, 90, True,
                   "https://indianrailways.gov.in/", "RRB Official"),
        make_paper("RRB Group D Phase 1", 2024, "All Shifts", 100, 90, True,
                   "https://indianrailways.gov.in/", "RRB Official"),
        make_paper("RRB JE CBT 1", 2024, "All Shifts", 100, 90, True,
                   "https://indianrailways.gov.in/", "RRB Official"),
        make_paper("RRB ALP CBT 1", 2024, "All Shifts", 75, 60, True,
                   "https://indianrailways.gov.in/", "RRB Official"),
    ]
    papers = papers + fallback
    return deduplicate(papers)


def scrape_banking() -> list[dict]:
    """Scrape IBPS and SBI for PYQ PDFs."""
    papers = []

    # IBPS
    soup = fetch("https://www.ibps.in/common-written-examination-cwe-previous-year-papers/")
    time.sleep(DELAY_BETWEEN)
    if soup:
        for a in soup.find_all("a", href=re.compile(r"\.pdf", re.I)):
            href = a.get("href", "")
            text = a.get_text(strip=True).lower()
            year_m = re.search(r"20(2[0-9]|1[5-9])", text)
            year = year_m.group() if year_m else "2024"
            if "po" in text and "ibps" in text:
                papers.append(make_paper("IBPS PO Prelims", year,
                                         pdf_url=href, source="IBPS Official"))
            elif "clerk" in text:
                papers.append(make_paper("IBPS Clerk Prelims", year,
                                         pdf_url=href, source="IBPS Official"))
            elif "rrb" in text:
                papers.append(make_paper("IBPS RRB PO Prelims", year,
                                         pdf_url=href, source="IBPS Official"))

    log.info(f"Banking: scraped {len(papers)} papers (+ fallback)")
    fallback = [
        make_paper("SBI PO Prelims", 2024, "Shift 1", 100, 60, True,
                   "https://sbi.co.in/careers", "SBI Official"),
        make_paper("SBI PO Mains", 2024, "–", 155, 180, True,
                   "https://sbi.co.in/careers", "SBI Official"),
        make_paper("SBI Clerk Prelims", 2024, "Shift 1", 100, 60, True,
                   "https://sbi.co.in/careers", "SBI Official"),
        make_paper("IBPS PO Prelims", 2024, "All Shifts", 100, 60, True,
                   "https://ibps.in/", "IBPS Official"),
        make_paper("IBPS Clerk Prelims", 2024, "All Shifts", 100, 60, True,
                   "https://ibps.in/", "IBPS Official"),
        make_paper("RBI Grade B Phase 1", 2024, "–", 200, 120, True,
                   "https://opportunities.rbi.org.in/", "RBI Official"),
    ]
    papers = papers + fallback
    return deduplicate(papers)


def scrape_upsc() -> list[dict]:
    """Scrape UPSC for previous year question papers."""
    papers = []
    url = "https://www.upsc.gov.in/examinations/previous-question-papers"
    soup = fetch(url)
    time.sleep(DELAY_BETWEEN)

    if soup:
        for a in soup.find_all("a", href=re.compile(r"pdf|question", re.I)):
            href = a.get("href", "")
            if not href.startswith("http"):
                href = "https://www.upsc.gov.in" + href
            text = a.get_text(strip=True)
            text_l = text.lower()
            year_m = re.search(r"20(2[0-9]|1[5-9])", text)
            year = year_m.group() if year_m else "2024"

            if "civil" in text_l and ("gs-1" in text_l or "general studies" in text_l):
                papers.append(make_paper("UPSC Civil Services Prelims GS-1", year,
                                         qs=100, mins=120, pdf_url=href,
                                         source="UPSC Official"))
            elif "nda" in text_l and "math" in text_l:
                papers.append(make_paper("UPSC NDA Paper I (Maths)", year,
                                         qs=120, mins=150, pdf_url=href,
                                         source="UPSC Official"))
            elif "cds" in text_l:
                papers.append(make_paper("UPSC CDS Paper I (GK)", year,
                                         qs=120, mins=120, pdf_url=href,
                                         source="UPSC Official"))

    log.info(f"UPSC: scraped {len(papers)} papers (+ fallback)")
    fallback = [
        make_paper("UPSC Civil Services Prelims GS-1", 2024, "–", 100, 120, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("UPSC Civil Services Prelims GS-2 (CSAT)", 2024, "–", 80, 120, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("UPSC Civil Services Prelims GS-1", 2023, "–", 100, 120, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("UPSC NDA Paper I (Maths)", 2024, "–", 120, 150, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("UPSC CDS Paper I (GK)", 2024, "–", 120, 120, True,
                   "https://upsc.gov.in/", "UPSC Official"),
    ]
    papers = papers + fallback
    return deduplicate(papers)


def scrape_state() -> list[dict]:
    """Hardcoded state PSC data (official sites vary widely by state)."""
    papers = [
        make_paper("UPPSC PCS Prelims GS", 2024, "–", 150, 120, True,
                   "https://uppsc.up.nic.in/", "UPPSC Official"),
        make_paper("MPPSC Prelims GS Paper 1", 2024, "–", 100, 120, True,
                   "https://mppsc.mp.gov.in/", "MPPSC Official"),
        make_paper("BPSC 70th Prelims", 2024, "–", 150, 120, True,
                   "https://bpsc.bih.nic.in/", "BPSC Official"),
        make_paper("RPSC RAS Prelims", 2024, "–", 150, 180, True,
                   "https://rpsc.rajasthan.gov.in/", "RPSC Official"),
        make_paper("MPSC Rajyaseva Prelims", 2024, "–", 100, 60, True,
                   "https://mpsc.gov.in/", "MPSC Official"),
        make_paper("KPSC KAS Prelims", 2024, "–", 100, 120, True,
                   "https://kpsc.kar.nic.in/", "KPSC Official"),
    ]
    log.info(f"State: {len(papers)} papers")
    return papers


def scrape_defence() -> list[dict]:
    """Defence exams from UPSC and IAF."""
    papers = [
        make_paper("NDA Paper I (Maths)", 2024, "–", 120, 150, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("NDA Paper II (GAT)", 2024, "–", 150, 150, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("CDS Paper I (English)", 2024, "–", 120, 120, True,
                   "https://upsc.gov.in/", "UPSC Official"),
        make_paper("AFCAT Paper", 2024, "–", 100, 120, True,
                   "https://afcat.cdac.in/", "IAF Official"),
        make_paper("Agniveer Army CEE", 2024, "All Shifts", 50, 60, True,
                   "https://joinindianarmy.nic.in/", "Army Official"),
    ]
    log.info(f"Defence: {len(papers)} papers")
    return papers


def scrape_teaching() -> list[dict]:
    """Teaching exams — CTET, DSSSB, state TETs."""
    papers = [
        make_paper("CTET Paper 1 (Class 1–5)", 2024, "–", 150, 150, True,
                   "https://ctet.nic.in/", "CTET Official"),
        make_paper("CTET Paper 2 (Class 6–8)", 2024, "–", 150, 150, True,
                   "https://ctet.nic.in/", "CTET Official"),
        make_paper("CTET Paper 1", 2023, "All Shifts", 150, 150, True,
                   "https://ctet.nic.in/", "CTET Official"),
        make_paper("DSSSB TGT (All Subjects)", 2024, "–", 200, 120, True,
                   "https://dsssb.delhi.gov.in/", "DSSSB Official"),
        make_paper("UP TET Paper 1", 2023, "–", 150, 150, True,
                   "https://updeled.gov.in/", "UPTET Official"),
    ]
    log.info(f"Teaching: {len(papers)} papers")
    return papers


# ──────────────────────────────────────────────
# ALSO: Scrape aggregator sites for PDF links
# (sites like GovtJobGuru, TestBook, Exampur)
# ──────────────────────────────────────────────
def scrape_aggregators() -> dict:
    """
    Scrape well-known aggregator sites that index PYQ PDFs.
    Returns a dict of category → [papers].
    These supplement official site data.
    """
    extra = {cat: [] for cat in
             ["ssc", "railway", "banking", "upsc", "state", "defence", "teaching"]}

    aggregators = [
        {
            "url": "https://www.sscadda.com/previous-year-papers/",
            "cat_map": {"cgl": "ssc", "chsl": "ssc", "ntpc": "railway",
                        "group d": "railway", "sbi po": "banking",
                        "ibps": "banking", "upsc": "upsc", "cds": "defence",
                        "nda": "defence", "ctet": "teaching"},
        },
    ]

    for agg in aggregators:
        soup = fetch(agg["url"])
        time.sleep(DELAY_BETWEEN)
        if not soup:
            continue
        for a in soup.find_all("a", href=re.compile(r"previous|question|pyq|paper", re.I)):
            text = a.get_text(strip=True)
            href = a.get("href", "")
            if not href.startswith("http"):
                continue  # skip relative links from unknown origin
            text_l = text.lower()
            year_m = re.search(r"20(2[0-9]|1[5-9])", text)
            year = year_m.group() if year_m else "2024"
            for keyword, cat in agg["cat_map"].items():
                if keyword in text_l:
                    extra[cat].append(make_paper(
                        text[:60].strip(), year,
                        pdf_url=href, source="Aggregator"
                    ))
                    break

    return extra


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def run():
    log.info("=" * 50)
    log.info("NaukriBulletin PYP Scraper starting…")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Official site scrapers
    data = {
        "ssc":      scrape_ssc(),
        "railway":  scrape_railway(),
        "banking":  scrape_banking(),
        "upsc":     scrape_upsc(),
        "state":    scrape_state(),
        "defence":  scrape_defence(),
        "teaching": scrape_teaching(),
    }

    # 2. Aggregator supplementation
    extra = scrape_aggregators()
    for cat, papers in extra.items():
        data[cat] = deduplicate(data[cat] + papers)

    # 3. Sort newest first within each category
    for cat in data:
        data[cat].sort(key=lambda p: p["year"], reverse=True)

    # 4. Write JSON
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_papers": sum(len(v) for v in data.values()),
        "papers": data,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Written {payload['total_papers']} papers → {OUTPUT_FILE}")
    log.info("=" * 50)

    # 5. Print summary
    print("\n📄 PYP Scrape Summary")
    print("-" * 40)
    for cat, papers in data.items():
        print(f"  {cat:12s} → {len(papers):3d} papers")
    print(f"\n  TOTAL: {payload['total_papers']} papers")
    print(f"  Output: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    run()
