# MANTA — the "one ribbon" chair (Open Chair)

The whole chair is **one continuous ribbon**, **sliced crosswise** (like a
baguette) so every part fits a home printer and every joint stays strong.

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
| 2 | `python manta_strength_check.py` | **strength + stability check** (first-order, pure math) | printed to the console |
| 3 | `python manta_joint_test.py` | **physical joint test** — small pieces to print and glue | `MANTA_TEST/` |
| — | *renders and submission files:* | | |
| 4 | `python manta_render.py` | renders (poster + board views) | `_deliver/` |
| 5 | `python manta_explode.py` | exploded view + parts grid | `_deliver/` |
| 6 | `python manta_pdf.py` | description -> PDF | `TEAMID_Description.pdf` |
| 7 | `python manta_poster.py` | A2 poster | `TEAMID_Poster.jpg` |
| 8 | `python manta_board.py` | A2 board (on the official template) | `TEAMID_Board.jpg` |
| 9 | `python manta_package.py` | packs the submission files + checks total size | `ODOVZDANIE/` |

**Slicing is NOT a separate file** — it lives inside `manta_ribbon.py`, in the
`build()` function: it makes crosswise cuts (by length + curvature, avoiding
the knee and lumbar), a lengthwise L/R cut on wide segments, conical tenons
at every cut, and a dia 10 pin only at the lumbar joints.

---

## How to tune it

Everything is set in the `PARAMETERS` block at the top of `manta_ribbon.py`:
- `SPINE` — the ribbon's side profile (X = forward, Z = up)
- `W_S` — width along the length · `TH_S` — thickness along the length (follows the bending moment)
- `TWIST_S` — spiral twist of the section
- `SEG_MAX`, `FORK_SPLAY`, `TEN_R`, `PIN_R` ... — slicing and joints

After printing the joint test, note which clearance (`0.08 / 0.12 / 0.16`)
holds best — set it as `TEN_CLR` and regenerate the final STLs.

---

## How the joint holds (so you don't have to worry)

The joint is **not "just a pin."** In order of importance:

1. **The full solid cross-section, glued face-to-face.** Every cut is
   perpendicular to the ribbon's axis, so you're gluing two flat faces of
   solid material against each other — 6,600–17,000 mm² of epoxy per joint.
   This is the main strength. (Margin in the strength check: **15x**.)
2. **A conical tenon (dia 32)** at the centre of the cut — self-centring,
   and it carries the tension side so the joint can't "open up."
3. **A dia 10 pin** — ONLY at the 2 joints beside the lumbar. It's a
   **backup**, not the main joint. Even if the epoxy failed completely, the
   tenon + pin alone still give a **2.2x margin** there.

Epoxy on PETG: **sand the face (P120) and degrease** before gluing — otherwise
the epoxy won't bond well. Leave it clamped to cure for 24 h.

---

## Code files

- `manta_ribbon.py` — generator + slicing + joints + export
- `manta_strength_check.py` — strength + stability
- `manta_joint_test.py` — physical joint test
- `manta_material.py` — filament use + cost from the real STL parts
- the remaining `manta_*.py` files = rendering / submission packaging
- `MANTA_Description_DRAFT.md` — the description text (edit, then run `manta_pdf.py`)
- `_board_base.png` — the rasterised official board template (without instructions)

Older versions (CHRBTICA, LEKNO, VETVA) are in `stare/` — no longer used.
