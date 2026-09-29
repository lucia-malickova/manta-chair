# -*- coding: utf-8 -*-
"""MANTA -- ONE command that runs every check and says whether all is well.

RUN:  python manta_verify.py                 both variants, all checks (~45 min)
      python manta_verify.py light           just the light variant
      python manta_verify.py competition --fast
                                            skip the two slow ones (virtual
                                            assembly, PrusaSlicer) -- ~5 min

Checks, per variant:
  strength     weakest glued check >= 1.5x (manta_strength_check*.py)
  print files  42 numbered STLs + PARTS_LIST + ORIENT.json, every part on
               the bed and inside the Prusa CORE One volume (250x220x270)
  STL fit      every peg keeps >= 0.06 mm clearance in the print STLs
  assembly     virtual assembly: pegs in sockets, 2 mm walls, pins only in
               holes, nothing overlaps (slow)
  slicer       PrusaSlicer adds < 2 % support and < 0.5 g inside holes
               (slow; skipped if PrusaSlicer isn't installed)
and once for the submission:
  description  <= 500 words, 1 page;   package <= 15 MB
Exit code 0 = all passed.
"""
import glob
import importlib
import os
import re
import subprocess
import sys

import numpy as np
import trimesh

VARIANTS = {
    "competition": dict(gen="manta_ribbon", strength="manta_strength_check",
                        prints=["_print_ready_competition", "MANTA_RIBBON"],
                        slicer_set="layer_height = 0.2;perimeters = 5;fill_density = 35%"),
    "light": dict(gen="manta_ribbon_personal", strength="manta_strength_check_personal",
                  prints=["_print_ready_light", "MANTA_LIGHT"],
                  slicer_set="perimeters = 4;fill_density = 15%;top_solid_layers = 6"),
}
BED = (250.0, 220.0, 270.0)
results = []


def report(name, ok, detail):
    results.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:<26} {detail}", flush=True)


def run(*cmd, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable, "-u", *cmd], capture_output=True, text=True, env=e)
    return r.returncode, r.stdout + r.stderr


def print_folder(v):
    for f in VARIANTS[v]["prints"]:
        if glob.glob(f"{f}/[0-9][0-9]_*.stl"):
            return f
    return None


def check_strength(v):
    st = importlib.import_module(VARIANTS[v]["strength"])
    m, name = st.worst_margin()
    report("strength", m >= 1.5, f"weakest glued check {m:.1f}x ({name})")


def check_print_files(v):
    folder = print_folder(v)
    if not folder:
        report("print files", False, "no numbered print folder found")
        return None
    stls = sorted(glob.glob(f"{folder}/[0-9][0-9]_*.stl"))
    bad = []
    for f in stls:
        m = trimesh.load(f)
        lo, hi = m.bounds
        ext = hi - lo
        if abs(lo[2]) > 0.05 or ext[2] > BED[2] or lo[0] < -0.5 or lo[1] < -0.5 \
                or hi[0] > BED[0] + 0.5 or hi[1] > BED[1] + 0.5:
            bad.append(os.path.basename(f))
    extra = [x for x in ("PARTS_LIST.txt", "ORIENT.json") if not os.path.exists(f"{folder}/{x}")]
    ok = len(stls) == 42 and not bad and not extra
    report("print files", ok, f"{folder}: {len(stls)}/42 parts"
           + (f", off the bed: {bad}" if bad else ", all on the bed")
           + (f", missing {extra}" if extra else ""))
    return folder


def check_fit(v):
    g = importlib.import_module(VARIANTS[v]["gen"])
    if not glob.glob(f"{g.OUT}/SEG_*.stl"):
        report("STL fit", False, f"no generator output in {g.OUT}/ -- run: python "
               f"manta_print_ready.py {VARIANTS[v]['gen']} {g.OUT} {VARIANTS[v]['prints'][0]}")
        return
    code, out = run("manta_stl_fit_check.py", VARIANTS[v]["gen"])
    tight = re.findall(r"tightest: \+([\d.]+) mm", out)
    report("STL fit", code == 0, f"tightest peg clearance {min(map(float, tight)):.3f} mm"
           if tight else out.strip().splitlines()[-1][:80])


def check_assembly(v):
    code, out = run("manta_joint_check.py", VARIANTS[v]["gen"])
    last = [l for l in out.splitlines() if l.strip()]
    probs = [l.strip() for l in last if l.startswith("   ") and ":" in l][:3]
    report("assembly", code == 0, "every peg in its socket, walls >= 2 mm, nothing overlaps"
           if code == 0 else "; ".join(probs) or last[-1][:80])


def check_slicer(v, folder):
    code, out = run("manta_slicer_check.py", folder, env={"PS_SET": VARIANTS[v]["slicer_set"]})
    m = re.search(r"support (\d+) g = ([\d.]+) %", out)
    h = re.search(r"inside a hole \(([\d.]+) g in all\)", out)
    if code or not m or not h:
        report("slicer", False, (out.strip().splitlines() or ["no output"])[-1][:90])
        return
    pct, g_hole = float(m.group(2)), float(h.group(1))
    report("slicer", pct < 2.0 and g_hole < 0.5,
           f"support {m.group(1)} g = {pct:.1f} % of the filament, {g_hole:.2f} g inside holes")


def check_submission():
    try:
        from pypdf import PdfReader
        pages = len(PdfReader("TEAMID_Description.pdf").pages)
    except Exception:
        pages = -1
    code, out = run("manta_pdf.py")
    w = re.search(r"body words: (\d+)", out)
    words = int(w.group(1)) if w else 9999
    if pages < 0:
        from pypdf import PdfReader
        pages = len(PdfReader("TEAMID_Description.pdf").pages)
    report("description", words <= 500 and pages == 1, f"{words} words, {pages} page(s)")
    code, out = run("manta_package.py")
    t = re.search(r"TOTAL\s+([\d.]+)", out)
    mb = float(t.group(1)) if t else 99.0
    report("package", mb <= 15.0, f"{mb:.2f} MB of 15")


def main(argv):
    fast = "--fast" in argv
    which = [a for a in argv if a in VARIANTS] or list(VARIANTS)
    has_ps = os.path.exists(r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe")
    for v in which:
        print(f"\n== {v} ==", flush=True)
        check_strength(v)
        folder = check_print_files(v)
        check_fit(v)
        if fast:
            print("  [skip] assembly, slicer          (--fast)")
            continue
        check_assembly(v)
        if has_ps and folder:
            check_slicer(v, folder)
        else:
            print("  [skip] slicer                     (PrusaSlicer not installed)")
    if "competition" in which:
        print("\n== submission ==", flush=True)
        check_submission()
    bad = [n for n, ok in results if not ok]
    print("\n" + ("ALL CHECKS PASSED" if not bad else f"{len(bad)} CHECK(S) FAILED: {', '.join(bad)}"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
