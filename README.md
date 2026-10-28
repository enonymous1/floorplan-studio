# floorplan-studio

Draw a floor plan in the browser, then render it as a print-ready page. One repo, two halves, one shared plan format:

- **`editor/`** — interactive Canvas editor (walls, rooms, doors, windows, labels, dimensions, stairs, roads) with undo/redo, pan/zoom, and grid snapping.
- **`renderer/`** — Python CLI that turns a plan (YAML or JSON) into a scaled SVG/PNG/PDF page with a title block, dimensions, and a north arrow.

The workflow the merge exists for: draw in the editor, **Export JSON/YAML**, then render:

```powershell
floorplan render floor-plan.json --output-dir output
```

![Rendered sample plan](docs/demo.svg)

The image above is the real output of the renderer on `examples/floor_plan.yaml` — not a mockup.

## Editor

No build step is needed to run it; the built Tailwind CSS is committed in `editor/dist/styles.css`. Serve the folder with any static server and open it in a browser:

```powershell
cd editor
python -m http.server 8000
# open http://localhost:8000
```

In the editor you can:

- Draw with the toolbar (Select, Wall, Room, Door, Window, Label, Dimension, Eraser, Object library). Keyboard: V/W/R/D/I/O/T/M/E, Ctrl+Z / Ctrl+Y, Delete.
- **Export JSON / Export YAML** from the Plan section of the toolbar. The file is the shared plan format below and renders directly with the CLI.
- **Import JSON** to load a plan exported from the editor (or converted with `floorplan convert`).
- Work is autosaved to the browser's local storage as a plan, so a refresh restores the canvas. Clear is undoable.

If you change `editor/src/tailwind.css`, rebuild the committed CSS:

```powershell
cd editor
npm install
npm run build:css
```

## Renderer

Requires Python 3.10+. The distribution is named `floorplan-studio` (the repo name); the installed command and the import package are still `floorplan`. Install it editable from the repo root:

```powershell
pip install -e renderer
floorplan render examples/floor_plan.yaml --output-dir output
floorplan render examples/floor_plan.json --format png --output-dir output
floorplan convert examples/floor_plan.yaml floor-plan.json
```

`floorplan render` writes three files to the output directory (created when missing): `floor_plan.<format>`, `floor_plan_settings.<format>`, and `floor_plan_page_sections.<format>`. Options: `--style` (a style YAML; otherwise the bundled style is used), `--format svg|png|pdf`, `--title`, `--address`, `--date`. The title/address/date in a plan file override the style file; CLI flags override both.

`python -m floorplan` works the same way when the package is on `PYTHONPATH` without installing.

## Shared plan format (version 1)

Plans are JSON or YAML with the same shape. All coordinates are **feet**, origin **bottom-left**, y increasing upwards. Rooms use `[x, y, width, height]`; doors and windows use `pos: [[x1, y1], [x2, y2]]` and must be horizontal or vertical; `swing` is `"in"` or `"out"`.

```json
{
  "version": 1,
  "title": "Residential Floor Plan",
  "address": "123 Main Street",
  "date": "2025-09-19",
  "boundary": [[0, 0], [32, 0], [32, 27], [0, 27]],
  "rooms": [
    {
      "name": "Living Room",
      "rect": [0, 0, 20, 15],
      "doors": [{ "pos": [[10, 0], [13, 0]], "swing": "in" }],
      "windows": [{ "pos": [[2, 15], [8, 15]] }]
    }
  ]
}
```

Optional sections: `walls` (standalone segments), `openings` (door/window segments that lie on no room edge), `labels` (`text`, `point`, `rotation`), `dimensions` (`pos`, `label`), and `objects` (`kind: stairs|road`, `rect`, `label`). Only `rooms` is required (it may be empty). The sample in `examples/floor_plan.yaml` and its JSON twin `examples/floor_plan.json` show every section in use except `objects`.

How the editor maps to this format (in `editor/modules/plan.js`, covered by tests):

- Canvas pixels convert as `(x_px, y_px) -> (x_px / 20, -y_px / 20)`: a scale plus a Y flip anchored at the canvas origin. The conversion is lossless both ways; the renderer centres the plan on the page, so exported y values being negative is fine.
- A door/window segment lying on a room edge attaches to the first such room, so the renderer cuts a door gap in that wall. Segments on no room edge stay as `openings`.
- Unnamed rectangles become `Room 1`, `Room 2`, …; a rectangle imported with a name keeps it on re-export, though the editor UI has no rename control yet.
- Editor-only door fields (`swingDirection`, `hingeAtStart`) ride along under an `editor` key and are restored on import; the renderer ignores them.
- A plan's `boundary` has no canvas object in the editor: it is preserved on import and re-exported unchanged, and the renderer still uses it for exterior-wall checks.

Style lives separately in `examples/floor_plan_style.yaml` (also bundled with the renderer): paper size, scale, palette with `@key` references, line/text styles, and dimension/window/door settings. The address and date in the sample style are fictional example data.

## Known limits

- Windows are only drawn when they lie on an exterior wall (or, with no boundary, on a room wall). Interior windows in the data are skipped by design, matching the original renderer.
- Diagonal door/window segments are rejected by the loader; walls may be diagonal.
- Stairs and roads render as labelled rectangles, not as the editor's stepped/road drawing.
- The editor's canvas interaction (dragging, resizing, modal flows) was verified by syntax and plan-logic tests here, not by driving a browser; try it in a browser before relying on a new interaction.

## Layout

```text
editor/                 Browser editor (ES modules, Tailwind 3)
  index.html            Toolbar, canvas, modals, import/export controls
  script.js             Event handling, history, persistence, import/export
  modules/state.js      Shared mutable state
  modules/drawing.js    Canvas rendering
  modules/utils.js      Snapping, hit-testing, handles
  modules/plan.js       Shared-format conversion + YAML serializer (pure, tested)
  src/tailwind.css      Tailwind source
  dist/styles.css       Built CSS, committed so a fresh clone works
  tests/plan.test.mjs   Conversion, attachment, round-trip, YAML tests
renderer/               Python package (matplotlib + PyYAML)
  src/floorplan/        cli, data_loader, style_loader, drawing, room, models
  tests/                Loader, rendering, CLI tests
examples/               Sample plan (YAML + JSON) and style file
docs/demo.svg           Real renderer output on the sample plan
```

## Development

```powershell
cd renderer
pip install -e ".[dev]"
ruff check src tests
pytest
```

```powershell
cd editor
npm install
npm test
npm run check
npm run build:css
git diff --exit-code dist/styles.css
```

## History

Version 2.0.0 merges two February 2026 projects — the Python renderer (`ss-floorplan`) and the browser editor (`ss-floor_plan_creator`) — into this single repo, `floorplan-studio`, under a shared plan format, keeping both stacks. This is a squashed export: the earlier single-commit histories under a student identity are intentionally not included. See `CHANGELOG.md` for what changed and what was removed.
