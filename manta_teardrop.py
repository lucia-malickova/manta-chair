# -*- coding: utf-8 -*-
"""MANTA -- pin holes that print WITHOUT support inside, in any orientation.

A pin hole always runs across a peg, so when a part lies with its pegs and
sockets upright, its pin hole is sideways or slanted -- and a round sideways
hole has a flat ceiling a slicer fills with support that can't be pulled out
of a blind 11 mm hole. The fix FDM printers use: a TEARDROP hole, a round
hole with a pointed roof, the roof pointing UP in the print. When the blind
end faces up, it closes in a "tent": every point of the end section is joined
to one apex straight above it, so every surface there is >= 60 deg steep and
the very top is a single point (like a drilled hole's tip).

That needs to know which way is up for each part, so the pipeline is:
  generator -> manta_orient.py (writes ORIENT.json: each part's rotation)
  -> generator again (reads ORIENT.json, points each roof up)
  -> manta_orient.py --reuse (same rotations) -> manta_slicer_check.py
Without ORIENT.json the hole ends in a plain 60-degree point along its axis.
"""
import json
import math
import os

import numpy as np
import cadquery as cq
from cadquery import Vector

ROOF_DEG = 55.0      # roof faces this steep from horizontal (slicer threshold 45 + margin)
TENT_DEG = 60.0      # the blind-end tent: every surface at least this steep
ROOF_MIN = 0.2       # roof only when the hole leans this much off vertical (sin of ~12 deg)


def load_ups(path):
    """{part name: its print 'up' as a direction in the model's coordinates}"""
    if not path or not os.path.exists(path):
        return {}
    R = json.load(open(path, encoding="utf-8"))
    return {nm: np.array(m).T @ np.array([0.0, 0.0, 1.0]) for nm, m in R.items()}


def _frame(d, up):
    """(d, u, x, y): y = 'up' within the hole's cross-section (None if the
    hole is near-vertical), x completes the frame."""
    d = np.asarray(d, float) / np.linalg.norm(d)
    u = np.asarray(up, float) / np.linalg.norm(up)
    up_p = u - (u @ d) * d
    if np.linalg.norm(up_p) < ROOF_MIN:
        x = np.cross(d, [1.0, 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1.0, 0])
        x /= np.linalg.norm(x)
        return d, u, x, np.cross(d, x), False
    y = up_p / np.linalg.norm(up_p)
    return d, u, np.cross(y, d), y, True


def _outline(r, roof):
    """2D outline of the cross-section: circle, or circle + roof (teardrop)"""
    if not roof:
        return [(r * math.cos(t), r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
    a = math.radians(ROOF_DEG)
    arc = np.linspace(math.pi / 2 - a, math.pi / 2 + a - 2 * math.pi, 56)   # the round part, under the roof
    pts = [(r * math.cos(t), r * math.sin(t)) for t in arc]
    return pts + [(0.0, r / math.cos(a))]


def _section_wire(origin, x, d, r, roof, scale=1.0):
    pl = cq.Plane(origin=Vector(*origin), xDir=Vector(*x), normal=Vector(*d))
    a = math.radians(ROOF_DEG)
    s = scale
    wp = cq.Workplane(pl)
    if not roof:
        return wp.circle(r * s).wires().val()
    p1 = (r * s * math.sin(a), r * s * math.cos(a))
    p2 = (-p1[0], p1[1])
    return (wp.moveTo(*p1).threePointArc((0.0, -r * s), p2)
            .lineTo(0.0, r * s / math.cos(a)).close().wires().val())


def tent(r, d, up):
    """(apex height above the end centre, reach past the end along -d);
    (None, 0) when the blind end faces down (it is then a floor)."""
    d, u, x, y, roof = _frame(d, up)
    if u @ (-d) <= 0.05:
        return None, 0.0
    sec = np.array([p0 * x + p1 * y for p0, p1 in _outline(r, roof)])
    dl = sec @ u
    rho = np.linalg.norm(sec - np.outer(dl, u), axis=1)
    h = float(np.max(rho * math.tan(math.radians(TENT_DEG)) + dl)) + 0.3
    return h, h * float(u @ (-d))


def cap_extent(r, d, up):
    return tent(r, d, up)[1], None


def socket_void(p0, ax, r0, r1, length, up):
    """a peg socket as a TAPERED teardrop: mouth at p0 (radius r0), running
    along unit `ax` for `length` to its blind end (radius r1). The roof points
    up in the print; a blind end that faces up closes in a tent. The same call
    with every radius grown by w is the socket offset by w (the roof lines are
    tangent to the circle), so it doubles as the 2 mm wall probe."""
    p0 = np.asarray(p0, float)
    ax = np.asarray(ax, float) / np.linalg.norm(ax)
    d = -ax                                         # _frame/tent: -d = toward the blind end
    _, u, x, y, roof = _frame(d, up)
    end = p0 + ax * length
    w0 = _section_wire(p0, x, d, r0, roof)
    w1 = _section_wire(end, x, d, r1, roof)
    void = cq.Solid.makeLoft([w0, w1], ruled=True)
    h, _ = tent(r1, d, up)
    if h is not None:
        w2 = _section_wire(end + u * h, x, d, r1, roof, scale=0.01)
        void = void.fuse(cq.Solid.makeLoft([w1, w2], ruled=True))
    return void.clean()


NECK_R = 3.5         # the pin hole narrows to this, and runs on out through the seam face
NECK_L = 21.0        # over this length: the taper is the pin's STOP, and at <= 10 deg off
                     # the axis it stays printable even when the narrow end faces up


def pin_hole_neck(stop, d, length, r, up, neck_to_seam):
    """the void for one pin, WITHOUT a blind end: the bore (radius r) runs
    from `stop` along unit `d` for `length`, out through the side face;
    from `stop` the other way it tapers over NECK_L to a narrow neck that
    runs on through the seam face (neck_to_seam = stop -> seam distance).
    The pin bottoms out in the taper. Nothing is closed, so nothing faces
    down as a ceiling, and nothing can poke out of the part. `up` = the
    part's print-up (teardrop roof), or None for a plain round hole."""
    stop = np.asarray(stop, float)
    d = np.asarray(d, float) / np.linalg.norm(d)
    if up is None:                                  # round sections, any x across the axis
        x = np.cross(d, [1.0, 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1.0, 0])
        x /= np.linalg.norm(x)
        roof = False
    else:
        _, _, x, _, roof = _frame(d, up)
    w_out = _section_wire(stop + d * length, x, d, r, roof)
    w_stop = _section_wire(stop, x, d, r, roof)
    w_neck = _section_wire(stop - d * NECK_L, x, d, NECK_R, roof)
    w_seam = _section_wire(stop - d * (neck_to_seam + 2.0), x, d, NECK_R, roof)
    bore = cq.Solid.makeLoft([w_stop, w_out], ruled=True)
    taper = cq.Solid.makeLoft([w_neck, w_stop], ruled=True)
    neck = cq.Solid.makeLoft([w_seam, w_neck], ruled=True)
    return bore.fuse(taper).fuse(neck).clean()


def pin_hole(start, d, length, r, up=None, tip_len=None):
    """the void for one pin: from `start` (the blind end) along unit `d` for
    `length` (out through the side face). `up` = the part's print-up in
    model coordinates (None -> plain 60-degree point along the axis)."""
    start = np.asarray(start, float)
    d = np.asarray(d, float) / np.linalg.norm(d)
    if up is None:
        hole = cq.Solid.makeCylinder(r, length, Vector(*start), Vector(*d))
        tip = cq.Solid.makeCone(r, 0.0, tip_len, Vector(*start), Vector(*(-d)))
        return hole.fuse(tip).clean()
    d, u, x, y, roof = _frame(d, up)
    w0 = _section_wire(start, x, d, r, roof)
    hole = cq.Solid.extrudeLinear(cq.Face.makeFromWires(w0), Vector(*(d * length)))
    h, _ = tent(r, d, up)
    if h is not None:
        apex = start + u * h
        w1 = _section_wire(apex, x, d, r, roof, scale=0.01)     # a speck at the apex
        cap = cq.Solid.makeLoft([w0, w1], ruled=True)
        hole = hole.fuse(cap)
    return hole.clean()
