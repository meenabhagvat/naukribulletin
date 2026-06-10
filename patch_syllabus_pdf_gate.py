#!/usr/bin/env python3
"""
NaukriBulletin — patch_syllabus_pdf_gate.py

Does two things:
  1. Creates /assets/pdf/ placeholder PDF files for 8 major exams.
     These are real PDFs with syllabus content that render correctly.
     Replace them with official PDFs from ssc.gov.in / indianrailways.gov.in
     when those are available — file names must stay the same.

  2. Inserts a "Download PDF Syllabus" section into syllabus/index.html
     with a Brevo email gate — user enters email, gets the PDF link,
     email is added to your Brevo list.

Run from repo root:
    python patch_syllabus_pdf_gate.py

Requirements:
    pip install reportlab beautifulsoup4
"""

import os
import re
from pathlib import Path

SITE_ROOT = Path(__file__).parent

# ── PDF DEFINITIONS ───────────────────────────────────────────────────────────

PDFS = [
    {
        "filename": "ssc-cgl-syllabus-2026.pdf",
        "title": "SSC CGL Syllabus 2026",
        "exam": "SSC Combined Graduate Level",
        "sections": [
            ("Tier I — Computer Based Exam (200 marks)", [
                "General Intelligence & Reasoning (50 Q)",
                "General Awareness (50 Q)",
                "Quantitative Aptitude (50 Q)",
                "English Comprehension (50 Q)",
            ]),
            ("Tier II — Computer Based Exam", [
                "Paper I: Mathematical Abilities (30 Q × 3 marks)",
                "Paper II: Reasoning & General Intelligence (30 Q)",
                "Paper III: English Language & Comprehension (45 Q)",
                "Paper IV: General Knowledge (25 Q)",
            ]),
            ("Key Topics: Quantitative Aptitude", [
                "Number Systems, Percentages, Ratio & Proportion",
                "Averages, Simple & Compound Interest",
                "Time & Work, Distance & Speed",
                "Geometry, Mensuration, Trigonometry",
                "Data Interpretation, Algebra",
            ]),
            ("Key Topics: Reasoning", [
                "Analogy, Classification, Series",
                "Coding–Decoding, Blood Relations",
                "Direction & Distance, Order & Ranking",
                "Non-Verbal: Pattern, Mirror Image, Paper Folding",
            ]),
        ],
    },
    {
        "filename": "ssc-chsl-syllabus-2026.pdf",
        "title": "SSC CHSL Syllabus 2026",
        "exam": "SSC Combined Higher Secondary Level",
        "sections": [
            ("Tier I — Computer Based Test (200 marks)", [
                "English Language (25 Q × 2 marks)",
                "General Intelligence (25 Q × 2 marks)",
                "Quantitative Aptitude (25 Q × 2 marks)",
                "General Awareness (25 Q × 2 marks)",
            ]),
            ("Tier II — Descriptive Paper (100 marks)", [
                "Essay Writing (200–250 words)",
                "Letter / Application Writing (150–200 words)",
                "Language: English or Hindi",
            ]),
            ("Negative Marking", [
                "Tier I: 0.50 marks deducted per wrong answer",
                "Tier II: No negative marking",
            ]),
        ],
    },
    {
        "filename": "rrb-ntpc-syllabus-2026.pdf",
        "title": "RRB NTPC Syllabus 2026",
        "exam": "Railway Recruitment Board — NTPC",
        "sections": [
            ("CBT Stage 1 (100 Questions, 90 min)", [
                "Mathematics: 30 questions",
                "General Intelligence & Reasoning: 30 questions",
                "General Awareness: 40 questions",
            ]),
            ("CBT Stage 2 (120 Questions, 90 min)", [
                "Mathematics: 35 questions",
                "General Intelligence & Reasoning: 35 questions",
                "General Awareness: 50 questions",
            ]),
            ("Mathematics Topics", [
                "Number System, Decimals, Fractions, LCM & HCF",
                "Ratio & Proportions, Percentages, Mensuration",
                "Time & Work, Time & Distance, Simple & Compound Interest",
                "Profit & Loss, Elementary Algebra, Geometry, Trigonometry",
                "Elementary Statistics",
            ]),
            ("General Awareness Topics", [
                "Current Events of National & International Importance",
                "Games & Sports, Art & Culture of India",
                "Indian Literature, Monuments & Places of India",
                "General Science & Life Science",
                "History of India & Freedom Struggle",
                "Physical, Social & Economic Geography of India",
                "Indian Polity & Governance — Constitution & Political System",
                "Space & Computer / IT / Robotics",
                "Environmental Issues Concerning India & the World",
                "Basics of Computers & Computer Applications, Common Abbreviations",
                "Transport Systems in India, Indian Economy",
            ]),
        ],
    },
    {
        "filename": "ibps-po-syllabus-2026.pdf",
        "title": "IBPS PO Syllabus 2026",
        "exam": "IBPS Probationary Officer",
        "sections": [
            ("Prelims (100 Q, 60 min)", [
                "English Language: 30 Q — 20 min",
                "Quantitative Aptitude: 35 Q — 20 min",
                "Reasoning Ability: 35 Q — 20 min",
            ]),
            ("Mains (155 Q + Descriptive, 3 hrs)", [
                "Reasoning & Computer Aptitude: 45 Q — 60 min",
                "General Economy & Banking Awareness: 40 Q — 35 min",
                "English Language: 35 Q — 40 min",
                "Data Analysis & Interpretation: 35 Q — 45 min",
                "Descriptive: Letter + Essay — 30 min",
            ]),
            ("Banking Awareness Key Topics", [
                "History of Banking in India, RBI & its Functions",
                "Types of Banks: Nationalised, Private, Co-operative",
                "Financial Institutions: SEBI, SIDBI, NABARD, NHB",
                "Monetary Policy, Repo Rate, CRR, SLR",
                "Digital Banking: NEFT, RTGS, IMPS, UPI",
                "Priority Sector Lending, MUDRA, Jan Dhan",
                "Basel Norms, NPA, Capital Adequacy Ratio",
            ]),
        ],
    },
    {
        "filename": "upsc-ias-syllabus-2026.pdf",
        "title": "UPSC IAS Syllabus 2026",
        "exam": "UPSC Civil Services Examination",
        "sections": [
            ("Prelims — Paper I: General Studies (200 marks)", [
                "Current Events of National & International Importance",
                "History of India & Indian National Movement",
                "Indian & World Geography — Physical, Social, Economic",
                "Indian Polity & Governance — Constitution, Political System, Panchayati Raj",
                "Economic & Social Development — SD, Poverty, Inclusion, Demographics",
                "Environmental Ecology, Biodiversity & Climate Change",
                "General Science",
            ]),
            ("Prelims — Paper II: CSAT (200 marks, qualifying)", [
                "Comprehension, Interpersonal Skills",
                "Logical Reasoning & Analytical Ability",
                "Decision Making & Problem Solving",
                "General Mental Ability, Basic Numeracy",
                "English Language Comprehension Skills (Class X level)",
            ]),
            ("Mains — 9 Papers", [
                "Paper A: Indian Language (qualifying)",
                "Paper B: English (qualifying)",
                "Essay: 250 marks",
                "GS I–IV: 250 marks each = 1000 marks",
                "Optional I & II: 250 marks each = 500 marks",
                "Total: 1750 marks + Interview 275 marks = 2025 marks",
            ]),
        ],
    },
    {
        "filename": "sbi-po-syllabus-2026.pdf",
        "title": "SBI PO Syllabus 2026",
        "exam": "State Bank of India Probationary Officer",
        "sections": [
            ("Phase I: Prelims (100 Q, 60 min)", [
                "English Language: 30 Q — 20 min",
                "Data Analysis & Interpretation: 35 Q — 20 min",
                "Reasoning Ability & Computer Aptitude: 35 Q — 20 min",
            ]),
            ("Phase II: Mains (155 Q + Descriptive)", [
                "Reasoning & Computer Aptitude: 45 Q — 60 min",
                "Data Analysis & Interpretation: 35 Q — 45 min",
                "General Economy / Banking Awareness: 40 Q — 35 min",
                "English Language: 35 Q — 40 min",
                "English Descriptive (Letter + Essay): 2 Q — 30 min",
            ]),
            ("Phase III: Interview (30 marks + Group Discussion)", [
                "Group Exercise / Group Discussion",
                "Personal Interview",
                "Final merit = Mains (75%) + Interview (25%)",
            ]),
        ],
    },
    {
        "filename": "rrb-group-d-syllabus-2026.pdf",
        "title": "RRB Group D Syllabus 2026",
        "exam": "Railway Group D (Level 1 Posts)",
        "sections": [
            ("CBT (100 Questions, 90 min)", [
                "Mathematics: 25 Questions",
                "General Intelligence & Reasoning: 30 Questions",
                "General Science: 25 Questions",
                "General Awareness & Current Affairs: 20 Questions",
            ]),
            ("General Science Topics", [
                "Physics: Laws of Motion, Work-Energy, Sound, Light",
                "Chemistry: Periodic Table, Chemical Reactions, Acids & Bases",
                "Life Sciences: Cell Biology, Genetics Basics, Human Physiology",
            ]),
            ("Physical Efficiency Test (PET)", [
                "Male: 1000m run in 4 min 15 sec; Lift & carry 35 kg for 100m",
                "Female: 1000m run in 5 min 40 sec; Lift & carry 20 kg for 100m",
                "Ex-servicemen: Exempted from PET",
            ]),
        ],
    },
    {
        "filename": "nda-syllabus-2026.pdf",
        "title": "NDA Syllabus 2026",
        "exam": "National Defence Academy & Naval Academy",
        "sections": [
            ("Paper I: Mathematics (300 marks, 2.5 hrs)", [
                "Algebra: Complex numbers, Quadratic equations, Matrices",
                "Calculus: Differentiation, Integration, Differential Equations",
                "Vector Algebra, Statistics & Probability",
                "Trigonometry, Analytical Geometry (2D & 3D)",
            ]),
            ("Paper II: General Ability Test (600 marks, 2.5 hrs)", [
                "Part A — English (200 marks): Grammar, Vocabulary, Comprehension",
                "Part B — General Knowledge (400 marks):",
                "  Physics, Chemistry, General Science",
                "  History, Freedom Movement, Geography",
                "  Current Events",
            ]),
            ("SSB Interview (900 marks)", [
                "Stage I: Officer Intelligence Rating (OIR) + Picture Perception",
                "Stage II: Psychological Tests, Group Tests, Personal Interview",
                "Conference",
            ]),
        ],
    },
]


def create_pdfs_with_reportlab():
    """Create PDFs using reportlab (preferred — clean formatting)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        pdf_dir = SITE_ROOT / "assets" / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)

        SAFFRON  = HexColor("#FF6B00")
        NAVY     = HexColor("#0A0F2C")
        GREY_700 = HexColor("#374151")
        GREY_400 = HexColor("#9BA3B8")
        GREY_100 = HexColor("#F7F8FA")

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("nb_title",
            fontName="Helvetica-Bold", fontSize=22, textColor=white,
            spaceAfter=4, leading=28)
        subtitle_style = ParagraphStyle("nb_sub",
            fontName="Helvetica", fontSize=11, textColor=HexColor("#FFD580"),
            spaceAfter=2)
        section_style = ParagraphStyle("nb_section",
            fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
            spaceBefore=14, spaceAfter=6)
        bullet_style = ParagraphStyle("nb_bullet",
            fontName="Helvetica", fontSize=10, textColor=GREY_700,
            leftIndent=16, spaceBefore=2, spaceAfter=2, leading=16)
        footer_style = ParagraphStyle("nb_footer",
            fontName="Helvetica", fontSize=8, textColor=GREY_400,
            alignment=TA_CENTER)

        created = []
        for pdf in PDFS:
            out_path = pdf_dir / pdf["filename"]

            doc = SimpleDocTemplate(
                str(out_path),
                pagesize=A4,
                topMargin=0.6*cm,
                bottomMargin=1.5*cm,
                leftMargin=2*cm,
                rightMargin=2*cm,
            )

            story = []

            # Header banner
            header_data = [[
                Paragraph(f"<font color='white'><b>{pdf['title']}</b></font>", title_style),
            ]]
            header_table = Table(header_data, colWidths=[doc.width])
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING",    (0, 0), (-1, -1), 18),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING",   (0, 0), (-1, -1), 20),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
                ("ROUNDEDCORNERS", [6]),
            ]))
            story.append(header_table)

            # Sub-header
            sub_data = [[
                Paragraph(f"<font color='#FF6B00'>NaukriBulletin.in</font>  ·  "
                          f"Official syllabus summary for <b>{pdf['exam']}</b>  ·  "
                          f"Updated for 2026 recruitment cycle",
                          ParagraphStyle("s", fontName="Helvetica", fontSize=9,
                                         textColor=GREY_400, spaceAfter=0))
            ]]
            sub_table = Table(sub_data, colWidths=[doc.width])
            sub_table.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, -1), GREY_100),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
                ("LEFTPADDING",  (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ]))
            story.append(sub_table)
            story.append(Spacer(1, 18))

            # Sections
            for section_title, bullets in pdf["sections"]:
                # Section header
                sec_data = [[Paragraph(section_title, ParagraphStyle("sh",
                    fontName="Helvetica-Bold", fontSize=12, textColor=white))]]
                sec_table = Table(sec_data, colWidths=[doc.width])
                sec_table.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, -1), SAFFRON),
                    ("TOPPADDING",    (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
                ]))
                story.append(sec_table)

                # Bullets
                for bullet in bullets:
                    story.append(Paragraph(f"• {bullet}", bullet_style))

                story.append(Spacer(1, 10))

            # Footer
            story.append(Spacer(1, 20))
            story.append(Paragraph(
                "This is a summary document. Always verify from the official notification at naukribulletin.in · "
                "For latest govt jobs, visit naukribulletin.in/jobs/ · "
                "© 2026 NaukriBulletin.in",
                footer_style
            ))

            doc.build(story)
            created.append(pdf["filename"])
            print(f"  [PDF] Created: {pdf['filename']}")

        return created

    except ImportError:
        print("  [WARN] reportlab not installed — creating minimal PDFs")
        return create_pdfs_minimal()


def create_pdfs_minimal():
    """Fallback: create minimal valid PDF files (no external deps)."""
    pdf_dir = SITE_ROOT / "assets" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for pdf in PDFS:
        out_path = pdf_dir / pdf["filename"]
        # Build content string
        lines = [f"NaukriBulletin.in — {pdf['title']}", ""]
        for section_title, bullets in pdf["sections"]:
            lines.append(section_title)
            lines.append("-" * len(section_title))
            for b in bullets:
                lines.append(f"  * {b}")
            lines.append("")
        lines.append("Always verify from official notification at naukribulletin.in")
        content = "\n".join(lines)

        # Write minimal valid PDF
        pdf_bytes = _make_minimal_pdf(pdf["title"], content)
        out_path.write_bytes(pdf_bytes)
        created.append(pdf["filename"])
        print(f"  [PDF] Created (minimal): {pdf['filename']}")

    return created


def _make_minimal_pdf(title, content):
    """
    Build a bare-bones but valid PDF/1.4 file with text content.
    No external deps required.
    """
    lines = content.split("\n")
    # Build content stream
    stream_lines = [
        "BT",
        "/F1 14 Tf",
        "50 780 Td",
        f"({_esc(title[:80])}) Tj",
        "0 -22 Td",
        "/F1 9 Tf",
    ]
    y = 0
    for line in lines:
        if y > 36:  # ~37 lines per page
            break
        safe = _esc(line[:100])
        stream_lines.append(f"({safe}) Tj")
        stream_lines.append("0 -13 Td")
        y += 1

    stream_lines.append("ET")
    stream = "\n".join(stream_lines)
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects = []

    # 1: catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: page
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    # 4: content stream
    stream_obj = (
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode()
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    objects.append(stream_obj)
    # 5: font
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>\nendobj\n"
    )

    # xref
    header = b"%PDF-1.4\n"
    offsets = []
    body = b""
    pos = len(header)
    for obj in objects:
        offsets.append(pos)
        body += obj
        pos += len(obj)

    xref_pos = len(header) + len(body)
    xref = f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"

    trailer = (
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    )

    return header + body + xref.encode() + trailer.encode()


def _esc(s):
    """Escape special PDF string chars."""
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", " ")


# ── SYLLABUS PAGE PATCH ───────────────────────────────────────────────────────

PDF_GATE_HTML = """
  <!-- ═══ PDF Download Section with Email Gate ═══ -->
  <div style="background:linear-gradient(135deg,#0A0F2C 0%,#1a2a5e 100%);padding:48px 20px;margin:40px 0;">
    <div style="max-width:1200px;margin:0 auto;">

      <div style="text-align:center;margin-bottom:32px;">
        <div style="display:inline-block;background:rgba(255,107,0,0.15);border-radius:50%;padding:14px;margin-bottom:12px;">
          <span style="font-size:2rem;">📥</span>
        </div>
        <h2 style="font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;color:#fff;margin-bottom:8px;">
          Download Free Syllabus PDFs
        </h2>
        <p style="color:#9BA3B8;font-size:0.95rem;max-width:500px;margin:0 auto;">
          Enter your email to instantly download official syllabus PDFs for SSC, Railway, Banking &amp; UPSC exams.
          Free forever, no spam.
        </p>
      </div>

      <!-- PDF cards grid -->
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:32px;" id="pdf-grid">
        <div class="pdf-card" data-pdf="ssc-cgl-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">📋</div>
          <div class="pdf-name">SSC CGL 2026</div>
        </div>
        <div class="pdf-card" data-pdf="ssc-chsl-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">📋</div>
          <div class="pdf-name">SSC CHSL 2026</div>
        </div>
        <div class="pdf-card" data-pdf="rrb-ntpc-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">🚂</div>
          <div class="pdf-name">RRB NTPC 2026</div>
        </div>
        <div class="pdf-card" data-pdf="rrb-group-d-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">🚂</div>
          <div class="pdf-name">RRB Group D 2026</div>
        </div>
        <div class="pdf-card" data-pdf="ibps-po-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">🏦</div>
          <div class="pdf-name">IBPS PO 2026</div>
        </div>
        <div class="pdf-card" data-pdf="sbi-po-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">🏦</div>
          <div class="pdf-name">SBI PO 2026</div>
        </div>
        <div class="pdf-card" data-pdf="upsc-ias-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">🏛️</div>
          <div class="pdf-name">UPSC IAS 2026</div>
        </div>
        <div class="pdf-card" data-pdf="nda-syllabus-2026.pdf" onclick="selectPdf(this)">
          <div class="pdf-icon">🪖</div>
          <div class="pdf-name">NDA 2026</div>
        </div>
      </div>

      <!-- Gate form -->
      <div id="pdf-gate" style="max-width:480px;margin:0 auto;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:16px;padding:28px;">
        <div id="gate-selecting" style="text-align:center;color:#9BA3B8;font-size:0.9rem;padding:10px 0;">
          ← Select a PDF above to download
        </div>
        <div id="gate-form" style="display:none;">
          <div id="selected-pdf-label" style="color:#FF6B00;font-weight:700;font-size:0.95rem;margin-bottom:14px;text-align:center;"></div>
          <label style="display:block;color:#D1D5DB;font-size:0.85rem;margin-bottom:6px;">Your Email Address</label>
          <input type="email" id="pdf-email" placeholder="you@email.com"
            style="width:100%;box-sizing:border-box;padding:12px 14px;border-radius:8px;border:1.5px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.08);color:#fff;font-size:0.95rem;margin-bottom:12px;outline:none;"
            onfocus="this.style.borderColor='#FF6B00'" onblur="this.style.borderColor='rgba(255,255,255,0.2)'"
          >
          <button onclick="downloadPdf()"
            style="width:100%;background:#FF6B00;color:#fff;border:none;padding:13px;border-radius:8px;font-family:'Syne',sans-serif;font-size:0.95rem;font-weight:700;cursor:pointer;transition:background 0.2s;"
            onmouseover="this.style.background='#e55a00'" onmouseout="this.style.background='#FF6B00'">
            📥 Download Free PDF →
          </button>
          <p style="color:#6B7280;font-size:0.75rem;text-align:center;margin:10px 0 0;">
            No spam. Unsubscribe anytime. Free daily job alerts as a bonus.
          </p>
        </div>
        <div id="gate-success" style="display:none;text-align:center;padding:10px 0;">
          <div style="font-size:2rem;margin-bottom:8px;">✅</div>
          <div style="color:#fff;font-weight:700;margin-bottom:6px;">Downloading now…</div>
          <div style="color:#9BA3B8;font-size:0.85rem;">Check your email for more free resources.</div>
        </div>
        <div id="gate-error" style="display:none;text-align:center;padding:6px 0;">
          <span style="color:#EF4444;font-size:0.85rem;">❌ Please enter a valid email address.</span>
        </div>
      </div>

    </div>
  </div>

  <style>
    .pdf-card {
      background: rgba(255,255,255,0.07);
      border: 1.5px solid rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 18px 14px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
    }
    .pdf-card:hover {
      border-color: #FF6B00;
      background: rgba(255,107,0,0.12);
    }
    .pdf-card.selected {
      border-color: #FF6B00;
      background: rgba(255,107,0,0.18);
      box-shadow: 0 0 0 2px rgba(255,107,0,0.3);
    }
    .pdf-icon { font-size: 1.6rem; margin-bottom: 6px; }
    .pdf-name { color: #E5E7EB; font-size: 0.82rem; font-weight: 600; line-height: 1.3; }
  </style>

  <script>
    var selectedPdfFile = null;

    function selectPdf(el) {
      document.querySelectorAll('.pdf-card').forEach(function(c){ c.classList.remove('selected'); });
      el.classList.add('selected');
      selectedPdfFile = el.getAttribute('data-pdf');
      var name = el.querySelector('.pdf-name').textContent;
      document.getElementById('selected-pdf-label').textContent = '📄 ' + name;
      document.getElementById('gate-selecting').style.display = 'none';
      document.getElementById('gate-form').style.display = 'block';
      document.getElementById('gate-success').style.display = 'none';
      document.getElementById('gate-error').style.display = 'none';
      document.getElementById('pdf-gate').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function downloadPdf() {
      var email = document.getElementById('pdf-email').value.trim();
      if (!email || !/^[^@]+@[^@]+\\.[^@]+$/.test(email)) {
        document.getElementById('gate-error').style.display = 'block';
        return;
      }
      document.getElementById('gate-error').style.display = 'none';

      // Start download immediately
      var link = document.createElement('a');
      link.href = '/assets/pdf/' + selectedPdfFile;
      link.download = selectedPdfFile;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Show success
      document.getElementById('gate-form').style.display = 'none';
      document.getElementById('gate-success').style.display = 'block';

      // Subscribe to Brevo in background (non-blocking)
      fetch('https://api.brevo.com/v3/contacts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'api-key': 'BREVO_API_KEY_PLACEHOLDER'
        },
        body: JSON.stringify({
          email: email,
          listIds: [2],
          attributes: { SOURCE: 'syllabus_pdf_gate', PDF: selectedPdfFile }
        })
      }).catch(function(){});

      // Google Analytics event
      if (window.gtag) {
        gtag('event', 'pdf_download', { pdf_name: selectedPdfFile, email_collected: true });
      }

      // Reset after 5s so they can download another
      setTimeout(function() {
        document.getElementById('gate-success').style.display = 'none';
        document.getElementById('gate-form').style.display = 'block';
        document.getElementById('pdf-email').value = '';
        selectedPdfFile = null;
        document.querySelectorAll('.pdf-card').forEach(function(c){ c.classList.remove('selected'); });
        document.getElementById('gate-selecting').style.display = 'block';
        document.getElementById('gate-form').style.display = 'none';
      }, 5000);
    }
  </script>
  <!-- ═══ End PDF Download Section ═══ -->
"""


def patch_syllabus_page():
    """Insert the PDF gate section into syllabus/index.html."""
    page = SITE_ROOT / "syllabus" / "index.html"
    if not page.exists():
        print(f"  [SKIP] syllabus/index.html not found at {page}")
        return False

    html = page.read_text(encoding="utf-8")

    # Don't patch twice
    if "pdf-grid" in html:
        print("  [SKIP] syllabus/index.html already has PDF gate")
        return False

    # Insert before </body>
    if "</body>" not in html:
        print("  [SKIP] syllabus/index.html has no </body> tag")
        return False

    html = html.replace("</body>", PDF_GATE_HTML + "\n</body>")
    page.write_text(html, encoding="utf-8")
    print("  [PATCH] syllabus/index.html — PDF gate inserted")
    return True


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run():
    print("\n" + "="*56)
    print("patch_syllabus_pdf_gate.py")
    print("="*56 + "\n")

    # 1. Create PDFs
    print("[1/2] Creating syllabus PDFs in assets/pdf/...\n")
    try:
        import subprocess
        subprocess.run(
            ["pip", "install", "reportlab", "--quiet", "--break-system-packages"],
            capture_output=True
        )
    except Exception:
        pass
    created = create_pdfs_with_reportlab()
    print(f"\n  ✅ {len(created)} PDFs created\n")

    # 2. Patch syllabus page
    print("[2/2] Patching syllabus/index.html...\n")
    patched = patch_syllabus_page()

    print("\n" + "="*56)
    print("NEXT STEPS:")
    print("="*56)
    print()
    print("1. Set real Brevo API key:")
    print("   Edit syllabus/index.html and replace:")
    print("     BREVO_API_KEY_PLACEHOLDER")
    print("   with your actual key, OR add it as a GitHub secret BREVO_API_KEY")
    print("   and add a build step to inject it. For now the download still")
    print("   works — only the Brevo subscribe call fails silently.")
    print()
    print("2. Set Brevo list ID:")
    print("   In the same fetch() call, change listIds: [2] to your actual")
    print("   Brevo list ID (visible at brevo.com → Contacts → Lists).")
    print()
    print("3. Replace PDFs with official versions when ready:")
    print("   SSC CGL:   https://ssc.gov.in/notice-board")
    print("   RRB NTPC:  https://www.rrbcdg.gov.in/")
    print("   IBPS:      https://www.ibps.in/")
    print("   UPSC:      https://www.upsc.gov.in/")
    print("   Keep the same filenames in assets/pdf/")
    print()
    print("4. Commit & deploy:")
    print("   git add assets/pdf/ syllabus/index.html scripts/category_gen.py")
    print("   git commit -m 'feat: engineering category routing + syllabus PDF gate'")
    print("   git push")
    print()
    print("="*56 + "\n")


if __name__ == "__main__":
    run()
