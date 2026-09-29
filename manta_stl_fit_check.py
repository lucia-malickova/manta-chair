# -*- coding: utf-8 -*-
"""MANTA -- fit check on the EXPORTED print files (what the slicer sees).

manta_joint_check.py checks the exact CAD shapes. But a printer gets STL
triangles: every round peg and hole becomes a polygon, and that can eat the
0.12 mm peg/socket clearance (at the old 0.45 mm export tolerance only
~0.05 mm was left, and a few pegs touched their socket). This measures, for
every joint, the smallest gap between the peg's surface in one exported
part and the socket's surface in its neighbour, and the same for the pins.

RUN:  python manta_stl_fit_check.py                  (competition parts)
      python manta_stl_fit_check.py manta_ribbon_personal
"""
import importlib
import sys

import numpy as np
import trimesh

MIN_GAP = 0.06       # mm that must survive the export: nominal 0.12 minus up to 0.03 of
                     # facet error on each surface. A test joint exported at 0.1 mm tolerance
                     # (i.e. with LESS clearance than this) already slid in with play.


def main(gen_name="manta_ribbon"):
    g = importlib.import_module(gen_name)
    items, pins, cuts, pin_j = g.build()
    name = {(k, sd): nm for nm, _, _, k, sd in items}
    load = {}

    def part(key):
        if key not in load:
            load[key] = trimesh.load(f"{g.OUT}/{name[key]}.stl")
        return load[key]

    fails, gaps = [], []
    for jn, peg, sock, cc, ax, a_key, b_keys in g.JOINT_GEOM:
        A, B = part(a_key), part(b_keys[0])
        # the peg surface in the exported A: its vertices AND points on its facets
        pts, _ = trimesh.sample.sample_surface(A, 60000)
        pts = np.vstack([pts, A.vertices])
        s = (pts - cc) @ ax
        # keep only points of A's STL that ARE the peg (within 0.1 mm of the
        # exact CAD peg surface), beyond the joint plane
        v, f = peg.tessellate(0.01, 0.05)
        pm = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
        rad = np.linalg.norm((pts - cc) - np.outer(s, ax), axis=1)
        cand = pts[(s > 0.3) & (rad < g.TEN_R + 1.0)]           # quick pre-filter
        if not len(cand):
            continue
        pp = cand[np.abs(trimesh.proximity.signed_distance(pm, cand)) < 0.1]
        if not len(pp):
            continue
        # skip the rim of a pin hole: the peg's hole and the socket's hole are
        # the same size and line up, so their rims sit ~0.07 mm apart by design
        if pins:
            keep = np.ones(len(pp), bool)
            for pn in pins:
                bb = pn.BoundingBox()
                lo = np.array([bb.xmin, bb.ymin, bb.zmin]) - 1.0
                hi = np.array([bb.xmax, bb.ymax, bb.zmax]) + 1.0
                inbox = np.all((pp > lo) & (pp < hi), axis=1)
                if inbox.any():
                    v, f = pn.tessellate(0.02, 0.05)
                    pm2 = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
                    dd = np.abs(trimesh.proximity.signed_distance(pm2, pp[inbox]))
                    idx = np.where(inbox)[0][dd < g.PIN_CLR + 0.6]
                    keep[idx] = False
            pp = pp[keep]
            if not len(pp):
                continue
        d = trimesh.proximity.signed_distance(B, pp)        # >0 = inside B material
        gap = -d.max()
        gaps.append((gap, jn))
        if gap < MIN_GAP:
            fails.append(f"{jn}: only {gap:+.3f} mm clearance left in the STL files")
    # pins: the pin surface vs every part it passes through
    try:
        pin_mesh = trimesh.load(f"{g.OUT}/PIN.stl")
        r_pin = (pin_mesh.extents[:2].max()) / 2
        print(f"pin STL radius {r_pin:.3f} mm vs hole {g.PIN_R + g.PIN_CLR:.3f} mm")
    except Exception:
        pass
    gaps.sort()
    print(f"\nMANTA STL fit check -- {gen_name}: {len(gaps)} joints")
    for gp, jn in gaps[:5]:
        print(f"   tightest: {gp:+.3f} mm  {jn}")
    if fails:
        print(f"\n!! {len(fails)} joint(s) below {MIN_GAP} mm clearance:")
        for f in fails:
            print("   " + f)
        sys.exit(1)
    print(f"\nALL PEGS KEEP >= {MIN_GAP} mm CLEARANCE in the exported print files.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "manta_ribbon")
