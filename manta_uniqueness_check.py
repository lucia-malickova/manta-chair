# -*- coding: utf-8 -*-
"""MANTA — uniqueness check: proves "no two segments are identical" instead
of just asserting it. Compares every exported SEG_*.stl against every other
by volume, surface area, bounding box, and vertex count — four independent
signatures that would all have to collide by coincidence for two genuinely
different parts to read as "the same".

RUN:  python manta_uniqueness_check.py   (after manta_ribbon.py)
"""
import glob
import os
import trimesh

SRC = "MANTA_RIBBON"


def signature(path):
    m = trimesh.load(path)
    dims = tuple(round(x, 2) for x in (m.bounds[1] - m.bounds[0]))
    return (round(m.volume, 2), round(m.area, 2), dims, len(m.vertices))


def main():
    files = sorted(glob.glob(f"{SRC}/SEG_*.stl"))
    print(f"\nMANTA — uniqueness check ({len(files)} segments)\n")
    sigs = [(os.path.basename(f), signature(f)) for f in files]

    seen = {}
    dupes = []
    for name, sig in sigs:
        if sig in seen:
            dupes.append((name, seen[sig]))
        else:
            seen[sig] = name

    vols = sorted((sig[0], name) for name, sig in sigs)
    closest_gap = min(vols[i + 1][0] - vols[i][0] for i in range(len(vols) - 1))
    closest_pair = min(
        range(len(vols) - 1), key=lambda i: vols[i + 1][0] - vols[i][0])

    print(f"{'PART':10s}{'volume mm3':>12s}{'area mm2':>11s}{'bbox mm':>22s}{'verts':>8s}")
    for name, (vol, area, dims, nv) in sigs:
        print(f"{name:10s}{vol:12.1f}{area:11.1f}   {dims[0]:6.1f}x{dims[1]:6.1f}x{dims[2]:6.1f}{nv:8d}")

    print(f"\nDuplicate signatures: {len(dupes)}")
    for a, b in dupes:
        print(f"  {a}  ==  {b}")
    print(f"Closest pair by volume: {vols[closest_pair][1]} / {vols[closest_pair+1][1]}"
          f"  (differ by {closest_gap:.1f} mm3)")
    print("\nEVERY SEGMENT IS GEOMETRICALLY DISTINCT."
          if not dupes else "\n!! SOME SEGMENTS ARE IDENTICAL — see above.")
    print("(A perfectly plausible outcome by construction: each segment is a "
          "different slice of a continuously varying spline, so identical "
          "geometry would only happen if two cuts landed at the same "
          "position with the same width/thickness/twist — checked here "
          "rather than assumed.)\n")


if __name__ == "__main__":
    main()
