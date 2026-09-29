# -*- coding: utf-8 -*-
"""MANTA -- PARTS_LIST.txt for a numbered, pre-oriented print folder.

Merges the generator's PARTS_LIST (part names, joint notes) with
SUPPORT_REPORT.txt (written by manta_orient.py) into one list whose numbers
match the Board key and the numbers engraved on the parts.

RUN:  python manta_print_list.py MANTA_RIBBON   _print_ready_competition
      python manta_print_list.py MANTA_PERSONAL _print_ready_light light
"""
import sys

SUPPORT_FREE = 6.0      # cm2 -- same threshold as manta_orient.py

HEAD = """MANTA — numbered, pre-oriented printable parts (matches Board key)
{variant}
Each file is pre-rotated to the orientation needing the LEAST support, on a solid
base (python manta_orient.py) — import and print as-is. Slicer: "Support on build
plate only" (never "Everywhere"), overhang threshold 45° or lower. Every hole is
shaped for the way its part lies: sockets that lie sideways have a teardrop roof,
ends that face up are pointed, pin holes run on through the seam as a narrow
channel -- so no support grows inside them (checked in PrusaSlicer).
Pins: 100 % infill, lying on their flat.
Every peg sits in a socket closed inside ONE neighbour part with >= 2 mm wall
(python manta_joint_check.py); >= 0.06 mm clearance survives in these STL files
(python manta_stl_fit_check.py). Each part number is ENGRAVED on a glue face.
ASSEMBLY: glue each L+R pair first, then join segments. Print both halves of a
segment from the SAME version of the files.

"""

LIGHT = """
LIGHT variant — 70 kg design occupant, NOT the competition entry.
Print settings it was checked for (manta_strength_check_personal.py):
  4 perimeters, 15 % gyroid infill, >= 6 top / 5 bottom solid layers;
  PIN: 100 % infill (solid). Load-test before use: 30 -> 50 -> 70 kg.
"""


def main(src, dst, light=False):
    sup = {}
    for line in open(f"{dst}/SUPPORT_REPORT.txt", encoding="utf-8"):
        p = line.split("\t")
        if len(p) >= 2 and p[0].endswith(".stl"):
            sup[p[0][3:-4]] = float(p[1])
    # the real slicer's verdict (manta_slicer_check.py), when it has been run
    sl, sl_prof = {}, ""
    try:
        for line in open(f"{dst}/SLICER_REPORT.txt", encoding="utf-8"):
            if line.startswith("# PrusaSlicer"):
                sl_prof = line[2:].strip()
            p = line.rstrip("\n").split("\t")
            if len(p) >= 4 and p[0].endswith(".stl"):
                g_hole = float(p[5]) if len(p) >= 6 else float(int(p[2]) > 0)
                sl[p[0][3:-4]] = (int(p[1]), g_hole, float(p[3]))
    except OSError:
        pass
    out = [HEAD.format(variant=LIGHT if light else "")]
    if sl:
        out.append(f"Support tags below = what {sl_prof} actually generates.\n")
    body = False
    for line in open(f"{src}/PARTS_LIST.txt", encoding="utf-8"):
        l = line.rstrip("\n")
        if l.startswith("BOARD LEGEND"):
            body = True
        if not body:
            continue
        head = l.split()
        if head and head[0].endswith(".") and head[0][:-1].isdigit():
            nm = head[1]
            if nm == "PIN":
                tag = "no support  -- print at 100 % infill (solid), lying on its flat"
            elif nm in sl:
                n, g_hole, g = sl[nm]
                tag = ("no support" if n == 0 else
                       f"SUPPORT from build plate (~{g:.0f} g)" if g >= 0.5 else
                       "a few specks of support from the build plate (< 1 g)")
                if g_hole >= 0.05:
                    tag += (f"  -- ~{g_hole:.1f} g is a thin branch up a pin channel: it is open at "
                            f"both ends, push it out with a rod")
            elif nm in sup:
                a = sup[nm]
                tag = "no support" if a <= SUPPORT_FREE else f"SUPPORT from build plate (~{a:.0f} cm2)"
            else:
                tag = ""
            l = f"{head[0]:>3} {nm:<12} {head[2]:<4} {tag}".rstrip()
        out.append(l)
    try:
        tot = [0.0, 0.0, 0.0]                         # part g, support g, hours
        for line in open(f"{dst}/SLICER_REPORT.txt", encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 7 and p[0].endswith(".stl"):
                k = 4 if "PIN" in p[0] else 1
                tot[0] += k * float(p[4]); tot[1] += k * float(p[3]); tot[2] += k * float(p[6])
        if tot[0]:
            out.append(f"\nWHOLE CHAIR (PrusaSlicer, pins x4): {(tot[0] + tot[1]) / 1000:.1f} kg of filament, "
                       f"of which support {tot[1]:.0f} g ({100 * tot[1] / (tot[0] + tot[1]):.1f} %), "
                       f"~{tot[2]:.0f} h of printing on one printer")
    except OSError:
        pass
    open(f"{dst}/PARTS_LIST.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"{dst}/PARTS_LIST.txt written ({len(sup)} parts with support data)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], len(sys.argv) > 3)
