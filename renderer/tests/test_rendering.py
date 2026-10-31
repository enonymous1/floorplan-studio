import json
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")

from floorplan.data_loader import load_plan
from floorplan.drawing import draw_floor_plan, parse_paper_size, parse_scale
from floorplan.room import Room, get_window_wall_info
from floorplan.style_loader import load_style

def test_parse_helpers():
    import pytest

    assert parse_scale("1/4") == 0.25
    assert parse_scale(" 1/4 ") == 0.25
    assert parse_scale("0.25") == 0.25
    assert parse_scale(0.5) == 0.5
    # Unknown scales fail loudly now instead of silently rendering
    # at 1/4" — a typo must not produce a wrong-size page.
    with pytest.raises(ValueError, match="Unknown scale"):
        parse_scale("bogus")
    assert parse_paper_size("8.5x11") == (8.5, 11)
    assert parse_paper_size("a4", "horizontal") == (11.69, 8.27)
    assert parse_paper_size("8.5 x 11") == (8.5, 11)
    with pytest.raises(ValueError, match="Unknown paper size"):
        parse_paper_size("bogus")


def test_window_wall_info():
    rect = [0, 0, 20, 15]
    boundary = [[0, 0], [32, 0], [32, 27], [0, 27]]
    # The Living Room's top wall (y=15) is interior: bedrooms sit above
    # it, so its windows are not exterior. A top-floor room's top wall is.
    assert get_window_wall_info(rect, ((2, 15), (8, 15)), boundary) is None
    top_room = [0, 15, 15, 12]
    assert get_window_wall_info(top_room, ((2, 27), (8, 27)), boundary) == "top"
    assert get_window_wall_info(rect, ((0, 5), (0, 10)), boundary) == "left"
    # Interior wall: on the room edge but not the exterior boundary.
    assert get_window_wall_info(rect, ((20, 5), (20, 10)), boundary) is None
    # No boundary: every room wall counts as exterior.
    assert get_window_wall_info(rect, ((20, 5), (20, 10)), None) == "right"
    # Window not on any wall.
    assert get_window_wall_info(rect, ((5, 5), (10, 5)), boundary) is None


def test_room_validation():
    room = Room("R", [0, 0, 10, 10])
    assert room.get_area() == 100
    for bad in ([0, 0, 0, 10], [0, 0, 10], "rect"):
        try:
            Room("R", bad)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_render_sample_creates_output_dir(tmp_path, example_files):
    plan_path, style_path = example_files
    plan = load_plan(plan_path)
    style = load_style(style_path)
    out_dir = tmp_path / "nested" / "output"  # does not exist yet
    written = draw_floor_plan(plan, style, output_dir=str(out_dir))
    assert len(written) == 3
    main = out_dir / "floor_plan.svg"
    assert main.exists()
    ET.parse(main)  # well-formed SVG
    text = main.read_text(encoding="utf-8")
    assert "Living Room" in text
    assert "Residential Floor Plan" in text


def test_north_arrow_stays_on_page(example_files):
    # The original arrow took page dimensions as offsets and landed
    # off-page (clipped out of the SVG). Assert geometry directly:
    # SVG text is rendered as paths, so ">N<" never appears in output.
    import matplotlib.pyplot as plt

    from floorplan.drawing import draw_north_arrow

    _, style_path = example_files
    style = load_style(style_path)
    fig, ax = plt.subplots()
    ax.set_xlim(0, 850)
    ax.set_ylim(0, 1100)
    draw_north_arrow(ax, style, 25, 850, 1100)
    assert ax.patches, "north arrow patch missing"
    vertices = ax.patches[-1].get_path().vertices
    assert vertices.min(axis=0)[0] >= 0 and vertices.max(axis=0)[0] <= 850
    assert vertices.min(axis=0)[1] >= 0 and vertices.max(axis=0)[1] <= 1100
    assert [t.get_text() for t in ax.texts] == ["N"]
    x, y = ax.texts[0].get_position()
    assert 0 <= x <= 850 and 0 <= y <= 1100
    # Regression: the "N" used to sit at the shaft/head join, centred
    # on the black arrowhead, so it was invisible. It must sit
    # above the arrow's actual tip (shaft + head length).
    assert y > vertices.max(axis=0)[1]
    plt.close(fig)


def test_door_leaf_and_arc():
    # Regression: horizontal arcs were offset 90 degrees (a
    # bottom-wall door swinging in drew theta 90-144, north-west of
    # its hinge, instead of 0-90), vertical arcs were truncated to
    # 54 degrees, and a line along the wall filled the wall gap, so
    # doors read as stray curves. Now every door is one leaf line
    # plus one full quarter-circle arc, meeting at the hinge and
    # at the wall endpoint.
    import matplotlib.pyplot as plt
    from matplotlib.patches import Arc

    cases = [
        # (room rect, door pos, swing, expected theta, expected leaf end)
        ([0, 0, 20, 15], [[10, 0], [13, 0]], "in", (0, 90), (250, 75)),
        ([0, 0, 20, 15], [[10, 0], [13, 0]], "out", (270, 360), (250, -75)),
        ([0, 0, 20, 15], [[10, 15], [13, 15]], "in", (270, 360), (250, 300)),
        ([0, 0, 20, 15], [[10, 15], [13, 15]], "out", (0, 90), (250, 450)),
        ([0, 0, 20, 15], [[0, 6], [0, 9]], "in", (0, 90), (75, 150)),
        ([0, 0, 20, 15], [[0, 6], [0, 9]], "out", (90, 180), (-75, 150)),
        ([0, 0, 20, 15], [[20, 6], [20, 9]], "in", (90, 180), (425, 150)),
        ([0, 0, 20, 15], [[20, 6], [20, 9]], "out", (0, 90), (575, 150)),
    ]
    for rect, pos, swing, theta, leaf_end in cases:
        fig, ax = plt.subplots()
        room = Room("R", rect)
        room.doors = [{"pos": pos, "swing": swing}]
        room._draw_doors(ax, {}, 25, 0, 0)
        arcs = [p for p in ax.patches if isinstance(p, Arc)]
        assert len(arcs) == 1, (rect, pos, swing)
        assert (arcs[0].theta1, arcs[0].theta2) == theta, (rect, pos, swing)
        # Exactly one line: the open leaf. No along-wall line.
        assert len(ax.lines) == 1, (rect, pos, swing)
        line = ax.lines[0]
        hinge = (min(pos[0][0], pos[1][0]) * 25, min(pos[0][1], pos[1][1]) * 25)
        assert (line.get_xdata()[0], line.get_ydata()[0]) == hinge
        assert (line.get_xdata()[1], line.get_ydata()[1]) == leaf_end
        plt.close(fig)


def test_boundary_l_shaped_labels():
    import matplotlib.pyplot as plt

    from floorplan.drawing import draw_boundary

    style = {
        "settings": {"units": "feet"},
        "line_styles": {"exterior_wall": {"thickness": 4.0, "color": "black"}},
    }
    fig, ax = plt.subplots()
    draw_boundary(ax, [[0.0, -10.0], [20.0, -10.0], [20.0, 0.0],
                       [32.0, 0.0], [32.0, 27.0], [0.0, 27.0]],
                  style, 25, 0, 0)
    # Overall bounding dimensions, not per-edge lengths.
    assert [t.get_text() for t in ax.texts] == ["32.0 feet", "37.0 feet"]
    plt.close(fig)


def test_sample_plan_has_no_duplicate_rooms(example_files):
    # Regression for the sample that shipped with a Hallway room
    # identical to the Bathroom, and a Garage outside the boundary.
    plan_path, _ = example_files
    plan = load_plan(plan_path)
    assert [r.name for r in plan.rooms] == [
        "Living Room", "Kitchen", "Hall", "Master Bedroom", "Bathroom", "Bedroom 2", "Garage",
    ]
    xs = [p[0] for p in plan.boundary]
    ys = [p[1] for p in plan.boundary]
    for room in plan.rooms:
        x, y, w, h = room.rect
        assert min(xs) <= x and x + w <= max(xs)
        assert min(ys) <= y and y + h <= max(ys)


def test_passage_draws_no_leaf_or_arc():
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    room = Room("R", [0, 0, 20, 15])
    room.doors = [{"pos": [[20, 6], [20, 9]], "swing": "none"}]
    room._draw_doors(ax, {}, 25, 0, 0)
    assert len(ax.patches) == 0 and len(ax.lines) == 0
    plt.close(fig)


def test_boundary_breaks_at_exterior_door():
    import matplotlib.pyplot as plt

    from floorplan.drawing import draw_boundary

    style = {
        "settings": {"units": "feet"},
        "line_styles": {"exterior_wall": {"thickness": 4.0, "color": "black"}},
    }
    fig, ax = plt.subplots()
    boundary = [[0.0, -10.0], [20.0, -10.0], [20.0, 0.0],
                [32.0, 0.0], [32.0, 27.0], [0.0, 27.0]]
    # Front door on the west (closing) edge, y 6-9.
    draw_boundary(ax, boundary, style, 25, 0, 0,
                  doors=[{"pos": [[0.0, 6.0], [0.0, 9.0]]}])
    west_lines = [(tuple(line.get_xdata()), tuple(line.get_ydata()))
                  for line in ax.lines if set(line.get_xdata()) == {0.0}]
    # Closing edge runs 27 -> -10, broken at the door: 27-9 and 6--10.
    assert ((0.0, 0.0), (675.0, 225.0)) in west_lines
    assert ((0.0, 0.0), (150.0, -250.0)) in west_lines
    plt.close(fig)


def test_sample_circulation(example_files):
    # The sample's circulation contract: a short central Hall in
    # the bedroom wing (not a corridor across the house), every
    # bedroom/bathroom door paired with a Hall door on the same
    # segment, the Living-Kitchen passage in both rooms with swing
    # "none", and a front door that is not the Garage door.
    plan_path, _ = example_files
    plan = load_plan(plan_path)
    by_name = {r.name: r for r in plan.rooms}

    def door_map(room):
        return {tuple(map(tuple, d["pos"])): d.get("swing") for d in room.doors}

    living = door_map(by_name["Living Room"])
    kitchen = door_map(by_name["Kitchen"])
    hall = door_map(by_name["Hall"])
    # The hall is a small room in the bedroom wing, not a strip
    # across the house: 6 ft wide, 7 ft deep, bedrooms 13 ft deep.
    assert by_name["Hall"].rect == [14.0, 14.0, 6.0, 7.0]
    assert by_name["Master Bedroom"].rect[3] == 13.0
    assert by_name["Bedroom 2"].rect[3] == 13.0
    # Front door: west wall of the Living Room, into the house.
    assert living[((0.0, 6.0), (0.0, 9.0))] == "in"
    # Open passage: in both rooms, no leaf, no arc.
    passage = ((20.0, 6.0), (20.0, 9.0))
    assert living[passage] == "none" and kitchen[passage] == "none"
    # Every bedroom-wing room has exactly one door, and it is a
    # Hall door, swinging into that room.
    for name in ("Master Bedroom", "Bathroom", "Bedroom 2"):
        doors = door_map(by_name[name])
        assert len(doors) == 1, name
        pos, swing = next(iter(doors.items()))
        assert swing == "in" and pos in hall, (name, pos)
    # Hall has its Living Room entry plus those three doors.
    assert len(hall) == 4
    assert ((15.0, 14.0), (18.0, 14.0)) in hall
    # No door is shared between two bedrooms/bathroom directly.
    north = ["Master Bedroom", "Bathroom", "Bedroom 2"]
    for i, a in enumerate(north):
        for b in north[i + 1:]:
            assert not (set(door_map(by_name[a])) & set(door_map(by_name[b]))), (a, b)


def test_render_editor_plan(tmp_path, example_files):
    _, style_path = example_files
    plan_path = tmp_path / "editor.json"
    plan_path.write_text(json.dumps({
        "version": 1,
        "rooms": [{
            "name": "Room 1", "rect": [0, -15, 20, 15],
            "doors": [{"pos": [[10, -15], [13, -15]], "swing": "in"}],
            "windows": [],
        }],
        "walls": [{"pos": [[30, 0], [30, 10]]}],
    }), encoding="utf-8")
    plan = load_plan(plan_path)
    style = load_style(style_path)
    written = draw_floor_plan(plan, style, output_dir=str(tmp_path / "out"), fmt="png")
    assert written[0].suffix == ".png" and written[0].exists()


def test_render_empty_plan(tmp_path, example_files):
    _, style_path = example_files
    plan_path = tmp_path / "empty.json"
    plan_path.write_text('{"version": 1, "rooms": []}', encoding="utf-8")
    plan = load_plan(plan_path)
    style = load_style(style_path)
    written = draw_floor_plan(plan, style, output_dir=str(tmp_path / "out"))
    assert written[0].exists()


def test_wall_gap_tolerance_matches_editor(tmp_path, example_files):
    # Regression for the tolerance mismatch: the editor attaches a
    # door within 0.01 ft of a wall edge, so a door 0.005 ft off the
    # bottom edge must still split that wall into two segments.
    import matplotlib.pyplot as plt

    from floorplan.room import WALL_TOLERANCE_FT

    assert WALL_TOLERANCE_FT == 0.01
    room = Room("R", [0, 0, 20, 15])
    style = {"line_styles": {"interior_wall": {"color": "black", "thickness": 1.0}}}
    fig, ax = plt.subplots()
    scale_factor = 25
    tol = WALL_TOLERANCE_FT * scale_factor
    gaps = [{"x1": 250, "y1": -0.125, "x2": 325, "y2": -0.125, "is_vertical": False}]
    room._draw_wall_segment(ax, style, 0, 0, 500, 0, gaps, "bottom", tol)
    assert len(ax.lines) == 2  # 0–250 and 325–500, with the gap between
    plt.close(fig)


def test_window_wall_tolerance_matches_editor():
    # A window 0.005 ft off the exterior boundary still counts as
    # exterior, matching the editor's 0.01 ft attachment tolerance.
    boundary = [[0, 0], [32, 0], [32, 27], [0, 27]]
    top_room = [0, 15, 15, 12]
    assert get_window_wall_info(top_room, ((2, 27.005), (8, 27.005)), boundary) == "top"


def test_no_extras_writes_only_main_page(tmp_path, example_files):
    plan_path, style_path = example_files
    plan = load_plan(plan_path)
    style = load_style(style_path)
    out_dir = tmp_path / "out"
    written = draw_floor_plan(plan, style, output_dir=str(out_dir), extras=False)
    assert written == [out_dir / "floor_plan.svg"]
    assert not (out_dir / "floor_plan_settings.svg").exists()


def test_oversize_plan_warns(caplog, tmp_path, example_files):
    import logging

    _, style_path = example_files
    plan_path = tmp_path / "huge.json"
    plan_path.write_text(json.dumps({
        "version": 1,
        "rooms": [{"name": "Big", "rect": [0, 0, 500, 500], "doors": [], "windows": []}],
    }), encoding="utf-8")
    plan = load_plan(plan_path)
    style = load_style(style_path)
    with caplog.at_level(logging.WARNING, logger="floorplan.drawing"):
        draw_floor_plan(plan, style, output_dir=str(tmp_path / "out"))
    assert "clipped, not fitted" in caplog.text
