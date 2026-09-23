# MANTA — the "one ribbon" chair (Open Chair)

![MANTA poster](TEAMID_Poster.jpg)

The whole chair is **one continuous ribbon**, **sliced crosswise** (like a
baguette) so every part fits a home printer and every joint stays strong.
Named for the manta ray — the forked feet read as fins, the tail-brace as a
fluke — and for the ocean's role as the planet's largest source of oxygen,
which the surface relief carries in its own graded texture, bold at the
floor and calming toward the crown.

No two of its 41 printed segments are identical, on purpose: nothing in
nature repeats, so nothing here does either. Change a few tables in
`manta_ribbon.py` and the same script regenerates a lighter, cheaper, or
differently-sized chair with the same joints — this repo *is* that script.

📄 [Full description (PDF)](TEAMID_Description.pdf) · 🖼 [Board](TEAMID_Board.jpg) · 🖼 [Poster](TEAMID_Poster.jpg)

Shared under **CC BY-NC-SA** — free to study, adapt, and reprint; not for
commercial resale.

---

## Requirements (Python packages)

```
pip install cadquery numpy scipy shapely trimesh matplotlib vtk pypdfium2 reportlab pillow
```

The first 3 are enough for the geometry itself. The rest are for the
renders / board / poster / PDF.

---

## Run order

| # | command | what it does | output |
|---|---|---|---|
| 1 | `python manta_ribbon.py` | **generator** — builds the ribbon, **slices it**, adds tenons + pins, exports the parts and the assembled chair | `MANTA_RIBBON/` |
| 2 | `python manta_apply_template.py` | embeds the chair + numbered parts into the **official, unmodified** `3D_Template.stl` (chair centred in its 800x800mm footprint box, each part in its numbered 220x220x250mm cell) | overwrites `MANTA_RIBBON/MANTA_Chair.stl` + `MANTA_Assembly.stl` |
| 3 | `python manta_strength_check.py` | **strength + stability check** (first-order, pure math, live from the tables — also run automatically by step 1) | printed to the console |
| 4 | `python manta_ergonomics_check.py` | **ergonomics check** — 8 seat/backrest dimensions vs seating reference ranges | printed to the console |
| 5 | `python manta_uniqueness_check.py` | **uniqueness check** — proves no two segments share volume/area/bbox | printed to the console |
| 6 | `python manta_joint_test.py` | **physical joint test** — small pieces to print and glue | `MANTA_TEST/` |
| — | *renders and submission files:* | | |
| 7 | `python manta_render.py` | renders (poster + board views) | `_deliver/` |
| 8 | `python manta_explode.py` | exploded view + parts grid | `_deliver/` |
| 9 | `python manta_pdf.py` | description -> PDF | `TEAMID_Description.pdf` |
| 10 | `python manta_poster.py` | A2 poster | `TEAMID_Poster.jpg` |
| 11 | `python manta_board.py` | A2 board (on the official template) | `TEAMID_Board.jpg` |
| 12 | `python manta_package.py` | packs the submission files + checks total size | `ODOVZDANIE/` |

**Part numbering**: the official `3D_Template.stl` numbers its 49 cells
column-major (1,8,15,22,29,36,43 down column 1; 2,9,16,... down column 2;
etc) — that's fixed, unmodifiable template geometry. The Board's own key
graphic lays its numbers out row-major instead. Both are correct: only the
*number* has to match between the two (part "5" on the Board = part "5" in
the STL's cell "5"), not the box's on-page position.

**Slicing is NOT a separate file** — it lives inside `manta_ribbon.py`, in the
`build()` function: it makes crosswise cuts (by length + curvature, avoiding
the knee and lumbar), a lengthwise L/R cut on wide segments, conical tenons
at every cut, and a dia 10 pin only at the lumbar joints.

---

## Printing the parts

`TEAMID_Assembly.stl` is the **competition submission** format: all 42 parts
placed inside the official `3D_Template.stl` grid, because the brief
requires that. That template geometry is a non-solid reference grid (lines +
text, not a printable object) — a slicer will still try to load it alongside
your parts, which is confusing and pointless for an actual print.

For printing at home, use [`MANTA_RIBBON/`](MANTA_RIBBON) instead: the same
42 parts, no template geometry mixed in. Each file is named
`NN_SEG_xxx.stl`, where `NN` is the part number from the Board's key and the
exploded-view diagram (`01_SEG_00L.stl` = part 1, `42_PIN.stl` = part 42,
and so on) — so the file list itself tells you what to print against the
Board, no cross-referencing needed. `PARTS_LIST.txt` in that folder has the
same numbering.

**Every file in `MANTA_RIBBON/` and `MANTA_LIGHT/` is pre-rotated to its own
support-free orientation** — import and print as-is, no manual rotation.
This used to be a per-part text note ("print STANDING") based on a rough
spline-turn heuristic that was never actually checked against the mesh; on
the real geometry it left an average 18% of each part's surface overhanging
past 45°, up to 38% on the worst parts — well into "the slicer will ask for
supports" territory regardless of what the note said.

`manta_orient.py` searches candidate build directions per part (including
the part's own largest flat faces, not just a generic sweep) and scores
each on *both* overhang and bed-contact footprint — minimising overhang
alone kept picking orientations balanced on a single point, great overhang
number, terrible adhesion. The result: average overhang down to ~5% (worst
~9%), and a solid footprint on all but 12-14 parts — the naturally tapered
foot-tip segments and the dia-10 pin, which just don't have a large flat
side to offer. Those are marked `[use a brim]` in `PARTS_LIST.txt`; flip on
a brim for just those parts in your slicer. Run it yourself on any
regenerated `SEG_*.stl` set: `python manta_orient.py MANTA_RIBBON`.

---

## How to tune it

Everything is set in the `PARAMETERS` block at the top of `manta_ribbon.py`:
- `SPINE` — the ribbon's side profile (X = forward, Z = up)
- `W_S` — width along the length · `TH_S` — thickness along the length (follows the bending moment)
- `TWIST_S` — spiral twist of the section
- `SEG_MAX`, `FORK_SPLAY`, `TEN_R`, `PIN_R` ... — slicing and joints

After printing the joint test, note which clearance (`0.08 / 0.12 / 0.16`)
holds best — set it as `TEN_CLR` and regenerate the final STLs.

**Every run of `manta_ribbon.py` re-checks itself.** Before exporting
anything, it calls `manta_strength_check.py`'s `worst_margin()`, which
re-derives the seat/lumbar/cut/leg section properties live from whatever
`W_S`/`TH_S` are currently set to (not a hand-copied snapshot) and runs the
same load case as the printed report. If tuning the tables has pushed the
weakest joint below the intended safety factor, generation stops with an
error instead of quietly writing an unsafe STL. Run
`python manta_strength_check.py` on its own any time for the full
13-check breakdown.

**A ready-made lighter variant — [`MANTA_LIGHT/`](MANTA_LIGHT).** Not
everyone needs a chair rated for a 120 kg dynamic sitter. `manta_ribbon_personal.py`
is the exact same generator with `TH_S` thinned to 75%; `manta_strength_check_personal.py`
re-verifies it at a 90 kg design target (still a healthy margin over a single
60 kg user, plus guests) — safe static load **~123 kg**, weakest joint
**1.4x**. `MANTA_LIGHT/` is the already-generated, numbered result: same 42
parts, same joints, ~40% less filament (**9.6 kg vs 16.2 kg**, run
`manta_material_personal.py` for the cost at your own filament price). This
is a demonstration variant, not the competition entry — the competition
files are untouched.

Want to print it in more than one colour? `python manta_colour_guide.py`
buckets the 41 segments into 4 filament colours by height (floor -> crown),
matching the same gradient the renders already use — prints exactly which
part numbers go in which colour and how many kg/EUR of each. Multi-colour
costs nothing extra: it's the same total filament, just split across spools.

---

## How the joint holds (so you don't have to worry)

The joint is **not "just a pin."** In order of importance:

1. **The full solid cross-section, glued face-to-face.** Every cut is
   perpendicular to the ribbon's axis, so you're gluing two flat faces of
   solid material against each other — 6,600–17,000 mm² of epoxy per joint.
   This is the main strength. (Margin in the strength check: **~27x**, at
   the weakest epoxied joint **~4.8x** — see `manta_strength_check.py`.)
2. **A conical tenon (dia 32)** at the centre of the cut — self-centring,
   and it carries the tension side so the joint can't "open up."
3. **A dia 10 pin** — ONLY at the 2 joints beside the lumbar. It's a
   **backup**, not the main joint. Even if the epoxy failed completely, the
   tenon + pin alone still give a **1.6x margin** there (hand-break tested).

Epoxy on PETG: **sand the face (P120) and degrease** before gluing — otherwise
the epoxy won't bond well. Leave it clamped to cure for 24 h.

---

## Code files

- `manta_ribbon.py` — generator + slicing + joints + export
- `manta_apply_template.py` — embeds the chair/parts into the official `3D_Template.stl`
- `manta_strength_check.py` — strength + stability
- `manta_ergonomics_check.py` — seat/backrest dimensions vs standard reference ranges
- `manta_uniqueness_check.py` — proves no two of the 41 segments are geometrically identical
- `manta_orient.py` — rotates each part to its lowest-overhang, support-free print orientation
- `manta_joint_test.py` — physical joint test
- `manta_material.py` — filament use + cost from the real STL parts
- the remaining `manta_*.py` files = rendering / submission packaging
- `MANTA_Description_DRAFT.md` — the description text (edit, then run `manta_pdf.py`)
- `_board_base.png` — the rasterised official board template (without instructions)
- `3D_Template.stl` — the official 3D print file template (unmodified, as provided)
- `MANTA_RIBBON/` — the 42 individual part STLs, clean and ready to print (no template geometry) — see "Printing the parts" above
