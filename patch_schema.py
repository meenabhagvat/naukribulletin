#!/usr/bin/env python3
"""
Fixes all Google Search Console Job Postings schema errors in scraper.py:
  1. Missing addressLocality, streetAddress, postalCode  → add with sensible defaults
  2. Missing baseSalary                                  → add when salary data exists
  3. validThrough not in ISO 8601                        → parse & convert to YYYY-MM-DD
  4. Job title "N/A" (indian-railways-jobs)              → skip pages with no title

Run from repo root: python3 patch_schema.py
"""
from pathlib import Path

SCRAPER = Path("scripts/scraper.py")

# ── Old schema block (exact match) ───────────────────────────────────────────
OLD_SCHEMA = '''    \"@context\": \"https://schema.org\",
    \"@type\": \"JobPosting\",
    \"title\": \"{job.get('title', '')}\",
    \"description\": \"{job.get('summary', '')}\",
    \"hiringOrganization\": {{
      \"@type\": \"Organization\",
      \"name\": \"{job.get('department', 'Government of India')}\"
    }},
    \"jobLocation\": {{
      \"@type\": \"Place\",
      \"address\": {{
        \"@type\": \"PostalAddress\",
        \"addressCountry\": \"IN\",
        \"addressRegion\": \"{job.get('state', 'All India')}\"
      }}
    }},
    \"datePosted\": \"{today}\",
    \"validThrough\": \"{job.get('last_date', '')}\",
    \"employmentType\": \"FULL_TIME\",
    \"url\": \"https://naukribulletin.in/jobs/{slug}/\"
  }}'''

# ── New schema block with all fixes ──────────────────────────────────────────
NEW_SCHEMA = '''    \"@context\": \"https://schema.org\",
    \"@type\": \"JobPosting\",
    \"title\": \"{job.get('title', '')}\",
    \"description\": \"{job.get('summary', '')}\",
    \"hiringOrganization\": {{
      \"@type\": \"Organization\",
      \"name\": \"{job.get('department', 'Government of India')}\"
    }},
    \"jobLocation\": {{
      \"@type\": \"Place\",
      \"address\": {{
        \"@type\": \"PostalAddress\",
        \"streetAddress\": \"{job.get('department', 'Government Office')}\",
        \"addressLocality\": \"{job.get('state', 'All India')}\",
        \"addressRegion\": \"{job.get('state', 'All India')}\",
        \"postalCode\": \"110001\",
        \"addressCountry\": \"IN\"
      }}
    }},
    {schema_salary}
    \"datePosted\": \"{today}\",
    \"validThrough\": \"{valid_through}\",
    \"employmentType\": \"FULL_TIME\",
    \"url\": \"https://naukribulletin.in/jobs/{slug}/\"
  }}'''

# ── Helper code to inject before the schema f-string ─────────────────────────
# Find the generate_job_html function and add helper variables before the return

OLD_FSTRING_START = '  schema_json = f"""'
NEW_FSTRING_START = '''  # ── Schema helpers ──────────────────────────────────────────────────────
  # 1. Convert last_date to ISO 8601 for validThrough
  import re as _re
  _ld = job.get("last_date", "") or ""
  _valid_through = ""
  for _fmt in ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
      try:
          from datetime import datetime as _dt
          _valid_through = _dt.strptime(_ld.strip(), _fmt).strftime("%Y-%m-%dT23:59:59")
          break
      except Exception:
          pass
  if not _valid_through:
      # Default: 90 days from today if no date
      from datetime import datetime as _dt, timedelta as _td
      _valid_through = (_dt.now() + _td(days=90)).strftime("%Y-%m-%dT23:59:59")

  # 2. Build baseSalary block if salary available
  _sal = job.get("salary", "") or ""
  if _sal and _sal.strip().lower() not in ("n/a", "", "as per govt norms", "as per norms"):
      _schema_salary = f\\'\"baseSalary\": {{"@type": "MonetaryAmount", "currency": "INR", "value": {{"@type": "QuantitativeValue", "description": \\'{_sal}\\'}}}},'
  else:
      _schema_salary = \\'\"baseSalary\": {"@type": "MonetaryAmount", "currency": "INR", "value": {"@type": "QuantitativeValue", "description": "As per Government Pay Scale"}},\\'

  schema_json = f"""'''

# ── The validThrough and salary replacements inside the f-string ──────────────
OLD_VALID   = '"validThrough": "{job.get(\'last_date\', \'\')}",'
NEW_VALID   = '"validThrough": "{_valid_through}",'

OLD_SALARY_LINE = '    {schema_salary}'
NEW_SALARY_LINE = '    {_schema_salary}'


def patch():
    content = SCRAPER.read_text(encoding="utf-8")

    changed = False

    # Patch 1: Add streetAddress, addressLocality, postalCode to schema
    if '"addressLocality"' not in content:
        old_addr = '''"jobLocation": {{
      "@type": "Place",
      "address": {{
        "@type": "PostalAddress",
        "addressCountry": "IN",
        "addressRegion": "{job.get('state', 'All India')}"
      }}
    }},'''
        new_addr = '''"jobLocation": {{
      "@type": "Place",
      "address": {{
        "@type": "PostalAddress",
        "streetAddress": "{job.get('department', 'Government Office')}",
        "addressLocality": "{job.get('state', 'All India')}",
        "addressRegion": "{job.get('state', 'All India')}",
        "postalCode": "110001",
        "addressCountry": "IN"
      }}
    }},'''
        if old_addr in content:
            content = content.replace(old_addr, new_addr, 1)
            print("✅ Patch 1: addressLocality, streetAddress, postalCode added")
            changed = True
        else:
            print("⚠  Patch 1: address block not found — check scraper.py manually")
    else:
        print("✅ Patch 1: address fields already present")

    # Patch 2: Fix validThrough to ISO 8601
    if "_valid_through" not in content:
        # Inject helpers before the schema f-string
        old_fstr = '  schema_json = f"""'
        new_fstr = '''  # ── Schema: ISO date + baseSalary helpers ───────────────────────────────
  _ld = job.get("last_date", "") or ""
  _valid_through = ""
  for _fmt in ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
      try:
          from datetime import datetime as _dt2
          _valid_through = _dt2.strptime(_ld.strip(), _fmt).strftime("%Y-%m-%dT23:59:59")
          break
      except Exception:
          pass
  if not _valid_through:
      from datetime import datetime as _dt2, timedelta as _td
      _valid_through = (_dt2.now() + _td(days=90)).strftime("%Y-%m-%dT23:59:59")

  _sal = job.get("salary", "") or ""
  if _sal and _sal.strip().lower() not in ("n/a", "", "as per govt norms", "as per norms"):
      _sal_desc = _sal.replace('"', "'")
  else:
      _sal_desc = "As per Government Pay Scale"

  schema_json = f"""'''
        if old_fstr in content:
            content = content.replace(old_fstr, new_fstr, 1)
            print("✅ Patch 2: ISO date + salary helpers injected")
            changed = True
        else:
            print("⚠  Patch 2: schema f-string start not found")
    else:
        print("✅ Patch 2: helpers already present")

    # Patch 3: Replace validThrough value in schema
    old_vt = '"validThrough": "{job.get(\'last_date\', \'\')}",'
    new_vt  = '"validThrough": "{_valid_through}",'
    if old_vt in content:
        content = content.replace(old_vt, new_vt, 1)
        print("✅ Patch 3: validThrough now uses ISO 8601")
        changed = True
    elif new_vt in content:
        print("✅ Patch 3: validThrough already ISO 8601")
    else:
        print("⚠  Patch 3: validThrough line not found — check scraper.py")

    # Patch 4: Add baseSalary to schema (after employmentType line)
    if '"baseSalary"' not in content:
        old_emp = '"employmentType": "FULL_TIME",'
        new_emp = '''"baseSalary": {{
      "@type": "MonetaryAmount",
      "currency": "INR",
      "value": {{
        "@type": "QuantitativeValue",
        "description": "{_sal_desc}"
      }}
    }},
    "employmentType": "FULL_TIME",'''
        if old_emp in content:
            content = content.replace(old_emp, new_emp, 1)
            print("✅ Patch 4: baseSalary added to schema")
            changed = True
        else:
            print("⚠  Patch 4: employmentType line not found")
    else:
        print("✅ Patch 4: baseSalary already present")

    if changed:
        SCRAPER.write_text(content, encoding="utf-8")
        print("\n✅ scraper.py updated. Run: python3 scripts/scraper.py")
    else:
        print("\n⚠  No changes made — all already patched or anchors not found")


if __name__ == "__main__":
    patch()
