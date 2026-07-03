#!/usr/bin/env python3
"""
Batch job page enrichment for NaukriBulletin
Adds: stats grid, How to Apply steps, Documents Required checklist
Safe to re-run — skips already-enriched pages.
"""
import re
from pathlib import Path
from datetime import date, datetime

SITE_ROOT = Path('/Users/meenabhagvat/Projects/naukri-bulletin')
JOBS_DIR  = SITE_ROOT / 'jobs'
TODAY     = datetime.now().strftime("%d %B %Y")
MONTHS    = {'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
             'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}

def days_left(ld):
    if not ld or ld == 'N/A': return None
    m = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', ld, re.I)
    if not m: return None
    try:
        mon = MONTHS.get(m.group(2).lower())
        if not mon: return None
        d = date(int(m.group(3)), mon, int(m.group(1)))
        return (d - date.today()).days
    except: return None

def urgency_colour(dl):
    if dl is None: return 'var(--grey-400)'
    if dl < 0:  return '#888'
    if dl <= 3: return '#FF4444'
    if dl <= 7: return '#FF8C33'
    if dl <= 14:return '#FFD56C'
    return '#63FFDA'

def build_job_rich(data):
    vac   = data.get('total vacancies','N/A')
    ld    = data.get('last date','N/A')
    qual  = data.get('qualification','N/A')
    age   = data.get('age limit','')
    sal   = data.get('salary / pay scale','')
    loc   = data.get('location','All India')
    dept  = data.get('department','')
    dl    = days_left(ld)
    ld_col= urgency_colour(dl)

    # Stats grid
    stats = [
        ('👥 Vacancies', vac, 'var(--saffron)'),
        ('⏰ Last Date', ld, ld_col),
        ('📍 Location', loc, 'var(--white)'),
        ('🎓 Qualification', qual[:40] if qual else 'N/A', 'var(--white)'),
    ]
    if age and age != 'N/A':
        stats.append(('🎂 Age Limit', age, 'var(--white)'))
    if sal and sal != 'N/A':
        stats.append(('💰 Salary', sal[:40], '#63FFDA'))

    stats_html = ''.join(
        f'<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px;">'
        f'<div style="font-size:.72rem;color:var(--grey-400);font-weight:700;text-transform:uppercase;margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:.9rem;font-weight:700;color:{col};line-height:1.3;">{val}</div>'
        f'</div>'
        for label, val, col in stats
    )

    # How to Apply steps
    steps = [
        f'Visit the official website of <strong style="color:var(--white);">{dept or "the recruiting organisation"}</strong> and go to the Recruitment / Careers section.',
        'Download and read the official notification PDF carefully — note vacancies, eligibility, fee structure and important dates.',
        f'Check your eligibility: Qualification required — <strong style="color:var(--white);">{qual}</strong>' + (f', Age limit — <strong style="color:var(--white);">{age}</strong>' if age and age != 'N/A' else '') + '.',
        'Register on the official portal with a valid email ID and mobile number.',
        'Fill in the online application form accurately — personal details, educational qualifications and category.',
        f'Pay the application fee (if applicable) through online mode and submit before <strong style="color:var(--white);">{ld}</strong>.',
        'Save your application number and take a printout of the confirmation page for future reference.',
    ]
    steps_html = ''.join(
        f'<li style="padding:9px 0;color:var(--grey-700);border-bottom:1px solid var(--border);font-size:.9rem;line-height:1.6;">{s}</li>'
        for s in steps
    )

    # Documents checklist
    docs = [
        '10th marksheet (Date of Birth proof)',
        '12th marksheet',
        'Graduation / Degree certificate (if required)',
        'Caste certificate (for SC/ST/OBC candidates)',
        'Income certificate (for EWS category)',
        'Passport-size photograph (recent, white background)',
        'Scanned signature',
        'Valid photo ID (Aadhaar card / PAN card / Voter ID)',
        'PWD certificate (for PH/Divyang candidates, if applicable)',
    ]
    docs_html = ''.join(
        f'<li style="padding:5px 0;color:var(--grey-700);font-size:.88rem;">✓ {d}</li>'
        for d in docs
    )

    # Salary block
    sal_block = ''
    if sal and sal != 'N/A' and len(sal) < 100:
        sal_block = (
            f'<div style="background:rgba(99,255,218,.06);border:1px solid rgba(99,255,218,.2);'
            f'border-radius:10px;padding:14px 18px;margin-bottom:16px;">'
            f'<div style="font-size:.75rem;font-weight:700;color:#63FFDA;text-transform:uppercase;margin-bottom:4px;">💰 Salary / Pay Scale</div>'
            f'<div style="color:var(--white);font-weight:600;font-size:.95rem;">{sal}</div>'
            f'</div>'
        )

    return f'''<!-- NB-JOB-RICH-BLOCK -->
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;">
{stats_html}
</div>
{sal_block}
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:16px;">
  <div style="padding:14px 18px;border-bottom:1px solid var(--border);background:var(--navy-soft);">
    <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">📋 How to Apply — Step by Step</h2>
  </div>
  <div style="padding:4px 18px 12px;">
    <ol style="margin:0;padding-left:18px;">{steps_html}</ol>
  </div>
</div>
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:16px;">
  <div style="padding:14px 18px;border-bottom:1px solid var(--border);background:var(--navy-soft);">
    <h2 style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--white);margin:0;">📄 Documents Required</h2>
  </div>
  <div style="padding:8px 18px 14px;">
    <ul style="margin:0;padding-left:18px;">{docs_html}</ul>
  </div>
</div>
<div style="background:rgba(255,107,0,.06);border:1px solid rgba(255,107,0,.2);border-radius:12px;padding:14px 18px;margin-bottom:16px;">
  <div style="font-size:.82rem;font-weight:700;color:var(--saffron);margin-bottom:6px;">⚠️ Important</div>
  <div style="font-size:.85rem;color:var(--grey-700);line-height:1.6;">Always download the official notification PDF before applying. Verify eligibility, fee and dates on the official website. NaukriBulletin provides information only — apply directly on the official portal.</div>
</div>
<!-- END-NB-JOB-RICH-BLOCK -->'''


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
enriched = skipped = errors = 0
job_dirs = [p for p in JOBS_DIR.iterdir() if p.is_dir() and (p/'index.html').exists()]
# Skip state hub pages (they have many jobs, not a single job page)
STATE_SLUGS = {
    'andhra-pradesh','arunachal-pradesh','assam','bihar','chhattisgarh','goa','gujarat',
    'haryana','himachal-pradesh','jharkhand','karnataka','kerala','madhya-pradesh',
    'maharashtra','manipur','meghalaya','mizoram','nagaland','odisha','punjab','rajasthan',
    'sikkim','tamil-nadu','telangana','tripura','uttar-pradesh','uttarakhand','west-bengal',
    'andaman-nicobar','chandigarh','dadra-nagar-haveli','daman-diu','delhi','jammu-kashmir',
    'ladakh','lakshadweep','puducherry',
    # category hubs
    'ssc','railway','banking','upsc','defence','police','teaching','state-psc',
    'engineering','medical','graduate','10th','12th',
}

print(f"Found {len(job_dirs)} job directories")

for i, page_dir in enumerate(sorted(job_dirs)):
    if page_dir.name in STATE_SLUGS:
        skipped += 1
        continue

    idx_file = page_dir / 'index.html'
    try:
        html = idx_file.read_text(encoding='utf-8', errors='ignore')

        # Skip already enriched
        if 'NB-JOB-RICH-BLOCK' in html:
            skipped += 1
            continue

        # Skip non-job pages (hub pages, listing pages)
        if html.count('<table') == 0:
            skipped += 1
            continue

        # Skip very large hub pages
        if len(html) > 50000:
            skipped += 1
            continue

        # Extract table data
        table_m = re.search(r'<table[^>]*>(.*?)</table>', html, re.S)
        data = {}
        if table_m:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_m.group(1), re.S)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
                if len(cells) >= 2:
                    k = re.sub(r'<[^>]+>','',cells[0]).strip().lower()
                    v = re.sub(r'<[^>]+>','',cells[1]).strip()
                    if k and v and len(k) < 40:
                        data[k] = v

        # Need at least some data to enrich meaningfully
        if not data:
            skipped += 1
            continue

        # Build rich block
        rich = build_job_rich(data)

        # Inject after </table> closing div, before Apply button
        # Pattern: </table>\n      </div>\n\n      <div style="text-align:center
        inject_pattern = re.search(
            r'(</table>\s*</div>\s*)\n(\s*<div style="text-align:center)',
            html, re.S
        )
        if inject_pattern:
            insert = inject_pattern.start(2)
            html = html[:insert] + '\n      <!-- Rich Job Content -->\n      <div style="max-width:900px;margin:0 auto 0;padding:0 20px;">\n        ' + rich + '\n      </div>\n\n      ' + html[insert:].lstrip()
        else:
            # Fallback: inject before Apply button
            apply_m = re.search(r'(<div style="text-align:center;margin:32px)', html)
            if apply_m:
                insert = apply_m.start()
                html = html[:insert] + '\n<div style="max-width:900px;margin:0 auto;padding:0 20px;">' + rich + '</div>\n' + html[insert:]
            else:
                skipped += 1
                continue

        idx_file.write_text(html, encoding='utf-8')
        enriched += 1

        if enriched % 50 == 0:
            print(f"  Progress: {enriched} enriched ({i}/{len(job_dirs)} processed)...")

    except Exception as e:
        errors += 1

print(f"\nDone!")
print(f"  Enriched: {enriched} job pages")
print(f"  Skipped (hub/state/already done): {skipped}")
print(f"  Errors: {errors}")
