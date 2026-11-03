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
# the sea, from the floor to the foam -- the chair's own colour story
DEEP, FOAM = (12, 38, 74), (176, 228, 228)
_STOPS = [(0.0, DEEP), (0.5, TEAL), (1.0, FOAM)]


def depth(t):
    """colour at depth t: 0 = sea floor (deep blue), 1 = foam"""
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(_STOPS, _STOPS[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            return tuple(int(round(a + (b - a) * u)) for a, b in zip(c0, c1))
    return _STOPS[-1][1]

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

base = (Image.open("_board_base.png").convert("RGB").resize((W, H))
        if os.path.exists("_board_base.png") else Image.new("RGB", (W, H), "white"))
SURF = 2540                      # the waterline between the two halves of the board
SKY0, SKY1 = (240, 250, 250), (206, 236, 238)        # air and the sunlit surface
SEA0, SEA1 = (18, 66, 100), (7, 22, 44)              # down into the deep
_bg = Image.new("RGB", (1, H))
for _y in range(H):
    if _y < SURF:
        u = _y / SURF; a_, b_ = SKY0, SKY1
    else:
        u = (_y - SURF) / (H - SURF); a_, b_ = SEA0, SEA1
    _bg.putpixel((0, _y), tuple(int(round(p + (q - p) * u)) for p, q in zip(a_, b_)))
board = _bg.resize((W, H))
dr = ImageDraw.Draw(board)
# text colours for the deep half
DEEP_TXT, DEEP_SUB, DEEP_HEAD = (236, 246, 248), (160, 204, 212), (176, 228, 228)

# The template's key grid sits at a spot that collides with the hero render
# in this layout — the brief explicitly allows relocating it ("You can
# adjust the location of this key as necessary"), so cut the whole grid +
# ".STL parts arrangement" caption block out of the untouched template and
# move it to the clear space under the biomimicry column instead. Cover the
# old spot with white first so nothing of it peeks out from under the hero.
GRID_SRC_BOX = (40, 1950, 780, 2750)     # grid + caption, as provided
GRID_DX, GRID_DY = 6080, -250            # where it moves to
grid_block = base.crop(GRID_SRC_BOX)
_gm = grid_block.convert("L").point(lambda v: 255 if v < 235 else 0)     # ink + grey frame
_gbb = _gm.getbbox()                                                     # frame + caption box
_frame = Image.new("L", grid_block.size, 0)
ImageDraw.Draw(_frame).rounded_rectangle((_gbb[0], _gbb[1], _gbb[2], _gbb[1] + 600), radius=60, fill=255)
from PIL import ImageChops
_mask = ImageChops.lighter(_gm, _frame)
board.paste(grid_block, (GRID_SRC_BOX[0] + GRID_DX, GRID_SRC_BOX[1] + GRID_DY), _mask)

# the template's 49-slot grid stays whole (unused slots 44-49 = empty, allowed) —
# each of the 43 used boxes gets a small picture of that actual part (like a
# real furniture-assembly manual), with the box's own printed number redrawn
# on top in a corner so it stays legible regardless of what's under it.
# exact cell boundaries measured on _board_base.png (columns/rows are NOT
# perfectly uniform, so use the real gap positions rather than an average),
# then shifted by the same relocation offset as the grid block above.
COL_B = [x + GRID_DX for x in (148.5, 224.0, 299.5, 375.0, 450.5, 526.0, 602.0, 677.5)]
ROW_B = [y + GRID_DY for y in (2039.8, 2115.0, 2190.0, 2265.0, 2341.0, 2416.0, 2491.0, 2566.2)]
THUMBS = f"{D}/thumbs"
for n in range(1, len(_part_names()) + 1):        # 43 = the piece split off at the crossing
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

def section(xy, title, size=34, col=None, bar=None):
    x, y = xy
    dr.rectangle((x, y + 6, x + 10, y + size - 4), fill=bar or TEAL)
    dr.text((x + 24, y), title, font=F(size, True), fill=col or TEAL_DK)

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
wrap((M + 40, 292), "A wave that rose from the sea floor and stayed.", F(44), SUB, maxw=1250)


def hband(x0, x1, y, h=8):
    for x in range(int(x0), int(x1)):
        dr.line((x, y, x, y + h), fill=depth((x - x0) / (x1 - x0)))


def vband(x, y0, y1, w=6):
    for y in range(int(y0), int(y1)):
        dr.line((x, y, x + w, y), fill=depth(1 - (y - y0) / (y1 - y0)))


# three pillars: why this chair, this form, this colour
pillars = [
    ("OXYGEN", "The ocean makes at least half of the oxygen we breathe. MANTA is a wave of it, "
               "a story of a living planet: deep blue at the feet, foam at the crest."),
    ("WASTE", "We fill that ocean with plastic; microplastics are found even in human blood. "
              "MANTA is printed with sense: under 1 % support waste, ideally in recycled PETG."),
    ("LIFE", "The manta ray tells how healthy the sea is. Its fins hold the chair, from the side "
             "the seat draws its M (Manta, Mare), and biomimicry puts material only where the load is."),
]
px0, pw = 1560, 1740
for i, (key, txt) in enumerate(pillars):
    x = px0 + i * (pw + 50)
    col = depth(0.1 + 0.25 * i)
    dr.rectangle((x, 128, x + 10, 368), fill=col)
    dr.text((x + 34, 120), key, font=F(64, True), fill=col)
    wrap((x + 36, 206), txt, F(31), INK, maxw=pw - 60, sp=8)
hband(M, W - M, 392, 10)

# ============ VISUALISATION (top) ============
section((M, 432), "VISUALISATION")
img("b_hero.png", (M, 470, 2980, 2520))
# callouts ON the dark render (hero is fitted: scale 0.82, origin 581,470)
_hx = lambda x, y: (581 + x * 0.82, 470 + y * 0.82)
LBL, LTX = (186, 236, 236), (196, 212, 218)


def callout(pt, at, key, txt, maxw=600, right=False):
    px, py = _hx(*pt)
    ax, ay = at
    # the label block's box; the leader stops on its edge, nearest the chair,
    # so it never runs through the words
    words, lines, cur = txt.split(), [], ""
    for w_ in words:
        if dr.textlength((cur + " " + w_).strip(), font=F(26)) <= maxw: cur = (cur + " " + w_).strip()
        else: lines.append(cur); cur = w_
    lines.append(cur)
    bw = max([dr.textlength(key, font=F(34, True))] + [dr.textlength(l_, font=F(26)) for l_ in lines])
    x0b, y0b, x1b, y1b = ax - 14, ay - 12, ax + bw + 14, ay + 48 + 32 * len(lines) + 6
    ex, ey = min(max(px, x0b), x1b), min(max(py, y0b), y1b)
    dr.line((px, py, ex, ey), fill=LBL, width=3)
    dr.ellipse((px - 11, py - 11, px + 11, py + 11), fill=LBL, outline=DEEP, width=3)
    dr.text((ax, ay), key, font=F(34, True), fill=LBL)
    wrap((ax, ay + 48), txt, F(26), LTX, maxw=maxw, sp=6)


callout((1150, 610), (640, 640), "THE CREST", "a wave breaking forward, falling back through itself", 560)
callout((960, 1050), (640, 1180), "COLOUR", "the depth of the sea: deep blue at the feet, foam at the crest", 560)
callout((1440, 1370), (1980, 1080), "THE CURRENT", "flutes, bold at the floor, calm at the crest, smooth where you sit", 520)
callout((540, 1975), (640, 2310), "FINS", "every foot forks into two splayed prongs: a manta on the seabed", 900)
# the REAL chair: printed at home, glued, photographed -- next to the render
def photo(path, box, focus=(0.5, 0.5)):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    if not os.path.exists(path):
        dr.rectangle(box, outline=HAIR, width=3); return
    im = Image.open(path).convert("RGB")
    s = max(bw / im.width, bh / im.height)
    im = im.resize((max(bw, int(im.width * s)), max(bh, int(im.height * s))))
    ox, oy = int((im.width - bw) * focus[0]), int((im.height - bh) * focus[1])
    board.paste(im.crop((ox, oy, ox + bw, oy + bh)), (x0, y0))

photo("photos/prototype_4.jpg", (3010, 486, 3860, 1610))                    # side
photo("photos/prototype_5.jpg", (3870, 486, 4720, 1610))                    # study model in the palm
photo("photos/prototype_3.jpg", (3010, 1620, 3860, 2440), focus=(0.35, 0.55))  # study model + chair
photo("photos/prototype_7.jpg", (3870, 1620, 4720, 2440), focus=(0.5, 0.70))   # study model on the seat (whole chair)
dr.rounded_rectangle((3030, 1530, 3600, 1592), radius=12, fill=DEEP)
dr.text((3052, 1561), "the M, seen from the side", font=F(30, True), fill=FOAM, anchor="lm")
dr.rounded_rectangle((3030, 506, 3720, 570), radius=12, fill=TEAL)
dr.text((3052, 538), "BUILT  -  full-size prototype", font=F(34, True), fill=(255, 255, 255), anchor="lm")
wrap((3010, 2448), "Printed at home (light variant, 75 % walls): ~9 kg, ~160 h, ~77 EUR with glue. Every part means "
     "something: forked feet = manta fins; the side profile draws an M (Manta, Mare); the crest = a breaking wave; "
     "colour = sea depth to foam; white seams = sea foam (epoxy + silica). Black: the first study model.",
     F(23), SUB, maxw=1710, sp=3)

def bubbles(box, n, seed, rmax=34):
    import random
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        t = rnd.random() ** 1.6                       # more, smaller bubbles higher up
        y = y1 - (y1 - y0) * (1 - t) if rnd.random() < 0.5 else y0 + (y1 - y0) * t
        x = rnd.uniform(x0, x1)
        r = rnd.uniform(6, rmax) * (0.45 + 0.55 * (y - y0) / max(1, y1 - y0))
        dr.ellipse((x - r, y - r, x + r, y + r), outline=(120, 196, 204), width=max(2, int(r / 9)))
        dr.ellipse((x - r * 0.45, y - r * 0.55, x - r * 0.15, y - r * 0.25), fill=(255, 255, 255))


bubbles((2575, 600, 2990, 2480), 55, 1)          # between the render and the photos
bubbles((165, 480, 560, 2500), 40, 2, 26)          # left of the render
dr.text((2780, 1500), "O", font=F(46, True), fill=(80, 160, 170), anchor="mm")
dr.text((2808, 1516), "2", font=F(26, True), fill=(80, 160, 170), anchor="mm")

# ============ STRUCTURE & STABILITY (clear space, right of top view) ============
section((4790, 470), "STRUCTURE & STABILITY", size=34)
wrap((4790, 530), "First-order check at 120 kg x 1.8 dynamic x 2.0 safety — every member passes.",
     F(28), SUB, maxw=1320, sp=6)
stats = [
    ("~250 kg", "safe static load, glued — weakest glued check 2.1x"),
    ("26x", "the glued full cross-section, the real load path. With no glue at all, peg + solid pin alone still carry 0.9x of the full design load"),
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
dr.text((4790 + 420, sy), "428", font=F(46, True), fill=TEAL_DK)
dr.text((4790 + 420, sy + 58), "seat height, mm", font=F(20), fill=SUB)
dr.text((4790 + 780, sy), "5 deg", font=F(46, True), fill=TEAL_DK)
dr.text((4790 + 780, sy + 58), "rearward tilt", font=F(20), fill=SUB)
dr.text((4790, sy + 140), "812 x 698 x 998", font=F(40, True), fill=TEAL_DK)
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
for j, (k, v) in enumerate(bio):
    dr.rectangle((cx - 22, y + 4, cx - 14, y + 128), fill=depth(0.1 + 0.15 * j))
    dr.text((cx, y), k, font=F(27, True), fill=INK)
    wrap((cx, y+36), v, F(22), SUB, maxw=770, sp=5)
    y += 168

hband(M, W - M, 2540, 8)
# what we leave in the sea floats on its surface
PLAS, PLAS2 = (126, 150, 166), (196, 140, 112)
def bottle_h(x, y, a=0.0, col=PLAS):
    pts = [(-62, -16), (30, -16), (44, -9), (62, -9), (62, 9), (44, 9), (30, 16), (-62, 16)]
    c, s_ = math.cos(a), math.sin(a)
    dr.polygon([(x + px * c - py * s_, y + px * s_ + py * c) for px, py in pts], fill=col)
def bag_f(x, y, col=PLAS):
    dr.polygon([(x - 46, y + 6), (x - 30, y - 22), (x - 6, y - 10), (x + 12, y - 30), (x + 34, y - 8),
                (x + 52, y + 4), (x + 20, y + 14), (x - 20, y + 16)], fill=col)
def cap_f(x, y, col=PLAS2):
    dr.ellipse((x - 13, y - 9, x + 13, y + 9), fill=col)
bottle_h(2660, 2536, 0.12); cap_f(2780, 2540); bag_f(2900, 2534)
bag_f(4900, 2532); bottle_h(5120, 2540, -0.08); cap_f(5300, 2538); cap_f(5520, 2542, PLAS)
bottle_h(5800, 2534, 0.2, PLAS2); bag_f(6460, 2534); cap_f(6650, 2540)

# ============ ASSEMBLY GUIDE ============  (template's 49-key grid: x~118..708 y~2008..2570)
section((820, 2585), "ASSEMBLY GUIDE", col=DEEP_HEAD, bar=FOAM)
# the exploded view as a rounded card on the deep half
_ex = Image.open(f"{D}/b_exploded.png").convert("RGB")
_s = min(2900 / _ex.width, 2070 / _ex.height)
_ex = _ex.resize((int(_ex.width * _s), int(_ex.height * _s)))
_ox, _oy = 150 + (2900 - _ex.width) // 2, 2690 + (2070 - _ex.height) // 2
_rm = Image.new("L", _ex.size, 0)
ImageDraw.Draw(_rm).rounded_rectangle((0, 0, _ex.width - 1, _ex.height - 1), radius=48, fill=255)
board.paste(_ex, (_ox, _oy), _rm)
wrap((170, 4770), "Exploded — 43 parts (42 pieces of ribbon + the pin), no two alike. Cuts and pegs are computed: cuts stay clear of the peak-load knee and lumbar, pegs follow the section, every joint verified by virtual assembly.",
     F(28), DEEP_SUB, maxw=2800)

steps = [
 ("1", "Lay out by zone", "Every part has its number (1-43) ENGRAVED on a glue face. In reading order they form six zones: fore-foot fork, front leg, seat, lumbar, backrest, tail-foot fork."),
 ("2", "Left + right halves FIRST", "Wide segments come in L+R halves. Glue each pair along the centre-line on its transverse peg (up to dia 20) before anything else; the seam is the keel."),
 ("3", "Crosswise joints", "Then join the segments: seat the printed conical peg (dia 27 at the face) in its socket, two-part epoxy over the whole face. No screws."),
 ("4", "Lumbar pins", "Only the two joints beside the lumbar: slide a dia 11 pin in from each side face until it stops (2 per joint) before the epoxy sets."),
 ("5", "The crossing, cure", "Where the ribbon returns through the backrest it is trimmed to the backrest's shape: epoxy the loop's end (27, 28 + small piece 43, split from 29) onto its front and the tail brace (29, 30) onto its back (saddle, 56 cm2). Build seat, backrest and fork-feet separately, cure 24 h, then join at the lumbar and knees."),
 ("6", "Stand & load", "Set on a flat floor, weight the seat, leave 24 h. Tipping 0.56 sideways; safe static load ~250 kg."),
]
sx = 3230
for i, (n, t, b) in enumerate(steps):
    yy = 2700 + i*300
    _c = depth(0.1 + 0.16 * i)
    dr.ellipse((sx, yy, sx+92, yy+92), fill=_c)
    dr.text((sx+46, yy+46), n, font=F(46, True), fill=(255, 255, 255) if i < 4 else DEEP, anchor="mm")
    dr.text((sx+128, yy+2), t, font=F(46, True), fill=DEEP_TXT)
    wrap((sx+128, yy+66), b, F(33), DEEP_SUB, maxw=1680, sp=9)

vband(5168, 2560, 4770, 6)

# down in the deep there is life: mantas swimming
def manta(cx, cy, w, ang=0.0, col=(44, 104, 132)):
    pts = []
    for k in range(0, 21):                      # right wing: leading edge, tip, trailing edge
        t = k / 20.0
        pts.append((0.08 * w + 0.42 * w * t, -0.24 * w + 0.24 * w * t ** 0.6))
    for k in range(0, 21):
        t = k / 20.0
        pts.append((0.5 * w - 0.38 * w * t, 0.02 * w + 0.18 * w * t ** 1.4))
    body = ([(0.12 * w, 0.2 * w), (0.06 * w, 0.24 * w)] +
            [(-x, y) for x, y in [(0.06 * w, 0.24 * w), (0.12 * w, 0.2 * w)]] +
            [(-x, y) for x, y in reversed(pts)] +
            [(-0.06 * w, -0.3 * w), (-0.03 * w, -0.24 * w), (0.03 * w, -0.24 * w), (0.06 * w, -0.3 * w)])
    poly = pts + body
    c, s_ = math.cos(ang), math.sin(ang)
    dr.polygon([(cx + x * c - y * s_, cy + x * s_ + y * c) for x, y in poly], fill=col)
    tx, ty = 0.0, 0.62 * w                       # the long thin tail
    dr.line((cx - 0.0 * c - 0.24 * w * s_, cy + 0.24 * w * c, cx + tx * c - ty * s_, cy + tx * s_ + ty * c),
            fill=col, width=max(3, int(w / 90)))


manta(3640, 4790, 260, -0.15)
manta(4330, 4760, 190, 0.22, (36, 92, 120))
manta(4880, 4850, 120, -0.35, (32, 82, 110))
manta(250, 2630, 130, 0.3, (40, 98, 126))

# what MANTA throws away: its supports, against the chair itself
wx0, wy0, wx1 = 3230, 4470, 5060
dr.text((wx0, wy0), "WASTE", font=F(46, True), fill=DEEP_HEAD)
wrap((wx0 + 190, wy0 + 8), "Plastic, printed with sense: supports are 0.7 % of the filament (121 g of "
     "16.4 kg, PrusaSlicer), none trapped in a hole, and we recommend recycled PETG.",
     F(28), DEEP_SUB, maxw=wx1 - wx0 - 190, sp=6)
by = wy0 + 120
dr.rounded_rectangle((wx0, by, wx1, by + 56), radius=12, fill=(36, 132, 146))
_wx = wx1 - max(8, int((wx1 - wx0) * 0.007))
dr.rounded_rectangle((_wx, by, wx1, by + 56), radius=6, fill=(238, 120, 90))
dr.text((wx0 + 22, by + 28), "the chair  99.3 %", font=F(28, True), fill=(255, 255, 255), anchor="lm")
dr.text((_wx - 14, by + 28), "supports 0.7 %", font=F(28, True), fill=(255, 220, 205), anchor="rm")

# ============ 3D PRINTING (right) ============
section((5250, 2585), "3D PRINTING", col=DEEP_HEAD, bar=FOAM)
rows = [
 ("PARTS", "43: 42 pieces of ribbon (41 segments, one in two pieces) + the pin (print x4)  -  limit 49"),
 ("PART SIZE", "each <= 212 x 220 x 250 mm"),
 ("SUPPORTS", "almost none: under 1 % of the filament (121 g, PrusaSlicer), from the build plate only; every hole is shaped for how its part lies, so none grows inside"),
 ("MATERIAL", "PETG"),
 ("LAYER / NOZZLE", "0.20 mm  /  0.4 mm"),
 ("WALLS", "5 perimeters"),
 ("INFILL", "35 % gyroid  (kept low — the ribbon's own bulk carries the load)"),
 ("ADHESIVE", "two-part epoxy thickened with fumed silica: ~20 EUR for the whole chair"),
 ("PIN", "dia 11 x 133 mm rod, 100 % infill, printed lying on its flat, x4 (2 lumbar joints)"),
 ("EST. WEIGHT", "~16.5 kg  -  ~110 EUR: ~90 filament (PrusaSlicer) + ~20 epoxy"),
 ("BATCH TIME", "~460 h on one printer (PrusaSlicer estimate)"),
]
y = 2680
for k, v in rows:
    dr.text((5250, y), k, font=F(26, True), fill=DEEP_SUB)
    wrap((5250, y+38), v, F(31), DEEP_TXT, maxw=1560, sp=5)
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
     "either: all 42 pieces of the ribbon are geometrically unique — script-verified. One "
     "parametric script: change the width, thickness or infill tables and it regenerates a leaner "
     "variant with the same joints, automatically re-checked so it can't export something that "
     "fails. One command (manta_verify.py) re-runs every check: strength, virtual assembly, "
     "bed fit, real-slicer support. A ready 70 kg, half-filament variant is in the repo.",
     F(25), INK, maxw=1512, sp=6)
dr.text((box_x0 + 24, 4840), "Full source, anonymised for review:", font=F(22), fill=SUB)
dr.text((box_x0 + 24, 4868), "anonymous.4open.science/r/manta-chair-23D4", font=F(24, True), fill=TEAL_DK)

board.convert("RGB").save(OUTF, "JPEG", quality=86)
print(f"{OUTF}  {board.size}  {os.path.getsize(OUTF)/1e6:.2f} MB")
