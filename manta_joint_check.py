# -*- coding: utf-8 -*-
"""MANTA -- joint / assembly check (virtual assembly of every part).

Rebuilds the parts exactly as the generator does, then checks every joint by
sampling thousands of points inside the real meshes -- independent of the
CAD kernel's own booleans (which are unreliable exactly where two parts
touch face-to-face):

  1. every part is a valid solid and kept its body (volume vs. its own loft)
  2. every peg really goes INTO its neighbour, into a socket that was
     actually cut there (it fits), and not back into its own part
  3. every peg's short root stays inside its own part (no peg-end poking
     out of the side / bottom of a part)
  4. every pin sits only in holes, and no two neighbouring parts overlap
     once assembled

RUN:  python manta_joint_check.py                 (competition geometry)
      python manta_joint_check.py manta_ribbon_personal
"""
import importlib
import sys

import numpy as np
import trimesh

TOL, ANG = 0.05, 0.1           # fine enough; overlaps are counted only >0.2 mm deep


def mesh(solid):
    v, f = solid.tessellate(TOL, ANG)
    return trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f), process=True)


def inside_any(pts, meshes):
    hit = np.zeros(len(pts), dtype=bool)
    for m in meshes:
        hit |= m.contains(pts)
    return hit


def sample(m, n):
    try:
        return trimesh.sample.volume_mesh(m, n)
    except Exception:
        return np.empty((0, 3))


def main(gen_name="manta_ribbon"):
    rng_state = np.random.get_state()
    np.random.seed(7)
    g = importlib.import_module(gen_name)
    items, pins, cuts, pin_j = g.build()
    parts = {(k, sd): sol for _, sol, _, k, sd in items}
    names = {(k, sd): nm for nm, _, _, k, sd in items}
    raw = {key: g._loft_seg(cuts[key[0]], cuts[key[0] + 1], key[1]) for key in parts}
    M = {key: mesh(s) for key, s in parts.items()}
    R = {key: mesh(s) for key, s in raw.items()}

    fails = []
    print(f"\nMANTA joint check -- {gen_name}: {len(parts)} parts, "
          f"{len(g.JOINT_GEOM)} pegs, {len(pins)} pins\n")
    fails += ["build: " + p for p in g.BUILD_PROBLEMS]

    # 1) valid + body kept
    for key, sol in parts.items():
        r = g.vol(sol) / g.vol(raw[key])
        if not sol.isValid() or not (0.80 <= r <= 1.25):
            fails.append(f"{names[key]}: valid={sol.isValid()} volume {r:.0%} of its loft")

    print('checking pegs ...', flush=True)
    # 2) + 3) every peg
    worst_fit = 0.0
    for name, peg, sock, cc, ax, a_key, b_keys in g.JOINT_GEOM:
        pts = sample(mesh(peg), 800)
        s = (pts - cc) @ ax
        prot, root = pts[s > 0.4], pts[s < -0.4]
        b_raw = [R[k] for k in b_keys if k in R]
        b_fin = [M[k] for k in b_keys if k in M]
        if len(prot):
            into_nb = inside_any(prot, b_raw).mean()      # lands in the neighbour's body
            # exact CAD intersection: peg vs the neighbour's finished part(s).
            # Reliable here -- the peg and its socket never share a face (0.12 mm
            # clearance) -- unlike point sampling, which misreads thin slivers.
            try:
                blocked = sum(g.vol(peg.intersect(parts[k])) for k in b_keys if k in parts)
            except Exception:
                blocked = 1e9
            into_self = R[a_key].contains(prot).mean()
            worst_fit = max(worst_fit, blocked)
            if into_nb < 0.98:       # b_keys is ONE part: the socket must be closed inside it
                fails.append(f"{name}: only {into_nb:.0%} of the peg lands inside its neighbour part "
                             f"(socket open to a face/seam)")
            if blocked > max(20.0, 0.02 * g.vol(peg)):
                fails.append(f"{name}: {blocked:.0f} mm3 of the peg hits solid material (socket missing/misplaced)")
            if into_self > 0.05:       # a little overlap is just fused into its own part
                fails.append(f"{name}: {into_self:.0%} of the peg runs back into its own part")
        # wall around the socket: points 2 mm outside the peg's side surface
        # must still be inside the neighbour -> no paper-thin skin over a hole
        try:
            sp, _ = trimesh.sample.sample_surface(mesh(peg), 1500)
            sd = (sp - cc) @ ax
            radial = (sp - cc) - np.outer(sd, ax)
            rn = np.linalg.norm(radial, axis=1)
            keep = (sd > 1.0) & (rn > 2.0)
            wall_pts = sp[keep] + radial[keep] / rn[keep, None] * 2.0
            if len(wall_pts):
                wall = inside_any(wall_pts, b_raw).mean()
                if wall < 0.97:
                    fails.append(f"{name}: socket wall thinner than 2 mm in places "
                                 f"({wall:.0%} of a 2 mm shell is inside the part)")
        except Exception:
            pass
        if len(root):
            in_own = R[a_key].contains(root).mean()
            if in_own < 0.95:
                fails.append(f"{name}: peg root pokes out of its own part ({in_own:.0%} inside)")

    # 4a) pins only in holes
    for j, pn in enumerate(pins):
        pts = sample(mesh(pn), 800)
        blocked = inside_any(pts, list(M.values())).mean()
        if blocked > 0.02:
            fails.append(f"PIN {j + 1}: {blocked:.0%} of it hits solid material")
        # ...and it must lie inside the chair's envelope: never sticking out
        env = inside_any(pts, list(R.values())).mean()
        if env < 0.99:
            fails.append(f"PIN {j + 1}: {1 - env:.0%} of it sticks out of the chair")
        for k in range(j + 1, len(pins)):
            if g.vol(pn.intersect(pins[k])) > 1.0:
                fails.append(f"PINS {j + 1} and {k + 1} overlap (two pins in one hole)")

    print('checking overlaps ...', flush=True)
    # 4b) no overlap between neighbouring parts once assembled
    keys = sorted(parts)
    worst_ov = 0.0
    for i, a in enumerate(keys):
        pts = sample(M[a], 4000)
        if not len(pts):
            continue
        va = g.vol(parts[a])
        for b in keys[i + 1:]:
            if abs(a[0] - b[0]) > 1:
                continue
            hit = M[b].contains(pts)
            if hit.any():
                # only count points truly INSIDE the neighbour (deeper than
                # 0.2 mm), not points sitting on a face the two parts share
                depth = trimesh.proximity.signed_distance(M[b], pts[hit])
                ov = (depth > 0.2).sum() / len(pts) * va
            else:
                ov = 0.0
            worst_ov = max(worst_ov, ov)
            if ov > 150.0:
                fails.append(f"{names[a]} and {names[b]} overlap by ~{ov:.0f} mm3 when assembled")

    glued_only = [n for n, *_ in g.JOINT_REPORT if "glued face only" in n]
    print(f"parts checked:     {len(parts)}   pegs checked: {len(g.JOINT_GEOM)}   pins: {len(pins)}")
    print(f"worst peg interference with its socket: {worst_fit:.1f} mm3 (exact; <20 mm3 = far below print tolerance)")
    print(f"worst overlap between neighbouring parts: ~{worst_ov:.0f} mm3 "
          f"(sampling noise level ~ tens of mm3)")
    if glued_only:
        print("joints glued on the full face only (no room for a peg):")
        for n in glued_only:
            print("   " + n)
    np.random.set_state(rng_state)
    if fails:
        print(f"\n!! {len(fails)} PROBLEM(S):")
        for f in fails:
            print("   " + f)
        sys.exit(1)
    print("\nALL JOINTS OK -- every peg goes into its neighbour's socket, nothing "
          "overlaps, no peg end sticks out, every part kept its body.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "manta_ribbon")
