#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA — MATERIAL + COST
========================
Computes filament use and cost from the real STL parts (MANTA_RIBBON/SEG_*.stl
+ PIN.stl), based on your slicer's infill/wall settings.

Filament estimate per part = SHELL (envelope of thickness WALLS*NOZZLE) +
CORE*INFILL. This is an approximation (+-15-20%) — your slicer gives the
exact number after loading the STL; this is for a quick estimate and for
comparing filament prices.

RUN:  python manta_material.py
REQUIRES: trimesh
"""
import glob
import os
import trimesh

# ══════════ SET THESE FOR YOURSELF ══════════
SRC = "MANTA_PERSONAL"
INFILL = 0.20           # gyroid infill (0..1) — match manta_strength_check_personal.py
WALLS = 5               # number of perimeter walls
NOZZLE = 0.4            # mm
PETG_DENSITY = 1.27     # g/cm3
PRICE_PER_KG = 6.39    # EUR/kg — your actual filament price
SPOOL_KG = 1.0          # kg per spool (for the spool-count conversion)
PIN_QTY = 4             # how many times PIN.stl is actually printed (see PARTS_LIST.txt)
# ════════════════════════════════════════

SHELL_T = WALLS * NOZZLE  # shell thickness (mm)


def filament_volume_mm3(mesh):
    """shell (surface * thickness) + core (remainder) * infill."""
    v_total = abs(mesh.volume)
    shell = min(mesh.area * SHELL_T, v_total)      # the shell can't exceed the whole part
    core = max(0.0, v_total - shell)
    return shell + core * INFILL, v_total


def main():
    files = sorted(glob.glob(f"{SRC}/SEG_*.stl"))
    pin_file = f"{SRC}/PIN.stl"
    rows = []
    tot_fil = tot_solid = 0.0

    for f in files:
        m = trimesh.load(f)
        fil, solid = filament_volume_mm3(m)
        rows.append((os.path.basename(f).replace(".stl", ""), 1, fil, solid))
        tot_fil += fil
        tot_solid += solid

    try:
        m = trimesh.load(pin_file)
        fil, solid = filament_volume_mm3(m)
        rows.append(("PIN", PIN_QTY, fil * PIN_QTY, solid * PIN_QTY))
        tot_fil += fil * PIN_QTY
        tot_solid += solid * PIN_QTY
    except Exception:
        print(f"  ({pin_file} not found, skipping)")

    rows.sort(key=lambda r: -r[2])

    print(f"\nMANTA — MATERIAL  (infill {INFILL:.0%}, {WALLS} walls x {NOZZLE} mm = {SHELL_T:.1f} mm shell)\n")
    print(f"{'PART':12s}{'qty':>4s}{'filament cm3':>14s}{'mass g':>12s}")
    for nm, qty, fil, solid in rows[:12]:
        print(f"{nm:12s}{qty:4d}{fil/1000:14.1f}{fil/1000*PETG_DENSITY:12.1f}")
    if len(rows) > 12:
        print(f"  ... and {len(rows)-12} more parts")

    tot_kg = tot_fil / 1000 * PETG_DENSITY / 1000
    solid_kg = tot_solid / 1000 * PETG_DENSITY / 1000
    price = tot_kg * PRICE_PER_KG
    spools = tot_kg / SPOOL_KG

    print(f"\n{'='*46}")
    print(f"Total parts:              {len(rows)}")
    print(f"Part volume (100% solid): {tot_solid/1000:9.0f} cm3  ({solid_kg:.1f} kg if 100%)")
    print(f"Filament at {INFILL:.0%} infill:   {tot_fil/1000:9.0f} cm3")
    print(f"Filament mass:            {tot_kg:9.2f} kg")
    print(f"Spools ({SPOOL_KG:.0f} kg):             {spools:9.1f}")
    print(f"Filament COST ({PRICE_PER_KG:.0f} EUR/kg): {price:8.2f} EUR")
    print(f"{'='*46}")
    print("\n(estimate +-15-20% — your slicer gives the exact number after loading the STL)")


if __name__ == "__main__":
    main()
