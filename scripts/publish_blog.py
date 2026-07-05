#!/usr/bin/env python3
"""
publish_blog.py — Add new blog articles to NaukriBulletin

Usage:
  1. Add your article to the ARTICLES list below
  2. Run: python3 scripts/publish_blog.py
  3. Run: ./deploy.sh

Article format:
  {
    "slug": "unique-url-slug",
    "title": "English Title",
    "title_hi": "हिंदी शीर्षक",
    "excerpt": "Short description in English",
    "excerpt_hi": "हिंदी में संक्षिप्त विवरण",
    "category": "Category Name",
    "category_hi": "श्रेणी",
    "tags": ["tag1", "tag2"],
    "date": "05 July 2026",
    "author": "NaukriBulletin Team",
    "read_time": "5 min",
    "featured": False,
    "content_en": "English content in markdown...",
    "content_hi": "हिंदी में सामग्री...",
  }
"""

import json, re, sys
from pathlib import Path
from datetime import datetime

SITE_ROOT  = Path(__file__).parent.parent
BLOG_DIR   = SITE_ROOT / 'blog'
POSTS_FILE = SITE_ROOT / 'scripts' / '_data' / 'blog_posts.json'
YR = datetime.now().year

# ── ADD NEW ARTICLES HERE ─────────────────────────────────────────────────────
NEW_ARTICLES = [
    # Paste new article dicts here
    # Example:
    # {
    #   "slug": "my-new-article",
    #   "title": "My Article Title",
    #   ...
    # }
]

# ── BUILDER ───────────────────────────────────────────────────────────────────
NAV = """<nav>
  <a href="/" class="logo" style="text-decoration:none;"><span class="logo-naukri">Naukri</span><span class="logo-bull">Bulletin</span></a>
  <ul id="navLinks">
    <li><a href="/jobs/">Jobs</a></li>
    <li><a href="/sarkari-naukri/">सरकारी नौकरी</a></li>
    <li><a href="/current-affairs/">Current Affairs</a></li>
    <li><a href="/results/">Results</a></li>
    <li><a href="/exam-calendar/">Exam Calendar</a></li>
    <li><a href="/syllabus/">Syllabus</a></li>
    <li><a href="/mock-test/">Mock Tests</a></li>
    <li><a href="/admit-card/">Admit Cards</a></li>
    <li><a href="/daily-quiz/">Daily Quiz</a></li>
    <li><a href="/previous-year-papers/">PYP</a></li>
    <li><a href="/ask-ai/">Ask AI 🤖</a></li>
  </ul>
  <div class="nav-right"><a href="/alerts/" class="nav-cta">🔔 Get Alerts</a></div>
  <button class="nav-hamburger" id="navHamburger" onclick="toggleMobileNav()" aria-label="Menu"><span></span><span></span><span></span></button>
</nav>"""

FOOTER = f"""<footer style="border-top:1px solid var(--border);background:var(--navy);padding:24px 0;margin-top:32px;">
  <div style="max-width:860px;margin:0 auto;padding:0 20px;color:var(--grey-400);font-size:.85rem;display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;">
    <span>© {YR} NaukriBulletin</span>
    <span><a href="/blog/" style="color:var(--grey-700);">Blog</a> · <a href="/schemes/" style="color:var(--grey-700);">Schemes</a> · <a href="/ask-ai/" style="color:var(--grey-700);">Ask AI</a></span>
  </div>
</footer>
<script src="/js/naukribot.js" defer></script>
<script>(function(){{var b=document.getElementById("navHamburger");var u=document.querySelector("nav ul");if(!b||!u)return;b.addEventListener("click",function(){{u.classList.toggle("mobile-open");b.classList.toggle("active");}});u.querySelectorAll("a").forEach(function(a){{a.addEventListener("click",function(){{u.classList.remove("mobile-open");b.classList.remove("active");}});}});}})();</script>"""

STYLE = """<style>
.bh2{font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:700;color:var(--white);margin:28px 0 12px;border-left:3px solid var(--saffron);padding-left:12px}
.bh3{font-size:1rem;font-weight:700;color:var(--white);margin:20px 0 8px}
.bp{color:var(--grey-700);line-height:1.8;font-size:.95rem;margin-bottom:14px}
.bul,.bol{margin:0 0 16px;padding-left:22px;background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px 14px 14px 32px}
.bul li,.bol li{padding:6px 0;color:var(--grey-700);font-size:.93rem;line-height:1.6;border-bottom:1px solid var(--border)}
.bul li:last-child,.bol li:last-child{border-bottom:none}
.bstep{counter-increment:step;background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px 16px 14px 48px;position:relative;margin-bottom:10px;color:var(--grey-700);font-size:.93rem;line-height:1.6}
.bstep::before{content:counter(step);position:absolute;left:14px;top:50%;transform:translateY(-50%);background:var(--saffron);color:#fff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.8rem}
.bsteps{counter-reset:step;margin:0 0 20px}
code{background:rgba(255,255,255,.08);padding:2px 6px;border-radius:4px;font-size:.88rem;color:var(--saffron)}
strong{color:var(--white)}
.btip{background:rgba(99,255,218,.06);border:1px solid rgba(99,255,218,.2);border-radius:10px;padding:14px 18px;margin-bottom:16px;font-size:.9rem;color:var(--text);line-height:1.6}
.bwarn{background:rgba(255,214,108,.06);border:1px solid rgba(255,214,108,.2);border-radius:10px;padding:14px 18px;margin-bottom:16px;font-size:.9rem;color:var(--yellow);line-height:1.6}
</style>"""

def md_to_html(text):
    """Convert simple markdown to styled HTML."""
    lines = text.strip().split('\n')
    html = []
    in_list = False
    in_ol = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list: html.append('</ul>'); in_list = False
            if in_ol:   html.append('</div>'); in_ol = False
            html.append('')
            continue

        if stripped.startswith('## '):
            if in_list: html.append('</ul>'); in_list = False
            if in_ol:   html.append('</div>'); in_ol = False
            html.append(f'<h2 class="bh2">{fmt(stripped[3:])}</h2>')
        elif stripped.startswith('### '):
            html.append(f'<h3 class="bh3">{fmt(stripped[4:])}</h3>')
        elif re.match(r'^\d+\. ', stripped):
            if not in_ol: html.append('<div class="bsteps">'); in_ol = True
            html.append(f'<div class="bstep">{fmt(re.sub(r"^\d+\. ", "", stripped))}</div>')
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if in_ol: html.append('</div>'); in_ol = False
            if not in_list: html.append('<ul class="bul">'); in_list = True
            html.append(f'<li>{fmt(stripped[2:])}</li>')
        elif stripped.startswith('> '):
            html.append(f'<div class="btip">💡 {fmt(stripped[2:])}</div>')
        elif stripped.startswith('⚠️') or stripped.startswith('NOTE:'):
            html.append(f'<div class="bwarn">{fmt(stripped)}</div>')
        else:
            if in_list: html.append('</ul>'); in_list = False
            if in_ol:   html.append('</div>'); in_ol = False
            html.append(f'<p class="bp">{fmt(stripped)}</p>')

    if in_list: html.append('</ul>')
    if in_ol:   html.append('</div>')
    return '\n'.join(html)

def fmt(text):
    """Format inline markdown."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank" rel="noopener" style="color:var(--saffron);">\1</a>', text)
    return text

def build_article(post, lang='en'):
    title   = post['title'] if lang == 'en' else post.get('title_hi', post['title'])
    excerpt = post['excerpt'] if lang == 'en' else post.get('excerpt_hi', post['excerpt'])
    content = md_to_html(post.get('content_en','') if lang == 'en' else post.get('content_hi', post.get('content_en','')))
    cat     = post['category'] if lang == 'en' else post.get('category_hi', post['category'])
    slug    = post['slug']

    lang_toggle = ''
    if post.get('lang') == 'both' or (post.get('content_hi') and post.get('content_en')):
        if lang == 'en':
            lang_toggle = f'<a href="/blog/{slug}/hi/" style="background:rgba(255,255,255,.06);color:var(--muted);padding:4px 12px;border-radius:20px;font-size:.78rem;text-decoration:none;margin-left:8px;">हिंदी में पढ़ें</a>'
        else:
            lang_toggle = f'<a href="/blog/{slug}/" style="background:rgba(255,255,255,.06);color:var(--muted);padding:4px 12px;border-radius:20px;font-size:.78rem;text-decoration:none;margin-left:8px;">Read in English</a>'

    schema = json.dumps({
        "@context":"https://schema.org","@type":"Article",
        "headline":title,"datePublished":post["date"],
        "author":{"@type":"Organization","name":"NaukriBulletin"},
        "publisher":{"@type":"Organization","name":"NaukriBulletin","url":"https://naukribulletin.in"},
        "description": excerpt[:155]
    }, ensure_ascii=False)

    canon = f"https://naukribulletin.in/blog/{slug}/{'hi/' if lang=='hi' else ''}"

    return f"""<!DOCTYPE html>
<html lang="{'hi' if lang=='hi' else 'en'}">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title} | NaukriBulletin</title>
  <meta name="description" content="{excerpt[:155]}">
  <link rel="canonical" href="{canon}">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{excerpt[:155]}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/css/style.css">
  {STYLE}
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
  <script type="application/ld+json">{schema}</script>
</head>
<body>
{NAV}
<header style="background:var(--navy);border-bottom:1px solid var(--border);padding:28px 20px 20px;">
  <div style="max-width:860px;margin:0 auto;">
    <div style="font-size:.78rem;color:var(--grey-400);margin-bottom:10px;">
      <a href="/" style="color:var(--grey-400);">Home</a> ›
      <a href="/blog/" style="color:var(--grey-400);">Blog</a> ›
      {title[:50]}
    </div>
    <div style="margin-bottom:10px;">
      <span style="background:rgba(255,107,0,.15);color:var(--saffron);padding:3px 12px;border-radius:20px;font-size:.75rem;font-weight:700;">{cat}</span>
      <span style="color:var(--muted);font-size:.78rem;margin-left:10px;">📖 {post['read_time']} · {post['date']}</span>
      {lang_toggle}
    </div>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;color:var(--white);margin:0 0 8px;line-height:1.3;">{title}</h1>
    <p style="color:var(--grey-700);font-size:.9rem;margin:0;">By <strong style="color:var(--white);">{post['author']}</strong></p>
  </div>
</header>
<main style="max-width:860px;margin:0 auto;padding:24px 20px 40px;">
  {content}
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:18px;margin-top:28px;">
    <div style="font-weight:700;color:var(--white);margin-bottom:10px;">उपयोगी लिंक / Useful Links</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <a href="/schemes/" style="background:var(--saffron);color:#fff;padding:8px 16px;border-radius:8px;font-weight:700;text-decoration:none;font-size:.85rem;">🏛️ Scheme Checker</a>
      <a href="/ask-ai/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:8px 16px;border-radius:8px;font-weight:600;text-decoration:none;font-size:.85rem;">🤖 Ask NaukriBot</a>
      <a href="/blog/" style="background:var(--card-bg);border:1px solid var(--border);color:var(--white);padding:8px 16px;border-radius:8px;font-weight:600;text-decoration:none;font-size:.85rem;">📝 More Guides</a>
    </div>
  </div>
</main>
{FOOTER}
</body>
</html>"""

def build_listing(posts):
    cards = ''
    for p in sorted(posts, key=lambda x: (not x.get('featured',False), x['date']), reverse=False):
        fb = '<span style="background:rgba(255,107,0,.15);color:var(--saffron);padding:2px 8px;border-radius:12px;font-size:.72rem;font-weight:700;margin-right:6px;">⭐</span>' if p.get('featured') else ''
        tags = ''.join(f'<span style="background:rgba(255,255,255,.05);color:var(--muted);padding:2px 8px;border-radius:12px;font-size:.72rem;margin-right:4px;">#{t}</span>' for t in p.get('tags',[]))
        cards += f"""<a href="/blog/{p['slug']}/" style="text-decoration:none;display:block;margin-bottom:12px;">
  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:18px;transition:.15s" onmouseover="this.style.borderColor='rgba(255,107,0,.4)'" onmouseout="this.style.borderColor='rgba(255,255,255,.1)'">
    <div style="margin-bottom:7px;">{fb}<span style="color:var(--saffron);font-size:.75rem;font-weight:700;">{p['category']}</span><span style="color:var(--muted);font-size:.75rem;margin-left:10px;">📖 {p['read_time']} · {p['date']}</span></div>
    <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin-bottom:6px;line-height:1.4;">{p['title']}</div>
    <div style="color:var(--grey-700);font-size:.88rem;line-height:1.5;margin-bottom:8px;">{p['excerpt']}</div>
    <div>{tags}</div>
  </div>
</a>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Blog — MP Schemes, Govt Services & Exam Prep | NaukriBulletin</title>
  <meta name="description" content="Step-by-step guides for Aadhaar update, Samagra ID, certificates, scholarships, DBT, NPCI and all MP government services — Hindi & English.">
  <link rel="canonical" href="https://naukribulletin.in/blog/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1001412206051588" crossorigin="anonymous"></script>
</head>
<body>
{NAV}
<header style="background:var(--navy);border-bottom:1px solid var(--border);padding:28px 20px 20px;">
  <div style="max-width:860px;margin:0 auto;">
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.7rem;color:var(--white);margin:0 0 8px;">📝 Blog</h1>
    <p style="color:var(--grey-700);font-size:.9rem;margin:0 0 14px;">Step-by-step guides for Aadhaar, Samagra, certificates, scholarships, DBT and all govt services — हिंदी & English</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <span style="background:rgba(255,107,0,.15);color:var(--saffron);padding:4px 12px;border-radius:20px;font-size:.78rem;font-weight:700;">{len(posts)} Guides</span>
      <a href="/schemes/" style="background:rgba(255,255,255,.06);color:var(--text);padding:4px 12px;border-radius:20px;font-size:.78rem;text-decoration:none;border:1px solid var(--border);">🏛️ Scheme Checker</a>
      <a href="/ask-ai/" style="background:rgba(255,255,255,.06);color:var(--text);padding:4px 12px;border-radius:20px;font-size:.78rem;text-decoration:none;border:1px solid var(--border);">🤖 Ask AI</a>
    </div>
  </div>
</header>
<main style="max-width:860px;margin:0 auto;padding:20px 16px 40px;">{cards}</main>
{FOOTER}
</body>
</html>"""

def main():
    # Load existing posts
    existing = []
    if POSTS_FILE.exists():
        existing = json.loads(POSTS_FILE.read_text())

    existing_slugs = {p['slug'] for p in existing}

    if not NEW_ARTICLES:
        print("No new articles in NEW_ARTICLES list.")
        print("Rebuilding all existing pages...")
        all_posts = existing
    else:
        new_posts = [p for p in NEW_ARTICLES if p['slug'] not in existing_slugs]
        all_posts = existing + new_posts
        print(f"Adding {len(new_posts)} new articles (skipping {len(NEW_ARTICLES)-len(new_posts)} duplicates)")

    BLOG_DIR.mkdir(exist_ok=True)

    # Build listing
    (BLOG_DIR / 'index.html').write_text(build_listing(all_posts), encoding='utf-8')
    print("✅ /blog/index.html rebuilt")

    # Build article pages
    for post in all_posts:
        en_dir = BLOG_DIR / post['slug']
        en_dir.mkdir(exist_ok=True)
        (en_dir / 'index.html').write_text(build_article(post, 'en'), encoding='utf-8')

        if post.get('content_hi') and 'जल्द' not in post.get('content_hi',''):
            hi_dir = en_dir / 'hi'
            hi_dir.mkdir(exist_ok=True)
            (hi_dir / 'index.html').write_text(build_article(post, 'hi'), encoding='utf-8')

    # Save posts JSON
    POSTS_FILE.parent.mkdir(exist_ok=True)
    POSTS_FILE.write_text(json.dumps(all_posts, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✅ {len(all_posts)} total articles. Run ./deploy.sh to publish.")

if __name__ == '__main__':
    main()
