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

echo "🚀 Deploying to Cloudflare..."
npx wrangler deploy

echo "✅ Done"
