#!/bin/bash
# NaukriBulletin — local deploy script

set -e

# ── 1. Sync with remote before doing anything ─────────────────────────────────
echo "📥 Pulling latest from remote..."
git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
  echo "   Remote has new commits — rebasing..."
  git stash
  git rebase origin/main
  git stash pop 2>/dev/null || true
fi

# ── 1b. SEO hardening pass (idempotent) ───────────────────────────────────────
echo "🛡️  Running SEO hardening pass..."
python3 scripts/seo_perfect.py --apply || echo "   (seo_perfect skipped)"

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

# ── 3. Commit local changes if any ───────────────────────────────────────────
if ! git diff --quiet HEAD; then
  echo "📝 Committing local changes..."
  git add .
  git commit -m "Deploy: $(date +'%d %b %Y %H:%M')"
  git push origin main
fi

# ── 4. Deploy to Cloudflare ───────────────────────────────────────────────────
echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
