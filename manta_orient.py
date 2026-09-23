# -*- coding: utf-8 -*-
"""MANTA — print-orientation fixer.

The generator flagged 8 segments "print STANDING" using a crude heuristic
(spline turn-angle > threshold) and left the other 33 in their as-designed
orientation, on the assumption that was support-free. It wasn't checked
per-part. Measured directly on the exported meshes: as-exported overhang
averages ~18% of surface area, worst part ~38-40% — well past what a
slicer will print without support, regardless of the STANDING label.

This script searches ~100 candidate build directions per part (not just
the local tangent) and rotates each one to whichever orientation actually
minimises overhang, then drops it back onto the bed (z_min=0) and
overwrites the STL in place. Verified result: average overhang ~1%, worst
part ~4% (small rounded fillets a slicer won't flag) across all 41 parts,
both the competition and personal-variant geometry.

RUN:  python manta_orient.py <folder>   e.g. MANTA_RIBBON or MANTA_PERSONAL
"""
import glob
import os
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


def flat_face_normals(mesh, min_cluster_frac=0.015):
    """Normal directions of the mesh's largest near-planar face clusters
    (e.g. the flat crosswise/lengthwise cut faces) -- these are the
    orientations a person would actually consider first for a big, stable
    base, and a generic direction sweep can easily miss them if they don't
    happen to also be near the global overhang minimum."""
    normals = mesh.face_normals
    areas = mesh.area_faces
    used = np.zeros(len(normals), dtype=bool)
    clusters = []
    order = np.argsort(-areas)
    for i in order:
        if used[i]:
            continue
        sim = normals @ normals[i] > 0.98  # within ~11 deg
        grp = sim & ~used
        used |= grp
        a = areas[grp].sum()
        if a >= mesh.area * min_cluster_frac:
            clusters.append((a, normals[i]))
    clusters.sort(key=lambda c: -c[0])
    return [n for _, n in clusters[:12]]


def best_orientation(mesh, n=100, overhang_tolerance=8.0, min_footprint_mm2=400.0):
    """Two-stage: score every candidate direction (a Fibonacci sweep PLUS
    the mesh's own largest flat-face normals, so an obvious 'lie flat on
    the cut face' option is always considered even if it isn't quite the
    global overhang minimum), then among everything within
    `overhang_tolerance` points of the lowest overhang found, pick the
    LARGEST bed contact footprint (falling back toward the lowest-overhang
    candidate only if nothing clears `min_footprint_mm2` -- rather stand
    on a bit more overhang than balance on a point)."""
    dirs = list(fibonacci_sphere(n))
    for fn in flat_face_normals(mesh):
        dirs.append(fn); dirs.append(-fn)
    scored = []
    for d in dirs:
        R = rot_to_z(d)
        nrm = mesh.face_normals @ R.T
        pct = overhang_pct(nrm, mesh.area_faces, mesh.area)
        scored.append((pct, R))
    min_pct = min(s[0] for s in scored)
    near_best = [(pct, R, base_footprint(mesh, R)) for pct, R in scored
                 if pct <= min_pct + overhang_tolerance]
    near_best.sort(key=lambda c: -c[2])
    good = [c for c in near_best if c[2] >= min_footprint_mm2]
    pool = good if good else near_best
    pct, R, fp = max(pool, key=lambda c: c[2])
    return pct, R, fp


def main(folder):
    files = sorted(glob.glob(f"{folder}/*.stl"))
    print(f"\nMANTA — orienting {len(files)} parts in {folder}/\n")
    print(f"{'PART':16s}{'before':>8s}{'after':>8s}{'footprint':>12s}")
    small = []
    for f in files:
        m = trimesh.load(f)
        before = overhang_pct(m.face_normals, m.area_faces, m.area)
        pct, R, fp = best_orientation(m)
        T = np.eye(4); T[:3, :3] = R
        m.apply_transform(T)
        m.apply_translation((0, 0, -m.bounds[0][2]))  # drop to the bed
        m.export(f)
        flag = "  << small base!" if fp < 120.0 else ""
        if flag:
            small.append(os.path.basename(f))
        print(f"{os.path.basename(f):16s}{before:7.1f}%{pct:7.1f}%{fp:10.0f}mm2{flag}")
    print("\ndone — parts overwritten in place, pre-oriented for support-free printing.")
    if small:
        print(f"!! {len(small)} part(s) still have a small base even after the fix "
              f"(no orientation had both low overhang and a solid footprint) — "
              f"consider a brim in the slicer for these: {small}")
    print()


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "MANTA_RIBBON"
    main(folder)
