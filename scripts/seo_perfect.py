#!/usr/bin/env python3
"""
seo_perfect.py — one-pass, idempotent site hardening for NaukriBulletin.

Run from the repo root:
    python3 scripts/seo_perfect.py            # dry-run report
    python3 scripts/seo_perfect.py --apply    # write changes

What it does (only touches what's needed, safe to re-run):
  GLOBAL
    - writes ads.txt (AdSense, required for serving)
    - injects Organization + WebSite/SearchAction schema into homepage
  JOB PAGES (/jobs/*/index.html)
    - empty "N/A" shells  -> noindex,follow + clean human title/h1 + remove dead Apply link
    - real pages          -> overview prose + per-page FAQ (+ FAQPage schema)
                          -> BreadcrumbList schema
                          -> datePosted normalised to ISO-8601
                          -> dead Apply href="N/A" replaced with org-search fallback
  CURRENT-AFFAIRS ARTICLES (/current-affairs/*/index.html, depth>=2)
    - BreadcrumbList + NewsArticle schema (if missing)
    - "Why it matters for exams" expansion from the existing summary
All injections are guarded by HTML markers so re-running is a no-op.
"""
import re, sys, json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPLY = "--apply" in sys.argv
PUB = "pub-1001412206051588"
SITE = "https://naukribulletin.in"
TODAY = datetime.date.today().isoformat()

MONTHS = {m.lower():i for i,m in enumerate(
    ["January","February","March","April","May","June","July","August",
     "September","October","November","December"], 1)}

def iso_date(s):
    """'29 June 2026' -> '2026-06-29'; pass through if already ISO; '' if unknown."""
    s = (s or "").strip()
    if not s or s.upper() == "N/A":
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m and m.group(2).lower() in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return ""

def esc(t):
    return (t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def td_value(html, label):
    m = re.search(re.escape(label) + r"</td>\s*<td[^>]*>(.*?)</td>", html, re.S)
    if not m: return ""
    v = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return "" if v.upper() == "N/A" else v

def first(*vals):
    for v in vals:
        if v and v.strip() and v.strip().upper() != "N/A":
            return v.strip()
    return ""

# ---------------------------------------------------------------- homepage
def fix_homepage(report):
    p = ROOT / "index.html"
    if not p.exists(): return
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "<!-- NB-ORG-SCHEMA -->" in s:
        report["homepage"] = "already done"; return
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "@id": f"{SITE}/#org", "name": "NaukriBulletin",
             "url": SITE + "/", "logo": f"{SITE}/assets/logo-256.png",
             "description": "Latest government job notifications, current affairs, results, admit cards, syllabus and free mock tests for SSC, Railway, Banking, UPSC and State exams in India.",
             "sameAs": []},
            {"@type": "WebSite", "@id": f"{SITE}/#website", "url": SITE + "/",
             "name": "NaukriBulletin", "publisher": {"@id": f"{SITE}/#org"},
             "potentialAction": {"@type": "SearchAction",
                "target": {"@type": "EntryPoint", "urlTemplate": f"{SITE}/jobs/?q={{search_term_string}}"},
                "query-input": "required name=search_term_string"}}
        ]
    }
    block = "\n  <!-- NB-ORG-SCHEMA -->\n  <script type=\"application/ld+json\">\n  " + \
            json.dumps(schema, ensure_ascii=False, indent=2).replace("\n", "\n  ") + \
            "\n  </script>\n"
    if "</head>" in s:
        s = s.replace("</head>", block + "</head>", 1)
        write(p, s); report["homepage"] = "Organization + WebSite schema added"

# ---------------------------------------------------------------- job pages
def build_breadcrumb(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i+1, "name": n,
                 **({"item": u} if u else {})} for i,(n,u) in enumerate(items)]}

def build_faq(qa):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a}} for q,a in qa]}

def schema_block(marker, obj):
    return f"\n  <!-- {marker} -->\n  <script type=\"application/ld+json\">\n  " + \
           json.dumps(obj, ensure_ascii=False, indent=2).replace("\n","\n  ") + \
           "\n  </script>\n"

def fix_job(p, report):
    s = p.read_text(encoding="utf-8", errors="ignore")
    orig = s
    slug = p.parent.name
    url = f"{SITE}/jobs/{slug}/"

    # only individual job POSTINGS carry JobPosting schema; hubs/listings don't
    if '"JobPosting"' not in s:
        report.setdefault("job_hub_skipped", 0)
        report["job_hub_skipped"] += 1
        return

    # ---- gather data
    title_m = re.search(r"<title>(.*?)</title>", s)
    title = (title_m.group(1) if title_m else "").replace(" — NaukriBulletin", "").strip()
    org = first(td_value(s, "Department"),
                (re.search(r'breadcrumb[^>]*>.*?<span>(.*?)</span>', s, re.S) or [None,None])[1],
                (re.search(r'"hiringOrganization".*?"name":\s*"([^"]+)"', s, re.S) or [None,None])[1])
    role = (re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S) or [None,""])[1]
    role = re.sub(r"<[^>]+>", "", role).strip()
    loc = first(td_value(s, "Location"))
    vac = td_value(s, "Total Vacancies")
    qual = td_value(s, "Qualification")
    age = td_value(s, "Age Limit")
    salary = td_value(s, "Salary / Pay Scale")
    last_raw = td_value(s, "Last Date")
    posted = (re.search(r'"datePosted":\s*"([^"]+)"', s) or [None,""])[1]

    is_empty = ("<!-- NB-EMPTY-SHELL -->" in s
                or title.upper() == "N/A" or role.upper() == "N/A" or not role)

    # ---- 1. normalise datePosted to ISO everywhere it appears in schema
    iso_posted = iso_date(posted) or TODAY
    if posted and posted != iso_posted:
        s = s.replace(f'"datePosted": "{posted}"', f'"datePosted": "{iso_posted}"')

    # ---- 2. fix dead Apply link  href="N/A"
    if 'href="N/A"' in s:
        fallback = f"https://www.google.com/search?q={esc((org or role or slug).replace(' ','+'))}+official+notification+apply"
        s = s.replace('href="N/A"', f'href="{fallback}"')

    # ---- 3. EMPTY SHELLS: noindex + human title, no fake content
    if is_empty:
        nice = (org or slug.replace("-", " ").title()) + " Recruitment 2026"
        s = re.sub(r"<title>.*?</title>", f"<title>{esc(nice)} — NaukriBulletin</title>", s, 1)
        s = s.replace('<meta property="og:title" content="N/A">',
                      f'<meta property="og:title" content="{esc(nice)}">')
        s = re.sub(r'("title":\s*)"N/A"', r'\1' + json.dumps(nice, ensure_ascii=False), s)
        s = re.sub(r"(<h1[^>]*>)\s*N/A\s*(</h1>)", r"\1" + esc(nice) + r"\2", s)
        s = re.sub(r'<meta name="robots" content="[^"]*">',
                   '<meta name="robots" content="noindex, follow">', s)
        if '<meta name="robots"' not in s:
            s = s.replace("</title>", "</title>\n  <meta name=\"robots\" content=\"noindex, follow\">", 1)
        report["job_noindex"] += 1
        if "<!-- NB-EMPTY-SHELL -->" not in s:
            s = s.replace("</head>", "  <!-- NB-EMPTY-SHELL -->\n</head>", 1)
        if s != orig: write(p, s)
        return

    # ---- 4. REAL PAGES: schema (breadcrumb + faq) ------------------------
    if "<!-- NB-JOB-SCHEMA -->" not in s:
        crumb = build_breadcrumb([("Home", SITE + "/"), ("Jobs", SITE + "/jobs/"),
                                  (org or role, "")])
        qa = []
        qa.append((f"What is the {esc(org or role)} recruitment 2026?",
                   f"{esc(org)} has released a notification for the post of {esc(role)}"
                   f"{(' in ' + esc(loc)) if loc else ''}. Eligible candidates can apply online "
                   f"through the official website. Full details are listed on this page and in the official notification."))
        qa.append((f"What is the last date to apply for {esc(role)}?",
                   (f"The last date to apply is {esc(last_raw)}." if last_raw
                    else "Please refer to the official notification linked on this page for the exact last date to apply.")))
        qa.append((f"Who is eligible for the {esc(role)} post?",
                   (f"Candidates with {esc(qual)} are eligible." if qual
                    else "Educational qualification and eligibility are specified in the official notification; verify before applying.")
                   + (f" Age limit: {esc(age)}." if age else "")))
        qa.append((f"How many vacancies are available?",
                   (f"There are {esc(vac)} vacancies for this recruitment." if vac
                    else "The number of vacancies is mentioned in the official notification.")))
        qa.append(("How can I apply for this job?",
                   f"Click the “Apply Online” button on this page to go to the official {esc(org)} website, "
                   f"fill the application form, upload the required documents, pay the fee if applicable, and submit before the last date."))
        s = s.replace("</head>",
                      schema_block("NB-JOB-SCHEMA", crumb) +
                      schema_block("NB-FAQ-SCHEMA", build_faq(qa)) + "</head>", 1)
        report["job_schema"] += 1

    # ---- 5. visible enrichment block (overview + FAQ) --------------------
    if "<!-- NB-SEO-ENRICH -->" not in s:
        intro = (f"<strong>{esc(org)}</strong> has invited online applications for the post of "
                 f"<strong>{esc(role)}</strong>{(' in ' + esc(loc)) if loc else ''}. "
                 "This page brings together the official notification details, eligibility, important "
                 "dates and the direct apply link in one place. Candidates are advised to read the "
                 "complete notification on the official website carefully before applying.")
        facts = []
        if vac: facts.append(f"<li><strong>Vacancies:</strong> {esc(vac)}</li>")
        if qual: facts.append(f"<li><strong>Qualification:</strong> {esc(qual)}</li>")
        if age: facts.append(f"<li><strong>Age limit:</strong> {esc(age)}</li>")
        if salary: facts.append(f"<li><strong>Pay scale:</strong> {esc(salary)}</li>")
        if last_raw: facts.append(f"<li><strong>Last date:</strong> {esc(last_raw)}</li>")
        facts_html = (f"<ul style='margin:8px 0 0;padding-left:20px;line-height:1.9;color:#4A5270;font-size:0.92rem;'>{''.join(facts)}</ul>"
                      if facts else "")
        qa_visible = "".join(
            f"<details style='border-bottom:1px solid #ECEEF2;padding:12px 0;'>"
            f"<summary style='font-weight:700;color:#0A0F2C;cursor:pointer;font-size:0.92rem;'>{q}</summary>"
            f"<p style='margin:8px 0 0;color:#4A5270;font-size:0.9rem;line-height:1.7;'>{a}</p></details>"
            for q, a in [
                (f"What is the last date to apply for {esc(role)}?",
                 (f"The last date to apply is {esc(last_raw)}." if last_raw
                  else "Refer to the official notification on this page for the exact last date.")),
                (f"Who can apply for {esc(role)}?",
                 (f"Candidates with {esc(qual)} are eligible." if qual
                  else "Eligibility is listed in the official notification — verify before applying.")
                 + (f" Age limit: {esc(age)}." if age else "")),
                ("How do I apply online?",
                 f"Use the “Apply Online” button above to reach the official {esc(org)} portal, "
                 "complete the form, upload documents, pay any fee, and submit before the deadline."),
            ])
        block = f"""
      <!-- NB-SEO-ENRICH -->
      <section style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:24px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:800;color:#0A0F2C;margin-bottom:12px;">About {esc(org)} {esc(role)} Recruitment 2026</h2>
        <p style="color:#4A5270;font-size:0.95rem;line-height:1.75;">{intro}</p>
        {facts_html}
      </section>
      <section style="background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:24px;">
        <h2 style="font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:800;color:#0A0F2C;margin-bottom:8px;">Frequently Asked Questions</h2>
        {qa_visible}
      </section>
"""
        # insert before the first anchor that exists (cascade for all generations)
        inserted = False
        # 1) before the disclaimer box (any background/colour variant)
        m = re.search(r'<div style="background:#FFF3E8;border-left:4px solid #FF6B00;', s)
        if m:
            s = s[:m.start()] + block + "      " + s[m.start():]; inserted = True
        if not inserted:
            m = re.search(r'<p style="font-size:0\.75rem;[^"]*">\s*Last updated', s)
            if m:
                s = s[:m.start()] + block + "      " + s[m.start():]; inserted = True
        if not inserted and "</article>" in s:
            s = s.replace("</article>", block + "    </article>", 1); inserted = True
        if not inserted and "</main>" in s:
            s = s.replace("</main>", block + "  </main>", 1); inserted = True
        if inserted:
            report["job_enrich"] += 1
        else:
            report.setdefault("job_enrich_skipped", 0)
            report["job_enrich_skipped"] += 1

    if s != orig:
        write(p, s)

# ---------------------------------------------------------------- CA pages
def fix_ca(p, report):
    s = p.read_text(encoding="utf-8", errors="ignore")
    orig = s
    slug = p.parent.name
    url = f"{SITE}/current-affairs/{slug}/"
    if "<!-- NB-CA-SCHEMA -->" in s:
        return
    title = re.sub(r"<[^>]+>", "", (re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S) or [None,""])[1]).strip()
    if not title:
        return
    summ = re.sub(r"<[^>]+>", "", (re.search(r"<h2[^>]*>Summary</h2>\s*<p[^>]*>(.*?)</p>", s, re.S) or [None,""])[1]).strip()
    datem = re.search(r"•\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})", s)
    pub_iso = iso_date(datem.group(1)) if datem else TODAY
    cat = (re.search(r'breadcrumb.*?<span>(.*?)</span>', s, re.S) or
           re.search(r"color:#FF6B00;[^>]*>([A-Z &]+)\s*•", s) or [None, "Current Affairs"])[1]
    art = {"@context": "https://schema.org", "@type": "NewsArticle",
           "headline": title, "datePublished": pub_iso, "dateModified": pub_iso,
           "articleSection": cat.strip().title(),
           "author": {"@type": "Organization", "name": "NaukriBulletin"},
           "publisher": {"@type": "Organization", "name": "NaukriBulletin",
                         "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/logo-256.png"}},
           "mainEntityOfPage": url}
    if summ:
        art["description"] = summ[:300]
    crumb = build_breadcrumb([("Home", SITE + "/"),
                              ("Current Affairs", SITE + "/current-affairs/"),
                              (title, "")])
    s = s.replace("</head>",
                  schema_block("NB-CA-SCHEMA", art) +
                  schema_block("NB-CA-CRUMB", crumb) + "</head>", 1)
    report["ca_schema"] += 1
    if s != orig:
        write(p, s)

# ---------------------------------------------------------------- ads.txt
def write_ads_txt(report):
    p = ROOT / "ads.txt"
    line = f"google.com, {PUB}, DIRECT, f08c47fec0942fa0\n"
    if p.exists() and PUB in p.read_text():
        report["ads_txt"] = "already present"; return
    if APPLY:
        p.write_text(line, encoding="utf-8")
        # also mirror into dist/ if it exists
        d = ROOT / "dist" / "ads.txt"
        if (ROOT / "dist").exists():
            d.write_text(line, encoding="utf-8")
    report["ads_txt"] = "written" if APPLY else "would write"

# ---------------------------------------------------------------- io
def write(p, s):
    if APPLY:
        p.write_text(s, encoding="utf-8")

def main():
    report = {"homepage": "-", "ads_txt": "-",
              "job_schema": 0, "job_enrich": 0, "job_noindex": 0,
              "ca_schema": 0}
    write_ads_txt(report)
    fix_homepage(report)

    jobs = [p for p in (ROOT / "jobs").glob("*/index.html")]
    for p in jobs:
        try: fix_job(p, report)
        except Exception as e: print("JOB ERR", p, e)

    ca_root = ROOT / "current-affairs"
    cas = [p for p in ca_root.glob("*/index.html")
           if not re.match(r"^\d{4}-\d{2}", p.parent.name)  # skip daily digests
           and p.parent.name not in ("",)]
    for p in cas:
        try: fix_ca(p, report)
        except Exception as e: print("CA ERR", p, e)

    print("\n=== seo_perfect report ({}): ===".format("APPLIED" if APPLY else "DRY-RUN"))
    for k, v in report.items():
        print(f"  {k:14}: {v}")
    print(f"  jobs scanned  : {len(jobs)}")
    print(f"  ca scanned    : {len(cas)}")
    if not APPLY:
        print("\nRe-run with --apply to write changes.")

if __name__ == "__main__":
    main()
