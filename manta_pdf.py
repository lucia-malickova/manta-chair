# -*- coding: utf-8 -*-
"""MANTA_Description_DRAFT.md -> TEAMID_Description.pdf  (<=500 words, A4)."""
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

src = open("MANTA_Description_DRAFT.md", encoding="utf-8").read()
styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=20, spaceAfter=3, spaceBefore=0)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceBefore=8, spaceAfter=2,
                    textColor="#333333")
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=9.1, leading=11.8,
                      alignment=TA_JUSTIFY, spaceAfter=3)
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=16, firstLineIndent=-10, spaceAfter=1)

def md_inline(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    return t

story, bullets = [], []
def flush_bullets():
    global bullets
    if bullets:
        story.append(ListFlowable([ListItem(Paragraph(md_inline(b), BUL), leftIndent=8,
                                            value="–", bulletColor="#888")
                                   for b in bullets], bulletType="bullet", start="–"))
        bullets = []

for raw in src.splitlines():
    line = raw.rstrip()
    if not line:
        flush_bullets(); continue
    if line.startswith("# "):
        flush_bullets(); story.append(Paragraph(md_inline(line[2:]), H1))
    elif line.startswith("## "):
        flush_bullets(); story.append(Paragraph(md_inline(line[3:]), H2))
    elif line.startswith("- "):
        bullets.append(line[2:])
    else:
        flush_bullets(); story.append(Paragraph(md_inline(line), BODY))
flush_bullets()

doc = SimpleDocTemplate("TEAMID_Description.pdf", pagesize=A4,
                        leftMargin=20*mm, rightMargin=20*mm, topMargin=16*mm, bottomMargin=16*mm,
                        title="Chair Description", author="")
doc.build(story)

# word count
body = re.sub(r"^#.*$", "", src, flags=re.M)
body = re.sub(r"[#*_>-]", " ", body)
print("PDF ok - body words:", len([w for w in body.split() if any(c.isalnum() for c in w)]))
