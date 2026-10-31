"""Command line: render plans and convert between YAML and JSON."""

import argparse
import logging
import sys
from importlib import resources
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from floorplan import __version__  # noqa: E402
from floorplan.data_loader import dump_plan, load_plan  # noqa: E402
from floorplan.drawing import draw_floor_plan  # noqa: E402
from floorplan.style_loader import load_style  # noqa: E402


def _default_style_path() -> Path:
    return Path(resources.files("floorplan") / "data" / "floor_plan_style.yaml")


def _apply_metadata(plan, style, title, address, date):
    """CLI overrides win, then plan metadata, then the style file."""
    settings = style.setdefault("settings", {})
    if plan.title is not None:
        settings["title"] = plan.title
    if plan.address is not None:
        settings["address"] = plan.address
    if plan.date is not None:
        settings["date"] = plan.date
    if title is not None:
        settings["title"] = title
    if address is not None:
        settings["address"] = address
    if date is not None:
        settings["date"] = date
    return style


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="floorplan",
        description="Render floor plans (YAML/JSON) to print-ready pages.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable info logging (plan/style loading, fit warnings).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render a plan file to SVG/PNG/PDF.")
    render.add_argument("plan", help="Plan file (.yaml, .yml, or .json).")
    render.add_argument(
        "--style", default=None,
        help="Style YAML file. Defaults to the bundled floor_plan_style.yaml.",
    )
    render.add_argument(
        "--output-dir", "-o", default="output",
        help="Directory for the rendered files (created if missing).",
    )
    render.add_argument(
        "--format", choices=["svg", "png", "pdf"], default="svg",
        help="Output format for the rendered pages.",
    )
    render.add_argument("--title", default=None, help="Override the page title.")
    render.add_argument("--address", default=None, help="Override the title-block address.")
    render.add_argument("--date", default=None, help="Override the title-block date.")
    render.add_argument(
        "--no-extras", action="store_true",
        help="Write only floor_plan.<format>; skip the settings and "
        "page-section diagrams.",
    )

    convert = sub.add_parser(
        "convert", help="Convert a plan between YAML and JSON (chosen by suffix).")
    convert.add_argument("plan", help="Input plan file.")
    convert.add_argument("output", help="Output file (.yaml/.yml/.json).")
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="floorplan: %(levelname)s: %(message)s",
    )
    try:
        if args.command == "render":
            plan = load_plan(args.plan)
            style = load_style(args.style) if args.style else load_style(_default_style_path())
            style = _apply_metadata(plan, style, args.title, args.address, args.date)
            written = draw_floor_plan(
                plan, style, output_dir=args.output_dir, fmt=args.format,
                extras=not args.no_extras,
            )
            for path in written:
                print(path)
            return 0
        if args.command == "convert":
            plan = load_plan(args.plan)
            dump_plan(plan, args.output)
            print(args.output)
            return 0
    except (OSError, ValueError, KeyError) as exc:
        # KeyError is belt-and-braces: load_style validates the
        # sections up front, but a style that passes validation can
        # still miss a nested key a draw method reads. Either way
        # the user gets one clean line, not a traceback.
        print(f"floorplan: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
