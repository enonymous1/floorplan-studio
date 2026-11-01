# Changelog

## 2.2.4 — 2026-11-01

- GitHub Pages workflow for the editor
  (`.github/workflows/pages.yml`, as documented in the
  README's Deployment section): on push to `main`
  touching `editor/**` or the workflow itself, or on
  manual dispatch, it runs the editor's test, syntax
  check, and CSS build, then deploys `editor/` via
  `configure-pages` / `upload-pages-artifact` /
  `deploy-pages`. One-time setup after push:
  Settings → Pages → Source: GitHub Actions.
- **Load sample** button in the editor's Plan section:
  it loads the bundled sample house straight into the
  canvas, no file needed. The sample is
  `editor/sample-plan.json`, a copy of
  `examples/floor_plan.json`, kept identical by a new
  CI contract check — it has to live inside `editor/`
  because the Pages artifact uploads only that folder,
  so the repo's `examples/` file never deploys. Load
  sample shares Import's code path exactly (history
  reset, autosave, redraw); like Import, it replaces
  the canvas, so export first if you want to keep
  your current work. If the editor was opened from a
  `file://` URL, the fetch cannot run and the alert
  says so, pointing at Import with the repo's example
  file instead.
- Two fixes Load sample exposed, both needed for the
  load -> export -> render loop to work at all:
  importing a paired plan used to put two identical
  door objects on the canvas (one per room listing),
  and exporting then listed each shared door twice
  in the first room and not at all in the second.
  Import now dedupes shared door/window segments
  (first listing wins), and the renderer now gaps a
  shared wall at any door listed by either room
  (wall gaps come from every door in the plan, not
  just the room's own; leaf/arc drawing is unchanged
  and still comes from the listing room). Before
  this, an editor export of any shared-wall door
  rendered with the neighbour's wall drawn straight
  across the gap.

## 2.2.3 — 2026-11-01

Sample plan rebuilt after the reference plan the user
supplied (68 ft x 34 ft 6 in), fixing the two
complaints about v2.2.2, plus a small renderer fix the
new sample exposed. No plan-format change.

- No long dead-end hallway. v2.2.2's Hall was a
  5 x 24 ft spur off the Living Room, ending at
  Bedroom 2. The reference's hall is a small 4 x 11.5
  ft junction east of the Bathroom, between Bedroom 3
  (north) and Bedroom 2 (south), with five openings:
  north to Bedroom 3, south to Bedroom 2, west to the
  Bathroom, east to the Great Room (a door), and east
  to the Kitchen/Dining (a cased opening). It connects
  the Great Room to the Kitchen, so it is a through
  route, not a dead end.
- No walking through a closet to reach a bathroom.
  v2.2.2 ran Bedroom -> Closet -> Bath in series. The
  Master Bedroom now has two separate doors on its
  north wall, one to the Closet and one to the Master
  Bath; both are directly off the bedroom and share
  no door with each other.
- Layout (68 x 34.5 ft, 1,518 sq ft living): Great
  Room 18 x 19 ft, entry from the Covered Porch
  (south wall); Kitchen/Dining 18 x 15.5 ft, open to
  the Great Room through a 14 ft passage (the
  reference has no wall there at all) and a patio
  door north to the Patio; Bedroom 3 12 x 11.5 ft,
  Bathroom 8 x 11.5 ft, Bedroom 2 12 x 11.5 ft, all
  off the Hall; Master Bedroom 14 x 12.5 ft, Closet
  5 x 13.5 ft, Master Bath 9 x 13.5 ft (interior, as
  in the reference — no exterior window); Laundry
  14 x 8.5 ft, entered from the Kitchen and opening
  to the Garage; Garage 24 x 24 ft, north-aligned,
  with a 16 ft double vehicle door on its south
  wall. The Covered Porch and Patio are exterior and
  are not rooms here. Room sizes are rounded to whole
  or half feet so the rectangles tile exactly; the
  reference's labels are interior clear sizes.
- Renderer fix: with dimensions drawn inside, the
  vertical dimension text sat at a narrow room's
  right edge, centred vertically — on top of the
  centred room label (the 4 ft Hall rendered its
  "11.5 ft" over "Hall"). Rooms narrower than 90
  points now put that text near the bottom of the
  line instead, clear of the label and of the
  horizontal dimension text at the top. Wide rooms
  are unchanged. The sample's long room name was
  also shortened ("Walk-in Closet" -> "Closet") so
  its label fits its 5 ft room instead of spilling
  into the Bath.

## 2.2.2 — 2026-10-31

Sample plan rebuilt again, this time after a published
plan instead of an invented tiling. No plan-format
change; the sample style changes scale and orientation
so the wider house fits its page (see below).

- Model: the split-bedroom ranch pattern of Houseplans
  430-10 (1,400 sq ft, 3 bed / 2 bath, living 17 x 16.5
  ft, primary 14'4" x 11'6", secondary 11'4" x 11',
  garage 21'4" x 21'8") — the same arrangement, redrawn
  to rectangle-only rooms, not a copy of its drawings.
  Front entry into an open great room, kitchen and
  dining open to it at the rear, primary suite in its
  own west wing, secondary bedrooms off one hall in
  the east wing, garage entry through a mudroom.
- Layout (74 x 36 ft, 1,872 sq ft living): Garage
  22 x 20 ft (440 sq ft) with a 16 ft double vehicle
  door (`swing: "none"`, an overhead door has no leaf
  or arc — the old "garage door" was a 3 ft swing door
  on a 20 x 10 ft garage a car cannot fit in);
  Mudroom 14 x 10 ft (garage entry, laundry here);
  Living Room 22 x 18 ft with the front door on the
  south (street) wall; Kitchen 11 x 18 ft and Dining
  Room 11 x 18 ft open to the Living Room and each
  other, rear door from the Kitchen; Primary Bedroom
  14 x 14 ft -> Walk-in Closet 14 x 6 ft -> Primary
  Bath 14 x 6 ft, entered from the Living Room; Hall
  5 x 24 ft, a single-loaded corridor off the Living
  Room serving Bedroom 3 (16 x 12 ft, front), Bathroom
  (11 x 10 ft, shared), and Bedroom 2 (11 x 14 ft,
  rear). No bedroom is reached through another room,
  and every bedroom has an exterior window — the
  Primary Bedroom's is on the west wall north of the
  Garage roofline, because its wall south of that line
  backs onto the Garage and a window there would open
  into it.
- Sample style: scale 1/4" portrait -> 1/8" landscape.
  At 1/4" the 74 ft house is 1,850 points wide against
  an 850-point portrait page, so the Garage and the
  whole east wing were clipped off the render (the
  first render of this layout showed exactly that).
  1/8" landscape is the usual sheet for a wide
  single-story house; the render now fits with no
  clipping warning.
- Known minor, unchanged from 2.1.1: room dimensions
  are drawn inside rooms, so in the 5 ft Hall the
  vertical dimension label sits tight against the
  room label. Both are readable; moving dimensions
  outside narrow rooms is still a separate change.

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
