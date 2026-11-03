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
BANNER = "_pdf_banner.jpg"   # a ~4 cm icon: 800 px is plenty (the full PNG was 2.3 MB of the PDF)
_im = PILImage.open("_deliver/b_hero.png").convert("RGB")
_arr = np.array(_im).astype(int)
_bg_row = _arr[:, 20, :]
_mask = np.abs(_arr - _bg_row[:, None, :]).sum(axis=2) > 20
_ys, _xs = np.where(_mask)
_x0, _x1, _y0, _y1 = _xs.min(), _xs.max(), _ys.min(), _ys.max()
_cx, _cy = (_x0 + _x1) / 2, (_y0 + _y1) / 2
_half = max(_x1 - _x0, _y1 - _y0) / 2 * 1.10
_box = (int(_cx - _half), int(_cy - _half), int(_cx + _half), int(_cy + _half))
_ban = _im.crop(_box)
_ban.thumbnail((800, 800))
_ban.save(BANNER, quality=88)

src = open("MANTA_Description_DRAFT.md", encoding="utf-8").read()
styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=20, spaceAfter=3, spaceBefore=0)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=3.5,
                    textColor=TEAL_DK)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=10.5, leading=14.6,
                      alignment=TA_JUSTIFY, spaceAfter=3.0, textColor=INK)
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=16, firstLineIndent=-10, spaceAfter=1.6)
LIST = ParagraphStyle("LIST", parent=BODY, leftIndent=0, spaceAfter=2.4)
STAT_BIG = ParagraphStyle("STAT_BIG", fontName="Helvetica-Bold", fontSize=17,
                          textColor=TEAL_DK, alignment=TA_CENTER, leading=19)
STAT_LBL = ParagraphStyle("STAT_LBL", fontName="Helvetica", fontSize=6.6,
                          textColor=SUB, alignment=TA_CENTER, leading=8)

def md_inline(t):
    t = re.sub(r"\*\*(.+?)\*\*", r'<b><font color="#084a52">\1</font></b>', t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    return t

_HDEPTH = ["#1f9aa3", "#13808e", "#0d6a7c", "#0b5468", "#0a3f58"]
_hcount = [0]


def section_header(title):
    """no bullet mark: the heading itself sinks one shade deeper each time"""
    col = _HDEPTH[min(_hcount[0], len(_HDEPTH) - 1)]
    _hcount[0] += 1
    return Paragraph(f'<font color="{col}">{title.upper()}</font>', H2)

def stat_strip():
    stats = [("~250 kg", "safe static load"), ("26×", "glued full-section joint"),
             ("~16.5 kg", "finished weight"), ("~110 €", "filament + epoxy")]
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
        for b in bullets:                 # clean lines, no bullet marks: the bold name leads
            story.append(Paragraph(md_inline(b), LIST))
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
        if line[3:].strip().lower() in ("stability and load", "engineering that checks itself", "the algorithm — print only the chair you need", "strength and stability"):
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

import math
import random

DEEP_RGB = (10 / 255, 34 / 255, 58 / 255)
FOOT_H = 44 * mm


def _vgrad(c, x, y0, w, h, top, bot, n=120):
    """vertical gradient from colour `top` (at y0 + h) to `bot` (at y0)"""
    for i in range(n):
        u = i / (n - 1)
        col = [t + (b - t) * u for t, b in zip(top, bot)]
        c.setFillColorRGB(*col)
        c.rect(x, y0 + h - (i + 1) * h / n, w, h / n + 0.4, fill=1, stroke=0)


def _manta(c, cx, cy, w, ang, rgb):
    pts = []
    for k in range(21):
        t = k / 20.0
        pts.append((0.08 * w + 0.42 * w * t, 0.24 * w - 0.24 * w * t ** 0.6))
    for k in range(21):
        t = k / 20.0
        pts.append((0.5 * w - 0.38 * w * t, -0.02 * w - 0.18 * w * t ** 1.4))
    body = [(0.12 * w, -0.2 * w), (0.06 * w, -0.24 * w), (-0.06 * w, -0.24 * w), (-0.12 * w, -0.2 * w)]
    left = [(-x, y) for x, y in reversed(pts)]
    head = [(-0.06 * w, 0.3 * w), (-0.03 * w, 0.24 * w), (0.03 * w, 0.24 * w), (0.06 * w, 0.3 * w)]
    poly = pts + body + left + head
    ca, sa = math.cos(ang), math.sin(ang)
    P = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in poly]
    c.setFillColorRGB(*rgb)
    p = c.beginPath()
    p.moveTo(*P[0])
    for q in P[1:]:
        p.lineTo(*q)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setStrokeColorRGB(*rgb); c.setLineWidth(max(0.6, w / 120))
    c.line(cx + 0.24 * w * sa, cy - 0.24 * w * ca, cx + 0.62 * w * sa, cy - 0.62 * w * ca)


def draw_band(c, doc):
    pw, ph = A4
    c.saveState()
    # the water below the waterline, deepening down the page
    _vgrad(c, 0, FOOT_H, pw, ph - BAND_H - FOOT_H, (0.93, 0.98, 0.98), (0.80, 0.92, 0.93))
    # air and the sunlit surface, with oxygen rising
    _vgrad(c, 0, ph - BAND_H, pw, BAND_H, (0.97, 0.995, 0.995), (0.80, 0.93, 0.94), 60)
    rnd = random.Random(4)
    c.setStrokeColorRGB(0.45, 0.72, 0.76)
    for _ in range(26):
        x = rnd.uniform(146 * mm, 166 * mm) if rnd.random() < 0.7 else rnd.uniform(4 * mm, 16 * mm)
        y = rnd.uniform(ph - BAND_H + 4 * mm, ph - 3 * mm)
        r = rnd.uniform(0.5, 2.2) * mm * (0.5 + 0.5 * (ph - y) / BAND_H)
        c.setLineWidth(0.5)
        c.circle(x, y, r, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 8); c.setFillColorRGB(0.30, 0.58, 0.63)
    c.drawString(160 * mm, ph - 9 * mm, "O")
    c.setFont("Helvetica-Bold", 5.5); c.drawString(163.2 * mm, ph - 10.2 * mm, "2")
    # the waterline, with our plastic floating on it
    wy = ph - BAND_H
    c.setStrokeColorRGB(0.06, 0.40, 0.48); c.setLineWidth(1.1)
    p = c.beginPath(); p.moveTo(0, wy)
    for k in range(0, 211, 3):
        p.lineTo(k * mm, wy + 0.9 * mm * math.sin(k / 9.0))
    c.drawPath(p, stroke=1, fill=0)
    # the same recognisable plastic as on the board: bottles, bags, six-pack
    # rings, straws, cups, a scrap of net, caps -- and microplastics below
    def _poly(X, Y, pts, a=0.0, k=1.0):
        ca, sa = math.cos(a), math.sin(a)
        q = c.beginPath()
        for n, (px, py) in enumerate(pts):
            x_, y_ = X + k * (px * ca - py * sa) * mm, Y + k * (px * sa + py * ca) * mm
            q.moveTo(x_, y_) if n == 0 else q.lineTo(x_, y_)
        q.close(); c.drawPath(q, fill=1, stroke=0)

    def bottle(X, Y, a=0.0, cap=(0.84, 0.25, 0.20)):
        c.setFillColorRGB(0.59, 0.77, 0.84)
        _poly(X, Y, [(-4.4, -1.1), (2.1, -1.1), (3.1, -0.6), (4.4, -0.6), (4.4, 0.6), (3.1, 0.6), (2.1, 1.1), (-4.4, 1.1)], a)
        c.setFillColorRGB(0.93, 0.94, 0.95)
        _poly(X, Y, [(-2.5, -1.1), (0.3, -1.1), (0.3, 1.1), (-2.5, 1.1)], a)
        c.setFillColorRGB(*cap)
        _poly(X, Y, [(4.4, -0.75), (5.2, -0.75), (5.2, 0.75), (4.4, 0.75)], a)

    def bag(X, Y):
        c.setFillColorRGB(0.74, 0.81, 0.85)
        _poly(X, Y, [(-3.2, -0.4), (-2.1, 1.5), (-0.4, 0.7), (0.8, 2.1), (2.4, 0.6), (3.6, -0.3), (1.4, -1.0), (-1.4, -1.1)])
        c.setStrokeColorRGB(0.74, 0.81, 0.85); c.setLineWidth(0.9)
        c.arc(X - 2.1 * mm, Y + 0.6 * mm, X - 0.3 * mm, Y + 3.2 * mm, 0, 180)

    def rings(X, Y):
        c.setStrokeColorRGB(0.80, 0.70, 0.42); c.setLineWidth(0.9)
        for i_ in range(3):
            for j_ in range(2):
                cx_, cy_ = X + (i_ - 1) * 2.1 * mm, Y + (j_ - 0.5) * 1.5 * mm
                c.ellipse(cx_ - 1.05 * mm, cy_ - 0.7 * mm, cx_ + 1.05 * mm, cy_ + 0.7 * mm, stroke=1, fill=0)

    def straw(X, Y, a=0.0):
        ca, sa = math.cos(a), math.sin(a)
        c.setStrokeColorRGB(0.93, 0.36, 0.49); c.setLineWidth(1.3); c.setLineCap(1)
        pts = [(-4.2, 0), (2.1, 0), (3.6, 1.3)]
        q = c.beginPath()
        for n, (px, py) in enumerate(pts):
            x_, y_ = X + (px * ca - py * sa) * mm, Y + (px * sa + py * ca) * mm
            q.moveTo(x_, y_) if n == 0 else q.lineTo(x_, y_)
        c.drawPath(q, stroke=1, fill=0)

    def cup(X, Y, a=0.0):
        c.setFillColorRGB(0.96, 0.96, 0.94)
        _poly(X, Y, [(-2.1, 1.5), (2.1, 1.1), (2.1, -1.1), (-2.1, -1.5)], a)
        c.setFillColorRGB(0.24, 0.59, 0.78)
        _poly(X, Y, [(2.1, 1.4), (2.7, 1.4), (2.7, -1.4), (2.1, -1.4)], a)

    def capf(X, Y, rgb=(0.77, 0.55, 0.44)):
        c.setFillColorRGB(*rgb)
        c.ellipse(X - 1.1 * mm, Y - 0.75 * mm, X + 1.1 * mm, Y + 0.75 * mm, stroke=0, fill=1)

    def net(X, Y, w=10.0, h=3.0):
        c.setStrokeColorRGB(0.38, 0.63, 0.52); c.setLineWidth(0.5)
        t = -w / 2
        while t <= w / 2:
            c.line(X + (t - 1) * mm, Y - h / 2 * mm, X + (t + 1) * mm, Y + h / 2 * mm)
            c.line(X + (t + 1) * mm, Y - h / 2 * mm, X + (t - 1) * mm, Y + h / 2 * mm)
            t += 1.3

    def wl(x):
        return wy + 0.9 * mm * math.sin(x / 9.0) + 0.35 * mm

    # microplastics first, so the floating things sit on top of them
    rm = random.Random(7)
    mcols = [(0.84, 0.47, 0.38), (0.59, 0.77, 0.84), (0.90, 0.90, 0.84), (0.93, 0.36, 0.49), (0.38, 0.63, 0.52)]
    for _ in range(170):
        x = rm.uniform(3, 207)
        d = 5.5 * rm.random() ** 1.7
        r = rm.uniform(0.18, 0.45) * (1 - d / 7.5)
        c.setFillColorRGB(*rm.choice(mcols))
        c.circle(x * mm, wl(x) - 0.6 * mm - d * mm, r * mm, stroke=0, fill=1)
    bottle(14 * mm, wl(14), 0.08); capf(23 * mm, wl(23)); rings(31 * mm, wl(31)); bag(42 * mm, wl(42))
    straw(54 * mm, wl(54), 0.05); bottle(66 * mm, wl(66), -0.12, (0.16, 0.47, 0.78)); cup(78 * mm, wl(78), 0.3)
    net(90 * mm, wl(90)); capf(100 * mm, wl(100), (0.24, 0.59, 0.78)); bottle(110 * mm, wl(110), 0.15)
    bag(122 * mm, wl(122)); rings(133 * mm, wl(133)); straw(144 * mm, wl(144), -0.1); cup(154 * mm, wl(154), -0.25)
    capf(163 * mm, wl(163), (0.84, 0.25, 0.20)); bottle(173 * mm, wl(173), -0.08); net(186 * mm, wl(186), 8)
    bag(198 * mm, wl(198)); capf(206 * mm, wl(206))
    # a porthole onto the chair
    R = (BAND_H - 12 * mm) / 2
    pcx, pcy = pw - 16 * mm - R, ph - BAND_H / 2 + 1 * mm
    c.saveState()
    cp = c.beginPath(); cp.circle(pcx, pcy, R)
    c.clipPath(cp, stroke=0, fill=0)
    c.drawImage(BANNER, pcx - R * 1.08, pcy - R * 1.08, 2.16 * R, 2.16 * R,
                preserveAspectRatio=True, mask=None)
    c.restoreState()
    c.setStrokeColorRGB(0.06, 0.40, 0.48); c.setLineWidth(1.6)
    c.circle(pcx, pcy, R, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 27)
    c.setFillColorRGB(*DEEP_RGB)
    c.drawString(20 * mm, ph - 18.5 * mm, "MANTA")
    c.setFont("Helvetica-Oblique", 8.3)
    c.setFillColor(colors.HexColor("#0d6a7c"))
    sub1 = "The ocean makes the oxygen we breathe, and we fill it with plastic."
    sub2 = "MANTA is a wave from that ocean, made by an algorithm so you print only what you need."
    c.drawString(20 * mm, ph - 26 * mm, sub1)
    c.drawString(20 * mm, ph - 31.5 * mm, sub2)
    c.restoreState()

def draw_footer(c, doc):
    pw, ph = A4
    c.saveState()
    _vgrad(c, 0, 0, pw, FOOT_H, (0.80, 0.92, 0.93), DEEP_RGB, 60)
    _manta(c, 44 * mm, 20 * mm, 34 * mm, 0.25, (0.20, 0.42, 0.52))
    _manta(c, 95 * mm, 12 * mm, 18 * mm, -0.2, (0.15, 0.34, 0.45))
    _manta(c, 138 * mm, 26 * mm, 13 * mm, 0.4, (0.26, 0.50, 0.60))
    _manta(c, 172 * mm, 18 * mm, 9 * mm, -0.35, (0.22, 0.44, 0.55))
    c.setFont("Helvetica-Bold", 7.6)
    c.setFillColorRGB(0.82, 0.93, 0.94)
    c.drawRightString(pw - 14 * mm, 6 * mm, "Anonymised source: anonymous.4open.science/r/manta-chair-23D4")
    c.restoreState()

def on_first_page(c, doc):
    draw_band(c, doc); draw_footer(c, doc)

doc = SimpleDocTemplate("TEAMID_Description.pdf", pagesize=A4,
                        leftMargin=20 * mm, rightMargin=20 * mm,
                        topMargin=TOPMARGIN, bottomMargin=FOOT_H + 3 * mm,
                        title="Chair Description", author="")
doc.build(story, onFirstPage=on_first_page, onLaterPages=draw_footer)

# word count
body = re.sub(r"^#.*$", "", src, flags=re.M)
body = re.sub(r"[#*_>-]", " ", body)
print("PDF ok - body words:", len([w for w in body.split() if any(c.isalnum() for c in w)]))
