#!/bin/bash
# NaukriBulletin — local deploy script

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
  --exclude='.gitignore' \
  --exclude='.DS_Store' \
  . dist/

cp _redirects dist/_redirects 2>/dev/null || true
echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
