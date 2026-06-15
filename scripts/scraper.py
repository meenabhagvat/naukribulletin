#!/usr/bin/env python3
"""
NaukriBulletin — Automated Job Scraper & Site Generator
Phase 1 upgrade: direct .gov.in sources, state PSCs, 3× daily runs
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime, date
from bs4 import BeautifulSoup
from pathlib import Path
import re
import subprocess

# ─── CONFIG ───────────────────────────────────────────────────────────────────

GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
ADSENSE_CLIENT  = os.environ.get("ADSENSE_CLIENT", "ca-pub-1001412206051588")
ADSENSE_SLOT_TOP = os.environ.get("ADSENSE_SLOT_TOP", "XXXXXXXXXX")
ADSENSE_SLOT_MID = os.environ.get("ADSENSE_SLOT_MID", "XXXXXXXXXX")
SITE_ROOT = Path(__file__).parent.parent
SITE_URL  = "https://naukribulletin.in"

# ─── SOURCES ──────────────────────────────────────────────────────────────────
# Strategy: primary = direct .gov.in feeds (original, first-party)
#           secondary = official exam bodies (IBPS, RBI, etc.)
#           state PSCs = competitor gap (FreeJobAlert weak here)
#           supplementary = Employment News + NCS (official govt portals)
#           current affairs = PIB + DD News (official only)
#           news sources = The Hindu kept for current affairs only

SOURCES = [

    # ── CENTRAL / NATIONAL ─────────────────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/ssc/",
        "fallback_url": "https://www.freejobalert.com/tag/ssc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a, .post-title a",
        "dept": "SSC",
        "category": "ssc",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.rrbapply.gov.in/",
        "fallback_url": "https://www.rrbapply.gov.in/",
        "type": "html",
        "dept": "Indian Railways",
        "category": "railway",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/upsc/",
        "fallback_url": "https://www.freejobalert.com/tag/upsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a, .post-title a",
        "dept": "UPSC",
        "category": "upsc",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.ibps.in/feed/",
        "fallback_url": "https://www.ibps.in/",
        "type": "rss",
        "dept": "IBPS",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://bank.sbi/web/careers/current-openings",
        "fallback_url": "https://bank.sbi/web/careers/current-openings",
        "type": "html",
        "dept": "SBI",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/rbi/",
        "fallback_url": "https://www.freejobalert.com/tag/reserve-bank-of-india/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a, .post-title a",
        "dept": "RBI",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/central-government-jobs/",
        "fallback_url": "https://www.freejobalert.com/tag/central-government/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "NCS (National Career Service)",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/",
        "fallback_url": "https://www.freejobalert.com/latest-jobs/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "Employment News",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },

    # ── DEFENCE / PARAMILITARY ─────────────────────────────────────────────
    {
        "url": "https://joinindianarmy.nic.in/",
        "fallback_url": "https://joinindianarmy.nic.in/",
        "type": "html",
        "selector": ".notification-list a, table tr td a, h3 a",
        "dept": "Indian Army",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/indian-navy/",
        "fallback_url": "https://www.freejobalert.com/tag/indian-navy/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "Indian Navy",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://careerindianairforce.cdac.in/",
        "fallback_url": "https://careerindianairforce.cdac.in/",
        "type": "html",
        "dept": "Indian Air Force",
        "category": "defence",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/crpf/",
        "fallback_url": "https://www.freejobalert.com/tag/crpf/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "CRPF",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },

    # ── STATE PSCs (FreeJobAlert gap — prioritised) ─────────────────────────
    {
        "url": "https://uppsc.up.nic.in/CandidateInfo/LatestNews.aspx",
        "fallback_url": "https://uppsc.up.nic.in/CandidateInfo/LatestNews.aspx",
        "type": "html",
        "dept": "UPPSC (Uttar Pradesh)",
        "category": "state",
        "state": "Uttar Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/bpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/bpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "BPSC (Bihar)",
        "category": "state",
        "state": "Bihar",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/mppsc/",
        "fallback_url": "https://www.freejobalert.com/tag/mppsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "MPPSC (Madhya Pradesh)",
        "category": "state",
        "state": "Madhya Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/rpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/rpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "RPSC (Rajasthan)",
        "category": "state",
        "state": "Rajasthan",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/tnpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/tnpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "TNPSC (Tamil Nadu)",
        "category": "state",
        "state": "Tamil Nadu",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/kpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/kpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "KPSC (Karnataka)",
        "category": "state",
        "state": "Karnataka",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/mpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/mpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "MPSC (Maharashtra)",
        "category": "state",
        "state": "Maharashtra",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://gpsc.gujarat.gov.in/ViewNotification",
        "fallback_url": "https://gpsc.gujarat.gov.in/ViewNotification",
        "type": "html",
        "dept": "GPSC (Gujarat)",
        "category": "state",
        "state": "Gujarat",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/hpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/hpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "HPSC (Haryana)",
        "category": "state",
        "state": "Haryana",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/apsc/",
        "fallback_url": "https://www.freejobalert.com/tag/apsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "APSC (Assam)",
        "category": "state",
        "state": "Assam",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.keralapsc.gov.in/rss.xml",
        "fallback_url": "https://www.keralapsc.gov.in/notifications",
        "type": "rss",
        "dept": "Kerala PSC",
        "category": "state",
        "state": "Kerala",
        "priority": 2,
        "content_type": "job",
    },

    # ── CURRENT AFFAIRS (official sources only) ────────────────────────────
    {
        "url": "https://indianexpress.com/section/india/feed/",
        "fallback_url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "type": "rss",
        "dept": "PIB",
        "category": "news",
        "priority": 1,
        "content_type": "affairs",
    },
    {
        "url": "https://newsonair.gov.in/",
        "fallback_url": None,
        "type": "html",
        "dept": "DD News",
        "category": "news",
        "priority": 1,
        "content_type": "affairs",
    },
    {
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "fallback_url": None,
        "type": "rss",
        "dept": "The Hindu",
        "category": "news",
        "priority": 2,
        "content_type": "affairs",
    },

    # ── MISSING STATE PSCs ─────────────────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/tspsc/",
        "fallback_url": "https://www.freejobalert.com/tag/tspsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "TGPSC (Telangana)",
        "category": "state",
        "state": "Telangana",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/appsc/",
        "fallback_url": "https://www.freejobalert.com/tag/appsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "APPSC (Andhra Pradesh)",
        "category": "state",
        "state": "Andhra Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://opsc.gov.in/Advt.aspx",
        "fallback_url": "https://opsc.gov.in/Advt.aspx",
        "type": "html",
        "dept": "OPSC (Odisha)",
        "category": "state",
        "state": "Odisha",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/wbpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/wbpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "WBPSC (West Bengal)",
        "category": "state",
        "state": "West Bengal",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://ppsc.gov.in/Advertisements.aspx",
        "fallback_url": "https://ppsc.gov.in/Advertisements.aspx",
        "type": "html",
        "dept": "PPSC (Punjab)",
        "category": "state",
        "state": "Punjab",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/hppsc/",
        "fallback_url": "https://www.freejobalert.com/tag/hppsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "HPPSC (Himachal Pradesh)",
        "category": "state",
        "state": "Himachal Pradesh",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/jpsc/",
        "fallback_url": "https://www.freejobalert.com/tag/jpsc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "JPSC (Jharkhand)",
        "category": "state",
        "state": "Jharkhand",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://psc.cg.gov.in/",
        "fallback_url": "https://psc.cg.gov.in/",
        "type": "html",
        "dept": "CGPSC (Chhattisgarh)",
        "category": "state",
        "state": "Chhattisgarh",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/dsssb/",
        "fallback_url": "https://www.freejobalert.com/tag/dsssb/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "DSSSB (Delhi)",
        "category": "state",
        "state": "Delhi",
        "priority": 1,
        "content_type": "job",
    },

    # ── PSUs / CENTRAL ORGS ────────────────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/ntpc/",
        "fallback_url": "https://www.freejobalert.com/tag/ntpc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "NTPC",
        "category": "engineering",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.bhel.com/rss.xml",
        "fallback_url": "https://www.bhel.com/career",
        "type": "rss",
        "dept": "BHEL",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/ongc/",
        "fallback_url": "https://www.freejobalert.com/tag/ongc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "ONGC",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/nalco/",
        "fallback_url": "https://www.freejobalert.com/tag/nalco/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "NALCO",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.coalindia.in/en-us/career/currentopenings.aspx",
        "fallback_url": "https://www.coalindia.in/en-us/career/currentopenings.aspx",
        "type": "html",
        "dept": "Coal India",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/rec/",
        "fallback_url": "https://www.freejobalert.com/tag/rec/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "REC",
        "category": "engineering",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/nabard/",
        "fallback_url": "https://www.freejobalert.com/tag/nabard/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "NABARD",
        "category": "banking",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/pnb/",
        "fallback_url": "https://www.freejobalert.com/tag/punjab-national-bank/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "PNB",
        "category": "banking",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.bankofbaroda.in/careers",
        "fallback_url": "https://www.bankofbaroda.in/careers",
        "type": "html",
        "dept": "Bank of Baroda",
        "category": "banking",
        "priority": 2,
        "content_type": "job",
    },

    # ── HIGH COURTS ────────────────────────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/allahabad-high-court/",
        "fallback_url": "https://www.freejobalert.com/tag/allahabad-high-court/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "Allahabad High Court",
        "category": "state",
        "state": "Uttar Pradesh",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/mp-high-court/",
        "fallback_url": "https://www.freejobalert.com/tag/mp-high-court/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "MP High Court",
        "category": "state",
        "state": "Madhya Pradesh",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/rajasthan-high-court/",
        "fallback_url": "https://www.freejobalert.com/tag/rajasthan-high-court/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "Rajasthan High Court",
        "category": "state",
        "state": "Rajasthan",
        "priority": 2,
        "content_type": "job",
    },

    # ── HEALTH / MEDICAL ───────────────────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/esic/",
        "fallback_url": "https://www.freejobalert.com/tag/esic/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "ESIC",
        "category": "state",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/aiims/",
        "fallback_url": "https://www.freejobalert.com/tag/aiims/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "AIIMS Delhi",
        "category": "teaching",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/icmr/",
        "fallback_url": "https://www.freejobalert.com/tag/icmr/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "ICMR",
        "category": "teaching",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/nhm/",
        "fallback_url": "https://www.freejobalert.com/tag/nhm/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "NHM",
        "category": "state",
        "priority": 2,
        "content_type": "job",
    },

    # ── TEACHING / UNIVERSITIES ────────────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/ugc/",
        "fallback_url": "https://www.freejobalert.com/tag/ugc/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "UGC",
        "category": "teaching",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://nta.ac.in/",
        "fallback_url": "https://nta.ac.in/",
        "type": "html",
        "dept": "NTA",
        "category": "teaching",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/iit/",
        "fallback_url": "https://www.freejobalert.com/tag/iit/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "IIT Delhi",
        "category": "teaching",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/delhi-university/",
        "fallback_url": "https://www.freejobalert.com/tag/delhi-university/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "Delhi University",
        "category": "teaching",
        "priority": 2,
        "content_type": "job",
    },

    # ── POLICE / PARAMILITARY (additional) ────────────────────────────────
    {
        "url": "https://www.freejobalert.com/bsf/",
        "fallback_url": "https://www.freejobalert.com/tag/bsf/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "BSF",
        "category": "police",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/cisf/",
        "fallback_url": "https://www.freejobalert.com/tag/cisf/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "CISF",
        "category": "police",
        "priority": 1,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/itbp/",
        "fallback_url": "https://www.freejobalert.com/tag/itbp/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "ITBP",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/ssb/",
        "fallback_url": "https://www.freejobalert.com/tag/ssb/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "SSB",
        "category": "police",
        "priority": 2,
        "content_type": "job",
    },

    # ── RAILWAYS (additional boards) ───────────────────────────────────────
    {
        "url": "https://www.freejobalert.com/rrb-chennai/",
        "fallback_url": "https://www.freejobalert.com/tag/rrb-chennai/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "RRB Chennai",
        "category": "railway",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/rrb-mumbai/",
        "fallback_url": "https://www.freejobalert.com/tag/rrb-mumbai/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "RRB Mumbai",
        "category": "railway",
        "priority": 2,
        "content_type": "job",
    },
    {
        "url": "https://www.freejobalert.com/rrb-allahabad/",
        "fallback_url": "https://www.freejobalert.com/tag/rrb-allahabad/",
        "type": "html",
        "selector": "h2.entry-title a, .jeg_post_title a, article h2 a",
        "dept": "RRB Allahabad",
        "category": "railway",
        "priority": 2,
        "content_type": "job",
    },
]

GROQ_MODELS  = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama3-70b-8192"]
GEMINI_MODEL = "gemini-1.5-flash"

PROCESSED_FILE = SITE_ROOT / "scripts" / "processed.json"

# User-Agent rotator — avoids simple bot blocks on .gov.in sites
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "NaukriBulletin/2.0 (+https://naukribulletin.in/)",
]
_ua_index = 0


def next_ua():
    global _ua_index
    ua = UA_LIST[_ua_index % len(UA_LIST)]
    _ua_index += 1
    return ua


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(hashes):
    PROCESSED_FILE.parent.mkdir(exist_ok=True)
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(hashes), f)


def export_jobs_json(jobs_list: list):
    """Export new jobs to scripts/_data/jobs.json for telegram_notify.py"""
    data_dir = Path(__file__).parent / "_data"
    data_dir.mkdir(exist_ok=True)
    out_path  = data_dir / "jobs.json"
    # Load existing
    existing = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except Exception:
            existing = []
    # Merge — keep last 500 entries
    existing_ids = {j.get("id") for j in existing}
    new = [j for j in jobs_list if j.get("id") not in existing_ids]
    merged = (new + existing)[:500]
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"[EXPORT] jobs.json updated: {len(new)} new / {len(merged)} total")



def make_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


def make_slug(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = slug[:60].strip("-")
    return slug

_JUNK_SLUGS = {
    "na", "n-a", "nil", "none", "null", "apply-online", "click-here",
    "download", "home", "contact-us", "about-us", "privacy-policy",
    "otr-apply-online-recruitment-portal", "online-application-submission",
    "combined-examination", "combined-exam", "engineering", "banking",
    "teaching", "police", "railway", "defence", "graduate", "post-graduate",
    "10th-pass", "12th-pass", "iti-govt-jobs-2026", "mba-govt-jobs-2026",
}

def is_valid_slug(slug, title=""):
    if not slug or len(slug) < 8:
        return False
    if slug in _JUNK_SLUGS:
        return False
    # Block PHP, query strings, file extensions leaked into slug
    if any(x in slug for x in ['.php', '.json', '.asp', 'admitcard', 'list-rti', 'transfer-posting']):
        return False
    # Block state-name-only slugs
    if slug in {'assam', 'odisha', 'jharkhand', 'telangana', 'chhattisgarh', 'karnataka', 'bihar', 'rajasthan', 'uttar-pradesh', 'gujarat', 'haryana', 'delhi', 'himachal-pradesh', 'kerala', 'tamil-nadu', 'andhra-pradesh', 'madhya-pradesh'}:
        return False
    return True


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

def _get(url, timeout=20, is_html=False):
    """GET with rotating UA, retry once on failure.
    is_html=True sends browser-like Accept headers (needed for .gov.in HTML pages).
    """
    if is_html:
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    else:
        accept = "application/xml, text/xml, */*"
    headers = {
        "User-Agent": next_ua(),
        "Accept": accept,
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        r.raise_for_status()
        return r
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code in (403, 404, 410):
            return None          # permanent failure — skip silently
        raise
    except Exception:
        # One retry with a different UA after a short pause
        time.sleep(2)
        try:
            headers["User-Agent"] = next_ua()
            return requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        except Exception:
            return None


def scrape_rss(url, dept, fallback_url=None):
    """Fetch RSS. If RSS fails and a fallback HTML URL exists, fall back."""
    items = []
    resp = _get(url)

    if not resp or not resp.content.strip():
        if fallback_url:
            print(f"  [SCRAPER] RSS unavailable, trying HTML fallback: {fallback_url}")
            return scrape_html_smart(fallback_url, dept)
        return items

    try:
        soup = BeautifulSoup(resp.content, "xml")
        for item in soup.find_all("item")[:20]:
            title_tag       = item.find("title")
            desc_tag        = item.find("description")
            link_tag        = item.find("link")
            pubdate_tag     = item.find("pubDate")
            items.append({
                "title":       title_tag.get_text(strip=True)   if title_tag   else "",
                "description": desc_tag.get_text(strip=True)    if desc_tag    else "",
                "link":        link_tag.get_text(strip=True)     if link_tag    else "",
                "pubDate":     pubdate_tag.get_text(strip=True)  if pubdate_tag else "",
                "dept":        dept,
                "source_url":  url,
            })
    except Exception as e:
        print(f"  [SCRAPER] RSS parse error {url}: {e}")

    return items


def scrape_html(url, dept, selector=None):
    """Fetch HTML notification page and extract visible text (legacy blob method).
    Prefer scrape_html_smart() for list pages.
    """
    items = []
    resp = _get(url, is_html=True)
    if not resp:
        return items
    try:
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        items.append({
            "title":       f"Latest Notifications from {dept}",
            "description": text[:3000],
            "link":        url,
            "pubDate":     str(date.today()),
            "dept":        dept,
            "source_url":  url,
        })
    except Exception as e:
        print(f"  [SCRAPER] HTML error {url}: {e}")
    return items


def scrape_html_smart(url, dept, selector=None):
    """Smart HTML scraper: extracts individual notification rows.

    Strategy (tried in order):
    1. Per-source CSS selector from SOURCES config  → individual <a> or <li> elements
    2. Generic table-row extraction                 → <tr> rows with links
    3. Generic link-list extraction                 → <a> tags matching job keywords
    4. Fall back to scrape_html (blob)              → single item

    Returns a list of items, each being one notification.
    """
    JOB_KEYWORDS = re.compile(
        r"(recruit|vacanc|post|appoint|notif|advertis|appl|exam|result|admit|syllabus"
        r"|job|career|opening|walkin|walk-in|interview|selection|merit|list|answer.key"
        r"|hall.ticket|call.letter|cut.off|cutoff|sarkari|bharti|notification)",
        re.IGNORECASE,
    )

    resp = _get(url, is_html=True)
    if not resp:
        return []

    try:
        soup = BeautifulSoup(resp.content, "html.parser")
    except Exception as e:
        print(f"  [SMART] Parse error {url}: {e}")
        return []

    items = []

    # ── Strategy 1: explicit CSS selector ───────────────────────────────────
    if selector:
        try:
            nodes = soup.select(selector)[:15]
            for node in nodes:
                link_tag = node if node.name == "a" else node.find("a")
                title = node.get_text(separator=" ", strip=True)[:200]
                href  = link_tag["href"] if link_tag and link_tag.get("href") else url
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    base = urlparse(url)
                    href = f"{base.scheme}://{base.netloc}{href}"
                if title:
                    items.append({
                        "title":       title,
                        "description": title,
                        "link":        href,
                        "pubDate":     str(date.today()),
                        "dept":        dept,
                        "source_url":  url,
                    })
            if items:
                return items
        except Exception as e:
            print(f"  [SMART] Selector error: {e}")

    # ── Strategy 2: table rows with links ───────────────────────────────────
    for table in soup.find_all("table")[:5]:
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        for row in rows[1:16]:  # skip header row, take up to 15
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            link_tag = row.find("a", href=True)
            # find the cell with the most text (notification title)
            text_cell = max(cells, key=lambda c: len(c.get_text(strip=True)))
            title = text_cell.get_text(separator=" ", strip=True)[:200]
            if not title or len(title) < 10:
                continue
            href = url
            if link_tag:
                href = link_tag["href"]
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    base = urlparse(url)
                    href = f"{base.scheme}://{base.netloc}{href}"
            items.append({
                "title":       title,
                "description": title,
                "link":        href,
                "pubDate":     str(date.today()),
                "dept":        dept,
                "source_url":  url,
            })
        if items:
            return items

    # ── Strategy 3: anchor tags matching job keywords ────────────────────────
    for a in soup.find_all("a", href=True)[:100]:
        text = a.get_text(strip=True)
        if len(text) < 15 or len(text) > 300:
            continue
        if not JOB_KEYWORDS.search(text):
            continue
        href = a["href"]
        if href.startswith("/"):
            from urllib.parse import urlparse
            base = urlparse(url)
            href = f"{base.scheme}://{base.netloc}{href}"
        items.append({
            "title":       text,
            "description": text,
            "link":        href,
            "pubDate":     str(date.today()),
            "dept":        dept,
            "source_url":  url,
        })
        if len(items) >= 10:
            break

    if items:
        return items

    # ── Strategy 4: fall back to blob ───────────────────────────────────────
    return scrape_html(url, dept)


# ─── AI FORMATTER ─────────────────────────────────────────────────────────────

JOB_PROMPT = """\
You are a govt job notification formatter for India.
Extract job details from the raw text below and return ONLY valid JSON, no other text.

Raw text: {raw_text}
Department hint: {dept}
State hint: {state}

Return this exact JSON structure (fill with "N/A" if not found):
{{
  "is_job_notification": true,
  "title": "Full job title including post name and organisation. Spell out abbreviations (e.g. 'Assistant Engineer' not 'AE', 'Junior Research Fellow' not 'JRF'). Do NOT include vacancy count or dates here.",
  "department": "Full official department/organisation name",
  "vacancies": "Total number of posts as a plain integer, or N/A",
  "qualification": "Minimum educational qualification",
  "age_limit": "Age range e.g. 18-25 years",
  "last_date": "DD Month YYYY or N/A",
  "salary": "Pay scale or salary range in ₹, or N/A",
  "state": "{state_hint}",
  "category": "10th Pass / 12th Pass / Graduate / Post Graduate / Engineering",
  "apply_link": "Official apply URL or source URL",
  "summary": "2 plain-English sentences about this job opportunity",
  "meta_description": "SEO description 130-155 characters. Must include: organisation name, number of posts (if known), qualification required, and last date (if known). Example: 'DRDO SAG Paid Internship 2026: 40 posts for B.Tech/M.Tech graduates. Apply online before 15 June 2026 at the official DRDO website.'",
  "exam_relevance": "Which exams this relates to e.g. SSC CGL, Railway NTPC",
  "slug": "url-friendly-slug-max-60-chars"
}}
"""

AFFAIRS_PROMPT = """\
You are a current affairs formatter for Indian competitive exam students.
Extract key news from the raw text and return ONLY a valid JSON array, no other text.

Raw text: {raw_text}

Return a JSON array of up to 5 items, each:
{{
  "title": "Clear news headline",
  "category": "Economy / Science & Tech / International / Sports / Awards / Government Schemes / Environment",
  "summary": "2-3 sentences explaining relevance for competitive exams",
  "key_facts": ["fact1", "fact2", "fact3"],
  "exam_relevance": "UPSC / SSC / Banking / All",
  "slug": "url-friendly-slug"
}}
"""


def call_groq(prompt):
    for model in GROQ_MODELS:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            if resp.status_code == 429:
                print(f"  [GROQ] Rate limited on {model}, trying next...")
                time.sleep(3)
        except Exception as e:
            print(f"  [GROQ] Error with {model}: {e}")
    return None


def call_gemini(prompt):
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  [GEMINI] Error: {e}")
    return None


def extract_json(text):
    if not text:
        return None
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def format_with_ai(item, content_type="job"):
    raw_text   = f"{item.get('title', '')} {item.get('description', '')} {item.get('link', '')}"[:2500]
    dept       = item.get("dept", "")
    state_hint = item.get("state", "All India")

    if content_type == "job":
        prompt = JOB_PROMPT.format(raw_text=raw_text, dept=dept, state=state_hint, state_hint=state_hint)
    else:
        prompt = AFFAIRS_PROMPT.format(raw_text=raw_text)

    result = call_groq(prompt)
    if not result:
        print("  [AI] Groq failed, trying Gemini...")
        result = call_gemini(prompt)

    return extract_json(result)


# ─── HTML GENERATORS ──────────────────────────────────────────────────────────

def generate_job_html(job):
    slug  = job.get("slug") or make_slug(job.get("title", "job"))
    today = datetime.now().strftime("%d %B %Y")

    # ── Schema helpers ──────────────────────────────────────────────────────
    _ld = job.get("last_date", "") or ""
    _valid_through = ""
    for _fmt in ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            from datetime import datetime as _dt2
            _valid_through = _dt2.strptime(_ld.strip(), _fmt).strftime("%Y-%m-%dT23:59:59")
            break
        except Exception:
            pass
    if not _valid_through:
        from datetime import datetime as _dt2, timedelta as _td
        _valid_through = (_dt2.now() + _td(days=90)).strftime("%Y-%m-%dT23:59:59")
    _sal = job.get("salary", "") or ""
    _sal_desc = _sal.replace('"', "'") if _sal and _sal.strip().lower() not in ("n/a", "", "as per govt norms") else "As per Government Pay Scale"

    # ── SEO title: base title + vacancy suffix + deadline suffix ────────────
    _base_title = job.get("title", "Govt Job")
    _vac   = str(job.get("vacancies", "") or "").strip()
    _ldate = str(job.get("last_date",  "") or "").strip()
    _suffix_parts = []
    if _vac and _vac.lower() not in ("n/a", "0", ""):
        try:
            _n = int(_vac.replace(',', ''))
            _label = "Post" if _n == 1 else "Posts"
            _suffix_parts.append(f"{_n:,} {_label}")
        except ValueError:
            _suffix_parts.append(f"{_vac} Posts")
    if _ldate and _ldate.lower() not in ("n/a", ""):
        _suffix_parts.append(f"Apply by {_ldate}")
    _suffix = " — " + " | ".join(_suffix_parts) if _suffix_parts else ""
    _seo_title = f"{_base_title}{_suffix}"
    if len(_seo_title) > 75:
        _seo_title = f"{_base_title}" + (" — " + _suffix_parts[0] if _suffix_parts else "")
    if len(_seo_title) > 75:
        _seo_title = _base_title

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_seo_title} — NaukriBulletin</title>
  <meta name="description" content="{job.get('meta_description', '')}">
  <link rel="canonical" href="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:title" content="{_seo_title}">
  <meta property="og:description" content="{job.get('meta_description', '')}">
  <meta property="og:url" content="https://naukribulletin.in/jobs/{slug}/">
  <meta property="og:type" content="website">
  <meta property="og:image" content="https://naukribulletin.in/assets/logo-256.png">
  <meta name="twitter:card" content="summary">
  <meta name="robots" content="index, follow">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "{job.get('title', '')}",
    "description": "{job.get('summary', '')}",
    "hiringOrganization": {{
      "@type": "Organization",
      "name": "{job.get('department', 'Government of India')}"
    }},
    "jobLocation": {{
      "@type": "Place",
      "address": {{
        "@type": "PostalAddress",
        "streetAddress": "{job.get('department', 'Government Office')}",
        "addressLocality": "{job.get('state', 'All India')}",
        "addressRegion": "{job.get('state', 'All India')}",
        "postalCode": "110001",
        "addressCountry": "IN"
      }}
    }},
    "datePosted": "{today}",
    "validThrough": "{_valid_through}",
    "baseSalary": {{
      "@type": "MonetaryAmount",
      "currency": "INR",
      "value": {{
        "@type": "QuantitativeValue",
        "description": "{_sal_desc}"
      }}
    }},
    "employmentType": "FULL_TIME",
    "url": "https://naukribulletin.in/jobs/{slug}/"
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <a href="/jobs/" style="color:#9BA3B8;text-decoration:none;font-size:0.85rem;">← All Jobs</a>
    </div>
  </nav>

  <div style="max-width:900px;margin:20px auto;padding:0 20px;">
    <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_TOP}" data-ad-format="auto"></ins>
  </div>

  <main style="max-width:900px;margin:0 auto;padding:20px;">
    <div class="breadcrumb" style="font-size:0.8rem;color:#9BA3B8;margin-bottom:16px;">
      <a href="/" style="color:#9BA3B8;">Home</a> ›
      <a href="/jobs/" style="color:#9BA3B8;">Jobs</a> ›
      <span>{job.get('department', '')}</span>
    </div>

    <article class="job-detail">
      <div class="job-header" style="background:#0A0F2C;border-radius:16px;padding:32px;margin-bottom:24px;">
        <div style="color:#FF6B00;font-size:0.75rem;font-weight:700;letter-spacing:0.05em;margin-bottom:8px;">{job.get('department', '').upper()}</div>
        <h1 style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:#fff;margin-bottom:16px;">{job.get('title', '')}</h1>
        <p style="color:#9BA3B8;font-size:0.95rem;">{job.get('summary', '')}</p>
        <div style="margin-top:20px;display:flex;gap:12px;flex-wrap:wrap;">
          <span style="background:rgba(255,107,0,0.15);color:#FF8C33;padding:5px 12px;border-radius:6px;font-size:0.8rem;font-weight:600;">📅 Last Date: {job.get('last_date', 'N/A')}</span>
          <span style="background:rgba(19,136,8,0.15);color:#1AA60A;padding:5px 12px;border-radius:6px;font-size:0.8rem;font-weight:600;">👥 Vacancies: {job.get('vacancies', 'N/A')}</span>
        </div>
      </div>

      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;overflow:hidden;margin-bottom:24px;">
        <table style="width:100%;border-collapse:collapse;">
          <tbody>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;width:40%;background:#F7F8FA;">Department</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('department', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Total Vacancies</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('vacancies', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Qualification</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('qualification', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Age Limit</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('age_limit', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Salary / Pay Scale</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('salary', 'N/A')}</td>
            </tr>
            <tr style="border-bottom:1px solid #ECEEF2;">
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Location</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:500;">{job.get('state', 'All India')}</td>
            </tr>
            <tr>
              <td style="padding:14px 20px;color:#4A5270;font-size:0.85rem;font-weight:600;background:#F7F8FA;">Last Date</td>
              <td style="padding:14px 20px;font-size:0.9rem;font-weight:600;color:#E65100;">{job.get('last_date', 'N/A')}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style="text-align:center;margin:32px 0;">
        <a href="{job.get('apply_link') or job.get('source_url') or '#'}" target="_blank" rel="nofollow noopener"
           style="background:#FF6B00;color:#fff;padding:14px 40px;border-radius:10px;font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;text-decoration:none;display:inline-block;">
          Apply Online →
        </a>
        <p style="margin-top:10px;font-size:0.78rem;color:#9BA3B8;">You will be redirected to the official website</p>
      </div>

      <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_MID}" data-ad-format="auto"></ins>

      <!-- Coaching Affiliate Banners -->
      <div style="margin:28px 0;">
        <p style="font-size:0.75rem;font-weight:700;color:#9BA3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px;">📚 Prepare for this exam</p>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;">
          <a href="https://unacademy.com/?referral=NAUKRIBULLETIN" target="_blank" rel="noopener sponsored"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #08bd80;">
            <div style="width:40px;height:40px;border-radius:8px;background:#08bd80;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">UN</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Unacademy — Live Classes</div>
              <div style="font-size:0.74rem;color:#6b7280;">SSC, Railway, Banking &amp; State Exams</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#08bd80;color:#fff;white-space:nowrap;">Free</span>
          </a>
          <a href="https://testbook-books.myshopify.com?ref=naukri_bulletin" target="_blank" rel="noopener sponsored"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #1d4ed8;">
            <div style="width:40px;height:40px;border-radius:8px;background:#1d4ed8;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">TB</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Testbook — Mock Tests</div>
              <div style="font-size:0.74rem;color:#6b7280;">10,000+ tests · Hindi &amp; English</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#1d4ed8;color:#fff;white-space:nowrap;">Free</span>
          </a>
          <a href="https://www.adda247.com/?utm_source=naukribulletin&utm_medium=affiliate" target="_blank" rel="noopener sponsored"
             style="display:flex;align-items:center;gap:10px;border:1px solid #e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;color:inherit;border-left:4px solid #f97316;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f97316;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:#fff;flex-shrink:0;">A2</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.82rem;font-weight:700;color:#111827;">Adda247 — Study Material</div>
              <div style="font-size:0.74rem;color:#6b7280;">eBooks, Videos, Quizzes</div>
            </div>
            <span style="font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:6px;background:#f97316;color:#fff;white-space:nowrap;">Explore</span>
          </a>
        </div>
      </div>

      <div style="background:#FFF3E8;border-left:4px solid #FF6B00;border-radius:0 8px 8px 0;padding:14px 18px;margin-top:24px;">
        <p style="font-size:0.8rem;color:#4A5270;">⚠️ <strong>Disclaimer:</strong> Always verify details from the official website before applying. NaukriBulletin is not responsible for any errors in the notification details.</p>
      </div>
      <p style="font-size:0.75rem;color:#9BA3B8;margin-top:12px;">Last updated: {today}</p>
    </article>
  </main>

  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</body>
</html>"""
    return slug, html


def generate_affairs_html(affair):
    slug       = affair.get("slug") or make_slug(affair.get("title", "news"))
    today      = datetime.now().strftime("%d %B %Y")
    key_facts  = affair.get("key_facts", [])
    facts_html = "".join([f"<li style='margin-bottom:8px;font-size:0.9rem;'>{f}</li>" for f in key_facts])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{affair.get('title', 'Current Affairs')} — NaukriBulletin</title>
  <meta name="description" content="{affair.get('summary', '')[:155]}">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/{slug}/">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
</head>
<body style="font-family:'DM Sans',sans-serif;background:#F7F8FA;margin:0;">
  <nav style="background:#0A0F2C;border-bottom:3px solid #FF6B00;padding:0 20px;">
    <div style="max-width:900px;margin:0 auto;display:flex;align-items:center;height:60px;">
      <a href="/" style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;color:#fff;text-decoration:none;">NaukriBulletin</a>
    </div>
  </nav>

  <main style="max-width:900px;margin:0 auto;padding:32px 20px;">
    <div style="font-size:0.8rem;color:#9BA3B8;margin-bottom:16px;">
      <a href="/" style="color:#9BA3B8;">Home</a> ›
      <a href="/current-affairs/" style="color:#9BA3B8;">Current Affairs</a> ›
      <span>{affair.get('category', '')}</span>
    </div>
    <article>
      <div style="background:#0A0F2C;border-radius:16px;padding:32px;margin-bottom:24px;">
        <div style="color:#FF6B00;font-size:0.75rem;font-weight:700;letter-spacing:0.05em;margin-bottom:8px;">{affair.get('category', '').upper()} • {today}</div>
        <h1 style="font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;color:#fff;line-height:1.2;margin-bottom:12px;">{affair.get('title', '')}</h1>
        <div style="color:#9BA3B8;font-size:0.75rem;">Exam Relevance: <strong style="color:#FF8C33;">{affair.get('exam_relevance', 'All Exams')}</strong></div>
      </div>
      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:12px;">Summary</h2>
        <p style="color:#1A1F35;font-size:0.95rem;line-height:1.7;">{affair.get('summary', '')}</p>
      </div>
      <div style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:16px;">📌 Key Facts for Exam</h2>
        <ul style="list-style:none;padding:0;">{facts_html}</ul>
      </div>
      <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_TOP}" data-ad-format="auto"></ins>
    </article>
  </main>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</body>
</html>"""
    return slug, html


# ─── SITE BUILDER ─────────────────────────────────────────────────────────────

def save_page(slug, html, folder):
    page_dir = SITE_ROOT / folder / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    with open(page_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [SAVED] /{folder}/{slug}/")
    return str(page_dir / "index.html")


def git_push(message="Auto: Update"):
    try:
        subprocess.run(["git", "add", "."], cwd=SITE_ROOT, check=True)
        # Commit first (may fail if nothing to commit — that's fine)
        subprocess.run(["git", "commit", "-m", message], cwd=SITE_ROOT, check=False)
        # Pull with rebase to avoid conflicts with parallel runs
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=SITE_ROOT, check=False)
        subprocess.run(["git", "push"], cwd=SITE_ROOT, check=True)
        print(f"[GIT] Pushed: {message}")
    except subprocess.CalledProcessError as e:
        print(f"[GIT] Push failed (maybe nothing to commit): {e}")


# ─── MAIN RUNNER ──────────────────────────────────────────────────────────────

def run():
    run_label = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    print(f"\n{'='*60}")
    print(f"NaukriBulletin — {run_label}")
    print(f"Sources: {len(SOURCES)} | Phase 1 upgraded scraper")
    print(f"{'='*60}\n")

    processed     = load_processed()
    new_pages     = 0
    failed_src    = []
    collected_jobs = []

    # Sort by priority (1 = highest) so most important sources process first
    # Track titles seen this run to avoid near-duplicate pages across sources
    seen_titles_this_run = set()

    for source in sorted(SOURCES, key=lambda s: s.get("priority", 9)):
        dept = source["dept"]
        url  = source["url"]
        print(f"\n[FETCH] {dept}")
        print(f"  URL: {url}")

        if source["type"] == "rss":
            items = scrape_rss(url, dept, fallback_url=source.get("fallback_url"))
        else:
            selector = source.get("selector")
            items = scrape_html_smart(url, dept, selector=selector)

        if not items:
            print(f"  ⚠ No items fetched — source may be down")
            failed_src.append(dept)
            continue

        print(f"  ✓ Got {len(items)} items")

        for item in items:
            # Carry state hint from source config into item
            if source.get("state"):
                item["state"] = source["state"]

            item_hash = make_hash(item.get("title", "") + item.get("description", "")[:100])
            if item_hash in processed:
                continue

            # Skip thin/generic nav titles — these create low-quality pages
            _raw_title = item.get("title", "").strip()
            _SKIP_TITLES = {
                "active examinations", "forthcoming examinations", "recruitment advertisements",
                "recruitment tests", "recruitment requisition", "online recruitment application",
                "online application submission", "revised syllabus and scheme", "syllabus and scheme",
                "examination rules", "recruitment methods", "examination schedule",
                "scheme of examination", "direct recruitment", "status of applications",
                "admit cards", "admit cards/call letters", "written/screening test results",
                "interview schedule", "tentative interview dates", "tentative exam calendar",
                "proposed examination dates", "marks of recommended candidates",
                "marks of all interviewed candidates", "status of recruitment cases",
                "recruitment cases kept on hold", "status of lateral recruitment cases",
                "contact us", "home", "apply online", "online application", "click here",
                "download advertisement", "selection procedure", "instructions for written exam",
                "vacancy dashboard", "bed occupancy/vacancy dashboard profile",
                "apply under mimp scheme", "current vacancies", "archived vacancies",
                "notice of exam and circulars", "combined examination",
                "all oms related to combined exam", "section a indicative syllabus",
                "section-b indicative syllabus", "new examination and interview scheme",
                "list of chairpersons", "computer based recruitment test (cbrt)",
                "otr/apply online (recruitment portal)", "instructions / interview letter",
                "previous question papers", "results previous question papers syllabus archive",
                "transfer/postings", "recruitment support :",
            }
            if _raw_title.lower().strip() in _SKIP_TITLES:
                continue
            # Skip very short titles (likely nav links)
            if len(_raw_title) < 15:
                continue
            # Skip titles that are phone numbers, times, salary ranges
            if re.match(r'^[\d\s\-\+\:\.]+$', _raw_title):
                continue
            if re.match(r'^\d{2}:\d{2}', _raw_title):
                continue

            # Skip near-duplicate titles seen in this run (across different sources)
            title_key = re.sub(r"\s+", " ", item.get("title", "").lower().strip())[:80]
            if title_key in seen_titles_this_run:
                continue
            seen_titles_this_run.add(title_key)

            content_type = source.get("content_type", "job")
            print(f"  → Processing: {item.get('title', '')[:70]}")
            time.sleep(0.6)  # be polite to AI APIs

            formatted = format_with_ai(item, content_type)
            if not formatted:
                print("  ✗ AI formatting failed, skipping")
                continue

            if content_type == "job":
                jobs = [formatted] if isinstance(formatted, dict) else formatted
                for job in jobs:
                    if not job.get("is_job_notification", True):
                        continue
                    # Preserve state from source if AI returned N/A
                    if source.get("state") and job.get("state") in ("N/A", "All India", ""):
                        job["state"] = source["state"]
                    slug, html = generate_job_html(job)
                    if is_valid_slug(slug, item.get("title","")):
                        save_page(slug, html, "jobs")
                    else:
                        print(f"  [SKIP] Invalid slug: {slug}")
                    new_pages += 1
                    # Collect for JSON export (notify.py needs this)
                    job["id"]   = job.get("id") or slug
                    job["slug"] = slug
                    job["url"]  = f"{SITE_URL}/jobs/{slug}/"
                    collected_jobs.append(job)
            else:
                affairs = formatted if isinstance(formatted, list) else [formatted]
                for affair in affairs:
                    slug, html = generate_affairs_html(affair)
                    if is_valid_slug(slug, item.get("title","")):
                        save_page(slug, html, "current-affairs")
                    else:
                        print(f"  [SKIP] Invalid slug: {slug}")
                    new_pages += 1

            processed.add(item_hash)

    save_processed(processed)

    print(f"\n{'='*60}")
    print(f"✅ Done — {new_pages} new pages generated")
    if failed_src:
        print(f"⚠  Failed sources ({len(failed_src)}): {', '.join(failed_src)}")
    print(f"{'='*60}\n")

    rebuild_homepage()
    rebuild_jobs_listing()
    rebuild_affairs_listing()
    rebuild_syllabus()

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sitemap_gen", SITE_ROOT / "scripts" / "sitemap_gen.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run()
    except Exception as e:
        print(f"[SITEMAP] Error: {e}")

    today_str = date.today().strftime("%d %b %Y")
    if collected_jobs:
        export_jobs_json(collected_jobs)

    if new_pages > 0:
        git_push(f"Auto: {new_pages} new pages — {today_str}")
    else:
        git_push(f"Auto: Refresh listings — {today_str}")


# ─── LISTING REBUILDERS ───────────────────────────────────────────────────────
# (kept identical to original — only listing logic, no scraper changes needed)

def get_job_meta_from_html(html_path):
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        dept_tag = soup.find(style=lambda s: s and "letter-spacing" in s and "FF6B00" in s)
        dept = dept_tag.get_text(strip=True).title() if dept_tag else ""

        rows = soup.find_all("tr")
        data = {}
        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 2:
                data[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)

        slug         = html_path.parent.name
        last_date    = data.get("last date", "N/A")
        vacancies    = data.get("total vacancies", "N/A")
        salary       = data.get("salary / pay scale", "N/A")
        location     = data.get("location", "All India")
        qualification = data.get("qualification", "N/A")

        qual_lower = qualification.lower()
        if any(x in qual_lower for x in ["engineer", "b.tech", "b.e"]):
            category, cat_key = "Engineering", "engineering"
        elif any(x in qual_lower for x in ["post graduate", "master", "mba"]):
            category, cat_key = "Post Graduate", "state"
        elif any(x in qual_lower for x in ["graduate", "degree", "b.sc", "b.com", "ba"]):
            category, cat_key = "Graduate", "graduate"
        elif any(x in qual_lower for x in ["12th", "intermediate", "hsc"]):
            category, cat_key = "12th Pass", "12th"
        elif any(x in qual_lower for x in ["10th", "matriculation"]):
            category, cat_key = "10th Pass", "10th"
        else:
            category, cat_key = "Graduate", "graduate"

        td = (title + " " + dept).lower()
        if any(x in td for x in ["ssc", "cgl", "chsl", "mts", "gd constable"]):
            tab_cat = "ssc"
        elif any(x in td for x in ["railway", "rrb", "ntpc", "group d", "loco"]):
            tab_cat = "railway"
        elif any(x in td for x in ["bank", "sbi", "ibps", "rbi", "nabard"]):
            tab_cat = "banking"
        elif any(x in td for x in ["upsc", "ias", "ips", "civil service", "nda", "cds"]):
            tab_cat = "upsc"
        elif any(x in td for x in ["army", "navy", "air force", "defence", "agniveer"]):
            tab_cat = "defence"
        elif any(x in td for x in ["police", "constable", "crpf", "bsf", "cisf"]):
            tab_cat = "police"
        elif any(x in td for x in ["teacher", "professor", "lecturer", "kvs", "nvs"]):
            tab_cat = "teaching"
        else:
            tab_cat = "state"

        emoji_map = {
            "ssc": "📋", "railway": "🚂", "banking": "🏦", "upsc": "🏛️",
            "defence": "🪖", "police": "👮", "teaching": "📚", "state": "🏢",
        }
        return {
            "slug": slug, "title": title, "dept": dept, "last_date": last_date,
            "vacancies": vacancies, "salary": salary, "location": location,
            "category": category, "tab_cat": tab_cat, "emoji": emoji_map.get(tab_cat, "📋"),
        }
    except Exception as e:
        print(f"[META] Error reading {html_path}: {e}")
        return None


def build_job_card(job):
    urgency_badge = ""
    ld = job.get("last_date", "N/A")
    if ld != "N/A":
        try:
            for fmt in ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    days_left = (datetime.strptime(ld, fmt).date() - date.today()).days
                    urgency_badge = '<span class="badge badge-urgent">🔥 URGENT</span>' if days_left <= 7 else '<span class="badge badge-new">🟢 NEW</span>'
                    break
                except ValueError:
                    continue
        except Exception:
            pass
    if not urgency_badge:
        urgency_badge = '<span class="badge badge-new">🟢 NEW</span>'

    return f"""
      <a href="/jobs/{job['slug']}/" class="card fade-up" style="text-decoration:none;color:inherit;display:block;position:relative;overflow:hidden;" data-category="{job['tab_cat']}">
        <div style="position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--saffron);"></div>
        <div style="padding-left:12px;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
            <div style="display:flex;gap:10px;align-items:flex-start;flex:1;">
              <div style="width:42px;height:42px;border-radius:10px;background:var(--saffron-pale);display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">{job['emoji']}</div>
              <div>
                <div style="font-size:0.72rem;color:var(--grey-400);font-weight:500;margin-bottom:2px;">{job['dept']}</div>
                <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--navy);">{job['title']}</div>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0;">
              {urgency_badge}
              <span class="badge badge-category">{job['category']}</span>
            </div>
          </div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;">
            <span style="font-size:0.8rem;color:var(--grey-700);">👥 {job['vacancies']}</span>
            <span style="font-size:0.8rem;color:var(--grey-700);">📍 {job['location']}</span>
            <span style="font-size:0.8rem;color:var(--grey-700);">💰 {job['salary']}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--grey-200);">
            <span style="font-size:0.8rem;color:#E65100;font-weight:600;">⏰ Last Date: {job['last_date']}</span>
            <span style="background:var(--navy);color:var(--white);padding:5px 14px;border-radius:6px;font-size:0.78rem;font-weight:600;">Apply Now →</span>
          </div>
        </div>
      </a>"""




def rebuild_syllabus():
    """
    Auto-generates syllabus/index.html by scanning all job pages.
    Groups them by exam category (SSC / Railway / Banking / UPSC / Defence / Police / Teaching / State).
    Called automatically after every scraper run.
    """
    from datetime import datetime

    jobs_dir  = SITE_ROOT / "jobs"
    out_path  = SITE_ROOT / "syllabus" / "index.html"
    yr        = datetime.now().year

    # Category config: tab_cat → display label, emoji, colour
    CATS = [
        ("ssc",      "SSC",         "📋", "#FF6B00"),
        ("railway",  "Railway",     "🚂", "#1565C0"),
        ("banking",  "Banking",     "🏦", "#2E7D32"),
        ("upsc",     "UPSC / IAS",  "🏛️", "#6A1B9A"),
        ("defence",  "Defence",     "🪖", "#BF360C"),
        ("police",   "Police",      "👮", "#37474F"),
        ("teaching", "Teaching",    "📚", "#00695C"),
        ("state",    "State PSC",   "🏢", "#283593"),
    ]
    cat_map = {c[0]: c for c in CATS}

    # Collect all jobs grouped by tab_cat
    grouped = {c[0]: [] for c in CATS}
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir():
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        meta = get_job_meta_from_html(idx)
        if not meta or not meta.get("title"):
            continue
        cat = meta.get("tab_cat", "state")
        if cat in grouped:
            grouped[cat].append(meta)

    total = sum(len(v) for v in grouped.values())
    print(f"[SYLLABUS] Rebuilding syllabus page with {total} jobs across {len(CATS)} categories")

    # ── Tab buttons ───────────────────────────────────────────────────────────
    tab_buttons = '\n          '.join(
        f'<button class="stab{" stab-active" if i==0 else ""}" '
        f'onclick="filterSyllabus(\'{c[0]}\',this)">{c[2]} {c[1]}</button>'
        for i, c in enumerate(CATS)
    )

    # ── Syllabus cards per category ───────────────────────────────────────────
    def make_section(cat_key):
        cfg = cat_map[cat_key]
        jobs = grouped[cat_key]
        if not jobs:
            return ""

        rows = ""
        for job in jobs[:40]:          # cap at 40 per category
            title     = job.get("title", "")
            slug      = job.get("slug", "")
            last_date = job.get("last_date", "N/A")
            vacancies = job.get("vacancies", "N/A")
            er        = job.get("exam_relevance", "")
            rows += f"""
              <a href="/jobs/{slug}/" class="syl-row" style="display:flex;align-items:center;gap:12px;
                 padding:12px 16px;border-bottom:1px solid var(--grey-200);text-decoration:none;
                 color:inherit;transition:background .1s;" onmouseover="this.style.background=\'#fffbf5\'"
                 onmouseout="this.style.background=\'\'" >
                <div style="flex:1;min-width:0;">
                  <div style="font-size:0.88rem;font-weight:600;color:var(--navy);
                       white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{title}</div>
                  <div style="font-size:0.75rem;color:var(--grey-400);margin-top:2px;">
                    {"📌 " + er if er else ""}
                  </div>
                </div>
                <div style="display:flex;gap:8px;flex-shrink:0;align-items:center;">
                  <span style="font-size:0.74rem;color:var(--grey-700);">👥 {vacancies}</span>
                  <span style="font-size:0.74rem;color:#E65100;font-weight:600;
                       white-space:nowrap;">⏰ {last_date}</span>
                  <span style="background:var(--navy);color:#fff;padding:4px 10px;
                       border-radius:6px;font-size:0.72rem;font-weight:600;">Syllabus →</span>
                </div>
              </a>"""

        return f"""
        <div class="scat" data-cat="{cat_key}" style="margin-bottom:24px;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="width:38px;height:38px;border-radius:9px;background:{cfg[3]}22;
                 display:flex;align-items:center;justify-content:center;font-size:1.1rem;">{cfg[2]}</div>
            <div>
              <div style="font-family:var(--font-display);font-size:1.05rem;font-weight:700;
                   color:var(--navy);">{cfg[1]} Syllabus {yr}</div>
              <div style="font-size:0.75rem;color:var(--grey-400);">{len(jobs)} active notifications</div>
            </div>
          </div>
          <div style="background:var(--white);border-radius:12px;border:1.5px solid var(--grey-200);
               overflow:hidden;">
            {rows}
            <div style="padding:10px 16px;background:#fafafa;text-align:center;">
              <a href="/jobs/{cat_key}/" style="font-size:0.8rem;color:var(--saffron);
                 font-weight:600;text-decoration:none;">View all {cfg[1]} jobs →</a>
            </div>
          </div>
        </div>"""

    sections_html = "\n".join(make_section(c[0]) for c in CATS)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exam Syllabus {yr} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="Complete exam syllabus {yr} for SSC CGL, CHSL, Railway NTPC, SBI PO, UPSC, IBPS and 200+ govt exams. Updated daily at NaukriBulletin.in">
  <link rel="canonical" href="https://naukribulletin.in/syllabus/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{
        appId: "89e83d08-e30e-46f9-baec-f0167f8baa35",
        notifyButton: {{ enable: true, size: "medium", position: "bottom-left" }}
      }});
    }});
  </script>
  <style>
    .stab {{
      border: none; background: var(--grey-100); color: var(--grey-700);
      padding: 7px 16px; border-radius: 20px; font-size: 0.82rem;
      font-weight: 600; cursor: pointer; transition: all .15s; white-space: nowrap;
    }}
    .stab:hover {{ background: var(--saffron-pale); color: var(--saffron); }}
    .stab-active {{ background: var(--saffron) !important; color: #fff !important; }}
    .scat {{ transition: opacity .2s; }}
    .scat.hidden {{ display: none; }}
  </style>
</head>
<body>

  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/syllabus/" class="active">Syllabus</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>

  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="color:var(--grey-400);font-size:0.8rem;margin-bottom:8px;">
        <a href="/" style="color:var(--grey-400);text-decoration:none;">Home</a> › Syllabus
      </div>
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        📚 Exam <span style="color:var(--saffron);">Syllabus {yr}</span>
      </h1>
      <p style="color:var(--grey-400);font-size:0.95rem;">{total} active notifications — SSC · Railway · Banking · UPSC · Defence · State PSC</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:0 auto;padding:0 20px;">
    <div class="ad-slot ad-banner">Advertisement</div>
  </div>

  <div class="container">
    <div style="overflow-x:auto;padding-bottom:4px;margin-bottom:20px;">
      <div style="display:flex;gap:8px;min-width:max-content;">
        <button class="stab stab-active" onclick="filterSyllabus(\'all\',this)">🗂 All Exams</button>
        {tab_buttons}
      </div>
    </div>

    <div id="syl-sections">
      {sections_html}
    </div>

  </div>

  <footer style="background:var(--navy);color:var(--grey-400);padding:32px 20px;margin-top:48px;text-align:center;font-size:0.82rem;">
    <div style="max-width:1200px;margin:0 auto;">
      <p>© {yr} NaukriBulletin.in — Updated automatically 3× daily</p>
      <div style="margin-top:12px;display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
        <a href="/jobs/" style="color:var(--grey-400);text-decoration:none;">Latest Jobs</a>
        <a href="/current-affairs/" style="color:var(--grey-400);text-decoration:none;">Current Affairs</a>
        <a href="/age-calculator/" style="color:var(--grey-400);text-decoration:none;">Age Calculator</a>
        <a href="/answer-key/" style="color:var(--grey-400);text-decoration:none;">Answer Key</a>
      </div>
    </div>
  </footer>

  <script>
    function filterSyllabus(cat, btn) {{
      document.querySelectorAll('.stab').forEach(b => b.classList.remove('stab-active'));
      btn.classList.add('stab-active');
      document.querySelectorAll('.scat').forEach(s => {{
        if (cat === 'all' || s.dataset.cat === cat) {{
          s.classList.remove('hidden');
        }} else {{
          s.classList.add('hidden');
        }}
      }});
    }}
  </script>
</body>
</html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[SYLLABUS] ✅ Written syllabus/index.html ({total} jobs, {len(CATS)} categories)")



def rebuild_homepage():
    """
    Regenerates index.html with real scraped jobs and current affairs.
    Fixes: stale 2025 content, fake ticker, fake hero stats, fake current affairs.
    """
    from datetime import datetime, date

    yr       = datetime.now().year
    out_path = SITE_ROOT / "index.html"

    jobs_dir    = SITE_ROOT / "jobs"
    affairs_dir = SITE_ROOT / "current-affairs"

    # ── Collect real jobs ──────────────────────────────────────────────────
    SKIP = {"ssc","railway","banking","upsc","defence","police","teaching","state",
            "10th-pass","12th-pass","graduate","all-india","uttar-pradesh","bihar",
            "madhya-pradesh","rajasthan","tamil-nadu","karnataka","maharashtra",
            "gujarat","kerala","engineering","all-india-government-jobs",
            "government-jobs-2026","psu-jobs-2026","graduate-govt-jobs-2026",
            "iti-govt-jobs-2026","mba-govt-jobs-2026","mca-govt-jobs-2026",
            "law-govt-jobs-2026","govt-bank-jobs-2026","govt-jobs-closing-today",
            "non-executive-posts","faculty-posts-recruitment"}

    all_jobs = []
    seen_titles = set()
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir() or job_dir.name in SKIP:
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        meta = get_job_meta_from_html(idx)
        if not meta or not meta.get("title"):
            continue
        # Deduplicate by normalised title
        norm = meta["title"].lower().strip()[:60]
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        all_jobs.append(meta)

    # Take top 8 newest for homepage (prioritise ones with known vacancy count)
    def sort_key(j):
        v = j.get("vacancies","N/A")
        has_vac = 0 if v in ("N/A","","0") else 1
        return (has_vac, j.get("slug",""))
    featured = sorted(all_jobs, key=sort_key, reverse=True)[:8]

    total_jobs      = len(all_jobs)
    total_vacancies = 0
    for j in all_jobs:
        v = j.get("vacancies","N/A")
        try:
            total_vacancies += int(str(v).replace(",","").replace("+","").strip())
        except Exception:
            pass

    # ── Collect real current affairs ──────────────────────────────────────
    CAT_EMOJI = {
        "economy":"📈","science & tech":"🚀","international":"🌍",
        "sports":"🏆","awards":"🏅","government schemes":"🏛️",
        "environment":"🌿","politics":"🗳️","default":"📰"
    }
    affairs = []
    for adir in sorted(affairs_dir.iterdir(), reverse=True):
        if not adir.is_dir():
            continue
        idx = adir / "index.html"
        if not idx.exists():
            continue
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(idx.read_text(encoding="utf-8"), "html.parser")
            h1   = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
            if not title or len(title) < 10:
                continue
            cat_el = soup.find(class_="affair-category") or soup.find("span", string=lambda s: s and s.isupper() and len(s)<30)
            cat    = cat_el.get_text(strip=True).lower() if cat_el else "default"
            summary_el = soup.find("p")
            summary = summary_el.get_text(strip=True)[:120] if summary_el else ""
            affairs.append({
                "slug":    adir.name,
                "title":   title,
                "cat":     cat.upper() if cat != "default" else "CURRENT AFFAIRS",
                "emoji":   CAT_EMOJI.get(cat, "📰"),
                "summary": summary,
            })
        except Exception:
            continue
        if len(affairs) >= 4:
            break

    # ── Build ticker from real job titles ────────────────────────────────
    ticker_items = []
    for j in all_jobs[:12]:
        t = j.get("title","")
        v = j.get("vacancies","")
        ld = j.get("last_date","")
        line = t[:55]
        if v and v != "N/A":   line += f" — {v} Vacancies"
        if ld and ld != "N/A": line += f" | Last: {ld}"
        ticker_items.append(line)
    # Duplicate for seamless scroll
    ticker_spans = "".join(f"<span>{t}</span>\n            " for t in ticker_items * 2)

    # ── Build job cards ───────────────────────────────────────────────────
    def job_card(job):
        title    = job.get("title","")
        dept     = job.get("dept","")
        slug     = job.get("slug","")
        vac      = job.get("vacancies","N/A")
        loc      = job.get("location","All India") or "All India"
        sal      = job.get("salary","N/A") or "N/A"
        cat      = job.get("category","Graduate") or "Graduate"
        ld       = job.get("last_date","N/A") or "N/A"
        emoji    = job.get("emoji","📋")
        tab_cat  = job.get("tab_cat","state")

        try:
            urgent = False
            for fmt in ["%d %B %Y","%d %b %Y","%Y-%m-%d","%d/%m/%Y","%d-%m-%Y"]:
                try:
                    days = (datetime.strptime(ld, fmt).date() - date.today()).days
                    urgent = days <= 7
                    break
                except ValueError:
                    continue
        except Exception:
            urgent = False

        badge = '<span class="badge badge-urgent">🔥 URGENT</span>' if urgent else '<span class="badge badge-new">🟢 NEW</span>'
        deadline_label = "Last Date to Apply" if ld != "N/A" else "Apply Now"
        deadline_val   = f"⏰ {ld}" if ld != "N/A" else "→ Open"

        sal_display = sal if sal and sal != "N/A" else "As per govt norms"

        return f"""
        <a href="/jobs/{slug}/" class="job-card fade-up" data-category="{tab_cat}">
          <div class="job-card-top">
            <div class="job-dept">
              <div class="dept-icon">{emoji}</div>
              <div>
                <div class="dept-name">{dept}</div>
                <div class="job-title">{title}</div>
              </div>
            </div>
            <div class="job-badges">
              {badge}
              <span class="badge badge-category">{cat}</span>
            </div>
          </div>
          <div class="job-meta">
            <div class="meta-item"><span class="meta-icon">👥</span> {vac} Vacancies</div>
            <div class="meta-item"><span class="meta-icon">📍</span> {loc}</div>
            <div class="meta-item"><span class="meta-icon">💰</span> {sal_display}</div>
          </div>
          <div class="job-deadline">
            <div>
              <div class="deadline-text">{deadline_label}</div>
              <div class="deadline-date">{deadline_val}</div>
            </div>
            <button class="apply-btn">Apply Now →</button>
          </div>
        </a>"""

    job_cards_html = "\n".join(job_card(j) for j in featured)

    # ── Build current affairs cards ───────────────────────────────────────
    def affair_card(a):
        return f"""
        <a href="/current-affairs/{a['slug']}/" style="background:var(--white);border-radius:10px;padding:16px;border:1.5px solid var(--grey-200);text-decoration:none;color:inherit;display:flex;gap:12px;align-items:flex-start;transition:all 0.2s;" onmouseover="this.style.borderColor='var(--saffron)'" onmouseout="this.style.borderColor='var(--grey-200)'">
          <span style="font-size:1.5rem;flex-shrink:0;">{a['emoji']}</span>
          <div>
            <div style="font-size:0.7rem;color:var(--saffron);font-weight:700;margin-bottom:4px;">{a['cat']}</div>
            <div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--navy);margin-bottom:4px;">{a['title'][:80]}</div>
            <div style="font-size:0.8rem;color:var(--grey-700);">{a['summary']}</div>
          </div>
        </a>"""

    affairs_html = "\n".join(affair_card(a) for a in affairs) if affairs else """
        <a href="/current-affairs/" style="background:var(--white);border-radius:10px;padding:16px;border:1.5px solid var(--grey-200);text-decoration:none;color:inherit;display:flex;gap:12px;align-items:flex-start;">
          <span style="font-size:1.5rem;">📰</span>
          <div><div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--navy);">Latest Current Affairs</div>
          <div style="font-size:0.8rem;color:var(--grey-700);">Updated daily for SSC, Banking, UPSC exams.</div></div>
        </a>"""

    vac_display  = f"{total_vacancies:,}+" if total_vacancies > 0 else "50,000+"
    jobs_display = f"{total_jobs}+"

    # ── Read existing index.html and do surgical replacements ─────────────
    html = out_path.read_text(encoding="utf-8")

    # 1. Fix meta keywords year
    html = html.replace("govt job 2025", f"govt job {yr}")

    # 2. Fix footer copyright year
    html = html.replace("© 2025 NaukriBulletin", f"© {yr} NaukriBulletin")

    # 3. Fix ticker — replace entire ticker-text div content
    import re
    html = re.sub(
        r'(<div class="ticker-text">).*?(</div>\s*</div>\s*</div>\s*</div>\s*</div>\s*<!-- HERO -->)',
        lambda m: m.group(1) + "\n            " + ticker_spans + "\n          " + m.group(2),
        html, flags=re.DOTALL
    )

    # 4. Fix hero stats — job count (matches: 221<span>+</span>)
    html = re.sub(
        r'<div class="stat-num">\d+<span>\+</span></div>\s*<div class="stat-label">Active Job Notifications</div>',
        f'<div class="stat-num">{total_jobs}<span>+</span></div>\n          <div class="stat-label">Active Job Notifications</div>',
        html
    )

    # 5. Fix job cards — replace the jobs-grid div content
    html = re.sub(
        r'(<div class="jobs-grid">).*?(</div>\s*<!-- AD -->)',
        lambda m: m.group(1) + job_cards_html + "\n\n      " + m.group(2),
        html, flags=re.DOTALL
    )

    # 6. Fix current affairs — replace the 3 hardcoded affair cards
    html = re.sub(
        r'(<div style="display: flex; flex-direction: column; gap: 10px;">).*?(</div>\s*</section>)',
        lambda m: m.group(1) + affairs_html + "\n\n      " + m.group(2),
        html, flags=re.DOTALL
    )

    out_path.write_text(html, encoding="utf-8")
    print(f"[HOMEPAGE] ✅ index.html rebuilt — {total_jobs} jobs, {len(affairs)} current affairs, ticker updated")

def rebuild_jobs_listing():
    jobs_dir = SITE_ROOT / "jobs"
    jobs = []
    for job_dir in sorted(jobs_dir.iterdir(), reverse=True):
        if not job_dir.is_dir():
            continue
        index_file = job_dir / "index.html"
        if not index_file.exists():
            continue
        meta = get_job_meta_from_html(index_file)
        if meta and meta.get("title"):
            jobs.append(meta)

    print(f"[LISTING] Rebuilding /jobs/ with {len(jobs)} jobs")
    cards_html = "\n".join(build_job_card(j) for j in jobs)
    count      = len(jobs)
    yr         = datetime.now().year

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Latest Govt Jobs {yr} — SSC, Railway, Banking, UPSC | NaukriBulletin</title>
  <meta name="description" content="All latest govt job notifications {yr}. SSC, Railway, Banking, UPSC, State PSC jobs. Direct from official sources. Free daily alerts.">
  <link rel="canonical" href="https://naukribulletin.in/jobs/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-6WQJ4W7T1N"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-6WQJ4W7T1N');</script>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/" class="active">Latest Jobs</a></li>
        <li><a href="/current-affairs/">Current Affairs</a></li>
        <li><a href="/cut-off/">Cut Off</a></li>
        <li><a href="/admit-card/">Admit Card</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>

  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <div style="color:var(--grey-400);font-size:0.8rem;margin-bottom:8px;">
        <a href="/" style="color:var(--grey-400);text-decoration:none;">Home</a> › Latest Jobs
      </div>
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        Latest <span style="color:var(--saffron);">Govt Jobs {yr}</span>
      </h1>
      <p style="color:var(--grey-400);font-size:0.95rem;">{count}+ active notifications — from official sources, updated 3× daily</p>
    </div>
  </div>

  <div style="max-width:1200px;margin:0 auto;padding:0 20px;">
    <div class="ad-slot ad-banner">Advertisement</div>
  </div>

  <div class="container">
    <div class="two-col">
      <section>
        <div class="filter-tabs">
          <div class="tab active" onclick="filterJobs('all',this)">All</div>
          <div class="tab" onclick="filterJobs('ssc',this)">SSC</div>
          <div class="tab" onclick="filterJobs('railway',this)">Railway</div>
          <div class="tab" onclick="filterJobs('banking',this)">Banking</div>
          <div class="tab" onclick="filterJobs('upsc',this)">UPSC</div>
          <div class="tab" onclick="filterJobs('defence',this)">Defence</div>
          <div class="tab" onclick="filterJobs('police',this)">Police</div>
          <div class="tab" onclick="filterJobs('teaching',this)">Teaching</div>
          <div class="tab" onclick="filterJobs('state',this)">State PSC</div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <span style="font-size:0.85rem;color:var(--grey-700);">Showing <strong id="job-count">{count}</strong> jobs</span>
          <select id="sort-select" onchange="sortJobs(this.value)" style="font-family:var(--font-body);font-size:0.82rem;border:1.5px solid var(--grey-200);border-radius:6px;padding:5px 10px;background:var(--white);color:var(--text);">
            <option value="newest">Newest First</option>
            <option value="urgent">Last Date (Urgent)</option>
          </select>
        </div>
        <div id="jobs-list" style="display:flex;flex-direction:column;gap:12px;">
{cards_html}
        </div>
      </section>

      <aside class="sidebar">
        <div class="telegram-cta">
          <h3>📢 Free Job Alerts</h3>
          <p>Get daily alerts on Telegram</p>
          <a href="https://t.me/naukribulletin24" class="telegram-btn">Join Channel →</a>
        </div>
        <div class="card">
          <div style="font-family:var(--font-display);font-size:1rem;font-weight:700;color:var(--navy);margin-bottom:14px;">🔍 Filter by Category</div>
          <select onchange="filterJobs(this.value,null)" style="width:100%;font-family:var(--font-body);font-size:0.85rem;border:1.5px solid var(--grey-200);border-radius:8px;padding:8px 12px;color:var(--text);background:var(--white);">
            <option value="all">All Categories</option>
            <option value="ssc">SSC</option>
            <option value="railway">Railway</option>
            <option value="banking">Banking</option>
            <option value="upsc">UPSC</option>
            <option value="defence">Defence</option>
            <option value="police">Police</option>
            <option value="teaching">Teaching</option>
            <option value="state">State PSC</option>
          </select>
        </div>
        <div class="ad-slot ad-sidebar">Advertisement</div>
      </aside>
    </div>
  </div>

  <footer>
    <div class="footer-inner">
      <div class="footer-grid">
        <div class="footer-brand">
          <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
          <p>India's smartest govt job portal. Direct from official sources — not aggregators. AI-powered daily alerts, always free.</p>
        </div>
        <div class="footer-col">
          <h4>Central Jobs</h4>
          <ul>
            <li><a href="/jobs/">SSC Jobs</a></li>
            <li><a href="/jobs/">Railway Jobs</a></li>
            <li><a href="/jobs/">Banking Jobs</a></li>
            <li><a href="/jobs/">UPSC Jobs</a></li>
            <li><a href="/jobs/">Defence Jobs</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>State PSC Jobs</h4>
          <ul>
            <li><a href="/jobs/">UPPSC (UP)</a></li>
            <li><a href="/jobs/">BPSC (Bihar)</a></li>
            <li><a href="/jobs/">MPPSC (MP)</a></li>
            <li><a href="/jobs/">RPSC (Rajasthan)</a></li>
            <li><a href="/jobs/">TNPSC (Tamil Nadu)</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>Resources</h4>
          <ul>
            <li><a href="/cut-off/">Cut Off</a></li>
            <li><a href="/admit-card/">Admit Cards</a></li>
            <li><a href="/syllabus/">Syllabus</a></li>
            <li><a href="/current-affairs/">Current Affairs</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <p>© {yr} NaukriBulletin.in — All Rights Reserved</p>
        <p>
          <a href="/privacy/" style="color:var(--grey-400);text-decoration:none;margin-right:16px;">Privacy Policy</a>
          <a href="/disclaimer/" style="color:var(--grey-400);text-decoration:none;">Disclaimer</a>
        </p>
      </div>
    </div>
  </footer>

  <script>
    function filterJobs(category, el) {{
      if (el) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        el.classList.add('active');
      }}
      const cards = document.querySelectorAll('#jobs-list a');
      let count = 0;
      cards.forEach(card => {{
        const show = category === 'all' || card.dataset.category === category;
        card.style.display = show ? 'block' : 'none';
        if (show) count++;
      }});
      document.getElementById('job-count').textContent = count;
    }}
    function sortJobs(val) {{
      const list = document.getElementById('jobs-list');
      const cards = Array.from(list.querySelectorAll('a'));
      if (val === 'urgent') {{
        cards.sort((a, b) => {{
          const da = a.querySelector('span[style*="E65100"]')?.textContent || '';
          const db = b.querySelector('span[style*="E65100"]')?.textContent || '';
          return da.localeCompare(db);
        }});
        cards.forEach(c => list.appendChild(c));
      }}
    }}
  </script>
</body>
</html>"""

    with open(SITE_ROOT / "jobs" / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ /jobs/index.html rebuilt with {count} jobs")


def get_affairs_meta_from_html(html_path):
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        slug  = html_path.parent.name
        cat_div = soup.find(style=lambda s: s and "FF6B00" in str(s) and "letter-spacing" in str(s))
        cat_raw = cat_div.get_text(strip=True) if cat_div else "General"
        category = cat_raw.split("•")[0].strip().title() if "•" in cat_raw else cat_raw.strip().title()
        exam_tag = soup.find(style=lambda s: s and "FF8C33" in str(s))
        exam_rel = exam_tag.get_text(strip=True) if exam_tag else "All Exams"
        summary_p = soup.find("p", style=lambda s: s and "1.7" in str(s))
        summary = (summary_p.get_text(strip=True)[:120] + "...") if summary_p else ""
        mtime    = html_path.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%d %b")
        cat_class_map = {
            "economy": "cat-economy", "science": "cat-science",
            "international": "cat-international", "sports": "cat-sports",
            "awards": "cat-awards", "government": "cat-government",
            "environment": "cat-environment",
        }
        cat_class = next((v for k, v in cat_class_map.items() if k in category.lower()), "cat-government")
        return {"slug": slug, "title": title, "category": category, "cat_class": cat_class,
                "exam_rel": exam_rel, "summary": summary, "date_str": date_str}
    except Exception as e:
        print(f"[META] Error reading {html_path}: {e}")
        return None


def rebuild_affairs_listing():
    affairs_dir = SITE_ROOT / "current-affairs"
    items = []
    for item_dir in sorted(affairs_dir.iterdir(), reverse=True):
        if not item_dir.is_dir():
            continue
        index_file = item_dir / "index.html"
        if not index_file.exists():
            continue
        meta = get_affairs_meta_from_html(index_file)
        if meta and meta.get("title"):
            items.append(meta)

    print(f"[LISTING] Rebuilding /current-affairs/ with {len(items)} items")
    cards_html = ""
    for item in items:
        parts = item["date_str"].split(" ")
        day   = parts[0] if parts else ""
        month = parts[1] if len(parts) > 1 else ""
        cards_html += f"""
      <a href="/current-affairs/{item['slug']}/" class="affairs-card fade-up" style="text-decoration:none;color:inherit;">
        <div style="background:var(--navy);border-radius:8px;padding:8px 10px;text-align:center;min-width:48px;color:var(--white);flex-shrink:0;">
          <div style="font-family:var(--font-display);font-size:1.2rem;font-weight:800;line-height:1;">{day}</div>
          <div style="font-size:0.65rem;opacity:0.7;text-transform:uppercase;">{month}</div>
        </div>
        <div style="flex:1;min-width:0;">
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
            <span class="cat-pill {item['cat_class']}">{item['category'].upper()}</span>
            <span style="font-size:0.72rem;color:var(--grey-400);">📚 {item['exam_rel']}</span>
          </div>
          <div style="font-family:var(--font-display);font-size:0.95rem;font-weight:700;color:var(--navy);margin-bottom:6px;line-height:1.3;">{item['title']}</div>
          <p style="font-size:0.82rem;color:var(--grey-700);line-height:1.5;margin:0;">{item['summary']}</p>
        </div>
      </a>"""

    yr    = datetime.now().year
    count = len(items)
    html  = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Current Affairs {yr} for UPSC, SSC, Banking | NaukriBulletin</title>
  <meta name="description" content="Daily current affairs {yr} for UPSC, SSC, Railway, Banking exams. Economy, Science, International, Sports, Awards — AI-summarized exam-ready notes.">
  <link rel="canonical" href="https://naukribulletin.in/current-affairs/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="preload" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap"></noscript></noscript>
  <link rel="stylesheet" href="/css/style.css">
  <style>
    .affairs-card {{background:var(--white);border-radius:12px;border:1.5px solid var(--grey-200);padding:20px;display:flex;gap:16px;text-decoration:none;color:inherit;transition:all 0.25s;}}
    .affairs-card:hover {{border-color:var(--saffron);box-shadow:0 4px 20px rgba(255,107,0,0.1);transform:translateY(-1px);}}
    .cat-pill {{font-size:0.68rem;font-weight:700;padding:3px 8px;border-radius:4px;letter-spacing:0.04em;white-space:nowrap;}}
    .cat-economy {{background:#E8F5E9;color:#2E7D32;}}
    .cat-science {{background:#E3F2FD;color:#1565C0;}}
    .cat-international {{background:#F3E5F5;color:#6A1B9A;}}
    .cat-sports {{background:#FFF3E0;color:#E65100;}}
    .cat-awards {{background:#FCE4EC;color:#AD1457;}}
    .cat-government {{background:#E0F2F1;color:#00695C;}}
    .cat-environment {{background:#F1F8E9;color:#33691E;}}
  </style>
</head>
<body>
  <nav class="nav-bar">
    <div class="nav-inner">
      <a href="/" class="logo"><span class="logo-dot"></span>NaukriBulletin</a>
      <ul class="nav-links">
        <li><a href="/">Home</a></li>
        <li><a href="/jobs/">Latest Jobs</a></li>
        <li><a href="/current-affairs/" class="active">Current Affairs</a></li>
        <li><a href="/cut-off/">Cut Off</a></li>
        <li><a href="/admit-card/">Admit Card</a></li>
        <li><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></li>
      </ul>
    </div>
  </nav>
  <div style="background:var(--navy);padding:40px 20px;">
    <div style="max-width:1200px;margin:0 auto;">
      <h1 style="font-family:var(--font-display);font-size:2rem;font-weight:800;color:var(--white);margin-bottom:8px;">
        Daily <span style="color:var(--saffron);">Current Affairs {yr}</span>
      </h1>
      <p style="color:var(--grey-400);font-size:0.95rem;">{count}+ articles — exam-ready summaries, updated daily</p>
    </div>
  </div>
  <div class="container">
    <div class="two-col">
      <section>
        <div style="display:flex;flex-direction:column;gap:12px;">
{cards_html}
        </div>
      </section>
      <aside class="sidebar">
        <div class="telegram-cta">
          <h3>📢 Free Alerts</h3>
          <p>Daily current affairs on Telegram</p>
          <a href="https://t.me/naukribulletin24" class="telegram-btn">Join Channel →</a>
        </div>
        <div class="ad-slot ad-sidebar">Advertisement</div>
      </aside>
    </div>
  </div>
  <footer>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© {yr} NaukriBulletin.in — All Rights Reserved</p>
      </div>
    </div>
  </footer>
</body>
</html>"""

    with open(SITE_ROOT / "current-affairs" / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[LISTING] ✅ /current-affairs/index.html rebuilt with {count} items")



# ─── EXPIRED JOB PRUNER ───────────────────────────────────────────────────────

def prune_expired_jobs(days_grace=7):
    """
    Remove job pages whose last date has passed by more than days_grace days.
    Keeps the sitemap clean and avoids Google indexing stale pages.
    Returns count of removed pages.
    """
    from datetime import datetime, date, timedelta
    from bs4 import BeautifulSoup

    jobs_dir  = SITE_ROOT / "jobs"
    cutoff    = date.today() - timedelta(days=days_grace)
    removed   = 0

    SKIP = {
        "ssc","railway","banking","upsc","defence","police","teaching","state",
        "10th-pass","12th-pass","graduate","post-graduate","engineering","all-india",
        "uttar-pradesh","bihar","madhya-pradesh","rajasthan","tamil-nadu","karnataka",
        "maharashtra","gujarat","kerala","delhi","odisha","assam","punjab","haryana",
        "andhra-pradesh","telangana","west-bengal","chhattisgarh","himachal-pradesh",
        "jharkhand","all-india-government-jobs","government-jobs-2026","psu-jobs-2026",
        "graduate-govt-jobs-2026","iti-govt-jobs-2026","mba-govt-jobs-2026",
        "mca-govt-jobs-2026","law-govt-jobs-2026","govt-bank-jobs-2026",
        "govt-jobs-closing-today","non-executive-posts","faculty-posts-recruitment",
        "indian-railways-jobs","combined-defence-services","banking",
        "national-defence-academy-naval-academy-exam","all-india-government-jobs",
        "iaf-agniveer-vayu","nabard-specialist-jobs","sbi-job-openings",
        "indian-railway-recruitment-2026","sbi-job-openings","government-jobs-2026",
    }

    for job_dir in list(jobs_dir.iterdir()):
        if not job_dir.is_dir() or job_dir.name in SKIP:
            continue
        idx = job_dir / "index.html"
        if not idx.exists():
            continue
        try:
            soup = BeautifulSoup(idx.read_text(encoding="utf-8"), "html.parser")
            rows = {}
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) == 2:
                    rows[cells[0].get_text(strip=True).lower()] = cells[1].get_text(strip=True)
            ld = rows.get("last date", "").strip()
            if not ld or ld.lower() in ("n/a", ""):
                continue
            for fmt in ["%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                try:
                    last_date = __import__("datetime").datetime.strptime(ld, fmt).date()
                    if last_date < cutoff:
                        import shutil
                        shutil.rmtree(job_dir)
                        print(f"  [PRUNE] Removed expired: {job_dir.name} (last date: {ld})")
                        removed += 1
                    break
                except ValueError:
                    continue
        except Exception as e:
            print(f"  [PRUNE] Error checking {job_dir.name}: {e}")

    print(f"[PRUNE] ✅ Removed {removed} expired job pages")
    return removed


# ─── INDEXNOW + GSC PING ──────────────────────────────────────────────────────

def ping_search_engines(new_slugs: list):
    """
    Ping IndexNow (Bing/Yandex/others) and Google Search Console
    with newly published URLs so they get indexed faster.
    Only runs if INDEXNOW_KEY env var is set.
    """
    import os, requests

    key = os.environ.get("INDEXNOW_KEY", "")
    gsc_key = os.environ.get("GOOGLE_INDEXING_KEY", "")  # optional service account JSON

    if not new_slugs:
        print("[PING] No new URLs to ping")
        return

    urls = [f"{SITE_URL}/jobs/{slug}/" for slug in new_slugs]
    # Also ping listing pages
    urls += [f"{SITE_URL}/jobs/", f"{SITE_URL}/sitemap.xml"]

    # ── IndexNow ──────────────────────────────────────────────────────────────
    if key:
        try:
            payload = {
                "host": "naukribulletin.in",
                "key": key,
                "keyLocation": f"{SITE_URL}/{key}.txt",
                "urlList": urls[:100],  # IndexNow limit
            }
            r = requests.post(
                "https://api.indexnow.org/IndexNow",
                json=payload,
                timeout=15,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            if r.status_code in (200, 202):
                print(f"[PING] ✅ IndexNow accepted {len(urls)} URLs")
            else:
                print(f"[PING] IndexNow response: {r.status_code}")
        except Exception as e:
            print(f"[PING] IndexNow error: {e}")
    else:
        print("[PING] INDEXNOW_KEY not set — skipping IndexNow ping")

    # ── Google Search Console (Indexing API) ──────────────────────────────────
    # Requires GOOGLE_INDEXING_KEY = service account JSON as env var string
    # Only worth setting up after AdSense approval; skip gracefully otherwise
    if gsc_key:
        try:
            import json as _json
            from google.oauth2 import service_account
            import googleapiclient.discovery
            creds_info = _json.loads(gsc_key)
            creds = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=["https://www.googleapis.com/auth/indexing"],
            )
            service = googleapiclient.discovery.build("indexing", "v3", credentials=creds)
            for url in urls[:200]:
                service.urlNotifications().publish(
                    body={"url": url, "type": "URL_UPDATED"}
                ).execute()
            print(f"[PING] ✅ GSC Indexing API notified {len(urls)} URLs")
        except Exception as e:
            print(f"[PING] GSC error (non-fatal): {e}")


# ─── STATE PAGES REBUILDER ────────────────────────────────────────────────────

def rebuild_state_and_category_pages():
    """
    Runs patch_state_pages.py and category_gen.py from within scraper.py
    so state/category hub pages stay fresh after every scrape.
    """
    import importlib.util

    for script_name, func_name in [
        ("category_gen", "run"),
        ("patch_state_pages", "run"),
    ]:
        script_path = SITE_ROOT / "scripts" / f"{script_name}.py"
        # patch_state_pages.py lives at repo root, not scripts/
        if not script_path.exists():
            script_path = SITE_ROOT / f"{script_name}.py"
        if not script_path.exists():
            print(f"[REBUILD] {script_name}.py not found — skipping")
            continue
        try:
            spec = importlib.util.spec_from_file_location(script_name, script_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, func_name):
                getattr(mod, func_name)()
                print(f"[REBUILD] ✅ {script_name}.run() completed")
            else:
                print(f"[REBUILD] {script_name} has no run() — skipping")
        except Exception as e:
            print(f"[REBUILD] {script_name} error: {e}")


if __name__ == "__main__":
    run()

