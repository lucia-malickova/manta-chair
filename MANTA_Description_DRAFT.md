# MANTA

**One continuous ribbon. One gesture. Cut like a baguette so it can be printed at home and still hold an adult.**

## Idea

MANTA is a single thick ribbon: floor, dished seat, cantilevered backrest,
forward-curled crown, tail-brace, back to the floor — no separate legs, no
frame, no visible assembly. The name is literal: forked feet read as fins,
the tail-brace as a fluke. The ocean makes most of the oxygen we breathe,
and the manta ray is one of its health indicators — so the surface carries
the story too: flutes that follow the ribbon's own motion, bold at the
floor and easing toward the crown, capped where you sit so they never press into a bone.

## Biomimicry as structure, not ornament

Each rule sets the section, and each carries load:

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

41 segments, each within 212 × 220 × 250 mm, auto-oriented for the least
support: over half print with **none**, the rest need a little, from the
build plate only. PETG, 0.2 mm layers, 5 perimeters, 35 % gyroid,
solid pins. ~16 kg, ~180 h of printing, ~90 € of filament.

## Assembly — computed joints, no screws

Cuts and joints are computed, not drawn by hand. The script slices the
ribbon **crosswise** by length and curvature, keeping every cut ≥ 70 mm from
the knee and lumbar where bending peaks, so those knots sit whole,
mid-segment. Every joint is a full solid cross-section (7,000–17,000 mm²),
epoxied, with a self-centring conical peg sized to the local thickness,
centred on its face, shrunk until its socket keeps a 2 mm wall.
Wide segments split along a flute-hidden keel. Only the two most-loaded
lumbar joints add a solid Ø11 pin. Every part's number is engraved on a glue face. A virtual assembly
verifies every peg seats in its neighbour.

## Stability and load

First-order check (120 kg × 1.8 dynamic × 2.0 safety): every member passes; glued full-section joint 26×,
weakest glued check 2.1×; with no glue at all, peg and pin still carry
0.9×. Tipping 0.56 sideways, 0.55–0.77 rearward; safe static load
~250 kg. Seat 429 × 364 mm, 428 mm high; 8/8 ergonomics checks pass.

## Open design — nothing repeats

Nothing in nature repeats, so no two parts of this chair do either: all 41
segments are geometrically unique (script-verified, no duplicates). Change
the tables and the same script regenerates a leaner chair, joints and
load checks included; a 90 kg, 40 % lighter variant is in the repo (anonymised source link below).
