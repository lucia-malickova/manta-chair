# MANTA

**A wave that rose from the sea floor and stayed. One continuous ribbon, cut like a baguette so it prints at home and still holds an adult.**

## The story

Once, a wave rose from the sea floor and did not fall back. Its feet still
hold the seabed like the fins of a manta; its body swells into a seat,
climbs into a backrest and breaks at the crest, curling forward and falling
back *through* itself to the floor — one ribbon, no separate legs, no frame.
The colour follows the water: deep blue at the feet, turquoise through the
seat, pale foam at the crest. Every seam is left white — epoxy thickened
with silica, foamed like the spray between waves. Seen from the front, the
seat writes an **M**: for Manta, and for *Mare*, the sea that makes most of
the oxygen we breathe. Flutes follow the ribbon's motion, bold at the floor,
calming toward the crest, smooth where you sit.

## Biomimicry as structure, not ornament

- **Wolff's law** — thickness follows the bending moment: 84 mm at the lumbar knot, 32 mm at the crest.
- **Murray's law** — the lumbar, the one true junction, is the cube-root-sum of its branches.
- **Spiral fibre** — flutes follow the stress path and stiffen by corrugation; the section twists up to 20°.
- **Shell** — the closed section and dished seat carry load as a shell.
- **Fiddlehead scroll** — the crest curls back through the backrest: a closed loop, not a cantilever.
- **Buttress roots** — each foot forks into two splayed prongs.

## Built, and printable at home

41 segments (each ≤ 212 × 220 × 250 mm), auto-oriented: under 1 % of the
filament is support (PrusaSlicer), none inside the holes. PETG, 0.2 mm
layers, 35 % gyroid: ~16.5 kg, ~460 h on one printer, ~90 € filament +
~20 € epoxy. **A full-size prototype is printed and assembled** (the light
variant, 75 % wall thickness) — photos on the board.

## Assembly — computed joints, no screws

The script slices the ribbon crosswise by length and curvature, keeping
every cut ≥ 70 mm from the knee and lumbar, where bending peaks. Every joint
is a full solid cross-section (7,000–17,000 mm²), epoxied, with a
self-centring conical peg sized to the local thickness; the two most-loaded
joints add a solid Ø11 pin. Where the crest returns through the backrest it
is trimmed to the backrest's shape and glued on as a saddle. Part numbers
are engraved on the glue faces. One command (manta_verify.py) re-checks
everything: strength, a **virtual assembly** (pegs seated, 2 mm walls, no
overlaps), bed fit, real-slicer support.

## Stability and load

First-order check (120 kg × 1.8 dynamic × 2.0 safety): every member passes;
glued full-section joint 26×, weakest glued check 2.1×; with no glue at all,
peg and pin still carry 0.9×. Tipping 0.56 sideways, 0.55–0.77 rearward;
safe static load ~250 kg; 8/8 ergonomics checks pass.

## Open design — nothing repeats

Nothing in nature repeats, so no two of the 41 segments do either. Change
the tables and the script regenerates a leaner chair with its joints and
checks; the 70 kg variant built here is in the repo.
