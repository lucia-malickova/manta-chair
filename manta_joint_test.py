#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANTA — one continuous ribbon: JOINT TEST  (small, print this FIRST)
==============================================
The exact joint that holds the chair together:

  1) The FULL SOLID SECTION glued face-to-face (here ~70x44 = 3080 mm^2;
     up to 17,000 mm^2 at the lumbar)
  2) A CONICAL PEG (dia 27 at the face) on the cut axis — the SOCKET has the SAME cone
     + a uniform clearance, so the tenon seats FULLY and the joint "lands"
     on the cut FACE (not by wedging on a taper mismatch).
  3) A crosswise solid PIN dia 11 that runs THROUGH THE SOCKET *and through the
     TENON* -> the tenon cannot be pulled out. The hole is at the same
     distance (PIN_INTO) from the cut face in BOTH pieces, so the holes
     line up once the parts are seated.

The pin is not the main joint — it is a backup. The face + tenon hold the
load.

── HOW TO TEST ───────────────────────────────────────────────────────
1. Print  TEST_TENON + TEST_SOCKET + TEST_PIN (pin at 100% infill). PETG 0.2 / 5 walls / 35%
   gyroid (the whole chair now prints at 35% infill, not 55% — see
   manta_strength_check.py). Both halves with the cut face DOWN. ~2 h.
2. Dry-fit: push the tenon in until both cut faces meet. The pin holes must
   line up -> push the pin through the socket + tenon.
     - tenon too tight  -> increase CLR by 0.03, reprint
     - tenon too loose  -> decrease CLR by 0.03
3. Once it fits: sand the cut face (P120) + degrease, epoxy the WHOLE face,
   insert, pin, clamp, 24 h.
4. Try to break it by hand in bending. Tell me which CLR worked.

RUN:  python manta_joint_test.py
"""
import os
import cadquery as cq
from cadquery import Vector

import manta_ribbon as st                     # same joint numbers as the real chair

CLR = st.TEN_CLR                              # <<< socket clearance
W, D = 70.0, 44.0                             # test cross-section
BLOCK_L = 40.0                                # block length (excluding the tenon)
TEN_TIP = st.TEN_TIP
TEN_R = (st.TEN_R + st.TEN_TIP) / 2            # peg radius AT the cut face (dia 27)
TEN_L = st.TEN_L / 2                          # protruding peg length (22 mm)
PIN_R, PIN_CLR = st.PIN_R, st.PIN_CLR         # solid pin dia 11
PIN_INTO = TEN_L * st.PIN_POS                 # hole distance from the cut face (both pieces)
OUT = "MANTA_TEST"


def rbox():
    b = cq.Solid.makeBox(W, BLOCK_L, D, Vector(-W / 2, 0, -D / 2))
    b = cq.Workplane(obj=b).edges("|Y").fillet(8.0).val()
    return max(b.Solids(), key=lambda s: abs(s.Volume()))


def tenon_half():
    """block y[0,BLOCK_L]; tenon base sits in the cut plane y=BLOCK_L,
    protrudes outward to y=BLOCK_L+TEN_L."""
    b = rbox()
    c = cq.Solid.makeCone(TEN_R, TEN_TIP, TEN_L, Vector(0, BLOCK_L, 0), Vector(0, 1, 0))
    b = max(b.fuse(c).Solids(), key=lambda s: abs(s.Volume()))
    # hole THROUGH THE TENON, PIN_INTO beyond the cut plane
    h = cq.Solid.makeCylinder(PIN_R + PIN_CLR, W + 20,
                              Vector(-W / 2 - 10, BLOCK_L + PIN_INTO, 0), Vector(1, 0, 0))
    return max(b.cut(h).Solids(), key=lambda s: abs(s.Volume()))


def socket_half():
    """socket: the SAME cone + CLR, mouth in the cut plane y=0, depth TEN_L."""
    b = cq.Solid.makeBox(W, BLOCK_L + TEN_L + 8, D, Vector(-W / 2, 0, -D / 2))
    b = cq.Workplane(obj=b).edges("|Y").fillet(8.0).val()
    b = max(b.Solids(), key=lambda s: abs(s.Volume()))
    s = cq.Solid.makeCone(TEN_R + CLR, TEN_TIP + CLR - (TEN_R - TEN_TIP) / TEN_L * st.SOCK_EXTRA,
                          TEN_L + st.SOCK_EXTRA, Vector(0, 0, 0), Vector(0, 1, 0))
    b = max(b.cut(s).Solids(), key=lambda s: abs(s.Volume()))
    # 60-degree pointed end, same as the chair's sockets (prints without support)
    r_end = TEN_TIP + CLR - (TEN_R - TEN_TIP) / TEN_L * st.SOCK_EXTRA
    cap = cq.Solid.makeCone(r_end, 0.0, r_end * st.SOCK_TIP, Vector(0, TEN_L + st.SOCK_EXTRA, 0), Vector(0, 1, 0))
    b = max(b.cut(cap).Solids(), key=lambda s: abs(s.Volume()))
    # hole THROUGH THE SOCKET, PIN_INTO from the cut plane (mouth = y=0)
    h = cq.Solid.makeCylinder(PIN_R + PIN_CLR, W + 20,
                              Vector(-W / 2 - 10, PIN_INTO, 0), Vector(1, 0, 0))
    return max(b.cut(h).Solids(), key=lambda s: abs(s.Volume()))


os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith(".stl"):
        os.remove(os.path.join(OUT, f))

cq.exporters.export(tenon_half().translate(Vector(0, -BLOCK_L - 20, 0)),
                    f"{OUT}/TEST_TENON.stl", tolerance=0.1, angularTolerance=0.2)
cq.exporters.export(socket_half(),
                    f"{OUT}/TEST_SOCKET.stl", tolerance=0.1, angularTolerance=0.2)
cq.exporters.export(st._d_pin(W + 6, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),   # flat side down: print lying
                    f"{OUT}/TEST_PIN.stl", tolerance=0.1, angularTolerance=0.2)

print(f"CLR = {CLR:.2f} mm - pin {PIN_INTO:.0f} mm from the cut face in BOTH pieces")
print(f"tenon: cone {TEN_R*2:.0f}->{TEN_TIP*2:.0f} mm, length {TEN_L:.0f}  |  socket: same + {CLR:.2f}")
print(f"-> {OUT}/  (TEST_TENON + TEST_SOCKET + TEST_PIN)")
