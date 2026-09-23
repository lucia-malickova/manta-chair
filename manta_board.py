# -*- coding: utf-8 -*-
"""MANTA — A2 BOARD landscape (7016x4962). Composited onto the official
template (_board_base.png = 'Board Template Without Instructions', already
carries the 49-slot grid)."""
import os, re, math
from PIL import Image, ImageDraw, ImageFont
import manta_ribbon as st

W, H = 7016, 4962
D = "_deliver"
OUTF = "TEAMID_Board.jpg"
INK, SUB, HAIR = (26, 28, 32), (108, 112, 120), (200, 203, 208)
TEAL, TEAL_DK, TEAL_TINT = (10, 128, 138), (8, 74, 82), (223, 241, 241)

# part number (1-42, board key order) -> assembly-zone colour, same zones
# and colours as the exploded view, so the key grid and the diagram agree
_CUTS = st.cut_stations()
def _part_names():
    names = []
    with open(f"{D.replace('_deliver','MANTA_RIBBON')}/PARTS_LIST.txt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line[0].isdigit() or "." not in line.split()[0]:
                continue
            names.append(line.split(".", 1)[1].split()[0])
    return names
ZONE_RGB = [tuple(int(round(c * 255)) for c in col) for col in st.ZONE_COLORS]
_PART_ZONE = {}
for _i, _nm in enumerate(_part_names(), start=1):
    if _nm == "PIN":
        continue
    _k = int(re.match(r"SEG_(\d+)", _nm).group(1))
    _smid = 0.5 * (_CUTS[_k] + _CUTS[_k + 1])
    _PART_ZONE[_i] = st.zone_of(_smid)

def F(sz, b=False):
    p = r"C:\Windows\Fonts\arialbd.ttf" if b else r"C:\Windows\Fonts\arial.ttf"
    try: return ImageFont.truetype(p, sz)
    except Exception: return ImageFont.load_default()

board = (Image.open("_board_base.png").convert("RGB").resize((W, H))
         if os.path.exists("_board_base.png") else Image.new("RGB", (W, H), "white"))
dr = ImageDraw.Draw(board)

# The template's key grid sits at a spot that collides with the hero render
# in this layout — the brief explicitly allows relocating it ("You can
# adjust the location of this key as necessary"), so cut the whole grid +
# ".STL parts arrangement" caption block out of the untouched template and
# move it to the clear space under the biomimicry column instead. Cover the
# old spot with white first so nothing of it peeks out from under the hero.
GRID_SRC_BOX = (40, 1950, 780, 2750)     # grid + caption, as provided
GRID_DX, GRID_DY = 6080, -250            # where it moves to
grid_block = board.crop(GRID_SRC_BOX)
dr.rectangle(GRID_SRC_BOX, fill=(255, 255, 255))
board.paste(grid_block, (GRID_SRC_BOX[0] + GRID_DX, GRID_SRC_BOX[1] + GRID_DY))

# the template's 49-slot grid stays whole (unused slots 43-49 = empty, allowed) —
# each of the 42 used boxes gets a small picture of that actual part (like a
# real furniture-assembly manual), with the box's own printed number redrawn
# on top in a corner so it stays legible regardless of what's under it.
# exact cell boundaries measured on _board_base.png (columns/rows are NOT
# perfectly uniform, so use the real gap positions rather than an average),
# then shifted by the same relocation offset as the grid block above.
COL_B = [x + GRID_DX for x in (148.5, 224.0, 299.5, 375.0, 450.5, 526.0, 602.0, 677.5)]
ROW_B = [y + GRID_DY for y in (2039.8, 2115.0, 2190.0, 2265.0, 2341.0, 2416.0, 2491.0, 2566.2)]
THUMBS = f"{D}/thumbs"
for n in range(1, 43):
    p = f"{THUMBS}/{n:02d}.png"
    if not os.path.exists(p):
        continue
    col, row = (n - 1) % 7, (n - 1) // 7
    x0, x1 = COL_B[col], COL_B[col + 1]
    y0, y1 = ROW_B[row], ROW_B[row + 1]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cw, ch = x1 - x0, y1 - y0
    # blank the cell first — the template's own printed number sits at a
    # different spot per cell and would otherwise show through
    dr.rectangle((x0 + 3, y0 + 3, x1 - 3, y1 - 3), fill=(255, 255, 255))
    th = Image.open(p).convert("RGB")
    tw, thh = int(cw * 0.86), int(ch * 0.86)
    s = min(tw / th.width, thh / th.height)
    th = th.resize((max(1, int(th.width * s)), max(1, int(th.height * s))))
    board.paste(th, (int(cx - th.width / 2), int(cy - th.height / 2)))
    badge_r = 15
    bx, by = x0 + 4, y0 + 4
    zi = _PART_ZONE.get(n)
    fill = ZONE_RGB[zi] if zi is not None else (255, 255, 255)
    lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
    txt = (255, 255, 255) if lum < 150 else INK
    outline = (150, 152, 156) if zi is None else fill
    dr.ellipse((bx, by, bx + badge_r * 2, by + badge_r * 2), fill=fill, outline=outline)
    dr.text((bx + badge_r, by + badge_r), str(n), font=F(15, True), fill=txt, anchor="mm")

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

def section(xy, title, size=34):
    x, y = xy
    dr.rectangle((x, y + 6, x + 10, y + size - 4), fill=TEAL)
    dr.text((x + 24, y), title, font=F(size, True), fill=TEAL_DK)

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
dr.rectangle((M + 4, 108, M + 14, 258), fill=TEAL)      # ocean-teal accent tick beside the name
wrap((M + 40, 292), "One continuous ribbon, sliced crosswise so it prints on a home bed and still holds an adult.",
     F(44), SUB, maxw=4200)
dr.line((M, 392, W-M, 392), fill=TEAL, width=5)

# ============ VISUALISATION (top) ============
section((M, 432), "VISUALISATION")
img("b_hero.png", (M, 470, 2980, 2520))
img("b_side.png", (3010, 486, 3820, 2170))
img("b_back.png", (3830, 486, 4720, 2170))
img("b_top.png",  (3060, 2110, 4360, 2500))

# ============ STRUCTURE & STABILITY (clear space, right of top view) ============
section((4790, 470), "STRUCTURE & STABILITY", size=34)
wrap((4790, 530), "First-order check at 120 kg x 1.8 dynamic x 2.0 safety — every member passes.",
     F(28), SUB, maxw=1320, sp=6)
stats = [
    ("192 kg", "safe static load"),
    ("4.8x", "weakest epoxied joint margin — 1.6x on the tenon + pin alone, no glue (hand-break tested)"),
    ("0.56 / 0.77", "tipping ratio, sideways / rearward — greater than 0.5 counts as stable"),
]
sy = 660
for big, label in stats:
    dr.text((4790, sy), big, font=F(108, True), fill=TEAL_DK)
    wrap((4790, sy + 136), label, F(28), SUB, maxw=1330, sp=7)
    sy += 400

# dimensions strip — fills the rest of this column, still well clear of the
# key grid (which starts further right at x~6120)
dr.line((4790, sy - 30, 4790 + 1330, sy - 30), fill=HAIR, width=3)
dr.text((4790, sy), "429 x 364", font=F(46, True), fill=TEAL_DK)
dr.text((4790, sy + 58), "seat W x D, mm", font=F(20), fill=SUB)
dr.text((4790 + 420, sy), "455", font=F(46, True), fill=TEAL_DK)
dr.text((4790 + 420, sy + 58), "seat height, mm", font=F(20), fill=SUB)
dr.text((4790 + 780, sy), "3 deg", font=F(46, True), fill=TEAL_DK)
dr.text((4790 + 780, sy + 58), "rearward tilt", font=F(20), fill=SUB)
dr.text((4790, sy + 140), "798 x 685 x 1012", font=F(40, True), fill=TEAL_DK)
dr.text((4790, sy + 190), "overall D x W x H, mm", font=F(20), fill=SUB)
wrap((4790, sy + 250), "Every dimension checked against seating-ergonomics reference "
     "ranges by script — 8/8 pass.", F(23), SUB, maxw=1330, sp=6)

# biomimicry / concept callouts (top right) — kept clear of the key grid,
# which starts at y~1700 in this column
cx = 6180
section((cx, 470), "BIOMIMICRY", size=32)
dr.text((cx + 26, 512), "structural, not applied", font=F(23), fill=SUB)
bio = [
 ("Wolff's law", "thickness follows the bending moment: 84 mm at the lumbar knot, 32 mm blade at the crown"),
 ("Murray's law", "the lumbar is the one 3-way node; section ~ cube-root-sum, every transition filleted"),
 ("Spiral fibre", "flutes follow the stress path + stiffen by corrugation; section twists up to 20 deg"),
 ("Shell curvature", "closed superelliptical section + dished seat carry load in membrane action"),
 ("Fiddlehead scroll", "the curled crown closes the backrest into a rigid loop, not a cantilever"),
 ("Buttress root", "each foot forks into two splayed prongs — wide base, little material"),
]
y = 562
for k, v in bio:
    dr.text((cx, y), k, font=F(27, True), fill=INK)
    wrap((cx, y+36), v, F(22), SUB, maxw=770, sp=5)
    y += 168

dr.line((M, 2540, W-M, 2540), fill=TEAL, width=5)

# ============ ASSEMBLY GUIDE ============  (template's 49-key grid: x~118..708 y~2008..2570)
section((820, 2585), "ASSEMBLY GUIDE")
img("b_exploded.png", (150, 2690, 3050, 4760))
wrap((170, 4770), "Exploded — 41 printed segments, no two alike. The ribbon is one solid form; it is only cut to fit the bed.",
     F(28), SUB, maxw=2800)

steps = [
 ("1", "Lay out by zone", "Parts 1-42 in reading order form six zones: fore-foot fork, front leg, seat, lumbar, backrest, tail-foot fork."),
 ("2", "Crosswise joints", "Every cut is a full solid cross-section. Seat the printed conical tenon (dia 32); two-part epoxy over the whole face. No screws."),
 ("3", "Left + right halves", "Wide segments come in L+R halves. Join along the centre-line with the transverse tenon (dia 24) + epoxy; the seam is the keel."),
 ("4", "Lumbar pins", "Only the two joints beside the lumbar: drive the dia 10 printed pin (x2) through the joint before the epoxy sets."),
 ("5", "Sub-assemble, cure", "Build seat, backrest and each fork-foot separately. Cure 24 h. Then join at the lumbar and the two knees."),
 ("6", "Stand & load", "Set on a flat floor, weight the seat, leave 24 h. Tipping 0.56 sideways; safe static load ~192 kg."),
]
sx = 3230
for i, (n, t, b) in enumerate(steps):
    yy = 2700 + i*300
    dr.ellipse((sx, yy, sx+92, yy+92), fill=TEAL)
    dr.text((sx+46, yy+46), n, font=F(46, True), fill=(255, 255, 255), anchor="mm")
    dr.text((sx+128, yy+2), t, font=F(46, True), fill=INK)
    wrap((sx+128, yy+66), b, F(33), SUB, maxw=1680, sp=9)

dr.line((5170, 2560, 5170, 4770), fill=TEAL, width=4)

# ============ 3D PRINTING (right) ============
section((5250, 2585), "3D PRINTING")
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

# ---- OPEN DESIGN callout box — our strongest reproducibility argument, ----
# ---- given its own visual weight instead of hiding in the row list ----
box_x0, box_y0, box_x1 = 5250, 4640, 6810
try:
    dr.rounded_rectangle((box_x0, box_y0, box_x1, 4900), radius=18, fill=TEAL_TINT)
except AttributeError:
    dr.rectangle((box_x0, box_y0, box_x1, 4900), fill=TEAL_TINT)
section((box_x0 + 24, box_y0 + 22), "OPEN DESIGN", size=28)
wrap((box_x0 + 24, box_y0 + 70), "Nothing in nature repeats itself, so no two parts of this chair do "
     "either: every one of the 41 segments is geometrically unique — script-verified, no two share "
     "volume, area or bounding box. One parametric script: change the width, thickness or infill "
     "tables and it regenerates a leaner, cheaper variant with the same joints — automatically "
     "re-checked against the same load case, so it can't silently export something that fails.",
     F(25), INK, maxw=1512, sp=6)
dr.text((box_x0 + 24, 4840), "Full source, anonymised for review:", font=F(22), fill=SUB)
dr.text((box_x0 + 24, 4868), "anonymous.4open.science/r/manta-chair-23D4", font=F(24, True), fill=TEAL_DK)

board.convert("RGB").save(OUTF, "JPEG", quality=86)
print(f"{OUTF}  {board.size}  {os.path.getsize(OUTF)/1e6:.2f} MB")
