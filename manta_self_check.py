# -*- coding: utf-8 -*-
"""MANTA -- does the ribbon run into ITSELF anywhere?

manta_joint_check.py compares each part only with its neighbours along the
ribbon. But the ribbon curls: at the crown it turns and comes back down
behind the backrest, so parts that are far apart ALONG the ribbon end up
close together in space. This checks every such pair in the exported
print STLs: any shared volume (the chair could not be assembled), and the
smallest gap between them.

RUN:  python manta_self_check.py                  (competition)
      python manta_self_check.py manta_ribbon_personal
"""
import glob
import importlib
import os
import re
import sys

import numpy as np
import trimesh


def main(gen_name="manta_ribbon"):
    g = importlib.import_module(gen_name)
    parts = {}
    for f in sorted(glob.glob(f"{g.OUT}/SEG_*.stl")):
        nm = os.path.basename(f)[:-4]
        parts[nm] = (int(re.search(r"SEG_(\d+)", nm).group(1)), trimesh.load(f))
    names = sorted(parts)
    print(f"\nMANTA self-intersection check -- {gen_name}: {len(names)} parts\n")
    np.random.seed(3)
    pts = {n: trimesh.sample.sample_surface(parts[n][1], 6000)[0] for n in names}
    close, fails = [], []
    for i, a in enumerate(names):
        ka, ma = parts[a]
        for b in names[i + 1:]:
            kb, mb = parts[b]
            if abs(ka - kb) <= 1:
                continue                                  # neighbours: manta_joint_check.py
            if np.any(ma.bounds[0] > mb.bounds[1] + 15) or np.any(mb.bounds[0] > ma.bounds[1] + 15):
                continue
            da = trimesh.proximity.signed_distance(mb, pts[a])     # > 0 = inside b
            db = trimesh.proximity.signed_distance(ma, pts[b])
            deep = max(da.max(), db.max())
            gap = -deep
            if gap < 15:
                close.append((gap, a, b))
            if deep > 0.3:
                fails.append(f"{a} and {b} run into each other ({deep:.1f} mm deep)")
    for gap, a, b in sorted(close):
        print(f"   {a:8s} - {b:8s}  " + (f"gap {gap:5.1f} mm" if gap >= 0 else f"OVERLAP {-gap:.1f} mm"))
    if not close:
        print("   no two non-neighbouring parts come within 15 mm of each other")
    if fails:
        print(f"\n!! {len(fails)} PROBLEM(S):")
        for f in fails:
            print("   " + f)
        sys.exit(1)
    print("\nNO SELF-INTERSECTION -- parts that are not neighbours never share volume.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "manta_ribbon")
