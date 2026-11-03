# MANTA

**A wave that rose from the sea floor and stayed. One continuous ribbon, cut like a baguette so it prints at home and still holds an adult.**

## The story — every part means something

Once, a wave rose from the sea floor and did not fall back. MANTA is that
wave: one ribbon, no separate legs, no frame — and nothing on it is
decoration without a meaning.

- **Fins** — each foot forks into two splayed prongs: a manta's fins resting on the seabed.
- **M** — seen from the side, legs, seat and back draw an M: for Manta, and for *Mare*, the sea that makes most of the oxygen we breathe.
- **The crest** — the ribbon breaks forward like a wave and falls back *through* itself.
- **Colour** — the depth of the water: deep blue feet, turquoise seat, foam-pale crest.
- **Foam** — every seam is left white, epoxy thickened with silica, like spray between waves.
- **Current** — flutes follow the ribbon's motion, bold at the floor, calm at the crest, smooth where you sit.

## Biomimicry — every section sized by its load

- **Wolff's law** — thickness follows the bending moment: 84 mm at the lumbar knot, 32 mm at the crest.
- **Murray's law** — the lumbar, the one true junction, is the cube-root-sum of its branches.
- **Spiral fibre** — flutes run along the stress path and stiffen by corrugation.
- **Shell** — the closed section and dished seat carry load as a shell.
- **Fiddlehead loop** — the crest returns through the backrest: a closed loop, not a cantilever.
- **Buttress roots** — forked feet: a wide stance from little material.

## Engineering that checks itself

The script that draws the chair also proves it. Every run re-derives each
member's section from the live thickness tables and checks 15 load paths —
seat, lumbar, cuts, pegs, glue, legs and tail brace in compression and
buckling, feet, the crossing — at 120 kg × 1.8 dynamic × 2.0 safety, plus
tipping; if a glued one falls short, it refuses to export. Result: weakest glued
check 2.1×, safe static load ~250 kg, tipping 0.56 sideways and 0.55–0.77
rearward, 8/8 ergonomics checks. One command (manta_verify.py) then
re-checks everything: a **virtual assembly** of all 43 parts (pegs seated,
2 mm walls, no overlaps), bed fit, and the support PrusaSlicer really adds.

## Built — computed joints, printed at home

Cuts avoid the knee and lumbar, where bending peaks. Every joint is a full
solid cross-section, epoxied, with a self-centring conical peg sized to the
local thickness; the two most-loaded add a solid Ø11 pin; where the crest
crosses the backrest it is glued on as a saddle. Numbers are engraved on
the glue faces. 41 segments (≤ 212 × 220 × 250 mm), under 1 % support,
none inside a hole; PETG: ~16.5 kg, ~460 h, ~90 € filament + ~20 € epoxy.
**A full-size prototype is printed and assembled** (light variant, 75 %
walls) — photos on the board.

## Open design — nothing repeats

No two of the 41 segments are alike. Change the tables and the script
regenerates a leaner chair, joints and checks included; the 70 kg variant
built here is in the repo.
