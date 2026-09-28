#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA — one continuous ribbon  (one gesture, sliced crosswise + split lengthwise
down the centre)
===================================================================
The whole chair is ONE thick, continuous ribbon (Zaha / year 2500). No separate
legs, no visible assembly. Front + rear foot on the floor and an open loop
above -> a rigid loop, never a bare cantilever.

ERGONOMICS (a real chair, not a perch):
  seat front-edge height ~455 mm - seat depth ~410 mm - seat width ~430 mm
  seat tilt ~3 deg rearward - convex lumbar support - backrest recline ~11 deg

BIOMIMICRY — every rule is STRUCTURAL, never decoration:
  Wolff    — section thickness follows the bending moment: THICKEST at the
             lumbar (the knot where seat + backrest + tail meet) and at the
             knee; a BLADE at the free crown.
  Murray   — at the lumbar (the one true junction) section ~ (sum of
             branch^3)^(1/3); no sharp corners, every transition filleted.
  fibre    — longitudinal FLUTES run continuously along the axis = the stress
             direction; corrugation stiffens (a leaf, a blade of grass). A
             flat ribbon goes slack, a fluted one stands up.
  shell    — superelliptical (closed, rounded) section + a transverse dish in
             the seat = membrane-style load carrying (an egg, a lily pad).
  loop     — the forward curl at the top draws the front and back of the
             backrest together (a fern fiddlehead): the backrest becomes a
             closed tube, not a cantilever.
  root     — both feet WIDEN into a broad flat contact patch near the floor
             (fig-tree buttress roots / mangroves: stability from few
             contacts and little material).

JOINTS — no flat face is ever glued to another flat face:
  * CROSSWISE ("baguette" cut): the cut is perpendicular to the axis -> the
    glued face is the FULL cross-section (~430x85 = ~17,000 mm^2 at the
    lumbar). An axial conical tenon + epoxy.
  * LENGTHWISE, down the centre: wide segments (seat, backrest) split into
    L/R halves along the chair's centreline. The seam sits between the
    sit-bones (low stress), hidden in a flute, and reads as a visible spine
    (breastbone / leaf midrib). Transverse tenon + pin.
  * Cuts are never placed at the lumbar or the knee — those stay whole, in
    the middle of a segment.
  * A pin (dia 8) additionally crosses the joint at both legs (a lock
    against the joint opening under load).

OUTPUT:  ./MANTA_RIBBON/  (SEG_*.stl, PIN.stl, MANTA_Chair.stl,
                            MANTA_Assembly.stl, PARTS_LIST.txt)
RUN:     python manta_ribbon.py      REQUIRES: cadquery, numpy, scipy
"""

import os
import math
import numpy as np
from scipy.interpolate import splprep, splev
import cadquery as cq
from cadquery import Vector

# ═══════════════════════════ PARAMETERS ═══════════════════════════
# ribbon axis in side profile (X = forward +, Z = up). Starts at the front foot.
# VARIANT beta — DRAMATIC CANTILEVER: the backrest leans back (overhang), a
# long tail-brace well behind the backrest holds the balance (kangaroo tail /
# a buttress root in tension).
SPINE = [
    (472,    0),                        # front foot — sole
    (474,   90), (462, 300),            # support root + straight run-up
    (452,  455),                        # KNEE / front edge of the seat
    (330,  436), (205, 428), ( 92, 450),   # seat — shallow dish, ~3 deg rearward
    ( 32,  548),                        # LUMBAR
    (  6,  680), (-16, 812),            # backrest, ~11 deg overhang
    ( -8,  902),                        # shoulders / top edge
    ( 30,  952), ( 70,  946), ( 82,  892),  # CROWN — curled tip, forward ('2500')
    ( 46,  788),                        # return
    (-52,  548), (-160, 300), (-232, 110),  # long brace, back and down
    (-240,    0),                       # rear foot — sole (behind the backrest)
]

# ribbon width (Y). Narrow leg -> sudden widening into the seat (hood) ->
# backrest tapers gently -> narrow brace.
W_S = [(0.00,180),(0.08,188),(0.12,202),(0.15,286),(0.19,430),(0.30,428),
       (0.37,336),(0.43,286),(0.49,292),(0.55,312),(0.60,308),(0.65,238),
       (0.70,180),(0.79,148),(0.87,148),(0.94,170),(1.00,190)]
# section thickness (through) — bending moment (Wolff's law): max at the
# lumbar, a blade at the crown, a thicker lower brace (compression + moment
# from the backrest overhang).
TH_S = [(0.00,53),(0.07,46),(0.14,66),(0.21,46),(0.29,48),(0.36,90),(0.43,64),
        (0.50,39),(0.57,32),(0.63,24),(0.68,24),(0.74,38),(0.82,47),
        (0.90,55),(1.00,48)]

FLUTE_N = 4          # longitudinal flutes — main frequency (fewer = bolder, more dramatic lines)
# Flowing lines that follow the ribbon's own movement, not a cross-hatched
# cell pattern — the lines trace the gesture instead of breaking it up.
# Print-safety (45-deg rule) is verified numerically on the real surface,
# see _check_overhang.py in the project history: worst added slope ~28 deg.
FLUTE_A0 = 7.5       # amplitude at the floor (legs) — bold, dramatic lines
FLUTE_A1 = 4.5       # amplitude at the crown — calmer, still clearly present
FOAM_N   = 14        # a fine high-frequency line, only near the top (distinct from the main flute)
FOAM_A   = 2.0       # subtle accent near the crown
SECT_M  = 76
SE_N    = 3.0        # superellipse exponent (rounded, stiff edges)

# spiral fibre — the section twists around the flow axis (Zaha-style sweep +
# biomimicry). (fraction of length, angle in degrees). Near 0 in the seat
# (so it stays sittable).
# the twist eases off through the crown scroll (s~0.55-0.61, bend radius ~30 mm):
# twisting a 310 mm wide ribbon there folds its inner edge over itself
TWIST_S = [(0.00,0),(0.13,-12),(0.24,0),(0.34,0),(0.45,9),(0.51,12),(0.575,3),
           (0.645,21),(0.70,26),(0.80,16),(0.92,-8),(1.00,-16)]

SEAT_DISH_LAT = 12.0   # transverse seat dish (mm, at bottom centre)
LUMBAR_BUMP   = 18.0   # convex lumbar support toward the body (typical support range 15-25mm)

SEG_MAX  = 198.0
TURN_MAX = 1.02        # ~58 deg per segment; beyond VERT_TURN the segment prints standing up
VERT_TURN = 0.55       # a segment that turns more than this prints standing up (no supports)
MIN_SEG  = 80.0
FORBID   = 70.0        # a cut never comes closer than this to the lumbar/knee (mm)
                       # -> the moment at a cut stays ~2x lower than at the knot

SPLIT_W  = 214.0       # a segment wider than this also gets split lengthwise (L/R)

# ── FORKED FOOT (support root / Murray's fork) ──
# near the end the ribbon splits into 2 prongs that splay outward = a wide
# stable base from few contacts, little material (fig-tree buttress roots,
# mangroves).
FORK_ARC   = 198.0     # arc length from the tip where the fork develops (mm)
FORK_SPLAY = 252.0     # sideways splay of each prong's centre at the floor (mm from centreline)
FORK_SEG   = 78.0      # shorter segments in the fork zone (so they fit the bed)
PRONG_PAD_HALF = 76.0  # prong half-width at the floor
PRONG_TH_END   = 44.0  # thickness of the prong's flat pad
TEN_R, TEN_TIP, TEN_L = 16.0, 11.0, 44.0    # crosswise conical tenon
LTEN_R, LTEN_TIP, LTEN_L = 12.0, 8.0, 34.0  # lengthwise tenon (L/R)
TEN_CLR = 0.12
TEN_ROOT = 3.0        # mm of each peg fused into its own part (only the rest protrudes)
SOCK_EXTRA = 0.6      # socket this much deeper than the peg: the glue faces meet, not the tip
JOINT_REPORT, BUILD_PROBLEMS, JOINT_GEOM = [], [], []
PIN_R, PIN_CLR = 5.5, 0.15                   # dia 11 crosswise pin, printed SOLID (100% infill)
PIN_POS = 0.35        # pin centre at this fraction of the peg length past the cut: close to
                      # the face so enough peg is left beyond it to not tear out

BED = (212.0, 220.0, 250.0)
MESH_TOL, MESH_ANG = 0.14, 0.35     # MANTA_Chair.stl (submission + render)
STL_TOL, STL_ANG   = 0.45, 0.8      # segments + Assembly (10 MB total limit)
OUT = "MANTA_RIBBON"
# ════════════════════════════════════════════════════════════════

def set_spine(pts):
    global _TCK, _UU, _PP, _DL, _LEN
    a = np.asarray(pts, float)
    _TCK, _ = splprep([a[:, 0], a[:, 1]], s=0, k=3)
    _UU = np.linspace(0, 1, 1600)
    _PP = np.array([_raw(u) for u in _UU])
    _DL = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(_PP, axis=0), axis=1))]
    _LEN = float(_DL[-1])
    if "tangent" in globals():
        recompute_corners()


def _raw(u):
    x, z = splev(np.clip(u, 0, 1), _TCK)
    return np.array([float(x), 0.0, float(z)])


set_spine(SPINE)


def center(s):
    u = np.interp(np.clip(s, 0, 1) * _LEN, _DL, _UU)
    return _raw(u)


def tangent(s):
    d = 3.5e-4
    t = center(min(s + d, 1.0)) - center(max(s - d, 0.0))
    n = np.linalg.norm(t)
    return t / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])


try:
    from scipy.interpolate import PchipInterpolator
except Exception:
    PchipInterpolator = None
_PCH = {}


def itp(s, pairs):
    a = np.asarray(pairs, float)
    if PchipInterpolator is not None:          # smooth (C1) profile -> no kinks
        key = id(pairs)
        f = _PCH.get(key)
        if f is None:
            f = _PCH[key] = PchipInterpolator(a[:, 0], a[:, 1], extrapolate=True)
        return float(f(np.clip(s, 0.0, 1.0)))
    return float(np.interp(s, a[:, 0], a[:, 1]))


ERGO_LUMB_H = 170.0   # mm, the lumbar support should sit THIS HIGH above the seat (standard
                      # range 150-250mm above the compressed seat — the small-of-the-back
                      # curve, NOT the sit-bones)

# ── corners (knee, lumbar) = the points of sharpest axis turning ──
def recompute_corners():
    global _KNEE, _LUMB, CORNERS, _SEATMID, _ERGO_LUMB, _CROWN
    d = np.linspace(0, 1, 900)
    ang = np.unwrap([math.atan2(tangent(s)[2], tangent(s)[0]) for s in d])
    rate = np.abs(np.gradient(ang, d))

    def pk(lo, hi):
        idx = np.where((d >= lo) & (d <= hi))[0]
        return float(d[idx[int(np.argmax(rate[idx]))]])

    _KNEE = pk(0.09, 0.26)
    _LUMB = pk(0.28, 0.46)          # STRUCTURAL knot (bending moment) — for joints/thickness
    CORNERS = [_KNEE, _LUMB]
    _SEATMID = 0.5 * (_KNEE + _LUMB)
    # The ERGONOMIC lumbar support is a DIFFERENT point than _LUMB: found by
    # height above the seat, not by geometric curvature. _LUMB itself lands
    # almost at the sit-bones (barely above the seat) — too low to support
    # the lower back.
    seat_z = center(_SEATMID)[2]
    dd = np.linspace(_LUMB, min(_LUMB + 0.22, 0.85), 400)
    zz = np.array([center(s)[2] for s in dd])
    _ERGO_LUMB = float(dd[int(np.argmin(np.abs(zz - (seat_z + ERGO_LUMB_H))))])
    # crown = the highest point of the spine (the fiddlehead curl's tip)
    dz = np.linspace(0.3, 0.85, 900)
    zc = np.array([center(s)[2] for s in dz])
    _CROWN = float(dz[int(np.argmax(zc))])


recompute_corners()

# ── six assembly zones (matches "Lay out by zone" on the Board): computed
# from the same landmarks used everywhere else (knee/lumbar/crown/fork),
# not eyeballed, so relabelling stays correct if the spine is ever retuned.
ZONE_NAMES = ["fore-foot fork", "front leg", "seat", "lumbar", "backrest", "tail-foot fork"]
# ocean palette, but with real hue/lightness steps between zones so they
# actually read apart at a glance — a narrow teal-on-teal ramp looked like
# one colour. Lumbar stays a clear amber accent (the one true structural knot).
ZONE_COLORS = [
    (0.03, 0.09, 0.20),   # fore-foot fork — near-black navy
    (0.05, 0.42, 0.68),   # front leg — clear blue
    (0.02, 0.62, 0.55),   # seat — teal
    (0.88, 0.58, 0.08),   # lumbar — amber, the one true knot
    (0.15, 0.50, 0.14),   # backrest — forest green
    (0.72, 0.86, 0.30),   # tail-foot fork — lime, tip of the curl
]


def zone_of(s):
    """0..5 assembly zone for a spine fraction s, per ZONE_NAMES."""
    fork_lo = FORK_ARC / _LEN
    if s < fork_lo:
        return 0                       # fore-foot fork
    if s < _KNEE:
        return 1                       # front leg
    lumb_lo, lumb_hi = _LUMB - FORBID / _LEN, _LUMB + FORBID / _LEN
    if s < lumb_lo:
        return 2                       # seat
    if s < lumb_hi:
        return 3                       # lumbar (the knot itself stays whole)
    if s < _CROWN + 0.05:
        return 4                       # backrest (through the curl)
    return 5                           # tail-foot fork (return + brace + rear fork)


def fork_amt(s):
    """0 before the fork -> ~0.94 at the tip (foot). Ease-in, never reaches 1
    so the prong tip stays solid (not a sharp point)."""
    d = min(s, 1.0 - s) * _LEN
    return 0.94 * max(0.0, min(1.0, 1.0 - d / FORK_ARC)) ** 1.3


def foot_fac(s):
    return 1.0, 1.0        # (foot widening is now handled by the fork, not this)


def seat_win(s):
    return max(0.0, 1.0 - abs(s - _SEATMID) / (0.62 * (_LUMB - _KNEE) + 0.02))


def lumbar_win(s):
    """ergonomic lumbar support — centred on _ERGO_LUMB (the real height of
    the small-of-the-back curve above the seat), NOT on _LUMB (that is only
    the structural knot right above the seat, too low to support the lower back)."""
    return max(0.0, 1.0 - abs(s - _ERGO_LUMB) / 0.07)


def back_win(s):
    """the whole back (lumbar to shoulders) — the actual contact area, not
    just a narrow peak. Plateau = 1.0 across the full lumbar->shoulder span,
    a soft falloff only at the edges."""
    lo, hi = _LUMB - 0.02, 0.60
    if lo <= s <= hi:
        return 1.0
    if s < lo:
        return max(0.0, 1.0 - (lo - s) / 0.08)
    return max(0.0, 1.0 - (s - hi) / 0.06)


_SECT = []
for i in range(SECT_M):
    ph = 2 * math.pi * i / SECT_M
    cx = math.copysign(abs(math.cos(ph)) ** (2.0 / SE_N), math.cos(ph))
    cz = math.copysign(abs(math.sin(ph)) ** (2.0 / SE_N), math.sin(ph))
    broad = abs(cz) ** 1.5
    fl_main = broad * math.sin(FLUTE_N * math.pi * (cx * 0.5 + 0.5))
    fl_foam = broad * math.sin(FOAM_N * math.pi * (cx * 0.5 + 0.5) + 0.7)
    _SECT.append((cx, cz, fl_main, fl_foam))

_ZLO = float(min(p[2] for p in _PP))
_ZHI = float(max(p[2] for p in _PP))


def _depth_frac(s):
    """0 = at the floor (legs, 'the depths'), 1 = at the crown ('the surface')."""
    z = float(center(s)[2])
    return max(0.0, min(1.0, (z - _ZLO) / (_ZHI - _ZLO + 1e-9)))


_TWCAP = {"key": None, "d": None, "cap": None}


def _twist_cap(s):
    """Largest twist (radians) the section may have at s without its inner
    edge folding over itself on a tight curl. Twist tips one half of the
    width toward the inside of the bend; at the crown the spine turns with a
    ~30 mm radius, and 20 deg of twist on a 155 mm half-width pushed that edge
    ~50 mm inward -- past the centre of the bend -- so consecutive segments
    overlapped by several cm3 and could not be assembled. Rule: the inner
    edge (half-width * sin(twist) + half-thickness) stays within 80% of the
    local bend radius. Smoothed along the ribbon so the twist eases in and
    out instead of snapping."""
    key = (round(_LEN, 3), id(TWIST_S), id(W_S), id(TH_S))
    if _TWCAP["key"] != key:
        from scipy.ndimage import minimum_filter1d, gaussian_filter1d
        d = np.linspace(0.0, 1.0, 1201)
        tg = np.array([tangent(x) for x in d])
        ang = np.r_[np.arccos(np.clip((tg[1:] * tg[:-1]).sum(1), -1.0, 1.0)), 0.0]
        ang = np.maximum(ang, np.r_[0.0, ang[:-1]])
        R = (d[1] - d[0]) * _LEN / np.maximum(ang, 1e-9)
        a = np.array([itp(x, W_S) * 0.5 for x in d])
        b = np.array([itp(x, TH_S) * 0.5 for x in d])
        cap = np.arcsin(np.clip((0.8 * R - b) / a, 0.0, 1.0))
        cap = minimum_filter1d(cap, size=141)         # hold it low +-0.06 of the length
        cap = gaussian_filter1d(cap, sigma=40)        # ...and ease in/out over ~0.1
        _TWCAP.update(key=key, d=d, cap=cap)
    return float(np.interp(s, _TWCAP["d"], _TWCAP["cap"]))


def _frame(s):
    C = Vector(*center(s))
    T = Vector(*tangent(s))
    wdir = Vector(0, 1, 0)
    tdir = T.cross(wdir)
    tdir = tdir.normalized() if tdir.Length > 1e-6 else Vector(0, 0, 1)
    tw = math.radians(itp(s, TWIST_S))          # spiral fibre
    cap = _twist_cap(s)                          # ...but never so much that the
    if abs(tw) > cap:                            # inner edge folds over a tight curl
        tw = math.copysign(cap, tw)
    if abs(tw) > 1e-4:
        cs, sn = math.cos(tw), math.sin(tw)
        wdir, tdir = wdir * cs + tdir * sn, tdir * cs - wdir * sn
    return C, wdir, tdir


def _sec_z(s, cx, cz, fl_main, fl_foam, b, sw, lw, bw, top_sign, depth):
    z = cz * b
    if abs(cz) > 1e-6:
        # FLOWING LINES: pure longitudinal flutes, no cross-wave — the lines
        # trace the ribbon's own movement instead of breaking it into a
        # cell/cross-hatch pattern. Bold at the floor, calmer at the crown.
        flute_a = FLUTE_A0 + (FLUTE_A1 - FLUTE_A0) * depth ** 1.3     # depths -> surface
        foam = FOAM_A * max(0.0, depth - 0.30) ** 1.5                  # a fine accent line only near the top
        ripple = flute_a * fl_main + (foam * fl_foam if foam > 1e-6 else 0.0)
        # COMFORT: the contact zone (seat/back) keeps the same lines, just
        # noticeably quieter and capped, so nothing presses into a bone.
        contact = max(sw, lw, bw) if cz * top_sign > 0 else 0.0
        ripple *= (1.0 - 0.55 * contact)                # noticeable damping, texture still there
        cap = 0.8 * b * (1.0 - contact) + 2.2 * contact  # ceiling in contact zones ~2 mm
        ripple = max(-cap, min(cap, ripple))
        z += math.copysign(1.0, cz) * ripple
    if sw > 0 and cz * top_sign > 0:
        z -= top_sign * SEAT_DISH_LAT * sw * (1.0 - cx * cx)
    if lw > 0 and cz * top_sign > 0:
        z += top_sign * LUMBAR_BUMP * lw * (1.0 - cx * cx) ** 0.7
    return z


def wire_at(s, side=0):
    """side=0 the full section; -1/+1 only the left/right half (seam at
    cx=0), offset by FORK_SPLAY*fork_amt in the fork zone (forked foot)."""
    C, wdir, tdir = _frame(s)
    a = itp(s, W_S) * 0.5
    b = itp(s, TH_S) * 0.5
    fa = fork_amt(s)
    if fa > 0 and side == 0:                     # HERO: one continuous splayed pad (not a flipper)
        a = a * (1.0 - 0.55 * fa) + 168.0 * fa
        b = b * (1.0 - 0.55 * fa) + 24.0 * fa
    elif fa > 0:                                 # real part: the fork's narrow prong
        a = a * (1.0 - 0.66 * fa) + PRONG_PAD_HALF * fa
        b = b * (1.0 - 0.7 * fa) + PRONG_TH_END * 0.5 * fa
    sw, lw, bw = seat_win(s), lumbar_win(s), back_win(s)
    top_sign = 1.0 if tdir.z >= 0 else -1.0
    yoff = Vector(0, 1, 0) * (side * FORK_SPLAY * fa) if side else Vector(0, 0, 0)
    depth = _depth_frac(s)
    pts = []
    for cx, cz, fl_main, fl_foam in _SECT:
        if side < 0 and cx > 1e-6:
            continue
        if side > 0 and cx < -1e-6:
            continue
        z = _sec_z(s, cx, cz, fl_main, fl_foam, b, sw, lw, bw, top_sign, depth)
        pts.append(C + yoff + wdir * (cx * a) + tdir * z)
    return cq.Wire.makePolygon(pts + [pts[0]])


def loft(wires):
    for ruled in (False, True):
        try:
            c = cq.Solid.makeLoft(wires, ruled=ruled)
            if c is not None and c.isValid():
                return c
        except Exception:
            pass
    return None


def big(s):
    ss = s.Solids() if s is not None else []
    return max(ss, key=lambda x: abs(x.Volume())) if ss else s


def vol(s):
    try:
        return sum(abs(x.Volume()) for x in (s.Solids() if s is not None else []))
    except Exception:
        return 0.0


def cone(r0, r1, L, base, axis):
    return cq.Solid.makeCone(r0, r1, L, Vector(*base), Vector(*axis))


def frustum(p0, axis, r0, r1, L):
    """truncated cone from p0 along axis: radius r0 at p0, r1 at p0+axis*L."""
    if abs(r0 - r1) < 1e-3:
        return cq.Solid.makeCylinder(r0, L, Vector(*p0), Vector(*axis))
    return cq.Solid.makeCone(r0, r1, L, Vector(*p0), Vector(*axis))


def _inside(host, probe):
    """fraction of probe's volume that lies inside host."""
    pv = vol(probe)
    if host is None or pv <= 0:
        return 0.0
    try:
        return vol(host.intersect(probe)) / pv
    except Exception:
        return 0.0


def _try_bool(fn, old):
    """run a boolean; return (result, True) only if it is a valid solid that
    didn't collapse, else (old, False) -- no logging, the caller decides."""
    try:
        new = big(fn())
        if new is not None and not new.isValid():
            new = big(new.fix())
        if new is not None and new.isValid() and vol(new) > 0.7 * vol(old):
            return new, True
    except Exception:
        pass
    return old, False


def _checked(new, old, what):
    """keep a boolean result only if it is a valid solid that didn't collapse;
    otherwise repair it, or keep the previous shape and log the problem."""
    try:
        if new is not None and not new.isValid():
            new = big(new.fix())
    except Exception:
        pass
    ok = new is not None and new.isValid() and vol(new) > 0.7 * vol(old)
    if not ok:
        BUILD_PROBLEMS.append(f"{what}: boolean gave an invalid/collapsed solid, left out")
        return old
    return new


def y_half(sign, y0=0.0):
    """half-space y>=y0 (sign>0) or y<=y0."""
    if sign > 0:
        return cq.Solid.makeBox(4000, 2000, 4000, Vector(-2000, y0, -2000))
    return cq.Solid.makeBox(4000, 2000, 4000, Vector(-2000, y0 - 2000, -2000))


def cut_stations():
    d = np.linspace(0, 1, 1200)
    tg = np.array([tangent(s) for s in d])
    turn = np.r_[0.0, np.cumsum([
        math.acos(max(-1.0, min(1.0, float(np.dot(tg[i], tg[i - 1])))))
        for i in range(1, len(d))])]
    raw = [0.0]
    ls, lt = 0.0, 0.0
    for i, s in enumerate(d):
        if (s - ls) * _LEN >= SEG_MAX or (turn[i] - lt) >= TURN_MAX:
            if (s - raw[-1]) * _LEN >= MIN_SEG:
                raw.append(float(s)); ls, lt = s, turn[i]
    raw.append(1.0)
    # drop cuts too close to a corner (knee/lumbar stays whole, mid-segment)
    fb = FORBID / _LEN
    keep = [0.0]
    for s in raw[1:-1]:
        if any(abs(s - c) < fb for c in CORNERS):
            continue
        if s - keep[-1] >= MIN_SEG / _LEN:
            keep.append(s)
    if 1.0 - keep[-1] < MIN_SEG / _LEN and len(keep) > 1:
        keep[-1] = 1.0
    else:
        keep.append(1.0)
    # if a segment now exceeds SEG_MAX after dropping cuts, split it further
    out = [keep[0]]
    for a, b in zip(keep[:-1], keep[1:]):
        span = (b - a) * _LEN
        n = max(1, math.ceil(span / SEG_MAX))
        for j in range(1, n):
            out.append(a + (b - a) * j / n)
        out.append(b)
    # add extra cuts in the fork zone (shorter segments -> they fit the bed)
    out2 = []
    for a, b in zip(out[:-1], out[1:]):
        lim = FORK_SEG if (fork_amt(a) > 1e-3 or fork_amt(b) > 1e-3) else SEG_MAX
        n = max(1, math.ceil((b - a) * _LEN / lim))
        out2 += [a + (b - a) * j / n for j in range(n)]
    out2.append(1.0)
    out = sorted(set(round(x, 5) for x in out2))
    # merge cuts closer than the minimum (shorter allowed in the fork zone)
    fin = [out[0]]
    for s in out[1:]:
        mn = FORK_SEG * 0.7 if fork_amt(s) > 1e-3 else MIN_SEG
        if (s - fin[-1]) * _LEN < mn and s < 1.0 - 1e-6:
            continue
        fin.append(s)
    if fin[-1] < 1.0 - 1e-6:
        if (1.0 - fin[-1]) * _LEN < MIN_SEG and len(fin) > 1:
            fin[-1] = 1.0
        else:
            fin.append(1.0)
    return fin


LABEL_H = 7.0    # mm, id-label text height
LABEL_D = 0.7    # mm, how far the label stands proud of the flat cut face


def _label_solid(s, side, text, trailing):
    """A small raised ID label on the flat cut face at s, offset clear of
    the tenon/pin — sits INSIDE the glued joint once assembled (or on a
    non-fit cut for split halves), so it never shows on the finished chair.
    Lets a builder match a loose printed part to the assembly diagram.
    Returns None (skip silently) if there isn't comfortably enough flat
    area for it — a missing label beats a broken export."""
    Cc = center(s)
    _, wdir, tdir = _frame(s)
    ne = np.array(tangent(s)); ne = ne / (np.linalg.norm(ne) + 1e-9)
    if not trailing:
        ne = -ne
    a = itp(s, W_S) * 0.5
    off = max(TEN_R + 10.0, TEN_R + 0.35 * a)
    if off > a - 9.0:
        return None
    if side < 0:
        off = -off
    wv = np.array([wdir.x, wdir.y, wdir.z])
    base = Cc + wv * off
    try:
        pln = cq.Plane(origin=tuple(base), xDir=tuple(wv), normal=tuple(ne))
        lbl = cq.Workplane(pln).text(text, LABEL_H, LABEL_D, combine=False,
                                     halign="center", valign="center",
                                     font="Arial")
        return lbl.val() if hasattr(lbl, "val") else lbl
    except Exception:
        return None


def seg_turn(s0, s1):
    d = np.linspace(s0, s1, 30)
    tg = [tangent(s) for s in d]
    return sum(math.acos(max(-1.0, min(1.0, float(np.dot(tg[i], tg[i - 1])))))
               for i in range(1, len(tg)))


def _loft_seg(s0, s1, side):
    n = max(6, int((s1 - s0) * _LEN / 12) + 1)
    sol = big(loft([wire_at(s, side) for s in np.linspace(s0, s1, n)]))
    return sol if (sol is not None and vol(sol) > 500.0) else None


def build():
    cuts = cut_stations()
    nseg = len(cuts) - 1

    def split_here(k):
        if fork_amt(cuts[k]) > 1e-3 or fork_amt(cuts[k + 1]) > 1e-3:
            return True
        wmax = max(itp(cuts[k] + (cuts[k + 1] - cuts[k]) * t, W_S)
                   for t in (0.0, 0.25, 0.5, 0.75, 1.0))
        return wmax > 200.0

    # 1) half-solids (side -1/+1) or a single piece (side 0)
    seg = {}                       # k -> {side: solid}
    for k in range(nseg):
        sides = (-1, 1) if split_here(k) else (0,)
        seg[k] = {}
        for sd in sides:
            sol = _loft_seg(cuts[k], cuts[k + 1], sd)
            if sol is None:
                print(f"  !! segment {k} side {sd} loft failed")
            seg[k][sd] = sol
    raw = {k: dict(v) for k, v in seg.items()}   # untouched lofts, for checks

    # 2) crosswise conical tenons at every internal cut.
    #    The tenon is fused onto seg A and PROTRUDES past the cut plane into
    #    a matching socket in seg B. Only a short root (TEN_ROOT) sits inside
    #    A -- an earlier version buried half the cone (22 mm) inside A, and on
    #    curved / tapering segments that buried half punched out through A's
    #    side or bottom (visible "second peg"), or collided with the socket at
    #    A's other end (crown segment: the whole body was lost, only a cone
    #    was left). Every joint is now also checked by VOLUME: the socket must
    #    lie inside B, the root inside A, and the protruding peg must not run
    #    into A itself; if not, the peg is shortened / thinned until it fits.
    lj = next((j for j in range(nseg) if cuts[j] <= _LUMB <= cuts[j + 1]), 1)
    pin_j = {0, nseg - 1, max(1, lj), min(nseg - 1, lj + 1)}
    pins = []
    global JOINT_REPORT, BUILD_PROBLEMS, JOINT_GEOM
    JOINT_REPORT, BUILD_PROBLEMS, JOINT_GEOM = [], [], []
    try:
        from shapely.geometry import Polygon, Point
    except Exception:
        Polygon = Point = None

    def _room(pts, cc, ax):
        """true min distance from cc to the edge of the section polygon,
        measured in the plane perpendicular to ax (negative = outside)."""
        tmp = np.array([0.0, 0.0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        uu = np.cross(ax, tmp); uu /= (np.linalg.norm(uu) + 1e-9)
        vv = np.cross(ax, uu)
        rel = pts - cc
        pu, pv = rel @ uu, rel @ vv
        if Polygon is not None:
            try:
                poly = Polygon(np.column_stack([pu, pv])).buffer(0)
                d = poly.exterior.distance(Point(0.0, 0.0))
                return d if poly.contains(Point(0.0, 0.0)) else -d
            except Exception:
                pass
        return float(np.hypot(pu, pv).min())

    def _fit_peg(cc, ax, r_cut, slope, P, host_root, host_sock, own_body, name, keep_out=()):
        """shrink the peg (length P, radius r_cut at the joint plane) until:
        socket inside host_sock, root inside host_root, peg clear of own_body,
        and the socket clear of keep_out (the zone at the neighbour's OTHER
        end where its own peg root will sit -- on a tight curl, like the
        crown, the two joints of one part are only mm apart inside it).
        Returns (peg_solid, socket_solid, r_cut, P, ok)."""
        ok = False
        for _ in range(10):
            tip = max(2.5, r_cut - slope * P)
            peg = frustum(cc - ax * TEN_ROOT, ax, r_cut + slope * TEN_ROOT, tip, P + TEN_ROOT)
            prot = frustum(cc, ax, r_cut, tip, P)
            root = frustum(cc - ax * TEN_ROOT, ax, r_cut + slope * TEN_ROOT, r_cut, TEN_ROOT)
            sock = frustum(cc - ax * 0.5, ax, r_cut + slope * 0.5 + TEN_CLR,
                           max(2.5, r_cut - slope * (P + SOCK_EXTRA)) + TEN_CLR, P + 0.5 + SOCK_EXTRA)
            probe = frustum(cc + ax * 0.3, ax, r_cut + TEN_CLR,
                            max(2.5, r_cut - slope * (P + SOCK_EXTRA)) + TEN_CLR, P + SOCK_EXTRA - 0.3)
            f_sock = sum(_inside(h, probe) for h in host_sock)
            f_root = sum(_inside(h, root) for h in host_root)
            f_own = sum(_inside(h, prot) for h in own_body)
            f_keep = sum(_inside(k, sock) for k in keep_out)
            if f_sock > 0.985 and f_root > 0.97 and f_own < 0.01 and f_keep < 0.002:
                ok = True
                break
            P *= 0.85
            r_cut = max(4.0, r_cut * 0.92)
        why = (f"socket {f_sock:.2f}, root {f_root:.2f}, self {f_own:.2f}, far-end {f_keep:.3f}")
        return peg, sock, r_cut, P, ok, why

    for c in range(1, nseg):                     # cut between seg c-1 and seg c
        ne = np.array(tangent(cuts[c])); ne = ne / (np.linalg.norm(ne) + 1e-9)
        A, B = seg[c - 1], seg[c]
        want_pin = (c in pin_j and fork_amt(cuts[c]) < 1e-3)
        b_raw = [raw[c][kk] for kk in B if raw[c][kk] is not None]
        for sda, ap in list(A.items()):
            if ap is None:
                continue
            # peg centre = true centroid of THIS side's cut-face profile
            cut_pts = np.array([v.toTuple() for v in wire_at(cuts[c], sda).Vertices()])
            cc = cut_pts.mean(axis=0)
            th_loc = itp(cuts[c], TH_S)
            tr = min(TEN_R, max(7.0, 0.38 * th_loc))
            tr = min(tr, max(5.0, _room(cut_pts, cc, ne) - 3.0))
            slope = (TEN_R - TEN_TIP) / TEN_L
            r_cut = tr - slope * TEN_L * 0.5            # radius at the joint plane
            name = f"cut {c} (SEG_{c-1:02d}{ {-1:'L',1:'R',0:''}[sda] } -> SEG_{c:02d})"
            keep = []
            if c + 1 < nseg:                          # B's far end is a joint too
                nf = np.array(tangent(cuts[c + 1])); nf = nf / (np.linalg.norm(nf) + 1e-9)
                for kb in B:
                    if B[kb] is None:
                        continue
                    cf = np.array([v.toTuple() for v in wire_at(cuts[c + 1], kb).Vertices()]).mean(axis=0)
                    keep.append(cq.Solid.makeCylinder(TEN_R + 3.0, TEN_ROOT + 3.0,
                                                      Vector(*(cf - nf * (TEN_ROOT + 3.0))), Vector(*nf)))
            peg, sock, r_cut, P, ok, why = _fit_peg(
                cc, ne, r_cut, slope, TEN_L * 0.5,
                host_root=[A[sda]], host_sock=b_raw,
                own_body=[raw[c - 1][sda]], name=name, keep_out=keep)
            if not ok:
                if want_pin:           # a load-path joint MUST get its peg + pin
                    BUILD_PROBLEMS.append(f"{name}: no room for the peg on a load-path joint ({why})")
                else:
                    # no physical room (e.g. the inner side of the crown curl):
                    # this half is joined by its full glued face only; the other
                    # half + the L/R seam peg keep the joint aligned
                    JOINT_REPORT.append((name + " -> glued face only, no room for a peg", 0.0, 0.0, True))
                continue
            newA, fused = _try_bool(lambda: A[sda].fuse(peg), A[sda])
            if not fused:
                if want_pin:
                    BUILD_PROBLEMS.append(f"{name}: peg could not be fused cleanly on a load-path joint")
                else:
                    JOINT_REPORT.append((name + " -> glued face only (the CAD kernel can't fuse a peg "
                                         "cleanly onto this tightly curled part)", 0.0, 0.0, True))
                continue                      # no peg -> no socket either
            A[sda] = newA
            JOINT_REPORT.append((name, r_cut, P, ok))
            JOINT_GEOM.append((name, peg, sock, cc, ne, (c - 1, sda),
                               [(c, kb) for kb in B if B[kb] is not None]))
            # socket goes into EVERY half of B it touches: when a single piece
            # meets a split pair (or vice versa) the peg straddles the L/R seam,
            # and both halves need their share of the hole -- otherwise the
            # other half physically blocks the peg.
            for kb in list(B):
                if B[kb] is None:
                    continue
                try:
                    B[kb] = _checked(big(B[kb].cut(sock)), B[kb], name + " socket")
                except Exception:
                    BUILD_PROBLEMS.append(name + ": socket cut failed")
            # dia 10 PIN through socket + peg -> the peg cannot be pulled out
            if want_pin:
                pax = np.cross(ne, [0.0, 0.0, 1.0])
                if np.linalg.norm(pax) < 1e-6:
                    pax = np.array([0.0, 1.0, 0.0])
                pax = pax / (np.linalg.norm(pax) + 1e-9)
                pp = cc + ne * (P * PIN_POS)
                ph = cq.Solid.makeCylinder(PIN_R + PIN_CLR, 400,
                                           Vector(*(pp - pax * 200.0)), Vector(*pax))
                # the hole runs across the full width, so it goes through every
                # half it crosses (a pin must never collide with the neighbour)
                for grp in (A, B):
                    for kk in list(grp):
                        if grp[kk] is None:
                            continue
                        try: grp[kk] = _checked(big(grp[kk].cut(ph)), grp[kk], name + " pin hole")
                        except Exception: pass
                pins.append(cq.Solid.makeCylinder(PIN_R, 150,
                            Vector(*(pp - pax * 75.0)), Vector(*pax)))

    # 3) lengthwise (L/R) tenon on the seam -- only where the two halves'
    #    seam faces actually coincide (no fork splay anywhere on the segment).
    #    Axis = the section's own width direction (it twists with TWIST_S),
    #    centred on the seam face itself, radius limited by the local
    #    thickness -- the old fixed Y-axis, 12 mm radius peg was thicker
    #    than the backrest in places and broke out through its faces.
    lslope = (LTEN_R - LTEN_TIP) / LTEN_L
    for k in range(nseg):
        if not (-1 in seg[k] and 1 in seg[k]):
            continue
        if max(fork_amt(cuts[k]), fork_amt(cuts[k + 1])) > 1e-3:
            continue
        if seg[k][-1] is None or seg[k][1] is None:
            continue
        smid = 0.5 * (cuts[k] + cuts[k + 1])
        C, wv, tv = _frame(smid)
        C = np.array(C.toTuple()); w = np.array(wv.toTuple()); t = np.array(tv.toTuple())
        pts = np.array([v.toTuple() for v in wire_at(smid, -1).Vertices()])
        wc = (pts - C) @ w
        seam = pts[wc >= wc.max() - 0.5]              # the L half's seam edge
        if len(seam) < 2:
            continue
        zs = (seam - C) @ t
        cs = C + w * wc.max() + t * 0.5 * (zs.min() + zs.max())
        half = 0.5 * (zs.max() - zs.min())
        r_seam = min(LTEN_R - lslope * LTEN_L * 0.5, half - 3.0)
        name = f"seam SEG_{k:02d} L->R"
        if r_seam < 4.0:
            JOINT_REPORT.append((name + " (too thin: glued face only)", 0.0, 0.0, True))
            continue
        peg, sock, r_seam, P, ok, why = _fit_peg(
            cs, w, r_seam, lslope, LTEN_L * 0.5,
            host_root=[seg[k][-1]], host_sock=[seg[k][1]],
            own_body=[raw[k][-1]], name=name)
        if not ok:
            JOINT_REPORT.append((name + " -> glued face only, no room for a peg", 0.0, 0.0, True))
            continue
        newL, fused = _try_bool(lambda: seg[k][-1].fuse(peg), seg[k][-1])
        if not fused:
            JOINT_REPORT.append((name + " -> glued face only (peg can't be fused cleanly here)", 0.0, 0.0, True))
            continue
        seg[k][-1] = newL
        JOINT_REPORT.append((name, r_seam, P, ok))
        JOINT_GEOM.append((name, peg, sock, cs, w, (k, -1), [(k, 1)]))
        try:
            seg[k][1] = _checked(big(seg[k][1].cut(sock)), seg[k][1], name + " socket")
        except Exception:
            BUILD_PROBLEMS.append(name + ": socket cut failed")

    # 4) output + a final sanity gate on every part: valid solid, and its
    #    volume still close to its own raw loft (a joint may add a peg or
    #    remove a socket -- it must never eat the part itself)
    out = []
    for k in range(nseg):
        vert = seg_turn(cuts[k], cuts[k + 1]) > VERT_TURN
        for sd, sol in seg[k].items():
            if sol is None or vol(sol) < 500.0:
                continue
            tag = {-1: "L", 1: "R", 0: ""}[sd]
            v0 = vol(raw[k][sd]) if raw[k].get(sd) is not None else 0.0
            ratio = vol(sol) / v0 if v0 > 0 else 1.0
            if not sol.isValid():
                BUILD_PROBLEMS.append(f"SEG_{k:02d}{tag}: invalid solid after joints")
            if not (0.80 <= ratio <= 1.25):
                BUILD_PROBLEMS.append(f"SEG_{k:02d}{tag}: volume {ratio:.0%} of its raw loft")
            out.append((f"SEG_{k:02d}{tag}", sol, vert, k, sd))
    return out, pins, cuts, pin_j


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith((".stl", ".brep")):
            os.remove(os.path.join(OUT, f))

    # ── automatic safety gate — re-derives the load-path margins LIVE from
    # the current W_S/TH_S tables (manta_strength_check.py imports this same
    # module, so it always sees the parameters actually in effect, never a
    # stale hand-copied number). If tuning the tables has pushed the weakest
    # joint below the intended safety factor, stop here — before anything is
    # exported — instead of silently handing back an unsafe STL.
    import manta_strength_check as _sc
    _margin, _where = _sc.worst_margin()
    print(f"\nstrength check — weakest: {_where}  ({_margin:.2f}x)   "
          f"[full report: python manta_strength_check.py]")
    if _margin < 1.0:
        raise SystemExit(
            f"\n!! REFUSING TO EXPORT: '{_where}' is at {_margin:.2f}x, "
            f"below the intended safety factor (SF={_sc.SF} already applied "
            f"in the allowable). Increase the width/thickness table near "
            f"this location (or reduce INFILL's assumption) and try again.\n")

    items, pins, cuts, pin_j = build()
    nseg = len(cuts) - 1

    # ── geometry gate: every joint's peg + socket was volume-checked inside
    # build(); any part that came out invalid or lost/gained volume stops the
    # export here, the same way a failed strength check does.
    shrunk = [(n, r, p) for n, r, p, ok in JOINT_REPORT if ok and p > 0 and p < 21.9 and "seam" not in n]
    glued_only = [n for n, r, p, ok in JOINT_REPORT if "glued face only" in n]
    print(f"\njoints: {len(JOINT_REPORT)} checked, {len(shrunk)} crosswise pegs shortened to fit, "
          f"{len(glued_only)} glued face only")
    for n, r, p in shrunk:
        print(f"   {n}: peg r {r:.1f} mm, protrudes {p:.1f} mm")
    for n in glued_only:
        print(f"   {n}")
    if BUILD_PROBLEMS:
        raise SystemExit("\n!! REFUSING TO EXPORT -- joint geometry problems:\n   "
                         + "\n   ".join(BUILD_PROBLEMS) + "\n")

    # 220 sections keeps the coral/foam relief legible while staying well
    # under the 10 MB submission budget (the fine cell pattern bakes real
    # curvature into the loft, so STL tolerance alone can't shrink it —
    # only fewer sections can).
    ss = np.linspace(0, 1, 220)
    hv = [big(loft([wire_at(s, sd) for s in ss])) for sd in (-1, 1)]
    hv = [h for h in hv if h is not None]
    if hv:
        whole = cq.Compound.makeCompound(hv)
        cq.exporters.export(whole, f"{OUT}/MANTA_Chair.stl", tolerance=MESH_TOL, angularTolerance=MESH_ANG)
        bb = whole.BoundingBox()
        # clean halves for rendering (2 separate solids -> no seam/crack)
        for h, tag in zip(hv, ("L", "R")):
            hd = big(loft([wire_at(s, -1 if tag == "L" else 1) for s in np.linspace(0, 1, 460)]))
            cq.exporters.export(hd if hd is not None else h,
                                f"{OUT}/MANTA_Hero{tag}.stl", tolerance=0.06, angularTolerance=0.16)
        print(f"\nWHOLE RIBBON:  depth {bb.xlen:.0f}  width {bb.ylen:.0f}  height {bb.zlen:.0f} mm"
              f"   (axis {_LEN:.0f} mm - corners knee={_KNEE:.2f} lumbar={_LUMB:.2f})")

    print(f"\n{len(items)} parts + PIN\n")
    print(f"{'PART':10s}{'X':>7s}{'Y':>7s}{'Z':>7s}   note")
    laid, legend, bad = [], [], []
    gx, gy, col = 250.0, 260.0, 7      # 7 columns = matches the 49-slot board grid
    for idx, (nm, sol, vert, seg_k, seg_sd) in enumerate(items):
        if vol(sol) < 1000.0:
            print(f"{nm:10s}   (empty — skipping)"); continue
        trailing = seg_k < nseg - 1
        label_c = (seg_k + 1) if trailing else seg_k
        label_s = cuts[label_c]
        part_num = len(legend) + 1     # same 1..42 sequence as the board key / template cells
        # skip the 2 pin joints — the label offset doesn't account for the
        # pin hole there, avoid risking an overlap
        lbl = None if label_c in pin_j else _label_solid(
            label_s, seg_sd, str(part_num), trailing)
        if lbl is not None:
            try:
                sol = big(sol.fuse(lbl))
            except Exception:
                pass
        bb = sol.BoundingBox()
        dd = sorted([bb.xlen, bb.ylen, bb.zlen])
        fit = dd[0] <= BED[0] and dd[1] <= BED[1] and dd[2] <= BED[2]
        if not fit:
            fit = dd[0] <= 72 and dd[2] <= math.hypot(*BED[:2]) * 0.92
        if not fit:
            bad.append(nm)
        cq.exporters.export(sol, f"{OUT}/{nm}.stl", tolerance=STL_TOL, angularTolerance=STL_ANG)
        legend.append((nm, vert))
        r, c = divmod(idx, col)
        laid.append(sol.translate(Vector(c * gx - (bb.xmin + bb.xmax) / 2,
                                         -r * gy - (bb.ymin + bb.ymax) / 2, -bb.zmin)))
        print(f"{nm:10s}{bb.xlen:7.0f}{bb.ylen:7.0f}{bb.zlen:7.0f}   "
              f"{'DOES NOT FIT' if not fit else ('standing' if vert else '')}")

    if pins:
        cq.exporters.export(pins[0], f"{OUT}/PIN.stl", tolerance=0.2, angularTolerance=0.4)
        k = len(items); r, c = divmod(k, col); pb = pins[0].BoundingBox()
        laid.append(pins[0].translate(Vector(c * gx - (pb.xmin + pb.xmax) / 2,
                                             -r * gy - (pb.ymin + pb.ymax) / 2, -pb.zmin)))
        legend.append(("PIN", False))

    cq.exporters.export(cq.Compound.makeCompound(laid), f"{OUT}/MANTA_Assembly.stl",
                        tolerance=STL_TOL, angularTolerance=STL_ANG)

    nvert = sum(1 for _, v in legend if v)
    with open(f"{OUT}/PARTS_LIST.txt", "w", encoding="utf-8") as fh:
        fh.write(f"BOARD LEGEND  ({len(legend)} items, limit 49)\n")
        for i, (nm, v) in enumerate(legend, 1):
            q = f"{len(pins)}x" if nm == "PIN" else "1x"
            fh.write(f"{i:2d}. {nm:12s} {q}  {'[print STANDING, no supports]' if v else ''}\n")
        fh.write("\ncrosswise joint (baguette-cut): conical peg dia 27 at the face, 22 mm into the "
                 "neighbour's socket, + two-part epoxy on the whole face\n")
        fh.write("lengthwise joint (L/R seam): transverse peg up to dia 20 + epoxy\n")
        fh.write(f"PIN dia {2 * PIN_R:.0f}: {len(pins)}x, printed SOLID (100% infill), "
                 f"one on each side of the lumbar (the most loaded joint)\n")

    print(f"\nBOARD LEGEND: {len(legend)} items (limit 49)   standing: {nvert}")
    print("does not fit:", bad if bad else "none — all OK")
    print(f"{OUT}/MANTA_Chair.stl - MANTA_Assembly.stl - PARTS_LIST.txt")


if __name__ == "__main__":
    main()
