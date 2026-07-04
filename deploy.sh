#!/bin/bash
# NaukriBulletin — local deploy script (conflict-proof)

set -e

# ── 0. Fix nav + inject NaukriBot on all pages ────────────────────────────────
echo "🔧 Fixing nav consistency..."
python3 - << 'PYEOF'
import re, pathlib, shutil

root = pathlib.Path('.')
OLD_NAV = re.compile(r'<ul id="navLinks">.*?</ul>', re.S)
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
    <li><a href="/ask-ai/">Ask AI 🤖</a></li>
  </ul>'''

BOT_TAG = '<script src="/js/naukribot.js" defer></script>'
nav_fixed = bot_fixed = 0

for f in root.rglob('*.html'):
    if 'dist' in str(f) or '.git' in str(f): continue
    try:
        s = f.read_text(errors='ignore')
        changed = False
        if 'id="navLinks"' in s:
            m = re.search(r'<ul id="navLinks">(.*?)</ul>', s, re.S)
            if m:
                links = re.findall(r'href="([^"]+)"', m.group(1))
                if '/ask-ai/' not in links or '/daily-quiz/' not in links or '/sarkari-naukri/' not in links:
                    s = OLD_NAV.sub(NEW_NAV, s, count=1)
                    nav_fixed += 1
                    changed = True
        if '</body>' in s and 'naukribot' not in s:
            s = s.replace('</body>', BOT_TAG + '\n</body>', 1)
            bot_fixed += 1
            changed = True
        if changed:
            f.write_text(s)
    except: pass

js = root / 'dist' / 'js'
js.mkdir(exist_ok=True)
src = root / 'scripts' / 'naukribot.js'
if src.exists():
    shutil.copy2(src, js / 'naukribot.js')

print(f"Nav fixed: {nav_fixed} | NaukriBot: {bot_fixed}")
PYEOF

# ── 1. SEO hardening ──────────────────────────────────────────────────────────
echo "🛡️  Running SEO hardening pass..."
python3 scripts/seo_perfect.py --apply

# ── 2. Sync dist/ ─────────────────────────────────────────────────────────────
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

# ── 3. Commit + push ──────────────────────────────────────────────────────────
echo "📝 Committing and pushing..."
git add -A
git diff --cached --quiet || git commit -m "Deploy: $(date +'%d %b %Y %H:%M')"

git fetch origin main
git push origin main --force-with-lease || {
  git pull origin main --no-rebase -X ours --no-edit 2>/dev/null || true
  git push origin main
}

# ── 4. Deploy to Cloudflare ───────────────────────────────────────────────────
echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
