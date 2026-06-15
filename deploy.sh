#!/bin/bash
set -e

echo "🔄 Syncing dist/..."
rsync -a --delete \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='.gitignore' \
  --exclude='scripts' \
  --exclude='*.py' \
  --exclude='*.md' \
  --exclude='*.sh' \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='.wrangler' \
  --exclude='.wranglerignore' \
  --exclude='*.toml' \
  --exclude='.DS_Store' \
  --exclude='patch_*.py' \
  --exclude='fix_*.py' \
  . dist/

cp _redirects dist/_redirects 2>/dev/null || true
echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
