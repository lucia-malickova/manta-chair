# -*- coding: utf-8 -*-
"""MANTA — builds the two 3D submission files per the brief's "What to
Submit" section:
  Chair.stl    -> "one file showing the fully assembled chair" — the chair
                  ALONE, nothing else. manta_ribbon.py already produces
                  exactly this, so this script leaves it untouched.
  Assembly.stl -> "one file containing all individual printable parts...
                  numbered and organised, coordinated with the assembly
                  instructions shown on the A2 Board" — built INSIDE the
                  official, unmodified 3D_Template.stl (its own note says
                  "Do not modify or alter this template... retain all
                  lines, text, and geometry exactly as provided"), with a
                  small reference chair in its footprint box and each of
                  the 42 legend parts in its numbered 220x220x250mm cell
                  (cells are numbered column-major — 1,8,15,22,29,36,43
                  down column 1, 2,9,16,... down column 2, etc — read
                  directly off the official template; only the NUMBER has
                  to match the Board's own key, not the box's on-page
                  position, since the two use different visual layouts).

Overwrites MANTA_RIBBON/MANTA_Assembly.stl in place so the rest of the
pipeline (manta_package.py) needs no changes. MANTA_Chair.stl is read but
never modified.

RUN: python manta_apply_template.py   (after manta_ribbon.py)
REQUIRES: trimesh, cadquery
"""
import os
import trimesh
import numpy as np
import cadquery as cq
import manta_ribbon as st

SRC = "MANTA_RIBBON"
TEMPLATE = "3D_Template.stl"

# cell grid, read directly off the official template geometry
CELL_X0, CELL_XSTEP = 1250.0, 440.0     # column 0..6
CELL_Y0, CELL_YSTEP = 2473.8, -400.0    # row 0 (top) .. 6 (bottom)
CELL_SIZE = 220.0

# chair footprint rectangle (in the template, for the Assembly file's
# reference copy only — Chair.stl itself carries no template geometry)
CHAIR_CX, CHAIR_CY = 400.0, 473.8


def cell_center(n):
    """1-indexed part number -> (x, y) centre of its official template cell."""
    col = (n - 1) // 7
    row = (n - 1) % 7
    x0 = CELL_X0 + col * CELL_XSTEP
    y0 = CELL_Y0 + row * CELL_YSTEP
    return x0 + CELL_SIZE / 2, y0 + CELL_SIZE / 2


def place(mesh, cx, cy):
    b = mesh.bounds
    dx = cx - (b[0][0] + b[1][0]) / 2
    dy = cy - (b[0][1] + b[1][1]) / 2
    dz = -b[0][2]
    mesh.apply_translation((dx, dy, dz))
    return mesh


def parts_list():
    names = []
    with open(f"{SRC}/PARTS_LIST.txt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line[0].isdigit() or "." not in line.split()[0]:
                continue
            nm = line.split(".", 1)[1].split()[0]
            names.append(nm)
    return names


def main():
    template = trimesh.load(TEMPLATE)
    print(f"template: {len(template.vertices)} verts, bounds {template.bounds.tolist()}")

    # sanity-check the footprint constraint against the untouched chair file
    chair_bounds = trimesh.load(f"{SRC}/MANTA_Chair.stl").bounds
    fw = chair_bounds[1][0] - chair_bounds[0][0]
    fd = chair_bounds[1][1] - chair_bounds[0][1]
    print(f"chair footprint {fw:.1f} x {fd:.1f} mm (limit 800x800)")

    # Small reference copy for the Assembly file. Re-lofted with fewer
    # sections rather than decimated from the fine mesh — a coarser SMOOTH
    # surface reads far better than a decimated one, which turns the round
    # legs faceted/blocky. Full relief fidelity isn't needed for a
    # thumbnail-sized reference icon anyway.
    ss = np.linspace(0, 1, 100)
    hv_ref = [st.big(st.loft([st.wire_at(s, sd) for s in ss])) for sd in (-1, 1)]
    ref_solid = cq.Compound.makeCompound([h for h in hv_ref if h is not None])
    cq.exporters.export(ref_solid, "_ref_chair.stl", tolerance=0.3, angularTolerance=0.6)
    chair_ref = trimesh.load("_ref_chair.stl")
    os.remove("_ref_chair.stl")

    def placed_chair_ref():
        return place(chair_ref.copy(), CHAIR_CX, CHAIR_CY)

    # ---- Assembly: the full chair for reference + one part per numbered cell ----
    names = parts_list()
    print(f"{len(names)} parts to place")
    parts = [template, placed_chair_ref()]
    for i, nm in enumerate(names, start=1):
        # coarse copy (the fine print STL would blow the submission size limit)
        m = trimesh.load(f"{SRC}/coarse/{nm}.stl")
        cx, cy = cell_center(i)
        place(m, cx, cy)
        parts.append(m)
        print(f"  {i:2d}. {nm:10s} -> cell centre ({cx:.0f},{cy:.0f})")
    assembly = trimesh.util.concatenate(parts)
    assembly.export(f"{SRC}/MANTA_Assembly.stl")
    print(f"MANTA_Assembly.stl: {len(assembly.vertices)} verts")

    # ---- Chair.stl: untouched — "one file showing the fully assembled
    # chair" means the chair alone, no template geometry attached ----
    print("MANTA_Chair.stl: left as-is (chair only, no template)")


if __name__ == "__main__":
    main()
