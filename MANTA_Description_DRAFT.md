# MANTA

**The ocean makes the oxygen we breathe, and we fill it with plastic. MANTA is a wave from that ocean, made by an algorithm so you print only what you need.**

## The idea

At least half of the oxygen we breathe comes from the ocean, so MANTA is a
story of life: a wave that rose from the sea floor and stayed, one continuous
ribbon printed at home in 43 parts and glued without a single screw. Its forked feet are
the fins of a manta, the ray that tells us how healthy the sea is. From the
side, legs, seat and back draw an M, for Manta and for *Mare*. Its colour is
the depth of the water, deep blue at the feet to foam at the crest, and every
seam is left white, like spray.

Yet we fill that ocean with plastic; microplastics are now found even in
human blood, and more and more of us, children too, print plastic at home.
MANTA is plastic as well, so it is printed with sense: material only where
the load is, almost no waste, recycled PETG recommended.

## Printing — at home, almost no waste

Every part fits a 220 × 220 × 250 mm home printer. The algorithm turns each
part to the position needing least support and shapes its holes for it: supports are under 1 % of the filament, none trapped inside a
hole. PETG, 0.2 mm layers, 35 % gyroid: ~16.5 kg, ~460 h on one printer.

## Assembly — like furniture, no screws

The ribbon is cut crosswise, away from the knee and lumbar where bending
peaks, so every joint is a full solid cross-section glued face to face. A
printed conical peg centres each joint (0.12 mm play, tested on a printed
sample); the two most-loaded joints are pinned; where the crest crosses the
backrest it is glued on as a saddle. Parts are numbered; the board shows six
steps.

## Strength and stability

Biomimicry sizes each section:

- **Wolff's law** — thickness follows the bending moment: 84 mm at the lumbar, 32 at the crest.
- **Murray's law** — the lumbar junction is the cube-root-sum of its branches.
- **Fiddlehead loop** — the crest returns through the backrest: a closed loop.
- **Buttress roots** — forked feet: a wide stance from little material.

Checked at 120 kg × 1.8 dynamic × 2.0 safety: weakest glued joint 2.1×;
tipping 0.56 sideways, 0.55–0.77 rearward; 8/8 ergonomic dimensions. A
full-size prototype is printed and standing — photos on the board.

## Open design — the algorithm

The algorithm was written for MANTA. Choose who the chair is for and how
thick it is: it rebuilds every cut, peg and joint, re-checks strength and
stability, and refuses to export a chair that would fail. So anyone prints
only the plastic they need: the 70 kg version built here uses half the
filament. The source is open to download, change and print;
manta_verify.py re-checks it all.
