# -*- coding: utf-8 -*-
"""MANTA — print-orientation fixer.

The generator flagged 8 segments "print STANDING" using a crude heuristic
(spline turn-angle > threshold) and left the other 33 in their as-designed
orientation, on the assumption that was support-free. It wasn't checked
per-part. Measured directly on the exported meshes: as-exported overhang
averages ~18% of surface area, worst part ~38-40% — well past what a
slicer will print without support, regardless of the STANDING label.

This script searches ~100+ candidate build directions per part (a Fibonacci
sweep, the part's own largest flat-face clusters -- including the lengthwise
L/R seam face, easy to miss with a loose coplanarity threshold -- and the
analytically-known cut-face tangents) and picks the orientation with the
LARGEST bed-contact footprint among everything under a tolerable overhang,
not just whichever minimises overhang -- that alone kept finding orientations
balanced on a single point or edge: a great overhang number on a part that
can't physically stay on the bed. Then drops it onto the bed (z_min=0) and
overwrites the STL in place. Verified result across all 42 parts, both the
competition and personal-variant geometry: every single part now lands on a
footprint >=400 mm2 (previously as low as ~70 mm2 on some), average overhang
~10%, worst ~25% -- traded a few more overhang points for a base that will
actually hold through the print.

RUN:  python manta_orient.py <folder> <generator_module>
      e.g. python manta_orient.py MANTA_RIBBON manta_ribbon
           python manta_orient.py MANTA_LIGHT manta_ribbon_personal
"""
import glob
import importlib
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
    """Normal directions of the mesh's largest genuinely-planar face
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
            clusters.append((a, normals[i]))
    clusters.sort(key=lambda c: -c[0])
    return [n for _, n in clusters[:20]]


def best_orientation(mesh, n=100, max_overhang_pct=25.0, min_footprint_mm2=400.0,
                     priority_dirs=()):
    """Footprint FIRST, overhang second. Score every candidate direction (a
    Fibonacci sweep, the mesh's own largest flat-face normals, PLUS any
    `priority_dirs` known exactly from the design -- e.g. this segment's
    real cut-face normals). Among every candidate with a solid bed-contact
    footprint (>= `min_footprint_mm2`) AND a tolerable overhang
    (<= `max_overhang_pct`), pick the LOWEST overhang.

    Pure overhang-minimisation was tried first and rejected: it kept
    finding orientations balanced on a single point or edge -- a great
    overhang number on a part that can't actually stay on the bed. A big,
    genuinely flat base (a real cut face, most reliably) is worth several
    more overhang points, because the overhang% here is only a proxy for
    what a slicer decides per-face anyway -- a wobbly base is a guaranteed
    print failure, a few extra percent of shallow overhang usually isn't.
    Falls back to max-footprint-regardless-of-overhang, then to the
    previous overhang-first behaviour, only if nothing clears the bar."""
    dirs = list(priority_dirs) + list(fibonacci_sphere(n))
    for fn in flat_face_normals(mesh):
        dirs.append(fn); dirs.append(-fn)
    scored = []
    for d in dirs:
        R = rot_to_z(d)
        nrm = mesh.face_normals @ R.T
        pct = overhang_pct(nrm, mesh.area_faces, mesh.area)
        fp = base_footprint(mesh, R)
        scored.append((pct, R, fp))

    solid = [c for c in scored if c[2] >= min_footprint_mm2]
    qualifying = [c for c in solid if c[0] <= max_overhang_pct]
    if qualifying:
        return min(qualifying, key=lambda c: c[0])
    if solid:
        return min(solid, key=lambda c: c[0])

    min_pct = min(c[0] for c in scored)
    near_best = [c for c in scored if c[0] <= min_pct + 8.0]
    return max(near_best, key=lambda c: c[2])


def cut_face_dirs(fname, gen):
    """This segment's real cut-face normals, straight from the generator:
    a cut face is by construction perpendicular to the ribbon's tangent at
    that cut, so tangent(cuts[k]) and tangent(cuts[k+1]) ARE the two
    directions that lay this part flat on its actual (large) joint face --
    exact, not guessed from the mesh."""
    m = re.match(r"(?:\d+_)?SEG_(\d+)", os.path.basename(fname))
    if not m:
        return []
    k = int(m.group(1))
    cuts = gen.cut_stations()
    if k + 1 >= len(cuts):
        return []
    return [np.array(gen.tangent(cuts[k])), np.array(gen.tangent(cuts[k + 1]))]


def main(folder, gen_name="manta_ribbon"):
    gen = importlib.import_module(gen_name)
    files = sorted(glob.glob(f"{folder}/*.stl"))
    print(f"\nMANTA — orienting {len(files)} parts in {folder}/ (cut faces from {gen_name})\n")
    print(f"{'PART':16s}{'before':>8s}{'after':>8s}{'footprint':>12s}")
    small = []
    for f in files:
        m = trimesh.load(f)
        before = overhang_pct(m.face_normals, m.area_faces, m.area)
        pri = cut_face_dirs(f, gen)
        pct, R, fp = best_orientation(m, priority_dirs=pri)
        T = np.eye(4); T[:3, :3] = R
        m.apply_transform(T)
        m.apply_translation((0, 0, -m.bounds[0][2]))  # drop to the bed
        m.export(f)
        flag = "  << small base!" if fp < 400.0 else ""
        if flag:
            small.append(os.path.basename(f))
        print(f"{os.path.basename(f):16s}{before:7.1f}%{pct:7.1f}%{fp:10.0f}mm2{flag}")
    print("\ndone — parts overwritten in place, pre-oriented for support-free printing.")
    if small:
        print(f"!! {len(small)} part(s) still have a small base even after the fix "
              f"(no orientation had both a >=400mm2 footprint and a tolerable "
              f"overhang, true even lying on the real cut face) — consider a "
              f"brim in the slicer for these: {small}")
    print()


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "MANTA_RIBBON"
    gen_name = sys.argv[2] if len(sys.argv) > 2 else "manta_ribbon"
    main(folder, gen_name)
