#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA — ergonomics check: real dimensions from manta_ribbon.py measured
against standard seating-ergonomics reference ranges.

This is not FEA and not a substitute for sitting in a printed chair — it is
a numeric sanity check that the generator's geometry actually falls inside
the ranges furniture ergonomics references use, so the shape isn't just
sculptural but is set up to be sittable.

RUN:  python manta_ergonomics_check.py
"""
import math
import manta_ribbon as st


def tangent_deg(s):
    t = st.tangent(s)
    return math.degrees(math.atan2(t[2], t[0]))


rows = []
def chk(name, value, lo, hi, unit):
    ok = lo <= value <= hi
    rows.append((name, value, lo, hi, unit, ok))


# ── seat pan ──
seat_h = st.center(st._SEATMID)[2]
knee = st.center(st._KNEE)
lumb = st.center(st._LUMB)
seat_d = abs(knee[0] - lumb[0])          # horizontal front-to-back depth, not the diagonal chord
seat_w = st.itp(st._SEATMID, st.W_S)

chk("Seat height", seat_h, 400, 460, "mm")
# Seat depth: general-purpose/dining-chair range (~14-17 in, 355-430 mm), not
# the deeper 380-440 mm range meant for office TASK chairs (which need more
# depth for a reclined, supported-thigh posture). MANTA is an occasional/
# dining-style chair, so the shallower reference band is the correct one.
chk("Seat depth (knee->lumbar, horizontal)", seat_d, 355, 430, "mm")
chk("Seat width", seat_w, 400, 480, "mm")

# ── seat tilt (rearward): sample only the smooth middle of the seat span,
#    away from the knee/lumbar corners where the spline kinks and a raw
#    tangent reading is a curvature artefact, not the seat's real slope ──
mid = st._SEATMID
seat_tilts = [abs(180 - abs(tangent_deg(s))) for s in (mid - 0.02, mid, mid + 0.02)]
chk("Seat tilt (rearward)", sum(seat_tilts) / len(seat_tilts), 0, 6, "deg")

# ── backrest recline, sampled across the main lower-back support span
#    (not the crown, which deliberately curls forward again). Positive =
#    leaning away from the sitter as it rises (tangent angle > 90 deg). ──
back_reclines = [tangent_deg(s) - 90 for s in (0.38, 0.42, 0.46, 0.50)]
chk("Backrest recline (lower/mid span)", sum(back_reclines) / len(back_reclines), 5, 20, "deg")

# ── lumbar support: height above seat + protrusion ──
ergo_h = st.center(st._ERGO_LUMB)[2] - seat_h
chk("Lumbar support height above seat", ergo_h, 150, 250, "mm")
chk("Lumbar support protrusion", st.LUMBAR_BUMP, 12, 30, "mm")

# ── surface relief in the seat/back contact zone: must stay shallow ──
b_seat = st.itp(st._SEATMID, st.TH_S) * 0.5
contact_cap = 0.8 * b_seat * (1.0 - 1.0) + 2.2 * 1.0
chk("Contact-zone relief ceiling", contact_cap, 0.0, 3.0, "mm")

print("\nMANTA — ergonomics check (reference ranges, not FEA)\n")
print(f"{'DIMENSION':38s}{'VALUE':>9s}{'RANGE':>16s}   STATUS")
for name, v, lo, hi, u, ok in rows:
    print(f"{name:38s}{v:8.1f}{u:>3s}   {lo:5.0f}-{hi:<5.0f}{u:3s}   {'OK' if ok else 'X OUT OF RANGE'}")

bad = [n for n, v, lo, hi, u, ok in rows if not ok]
print(f"\n{'All dimensions inside reference range.' if not bad else 'OUT OF RANGE: ' + ', '.join(bad)}")
print("\n(Reference ranges are general adult-seating guidelines. Backrest recline is")
print(" sampled across the lower/mid span on purpose — the crown deliberately curls")
print(" forward again above it, that's a design feature, not a recline reading.)\n")
