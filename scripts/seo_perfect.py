#!/usr/bin/env python3
"""
seo_perfect.py  (v2 — student-utility enrichment)

Idempotent site hardening + content enrichment for NaukriBulletin.
Supersedes v1: detects each page's exam and adds genuinely useful, exam-specific
guidance (eligibility, selection process, exam pattern, how-to-apply, documents,
free-prep links) on top of the per-page facts — without inventing the specific
notification's numbers. Everything general is labelled "verify official notification".

Run from repo root:
    python3 scripts/seo_perfect.py            # dry-run
    python3 scripts/seo_perfect.py --apply    # write
Safe to re-run; v1 enrichment blocks are upgraded to v2 automatically.
"""
import re, sys, json, pathlib, datetime

ROOT  = pathlib.Path(__file__).resolve().parent.parent
APPLY = "--apply" in sys.argv
PUB   = "pub-1001412206051588"
SITE  = "https://naukribulletin.in"
TODAY = datetime.date.today().isoformat()

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August",
     "September","October","November","December"], 1)}

# ───────────────────────── EXAM KNOWLEDGE BASE ────────────────────────────────
EXAM_KB = {
 "ssc-cgl": {"kw":["ssc cgl","combined graduate level","cgl"],
   "name":"SSC CGL (Combined Graduate Level)",
   "elig":"Bachelor's degree from a recognised university (some posts need specific subjects).",
   "age":"Generally 18–32 years depending on the post; age relaxation applies for SC/ST/OBC/PwD/Ex-servicemen.",
   "stages":["Tier 1 — Computer Based Test (objective)","Tier 2 — Computer Based Test (objective + module/skill test where applicable)","Document Verification & final merit"],
   "pattern":"Tier 1 has 100 questions / 200 marks across General Intelligence, General Awareness, Quantitative Aptitude and English in 60 minutes, with 0.50 negative marking.",
   "mock":"/mock-test/ssc-cgl/"},
 "ssc-chsl": {"kw":["chsl","10+2","higher secondary"],
   "name":"SSC CHSL (10+2 Level)",
   "elig":"Passed Class 12 (10+2) from a recognised board.",
   "age":"Generally 18–27 years; relaxation as per rules.",
   "stages":["Tier 1 — Computer Based Test","Tier 2 — descriptive/skill & typing test","Document Verification"],
   "pattern":"Tier 1 has 100 questions / 200 marks (English, GI, Quant, GA) in 60 minutes with 0.50 negative marking.",
   "mock":"/mock-test/ssc-chsl/"},
 "ssc-mts": {"kw":["ssc mts","multi tasking","havaldar"],
   "name":"SSC MTS (Multi Tasking Staff)",
   "elig":"Passed Class 10 (Matriculation) from a recognised board.",
   "age":"Generally 18–25 years (up to 27 for some posts); relaxation as per rules.",
   "stages":["Computer Based Test (Session 1 & 2)","Physical test (for Havaldar)","Document Verification"],
   "pattern":"Objective CBT covering Numerical & Reasoning and General Awareness & English.",
   "mock":"/mock-test/"},
 "ssc-gd": {"kw":["ssc gd","gd constable","constable gd"],
   "name":"SSC GD Constable",
   "elig":"Passed Class 10 from a recognised board.",
   "age":"Generally 18–23 years; relaxation as per rules.",
   "stages":["Computer Based Test","Physical Efficiency Test (PET) & Physical Standard Test (PST)","Medical Examination","Document Verification"],
   "pattern":"Objective CBT on GI & Reasoning, GK & GA, Elementary Mathematics and English/Hindi.",
   "mock":"/mock-test/"},
 "rrb-ntpc": {"kw":["rrb ntpc","ntpc","non technical popular"],
   "name":"RRB NTPC (Non-Technical Popular Categories)",
   "elig":"Class 12 or graduation depending on the post level.",
   "age":"Generally 18–33 years depending on post; relaxation as per rules.",
   "stages":["CBT 1 (screening)","CBT 2","Typing/Computer-based aptitude test (for some posts)","Document Verification & Medical"],
   "pattern":"CBT covers Mathematics, General Intelligence & Reasoning, and General Awareness with negative marking.",
   "mock":"/mock-test/rrb-ntpc/"},
 "rrb-group-d": {"kw":["group d","rrb group","level 1"],
   "name":"RRB Group D (Level 1)",
   "elig":"Class 10 pass or ITI / equivalent.",
   "age":"Generally 18–33 years; relaxation as per rules.",
   "stages":["Computer Based Test","Physical Efficiency Test (PET)","Document Verification & Medical"],
   "pattern":"CBT covers Mathematics, General Science, General Intelligence & Reasoning and General Awareness.",
   "mock":"/mock-test/rrb-group-d/"},
 "rrb-alp": {"kw":["alp","assistant loco","loco pilot"],
   "name":"RRB ALP (Assistant Loco Pilot)",
   "elig":"Class 10 plus ITI / relevant engineering qualification.",
   "age":"Generally 18–30 years; relaxation as per rules.",
   "stages":["CBT 1","CBT 2 (Part A & B)","Computer Based Aptitude Test","Document Verification & Medical"],
   "pattern":"Technical + non-technical objective testing with negative marking.",
   "mock":"/mock-test/"},
 "ibps-po": {"kw":["ibps po","probationary officer"],
   "name":"IBPS PO (Probationary Officer)",
   "elig":"Graduation in any discipline from a recognised university.",
   "age":"Generally 20–30 years; relaxation as per rules.",
   "stages":["Preliminary Examination","Main Examination","Interview & final merit"],
   "pattern":"Prelims: English, Quantitative Aptitude and Reasoning (objective, sectional timing). Mains adds General/Banking Awareness, Computer & a descriptive paper.",
   "mock":"/mock-test/ibps-po/"},
 "ibps-clerk": {"kw":["ibps clerk","clerk cadre"],
   "name":"IBPS Clerk",
   "elig":"Graduation in any discipline.",
   "age":"Generally 20–28 years; relaxation as per rules.",
   "stages":["Preliminary Examination","Main Examination & final merit"],
   "pattern":"Prelims: English, Numerical Ability, Reasoning Ability (objective).",
   "mock":"/mock-test/"},
 "sbi-po": {"kw":["sbi po"],
   "name":"SBI PO (Probationary Officer)",
   "elig":"Graduation in any discipline.",
   "age":"Generally 21–30 years; relaxation as per rules.",
   "stages":["Preliminary Examination","Main Examination","Psychometric test, Group Exercise & Interview"],
   "pattern":"Prelims: English, Quantitative Aptitude, Reasoning. Mains: Reasoning & Computer, Data Analysis, General/Economy/Banking Awareness, English + descriptive.",
   "mock":"/mock-test/sbi-po/"},
 "sbi-clerk": {"kw":["sbi clerk","junior associate"],
   "name":"SBI Clerk (Junior Associate)",
   "elig":"Graduation in any discipline.",
   "age":"Generally 20–28 years; relaxation as per rules.",
   "stages":["Preliminary Examination","Main Examination & local language test"],
   "pattern":"Prelims: English, Numerical Ability, Reasoning Ability (objective).",
   "mock":"/mock-test/sbi-clerk/"},
 "rbi-gradeb": {"kw":["rbi grade b","grade b officer"],
   "name":"RBI Grade B Officer",
   "elig":"Graduation/Post-graduation with minimum marks as specified.",
   "age":"Generally 21–30 years; relaxation as per rules.",
   "stages":["Phase 1 (objective)","Phase 2 (objective + descriptive)","Interview"],
   "pattern":"Tests General Awareness, English, Quantitative Aptitude, Reasoning and Economic & Social Issues / Finance & Management.",
   "mock":"/mock-test/"},
 "upsc-cse": {"kw":["civil services","ias","upsc cse","upsc civil"],
   "name":"UPSC Civil Services (IAS/IPS/IFS etc.)",
   "elig":"Bachelor's degree in any discipline from a recognised university.",
   "age":"Generally 21–32 years; category relaxation and limited attempts apply.",
   "stages":["Preliminary Examination (objective)","Main Examination (written, descriptive)","Personality Test / Interview"],
   "pattern":"Prelims: General Studies + CSAT. Mains: 9 descriptive papers including essay, GS I–IV and optional subject.",
   "mock":"/mock-test/"},
 "upsc-nda": {"kw":["nda","national defence academy"],
   "name":"UPSC NDA (National Defence Academy)",
   "elig":"Class 12 pass (Maths & Physics required for Air Force/Navy and technical entries).",
   "age":"Unmarried candidates roughly 16.5–19.5 years (as per the notification).",
   "stages":["Written Examination (Maths + General Ability)","SSB Interview","Medical"],
   "pattern":"Objective Mathematics paper and a General Ability Test (English + GK).",
   "mock":"/mock-test/"},
 "ctet": {"kw":["ctet","teacher eligibility","tet"],
   "name":"CTET / Teacher Eligibility Test",
   "elig":"Class 12 + D.El.Ed / graduation + B.Ed as applicable to the level (Paper I / Paper II).",
   "age":"Usually no upper age limit (verify the notification).",
   "stages":["Paper I (Classes I–V) and/or Paper II (Classes VI–VIII)","Qualifying certificate"],
   "pattern":"Objective paper on Child Development & Pedagogy, Language I & II, and subject content.",
   "mock":"/mock-test/"},
 "ugc-net": {"kw":["ugc net","net jrf","assistant professor"],
   "name":"UGC NET (Assistant Professor / JRF)",
   "elig":"Master's degree with the minimum marks specified for the subject.",
   "age":"No upper limit for Assistant Professor; JRF has an upper age limit with relaxations.",
   "stages":["Computer Based Test — Paper 1 (Teaching/Research Aptitude) + Paper 2 (subject)"],
   "pattern":"Two objective papers conducted in a single CBT session; no negative marking.",
   "mock":"/mock-test/"},
 "agniveer": {"kw":["agniveer","agnipath","army agni","navy agni","air force agni"],
   "name":"Agniveer (Agnipath Scheme)",
   "elig":"Class 10/12 depending on entry; specific physical & medical standards apply.",
   "age":"Generally 17.5–21 years (as per the notification).",
   "stages":["Online Common Entrance Examination","Physical Fitness & Measurement Test","Medical Examination"],
   "pattern":"Objective entrance test followed by physical and medical screening.",
   "mock":"/mock-test/"},
 "police": {"kw":["police","constable","sub inspector","home guard"],
   "name":"Police / Constable Recruitment",
   "elig":"Class 10/12 or graduation depending on the rank and state rules.",
   "age":"Typically 18–25 years (varies by state and category); relaxation as per rules.",
   "stages":["Written Examination","Physical Standard & Efficiency Test","Medical Examination","Document Verification"],
   "pattern":"Written test on Reasoning, Numerical Ability, General Knowledge and state-specific topics.",
   "mock":"/mock-test/"},
 "state-psc": {"kw":["psc","public service commission","subordinate service"],
   "name":"State Public Service Commission Exam",
   "elig":"Graduation in a relevant discipline (varies by post).",
   "age":"Typically 21–40 years depending on state and category; relaxation applies.",
   "stages":["Preliminary Examination","Main Examination","Interview / Personality Test"],
   "pattern":"Objective prelims followed by descriptive mains and an interview, similar to the UPSC pattern at the state level.",
   "mock":"/mock-test/"},
}

def detect_exam(blob):
    b = blob.lower()
    order = ["ssc-cgl","ssc-chsl","ssc-mts","ssc-gd","rrb-ntpc","rrb-group-d","rrb-alp",
             "ibps-po","ibps-clerk","sbi-po","sbi-clerk","rbi-gradeb","upsc-cse","upsc-nda",
             "ctet","ugc-net","agniveer","police","state-psc"]
    for k in order:
        for kw in EXAM_KB[k]["kw"]:
            if kw in b:
                return EXAM_KB[k]
    return None

# ───────────────────────────── helpers ───────────────────────────────────────
def iso_date(s):
    s = (s or "").strip()
    if not s or s.upper() == "N/A": return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", s): return s[:10]
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m and m.group(2).lower() in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return ""

def esc(t): return (t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def td_value(html, label):
    m = re.search(re.escape(label) + r"</td>\s*<td[^>]*>(.*?)</td>", html, re.S)
    if not m: return ""
    v = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return "" if v.upper() == "N/A" else v

def first(*vals):
    for v in vals:
        if v and v.strip() and v.strip().upper() != "N/A": return v.strip()
    return ""

def _is_non_recruitment(role, slug):
    low = (role + " " + slug).lower()
    return any(k in low for k in ("admit","result","answer key","answer-key","syllabus",
                                  "cut off","cut-off","exam date","exam-date","datesheet"))

def opt_title(role, org, slug=""):
    """High-CTR <title>: ensure 'Recruitment 2026' for job postings; leave admit-card/result pages alone."""
    r = role.strip()
    if _is_non_recruitment(r, slug):
        core = r
    else:
        low = r.lower()
        if "recruit" in low or "vacanc" in low or "notification" in low:
            core = r if any(y in r for y in ("2025","2026")) else f"{r} 2026"
        else:
            core = f"{r} Recruitment 2026"
    if len(core) > 60:                      # keep keyword core within SERP display
        core = core[:57].rsplit(" ", 1)[0].rstrip(",-—") + "…"
    return f"{core} — NaukriBulletin"

def opt_desc(org, role, vac, qual, last, slug=""):
    """Rich meta description with aspirant-search hooks (CTR only, no ranking risk)."""
    r = role.strip()
    if _is_non_recruitment(r, slug):
        lead = r
    elif "recruit" in r.lower() or "vacanc" in r.lower():
        lead = r if any(y in r for y in ("2025","2026")) else f"{r} 2026"
    else:
        lead = f"{r} Recruitment 2026"
    if org and org.lower() not in lead.lower() and lead.lower() not in org.lower():
        lead = f"{org.split('(')[0].strip()} — {lead}"
    parts = [lead.rstrip('.') + "."]
    if vac:  parts.append(f"{vac} vacancies.")
    if qual: parts.append(f"Eligibility: {qual}.")
    if last: parts.append(f"Last date: {last}.")
    parts.append("Check age limit, salary, selection process & apply online.")
    d = re.sub(r"\s+", " ", " ".join(parts)).strip()
    if len(d) > 160:
        d = d[:158].rsplit(" ", 1)[0] + "…"
    return d

def schema_block(marker, obj):
    return (f"\n  <!-- {marker} -->\n  <script type=\"application/ld+json\">\n  " +
            json.dumps(obj, ensure_ascii=False, indent=2).replace("\n","\n  ") + "\n  </script>\n")

def build_breadcrumb(items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList",
            "itemListElement":[{"@type":"ListItem","position":i+1,"name":n,
                **({"item":u} if u else {})} for i,(n,u) in enumerate(items)]}

def build_faq(qa):
    return {"@context":"https://schema.org","@type":"FAQPage",
            "mainEntity":[{"@type":"Question","name":q,
                "acceptedAnswer":{"@type":"Answer","text":a}} for q,a in qa]}

CARD = "background:#fff;border-radius:12px;border:1.5px solid #ECEEF2;padding:24px;margin-bottom:20px;"
H2   = "font-family:'Syne',sans-serif;font-size:1.12rem;font-weight:800;color:#0A0F2C;margin-bottom:12px;"
P    = "color:#4A5270;font-size:0.95rem;line-height:1.75;margin:0 0 8px;"
LI   = "margin:6px 0;color:#4A5270;font-size:0.92rem;line-height:1.65;"

def section(title, inner):
    return f'      <section style="{CARD}">\n        <h2 style="{H2}">{title}</h2>\n{inner}\n      </section>\n'

def strip_old_enrich(s):
    s = re.sub(r"      <!-- NB-ENRICH-START -->.*?<!-- NB-ENRICH-END -->\n      ", "", s, flags=re.S)
    s = re.sub(r"\s*<!-- NB-SEO-ENRICH -->.*?Frequently Asked Questions.*?</section>", "", s, flags=re.S)
    return s

def strip_schema(s, marker):
    return re.sub(rf"\s*<!-- {marker} -->\s*<script type=\"application/ld\+json\">.*?</script>", "", s, flags=re.S)

def insert_before_tail(s, block):
    m=re.search(r'<div style="background:#FFF3E8;border-left:4px solid #FF6B00;', s)
    if m: return s[:m.start()]+block+s[m.start():]
    m=re.search(r'<p style="font-size:0\.75rem;[^"]*">\s*Last updated', s)
    if m: return s[:m.start()]+block+s[m.start():]
    if "</article>" in s: return s.replace("</article>", block+"</article>", 1)
    if "</main>" in s:     return s.replace("</main>", block+"</main>", 1)
    return s

# ───────────────────────────── homepage ──────────────────────────────────────
def fix_homepage(report):
    p = ROOT / "index.html"
    if not p.exists(): return
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "<!-- NB-ORG-SCHEMA -->" in s:
        report["homepage"]="already done"; return
    schema={"@context":"https://schema.org","@graph":[
        {"@type":"Organization","@id":f"{SITE}/#org","name":"NaukriBulletin","url":SITE+"/",
         "logo":f"{SITE}/assets/logo-256.png",
         "description":"Latest government job notifications, current affairs, results, admit cards, syllabus and free mock tests for SSC, Railway, Banking, UPSC and State exams in India.","sameAs":[]},
        {"@type":"WebSite","@id":f"{SITE}/#website","url":SITE+"/","name":"NaukriBulletin",
         "publisher":{"@id":f"{SITE}/#org"},
         "potentialAction":{"@type":"SearchAction",
            "target":{"@type":"EntryPoint","urlTemplate":f"{SITE}/jobs/?q={{search_term_string}}"},
            "query-input":"required name=search_term_string"}}]}
    s = s.replace("</head>", schema_block("NB-ORG-SCHEMA", schema)+"</head>", 1)
    write(p, s); report["homepage"]="Organization + WebSite schema added"

# ───────────────────────────── job pages ─────────────────────────────────────
def enrich_job_html(s, slug):
    """Pure string->string enrichment for one job page.
    Returns (html, status) where status in {'hub','noindex','enriched'}.
    Safe to call at generation time AND as a backfill; idempotent."""
    url=f"{SITE}/jobs/{slug}/"
    if '"JobPosting"' not in s:
        return s, "hub"

    title=(re.search(r"<title>(.*?)</title>", s) or [None,""])[1].replace(" — NaukriBulletin","").strip()
    org=first(td_value(s,"Department"),
              (re.search(r'"hiringOrganization".*?"name":\s*"([^"]+)"',s,re.S) or [None,None])[1])
    role=re.sub(r"<[^>]+>","",(re.search(r"<h1[^>]*>(.*?)</h1>",s,re.S) or [None,""])[1]).strip()
    loc=first(td_value(s,"Location")); vac=td_value(s,"Total Vacancies")
    qual=td_value(s,"Qualification"); age=td_value(s,"Age Limit")
    salary=td_value(s,"Salary / Pay Scale"); last_raw=td_value(s,"Last Date")
    posted=(re.search(r'"datePosted":\s*"([^"]+)"',s) or [None,""])[1]
    kb=detect_exam(" ".join([title,org,role,slug]))

    iso=iso_date(posted) or TODAY
    if posted and posted!=iso: s=s.replace(f'"datePosted": "{posted}"',f'"datePosted": "{iso}"')
    if 'href="N/A"' in s:
        fb=f"https://www.google.com/search?q={esc((org or role or slug).replace(' ','+'))}+official+notification+apply"
        s=s.replace('href="N/A"',f'href="{fb}"')

    empty=("<!-- NB-EMPTY-SHELL -->" in s or title.upper()=="N/A" or role.upper()=="N/A" or not role)
    if empty:
        nice=(org or slug.replace("-"," ").title())+" Recruitment 2026"
        s=re.sub(r"<title>.*?</title>",f"<title>{esc(nice)} — NaukriBulletin</title>",s,1)
        s=s.replace('<meta property="og:title" content="N/A">',f'<meta property="og:title" content="{esc(nice)}">')
        s=re.sub(r'("title":\s*)"N/A"',r'\1'+json.dumps(nice,ensure_ascii=False),s)
        s=re.sub(r"(<h1[^>]*>)\s*N/A\s*(</h1>)",r"\1"+esc(nice)+r"\2",s)
        s=re.sub(r'<meta name="robots" content="[^"]*">','<meta name="robots" content="noindex, follow">',s)
        if '<meta name="robots"' not in s:
            s=s.replace("</title>","</title>\n  <meta name=\"robots\" content=\"noindex, follow\">",1)
        if "<!-- NB-EMPTY-SHELL -->" not in s:
            s=s.replace("</head>","  <!-- NB-EMPTY-SHELL -->\n</head>",1)
        return s, "noindex"

    # ---- title + meta-description CTR optimisation (idempotent) ----
    if "<!-- NB-TITLE-OPT -->" not in s:
        new_title = opt_title(role, org, slug)
        new_desc  = opt_desc(org, role, vac, qual, last_raw, slug)
        s = re.sub(r"<title>.*?</title>", f"<title>{esc(new_title)}</title>", s, 1)
        s = re.sub(r'<meta name="description" content="[^"]*">',
                   f'<meta name="description" content="{esc(new_desc)}">', s, 1)
        s = re.sub(r'<meta property="og:title" content="[^"]*">',
                   f'<meta property="og:title" content="{esc(new_title.replace(" — NaukriBulletin",""))}">', s, 1)
        s = re.sub(r'<meta property="og:description" content="[^"]*">',
                   f'<meta property="og:description" content="{esc(new_desc)}">', s, 1)
        s = s.replace("</head>", "  <!-- NB-TITLE-OPT -->\n</head>", 1)

    qa=[(f"What is the {esc(org or role)} recruitment 2026?",
         f"{esc(org)} has released a notification for the post of {esc(role)}"
         f"{(' in '+esc(loc)) if loc else ''}. Eligible candidates can apply online; full details are on this page and in the official notification."),
        (f"What is the last date to apply for {esc(role)}?",
         (f"The last date to apply is {esc(last_raw)}." if last_raw else "Refer to the official notification on this page for the exact last date.")),
        (f"Who is eligible for the {esc(role)} post?",
         (f"Candidates with {esc(qual)} are eligible." if qual
          else (f"Eligibility for {esc(kb['name'])} is generally: {esc(kb['elig'])}" if kb
                else "Educational qualification is specified in the official notification; verify before applying."))
         + (f" Age limit: {esc(age)}." if age else "")),
        ("How many vacancies are there?",
         (f"There are {esc(vac)} vacancies." if vac else "The number of vacancies is given in the official notification.")),
        ("How can I apply?",
         f"Use the \u201cApply Online\u201d button on this page to reach the official {esc(org)} website, fill the form, upload documents, pay any fee, and submit before the last date.")]
    crumb=build_breadcrumb([("Home",SITE+"/"),("Jobs",SITE+"/jobs/"),(org or role,"")])
    s=strip_schema(s,"NB-JOB-SCHEMA"); s=strip_schema(s,"NB-FAQ-SCHEMA")
    s=s.replace("</head>",schema_block("NB-JOB-SCHEMA",crumb)+schema_block("NB-FAQ-SCHEMA",build_faq(qa))+"</head>",1)

    s=strip_old_enrich(s)
    blocks=[]
    intro=(f"<strong>{esc(org)}</strong> has invited online applications for the post of "
           f"<strong>{esc(role)}</strong>{(' in '+esc(loc)) if loc else ''}. This page collects the "
           "official notification details, eligibility, important dates, the selection process and the "
           "direct apply link in one place, along with free preparation resources. Always confirm the "
           "final details from the official notification before applying.")
    facts=[]
    for lab,val in [("Vacancies",vac),("Qualification",qual),("Age limit",age),("Pay scale",salary),("Last date",last_raw)]:
        if val: facts.append(f"<li style='{LI}'><strong>{lab}:</strong> {esc(val)}</li>")
    facts_html=f"<ul style='margin:8px 0 0;padding-left:20px;'>{''.join(facts)}</ul>" if facts else ""
    blocks.append(section(f"About {esc(org)} {esc(role)} Recruitment 2026",
                          f"        <p style='{P}'>{intro}</p>\n{facts_html}"))
    if qual or age:
        e=f"        <p style='{P}'>"
        if qual: e+=f"<strong>Educational qualification:</strong> {esc(qual)}.<br>"
        if age:  e+=f"<strong>Age limit:</strong> {esc(age)}."
        e+="</p>"
        blocks.append(section("Eligibility Criteria", e))
    elif kb:
        blocks.append(section("Eligibility Criteria",
            f"        <p style='{P}'>For {esc(kb['name'])}, eligibility is generally: {esc(kb['elig'])}<br>"
            f"<strong>Age:</strong> {esc(kb['age'])}</p>"
            f"        <p style='{P};font-size:0.82rem;color:#9BA3B8;'>This is general guidance — confirm the exact eligibility and age for this specific recruitment in the official notification.</p>"))
    if kb:
        st="".join(f"<li style='{LI}'>{esc(x)}</li>" for x in kb["stages"])
        blocks.append(section("Selection Process",
            f"        <ol style='margin:0;padding-left:20px;'>{st}</ol>\n"
            f"        <p style='{P};margin-top:10px;'><strong>Exam pattern:</strong> {esc(kb['pattern'])}</p>"))
    steps=[f"Visit the official {esc(org)} website (use the \u201cApply Online\u201d button above).",
           "Register with a valid email and mobile number, then log in.",
           "Fill the application form carefully with your personal and academic details.",
           "Upload a scanned photograph, signature and required documents in the specified format.",
           "Pay the application fee (if applicable) and submit the form before the last date.",
           "Download and keep a printout of the submitted form for future reference."]
    blocks.append(section("How to Apply — Step by Step",
        "        <ol style='margin:0;padding-left:20px;'>"+"".join(f"<li style='{LI}'>{x}</li>" for x in steps)+"</ol>"))
    docs=["Recent passport-size photograph and scanned signature",
          "Class 10 / 12 mark sheets and certificates",
          "Graduation / required qualification certificate",
          "Category certificate (SC/ST/OBC/EWS) if applicable",
          "Valid photo ID (Aadhaar / PAN / Voter ID)",
          "Active email ID and mobile number"]
    blocks.append(section("Documents Required",
        "        <ul style='margin:0;padding-left:20px;'>"+"".join(f"<li style='{LI}'>{x}</li>" for x in docs)+"</ul>"))
    mock=kb["mock"] if kb else "/mock-test/"
    prep=(f"        <p style='{P}'>Prepare smartly with our free resources:</p>\n"
          f"        <ul style='margin:0;padding-left:20px;'>"
          f"<li style='{LI}'>\U0001F4DD <a href='{mock}' style='color:#FF6B00;font-weight:600;'>Free mock tests</a> — practise with real exam-pattern questions.</li>"
          f"<li style='{LI}'>\U0001F4DA <a href='/syllabus/' style='color:#FF6B00;font-weight:600;'>Syllabus &amp; exam pattern</a> — know exactly what to study.</li>"
          f"<li style='{LI}'>\U0001F5DE\uFE0F <a href='/current-affairs/' style='color:#FF6B00;font-weight:600;'>Daily current affairs</a> — stay updated for the GA/GK section.</li>"
          f"<li style='{LI}'>\U0001F514 <a href='/alerts/' style='color:#FF6B00;font-weight:600;'>Set job alerts</a> — never miss a new vacancy.</li>"
          f"</ul>")
    blocks.append(section("Free Preparation Resources", prep))
    qv="".join(
        f"<details style='border-bottom:1px solid #ECEEF2;padding:12px 0;'>"
        f"<summary style='font-weight:700;color:#0A0F2C;cursor:pointer;font-size:0.92rem;'>{q}</summary>"
        f"<p style='{P};margin-top:8px;'>{a}</p></details>" for q,a in qa)
    blocks.append(section("Frequently Asked Questions", "        "+qv))

    block="      <!-- NB-ENRICH-START -->\n"+"".join(blocks)+"      <!-- NB-ENRICH-END -->\n      "
    s=insert_before_tail(s, block)
    return s, "enriched"

def fix_job(p, report):
    """Backfill wrapper: read file -> enrich -> write."""
    s = p.read_text(encoding="utf-8", errors="ignore")
    new, status = enrich_job_html(s, p.parent.name)
    report[{"hub":"job_hub_skipped","noindex":"job_noindex","enriched":"job_enrich"}[status]] += 1
    if status == "enriched":
        report["job_schema"] += 1
    if new != s:
        write(p, new)

# ───────────────────────── current-affairs pages ─────────────────────────────
def enrich_ca_html(s, slug):
    """Pure string->string enrichment for one current-affairs page.
    Returns (html, status) where status in {'skip','schema','enriched'}."""
    url=f"{SITE}/current-affairs/{slug}/"
    title=re.sub(r"<[^>]+>","",(re.search(r"<h1[^>]*>(.*?)</h1>",s,re.S) or [None,""])[1]).strip()
    if not title: return s, "skip"
    summ=re.sub(r"<[^>]+>","",(re.search(r"<h2[^>]*>Summary</h2>\s*<p[^>]*>(.*?)</p>",s,re.S) or [None,""])[1]).strip()
    datem=re.search(r"\u2022\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",s)
    pub=iso_date(datem.group(1)) if datem else TODAY
    cat=(re.search(r'breadcrumb.*?<span>(.*?)</span>',s,re.S) or
         re.search(r"color:#FF6B00;[^>]*>([A-Z &]+)\s*\u2022",s) or [None,"Current Affairs"])[1]
    cat=cat.strip().title()

    if "<!-- NB-CA-SCHEMA -->" not in s:
        art={"@context":"https://schema.org","@type":"NewsArticle","headline":title,
             "datePublished":pub,"dateModified":pub,"articleSection":cat,
             "author":{"@type":"Organization","name":"NaukriBulletin"},
             "publisher":{"@type":"Organization","name":"NaukriBulletin",
                          "logo":{"@type":"ImageObject","url":f"{SITE}/assets/logo-256.png"}},
             "mainEntityOfPage":url}
        if summ: art["description"]=summ[:300]
        crumb=build_breadcrumb([("Home",SITE+"/"),("Current Affairs",SITE+"/current-affairs/"),(title,"")])
        s=s.replace("</head>",schema_block("NB-CA-SCHEMA",art)+schema_block("NB-CA-CRUMB",crumb)+"</head>",1)
        _added_schema=True
    else:
        _added_schema=False

    if "<!-- NB-CA-ENRICH -->" not in s:
        why=("This development is useful for the General Awareness / Current Affairs section of exams like "
             "SSC, Railway (RRB), Banking, UPSC and State PSCs. Note the key facts above and be ready to answer "
             "objective questions on the who, what, when and why of this news.")
        block=f"""
      <!-- NB-CA-ENRICH -->
      <div style="{CARD}">
        <h2 style="{H2}">Why this matters for your exam</h2>
        <p style="{P}">{esc(why)}</p>
        <p style="{P};margin-top:10px;">
          \u2705 <a href="/mock-test/" style="color:#FF6B00;font-weight:600;">Practise current-affairs MCQs</a> &nbsp;\u00b7&nbsp;
          \U0001F4DA <a href="/current-affairs/" style="color:#FF6B00;font-weight:600;">More daily current affairs</a> &nbsp;\u00b7&nbsp;
          \U0001F514 <a href="/alerts/" style="color:#FF6B00;font-weight:600;">Get daily updates</a>
        </p>
      </div>
"""
        anchor=re.search(r"Key Facts for Exam.*?</div>\s*</div>", s, re.S)
        if anchor:
            s=s[:anchor.end()]+block+s[anchor.end():]
        elif "</article>" in s:
            s=s.replace("</article>", block+"    </article>", 1)
        _added_block=True
    else:
        _added_block=False

    if _added_block:   return s, "enriched"
    if _added_schema:  return s, "schema"
    return s, "noop"

def fix_ca(p, report):
    """Backfill wrapper: read file -> enrich -> write."""
    s = p.read_text(encoding="utf-8", errors="ignore")
    new, status = enrich_ca_html(s, p.parent.name)
    if status in ("schema", "enriched"): report["ca_schema"] += 1
    if status == "enriched": report["ca_enrich"] += 1
    if new != s:
        write(p, new)

# ───────────────────────────── ads.txt + io ──────────────────────────────────
def write_ads_txt(report):
    p=ROOT/"ads.txt"; line=f"google.com, {PUB}, DIRECT, f08c47fec0942fa0\n"
    if p.exists() and PUB in p.read_text(): report["ads_txt"]="already present"; return
    if APPLY:
        p.write_text(line,encoding="utf-8")
        if (ROOT/"dist").exists(): (ROOT/"dist"/"ads.txt").write_text(line,encoding="utf-8")
    report["ads_txt"]="written" if APPLY else "would write"

def write(p,s):
    if APPLY: p.write_text(s,encoding="utf-8")

def main():
    report={"homepage":"-","ads_txt":"-","job_schema":0,"job_enrich":0,"job_noindex":0,
            "job_hub_skipped":0,"ca_schema":0,"ca_enrich":0}
    write_ads_txt(report); fix_homepage(report)
    jobs=list((ROOT/"jobs").glob("*/index.html"))
    for p in jobs:
        try: fix_job(p,report)
        except Exception as e: print("JOB ERR",p,e)
    cas=[p for p in (ROOT/"current-affairs").glob("*/index.html")
         if not re.match(r"^\d{4}-\d{2}",p.parent.name)]
    for p in cas:
        try: fix_ca(p,report)
        except Exception as e: print("CA ERR",p,e)
    print("\n=== seo_perfect v2 report ({}): ===".format("APPLIED" if APPLY else "DRY-RUN"))
    for k,v in report.items(): print(f"  {k:16}: {v}")
    print(f"  jobs scanned    : {len(jobs)}\n  ca scanned      : {len(cas)}")
    if not APPLY: print("\nRe-run with --apply to write changes.")

if __name__=="__main__":
    main()
