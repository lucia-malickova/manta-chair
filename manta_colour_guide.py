# -*- coding: utf-8 -*-
"""MANTA — colour guide for a multi-colour print of the personal variant.
Buckets the 41 segments into 4 filament colours by height (floor -> crown),
matching the same teal-to-pearl gradient used in the renders
(see stops in manta_render.py). Multi-colour costs nothing extra in
filament — it's the same total weight, just split across spools.

RUN:  python manta_colour_guide.py   (after manta_ribbon_personal.py)
"""
import os
import re
import trimesh
import manta_ribbon_personal as st

SRC = "MANTA_PERSONAL"
INFILL = 0.20        # match manta_strength_check_personal.py
WALLS = 5
NOZZLE = 0.4
DENSITY = 1.27        # g/cm3, PETG
PRICE_PER_KG = 6.39   # EUR/kg — set to your actual filament price
SHELL_T = WALLS * NOZZLE

# 4 bands across the render's own depth gradient (0 = floor, 1 = crown)
BANDS = [
    (0.00, 0.30, "Deep teal   (floor)"),
    (0.30, 0.55, "Teal"),
    (0.55, 0.80, "Light aqua"),
    (0.80, 1.01, "Pearl / white (crown)"),
]


def parts_list():
    names = []
    with open(f"{SRC}/PARTS_LIST.txt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line[0].isdigit() or "." not in line.split()[0]:
                continue
            names.append(line.split(".", 1)[1].split()[0])
    return names


def main():
    names = parts_list()
    cuts = st.cut_stations()
    band_vol = {n: 0.0 for _, _, n in BANDS}
    band_parts = {n: [] for _, _, n in BANDS}

    for i, nm in enumerate(names, start=1):
        if nm == "PIN":
            continue
        k = int(re.match(r"SEG_(\d+)", nm).group(1))
        smid = 0.5 * (cuts[k] + cuts[k + 1])
        depth = st._depth_frac(smid)
        m = trimesh.load(f"{SRC}/{nm}.stl")
        v = abs(m.volume)
        shell = min(m.area * SHELL_T, v)
        core = max(0.0, v - shell)
        fil = shell + core * INFILL
        for lo, hi, name in BANDS:
            if lo <= depth < hi:
                band_vol[name] += fil
                band_parts[name].append(i)
                break
        else:
            band_vol["Pearl / white (crown)"] += fil
            band_parts["Pearl / white (crown)"].append(i)

    print(f"\nMANTA — colour guide ({SRC}, {INFILL:.0%} infill)\n")
    print(f"{'COLOUR':24s}{'kg':>7s}{'EUR':>8s}   PARTS #")
    tot_kg = tot_eur = 0.0
    for lo, hi, name in BANDS:
        kg = band_vol[name] / 1e6 * DENSITY
        eur = kg * PRICE_PER_KG
        tot_kg += kg; tot_eur += eur
        parts = sorted(band_parts[name])
        print(f"{name:24s}{kg:7.2f}{eur:8.0f}   {parts}")
    print(f"{'TOTAL':24s}{tot_kg:7.2f}{tot_eur:8.0f}   (+ PIN, ~0.1 kg, any colour)")
    print(f"\nSame total weight either way — going multi-colour costs nothing extra "
          f"in filament, only whatever your supplier charges per colour, and the "
          f"risk of leftover material if a colour needs less than a full spool.")


if __name__ == "__main__":
    main()
