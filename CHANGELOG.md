# Changelog

## 2.2.1 — 2026-10-31

Sample plan rebuilt on a typical small single-story
pattern. No code change, only the sample and its tests.

- The v2.2.0 full-width hallway is gone: it was 128 sq
  ft of corridor that shrank the bedrooms to 8 ft deep.
  Typical small plans keep circulation to a minimum and
  cluster bedrooms on one side of the house, with living
  and kitchen flowing together on the other.
- New layout: open Living Room (20 x 14) and Kitchen
  (12 x 14) across the south half, with an open passage
  between them; a short central Hall (6 x 7, 42 sq ft)
  in the bedroom wing, entered from the Living Room,
  serving a Master Bedroom (14 x 13, 182 sq ft), a
  Bedroom 2 (12 x 13, 156 sq ft), and a hall Bathroom
  (6 x 6, 36 sq ft) at the end of the hall. No room is
  reached through another room. Front door into the
  Living Room (west wall), Garage door into the Living
  Room, Garage door to the driveway.
- The Bathroom door sits at the west end of its wall
  (2.5 ft wide) so its leaf and arc stay clear of the
  room's centred label — a centred 3 ft door in a 6 ft
  room drew straight through it.

## 2.2.0 — 2026-10-31

The sample plan is now a house you can actually walk
through, plus the format support that makes it possible.
No breaking change: existing plans still validate.

- **Open passageways: `swing: "none"`.** A door with
  `swing: "none"` cuts a wall gap but draws no leaf or
  arc, in the Python loader, the JSON Schema, and the
  editor validator (standalone door openings too, where
  it draws only the dashed segment). The editor has no
  passage tool yet: a passage imported into the editor
  keeps `swing: "none"` on re-export, but the canvas
  still draws it as a door.
- **Sample circulation rebuilt.** A real 4 ft Hallway
  (y 15-19, 128 sq ft) runs across the house, entered
  from the Living Room, with a door to each of the
  Master Bedroom, Bathroom, and Bedroom 2. Bedrooms
  shrank from 12 ft to 8 ft deep to make room for it
  (Master 120, Bathroom 56, Bedroom 2 80 sq ft). A front
  entrance now exists: a west-wall door into the Living
  Room, alongside the Living-Garage door and the Garage
  door. The Living-Kitchen swing door is now an open
  passage (`swing: "none"`).
- **Paired-door rule, documented in the sample.**
  Every room draws its own walls, so a door between two
  rooms must be listed in both rooms with opposite
  swing flags ("in" for the room it swings into, "out"
  for the other), or one side's wall draws across the
  gap. The sample does this for every inter-room door.
- **Boundary breaks at exterior doors.** The boundary
  was a closed polygon, which drew straight over the
  gap a room wall had cut and hid exterior doors. It is
  now drawn edge by edge, breaking at any door lying
  on an edge — including the reversed closing edge,
  where the gap interval had to be min/max-sorted or
  no gap appeared at all (caught by the new test).
- Tests lock the circulation in: the sample's
  bedroom/bathroom doors are exactly the Hallway's
  doors, the passage is in both rooms with `"none"`,
  and no door is shared directly between two bedrooms.

## 2.1.1 — 2026-10-31

Render fixes for the artifacts in the sample render, plus the
sample plan itself. No plan-format change.

- **Doors are doors now.** `_draw_doors` draws an open leaf
  plus a full quarter-circle arc, with the hinge at the
  minimum-coordinate endpoint. Previously horizontal arcs
  were offset 90 degrees (a bottom-wall door swinging in
  drew theta 90-144, north-west of its hinge, instead of
  0-90 — the Garage door's arc landed in the title block),
  vertical arcs were truncated to a stylised 54 degrees,
  and a line plotted along the wall filled the wall gap
  back in, so only a stray-looking arc remained.
- **North arrow "N" visible.** A FancyArrow's tip is at
  shaft length + head length; the label sat at shaft length
  only, centred on the black head, so it was invisible. It
  now sits 5 points above the actual tip.
- **Boundary labels are bounding-box dimensions** for any
  shape, placed outside the box — not corner labels that
  were wrong for non-rectangles.
- **Sample plan fixed.** The Hallway room (identical
  rectangle to the Bathroom, so labels/walls/doors
  double-drew) is removed; its doors were duplicates of
  the Master Bedroom and Bedroom 2 doors, which remain.
  The boundary is now the L-shaped union outline of the
  rooms, enclosing the Garage; the empty southeast corner
  is outside the house and not enclosed. `docs/demo.svg`
  and the JSON twin are regenerated from the fixed sample.
- Known minor, left alone: room dimensions are drawn
  inside rooms, so a door arc can cross a dimension line
  (the Master Bedroom 12 ft line sits behind its door
  arc). Moving dimensions outside is a separate change.

## 2.1.0 — 2026-10-31

Staff-review fixes, on top of the 2.0.0 merge. Nothing here
changes the plan format, the `floorplan` command, or the
editor's object model.

- **Style errors are clean CLI errors now.** `load_style`
  wraps YAML parse errors and rejects styles missing the
  `settings`/`line_styles`/`text_styles` sections (or a
  `background_color`) with a `ValueError` naming the file,
  and the CLI also catches `KeyError`, so a custom `--style`
  file can no longer produce a traceback.
- **Shared wall tolerance.** `room.py` gains
  `WALL_TOLERANCE_FT = 0.01`, matching
  `editor/modules/plan.js`: door-gap matching and door-wall
  detection (previously exact float equality) use it, and
  `get_window_wall_info` defaults to it. A door the editor
  attaches within 0.01 ft of a wall now actually splits that
  wall in the render.
- **Editor:** undo history is capped at 100 entries;
  autosave/restore failures warn on the console and show a
  footer note instead of failing silently; importing a YAML
  file gives an actionable error pointing at
  `floorplan convert` (import remains JSON-only);
  `state.js` imports `PIXELS_PER_FOOT` from `plan.js` and
  the footer scale label is rendered from it; the dead
  `syncGlobals` shim is removed; `drawGrid` uses the real
  scale below 100% zoom instead of clamping it to 1.
- **Renderer hardening.** `load_plan`/`dump_plan` reject
  unknown suffixes; `dump_plan` creates parent directories
  and writes atomically (temp file + rename); unquoted YAML
  dates are accepted as metadata; `parse_scale` accepts
  whitespace and plain numbers and `parse_paper_size`
  accepts whitespace/case variants, and both raise on
  unknown input instead of silently falling back; boundary
  dimension labels are computed from the bounding box and
  only for axis-aligned rectangles; oversize plans log a
  clipping warning (visible with `--verbose`); `render`
  gains `--no-extras` to skip the settings/page-section
  pages; scaling uses named `UNITS_PER_INCH` /
  `POINTS_PER_INCH` constants with the 1-unit = 1-point
  invariant documented.
- **Version, single-sourced.** `floorplan.__version__` is
  read from installed metadata (`pyproject.toml` is the
  source); a CI step fails when `pyproject.toml` and
  `editor/package.json` versions differ.
- **Plan contract.** New `schema/plan-v1.json` (JSON Schema
  for the format) plus `scripts/check-schema.py`, a CI
  `contract` job that validates the examples against it,
  renders an editor export produced by
  `editor/scripts/export-golden.mjs` in Python, and diffs
  the example JSON twin against a fresh YAML conversion.
- **Docs.** README rewritten (Description, Prerequisites,
  Installation, Local Development, Deployment, plus Usage,
  Plan format, Architecture, Known limits, Contributing);
  new `docs/assets/architecture.svg`; Dependabot enabled
  for pip, npm, and GitHub Actions.
- **Deferred, deliberately:** the editor modularization
  (`script.js` split, explicit `utils.js` parameters), the
  renderer scene-graph split, the door-arc/label/dimension
  dedup refactors, and mypy/ESLint enforcement. They are
  geometry- or structure-sensitive and belong in their own
  changes on top of the contract job above.

## 2.0.0 — 2026-10-28

Merged `ss-floorplan` (Python renderer) and `ss-floor_plan_creator` (browser editor) into one repo, `floorplan-studio`, under a shared plan format (version 1). Both stacks are kept; neither was rewritten in the other's language. Squashed export: the earlier single-commit histories are intentionally not included.

### Shared format

- New canonical plan shape (feet, bottom-left origin): `rooms` with `rect`/`doors`/`windows`, plus optional `boundary`, `walls`, `openings`, `labels`, `dimensions`, `objects`, and `title`/`address`/`date` metadata. YAML and JSON carry the same shape.
- New `editor/modules/plan.js`: pure conversion between canvas objects and plans, room-edge attachment for doors/windows, a minimal YAML serializer, and plan validation. Covered by `node --test` round-trip tests.
- New renderer CLI: `floorplan render` (SVG/PNG/PDF, `--style`, `--output-dir`, title/address/date overrides) and `floorplan convert` (YAML <-> JSON). The bundled style file ships as package data.

### Editor

- Added Export JSON, Export YAML, and Import JSON controls; work autosaves to localStorage as a plan and restores on reload.
- Built Tailwind CSS (`dist/styles.css`) is now committed, so a fresh clone renders styled without a build step; CI checks the committed CSS is fresh.
- Removed debug code: the red test rectangle drawn on load, `console.log` tracing, and the MutationObserver that logged modal openings. The clear-confirmation text no longer claims the action cannot be undone (Undo restores it).
- Toolbar clicks now only activate real tools; export/import/clear/undo/redo buttons no longer fall through to tool selection. The object-library modal opens through the shared modal helpers.
- `package.json`: renamed to `floorplan-editor`, `private` removed, Tailwind/PostCSS/Autoprefixer pinned, `type: module`, `test`/`check`/`build:css` scripts added. Committed `package-lock.json`.

### Renderer

- `drawing.py` rewritten as single definitions. The original defined `parse_scale`, `parse_paper_size`, `draw_boundary`, and `draw_north_arrow` three times each (the first copy was also spliced mid-docstring); the surviving north-arrow copy took page dimensions as offsets and placed the arrow off-page. The arrow is now placed from the page size.
- The output directory is now created when missing; the original crashed with `FileNotFoundError` on a fresh checkout because `output/` was gitignored and never created.
- Fixed door-gap placement: wall-segment gaps used a hardcoded scale of 25.0 and offset 0 instead of the plan's scale/offset, so gaps drifted off walls once the plan was centred or at another scale.
- `style_loader` now resolves `@palette` references recursively (nested dicts/lists, chained references) and raises on an unknown reference instead of silently producing `None`.
- `data_loader` now loads YAML and JSON, validates segment shapes (doors/windows must be axis-aligned), `swing` values, boundary points, and rejects booleans as numbers. Plan metadata (title/address/date) overrides style settings; CLI flags override both.
- Renderer now also draws standalone `walls`, `openings`, `labels`, `dimensions`, and `objects` (stairs/roads as labelled rectangles) from editor exports.
- Packaged as an installable `floorplan-studio` distribution (`pyproject.toml`); the import package and the `floorplan` console script / `python -m floorplan` entry point are unchanged, with `Room` validation and the settings/page-section diagrams taking the output directory and format.
- Default font family changed from Arial (missing on Linux, warned on every render) to DejaVu Sans in the bundled and example style files.
- Removed `generator.py`: a dead `plt.show()` prototype that duplicated the room geometry and was never used by `main.py`. Its example is covered by `examples/floor_plan.yaml`.
- Added pytest suite (loader, rendering, CLI) and ruff config; the original had no tests, packaging, LICENSE, or CI.

### Repo-wide

- MIT LICENSE added. `.gitattributes` forces LF endings. New CI runs the Python tests/lint on Ubuntu and Windows and the editor tests, syntax check, and CSS-freshness check on Node 20/22/24.
- The only remaining `ss-floorplan` / `ss-floor_plan_creator` strings are in this changelog and the history note in the README.
