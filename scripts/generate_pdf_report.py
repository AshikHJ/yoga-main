"""
KI.AI Complete Technical Documentation PDF Generator.
Combines all 7 architectural documentation files into an executive-grade,
professionally styled PDF report with Table of Contents, visual Asana gallery,
flowcharts, and stamped page numbers.
"""

import base64
import html
import os
import re
import sys
from typing import Dict, List, Tuple

import mistune
from PySide6.QtCore import QPointF, QRectF, QSizeF
from PySide6.QtGui import QColor, QFont, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QApplication

import Quartz
from Foundation import NSURL
from AppKit import (
    NSFont,
    NSColor,
    NSString,
    NSGraphicsContext,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
TEMP_PDF = os.path.join(BASE_DIR, "KI_AI_Report_Intermediate.pdf")
OUTPUT_PDF = os.path.join(BASE_DIR, "KI_AI_Complete_Project_Report.pdf")


def get_image_b64(rel_path: str) -> str:
    """Reads local image and returns data URL string."""
    full_path = os.path.join(BASE_DIR, rel_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            ext = rel_path.split(".")[-1].lower()
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""


def clean_markdown_for_html(md_text: str) -> str:
    """Cleans LaTeX math formulas and special annotations into clean HTML entities."""
    # Replace block math
    md_text = re.sub(
        r"\$\$(.*?)\$\$",
        r'<div class="math-block"><i>\1</i></div>',
        md_text,
        flags=re.DOTALL,
    )
    # Replace inline math
    md_text = re.sub(r"\$([^\$\n]+)\$", r"<i>\1</i>", md_text)
    # Clean common LaTeX keywords
    md_text = md_text.replace(r"\arccos", "arccos")
    md_text = md_text.replace(r"\operatorname{clip}", "clip")
    md_text = md_text.replace(r"\operatorname{atan2}", "atan2")
    md_text = md_text.replace(r"\Delta", "&Delta;")
    md_text = md_text.replace(r"\theta", "&theta;")
    md_text = md_text.replace(r"\ge", "&ge;")
    md_text = md_text.replace(r"\le", "&le;")
    md_text = md_text.replace(r"\vec{u}", "<b>u&#773;</b>")
    md_text = md_text.replace(r"\vec{v}", "<b>v&#773;</b>")
    md_text = md_text.replace(r"\longleftrightarrow", " &longleftrightarrow; ")
    md_text = md_text.replace(r"\rightarrow", " &rarr; ")
    md_text = md_text.replace(r"\times", " &times; ")
    md_text = md_text.replace(r"\in", " &isin; ")
    md_text = md_text.replace(r"\|\vec{u}\|", "|<b>u</b>|")
    md_text = md_text.replace(r"\|\vec{v}\|", "|<b>v</b>|")
    return md_text


def parse_mermaid_to_html(md_text: str) -> str:
    """Converts Mermaid code blocks into styled HTML sequence cards."""
    def replace_mermaid(match):
        code = match.group(1).strip()
        lines = [line.strip() for line in code.split("\n") if line.strip()]
        steps = []
        for line in lines:
            if any(line.startswith(k) for k in ["autonumber", "sequenceDiagram", "actor", "participant", "loop", "opt", "end"]):
                continue
            if "->>" in line or "-->>" in line:
                parts = re.split(r"-+>>", line)
                if len(parts) == 2:
                    src = parts[0].strip()
                    rest = parts[1].strip()
                    if ":" in rest:
                        target, desc = rest.split(":", 1)
                        steps.append((src, target.strip(), desc.strip()))
                    else:
                        steps.append((src, rest, ""))

        if not steps:
            return f'<pre class="code-block"><code>{html.escape(code)}</code></pre>'

        html_flow = '<div class="flow-card">'
        html_flow += '<div class="flow-header">System Data Flow & Interaction Sequence</div>'
        html_flow += '<div class="flow-steps">'
        for idx, (src, tgt, desc) in enumerate(steps, 1):
            html_flow += f'''
            <div class="flow-step">
                <span class="step-num">{idx}</span>
                <span class="step-actors"><b>{html.escape(src)}</b> &rarr; <b>{html.escape(tgt)}</b>:</span>
                <span class="step-desc">{html.escape(desc)}</span>
            </div>'''
        html_flow += '</div></div>'
        return html_flow

    return re.sub(r"```mermaid\n(.*?)```", replace_mermaid, md_text, flags=re.DOTALL)


def build_asana_gallery_html() -> str:
    """Builds a responsive visual grid of real Asana photographs and figures."""
    poses = [
        ("Tadasana", "Mountain Pose", "assets/images/yoga/tadasana.png", "assets/pose_figures/tadasana.svg", "Beginner", "Standing", "Knees: 180°, Spine: 90° (Vertical)"),
        ("Vrikshasana", "Tree Pose", "assets/images/vrikshasana.png", "assets/pose_figures/vrikshasana.svg", "Beginner", "Balance", "Standing Knee: 180°, Bent Knee: 45°"),
        ("Virabhadrasana II", "Warrior II", "assets/images/yoga/virabhadrasana_ii.png", "assets/pose_figures/virabhadrasana_ii.svg", "Intermediate", "Standing", "Front Knee: 90°, Back Knee: 180°, Arms: 180°"),
        ("Trikonasana", "Triangle Pose", "assets/images/yoga/trikonasana.png", "assets/pose_figures/trikonasana.svg", "Intermediate", "Standing", "Both Knees: 180°, Torso Lateral: 45°"),
        ("Utkatasana", "Chair Pose", "assets/images/yoga/utkatasana.png", "assets/pose_figures/utkatasana.svg", "Beginner", "Standing", "Knees: 100°, Hips: 95°, Spine: 60°"),
        ("Adho Mukha Svanasana", "Downward Dog", "assets/images/yoga/adho_mukha_svanasana.png", "assets/pose_figures/adho_mukha_svanasana.svg", "Beginner", "Inversion", "Knees: 180°, Hips: 70°, Shoulders: 180°"),
        ("Bhujangasana", "Cobra Pose", "assets/images/yoga/bhujangasana.png", "assets/pose_figures/bhujangasana.svg", "Beginner", "Backbend", "Elbows: 150°, Spine: 135°"),
        ("Setu Bandhasana", "Bridge Pose", "assets/images/yoga/setu_bandhasana.png", "assets/pose_figures/setu_bandhasana.svg", "Beginner", "Backbend", "Knees: 90°, Hip Extension: 160°"),
        ("Dhanurasana", "Bow Pose", "assets/images/yoga/dhanurasana.png", "assets/pose_figures/dhanurasana.svg", "Advanced", "Backbend", "Knees: 70°, Shoulders: 60°"),
        ("Natarajasana", "Dancer Pose", "assets/images/yoga/natarajasana.png", "assets/pose_figures/natarajasana.svg", "Advanced", "Balance", "Standing Knee: 180°, Lifted: 60°, Torso: 65°"),
        ("Balasana", "Child's Pose", "assets/images/yoga/balasana.png", "assets/pose_figures/balasana.svg", "Beginner", "Restorative", "Knees: 40°, Hips: 30°, Spine Rested"),
        ("Sukhasana", "Easy Pose", "assets/images/yoga/sukhasana.png", "assets/pose_figures/sukhasana.svg", "Beginner", "Seated", "Knees: 45°, Spine Upright: 90°"),
    ]

    out = '<div class="gallery-container">'
    out += '<h3>Real-World Asana Biomechanical Reference Catalog</h3>'
    out += '<p>The following postures form the core seed library of KI.AI with codified angular tolerance rules:</p>'
    out += '<table class="gallery-table">'
    out += '<thead><tr><th>Live Pose</th><th>Anatomical Figure</th><th>Asana Name</th><th>Level & Category</th><th>Biomechanical Targets</th></tr></thead>'
    out += '<tbody>'

    for name, en_name, img_path, fig_path, diff, cat, rules in poses:
        img_b64 = get_image_b64(img_path)
        fig_b64 = get_image_b64(fig_path)

        img_tag = f'<img src="{img_b64}" width="70" height="70" style="border-radius: 6px; object-fit: cover;" />' if img_b64 else '<span>[Image]</span>'
        fig_tag = f'<img src="{fig_b64}" width="70" height="70" style="border-radius: 6px; object-fit: contain; background: #fff;" />' if fig_b64 else '<span>[Figure]</span>'

        out += f'''
        <tr>
            <td style="text-align: center; vertical-align: middle; padding: 6px;">{img_tag}</td>
            <td style="text-align: center; vertical-align: middle; padding: 6px;">{fig_tag}</td>
            <td><b>{name}</b><br><small style="color: #7A726D;">{en_name}</small></td>
            <td><span class="badge badge-sage">{diff}</span><br><small>{cat}</small></td>
            <td><small>{rules}</small></td>
        </tr>
        '''

    out += '</tbody></table></div>'
    return out


def build_surya_gallery_html() -> str:
    """Builds the 12-Step Surya Namaskar Vector Flow gallery."""
    steps = [
        ("1", "Pranamasana", "Prayer Pose", "assets/pose_figures/pranamasana.svg", "Normal / Exhale", "Spine 90° vertical, hands in Anjali Mudra"),
        ("2", "Hasta Uttanasana", "Raised Arms", "assets/pose_figures/hasta_uttanasana.svg", "Inhale", "Arms extended overhead 165°, slight backbend"),
        ("3", "Uttanasana", "Forward Fold", "assets/pose_figures/uttanasana.svg", "Exhale", "Hip flexion 50°, straight knees 180°"),
        ("4", "Ashwa Sanchalanasana (R)", "Equestrian (Right)", "assets/pose_figures/ashwa_sanchalanasana_r.svg", "Inhale", "Front knee 90°, back leg extended"),
        ("5", "Dandasana", "Plank Pose", "assets/pose_figures/dandasana.svg", "Retain", "Torso & spine rigid 180° straight plane"),
        ("6", "Ashtanga Namaskara", "Eight Limbs Salute", "assets/pose_figures/ashtanga_namaskara.svg", "Exhale", "8-point floor contact: toes, knees, chest, hands, chin"),
        ("7", "Bhujangasana", "Cobra Pose", "assets/pose_figures/bhujangasana.svg", "Inhale", "Chest lifted, elbows soft, lumbar extension"),
        ("8", "Parvatasana", "Downward Dog / Mountain", "assets/pose_figures/parvatasana.svg", "Exhale", "Inverted V-shape, hips elevated, heels grounded"),
        ("9", "Ashwa Sanchalanasana (L)", "Equestrian (Left)", "assets/pose_figures/ashwa_sanchalanasana_l.svg", "Inhale", "Left leg forward 90° knee, gaze elevated"),
        ("10", "Uttanasana", "Forward Fold", "assets/pose_figures/uttanasana.svg", "Exhale", "Deep standing forward bend, hands to floor"),
        ("11", "Hasta Uttanasana", "Raised Arms", "assets/pose_figures/hasta_uttanasana.svg", "Inhale", "Full extension arching backwards overhead"),
        ("12", "Pranamasana", "Prayer / Relax", "assets/pose_figures/pranamasana.svg", "Exhale", "Neutral standing prayer alignment"),
    ]

    out = '<div class="gallery-container" style="page-break-before: always;">'
    out += '<h3>12-Step Surya Namaskar (Sun Salutation) Kinetic Flow</h3>'
    out += '<p>Codified step-by-step sequential cycle with synchronized breathing phases:</p>'
    out += '<table class="gallery-table">'
    out += '<thead><tr><th>Step</th><th>Vector Figure</th><th>Asana Name</th><th>Breathing Phase</th><th>Biomechanical Cue</th></tr></thead>'
    out += '<tbody>'

    for step_num, name, en_name, fig_path, breath, cue in steps:
        fig_b64 = get_image_b64(fig_path)
        fig_tag = f'<img src="{fig_b64}" width="60" height="60" style="border-radius: 4px; object-fit: contain; background: #fff;" />' if fig_b64 else '<span>[Figure]</span>'

        out += f'''
        <tr>
            <td style="text-align: center; font-weight: bold; font-size: 13px; color: #C85A32;">{step_num}</td>
            <td style="text-align: center; vertical-align: middle; padding: 4px;">{fig_tag}</td>
            <td><b>{name}</b><br><small style="color: #7A726D;">{en_name}</small></td>
            <td><span class="badge badge-terracotta">{breath}</span></td>
            <td><small>{cue}</small></td>
        </tr>
        '''

    out += '</tbody></table></div>'
    return out


def generate_full_html() -> str:
    """Loads all documentation files and compiles them into a unified publication HTML."""
    logo_b64 = get_image_b64("assets/logo.png")
    hero_b64 = get_image_b64("assets/images/yoga_hero_modern.png")

    md = mistune.create_markdown(plugins=["table", "strikethrough"])

    doc_files = [
        "KI_AI_PROJECT_OVERVIEW.md",
        "KI_AI_FRONTEND_GUIDE.md",
        "KI_AI_BACKEND_AND_API_GUIDE.md",
        "KI_AI_POSE_DETECTION_PIPELINE.md",
        "KI_AI_DATABASE_AND_DATA_FLOW.md",
        "KI_AI_FUNCTION_INVENTORY.md",
        "KI_AI_TESTING_AND_STATUS.md",
    ]

    combined_body = ""

    for filename in doc_files:
        filepath = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        filtered_lines = []
        for line in lines:
            if line.startswith("# KI.AI —") and len(filtered_lines) == 0:
                continue
            if line.startswith("## Document Metadata"):
                continue
            if line.startswith("- **Project Name:") or line.startswith("- **Document Version:") or line.startswith("- **Target Repository:") or line.startswith("- **Scope:"):
                continue
            filtered_lines.append(line)

        cleaned_md = "\n".join(filtered_lines)
        cleaned_md = clean_markdown_for_html(cleaned_md)
        cleaned_md = parse_mermaid_to_html(cleaned_md)

        section_html = md(cleaned_md)

        if "KI_AI_DATABASE_AND_DATA_FLOW.md" in filename:
            gallery_markup = build_asana_gallery_html()
            surya_markup = build_surya_gallery_html()
            if "SECTION 10" in section_html:
                parts = section_html.split("SECTION 10", 1)
                section_html = parts[0] + gallery_markup + surya_markup + '<div style="page-break-after: always;"></div>' + "<h2>SECTION 10" + parts[1]
            else:
                section_html += gallery_markup + surya_markup

        combined_body += f'\n<div class="doc-section">{section_html}</div>\n<div style="page-break-after: always;"></div>\n'

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
/* Warm Editorial Design Stylesheet */
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #2E2927;
    background-color: #FAF8F5;
    margin: 0;
    padding: 0;
}}

h1, h2, h3, h4 {{
    font-family: Georgia, "Playfair Display", serif;
    color: #1A1615;
    font-weight: 700;
    margin-top: 1.3em;
    margin-bottom: 0.4em;
}}

h1 {{
    font-size: 20pt;
    border-bottom: 2px solid #C85A32;
    padding-bottom: 4px;
    margin-top: 0;
}}

h2 {{
    font-size: 14pt;
    border-bottom: 1px solid #EDE5DC;
    padding-bottom: 3px;
    color: #C85A32;
}}

h3 {{
    font-size: 12pt;
    color: #1A1615;
}}

h4 {{
    font-size: 10.5pt;
    color: #5B7065;
}}

p {{
    margin-top: 0;
    margin-bottom: 0.7em;
}}

b, strong {{
    color: #1A1615;
}}

/* Cover Page */
.cover-page {{
    text-align: center;
    padding-top: 40px;
    padding-bottom: 40px;
}}

.cover-logo {{
    margin-bottom: 20px;
}}

.cover-title {{
    font-family: Georgia, serif;
    font-size: 24pt;
    font-weight: bold;
    color: #1A1615;
    line-height: 1.2;
    margin-bottom: 8px;
}}

.cover-subtitle {{
    font-size: 12.5pt;
    color: #C85A32;
    font-weight: 600;
    margin-bottom: 25px;
    letter-spacing: 0.5px;
}}

.cover-card {{
    background-color: #F4EFEB;
    border: 1px solid #EDE5DC;
    border-radius: 8px;
    padding: 16px 22px;
    margin: 25px auto;
    text-align: left;
    max-width: 560px;
    font-size: 9.5pt;
    line-height: 1.55;
}}

.cover-meta {{
    margin-top: 30px;
    font-size: 9pt;
    color: #7A726D;
    line-height: 1.55;
}}

/* Table of Contents */
.toc-container {{
    background-color: #F4EFEB;
    border: 1px solid #EDE5DC;
    border-radius: 8px;
    padding: 18px;
    margin: 18px 0;
}}

.toc-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
}}

.toc-table td {{
    padding: 5px 8px;
    border-bottom: 1px dotted #D8CFC4;
}}

.toc-num {{
    font-weight: bold;
    color: #C85A32;
    width: 85px;
}}

.toc-title {{
    font-weight: 600;
    color: #1A1615;
}}

/* Content Elements & Tables */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9pt;
}}

th, td {{
    padding: 6px 8px;
    border: 1px solid #EDE5DC;
    text-align: left;
}}

th {{
    background-color: #EDE5DC;
    color: #1A1615;
    font-weight: bold;
    font-size: 9pt;
}}

tr:nth-child(even) td {{
    background-color: #F9F6F2;
}}

/* Code Blocks */
pre, code {{
    font-family: Menlo, Monaco, "Courier New", monospace;
    font-size: 8.5pt;
}}

code {{
    background-color: #EDE5DC;
    color: #1A1615;
    padding: 2px 4px;
    border-radius: 3px;
}}

pre {{
    background-color: #F4EFEB;
    border-left: 3px solid #C85A32;
    padding: 8px 12px;
    overflow-x: auto;
    margin: 10px 0;
    border-radius: 0 4px 4px 0;
}}

pre code {{
    background: none;
    padding: 0;
    color: #1A1615;
}}

/* Flowcards */
.flow-card {{
    background-color: #F4EFEB;
    border: 1px solid #EDE5DC;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 12px 0;
}}

.flow-header {{
    font-weight: bold;
    color: #C85A32;
    font-size: 9.5pt;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.flow-step {{
    padding: 3px 0;
    font-size: 9pt;
    border-bottom: 1px solid #EDE5DC;
}}

.flow-step:last-child {{
    border-bottom: none;
}}

.step-num {{
    display: inline-block;
    width: 18px;
    height: 18px;
    background-color: #C85A32;
    color: #fff;
    border-radius: 50%;
    text-align: center;
    line-height: 18px;
    font-size: 7.5pt;
    font-weight: bold;
    margin-right: 6px;
}}

/* Badges */
.badge {{
    display: inline-block;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 7.5pt;
    font-weight: bold;
    text-transform: uppercase;
}}

.badge-terracotta {{
    background-color: #F5E5DF;
    color: #C85A32;
}}

.badge-sage {{
    background-color: #E6EBE8;
    color: #5B7065;
}}

/* Galleries */
.gallery-container {{
    margin: 16px 0;
}}

.gallery-table td {{
    vertical-align: middle;
}}
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover-page">
    {'<div class="cover-logo"><img src="' + logo_b64 + '" height="55" /></div>' if logo_b64 else ''}
    <div class="cover-title">KI.AI &mdash; AI-Powered Yoga &amp; Posture Intelligence</div>
    <div class="cover-subtitle">Complete Production Architecture &amp; Technical Report</div>
    
    <div class="cover-card">
        <b>Executive Overview:</b><br>
        This document constitutes the comprehensive technical and operational report for <b>KI.AI</b>.
        It details the markerless 3D computer vision pipeline, 2D/3D kinematic vector calculations,
        real-time state machines, prioritized speech queue engine, 38 REST API routes, 12 SQLite tables,
        commercial Razorpay payment verification, and 81 automated tests.
        <br><br>
        <b>Target Repository:</b> <code>/Users/ashik/Downloads/yoga-main</code><br>
        <b>Software Version:</b> 1.0.0 (Production Release)<br>
        <b>Verification Status:</b> 81/81 Pytest Automated Tests Passing (100%)
    </div>

    {'<div style="margin: 16px 0;"><img src="' + hero_b64 + '" width="420" style="border-radius: 8px;" /></div>' if hero_b64 else ''}

    <div class="cover-meta">
        <b>Author:</b> Lead Product Engineer &amp; Technical Architecture Specialist<br>
        <b>Technology Stack:</b> Python 3.9+, MediaPipe Pose, OpenCV, Flask, SQLite3, PySide6, Razorpay SDK<br>
        <b>Date:</b> October 2026 &bull; Antigravity Production Release
    </div>
</div>

<div style="page-break-after: always;"></div>

<!-- TABLE OF CONTENTS -->
<h1>Table of Contents</h1>
<div class="toc-container">
    <table class="toc-table">
        <tbody>
            <tr><td class="toc-num">Section 1</td><td class="toc-title">Project Overview, Mission &amp; Core Problems Solved</td></tr>
            <tr><td class="toc-num">Section 2</td><td class="toc-title">Complete Repository Directory Structure &amp; File Responsibility</td></tr>
            <tr><td class="toc-num">Section 3</td><td class="toc-title">Frontend Architecture, Warm Editorial Design &amp; View Catalog</td></tr>
            <tr><td class="toc-num">Section 4</td><td class="toc-title">Backend Architecture &amp; Flask REST API Guide (38 Endpoints)</td></tr>
            <tr><td class="toc-num">Section 5</td><td class="toc-title">Pose Detection, Vector Angle Calculation &amp; Scoring Pipeline</td></tr>
            <tr><td class="toc-num">Section 6</td><td class="toc-title">AI Voice Coach, Priority Queue &amp; Conversational System</td></tr>
            <tr><td class="toc-num">Section 7</td><td class="toc-title">Session Planner Engine &amp; Guided Learning System</td></tr>
            <tr><td class="toc-num">Section 8</td><td class="toc-title">Database Structure, Relational Schema &amp; Indexes (12 Tables)</td></tr>
            <tr><td class="toc-num">Section 9</td><td class="toc-title">Supported Asana Catalog, Visual Gallery &amp; Surya Namaskar Flow</td></tr>
            <tr><td class="toc-num">Section 10</td><td class="toc-title">Authentication, User Profiles &amp; Commercial SaaS Payments</td></tr>
            <tr><td class="toc-num">Section 11</td><td class="toc-title">Progress Telemetry, Joint Heatmaps &amp; Analytics</td></tr>
            <tr><td class="toc-num">Section 12</td><td class="toc-title">Automated Testing Inventory (81 Tests), Status Matrix &amp; Limits</td></tr>
            <tr><td class="toc-num">Section 13</td><td class="toc-title">End-to-End System Data Flow &amp; Sequence Diagrams</td></tr>
            <tr><td class="toc-num">Section 14</td><td class="toc-title">Master Function and Class Inventory</td></tr>
        </tbody>
    </table>
</div>

<div style="page-break-after: always;"></div>

{combined_body}

</body>
</html>
"""
    return full_html


def render_pdf_report():
    """Generates intermediate PDF via Qt and stamps headers/footers via Quartz."""
    print("1. Compiling HTML report content...")
    report_html = generate_full_html()

    print("2. Initializing Qt Application...")
    app = QApplication.instance() or QApplication(sys.argv)
    doc = QTextDocument()
    doc.setHtml(report_html)

    print("3. Generating intermediate PDF with QPrinter...")
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(TEMP_PDF)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    doc.print_(printer)

    print("4. Stamping running headers, divider lines, and page numbers with Quartz...")
    in_url = NSURL.fileURLWithPath_(TEMP_PDF)
    out_url = NSURL.fileURLWithPath_(OUTPUT_PDF)

    in_doc = Quartz.PDFDocument.alloc().initWithURL_(in_url)
    total_pages = in_doc.pageCount()

    page0 = in_doc.pageAtIndex_(0)
    media_box = page0.boundsForBox_(Quartz.kPDFDisplayBoxMediaBox)

    pdf_ctx = Quartz.CGPDFContextCreateWithURL(out_url, media_box, None)

    font = NSFont.fontWithName_size_("Helvetica", 8)
    color_gray = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.48, 0.45, 0.43, 1.0)
    color_line = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.85, 0.82, 0.78, 1.0)
    attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: color_gray}

    for i in range(total_pages):
        page = in_doc.pageAtIndex_(i)
        page_box = page.boundsForBox_(Quartz.kPDFDisplayBoxMediaBox)
        Quartz.CGPDFContextBeginPage(pdf_ctx, None)

        # Draw original page content
        page.drawWithBox_toContext_(Quartz.kPDFDisplayBoxMediaBox, pdf_ctx)

        # Stamp headers and footers on page 2 through N (skip cover page)
        if i > 0:
            NSGraphicsContext.saveGraphicsState()
            ns_ctx = NSGraphicsContext.graphicsContextWithCGContext_flipped_(pdf_ctx, False)
            NSGraphicsContext.setCurrentContext_(ns_ctx)

            pw = page_box.size.width
            ph = page_box.size.height

            # Header text & divider
            header = NSString.stringWithString_(
                "KI.AI — AI-Powered Yoga & Posture Intelligence | Complete Technical Report"
            )
            header.drawAtPoint_withAttributes_(Quartz.CGPoint(40, ph - 28), attrs)

            color_line.setStroke()
            path = Quartz.CGPathCreateMutable()
            Quartz.CGPathMoveToPoint(path, None, 40, ph - 33)
            Quartz.CGPathAddLineToPoint(path, None, pw - 40, ph - 33)
            Quartz.CGContextAddPath(pdf_ctx, path)
            Quartz.CGContextSetLineWidth(pdf_ctx, 0.5)
            Quartz.CGContextStrokePath(pdf_ctx)

            # Footer text & divider
            path_foot = Quartz.CGPathCreateMutable()
            Quartz.CGPathMoveToPoint(path_foot, None, 40, 32)
            Quartz.CGPathAddLineToPoint(path_foot, None, pw - 40, 32)
            Quartz.CGContextAddPath(pdf_ctx, path_foot)
            Quartz.CGContextSetLineWidth(pdf_ctx, 0.5)
            Quartz.CGContextStrokePath(pdf_ctx)

            conf_note = NSString.stringWithString_(
                "CONFIDENTIAL & PROPRIETARY — PRODUCTION RELEASE AUDIT"
            )
            conf_note.drawAtPoint_withAttributes_(Quartz.CGPoint(40, 18), attrs)

            page_num_str = NSString.stringWithString_(f"Page {i + 1} of {total_pages}")
            page_num_str.drawAtPoint_withAttributes_(Quartz.CGPoint(pw - 110, 18), attrs)

            NSGraphicsContext.restoreGraphicsState()

        Quartz.CGPDFContextEndPage(pdf_ctx)

    Quartz.CGPDFContextClose(pdf_ctx)

    # Clean temporary intermediate PDF
    if os.path.exists(TEMP_PDF):
        os.remove(TEMP_PDF)

    print(f"5. Successfully generated final stamped PDF ({total_pages} pages): {OUTPUT_PDF}")


if __name__ == "__main__":
    render_pdf_report()
