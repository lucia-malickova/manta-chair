#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA — one continuous ribbon: strength check (first-order, NOT FEA)
==========================================================
Engineering screening for the ribbon cantilever from manta_ribbon.py.
Run:  python manta_strength_check.py         (pure math, no CAD)

Model: the chair is a ribbon. The seat is a shallow beam between the front
foot (knee) and the lumbar. The backrest is a cantilever fixed at the
lumbar, held by the tail-brace down to the floor. Cuts are always AWAY from
the lumbar and the knee (the ribbon stays whole there). The GLUED JOINTS are
the critical checks.
"""
import math
import manta_ribbon as st

# ══════════ (A) REAL-WORLD INPUTS ══════════
M_KG = 120.0     # heaviest expected user
G    = 9.81
DYN  = 1.8       # 1.0 slow sit / 1.8 normal sit-down / 2.5 a drop/flop
SF   = 2.0       # safety factor
C_BACK = 0.55    # lean into the backrest, as a fraction of body weight (strong recline)
C_SIDE = 0.35    # sideways lean

# PETG material (conservative, with infill)
SIG_ULT   = 45.0
SIG_LAYER = 25.0   # BETWEEN layers
TAU_ULT   = 27.0
E_MPA     = 2000.0
EPOXY_SH  = 12.0   # epoxy shear at the joint
EPOXY_TEN = 15.0   # epoxy tension (butt joint, conservative)
INFILL    = 0.35   # 35% gyroid, as printed (a slicer setting, not derived from the geometry)

# ══════════ (B) GEOMETRY — read LIVE from manta_ribbon.py's actual spine/
# width/thickness tables, not copied by hand. This means changing W_S, TH_S
# or the spine in manta_ribbon.py automatically changes these numbers too —
# there's no separate "shadow" copy that can go stale.
SEAT_W       = st.itp(st._SEATMID, st.W_S)
SEAT_TH_MID  = st.itp(st._SEATMID, st.TH_S)
SEAT_SPAN    = (st._LUMB - st._KNEE) * st._LEN      # knee -> lumbar (free seat span)
LUMBAR_W     = st.itp(st._LUMB, st.W_S)
LUMBAR_TH    = st.itp(st._LUMB, st.TH_S)            # thickness at the lumbar (Wolff maximum)
BACK_LEVER   = 330.0   # backrest force lever above the lumbar (up to the shoulder blades)
BACK_H_TOP   = 560.0   # backrest height above the lumbar

_cuts = st.cut_stations()
_cut_near_lumbar = min((c for c in _cuts if abs(c - st._LUMB) > 1e-6),
                        key=lambda c: abs(c - st._LUMB))
CUT_W        = st.itp(_cut_near_lumbar, st.W_S)     # ribbon width at the real cut nearest the lumbar
CUT_TH       = st.itp(_cut_near_lumbar, st.TH_S)
CUT_M_FACTOR = 0.42    # fraction of the lumbar moment present at this cut (FORBID keeps cuts away from the knot)

LEG_W        = st.itp(st._KNEE * 0.5, st.W_S)       # front-leg width, mid-span
LEG_TH       = st.itp(st._KNEE * 0.5, st.TH_S)      # front-leg thickness (weak axis)
LEG_FREE     = st._KNEE * st._LEN                   # free length of the front leg (foot -> knee)

TAIL_W       = 155.0   # tail-brace width
TAIL_TH      = 38.0    # min thickness at the brace's lumbar end
TAIL_FREE    = 620.0   # free length of the brace

TENON_R      = st.TEN_R      # crosswise conical tenon (large diameter)
TENON_TIP    = st.TEN_TIP
TENON_L      = st.TEN_L
LTEN_R       = st.LTEN_R     # lengthwise (L/R) tenon
LTEN_L       = st.LTEN_L
PIN_R        = st.PIN_R      # dia 10 crosswise pin (legs + lumbar)

# glued faces (full cross-section area at the cut * effective fraction after infill/flutes)
FACE_EFF     = 0.55

# footprint — FORKED foot, 4 contact points
FOOT_FRONT_X = 470.0   # front pad, forward
FOOT_BACK_X  = 240.0   # rear pad, backward
FOOT_HALF_Y  = 345.0   # half-spread of the fork prongs sideways (FORK_SPLAY + prong)
PRONG_W      = 176.0   # width of one prong
PRONG_TH     = 42.0    # prong thickness at the pad
PRONG_SPLAY_LEN = 210.0  # slanted length of the prong from ribbon to floor
COM_UP_H     = 650.0   # centre-of-mass height, person sitting upright
COM_LEAN_H   = 690.0   # centre-of-mass height, leaning back
# CoM X (from centre): + forward.  Seat centre ~ X=250 in the generator's axis.
COM_UP_X     = 250.0
COM_LEAN_X   = 120.0
CHAIR_KG     = 12.0
CHAIR_COM_X  = 120.0
# NOTE: BACK_LEVER/BACK_H_TOP/TAIL_*/footprint/CoM stay as representative
# fixed estimates of the overall shape (first-order, not FEA) — they only
# need hand-updating if you reshape the SPINE curve itself, not for a simple
# width/thickness/infill table edit. SEAT/LUMBAR/CUT/LEG above are the ones
# a table edit actually changes, and those are now always current.
# ═══════════════════════════════════════════════════════

k  = max(0.30, INFILL)
sa = SIG_ULT   * k / SF
la = SIG_LAYER * k / SF
ta = TAU_ULT   * k / SF
esh = EPOXY_SH / SF
etn = EPOXY_TEN / SF

W  = M_KG * G * DYN            # vertical
Hb = M_KG * G * C_BACK         # into the backrest
Hs = M_KG * G * C_SIDE         # sideways

Z = lambda w, h: w * h * h / 6.0
A = lambda w, h: w * h
I = lambda w, h: w * h ** 3 / 12.0
Acirc = lambda r: math.pi * r * r

rows = []
def chk(name, act, allow, unit, note=""):
    rows.append((name, act, allow, allow / act if act > 0 else 999, act <= allow, unit, note))

# 1) SEAT — bending at mid-span (UDL, simply supported knee<->lumbar)
M_seat = W * SEAT_SPAN / 8.0
chk("Seat: mid-span bending", M_seat / Z(SEAT_W, SEAT_TH_MID), sa, "MPa")

# 2) LUMBAR — bending from the backrest cantilever (lean-back + weight offset)
M_lumbar = Hb * BACK_LEVER + (W * 0.30) * BACK_LEVER * 0.4
chk("Lumbar: bending (backrest cantilever)", M_lumbar / Z(LUMBAR_W, LUMBAR_TH), sa, "MPa")

# 3) CUT nearest the lumbar — section bending (the ribbon is whole here, not a plate)
M_cut = CUT_M_FACTOR * M_lumbar
chk("Cut near lumbar: section bending", M_cut / Z(CUT_W, CUT_TH), sa, "MPa")

# 4) CUT near the lumbar — GLUED butt joint (full section), moment as a
#    force couple with lever arm ~0.7*h; tension on the tension half of the face
F_couple = M_cut / (0.7 * CUT_TH)
face_area = CUT_W * CUT_TH * FACE_EFF
chk("Cut near lumbar: epoxy tension (face)", F_couple / (0.5 * face_area), etn, "MPa")

# 5) CUT near the lumbar — MECHANICAL BACKUP (if the epoxy were to fail
#    eventually): the tension couple carried by the tenon (PETG core) + the
#    dia 10 pin (double shear).
cap_root = Acirc(TENON_R) * 0.85
pin_2sh  = 2 * Acirc(PIN_R)
cap_N    = cap_root * la + pin_2sh * ta          # tension capacity without glue [N]
chk("Cut at lumbar: tenon+pin in tension (no glue)", F_couple, cap_N, "N")
# 5b) transverse SHEAR at the cut (horizontal backrest reaction) — carried by the tenon in the socket
V_cut = Hb + W * 0.20
chk("Cut at lumbar: transverse shear (tenon in socket)", V_cut, Acirc(TENON_R) * 0.85 * ta + pin_2sh * ta, "N")
cap_lat = math.pi * (TENON_R + TENON_TIP) / 2 * TENON_L
chk("Cut at lumbar: tenon epoxy shear (with glue)", F_couple / cap_lat, esh, "MPa")

# 6) LENGTHWISE L/R SEAM under the seat — asymmetric sit (weight on one half)
M_seam = (W * 0.5) * 0.11        # lever ~110 mm from the centreline to the sit-bone
seam_len = 150.0                  # seam length for 1 segment
seam_area = seam_len * SEAT_TH_MID * FACE_EFF
F_seam = M_seam / (0.7 * SEAT_TH_MID)
chk("Lengthwise seam: epoxy shear", F_seam / seam_area, esh, "MPa")

# 7) FRONT LEG — compression
Fl = 0.55 * W                     # share carried by the front leg
chk("Front leg: compression", Fl / A(LEG_W, LEG_TH), sa, "MPa")

# 8) FRONT LEG — buckling (wide ribbon, weak axis; K=2 conservative)
Pcr = math.pi**2 * E_MPA * I(LEG_W, LEG_TH) / (2 * LEG_FREE) ** 2
chk("Front leg: buckling", Fl, Pcr / SF, "N")

# 9) TAIL-BRACE — compression from the backrest reaction
Ft = (Hb + W * 0.25) / math.sin(math.radians(38))   # brace tilt ~38 deg from vertical
chk("Tail-brace: compression", Ft / A(TAIL_W, TAIL_TH), sa, "MPa")

# 10) TAIL-BRACE — buckling
Pcrt = math.pi**2 * E_MPA * I(TAIL_W, TAIL_TH) / (2 * TAIL_FREE) ** 2
chk("Tail-brace: buckling", Ft, Pcrt / SF, "N")

# 11) (there is no pin at the front-leg cut — manta_ribbon.py only places
#      the dia 10 pin at the 2 cuts beside the lumbar (pin_j), so the front
#      leg joint relies on the tenon + epoxy face alone; a "leg pin shear"
#      check would be testing a part that isn't actually printed)

# 12) FORK PRONG — bending from a sideways push (a person leaning sideways)
#     one prong carries the sideways force as an angled fixed rod
M_prong = Hs * PRONG_SPLAY_LEN
chk("Fork prong: bending (sideways lean)", M_prong / Z(PRONG_W, PRONG_TH), sa, "MPa")

# 13) JOINT prong<->ribbon — full section + tenon, bending from the sideways force
F_pr = M_prong / (0.7 * PRONG_TH)
chk("Fork joint: epoxy tension", F_pr / (0.5 * PRONG_W * PRONG_TH * FACE_EFF), etn, "MPa")

# ── tipping (computed at import time too, so callers can read it without
# re-running the printed report) ──
mp = M_KG; cp = CHAIR_KG
def com(px, ph):
    x = (mp * px + cp * CHAIR_COM_X) / (mp + cp)
    h = (mp * ph + cp * 300.0) / (mp + cp)
    return x, h
_xu, _hu = com(COM_UP_X, COM_UP_H)
_xl, _hl = com(COM_LEAN_X, COM_LEAN_H)
TIP_REAR_UP   = (_xu - (-FOOT_BACK_X)) / _hu
TIP_REAR_LEAN = (_xl - (-FOOT_BACK_X)) / _hl
TIP_FWD       = (FOOT_FRONT_X - _xu) / _hu
TIP_SIDE      = FOOT_HALF_Y / _hu


def worst_margin():
    """(margin, name) of the weakest row — used by manta_ribbon.py to gate
    exports. Rows are already computed above, at import time, from the LIVE
    W_S/TH_S tables, so this always reflects the current parameters."""
    return min(((m, n) for n, a, al, m, ok, u, note in rows), key=lambda t: t[0])


if __name__ == "__main__":
    # ── report ──
    print("\nMANTA — one continuous ribbon: strength check")
    print(f"person {M_KG:.0f} kg - dyn {DYN} - SF {SF} - infill {INFILL:.0%}")
    print(f"W vertical {W:.0f} N - Hb into backrest {Hb:.0f} N - Hs sideways {Hs:.0f} N\n")
    print(f"{'LOCATION':38s}{'VALUE':>9s}{'ALLOW.':>9s}{'MARGIN':>7s}  STATUS")
    worst = (9e9, "")
    for n, a, al, m, ok, u, note in rows:
        if m < worst[0]:
            worst = (m, n)
        print(f"{n:38s}{a:8.1f}{u[:3]:>3s}{al:8.1f}{u[:3]:>3s}{m:6.1f}x  {'OK' if ok else 'X FAIL'}")

    print(f"\nWEAKEST LINK: {worst[1]}  (margin {worst[0]:.1f}x)")
    print(f"MAX safe weight (SF={SF}, dyn={DYN}): ~{M_KG * worst[0]:.0f} kg")

    print("\nTipping stability (ratio > 0.5 = good, 0.3-0.5 = OK for normal use):")
    print(f"  rearward (sitting upright): {TIP_REAR_UP:.2f}")
    print(f"  rearward (leaning into the backrest): {TIP_REAR_LEAN:.2f}")
    print(f"  forward: {TIP_FWD:.2f}")
    print(f"  sideways (splayed pad): {TIP_SIDE:.2f}")

    print("\nINCREASE THESE IF MARGIN < 1.5:")
    for n, a, al, m, ok, u, note in rows:
        if m < 1.5:
            print(f"  {n}  (margin {m:.1f}x)")
    print("\n(first-order, not FEA. Physical joint test: manta_joint_test.py.)\n")
