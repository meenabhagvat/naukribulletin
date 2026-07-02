#!/bin/bash
# NaukriBulletin — local deploy script (conflict-proof)

set -e

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

# ── 3. Commit + push (ours wins, no rebase) ───────────────────────────────────
echo "📝 Committing and pushing..."
git add -A
git diff --cached --quiet || git commit -m "Deploy: $(date +'%d %b %Y %H:%M')"

# Fetch remote but DON'T rebase — just force our version through
git fetch origin main
git push origin main --force-with-lease || {
  # If force-with-lease fails (rare), pull CI changes then push
  git pull origin main --no-rebase -X ours --no-edit 2>/dev/null || true
  git push origin main
}

# ── 4. Deploy to Cloudflare ───────────────────────────────────────────────────
echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
