#!/usr/bin/env python3
"""
NaukriBulletin quality gate. Runs LAST before dist/ sync.

Why: Google treated the site as scaled auto-generated content (thin AI news,
job pages full of "N/A", expired JobPosting schema). AdSense rejects the same
thing as "low value content". This script makes only complete pages indexable.

Rules
  jobs/<slug>/ with JobPosting schema
      index  -> validThrough in the future AND <2 "N/A" AND >=350 words
      else   -> noindex,follow + JobPosting schema removed
  jobs/<slug>/ listing pages (no JobPosting) -> noindex if <300 words
  current-affairs/<slug>/  -> noindex if <600 words (auto rewrites)
  blog/<slug>/             -> noindex if <200 words
  sitemap.xml              -> rebuilt from indexable pages only

Usage: python3 scripts/quality_gate.py [--dry-run]
"""
import re, sys, json, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://naukribulletin.in"
TODAY = datetime.date.today()
DRY = "--dry-run" in sys.argv
SKIP_DIRS = {"dist", "scripts", ".git", ".github", "node_modules", ".wrangler", "_data"}

ROBOTS_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*"\s*/?>', re.I)
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def words(html):
    m = re.search(r"<main.*?</main>", html, re.S)
    b = m.group(0) if m else html
    b = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<footer.*?</footer>", " ", b, flags=re.S)
    b = re.sub(r"<[^>]+>", " ", b)
    return len(b.split()), len(re.findall(r"\bN/A\b", b))


def is_noindex(html):
    m = ROBOTS_RE.search(html)
    return bool(m and "noindex" in m.group(0).lower())


def set_robots(html, value):
    tag = f'<meta name="robots" content="{value}">'
    if ROBOTS_RE.search(html):
        return ROBOTS_RE.sub(tag, html, count=1)
    return html.replace("</title>", "</title>\n  " + tag, 1)


def strip_jobposting(html):
    def repl(m):
        return "" if '"JobPosting"' in m.group(1) else m.group(0)
    return LD_RE.sub(repl, html)


def valid_through(html):
    m = re.search(r'"validThrough"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


LEGAL = ('<!-- NB-LEGAL --><div style="max-width:1100px;margin:24px auto;padding:16px;'
         'font-size:13px;text-align:center;border-top:1px solid rgba(128,128,128,.25)">'
         '<a href="/about/">About</a> &middot; <a href="/contact/">Contact</a> &middot; '
         '<a href="/privacy/">Privacy Policy</a> &middot; <a href="/terms/">Terms of Use</a> &middot; '
         '<a href="/disclaimer/">Disclaimer</a><br>NaukriBulletin.in is not a government website. '
         'Always verify details in the official notification.</div>')


def ensure_legal(html):
    if "NB-LEGAL" in html or "</body>" not in html:
        return html
    body_links = html.split("<body", 1)[-1]
    if all(f'href="/{x}/"' in body_links for x in ("about", "privacy", "terms")):
        return html
    return html.replace("</body>", LEGAL + "\n</body>", 1)


def decide(rel, html):
    """Return (indexable, reason)."""
    parts = rel.parts
    if parts and parts[0] in ("saved-jobs",):     # per-user utility page, no content
        return False, "utility page"
    w, na = words(html)
    if len(parts) == 2 and parts[0] == "jobs":
        if '"JobPosting"' in html:
            vt = valid_through(html)
            if not vt or vt < TODAY:
                return False, "expired or no last date"
            if na >= 2:
                return False, f"{na} N/A fields"
            if w < 350:
                return False, f"thin ({w} words)"
            return True, ""
        job_links = len(set(re.findall(r'href="/jobs/[a-z0-9-]+/"', html)))
        if job_links >= 10:                       # category / state listing page
            return (w >= 300), f"thin listing ({w} words)"
        return False, "expired or no last date"   # detail page without valid schema
    if len(parts) == 2 and parts[0] == "current-affairs":
        return (w >= 600), f"auto news ({w} words)"
    if len(parts) == 2 and parts[0] == "blog":
        return (w >= 200), f"thin blog ({w} words)"
    return (not is_noindex(html)), "noindex already"


def main():
    stats = {"indexable": 0, "noindexed_now": 0, "jobposting_removed": 0}
    by_reason = {}
    urls = []
    for f in sorted(ROOT.rglob("index.html")):
        rel = f.parent.relative_to(ROOT)
        if rel.parts and rel.parts[0] in SKIP_DIRS:
            continue
        html = f.read_text(encoding="utf-8", errors="ignore")
        ok, why = decide(rel, html)
        new = ensure_legal(html)
        if ok:
            stats["indexable"] += 1
            path = "/".join(rel.parts)
            urls.append(f"{SITE}/{path}/" if path else f"{SITE}/")
        else:
            key = why.split(" (")[0]
            by_reason[key] = by_reason.get(key, 0) + 1
            if not is_noindex(html):
                stats["noindexed_now"] += 1
            new = set_robots(new, "noindex, follow")
            if '"JobPosting"' in new:
                new = strip_jobposting(new)
                stats["jobposting_removed"] += 1
        if new != html and not DRY:
            f.write_text(new, encoding="utf-8")

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{u}</loc></url>" for u in urls]
    sm.append("</urlset>")
    if not DRY:
        (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    stats["sitemap_urls"] = len(urls)
    stats["noindex_reasons"] = by_reason
    print("[QUALITY GATE]", json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
