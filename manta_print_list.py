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
plate only" (never "Everywhere"). Every peg socket ends in a 45° point, so it
prints without support inside, whichever way it faces.
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
    out = [HEAD.format(variant=LIGHT if light else "")]
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
            elif nm in sup:
                a = sup[nm]
                tag = "no support" if a <= SUPPORT_FREE else f"SUPPORT from build plate (~{a:.0f} cm2)"
            else:
                tag = ""
            l = f"{head[0]:>3} {nm:<12} {head[2]:<4} {tag}".rstrip()
        out.append(l)
    open(f"{dst}/PARTS_LIST.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"{dst}/PARTS_LIST.txt written ({len(sup)} parts with support data)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], len(sys.argv) > 3)
