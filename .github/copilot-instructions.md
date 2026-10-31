# Copilot Instructions for floorplan-studio

Two halves, one plan format. Do not rewrite one half in the other's language.

## Big picture

- `editor/` — browser Canvas editor. Entry: `index.html` + `script.js` (ES modules). State in `modules/state.js`, canvas rendering in `modules/drawing.js`, snapping/hit-testing in `modules/utils.js`, plan conversion in `modules/plan.js`.
- `renderer/` — Python package `floorplan` (matplotlib + PyYAML). Entry: `floorplan.cli:main` (`floorplan render` / `floorplan convert`). Pipeline: `data_loader.load_plan` -> `Plan` (`models.py`, `Room` in `room.py`) -> `drawing.draw_floor_plan` with a resolved style from `style_loader.load_style`.
- `examples/` — sample plan (`floor_plan.yaml` + generated `floor_plan.json`) and style file. The renderer bundles the same style as package data.

## Plan format (version 1) — do not break

- Coordinates are feet, origin bottom-left, y up. Rooms: `[x, y, width, height]`. Doors/windows: `pos: [[x1, y1], [x2, y2]]`, horizontal or vertical only, `swing` in/out.
- Optional: `boundary` (list of points), `walls`, `openings` (door/window on no room edge), `labels`, `dimensions`, `objects` (stairs/road). Only `rooms` is required.
- Editor canvas coords are pixels, origin top-left, y down, 20 px/ft. Conversion lives only in `editor/modules/plan.js`: `(x_px, y_px) -> (x_px/20, -y_px/20)`, lossless both ways. Never flip coordinates in the renderer.
- Door/window attachment: a segment on a room edge attaches to the first such room (`findRoomForSegment`, 0.01 ft tolerance); otherwise it stays an `opening`. Editor-only door fields ride under `editor` and the renderer ignores them.
- The editor has no canvas object for `boundary`: it is stored in `state.planBoundary` and re-exported unchanged.

## Patterns and gotchas

- Renderer style: `@key` palette references resolve recursively in `style_loader.py`; unknown keys raise. Do not reintroduce the old one-level resolver. A style must contain `settings`/`line_styles`/`text_styles` (validated in `load_style`); the CLI reports style errors on stderr and exits 1, never with a traceback.
- Wall tolerance is shared: `room.py: WALL_TOLERANCE_FT = 0.01` must match `plan.js: TOLERANCE_FT`. Do not compare gaps in scaled units against a bare epsilon.
- Doors: hinge is the minimum-coordinate endpoint; draw the open leaf plus a full quarter-circle arc from the wall direction to the leaf (never a truncated arc, never a line along the wall — that fills the wall gap). Boundary labels are bounding-box dimensions, outside the box. The north-arrow label sits above the FancyArrow tip (shaft + head length), not at shaft length.
- Plan format contract: `schema/plan-v1.json` owns shape/required keys/types; semantic rules (axis-alignment, positive sizes) stay in the validators. The CI `contract` job validates the examples, renders an editor golden export in Python, and diffs the example JSON twin against a fresh conversion — keep all three green.
- `drawing.py` must keep exactly one definition of each helper. The north arrow is placed from page size, not from plan offsets. Door gaps in `room.py` must use the passed `scale_factor`/`offset_x`/`offset_y` (a hardcoded 25.0/0 was a real bug).
- Windows draw only on exterior walls (`room.get_window_wall_info`); with no boundary every room wall counts as exterior. Interior windows are skipped by design.
- `draw_floor_plan` creates its output directory; never save to a hardcoded `output/` path from the caller's cwd without creating it.
- Editor CSS: `dist/styles.css` is committed. After changing `src/tailwind.css`, run `npm run build:css` and commit the result; CI fails if it is stale.
- Editor persistence is a plan in localStorage (`floorplan-autosave-v1`) via `persistPlan`/`restorePlan` in `script.js`. Keep import/export and autosave on the same plan shape.
- Fonts: style files use DejaVu Sans (present everywhere), not Arial.

## How to run and test

- Renderer: `pip install -e "renderer[dev]"`, then `ruff check renderer/src renderer/tests`, `pytest renderer/tests -q`, `floorplan render examples/floor_plan.yaml --output-dir output`.
- Editor: `cd editor && npm install`, `npm test`, `npm run check`, `npm run build:css`; serve with `python -m http.server 8000` and open the page in a browser to check canvas behaviour (not covered by automated tests).
