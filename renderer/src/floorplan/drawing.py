"""Render a :class:`Plan` to a print-ready page (SVG/PNG/PDF).

One definition per helper: the original file defined
``parse_scale``/``parse_paper_size``/``draw_boundary``/
``draw_north_arrow`` three times each (the first copy was also
spliced), so which copy ran depended on file order. The north arrow
in the surviving copy took page dimensions as offsets and landed
off-page; it is now placed from the page size directly.
"""

import logging
import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrow

logger = logging.getLogger(__name__)

TITLE_MARGIN_TOP = 50  # points
BOTTOM_MARGIN = 50  # points

# Page-coordinate units. The figure is sized so that one coordinate
# unit equals one PostScript point: the figure width in inches is
# paper_width * UNITS_PER_INCH / POINTS_PER_INCH while the axes span
# the full figure and the x-limits span paper_width * UNITS_PER_INCH
# units. Do not "simplify" these into a single 100 — the invariant
# above is what makes font sizes (real points) line up with geometry.
UNITS_PER_INCH = 100
POINTS_PER_INCH = 72


def parse_scale(scale_str):
    """Parse a scale like '1/4' to inches per foot.

    Accepts the named fractions below, a plain number (``"0.25"``,
    or a numeric value from YAML. Anything else raises ValueError:
    a typo'd scale must not silently render at 1/4" unnoticed.
    """
    common_scales = {"1/8": 0.125, "1/4": 0.25, "1/2": 0.5, "1": 1.0, "2": 2.0}
    if isinstance(scale_str, (int, float)) and not isinstance(scale_str, bool):
        if scale_str > 0:
            return float(scale_str)
    elif isinstance(scale_str, str):
        key = scale_str.strip()
        if key in common_scales:
            return common_scales[key]
        try:
            value = float(key)
        except ValueError:
            value = None
        if value is not None and value > 0:
            return value
    raise ValueError(
        f"Unknown scale {scale_str!r} "
        f"(expected one of {sorted(common_scales)} or a positive number)"
    )


def parse_paper_size(size_str, orientation="vertical"):
    """Parse a paper size like '8.5x11' to (width, height) in inches.

    Matching is case- and whitespace-insensitive (``"A4"``,
    ``"8.5 x 11"``). Unknown sizes raise ValueError instead of
    silently falling back to letter.
    """
    common_sizes = {
        "8.5x11": (8.5, 11),
        "11x17": (11, 17),
        "a4": (8.27, 11.69),
        "a3": (11.69, 16.54),
        "letter": (8.5, 11),
        "tabloid": (11, 17),
    }
    if isinstance(size_str, str):
        key = size_str.strip().lower().replace(" ", "")
        if key in common_sizes:
            w, h = common_sizes[key]
            if orientation == "horizontal":
                w, h = h, w
            return (w, h)
    raise ValueError(
        f"Unknown paper size {size_str!r} "
        f"(expected one of {sorted(common_sizes)})"
    )


def draw_boundary(ax, boundary, style, scale_factor, offset_x=0, offset_y=0, doors=None):
    """Draw the boundary outline plus overall dimension labels.

    The labels are bounding-box dimensions (overall width/height),
    not per-edge lengths, and are placed outside the box (below the
    bottom edge, left of the left edge). That holds for any shape:
    the old code assumed a 4-point rectangle in BL, BR, TR, TL
    order and labelled a trapezoid's corners wrong, and the sample
    plan's rectangle labelled an edge that was actually interior
    once the Garage sat outside it.

    The outline is drawn edge by edge, not as one closed polygon,
    so it can break at exterior doors (``doors`` is the plan's
    room doors plus standalone door openings). A closed polygon
    would draw straight over the gap a room wall just cut, hiding
    every exterior door behind the outline.
    """
    if not boundary:
        return
    wall_style = style["line_styles"]["exterior_wall"]
    tol = 1e-6
    for i, (x1, y1) in enumerate(boundary):
        x2, y2 = boundary[(i + 1) % len(boundary)]
        # Gap intervals along this edge, as fractions of the edge
        # from (x1, y1) to (x2, y2), from doors lying on the edge.
        gaps = []
        for door in doors or []:
            pos = door.get("pos") if isinstance(door, dict) else None
            if not isinstance(pos, list) or len(pos) != 2:
                continue
            (dx1, dy1), (dx2, dy2) = pos
            if abs(y1 - y2) < tol and abs(dy1 - dy2) < tol and abs(dy1 - y1) < tol:
                lo = max(min(x1, x2), min(dx1, dx2))
                hi = min(max(x1, x2), max(dx1, dx2))
                if hi > lo and x2 != x1:
                    # min/max, not lo/hi order: an edge running
                    # right-to-left (like the closing west edge)
                    # gives a larger t for the smaller coordinate,
                    # and an unsorted interval draws no gap at all.
                    t1, t2 = (lo - x1) / (x2 - x1), (hi - x1) / (x2 - x1)
                    gaps.append((min(t1, t2), max(t1, t2)))
            elif abs(x1 - x2) < tol and abs(dx1 - dx2) < tol and abs(dx1 - x1) < tol:
                lo = max(min(y1, y2), min(dy1, dy2))
                hi = min(max(y1, y2), max(dy1, dy2))
                if hi > lo and y2 != y1:
                    t1, t2 = (lo - y1) / (y2 - y1), (hi - y1) / (y2 - y1)
                    gaps.append((min(t1, t2), max(t1, t2)))
        gaps.sort()
        current = 0.0
        segments = []
        for lo, hi in gaps:
            lo, hi = max(0.0, lo), min(1.0, hi)
            if lo > current:
                segments.append((current, lo))
            current = max(current, hi)
        if current < 1.0:
            segments.append((current, 1.0))
        for t1, t2 in segments:
            sx1 = (x1 + t1 * (x2 - x1)) * scale_factor + offset_x
            sy1 = (y1 + t1 * (y2 - y1)) * scale_factor + offset_y
            sx2 = (x1 + t2 * (x2 - x1)) * scale_factor + offset_x
            sy2 = (y1 + t2 * (y2 - y1)) * scale_factor + offset_y
            ax.plot([sx1, sx2], [sy1, sy2],
                    color=wall_style["color"], linewidth=wall_style["thickness"])
    xs = [p[0] for p in boundary]
    ys = [p[1] for p in boundary]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    units = style["settings"].get("units", "ft")
    ax.text((min_x + max_x) / 2 * scale_factor + offset_x,
            min_y * scale_factor + offset_y - 10,
            f"{max_x - min_x} {units}", ha="center", va="bottom",
            fontsize=10, color=wall_style["color"])
    ax.text(min_x * scale_factor + offset_x - 10,
            (min_y + max_y) / 2 * scale_factor + offset_y,
            f"{max_y - min_y} {units}", ha="right", va="center",
            fontsize=10, color=wall_style["color"], rotation=90)


def draw_north_arrow(ax, style, scale_factor, page_width_points, page_height_points):
    """North arrow in the top-right corner, fully inside the page.

    The arrow is page-relative and fixed-size: the original placed it
    25 points below the top edge and 75 points tall, so both arrow
    and label fell outside the page and were clipped from the SVG.
    Note the label position: a FancyArrow's tip is at
    ``arrow_y + length + head_length``, not at ``arrow_y + length``
    — the old label sat at the shaft/head join, centred on the black
    head, so the black "N" was invisible against it. The label now
    sits 5 points above the actual tip.
    """
    if not style["settings"].get("north_arrow", False):
        return
    arrow_x = page_width_points - 50
    arrow_y = page_height_points - 100
    length = 50
    head_length = min(1 * scale_factor, 20)
    ax.add_patch(FancyArrow(
        arrow_x, arrow_y, 0, length,
        width=0.5 * scale_factor, head_width=1.5 * scale_factor,
        head_length=head_length, color="black"))
    ax.text(arrow_x, arrow_y + length + head_length + 5, "N",
            ha="center", va="bottom", fontsize=12, fontweight="bold")


def _draw_walls(ax, plan, style, scale_factor, offset_x, offset_y):
    wall_style = style["line_styles"]["interior_wall"]
    for wall in plan.walls:
        (x1, y1), (x2, y2) = wall["pos"]
        ax.plot(
            [x1 * scale_factor + offset_x, x2 * scale_factor + offset_x],
            [y1 * scale_factor + offset_y, y2 * scale_factor + offset_y],
            color=wall_style["color"], linewidth=wall_style["thickness"])


def _draw_openings(ax, plan, style, scale_factor, offset_x, offset_y):
    """Standalone door/window segments (not attached to a room edge)."""
    door_style = style["line_styles"]["door_panel"]
    window_style = style["line_styles"]["window_frame"]
    for opening in plan.openings:
        (x1, y1), (x2, y2) = opening["pos"]
        sx1, sy1 = x1 * scale_factor + offset_x, y1 * scale_factor + offset_y
        sx2, sy2 = x2 * scale_factor + offset_x, y2 * scale_factor + offset_y
        if opening["kind"] == "window":
            ax.plot([sx1, sx2], [sy1, sy2],
                    color=window_style.get("edge_color", "black"),
                    linewidth=window_style["thickness"])
        else:
            ax.plot([sx1, sx2], [sy1, sy2],
                    color=door_style["color"], linewidth=door_style["thickness"],
                    linestyle=(0, (4, 3)))
            length = math.hypot(sx2 - sx1, sy2 - sy1)
            # A standalone passage ("none") is just the dashed
            # segment above: no swing arc, for the same reason as
            # room doors (see room.py).
            if length > 0 and opening.get("swing") != "none":
                swing_in = opening.get("swing", "in") == "in"
                # Quarter-circle swing from the hinge (first endpoint).
                angle = math.degrees(math.atan2(sy2 - sy1, sx2 - sx1))
                theta1 = angle + (90 if swing_in else -90)
                ax.add_patch(patches.Arc(
                    (sx1, sy1), length * 2, length * 2, angle=0,
                    theta1=min(angle, theta1), theta2=max(angle, theta1),
                    color="black", linewidth=1.5))


def _draw_labels(ax, plan, style, scale_factor, offset_x, offset_y):
    label_style = style["text_styles"]["room_label"]
    for label in plan.labels:
        x, y = label["point"]
        ax.text(
            x * scale_factor + offset_x, y * scale_factor + offset_y,
            label["text"], ha="center", va="center",
            fontsize=label_style["size"], weight=label_style["weight"],
            color=label_style["color"], family=label_style["font_family"],
            rotation=label.get("rotation", 0))


def _draw_dimensions(ax, plan, style, scale_factor, offset_x, offset_y):
    dim_settings = style.get("dimension_settings", {})
    line_color = dim_settings.get("line_color", "black")
    font_size = dim_settings.get("font_size", 6)
    for dimension in plan.dimensions:
        (x1, y1), (x2, y2) = dimension["pos"]
        sx1, sy1 = x1 * scale_factor + offset_x, y1 * scale_factor + offset_y
        sx2, sy2 = x2 * scale_factor + offset_x, y2 * scale_factor + offset_y
        ax.plot([sx1, sx2], [sy1, sy2], color=line_color, linewidth=0.5)
        text = dimension.get("label")
        if text is None:
            length_ft = math.hypot(x2 - x1, y2 - y1)
            text = f"{length_ft:.2f}'"
        ax.text((sx1 + sx2) / 2, (sy1 + sy2) / 2, text,
                ha="center", va="bottom", fontsize=font_size, color=line_color)


def _draw_objects(ax, plan, style, scale_factor, offset_x, offset_y):
    wall_style = style["line_styles"]["interior_wall"]
    label_style = style["text_styles"]["room_label"]
    for obj in plan.objects:
        x, y, w, h = obj["rect"]
        sx, sy = x * scale_factor + offset_x, y * scale_factor + offset_y
        ax.add_patch(patches.Rectangle(
            (sx, sy), w * scale_factor, h * scale_factor,
            linewidth=wall_style["thickness"], edgecolor=wall_style["color"],
            facecolor="none"))
        label = obj.get("label") or obj["kind"].title()
        ax.text(sx + w * scale_factor / 2, sy + h * scale_factor / 2, label,
                ha="center", va="center", fontsize=label_style["size"] - 2,
                weight=label_style["weight"], color=label_style["color"])


def _plan_bounds(plan):
    """All x/y extents in feet, from every geometry section."""
    xs, ys = [], []
    for room in plan.rooms:
        x, y, w, h = room.rect
        xs.extend([x, x + w])
        ys.extend([y, y + h])
    if plan.boundary:
        for x, y in plan.boundary:
            xs.append(x)
            ys.append(y)
    for section in (plan.walls, plan.openings, plan.dimensions):
        for entry in section:
            for x, y in entry["pos"]:
                xs.append(x)
                ys.append(y)
    for label in plan.labels:
        xs.append(label["point"][0])
        ys.append(label["point"][1])
    for obj in plan.objects:
        x, y, w, h = obj["rect"]
        xs.extend([x, x + w])
        ys.extend([y, y + h])
    if not xs:
        return 0.0, 0.0, 10.0, 10.0
    return min(xs), min(ys), max(xs), max(ys)


def draw_floor_plan(plan, style, output_dir="output", fmt="svg", extras=True):
    """Render ``plan`` with ``style`` into ``output_dir``.

    Writes ``floor_plan.<fmt>`` plus, unless ``extras`` is False,
    settings and page-section diagrams. The output directory is
    created when missing (the original crashed on a fresh
    checkout because it never was). Returns the list of files
    written. A plan larger than the drawable area is centred
    and clipped, not fitted — a warning is logged (visible
    with the CLI's ``--verbose`` flag) instead of silently
    losing geometry off the page.
    """
    settings = style["settings"]
    scale_factor = parse_scale(settings.get("scale", "1/4")) * UNITS_PER_INCH
    orientation = settings.get("orientation", "vertical")
    paper_width, paper_height = parse_paper_size(settings.get("paper_size", "8.5x11"), orientation)
    page_width_points = paper_width * UNITS_PER_INCH
    page_height_points = paper_height * UNITS_PER_INCH

    min_x, min_y, max_x, max_y = _plan_bounds(plan)
    plan_center_x = (min_x + max_x) / 2 * scale_factor
    plan_center_y = (min_y + max_y) / 2 * scale_factor
    middle_center_x = page_width_points / 2
    middle_center_y = (TITLE_MARGIN_TOP + (page_height_points - BOTTOM_MARGIN)) / 2
    offset_x = middle_center_x - plan_center_x
    offset_y = middle_center_y - plan_center_y

    plan_width_points = (max_x - min_x) * scale_factor
    plan_height_points = (max_y - min_y) * scale_factor
    drawable_height = page_height_points - TITLE_MARGIN_TOP - BOTTOM_MARGIN
    if plan_width_points > page_width_points or plan_height_points > drawable_height:
        logger.warning(
            "Plan is %.1f x %.1f points but the drawable area is "
            "%.1f x %.1f points; it will be clipped, not fitted "
            "to the page.",
            plan_width_points, plan_height_points,
            page_width_points, drawable_height,
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(
        figsize=(paper_width * UNITS_PER_INCH / POINTS_PER_INCH,
                 paper_height * UNITS_PER_INCH / POINTS_PER_INCH))
    ax.set_position([0, 0, 1, 1])
    fig.patch.set_facecolor(settings["background_color"])
    ax.add_patch(patches.Rectangle(
        (0, 0), page_width_points, page_height_points,
        facecolor=settings["background_color"], zorder=-1))
    # Deliberate page-anatomy aid, not debug leftovers: faint tints
    # marking the title, plan, title-block, and page-number regions
    # of the page (see the page-section diagram for the key).
    highlight_alpha = 0.1
    ax.add_patch(patches.Rectangle(
        (0, page_height_points - TITLE_MARGIN_TOP), page_width_points, TITLE_MARGIN_TOP,
        facecolor="lightblue", alpha=highlight_alpha))
    ax.add_patch(patches.Rectangle(
        (0, TITLE_MARGIN_TOP), page_width_points,
        page_height_points - BOTTOM_MARGIN - TITLE_MARGIN_TOP,
        facecolor="lightgreen", alpha=highlight_alpha))
    ax.add_patch(patches.Rectangle(
        (0, 0), page_width_points / 2, BOTTOM_MARGIN,
        facecolor="lightyellow", alpha=highlight_alpha))
    ax.add_patch(patches.Rectangle(
        (page_width_points / 2, 0), page_width_points / 2, BOTTOM_MARGIN,
        facecolor="lightpink", alpha=highlight_alpha))

    exterior_doors = [d for room in plan.rooms for d in room.doors]
    exterior_doors += [o for o in plan.openings if o.get("kind") == "door"]
    draw_boundary(ax, plan.boundary, style, scale_factor, offset_x, offset_y,
                  doors=exterior_doors)
    draw_north_arrow(ax, style, scale_factor, page_width_points, page_height_points)
    for room in plan.rooms:
        room.draw(ax, style, scale_factor, offset_x, offset_y, plan.boundary)
    _draw_walls(ax, plan, style, scale_factor, offset_x, offset_y)
    _draw_openings(ax, plan, style, scale_factor, offset_x, offset_y)
    _draw_labels(ax, plan, style, scale_factor, offset_x, offset_y)
    _draw_dimensions(ax, plan, style, scale_factor, offset_x, offset_y)
    _draw_objects(ax, plan, style, scale_factor, offset_x, offset_y)

    title = settings.get("title", "Floor Plan")
    ax.text(page_width_points / 2, page_height_points - TITLE_MARGIN_TOP / 2, title,
            ha="center", va="center", fontsize=18, fontweight="bold", color="black")
    title_style = style["text_styles"]["title_block"]
    address = settings.get("address", "")
    date = settings.get("date", "")
    ax.text(0, BOTTOM_MARGIN / 2, f"{title}\n{address}\nDate: {date}",
            ha="left", va="center", fontsize=title_style["size"],
            fontweight=title_style["weight"], color=title_style["color"])
    ax.text(page_width_points, BOTTOM_MARGIN / 2, "Page 1 of 1",
            ha="right", va="center", fontsize=title_style["size"],
            fontweight=title_style["weight"], color=title_style["color"])

    ax.set_xlim(0, page_width_points)
    ax.set_ylim(0, page_height_points)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    main_path = out_dir / f"floor_plan.{fmt}"
    plt.savefig(main_path, format=fmt)
    plt.close(fig)

    if not extras:
        return [main_path]
    settings_path = _draw_settings_page(style, paper_width, paper_height, out_dir, fmt)
    sections_path = _draw_page_sections(style, paper_width, paper_height, out_dir, fmt)
    return [main_path, settings_path, sections_path]


def _draw_settings_page(style, paper_width, paper_height, out_dir, fmt):
    fig, ax = plt.subplots(
        figsize=(paper_width * UNITS_PER_INCH / POINTS_PER_INCH,
                 paper_height * UNITS_PER_INCH / POINTS_PER_INCH))
    ax.set_position([0, 0, 1, 1])
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_xlim(0, paper_width * UNITS_PER_INCH)
    ax.set_ylim(0, paper_height * UNITS_PER_INCH)
    ax.axis("off")
    settings = style["settings"]
    text = (
        "Floor Plan Settings Used:\n\n"
        f"Scale: {settings.get('scale', '1/4')}\n"
        f"Paper Size: {settings.get('paper_size', '8.5x11')}\n"
        f"Units: {settings.get('units', 'feet')}\n"
        f"Title: {settings.get('title', 'N/A')}\n"
        f"Address: {settings.get('address', 'N/A')}\n"
        f"Date: {settings.get('date', 'N/A')}\n"
        f"North Arrow: {'Yes' if settings.get('north_arrow', False) else 'No'}\n\n"
        f"Generated on: {settings.get('date', 'N/A')}"
    )
    ax.text(50, paper_height * UNITS_PER_INCH - 100, text, ha="left", va="top",
            fontsize=12, family="DejaVu Sans")
    path = out_dir / f"floor_plan_settings.{fmt}"
    plt.savefig(path, format=fmt)
    plt.close(fig)
    return path


def _draw_page_sections(style, paper_width, paper_height, out_dir, fmt):
    fig, ax = plt.subplots(
        figsize=(paper_width * UNITS_PER_INCH / POINTS_PER_INCH,
                 paper_height * UNITS_PER_INCH / POINTS_PER_INCH))
    ax.set_position([0, 0, 1, 1])
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_xlim(0, paper_width * UNITS_PER_INCH)
    ax.set_ylim(0, paper_height * UNITS_PER_INCH)
    ax.axis("off")
    page_width_points = paper_width * UNITS_PER_INCH
    page_height_points = paper_height * UNITS_PER_INCH
    ax.add_patch(patches.Rectangle(
        (0, page_height_points - TITLE_MARGIN_TOP), page_width_points, TITLE_MARGIN_TOP,
        linewidth=2, edgecolor="blue", facecolor="lightblue", alpha=1.0))
    ax.text(page_width_points / 2, page_height_points - TITLE_MARGIN_TOP / 2,
            "Title Section", ha="center", va="center", fontsize=12, color="black")
    middle_top = BOTTOM_MARGIN
    middle_bottom = page_height_points - TITLE_MARGIN_TOP
    ax.add_patch(patches.Rectangle(
        (0, middle_top), page_width_points, middle_bottom - middle_top,
        linewidth=2, edgecolor="green", facecolor="lightgreen", alpha=1.0))
    ax.text(page_width_points / 2, (middle_top + middle_bottom) / 2,
            "Floor Plan Section", ha="center", va="center", fontsize=12, color="black")
    ax.add_patch(patches.Rectangle(
        (0, 0), page_width_points / 2, BOTTOM_MARGIN,
        linewidth=2, edgecolor="red", facecolor="lightcoral", alpha=1.0))
    ax.text(0, BOTTOM_MARGIN / 2, "Title Block Section", ha="left", va="center",
            fontsize=12, color="black")
    ax.add_patch(patches.Rectangle(
        (page_width_points / 2, 0), page_width_points / 2, BOTTOM_MARGIN,
        linewidth=2, edgecolor="orange", facecolor="wheat", alpha=1.0))
    ax.text(page_width_points, BOTTOM_MARGIN / 2, "Page Number Section",
            ha="right", va="center", fontsize=12, color="black")
    path = out_dir / f"floor_plan_page_sections.{fmt}"
    plt.savefig(path, format=fmt)
    plt.close(fig)
    return path
