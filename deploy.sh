#!/bin/bash
# NaukriBulletin — local deploy script (conflict-proof)

set -e

# ── 0. Fix nav on ALL pages (runs every deploy) ───────────────────────────────
echo "🔧 Fixing nav consistency..."
python3 - << 'PYEOF'
import re, pathlib

root = pathlib.Path('.')
OLD_NAV = re.compile(
    r'<ul id="navLinks">.*?</ul>',
    re.S
)
NEW_NAV = '''<ul id="navLinks">
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
  </ul>'''

fixed = 0
for f in root.rglob('*.html'):
    if 'dist' in str(f) or '.git' in str(f): continue
    try:
        s = f.read_text(errors='ignore')
        if 'id="navLinks"' not in s: continue
        # Check if nav already has all 10 links
        m = re.search(r'<ul id="navLinks">(.*?)</ul>', s, re.S)
        if not m: continue
        links = re.findall(r'href="([^"]+)"', m.group(1))
        if '/daily-quiz/' in links and '/previous-year-papers/' in links and '/sarkari-naukri/' in links:
            continue  # already correct
        # Replace with canonical nav
        new_s = OLD_NAV.sub(NEW_NAV, s, count=1)
        if new_s != s:
            f.write_text(new_s)
            fixed += 1
    except: pass
print(f"Nav fixed on {fixed} pages")
PYEOF

# ── 1. Inject NaukriBot on all pages ─────────────────────────────────────────
echo "🤖 Injecting NaukriBot widget..."
mkdir -p dist/js
cp scripts/naukribot.js dist/js/naukribot.js 2>/dev/null || true
python3 - << 'PYEOF'
import pathlib
root = pathlib.Path('.')
tag = '<script src="/js/naukribot.js" defer></script>'
fixed = 0
for f in root.rglob('*.html'):
    if 'dist' in str(f) or '.git' in str(f): continue
    try:
        s = f.read_text(errors='ignore')
        if '</body>' in s and 'naukribot' not in s:
            f.write_text(s.replace('</body>', tag + '\n</body>', 1))
            fixed += 1
    except: pass
print(f"NaukriBot: {fixed} pages updated")
PYEOF

# ── 2. SEO hardening ──────────────────────────────────────────────────────────
echo "🛡️  Running SEO hardening pass..."
python3 scripts/seo_perfect.py --apply

# ── 3. Sync dist/ ─────────────────────────────────────────────────────────────
echo "🔄 Syncing dist/..."
rsync -a --delete \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='scripts' \
  --exclude='*.py' \
  --exclude='*.md' \
  --exclude='*.sh' \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='.wrangler' \
  --exclude='.wranglerignore' \
  --exclude='*.toml' \
  --exclude='.gitignore' \
  --exclude='.DS_Store' \
  . dist/

cp _redirects dist/_redirects 2>/dev/null || true
mkdir -p dist/js
cp scripts/naukribot.js dist/js/naukribot.js 2>/dev/null || true

# ── 4. Commit + push ──────────────────────────────────────────────────────────
echo "📝 Committing and pushing..."
git add -A
git diff --cached --quiet || git commit -m "Deploy: $(date +'%d %b %Y %H:%M')"

git fetch origin main
git push origin main --force-with-lease || {
  git pull origin main --no-rebase -X ours --no-edit 2>/dev/null || true
  git push origin main
}

# ── 5. Deploy to Cloudflare ───────────────────────────────────────────────────
echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
