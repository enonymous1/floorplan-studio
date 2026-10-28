import json
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")

from floorplan.data_loader import load_plan
from floorplan.drawing import draw_floor_plan, parse_paper_size, parse_scale
from floorplan.room import Room, get_window_wall_info
from floorplan.style_loader import load_style

def test_parse_helpers():
    assert parse_scale("1/4") == 0.25
    assert parse_scale("bogus") == 0.25
    assert parse_paper_size("8.5x11") == (8.5, 11)
    assert parse_paper_size("a4", "horizontal") == (11.69, 8.27)
    assert parse_paper_size("bogus") == (8.5, 11)


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
    plt.close(fig)


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
