#!/usr/bin/env python3
"""Fails the GitHub Action (so GitHub emails you) when no AI provider answers.
This is what silently broke the site in Aug 2026: models were retired and the
scraper kept running with 0 new pages."""
import os, sys, requests
sys.path.insert(0, os.path.dirname(__file__))
from scraper import GROQ_MODELS, GEMINI_FALLBACKS

ok = []
k = os.environ.get("GROQ_API_KEY")
if k:
    for m in GROQ_MODELS:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {k}"}, timeout=30,
            json={"model": m, "messages": [{"role": "user", "content": "Reply OK"}],
                  "max_tokens": 200, "reasoning_effort": "low"})
        print(f"Groq {m}: HTTP {r.status_code}")
        if r.ok: ok.append(m)
k = os.environ.get("GEMINI_API_KEY")
if k:
    for gm in GEMINI_FALLBACKS:
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{gm}:generateContent",
            headers={"x-goog-api-key": k},
            json={"contents": [{"parts": [{"text": "Reply OK"}]}]}, timeout=30)
        print(f"Gemini {gm}: HTTP {r.status_code} {'' if r.ok else r.text[:120]}")
        if r.ok: ok.append(gm)
if not ok:
    print("::error::No AI provider is working. Update GROQ_MODELS / GEMINI_MODEL in scripts/scraper.py")
    sys.exit(1)
print("AI OK:", ", ".join(ok))
