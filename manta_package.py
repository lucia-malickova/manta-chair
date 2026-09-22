# -*- coding: utf-8 -*-
"""MANTA — pack the submission files into ./ODOVZDANIE/ with the TEAMID_ prefix.
After registration, rename TEAMID -> the team's real ID."""
import os, shutil

TEAM = "TEAMID"
OUT = "ODOVZDANIE"
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

src = {
    f"{TEAM}_Chair.stl":       "MANTA_RIBBON/MANTA_Chair.stl",
    f"{TEAM}_Assembly.stl":    "MANTA_RIBBON/MANTA_Assembly.stl",
    f"{TEAM}_Board.jpg":       "TEAMID_Board.jpg",
    f"{TEAM}_Poster.jpg":      "TEAMID_Poster.jpg",
    f"{TEAM}_Description.pdf": "TEAMID_Description.pdf",
}
total = 0
print(f"{'FILE':30s}{'MB':>8s}")
for dst, s in src.items():
    if not os.path.exists(s):
        print(f"{dst:30s}   MISSING — {s} does not exist"); continue
    shutil.copy(s, os.path.join(OUT, dst))
    mb = os.path.getsize(s) / 1e6
    total += mb
    print(f"{dst:30s}{mb:8.2f}")
LIMIT = 15.0  # confirmed on the live submission page — the brief PDF's 10MB is stale
print(f"{'TOTAL':30s}{total:8.2f}   (limit {LIMIT:.2f})  ->  {'OK' if total <= LIMIT else 'OVER LIMIT!'}")
print(f"\n{OUT}/  — after registration, rename TEAMID_ to the team's ID.")
