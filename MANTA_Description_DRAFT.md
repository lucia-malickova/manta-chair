# MANTA

**One continuous ribbon. One gesture. Cut like a baguette so it can be printed at home and still hold an adult.**

## Idea

MANTA is a single thick ribbon: floor, dished seat, cantilevered backrest,
forward-curled crown, tail-brace, back to the floor — no separate legs, no
frame, no visible assembly. The name is literal: forked feet read as fins,
the tail-brace as a fluke. The ocean makes most of the oxygen we breathe,
and the manta ray is one of its health indicators — so the surface carries
the story too: flutes that follow the ribbon's own motion, bold at the
floor and easing toward the crown, capped near the seat and back so they
stay tactile without ever pressing into a bone.

## Biomimicry as structure, not ornament

Every centimetre of the section is set by a biological rule, and each is
load-bearing:

- **Wolff's law** — thickness follows the bending moment: 84 mm at the lumbar
  knot, 50 mm at the knee, a 32 mm blade at the crown.
- **Murray's law** — the lumbar, the one true junction, is the cube-root-sum
  of seat, backrest and tail; every transition filleted.
- **Spiral fibre** — the flutes follow the stress path and stiffen by
  corrugation; the section twists up to 20° through the backrest.
- **Shell curvature** — the closed superelliptical section and dished seat
  carry load in membrane action.
- **Fiddlehead scroll** — the forward-curled crown closes the backrest into a
  tube, not an open cantilever.
- **Buttress roots** — each foot forks into two splayed prongs.

## Printing

41 segments, each within 212 × 220 × 250 mm, printable **without supports**
(8 print upright) — every gram becomes chair, none is scrapped as support
waste for an ocean that has enough plastic in it already. PETG, 0.2 mm
layers, 5 perimeters, 35 % gyroid — kept low, thickness already carries the
load. Finished weight ~16 kg, ~180 h batch print time, ~90 € in filament.

## Assembly — screw-free

The ribbon is sliced **crosswise**, so every joint is a full solid
cross-section (7,000–17,000 mm²), never a thin plate edge: a self-centring
conical tenon (Ø32) plus epoxy. Wide segments also split along the
centre-line, seam hidden in a flute, reading as a keel. The two joints
beside the lumbar get an added Ø10 pin. No screws, no brackets.

## Stability and load

First-order check (120 kg × 1.8 dynamic × 2.0 safety) re-derived live from
the width/thickness tables: every member passes, weakest link 1.6×
without glue (confirmed by hand-breaking a printed coupon that held on the
pin alone), 4.8× at the weakest epoxied joint. Tipping 0.56 sideways,
0.55–0.77 rearward, safe static load ~190 kg. Seat 429 × 364 mm, 455 mm
high, 3° rearward tilt, convex lumbar.

## Open design — nothing repeats

Nothing in nature repeats, so no two parts of this chair do either: all 41
segments are geometrically unique (only the small locking pin repeats). One
parametric script: change the tables and it regenerates a leaner variant
with the same joints — automatically re-checked against the same load
case, so it can't silently export a variant that fails. Full source,
anonymised for review: anonymous.4open.science/r/manta-chair-23D4
