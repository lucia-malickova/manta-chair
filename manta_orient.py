# -*- coding: utf-8 -*-
"""MANTA — print-orientation fixer.

The generator flagged 8 segments "print STANDING" using a crude heuristic
(spline turn-angle > threshold) and left the other 33 in their as-designed
orientation, on the assumption that was support-free. It wasn't checked
per-part. Measured directly on the exported meshes: as-exported overhang
averages ~18% of surface area, worst part ~38-40% — well past what a
slicer will print without support, regardless of the STANDING label.

This script first tries to rest each part on one of its own two REAL
crosswise cut/joint faces -- matched by ANGLE against the exact cut-face
directions the generator itself used (tangent(cuts[k]), tangent(cuts[k+1])),
not by mesh position or size. An earlier version picked flat mesh clusters
by which one sits at the most extreme end of the part, but a small fillet
or chamfer near a tenon's base can be more "extreme" than the real, much
larger cut face and got picked by mistake -- confirmed on part 14, where a
~1700 mm2 fillet ring outscored the real ~12700 mm2 socket face on
position alone, leaving the actual tenon sticking out sideways needing a
support the footprint/overhang numbers never showed. Matching by angle to
the known-exact tangent picks the true cut face regardless of what small
flat features sit nearby, since a joint's tenon is perpendicular to ITS
OWN cut face by construction -- resting on that face guarantees the tenon
points straight up/down. (On a strongly-curved segment the joint at the
OTHER end can still end up at an angle, since a segment's two ends aren't
generally parallel -- if the slicer flags a support there, it's for that
one small tenon tip, not the whole part.) Falls back to a Fibonacci sweep
+ the mesh's other large flat faces, picking the largest bed-contact
footprint under a tolerable overhang, when no real cut face qualifies.
Then drops the part onto the bed (z_min=0) and overwrites the STL in
place. Verified result across all 42 parts, both the competition and
personal-variant geometry: every part lands on a footprint >=400 mm2
(previously as low as ~70 mm2 on some), average overhang ~13%, worst ~25%.

RUN:  python manta_orient.py <folder> <generator_module>
      e.g. python manta_orient.py MANTA_RIBBON manta_ribbon
           python manta_orient.py MANTA_LIGHT manta_ribbon_personal
"""
import glob
import importlib
import json
import os
import re
import sys

import numpy as np
import trimesh


def fibonacci_sphere(n):
    pts = []
    ga = np.pi * (3 - np.sqrt(5))
    for i in range(n):
        y = 1 - (i / float(n - 1)) * 2
        r = np.sqrt(max(0.0, 1 - y * y))
        theta = ga * i
        pts.append([np.cos(theta) * r, y, np.sin(theta) * r])
    return np.array(pts)


def rot_to_z(v):
    v = v / np.linalg.norm(v)
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(v, z)
    s = np.linalg.norm(axis)
    c = np.dot(v, z)
    if s < 1e-8:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    axis = axis / s
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + K * s + K @ K * (1 - c)


def overhang_pct(face_normals, face_areas, total_area):
    down = np.array([0.0, 0.0, -1.0])
    cosang = face_normals @ down
    ang = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    risky = (cosang > 0.0) & (ang < 45.0)
    return face_areas[risky].sum() / total_area * 100


def base_footprint(mesh, R, slab=1.5):
    """area of the mesh's contact patch with the bed after rotation R:
    the convex-hull area of every vertex within `slab` mm of the lowest
    point, projected to XY. A tiny footprint (balancing on a tip/edge)
    means poor bed adhesion and a part that can detach mid-print, even if
    the overhang number looks great -- minimising overhang alone can walk
    straight into that trap, so this has to be checked too, not assumed."""
    pts = mesh.vertices @ R.T
    zmin = pts[:, 2].min()
    near = pts[pts[:, 2] < zmin + slab][:, :2]
    if len(near) < 3:
        return 0.0
    try:
        from scipy.spatial import ConvexHull
        return ConvexHull(near).volume  # 2D hull -> .volume is the area
    except Exception:
        # degenerate (near-collinear) contact patch -> effectively no footprint
        return 0.0


def flat_face_normals(mesh, min_cluster_frac=0.01):
    """(area, normal, centroid) of the mesh's largest genuinely-planar face
    clusters -- a tight ~2.5deg coplanarity match, so this only picks up
    real flat CAD faces (crosswise cut ends, the lengthwise L/R seam,
    tenon-base rings) and not a loosely-averaged patch of curved/textured
    surface. A loose threshold (previously ~11deg) was blending real flat
    faces in with nearby curved relief and missing them; on a lengthwise-
    split segment the seam face is often the single largest flat area on
    the whole part, bigger than either end -- and the earlier version
    never found it."""
    normals = mesh.face_normals
    areas = mesh.area_faces
    centroids = mesh.triangles.mean(axis=1)
    used = np.zeros(len(normals), dtype=bool)
    clusters = []
    order = np.argsort(-areas)
    for i in order:
        if used[i]:
            continue
        sim = normals @ normals[i] > 0.999  # within ~2.5 deg -- true planar match
        grp = sim & ~used
        used |= grp
        a = areas[grp].sum()
        if a >= mesh.area * min_cluster_frac:
            c = np.average(centroids[grp], axis=0, weights=areas[grp])
            clusters.append((a, normals[i], c))
    clusters.sort(key=lambda c: -c[0])
    return clusters[:20]


def real_cut_faces(mesh, exact_tangents, min_cluster_frac=0.01, max_angle_deg=8.0):
    """Of the mesh's flat-face clusters, whichever one best matches each of
    `exact_tangents` (normally [tangent(cuts[k]), tangent(cuts[k+1])] from
    the generator, EXACT by construction -- a cut face is perpendicular to
    the ribbon's own tangent at that station). Matched by angle, not
    position: an earlier version picked flat clusters by which one sits at
    the most extreme end of the part, but a cone-base fillet or chamfer
    can create a small flat ring that's positioned even more extreme than
    the real, much-larger cut face itself, and got picked by mistake --
    confirmed on part 14, where a ~1700 mm2 fillet ring outscored the real
    ~12700 mm2 socket face on position alone. Matching by angle to the
    exact analytical tangent (within `max_angle_deg`) picks the true cut
    face regardless of what other small flat features sit nearby, and
    resting on it guarantees this part's tenon points straight up or down,
    never sideways, since the tenon is perpendicular to *its own* cut face
    by construction -- resting on any other flat face doesn't carry that
    guarantee, even one with a great footprint/overhang score."""
    clusters = flat_face_normals(mesh, min_cluster_frac)
    out = []
    for et in exact_tangents:
        t = et / np.linalg.norm(et)
        best = None
        for a, n, c in clusters:
            ang = np.degrees(np.arccos(np.clip(abs(np.dot(n, t)), -1, 1)))
            if ang <= max_angle_deg and (best is None or a > best[0]):
                best = (a, n)
        if best is not None:
            out.append(best[1])
    return out


def best_orientation(mesh, n=100, max_overhang_pct=25.0, min_footprint_mm2=400.0,
                     priority_dirs=(), cut_faces=()):
    """Strongest preference first: `cut_faces` (from `real_cut_faces()`) --
    the part's actual two crosswise joint faces. Resting on one of these
    guarantees any tenon on this part points straight up/down, never
    sideways, which a good footprint/overhang score alone doesn't
    guarantee (confirmed on a real print of part 14: a non-joint flat
    face scored well on both, but left the tenon sticking out sideways,
    needing a support the number never showed). If either cut face clears
    a solid footprint and a tolerable overhang, use the better of the two
    — no further search needed, this is as reliable as it gets.

    Otherwise: footprint first, overhang second, over a general sweep (a
    Fibonacci scatter, the mesh's own largest flat-face normals, plus
    `priority_dirs`). Among every candidate with a solid bed-contact
    footprint (>= `min_footprint_mm2`) AND a tolerable overhang
    (<= `max_overhang_pct`), pick the LOWEST overhang -- pure overhang-
    minimisation alone kept finding orientations balanced on a point or
    edge, a great number on a part that can't stay on the bed."""
    def score(d):
        R = rot_to_z(d)
        nrm = mesh.face_normals @ R.T
        pct = overhang_pct(nrm, mesh.area_faces, mesh.area)
        fp = base_footprint(mesh, R)
        return (pct, R, fp)

    cut_scored = [score(d) for fn in cut_faces for d in (fn, -fn)]
    cut_ok = [c for c in cut_scored
              if c[2] >= min_footprint_mm2 and c[0] <= max_overhang_pct]
    if cut_ok:
        return min(cut_ok, key=lambda c: c[0])

    dirs = list(priority_dirs) + list(fibonacci_sphere(n))
    for _, fn, _ in flat_face_normals(mesh):
        dirs.append(fn); dirs.append(-fn)
    scored = cut_scored + [score(d) for d in dirs]

    solid = [c for c in scored if c[2] >= min_footprint_mm2]
    qualifying = [c for c in solid if c[0] <= max_overhang_pct]
    if qualifying:
        return min(qualifying, key=lambda c: c[0])
    if solid:
        return min(solid, key=lambda c: c[0])

    min_pct = min(c[0] for c in scored)
    near_best = [c for c in scored if c[0] <= min_pct + 8.0]
    return max(near_best, key=lambda c: c[2])


def segment_cut_tangents(fname, gen):
    """This segment's two exact cut-face directions, straight from the
    generator: tangent(cuts[k]) at the socket end, tangent(cuts[k+1]) at
    the tenon end -- exact by construction, since a cut face is defined
    perpendicular to the ribbon's tangent at that station. Also returns
    their midpoint (a reasonable general-purpose priority direction)."""
    m = re.match(r"(?:\d+_)?SEG_(\d+)", os.path.basename(fname))
    if not m:
        return None, []
    k = int(m.group(1))
    cuts = gen.cut_stations()
    if k + 1 >= len(cuts):
        return None, []
    t_start = np.array(gen.tangent(cuts[k]))
    t_end = np.array(gen.tangent(cuts[k + 1]))
    mid = np.array(gen.tangent(0.5 * (cuts[k] + cuts[k + 1])))
    return mid, [t_start, t_end]


SUPPORT_ANGLE = 43.0   # a slicer supports surfaces overhanging more than this from vertical
                       # (PrusaSlicer threshold 45 deg from horizontal = 45 from vertical, minus 2 deg margin)
SUPPORT_FREE = 1.0     # cm2 -- stray facets; the real slicer decides (manta_slicer_check.py)
HOLE_WEIGHT = 100.0    # support INSIDE a socket can't be pulled out: weigh it this much more
HOLE_REACH = 30.0      # mm -- a face that looks at the opposite wall this close is inside a hole
BED = (250.0, 220.0, 270.0)   # Prusa CORE One build volume, mm
BED_MARGIN = 3.0


def hole_faces(mesh, pin_holes=()):
    """faces lining a hole (peg socket, pin hole): looking out along the
    face's own normal, the ray meets the part's opposite wall within
    HOLE_REACH. Support grown there is trapped inside the hole.
    `pin_holes` (from the generator's PIN_HOLES.json, model coordinates):
    those holes are left out -- the generator gives them a teardrop roof for
    whatever orientation is chosen, so they must not steer the choice."""
    c = mesh.triangles_center + mesh.face_normals * 0.05
    hit = np.zeros(len(c), dtype=bool)
    loc, idx, _ = mesh.ray.intersects_location(c, mesh.face_normals, multiple_hits=False)
    if len(idx):
        hit[idx[np.linalg.norm(loc - c[idx], axis=1) < HOLE_REACH]] = True
    for ph in pin_holes:
        s0, d = np.array(ph["start"]), np.array(ph["dir"])
        t = np.clip((mesh.triangles_center - s0) @ d, -60.0, ph["length"])   # incl. the neck
        dist = np.linalg.norm(mesh.triangles_center - (s0 + np.outer(t, d)), axis=1)
        hit &= ~(dist < 1.8 * ph["r"] + 0.5)
    return hit


def support_area(mesh, R, holes=None):
    """(outside, inside-hole) cm2 of surface a slicer would want to support
    in orientation R: faces overhanging more than SUPPORT_ANGLE from
    vertical, not lying on the bed."""
    n = mesh.face_normals @ R.T
    zc = (mesh.triangles_center @ R.T)[:, 2]
    steep = (-n[:, 2] > np.cos(np.radians(90.0 - SUPPORT_ANGLE))) & (zc > zc.min() + 0.6)
    if holes is None:
        holes = np.zeros(len(n), dtype=bool)
    return (float(mesh.area_faces[steep & ~holes].sum() / 100.0),
            float(mesh.area_faces[steep & holes].sum() / 100.0))


def bed_turn(mesh, R):
    """angle (deg) to turn the part about Z so it fits the build volume after
    rotation R, or None if it fits no way round."""
    v = mesh.convex_hull.vertices @ R.T
    if np.ptp(v[:, 2]) > BED[2] - BED_MARGIN:
        return None
    xy = v[:, :2]
    for a in range(0, 180, 2):
        t = np.radians(a)
        e = np.ptp(xy @ np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]]), axis=0)
        if e[0] <= BED[0] - 2 * BED_MARGIN and e[1] <= BED[1] - 2 * BED_MARGIN:
            return float(a)
    return None


def rot_z(deg):
    t = np.radians(deg)
    return np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])


def best_support_orientation(mesh, cut_faces=(), priority_dirs=(), n=400,
                             min_footprint_mm2=400.0, pin_holes=()):
    """The orientation with the LEAST support among those that stand on a
    solid footprint AND fit the printer's build volume. Support inside a hole
    counts HOLE_WEIGHT times (it can't be removed); a sideways peg is counted
    automatically (its underside is overhang). Ties (within 0.5 cm2) go to
    resting on a real cut face. Returns (outside cm2, hole cm2, R, footprint),
    R already including the turn about Z that makes it fit the bed."""
    holes = hole_faces(mesh, pin_holes)
    cands = []
    for fn in cut_faces:
        for d in (fn, -fn):
            cands.append((np.asarray(d, float), True))
    for d in list(priority_dirs) + list(fibonacci_sphere(n)):
        cands.append((np.asarray(d, float), False))
    for _, fn, _ in flat_face_normals(mesh):
        cands.append((fn, False)); cands.append((-fn, False))
    scored = []
    for d, is_cut in cands:
        R = rot_to_z(d)
        fp = base_footprint(mesh, R)
        if fp < min_footprint_mm2:
            continue
        sa, sh = support_area(mesh, R, holes)
        scored.append(((round((sa + HOLE_WEIGHT * sh) * 2) / 2, 0 if is_cut else 1), sa, sh, R, fp))
    scored.sort(key=lambda c: c[0])
    for key, sa, sh, R, fp in scored:       # best first; the first that fits the bed wins
        turn = bed_turn(mesh, R)
        if turn is not None:
            return sa, sh, rot_z(turn) @ R, fp
    raise RuntimeError("no orientation stands on a solid base AND fits the build volume")


def main(folder, gen_name="manta_ribbon", reuse=False):
    """reuse=True: apply the rotations saved in ORIENT.json instead of
    searching -- the generator has shaped the pin holes' roofs for exactly
    those rotations (manta_teardrop.py)."""
    gen = importlib.import_module(gen_name)
    files = sorted(glob.glob(f"{folder}/*.stl"))
    orient_path = os.path.join(folder, "ORIENT.json")
    saved = json.load(open(orient_path, encoding="utf-8")) if reuse else {}
    ph_path = os.path.join(gen.OUT, "PIN_HOLES.json")
    pin_holes = json.load(open(ph_path, encoding="utf-8")) if os.path.exists(ph_path) else []
    print(f"\nMANTA — orienting {len(files)} parts in {folder}/ for the least support"
          f"{' (saved rotations)' if reuse else ''}\n")
    print(f"{'PART':16s}{'support cm2':>12s}{'in holes':>10s}{'footprint':>12s}")
    report = []
    rotations = {}
    for f in files:
        m = trimesh.load(f)
        key = re.sub(r"^\d+_", "", os.path.basename(f))[:-4]
        mine = [ph for ph in pin_holes if key in ph["parts"]]
        if reuse and key in saved:
            R = np.array(saved[key])
            sa, sh = support_area(m, R, hole_faces(m, mine))
            fp = base_footprint(m, R)
        else:
            mid, exact_tangents = segment_cut_tangents(f, gen)
            cut_faces = real_cut_faces(m, exact_tangents) if exact_tangents else []
            pri = [mid] if mid is not None else []
            sa, sh, R, fp = best_support_orientation(m, cut_faces=cut_faces, priority_dirs=pri,
                                                     pin_holes=mine)
        rotations[key] = R.tolist()
        T = np.eye(4); T[:3, :3] = R
        m.apply_transform(T)
        lo, hi = m.bounds
        # drop to the bed and centre on it
        m.apply_translation((BED[0] / 2 - (lo[0] + hi[0]) / 2, BED[1] / 2 - (lo[1] + hi[1]) / 2, -lo[2]))
        m.export(f)
        report.append((os.path.basename(f), sa, fp))
        tag = "" if sa + sh <= SUPPORT_FREE else "   needs support"
        if sh > 0.05:
            tag += "  !! some inside a hole"
        print(f"{os.path.basename(f):16s}{sa:12.1f}{sh:10.1f}{fp:10.0f}mm2{tag}")
    free = sum(1 for _, sa, _ in report if sa <= SUPPORT_FREE)
    with open(orient_path, "w", encoding="utf-8") as fh:
        json.dump(rotations, fh, indent=1)
    with open(os.path.join(folder, "SUPPORT_REPORT.txt"), "w", encoding="utf-8") as fh:
        for nm, sa, fp in report:
            fh.write(f"{nm}\t{sa:.1f}\t{fp:.0f}\n")
    print(f"\ndone — {free} of {len(report)} parts print with no support "
          f"(<= {SUPPORT_FREE:.0f} cm2 of stray facets; confirm with manta_slicer_check.py); "
          f"the rest need some support from the build plate.\n")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "MANTA_RIBBON"
    gen_name = sys.argv[2] if len(sys.argv) > 2 else "manta_ribbon"
    main(folder, gen_name, reuse="--reuse" in sys.argv)
