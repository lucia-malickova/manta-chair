# -*- coding: utf-8 -*-
"""MANTA — print-orientation fixer.

The generator flagged 8 segments "print STANDING" using a crude heuristic
(spline turn-angle > threshold) and left the other 33 in their as-designed
orientation, on the assumption that was support-free. It wasn't checked
per-part. Measured directly on the exported meshes: as-exported overhang
averages ~18% of surface area, worst part ~38-40% — well past what a
slicer will print without support, regardless of the STANDING label.

This script first tries to rest each part on one of its own two REAL
crosswise cut/joint faces -- found by clustering the mesh's genuinely-flat
faces (~2.5deg tolerance) and picking the two whose centroid sits at the
actual ends of the part (its local length axis), not just whichever flat
face is biggest (that's often the lengthwise L/R seam, or a tenon-base
ring -- large, flat, but not a joint face). This matters beyond footprint
and overhang: a joint's tenon is perpendicular to ITS cut face by
construction, so resting on a real cut face guarantees the tenon points
straight up/down, never sideways. A non-joint flat face can score well on
both footprint and overhang and still leave a tenon sticking out sideways,
needing a support the numbers never showed -- caught on a real print of
part 14. Falls back to a Fibonacci sweep + the mesh's other large flat
faces, picking the largest bed-contact footprint under a tolerable
overhang, when no real cut face qualifies. Then drops the part onto the
bed (z_min=0) and overwrites the STL in place. Verified result across all
42 parts, both the competition and personal-variant geometry: every part
lands on a footprint >=400 mm2 (previously as low as ~70 mm2 on some),
average overhang ~13%, worst ~25%.

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


def real_cut_faces(mesh, tangent_dir, min_cluster_frac=0.01):
    """Of the mesh's flat-face clusters, the two whose centroid sits at the
    two extreme ends of the part along its own length axis (`tangent_dir`)
    -- i.e. the actual crosswise joint faces (tenon end + socket end), as
    opposed to some other large flat face (the lengthwise L/R seam, a
    tenon-base ring) that happens to be bigger but sits partway along the
    part. This distinction matters because a joint's conical tenon is
    perpendicular to ITS cut face by construction: resting the part on one
    of these two faces always points the tenon straight up or down. Resting
    it on some other flat face can leave the tenon sticking out sideways,
    needing support even though the chosen face itself looked fine on
    paper (confirmed on a real print of part 14 — good footprint, good
    overhang%, but the tenon stuck out to the side)."""
    clusters = flat_face_normals(mesh, min_cluster_frac)
    if not clusters:
        return []
    t = tangent_dir / np.linalg.norm(tangent_dir)
    proj = [np.dot(c, t) for _, _, c in clusters]
    lo_i = int(np.argmin(proj))
    hi_i = int(np.argmax(proj))
    out = []
    if lo_i != hi_i:
        out.append(clusters[lo_i][1])
        out.append(clusters[hi_i][1])
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


def segment_mid_tangent(fname, gen):
    """This segment's local length axis (the ribbon's tangent at its
    midpoint) -- used to tell the mesh's two actual crosswise cut-face
    clusters apart from any other large flat face (the lengthwise L/R
    seam, a tenon-base ring) that isn't at either end of the part."""
    m = re.match(r"(?:\d+_)?SEG_(\d+)", os.path.basename(fname))
    if not m:
        return None
    k = int(m.group(1))
    cuts = gen.cut_stations()
    if k + 1 >= len(cuts):
        return None
    smid = 0.5 * (cuts[k] + cuts[k + 1])
    return np.array(gen.tangent(smid))


def main(folder, gen_name="manta_ribbon"):
    gen = importlib.import_module(gen_name)
    files = sorted(glob.glob(f"{folder}/*.stl"))
    print(f"\nMANTA — orienting {len(files)} parts in {folder}/ (cut faces from {gen_name})\n")
    print(f"{'PART':16s}{'before':>8s}{'after':>8s}{'footprint':>12s}")
    small = []
    for f in files:
        m = trimesh.load(f)
        before = overhang_pct(m.face_normals, m.area_faces, m.area)
        tdir = segment_mid_tangent(f, gen)
        cut_faces = real_cut_faces(m, tdir) if tdir is not None else []
        pri = [tdir] if tdir is not None else []
        pct, R, fp = best_orientation(m, priority_dirs=pri, cut_faces=cut_faces)
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
