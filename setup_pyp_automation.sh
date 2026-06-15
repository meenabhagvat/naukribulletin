#!/bin/bash
# ============================================================
# NaukriBulletin — PYP Automation Setup
# Run once on your server to install and schedule the scraper
# ============================================================

echo "📦 Installing Python dependencies…"
pip install requests beautifulsoup4 lxml --quiet

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/scrape_pyp.py"

echo "✅ Script path: $SCRIPT_PATH"

# ── Add to crontab (runs daily at 2:00 AM) ──
CRON_JOB="0 2 * * * /usr/bin/python3 $SCRIPT_PATH >> $SCRIPT_DIR/../previous-year-papers/scrape_pyp.log 2>&1"

# Check if cron entry already exists
(crontab -l 2>/dev/null | grep -qF "scrape_pyp.py") && {
  echo "⚠️  Cron job already exists. Skipping."
} || {
  (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
  echo "✅ Cron job added: runs daily at 2 AM"
}

echo ""
echo "Current crontab:"
crontab -l
echo ""

# ── Run once immediately to generate initial data ──
echo "🚀 Running scraper now to generate initial pyp-data.json…"
python3 "$SCRIPT_PATH"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Check previous-year-papers/pyp-data.json was created"
echo "   2. Deploy previous-year-papers/index.html to your site"
echo "   3. Add PYQ link to your nav bar (see patch instructions below)"
echo ""
echo "──────────────────────────────────────────────────────────"
echo "NAV PATCH — Add this <li> to every page's nav-links <ul>:"
echo ""
echo '   <li><a href="/previous-year-papers/">PYQ Papers</a></li>'
echo ""
echo "HOMEPAGE PATCH — Add this to your quick-links / cards section:"
echo ""
cat << 'EOF'
   <a href="/previous-year-papers/" style="display:flex;align-items:center;
      gap:12px;background:linear-gradient(135deg,#0A0F2C,#151C3D);
      border-radius:10px;padding:14px;text-decoration:none;">
     <div style="font-size:1.8rem;">📄</div>
     <div>
       <div style="font-weight:800;font-family:'Syne',sans-serif;
            color:#fff;font-size:1rem;">Previous Year Papers</div>
       <div style="font-size:0.78rem;color:#9BA3B8;margin-top:2px;">
            SSC · Railway · Banking · UPSC</div>
     </div>
   </a>
EOF
echo "──────────────────────────────────────────────────────────"
