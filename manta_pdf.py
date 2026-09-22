# -*- coding: utf-8 -*-
"""MANTA_Description_DRAFT.md -> TEAMID_Description.pdf  (<=500 words, A4).

Styled to match the Board: navy hero band with the chair render, teal
section markers, teal-tinted stat strip for the headline numbers."""
import re
import numpy as np
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, ListFlowable,
                                ListItem, Table, TableStyle)

NAVY = colors.HexColor("#0a1620")
TEAL = colors.HexColor("#0a828a")
TEAL_DK = colors.HexColor("#084a52")
TEAL_TINT = colors.HexColor("#dff1f1")
SUB = colors.HexColor("#6b7280")
INK = colors.HexColor("#1a1a1a")

BAND_H = 44 * mm
TOPMARGIN = BAND_H + 7 * mm

# ---- crop a square icon of the hero chair render (keeps its navy bg, so it
# drops into the header band with no masking needed). The background is a
# vertical gradient, not flat, so detect the chair by diffing each pixel
# against its own row's background sample instead of a fixed colour. ----
BANNER = "_pdf_banner.png"
_im = PILImage.open("_deliver/b_hero.png").convert("RGB")
_arr = np.array(_im).astype(int)
_bg_row = _arr[:, 20, :]
_mask = np.abs(_arr - _bg_row[:, None, :]).sum(axis=2) > 20
_ys, _xs = np.where(_mask)
_x0, _x1, _y0, _y1 = _xs.min(), _xs.max(), _ys.min(), _ys.max()
_cx, _cy = (_x0 + _x1) / 2, (_y0 + _y1) / 2
_half = max(_x1 - _x0, _y1 - _y0) / 2 * 1.10
_box = (int(_cx - _half), int(_cy - _half), int(_cx + _half), int(_cy + _half))
_im.crop(_box).save(BANNER)

src = open("MANTA_Description_DRAFT.md", encoding="utf-8").read()
styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=20, spaceAfter=3, spaceBefore=0)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11.4, spaceBefore=9, spaceAfter=3.4,
                    textColor=TEAL_DK)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=9.3, leading=12.4,
                      alignment=TA_JUSTIFY, spaceAfter=3.4, textColor=INK)
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=16, firstLineIndent=-10, spaceAfter=1.6)
STAT_BIG = ParagraphStyle("STAT_BIG", fontName="Helvetica-Bold", fontSize=17,
                          textColor=TEAL_DK, alignment=TA_CENTER, leading=19)
STAT_LBL = ParagraphStyle("STAT_LBL", fontName="Helvetica", fontSize=6.6,
                          textColor=SUB, alignment=TA_CENTER, leading=8)

def md_inline(t):
    t = re.sub(r"\*\*(.+?)\*\*", r'<b><font color="#084a52">\1</font></b>', t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    return t

def section_header(title):
    return Paragraph(f'<font color="#0a828a">■</font>&nbsp;&nbsp;{title.upper()}', H2)

def stat_strip():
    stats = [("166 kg", "safe static load"), ("15×", "joint margin, epoxied"),
             ("~16 kg", "finished weight"), ("~90 €", "filament cost")]
    cells = [[Paragraph(big, STAT_BIG)] for big, _ in stats]
    lbls = [[Paragraph(lbl, STAT_LBL)] for _, lbl in stats]
    t = Table([[c[0] for c in cells], [l[0] for l in lbls]], colWidths=[42.5 * mm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_TINT),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t

story, bullets, para_lines = [], [], []
def flush_bullets():
    global bullets
    if bullets:
        story.append(ListFlowable([ListItem(Paragraph(md_inline(b), BUL), leftIndent=8,
                                            value="–", bulletColor="#0a828a")
                                   for b in bullets], bulletType="bullet", start="–"))
        bullets = []
def flush_para():
    global para_lines
    if para_lines:
        story.append(Paragraph(md_inline(" ".join(para_lines)), BODY))
        para_lines = []

pending_stats = False
skip_next_bold = False
last_block = None  # tracks whether we're mid-paragraph or mid-bullet, so
                   # soft-wrapped source lines rejoin instead of becoming
                   # their own tiny left-aligned paragraphs
for raw in src.splitlines():
    line = raw.rstrip()
    if not line:
        flush_para(); flush_bullets(); last_block = None
        continue
    if line.startswith("# "):
        # title + its lede line are already shown in the navy header band
        flush_para(); flush_bullets(); skip_next_bold = True; last_block = None
        continue
    if skip_next_bold and re.fullmatch(r"\*\*.+\*\*", line):
        skip_next_bold = False
        continue
    if line.startswith("## "):
        flush_para(); flush_bullets()
        if pending_stats:
            story.append(Spacer(1, 4)); story.append(stat_strip()); story.append(Spacer(1, 5))
            pending_stats = False
        story.append(section_header(line[3:]))
        if line[3:].strip().lower() == "stability and load":
            pending_stats = True
        last_block = None
        continue
    if line.startswith("- "):
        flush_para()
        bullets.append(line[2:])
        last_block = "bullet"
        continue
    if last_block == "bullet" and raw.startswith(" ") and bullets:
        bullets[-1] += " " + line.strip()
    else:
        para_lines.append(line.strip())
        last_block = "para"
flush_para(); flush_bullets()
if pending_stats:
    story.append(Spacer(1, 3)); story.append(stat_strip())

def draw_band(c, doc):
    pw, ph = A4
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, ph - BAND_H, pw, BAND_H, fill=1, stroke=0)
    icon = BAND_H - 10 * mm
    c.drawImage(BANNER, pw - 16 * mm - icon, ph - BAND_H + 5 * mm, icon, icon,
               preserveAspectRatio=True, mask=None)
    c.setFillColor(TEAL)
    c.rect(20 * mm, ph - 19 * mm, 2.6 * mm, 9 * mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 27)
    c.setFillColor(colors.white)
    c.drawString(25 * mm, ph - 18.5 * mm, "MANTA")
    c.setFont("Helvetica-Oblique", 8.3)
    c.setFillColor(colors.HexColor("#a9d3d3"))
    sub1 = "One continuous ribbon. One gesture."
    sub2 = "Cut like a baguette so it can be printed at home and still hold an adult."
    c.drawString(25 * mm, ph - 26 * mm, sub1)
    c.drawString(25 * mm, ph - 31.5 * mm, sub2)
    c.restoreState()

def draw_footer(c, doc):
    pw, ph = A4
    c.saveState()
    c.setStrokeColor(TEAL); c.setLineWidth(1)
    c.line(20 * mm, 13.5 * mm, pw - 20 * mm, 13.5 * mm)
    c.setFont("Helvetica", 7.3)
    c.setFillColor(SUB)
    c.drawString(20 * mm, 9.5 * mm, "MANTA — Open Chair 2026, chair description")
    c.setFont("Helvetica-Bold", 7.6)
    c.setFillColor(TEAL_DK)
    c.drawRightString(pw - 20 * mm, 9.5 * mm, "Full source released under CC BY-NC-SA")
    c.restoreState()

def on_first_page(c, doc):
    draw_band(c, doc); draw_footer(c, doc)

doc = SimpleDocTemplate("TEAMID_Description.pdf", pagesize=A4,
                        leftMargin=20 * mm, rightMargin=20 * mm,
                        topMargin=TOPMARGIN, bottomMargin=15 * mm,
                        title="Chair Description", author="")
doc.build(story, onFirstPage=on_first_page, onLaterPages=draw_footer)

# word count
body = re.sub(r"^#.*$", "", src, flags=re.M)
body = re.sub(r"[#*_>-]", " ", body)
print("PDF ok - body words:", len([w for w in body.split() if any(c.isalnum() for c in w)]))
