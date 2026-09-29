# -*- coding: utf-8 -*-
"""MANTA -- the whole print-ready pipeline for one variant, in order.

  1. generator                       (parts in model coordinates)
  2. numbered copies + manta_orient  (search: least support, fits the bed;
                                      writes ORIENT.json)
  3. generator again                 (pin holes get teardrop roofs pointing
                                      up for exactly those rotations)
  4. numbered copies + manta_orient --reuse

RUN:  python manta_print_ready.py manta_ribbon_personal MANTA_PERSONAL _print_ready_light
      python manta_print_ready.py manta_ribbon          MANTA_RIBBON   _print_ready_competition
"""
import os
import shutil
import subprocess
import sys


def run(*cmd):
    print(">>", " ".join(cmd), flush=True)
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-4:])
    print(tail, flush=True)
    if r.returncode:
        raise SystemExit(f"FAILED: {' '.join(cmd)}")


def numbered_copies(src, dst):
    os.makedirs(dst, exist_ok=True)
    for line in open(f"{src}/PARTS_LIST.txt", encoding="utf-8"):
        l = line.strip()
        if not l or not l[0].isdigit() or "." not in l.split()[0]:
            continue
        i, rest = l.split(".", 1)
        nm = rest.split()[0]
        shutil.copy(f"{src}/{nm}.stl", f"{dst}/{int(i):02d}_{nm}.stl")


def main(gen, src, dst, search=True):
    if search:
        run(f"{gen}.py")
        numbered_copies(src, dst)
        run("manta_orient.py", dst, gen)
    run(f"{gen}.py")
    numbered_copies(src, dst)
    run("manta_orient.py", dst, gen, "--reuse")


if __name__ == "__main__":
    main(*sys.argv[1:4], search="--no-search" not in sys.argv)
