# -*- coding: utf-8 -*-
"""MANTA -- ask the REAL slicer where it puts support.

Slices every numbered part with PrusaSlicer (command line, the user's own
profiles) and reads the G-code back: how much support each part gets, and
how much of it ends up INSIDE a hole (peg socket / pin hole), where it can't
be pulled out. A support point counts as "in a hole" when a horizontal ray
hits the part within 16 mm in every one of 16 directions (walled in on all sides).

RUN:  python manta_slicer_check.py _print_ready_light
      (env PS_PRINT / PS_PRINTER / PS_FILAMENT / PS_DATADIR pick the profiles;
       PS_SET="fill_density = 35%;perimeters = 5" overrides single settings)
"""
import glob
import os
import re
import subprocess
import tempfile
import sys

import numpy as np
import trimesh

EXE = r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe"
# a COPY of your PrusaSlicer settings folder (%APPDATA%\PrusaSlicer) is safest
DATADIR = os.environ.get("PS_DATADIR", os.path.join(os.environ.get("APPDATA", ""), "PrusaSlicer"))
WORK = os.path.join(tempfile.gettempdir(), "manta_slicer_check")   # G-code + override files
PRINTER = os.environ.get("PS_PRINTER", "Prusa CORE One HF0.4 nozzle")
PRINT = os.environ.get("PS_PRINT", "0.28mm DRAFT @COREONE HF0.4")
FILAMENT = os.environ.get("PS_FILAMENT", "Prusament PETG @COREONE HF0.4")
HOLE_REACH = 16.0          # mm -- walled in on all sides within this = inside a hole (sockets are <= 30 mm across)


def slice_part(stl, out):
    os.makedirs(WORK, exist_ok=True)
    nobin = os.path.join(WORK, "overrides.ini")
    extra = [kv.strip() for kv in os.environ.get("PS_SET", "").split(";") if "=" in kv]
    open(nobin, "w").write("binary_gcode = 0\n" + "".join(f"{kv}\n" for kv in extra))
    if os.path.exists(out):
        os.remove(out)                   # never read the previous part's G-code
    r = subprocess.run([EXE, "--datadir", DATADIR, "--printer-profile", PRINTER,
                        "--print-profile", PRINT, "--material-profile", FILAMENT,
                        "--load", nobin, "--export-gcode", "--output", out, stl],
                       capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        raise RuntimeError(f"PrusaSlicer failed on {stl}:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")


def read_gcode(path):
    """-> (support xyz points, model xyz points, support / model filament mm);
    extruding moves only, relative E (M83, PrusaSlicer's default)."""
    sup, mod = [], []
    e_sup = e_mod = 0.0
    x = y = z = 0.0
    kind = ""
    for line in open(path, encoding="utf-8", errors="ignore"):
        if line.startswith(";TYPE:"):
            kind = line[6:].strip()
            continue
        if line.startswith(";Z:"):
            z = float(line[3:])
            continue
        if not line.startswith("G1"):
            continue
        mx = re.search(r"X([-\d.]+)", line)
        my = re.search(r"Y([-\d.]+)", line)
        me = re.search(r"E([-\d.]+)", line)
        if mx:
            x = float(mx.group(1))
        if my:
            y = float(my.group(1))
        if me and float(me.group(1)) > 0 and (mx or my):
            (sup if kind.startswith("Support") else mod).append((x, y, z))
            if kind.startswith("Support"):
                e_sup += float(me.group(1))
            else:
                e_mod += float(me.group(1))
    return np.array(sup).reshape(-1, 3), np.array(mod).reshape(-1, 3), e_sup, e_mod


def slicer_totals(path):
    """(grams, hours) as PrusaSlicer itself reports them in the G-code footer"""
    g = h = 0.0
    for line in open(path, encoding="utf-8", errors="ignore"):
        if line.startswith("; total filament used [g] ="):
            g = float(line.split("=")[1])
        elif line.startswith("; estimated printing time (normal mode) ="):
            t = line.split("=")[1]
            for v, u in re.findall(r"(\d+)([dhms])", t):
                h += int(v) * {"d": 24.0, "h": 1.0, "m": 1 / 60.0, "s": 1 / 3600.0}[u]
    return g, h


def in_hole(mesh, pts):
    """support points that hold up a HOLE's wall: straight above them the
    first surface is one lining a socket or pin hole (manta_orient.hole_faces)"""
    if not len(pts):
        return np.zeros(0, dtype=bool)
    import manta_orient
    holes = manta_orient.hole_faces(mesh)
    res = np.zeros(len(pts), dtype=bool)
    loc, idx, tri = mesh.ray.intersects_location(pts, np.tile([0.0, 0.0, 1.0], (len(pts), 1)),
                                                 multiple_hits=False)
    if len(idx):
        res[idx] = holes[tri]
    return res


def main(folder):
    rows = []
    for stl in sorted(glob.glob(os.path.join(folder, "*.stl"))):
        out = os.path.join(WORK, "_chk.gcode")
        slice_part(stl, out)
        sup, mod, e_sup, e_mod = read_gcode(out)
        total_g, hours = slicer_totals(out)
        # split the slicer's own total between support and part by extruded length
        grams = total_g * e_sup / max(e_sup + e_mod, 1e-9)
        part_g = total_g - grams
        mesh = trimesh.load(stl)
        n_hole = 0
        if len(sup) and len(mod):
            # G-code -> STL coordinates: the slicer centres the part in XY and drops it to z=0
            off = (mod[:, :2].min(0) + mod[:, :2].max(0)) / 2 - (mesh.bounds[0, :2] + mesh.bounds[1, :2]) / 2
            p = sup.copy()
            p[:, :2] -= off
            p[:, 2] += mesh.bounds[0, 2] - 0.15      # mid-layer
            pts = p[:: max(1, len(p) // 3000)]
            n_hole = in_hole(mesh, pts).mean() * len(sup) if len(pts) else 0
        g_hole = grams * n_hole / max(len(sup), 1)
        copies = 4 if "PIN" in os.path.basename(stl) else 1
        rows.append((os.path.basename(stl), len(sup), int(n_hole), grams, part_g, g_hole, hours, copies))
        print(f"{rows[-1][0]:<22} support moves {len(sup):>6}   of them inside a hole {int(n_hole):>6}"
              f"   ~{grams:.1f} g support ({g_hole:.2f} g in holes) / {part_g:.0f} g part"
              f"   {hours:.1f} h", flush=True)
    with open(os.path.join(folder, "SLICER_REPORT.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"# PrusaSlicer, profile: {PRINT} / {PRINTER} / {FILAMENT}"
                 f"{' + ' + os.environ['PS_SET'] if os.environ.get('PS_SET') else ''}\n"
                 "# part\tsupport moves\tof them inside a hole\tsupport grams\tpart grams"
                 "\tsupport grams in holes\thours\n")
        for r in rows:
            fh.write(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]:.1f}\t{r[4]:.0f}\t{r[5]:.2f}\t{r[6]:.2f}\n")
    clean = sum(1 for r in rows if r[1] == 0)
    holes = [r for r in rows if r[2] > 0]
    g_sup = sum(r[3] * r[7] for r in rows)
    g_all = g_sup + sum(r[4] * r[7] for r in rows)
    g_hole = sum(r[5] * r[7] for r in rows)
    hours = sum(r[6] * r[7] for r in rows)
    print(f"\nprofile: {PRINT}")
    print(f"{clean} of {len(rows)} parts slice with NO support; "
          f"{len(holes)} parts get support inside a hole ({g_hole:.2f} g in all)")
    print(f"whole chair (pin x4): {g_all / 1000:.2f} kg printed, support {g_sup:.0f} g = "
          f"{100 * g_sup / max(g_all, 1e-9):.1f} %, {hours:.0f} h of printing")
    return rows


if __name__ == "__main__":
    main(sys.argv[1])
