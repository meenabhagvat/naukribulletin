#!/usr/bin/env python3
"""
NaukriBulletin — OneSignal Web Push Integration
App ID: 89e83d08-e30e-46f9-baec-f0167f8baa35

Run:  python3 scripts/onesignal_integrate.py
Does:
  1. Creates OneSignalSDKWorker.js in site root (required by browser spec)
  2. Injects SDK snippet into every HTML file's <head>
  3. Patches scraper.py + category_gen.py to include snippet in future pages
"""

import os
import re
from pathlib import Path

SITE_ROOT  = Path(__file__).parent.parent
APP_ID     = "89e83d08-e30e-46f9-baec-f0167f8baa35"

# ── 1. SERVICE WORKER FILE ────────────────────────────────────────────────────
# Must live at the root of the site so it can control all pages.
# Cloudflare Pages serves static files from root automatically.

SERVICE_WORKER = """importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDKWorker.js");
"""

# ── 2. HEAD SNIPPET ───────────────────────────────────────────────────────────
# Per docs: load SDK with defer, then init inside OneSignalDeferred.
# notifyButton shows a bell widget bottom-left — users can subscribe anytime.
# welcomeNotification fires once when they first subscribe.

HEAD_SNIPPET = f"""  <!-- OneSignal Web Push v16 — App: {APP_ID} -->
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{
        appId: "{APP_ID}",
        notifyButton: {{
          enable: true,
          size: "medium",
          position: "bottom-left",
          text: {{
            "tip.state.unsubscribed":  "Get free govt job alerts!",
            "tip.state.subscribed":    "\\u2713 Job alerts active",
            "tip.state.blocked":       "You have blocked notifications",
            "message.prenotify":       "Click to get instant govt job alerts",
            "message.action.subscribed":   "Thanks for subscribing!",
            "message.action.resubscribed": "You are now subscribed.",
            "message.action.unsubscribed": "Alerts turned off.",
            "dialog.main.title":       "Get Govt Job Alerts",
            "dialog.main.button.subscribe":   "GET ALERTS",
            "dialog.main.button.unsubscribe": "TURN OFF",
            "dialog.blocked.title":    "Unblock Notifications",
            "dialog.blocked.message":  "Follow these steps to allow job alerts:"
          }},
          colors: {{
            "circle.background":        "#FF6B00",
            "circle.foreground":        "white",
            "badge.background":         "#FF6B00",
            "badge.foreground":         "white",
            "badge.bordercolor":        "white",
            "pulse.color":              "#FF6B00",
            "dialog.button.background.hovering": "#e05a00",
            "dialog.button.background.active":   "#c44f00",
            "dialog.button.background":          "#FF6B00",
            "dialog.button.foreground":          "white"
          }}
        }},
        welcomeNotification: {{
          title:   "NaukriBulletin Alerts ON \\ud83c\\udf89",
          message: "You will get instant alerts for new govt jobs!"
        }}
      }});
    }});
  </script>"""

MARKER = "OneSignalDeferred"   # used to detect already-patched files


def write_service_worker():
    sw_path = SITE_ROOT / "OneSignalSDKWorker.js"
    sw_path.write_text(SERVICE_WORKER, encoding="utf-8")
    print(f"  [SW] Written: OneSignalSDKWorker.js")


def patch_html_files():
    patched = skipped = errors = 0
    skip_dirs = {".git", "node_modules", "__pycache__", ".github"}

    for html_path in sorted(SITE_ROOT.rglob("*.html")):
        # Skip files inside hidden/system dirs
        if any(part in skip_dirs for part in html_path.parts):
            continue
        # Skip template files with Python format placeholders
        if "{" in html_path.read_text(encoding="utf-8", errors="ignore")[:200]:
            skipped += 1
            continue
        try:
            content = html_path.read_text(encoding="utf-8")
            if MARKER in content:
                skipped += 1
                continue
            if "</head>" not in content:
                skipped += 1
                continue
            # Insert just before </head>
            new_content = content.replace("</head>", HEAD_SNIPPET + "\n</head>", 1)
            html_path.write_text(new_content, encoding="utf-8")
            patched += 1
        except Exception as e:
            print(f"  [ERR] {html_path.name}: {e}")
            errors += 1

    print(f"  [HTML] Patched {patched} files | Skipped {skipped} | Errors {errors}")
    return patched


def patch_python_scripts():
    """
    Add HEAD_SNIPPET into scraper.py and category_gen.py so all
    future-generated pages also include OneSignal automatically.
    """
    snippet_escaped = HEAD_SNIPPET.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    for script_name in ["scraper.py", "category_gen.py"]:
        path = SITE_ROOT / "scripts" / script_name
        if not path.exists():
            print(f"  [PY] {script_name} not found, skipping")
            continue

        content = path.read_text(encoding="utf-8")
        if MARKER in content:
            print(f"  [PY] {script_name} already patched, skipping")
            continue

        # Find </head> string literals in the Python source and insert before them
        # Pattern: any string ending with </head>
        old = '"</head>"'
        new = f'"{HEAD_SNIPPET}\\n</head>"'

        if old in content:
            content = content.replace(old, new, 1)   # only first occurrence
            path.write_text(content, encoding="utf-8")
            print(f"  [PY] Patched {script_name}")
        else:
            # Try single-quote variant
            old2 = "'</head>'"
            new2 = f"'{HEAD_SNIPPET}\\n</head>'"
            if old2 in content:
                content = content.replace(old2, new2, 1)
                path.write_text(content, encoding="utf-8")
                print(f"  [PY] Patched {script_name} (single-quote variant)")
            else:
                print(f"  [PY] Could not auto-patch {script_name} — add snippet manually")


def run():
    print(f"\n{'='*60}")
    print(f"OneSignal Integration — App ID: {APP_ID}")
    print(f"{'='*60}\n")

    print("1. Writing service worker...")
    write_service_worker()

    print("\n2. Patching HTML files...")
    n = patch_html_files()

    print("\n3. Patching Python scripts...")
    patch_python_scripts()

    print(f"\n{'='*60}")
    print(f"✅ Done — {n} HTML files now have OneSignal")
    print(f"\nNext steps:")
    print(f"  git add .")
    print(f"  git commit -m 'feat: OneSignal web push integrated'")
    print(f"  git push origin main")
    print(f"\nThen in OneSignal dashboard:")
    print(f"  Settings → Push & In-App → Web → configure prompt timing")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
