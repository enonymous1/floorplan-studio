"""Room geometry and drawing.

Coordinates are in feet. ``Room.rect`` is ``[x, y, width, height]``
with (x, y) at the bottom-left corner.
"""

import matplotlib.patches as patches
from typing import Dict, List, Optional, Tuple


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def get_window_wall_info(
    room_rect: List[float],
    window_pos: Tuple[Tuple[float, float], Tuple[float, float]],
    boundary: Optional[List[List[float]]] = None,
    tol: float = 1e-6,
) -> Optional[str]:
    """
    Determine which wall a window is on.

    Only returns wall info if the window is on both the room boundary
    AND the exterior boundary. Without a boundary, every room wall
    counts as exterior.

    Returns 'top', 'bottom', 'left', 'right', or None.
    """
    x, y, w, h = room_rect
    (x1, y1), (x2, y2) = window_pos

    wall_type = None

    if abs(y1 - y2) < tol:
        if abs(y1 - (y + h)) < tol and x <= x1 <= x + w and x <= x2 <= x + w:
            wall_type = "top"
        elif abs(y1 - y) < tol and x <= x1 <= x + w and x <= x2 <= x + w:
            wall_type = "bottom"
    elif abs(x1 - x2) < tol:
        if abs(x1 - x) < tol and y <= y1 <= y + h and y <= y2 <= y + h:
            wall_type = "left"
        elif abs(x1 - (x + w)) < tol and y <= y1 <= y + h and y <= y2 <= y + h:
            wall_type = "right"

    if boundary is None or wall_type is None:
        return wall_type

    if len(boundary) >= 4:
        boundary_x = [point[0] for point in boundary]
        boundary_y = [point[1] for point in boundary]
        min_x, max_x = min(boundary_x), max(boundary_x)
        min_y, max_y = min(boundary_y), max(boundary_y)

        if wall_type == "top" and abs(y1 - max_y) < tol:
            if min_x <= x1 <= max_x and min_x <= x2 <= max_x:
                return "top"
        elif wall_type == "bottom" and abs(y1 - min_y) < tol:
            if min_x <= x1 <= max_x and min_x <= x2 <= max_x:
                return "bottom"
        elif wall_type == "left" and abs(x1 - min_x) < tol:
            if min_y <= y1 <= max_y and min_y <= y2 <= max_y:
                return "left"
        elif wall_type == "right" and abs(x1 - max_x) < tol:
            if min_y <= y1 <= max_y and min_y <= y2 <= max_y:
                return "right"

    return None


class Room:
    """A room: rectangle in feet, plus doors and windows on its walls."""

    def __init__(
        self,
        name: str,
        rect: List[float],
        doors: Optional[List[Dict]] = None,
        windows: Optional[List[Dict]] = None,
    ):
        if not isinstance(name, str) or not name:
            raise ValueError("room name must be a non-empty string")
        if (
            not isinstance(rect, list)
            or len(rect) != 4
            or not all(_is_number(v) for v in rect)
            or rect[2] <= 0
            or rect[3] <= 0
        ):
            raise ValueError(
                "rect must be a list of 4 numbers [x, y, width, height] "
                "with positive width and height"
            )
        self.name = name
        self.rect = [float(v) for v in rect]
        self.doors = list(doors) if doors else []
        self.windows = list(windows) if windows else []

    def get_area(self) -> float:
        """Room area in square feet."""
        _, _, w, h = self.rect
        return w * h

    def draw(
        self,
        ax,
        style: Dict,
        scale_factor: float,
        offset_x: float,
        offset_y: float,
        boundary: Optional[List[List[float]]] = None,
    ):
        x, y, w, h = self.rect
        scaled_x = x * scale_factor + offset_x
        scaled_y = y * scale_factor + offset_y
        scaled_w = w * scale_factor
        scaled_h = h * scale_factor

        self._draw_room_shape(
            ax, style, scaled_x, scaled_y, scaled_w, scaled_h, scale_factor, offset_x, offset_y)
        self._draw_label(ax, style, scaled_x, scaled_y, scaled_w, scaled_h)
        self._draw_dimensions(ax, style, scaled_x, scaled_y, scaled_w, scaled_h, w, h)
        self._draw_doors(ax, style, scale_factor, offset_x, offset_y)
        self._draw_windows(ax, style, scale_factor, offset_x, offset_y, boundary)

    def _draw_room_shape(
        self, ax, style, scaled_x, scaled_y, scaled_w, scaled_h,
        scale_factor, offset_x, offset_y,
    ):
        room_style = style["line_styles"]["interior_wall"]
        facecolor = room_style.get("facecolor", "whitesmoke")
        ax.add_patch(
            patches.Rectangle(
                (scaled_x, scaled_y), scaled_w, scaled_h,
                linewidth=0, facecolor=facecolor,
            )
        )
        self._draw_wall_segments(
            ax, style, scaled_x, scaled_y, scaled_w, scaled_h, scale_factor, offset_x, offset_y
        )

    def _draw_wall_segments(
        self, ax, style, scaled_x, scaled_y, scaled_w, scaled_h,
        scale_factor, offset_x, offset_y,
    ):
        # Door gaps must use the same scale/offset as the room itself.
        # (The original code hardcoded 25.0/0 here, so gaps drifted off
        # the walls at any other scale or once the plan was centred.)
        door_gaps = []
        for door in self.doors:
            pos = door.get("pos")
            if isinstance(pos, list) and len(pos) == 2:
                (x1, y1), (x2, y2) = pos
                sx1 = x1 * scale_factor + offset_x
                sy1 = y1 * scale_factor + offset_y
                sx2 = x2 * scale_factor + offset_x
                sy2 = y2 * scale_factor + offset_y
                door_gaps.append(
                    {"x1": sx1, "y1": sy1, "x2": sx2, "y2": sy2,
                     "is_vertical": abs(sx1 - sx2) < 1e-6}
                )

        self._draw_wall_segment(ax, style, scaled_x, scaled_y + scaled_h,
                                scaled_x + scaled_w, scaled_y + scaled_h, door_gaps, "top")
        self._draw_wall_segment(ax, style, scaled_x, scaled_y,
                                scaled_x + scaled_w, scaled_y, door_gaps, "bottom")
        self._draw_wall_segment(ax, style, scaled_x, scaled_y,
                                scaled_x, scaled_y + scaled_h, door_gaps, "left")
        self._draw_wall_segment(ax, style, scaled_x + scaled_w, scaled_y,
                                scaled_x + scaled_w, scaled_y + scaled_h, door_gaps, "right")

    def _draw_wall_segment(self, ax, style, x1, y1, x2, y2, door_gaps, wall_side):
        room_style = style["line_styles"]["interior_wall"]
        relevant_gaps = []
        if wall_side in ["top", "bottom"]:
            wall_y = y1
            for gap in door_gaps:
                if not gap["is_vertical"] and abs(gap["y1"] - wall_y) < 1e-6:
                    relevant_gaps.append((min(gap["x1"], gap["x2"]), max(gap["x1"], gap["x2"])))
        else:
            wall_x = x1
            for gap in door_gaps:
                if gap["is_vertical"] and abs(gap["x1"] - wall_x) < 1e-6:
                    relevant_gaps.append((min(gap["y1"], gap["y2"]), max(gap["y1"], gap["y2"])))
        relevant_gaps.sort()

        if wall_side in ["top", "bottom"]:
            current_x = x1
            for gap_start, gap_end in relevant_gaps:
                if current_x < gap_start:
                    ax.plot([current_x, gap_start], [y1, y2],
                            color=room_style["color"], linewidth=room_style["thickness"])
                current_x = gap_end
            if current_x < x2:
                ax.plot([current_x, x2], [y1, y2],
                        color=room_style["color"], linewidth=room_style["thickness"])
        else:
            current_y = y1
            for gap_start, gap_end in relevant_gaps:
                if current_y < gap_start:
                    ax.plot([x1, x2], [current_y, gap_start],
                            color=room_style["color"], linewidth=room_style["thickness"])
                current_y = gap_end
            if current_y < y2:
                ax.plot([x1, x2], [current_y, y2],
                        color=room_style["color"], linewidth=room_style["thickness"])

    def _draw_label(self, ax, style, scaled_x, scaled_y, scaled_w, scaled_h):
        label_style = style["text_styles"]["room_label"]
        label = f"{self.name}\n{self.get_area():.0f} sq ft"
        ax.text(
            scaled_x + scaled_w / 2, scaled_y + scaled_h / 2, label,
            ha=label_style.get("alignment", "center"), va="center",
            fontsize=label_style["size"] - 2,
            weight=label_style["weight"], color=label_style["color"],
            family=label_style["font_family"], transform=ax.transData,
        )

    def _draw_dimensions(self, ax, style, scaled_x, scaled_y, scaled_w, scaled_h, w, h):
        dim_settings = style.get("dimension_settings", {})
        line_offset = dim_settings.get("line_offset", 5)
        tick_length = dim_settings.get("tick_length", 3)
        text_offset = dim_settings.get("text_offset", 7)
        font_size = dim_settings.get("font_size", 6)
        line_color = dim_settings.get("line_color", "black")
        line_thickness = dim_settings.get("line_thickness", 0.5)
        position = dim_settings.get("position", "outside")

        if position == "inside":
            horiz_y = scaled_y + scaled_h - line_offset
            vert_x = scaled_x + scaled_w - line_offset
            horiz_text_y = horiz_y - text_offset
            vert_text_x = vert_x - text_offset
            horiz_text_va = "top"
            vert_text_ha = "right"
        else:
            horiz_y = scaled_y + scaled_h + line_offset
            vert_x = scaled_x + scaled_w + line_offset
            horiz_text_y = horiz_y + text_offset
            vert_text_x = vert_x + text_offset
            horiz_text_va = "bottom"
            vert_text_ha = "left"

        ax.plot([scaled_x, scaled_x + scaled_w], [horiz_y, horiz_y],
                color=line_color, linewidth=line_thickness)
        ax.plot([scaled_x, scaled_x], [horiz_y - tick_length / 2, horiz_y + tick_length / 2],
                color=line_color, linewidth=line_thickness)
        ax.plot([scaled_x + scaled_w, scaled_x + scaled_w],
                [horiz_y - tick_length / 2, horiz_y + tick_length / 2],
                color=line_color, linewidth=line_thickness)
        ax.text(scaled_x + scaled_w / 2, horiz_text_y, f"{w:.1f} ft",
                ha="center", va=horiz_text_va, fontsize=font_size, color=line_color)

        ax.plot([vert_x, vert_x], [scaled_y, scaled_y + scaled_h],
                color=line_color, linewidth=line_thickness)
        ax.plot([vert_x - tick_length / 2, vert_x + tick_length / 2], [scaled_y, scaled_y],
                color=line_color, linewidth=line_thickness)
        ax.plot([vert_x - tick_length / 2, vert_x + tick_length / 2],
                [scaled_y + scaled_h, scaled_y + scaled_h],
                color=line_color, linewidth=line_thickness)
        ax.text(vert_text_x, scaled_y + scaled_h / 2, f"{h:.1f} ft",
                ha=vert_text_ha, va="center", fontsize=font_size,
                color=line_color, rotation=90)

    def _draw_doors(self, ax, style, scale_factor, offset_x, offset_y):
        wall_thickness = style["line_styles"]["interior_wall"]["thickness"]

        for door in self.doors:
            pos = door.get("pos")
            if not isinstance(pos, list) or len(pos) != 2:
                continue
            (x1, y1), (x2, y2) = pos
            sx1 = x1 * scale_factor + offset_x
            sy1 = y1 * scale_factor + offset_y
            sx2 = x2 * scale_factor + offset_x
            sy2 = y2 * scale_factor + offset_y

            door_width = abs(sx2 - sx1) if abs(sy1 - sy2) < 1e-6 else abs(sy2 - sy1)
            door_thickness = wall_thickness * 0.3

            if abs(sx1 - sx2) < 1e-6:  # Vertical door
                is_left_wall = sx1 == self.rect[0] * scale_factor + offset_x
                if is_left_wall:
                    door_rect = patches.Rectangle(
                        (sx1, min(sy1, sy2)), door_thickness, door_width,
                        linewidth=1.0, edgecolor="black", facecolor="white")
                else:
                    door_rect = patches.Rectangle(
                        (sx1 - door_thickness, min(sy1, sy2)), door_thickness, door_width,
                        linewidth=1.0, edgecolor="black", facecolor="white")
                ax.add_patch(door_rect)
                ax.plot([sx1, sx1], [sy1, sy2], color="black", linewidth=1.5)
                swing_in = door.get("swing", "in") == "in"
                center_y = min(sy1, sy2)
                center_x = sx1
                arc_radius = door_width
                arc_angle = 54
                if is_left_wall:
                    theta = (0, arc_angle) if swing_in else (180 - arc_angle, 180)
                else:
                    theta = (180 - arc_angle, 180) if swing_in else (0, arc_angle)
                ax.add_patch(patches.Arc((center_x, center_y), arc_radius * 2, arc_radius * 2,
                                         angle=0, theta1=theta[0], theta2=theta[1],
                                         color="black", linewidth=2.0))
            elif abs(sy1 - sy2) < 1e-6:  # Horizontal door
                is_bottom_wall = sy1 == self.rect[1] * scale_factor + offset_y
                if is_bottom_wall:
                    door_rect = patches.Rectangle(
                        (min(sx1, sx2), sy1), door_width, door_thickness,
                        linewidth=1.0, edgecolor="black", facecolor="white")
                else:
                    door_rect = patches.Rectangle(
                        (min(sx1, sx2), sy1 - door_thickness), door_width, door_thickness,
                        linewidth=1.0, edgecolor="black", facecolor="white")
                ax.add_patch(door_rect)
                ax.plot([sx1, sx2], [sy1, sy1], color="black", linewidth=1.5)
                swing_in = door.get("swing", "in") == "in"
                center_x = min(sx1, sx2)
                center_y = sy1
                arc_radius = door_width
                arc_angle = 54
                if is_bottom_wall:
                    theta = (90, 90 + arc_angle) if swing_in else (270 - arc_angle, 270)
                else:
                    theta = (270 - arc_angle, 270) if swing_in else (90, 90 + arc_angle)
                ax.add_patch(patches.Arc((center_x, center_y), arc_radius * 2, arc_radius * 2,
                                         angle=0, theta1=theta[0], theta2=theta[1],
                                         color="black", linewidth=2.0))
            # Diagonal doors are rejected by the loader; nothing to draw here.

    def _draw_windows(self, ax, style, scale_factor, offset_x, offset_y, boundary=None):
        """Draw windows, only when they lie on an exterior wall."""
        window_frame_style = style["line_styles"]["window_frame"]
        window_center_style = style["line_styles"]["window_center"]
        window_settings = style.get("window_settings", {"width": 4.0, "height": 3.0})
        window_width = window_settings.get("width", 4.0)
        window_height = window_settings.get("height", 3.0)

        for window in self.windows:
            pos = window.get("pos")
            if not isinstance(pos, list) or len(pos) != 2:
                continue
            (x1, y1), (x2, y2) = pos
            wall = get_window_wall_info(self.rect, pos, boundary)
            if wall is None:
                continue
            sx1 = x1 * scale_factor + offset_x
            sy1 = y1 * scale_factor + offset_y
            sx2 = x2 * scale_factor + offset_x
            sy2 = y2 * scale_factor + offset_y
            thickness = window_frame_style["thickness"]

            if wall in ("left", "right"):
                mid_y = (sy1 + sy2) / 2
                half_height = (window_height * scale_factor) / 2
                rect_y = mid_y - half_height
                height = window_height * scale_factor
                rect_x = sx1 - thickness if wall == "left" else sx1
                ax.add_patch(patches.Rectangle(
                    (rect_x, rect_y), thickness, height,
                    linewidth=1.0, edgecolor=window_frame_style.get("edge_color", "black"),
                    facecolor=window_frame_style["color"], alpha=1.0, zorder=2))
                ax.plot([sx1, sx1], [rect_y, rect_y + height],
                        color=window_center_style["color"],
                        linewidth=window_center_style["thickness"], zorder=3)
                ax.plot([sx1 - thickness / 4 if wall == "left" else sx1 + thickness / 4,
                         sx1 + thickness / 4 if wall == "left" else sx1 - thickness / 4],
                        [mid_y, mid_y],
                        color=window_center_style["color"],
                        linewidth=window_center_style["thickness"], zorder=3)
            elif wall in ("top", "bottom"):
                mid_x = (sx1 + sx2) / 2
                half_width = (window_width * scale_factor) / 2
                rect_x = mid_x - half_width
                width = window_width * scale_factor
                rect_y = sy1 - thickness if wall == "bottom" else sy1
                ax.add_patch(patches.Rectangle(
                    (rect_x, rect_y), width, thickness,
                    linewidth=1.0, edgecolor=window_frame_style.get("edge_color", "black"),
                    facecolor=window_frame_style["color"], alpha=1.0, zorder=2))
                ax.plot([rect_x, rect_x + width], [sy1, sy1],
                        color=window_center_style["color"],
                        linewidth=window_center_style["thickness"], zorder=3)
                ax.plot([mid_x, mid_x],
                        [sy1 - thickness / 4 if wall == "bottom" else sy1 + thickness / 4,
                         sy1 + thickness / 4 if wall == "bottom" else sy1 - thickness / 4],
                        color=window_center_style["color"],
                        linewidth=window_center_style["thickness"], zorder=3)
