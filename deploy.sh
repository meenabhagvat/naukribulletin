#!/bin/bash
# NaukriBulletin — local deploy script
# Usage: ./deploy.sh
# Syncs repo → dist/ then deploys to Cloudflare Workers

set -e

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
  . dist/

cp _redirects dist/_redirects 2>/dev/null || true
echo "🚀 Deploying to Cloudflare..."
npx wrangler pages deploy dist/

echo "✅ Done"
