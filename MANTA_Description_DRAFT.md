# MANTA

**The ocean makes the oxygen we breathe, and it is full of our plastic. MANTA is a wave of it, printed with under 1 % waste.**

## The story — oxygen, waste and a wave

At least half of the oxygen we breathe comes from the ocean, so MANTA is a
story of life: a wave that rose from the sea floor and stayed. Its feet hold
the seabed like the fins of a manta, the ray that tells us how healthy the
sea is. Seen from the side, legs, seat and back draw an M, for Manta and for
*Mare*, the sea. The colour is the depth of the water: deep blue at the
feet, turquoise through the seat, foam at the crest, where the ribbon breaks
forward like a wave and falls back through itself. Every seam is left white,
epoxy thickened with silica, like spray between waves, and the flutes follow
the current: bold at the floor, calm at the crest, smooth where you sit.

But the ocean is also full of our plastic, and MANTA is plastic too. So it
had to waste almost nothing. Home 3D prints often throw away a pile of
supports; this chair needs under 1 % of its filament for them, and none is
trapped inside a hole.

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
seat, joints, legs, tail brace, feet and the crossing — at 120 kg × 1.8 dynamic × 2.0 safety, plus
tipping; if a glued one falls short, it refuses to export. Weakest glued
check 2.1×, tipping 0.56 sideways, 0.55–0.77
rearward, 8/8 ergonomics checks. One command (manta_verify.py) re-checks it
all: a **virtual assembly** of all 43 parts (pegs seated, 2 mm walls, no
overlaps), bed fit, and the support PrusaSlicer really adds.

## Built — computed joints, printed at home

Cuts avoid the knee and lumbar, where bending peaks. Every joint is a full
solid cross-section, epoxied, with a self-centring conical peg sized to the
local thickness; the two most-loaded add a solid Ø11 pin; where the crest
crosses the backrest it is glued on as a saddle. 43 parts, each ≤ 212 × 220 × 250 mm; PETG: ~16.5 kg, ~460 h,
~90 € filament + ~20 € epoxy. **A full-size prototype is printed and
assembled** (light variant, 75 % walls) — photos on the board.

## Open design — nothing repeats

No two of the 42 ribbon pieces are alike. Change the tables and the script
regenerates a leaner chair, joints and checks included; the 70 kg variant
built here is in the repo.
