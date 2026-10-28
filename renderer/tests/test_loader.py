import json

import pytest
import yaml

from floorplan.data_loader import dump_plan, load_plan, plan_from_dict
from floorplan.style_loader import load_style


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def sample_dict():
    return {
        "version": 1,
        "title": "Test Plan",
        "boundary": [[0, 0], [32, 0], [32, 27], [0, 27]],
        "rooms": [
            {
                "name": "Living Room",
                "rect": [0, 0, 20, 15],
                "doors": [{"pos": [[10, 0], [13, 0]], "swing": "in"}],
                "windows": [{"pos": [[2, 15], [8, 15]]}],
            },
            {"name": "Kitchen", "rect": [20, 0, 12, 15], "doors": [], "windows": []},
        ],
    }


def test_load_yaml_and_json_round_trip(tmp_path):
    yaml_path = write(tmp_path, "plan.yaml", yaml.safe_dump(sample_dict(), sort_keys=False))
    plan = load_plan(yaml_path)
    assert [r.name for r in plan.rooms] == ["Living Room", "Kitchen"]
    assert plan.rooms[0].get_area() == 300
    assert plan.title == "Test Plan"

    json_path = tmp_path / "plan.json"
    dump_plan(plan, json_path)
    reloaded = load_plan(json_path)
    assert reloaded.to_dict() == plan.to_dict()

    yaml_out = tmp_path / "out.yaml"
    dump_plan(plan, yaml_out)
    assert load_plan(yaml_out).to_dict() == plan.to_dict()


def test_load_editor_sections(tmp_path):
    data = sample_dict()
    data.update(
        walls=[{"pos": [[0, 0], [0, 10]]}],
        openings=[{"kind": "door", "pos": [[40, 0], [43, 0]], "swing": "out"}],
        labels=[{"text": "Hall", "point": [5, 5], "rotation": 90}],
        dimensions=[{"pos": [[0, 0], [20, 0]], "label": "20.00'"}],
        objects=[{"kind": "stairs", "rect": [0, 0, 3, 10]}],
    )
    plan = load_plan(write(tmp_path, "plan.json", json.dumps(data)))
    assert len(plan.walls) == 1 and len(plan.openings) == 1
    assert plan.labels[0]["rotation"] == 90
    assert plan.objects[0]["kind"] == "stairs"


def test_validation_rejects_bad_shapes():
    with pytest.raises(ValueError, match="rooms"):
        plan_from_dict({})
    with pytest.raises(ValueError, match="version"):
        plan_from_dict({"version": 2, "rooms": []})
    bad = sample_dict()
    bad["rooms"][0]["rect"] = [0, 0, 20]  # too short
    with pytest.raises(ValueError, match="rect"):
        plan_from_dict(bad)
    bad = sample_dict()
    bad["rooms"][0]["doors"] = [{"pos": [[0, 0], [3, 3]]}]  # diagonal
    with pytest.raises(ValueError, match="horizontal or vertical"):
        plan_from_dict(bad)
    bad = sample_dict()
    bad["rooms"][0]["doors"] = [{"pos": [[10, 0], [13, 0]], "swing": "sideways"}]
    with pytest.raises(ValueError, match="swing"):
        plan_from_dict(bad)
    bad = sample_dict()
    bad["rooms"][0]["rect"] = [0, 0, True, 15]  # bool is not a number here
    with pytest.raises(ValueError, match="rect"):
        plan_from_dict(bad)
    bad = sample_dict()
    bad["boundary"] = [[0, 0], [1, 1]]  # too few points
    with pytest.raises(ValueError, match="boundary"):
        plan_from_dict(bad)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_plan(tmp_path / "nope.yaml")


def test_style_resolution_recursive_and_unknown(tmp_path):
    style = {
        "palette": {"base": "#111111", "alias": "@base"},
        "settings": {"background_color": "#FFFFFF"},
        "line_styles": {"wall": {"color": "@alias", "nested": {"fill": "@base"}}},
        "text_styles": {},
    }
    path = write(tmp_path, "style.yaml", yaml.safe_dump(style))
    loaded = load_style(path)
    assert loaded["line_styles"]["wall"]["color"] == "#111111"
    assert loaded["line_styles"]["wall"]["nested"]["fill"] == "#111111"

    style["line_styles"]["wall"]["color"] = "@missing"
    path = write(tmp_path, "style.yaml", yaml.safe_dump(style))
    with pytest.raises(ValueError, match="Unknown palette reference"):
        load_style(path)
