# Changelog

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
