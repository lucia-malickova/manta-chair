# -*- coding: utf-8 -*-
"""MANTA — A2 BOARD landscape (7016x4962). Composited onto the official
template (_board_base.png = 'Board Template Without Instructions', already
carries the 49-slot grid)."""
import os, math
from PIL import Image, ImageDraw, ImageFont

W, H = 7016, 4962
D = "_deliver"
OUTF = "TEAMID_Board.jpg"
INK, SUB, HAIR = (26, 28, 32), (108, 112, 120), (200, 203, 208)

def F(sz, b=False):
    p = r"C:\Windows\Fonts\arialbd.ttf" if b else r"C:\Windows\Fonts\arial.ttf"
    try: return ImageFont.truetype(p, sz)
    except Exception: return ImageFont.load_default()

board = (Image.open("_board_base.png").convert("RGB").resize((W, H))
         if os.path.exists("_board_base.png") else Image.new("RGB", (W, H), "white"))
dr = ImageDraw.Draw(board)

# the template's 49-slot grid stays whole (unused slots 43-49 = empty, allowed).

def img(name, box, contain=True):
    x0, y0, x1, y1 = box
    p = f"{D}/{name}"
    if not os.path.exists(p):
        dr.rectangle(box, outline=HAIR, width=3)
        dr.text(((x0+x1)//2, (y0+y1)//2), name, font=F(38), fill=HAIR, anchor="mm"); return
    im = Image.open(p).convert("RGB")
    bw, bh = x1-x0, y1-y0
    s = (min if contain else max)(bw/im.width, bh/im.height)
    im = im.resize((max(1, int(im.width*s)), max(1, int(im.height*s))))
    if not contain:
        im = im.crop(((im.width-bw)//2, (im.height-bh)//2,
                      (im.width-bw)//2+bw, (im.height-bh)//2+bh))
        board.paste(im, (x0, y0))
    else:
        board.paste(im, (x0 + (bw-im.width)//2, y0 + (bh-im.height)//2))

def wrap(xy, s, font, fill=INK, maxw=900, sp=9, anchor="la"):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if dr.textlength((cur+" "+w).strip(), font=font) <= maxw: cur = (cur+" "+w).strip()
        else: lines.append(cur); cur = w
    lines.append(cur)
    dr.multiline_text(xy, "\n".join(lines), font=font, fill=fill, spacing=sp, anchor=anchor)

M = 150
# ============ HEADER ============
dr.text((M, 120), "MANTA", font=F(146, True), fill=INK)
wrap((M, 292), "One continuous ribbon, sliced crosswise so it prints on a home bed and still holds an adult.",
     F(44), SUB, maxw=4200)
dr.line((M, 392, W-M, 392), fill=HAIR, width=3)

# ============ VISUALISATION (top) ============
dr.text((M, 432), "VISUALISATION", font=F(34, True), fill=SUB)
img("b_hero.png", (M, 470, 2980, 2520))
img("b_side.png", (3010, 486, 3820, 2170))
img("b_back.png", (3830, 486, 4720, 2170))
img("b_top.png",  (3060, 2110, 4360, 2500))
img("b_parts.png", (4300, 1700, 5900, 2500))
dr.text((4300, 2500), ".STL PARTS ARRANGEMENT  —  numbers 1-42 in reading order", font=F(24, True), fill=SUB)

# biomimicry / concept callouts (top right)
cx = 6180
dr.text((cx, 470), "BIOMIMICRY — STRUCTURAL, NOT APPLIED", font=F(27, True), fill=SUB)
bio = [
 ("Wolff", "section thickness = the bending-moment diagram: 90 mm at the lumbar knot, 26 mm blade at the crown"),
 ("Murray", "the lumbar is the one 3-way node; section ~ cube-root-sum, all transitions filleted"),
 ("Spiral fibre", "longitudinal flutes follow the stress path + stiffen by corrugation; section twists up to 20 deg"),
 ("Shell", "closed superelliptical section + dished seat carry load in membrane action"),
 ("Fiddlehead", "the curled crown closes the backrest into a tube, not a cantilever"),
 ("Buttress root", "each foot forks into two splayed prongs — wide base, few contacts, little material"),
]
y = 528
for k, v in bio:
    dr.text((cx, y), k, font=F(26, True), fill=INK)
    wrap((cx, y+34), v, F(22), SUB, maxw=680, sp=5)
    y += 158

wrap((6180, 1560), "One gesture: fork-foot -> dished seat -> cantilevered backrest -> curled crown -> "
     "tail-brace to the floor behind.  Seat 430 x 430 mm, 455 mm high, 3 deg rear tilt, convex "
     "lumbar.  Overall 820 d x 700 w x 1030 h mm.", F(26), SUB, maxw=760, sp=6)

dr.line((M, 2540, W-M, 2540), fill=HAIR, width=3)

# ============ ASSEMBLY GUIDE ============  (template's 49-key grid: x~118..708 y~2008..2570)
dr.text((820, 2585), "ASSEMBLY GUIDE", font=F(34, True), fill=SUB)
img("b_exploded.png", (150, 2690, 3050, 4760))
wrap((170, 4770), "Exploded — 42 printed segments, no two alike. The ribbon is one solid form; it is only cut to fit the bed.",
     F(28), SUB, maxw=2800)

steps = [
 ("1", "Lay out by zone", "Parts 1-42 in reading order form six zones: fore-foot fork, front leg, seat, lumbar, backrest, tail-foot fork."),
 ("2", "Crosswise joints", "Every cut is a full solid cross-section. Seat the printed conical tenon (dia 32); two-part epoxy over the whole face. No screws."),
 ("3", "Left + right halves", "Wide segments come in L+R halves. Join along the centre-line with the transverse tenon (dia 24) + epoxy; the seam is the keel."),
 ("4", "Lumbar pins", "Only the two joints beside the lumbar: drive the dia 10 printed pin (x2) through the joint before the epoxy sets."),
 ("5", "Sub-assemble, cure", "Build seat, backrest and each fork-foot separately. Cure 24 h. Then join at the lumbar and the two knees."),
 ("6", "Stand & load", "Set on a flat floor, weight the seat, leave 24 h. Tipping 0.56 sideways; safe static load ~166 kg."),
]
sx = 3230
for i, (n, t, b) in enumerate(steps):
    yy = 2700 + i*350
    dr.ellipse((sx, yy, sx+66, yy+66), outline=INK, width=4)
    dr.text((sx+33, yy+33), n, font=F(34, True), fill=INK, anchor="mm")
    dr.text((sx+104, yy-2), t, font=F(37, True), fill=INK)
    wrap((sx+104, yy+54), b, F(28), SUB, maxw=1640, sp=7)

dr.line((5170, 2560, 5170, 4770), fill=HAIR, width=3)

# ============ 3D PRINTING (right) ============
dr.text((5250, 2585), "3D PRINTING", font=F(34, True), fill=SUB)
rows = [
 ("PARTS", "41 segments + 1 pin type (x4)  -  limit 49"),
 ("PART SIZE", "each <= 212 x 220 x 250 mm"),
 ("SUPPORTS", "none — every gram becomes chair, none scrapped as support waste"),
 ("MATERIAL", "PETG"),
 ("LAYER / NOZZLE", "0.20 mm  /  0.4 mm"),
 ("WALLS", "5 perimeters"),
 ("INFILL", "35 % gyroid  (kept low — the ribbon's own bulk carries the load)"),
 ("ADHESIVE", "two-part epoxy (structural)"),
 ("PIN", "dia 10 printed rod, x4, at the 2 lumbar joints"),
 ("EST. WEIGHT", "~16 kg  -  ~90 EUR in budget filament"),
 ("BATCH TIME", "~160-200 h"),
]
y = 2680
for k, v in rows:
    dr.text((5250, y), k, font=F(26, True), fill=SUB)
    wrap((5250, y+38), v, F(31), INK, maxw=1560, sp=5)
    y += 176

wrap((5250, 4590), "Nothing in nature repeats itself, so no two parts of this chair do either: "
     "every one of the 42 segments is geometrically unique. This mass is a choice, not a default — "
     "solid, Wolff-graded material, because thin printed shells don't glue into strong joints. One "
     "parametric script — change the width, thickness or infill tables and it regenerates a leaner, "
     "cheaper variant with the same joints, so no one has to own the same chair.  Shared CC BY-NC-SA.",
     F(25), SUB, maxw=1560)

board.convert("RGB").save(OUTF, "JPEG", quality=86)
print(f"{OUTF}  {board.size}  {os.path.getsize(OUTF)/1e6:.2f} MB")
