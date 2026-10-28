"""Load and validate plan files (YAML or JSON) into :class:`Plan` objects."""

import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple

import yaml

from floorplan.models import Plan
from floorplan.room import Room

logger = logging.getLogger(__name__)

_TOL = 1e-6


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_point(value: Any, what: str) -> List[float]:
    if not isinstance(value, list) or len(value) != 2 or not all(_is_number(v) for v in value):
        raise ValueError(f"{what} must be a list of 2 numbers")
    return [float(value[0]), float(value[1])]


def _as_segment(value: Any, what: str) -> List[List[float]]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{what} must be [[x1, y1], [x2, y2]]")
    return [_as_point(value[0], what), _as_point(value[1], what)]


def _as_axis_aligned_segment(value: Any, what: str) -> List[List[float]]:
    segment = _as_segment(value, what)
    (x1, y1), (x2, y2) = segment
    if abs(x1 - x2) > _TOL and abs(y1 - y2) > _TOL:
        raise ValueError(f"{what} must be horizontal or vertical, got {value!r}")
    return segment


def _validate_opening(entry: Any, index: int, what: str) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"{what} {index} must be a dictionary")
    if "pos" not in entry:
        raise ValueError(f"{what} {index} must have a 'pos' key")
    pos = _as_axis_aligned_segment(entry["pos"], f"{what} {index} pos")
    validated: dict[str, Any] = {"pos": pos}
    if "swing" in entry:
        if entry["swing"] not in ("in", "out"):
            raise ValueError(f"{what} {index} swing must be 'in' or 'out'")
        validated["swing"] = entry["swing"]
    for key in ("editor",):
        if key in entry:
            validated[key] = entry[key]
    return validated


def _validate_room(room_dict: Any, index: int) -> Room:
    if not isinstance(room_dict, dict):
        raise ValueError(f"Room {index} must be a dictionary")
    if "name" not in room_dict:
        raise ValueError(f"Room {index} must have a 'name' key")
    if "rect" not in room_dict:
        raise ValueError(f"Room {index} must have a 'rect' key")
    rect = room_dict["rect"]
    if not isinstance(rect, list) or len(rect) != 4 or not all(_is_number(v) for v in rect):
        raise ValueError(f"Room '{room_dict['name']}' rect must be a list of 4 numbers")
    doors = room_dict.get("doors", [])
    if not isinstance(doors, list):
        raise ValueError(f"Room '{room_dict['name']}' doors must be a list")
    windows = room_dict.get("windows", [])
    if not isinstance(windows, list):
        raise ValueError(f"Room '{room_dict['name']}' windows must be a list")
    return Room(
        name=room_dict["name"],
        rect=[float(v) for v in rect],
        doors=[_validate_opening(d, i, "door") for i, d in enumerate(doors)],
        windows=[_validate_opening(w, i, "window") for i, w in enumerate(windows)],
    )


def _validate_boundary(raw: Any) -> Optional[List[List[float]]]:
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) < 3:
        raise ValueError("'boundary' must be a list of at least 3 points")
    return [_as_point(p, f"Boundary point {i}") for i, p in enumerate(raw)]


def _validate_segment_list(raw: Any, key: str) -> List[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError(f"'{key}' must be a list")
    out = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or "pos" not in entry:
            raise ValueError(f"{key} {i} must be a dictionary with a 'pos' key")
        out.append({"pos": _as_segment(entry["pos"], f"{key} {i} pos")})
    return out


def _validate_labels(raw: Any) -> List[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("'labels' must be a list")
    out = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or "text" not in entry or "point" not in entry:
            raise ValueError(f"Label {i} must have 'text' and 'point' keys")
        item: dict[str, Any] = {
            "text": str(entry["text"]),
            "point": _as_point(entry["point"], f"Label {i} point"),
        }
        if "rotation" in entry:
            if not _is_number(entry["rotation"]):
                raise ValueError(f"Label {i} rotation must be a number")
            item["rotation"] = float(entry["rotation"])
        out.append(item)
    return out


def _validate_dimensions(raw: Any) -> List[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("'dimensions' must be a list")
    out = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or "pos" not in entry:
            raise ValueError(f"Dimension {i} must have a 'pos' key")
        item: dict[str, Any] = {"pos": _as_segment(entry["pos"], f"Dimension {i} pos")}
        if "label" in entry:
            item["label"] = str(entry["label"])
        out.append(item)
    return out


def _validate_objects(raw: Any) -> List[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("'objects' must be a list")
    out = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict) or "kind" not in entry or "rect" not in entry:
            raise ValueError(f"Object {i} must have 'kind' and 'rect' keys")
        if entry["kind"] not in ("stairs", "road"):
            raise ValueError(f"Object {i} kind must be 'stairs' or 'road'")
        rect = entry["rect"]
        if not isinstance(rect, list) or len(rect) != 4 or not all(_is_number(v) for v in rect):
            raise ValueError(f"Object {i} rect must be a list of 4 numbers")
        item: dict[str, Any] = {
            "kind": entry["kind"],
            "rect": [float(v) for v in rect],
        }
        if "label" in entry and entry["label"] is not None:
            item["label"] = str(entry["label"])
        out.append(item)
    return out


def plan_from_dict(raw_data: Any) -> Plan:
    """Validate a parsed plan mapping and build a :class:`Plan`."""
    if not isinstance(raw_data, dict):
        raise ValueError("Plan root must be a dictionary")
    version = raw_data.get("version", 1)
    if version != 1:
        raise ValueError(f"Unsupported plan version: {version!r} (expected 1)")
    if "rooms" not in raw_data:
        raise ValueError("Plan must contain a 'rooms' key")
    rooms_data = raw_data["rooms"]
    if not isinstance(rooms_data, list):
        raise ValueError("'rooms' must be a list")
    rooms = [_validate_room(r, i) for i, r in enumerate(rooms_data)]
    boundary = _validate_boundary(raw_data.get("boundary"))

    openings = []
    for i, entry in enumerate(raw_data.get("openings", [])):
        if not isinstance(entry, dict) or "kind" not in entry:
            raise ValueError(f"Opening {i} must have a 'kind' key")
        if entry["kind"] not in ("door", "window"):
            raise ValueError(f"Opening {i} kind must be 'door' or 'window'")
        validated = _validate_opening(entry, i, "opening")
        validated["kind"] = entry["kind"]
        openings.append(validated)

    title = raw_data.get("title")
    address = raw_data.get("address")
    date = raw_data.get("date")
    for key, value in (("title", title), ("address", address), ("date", date)):
        if value is not None and not isinstance(value, (str, int, float)):
            raise ValueError(f"'{key}' must be a string")

    return Plan(
        rooms=rooms,
        boundary=boundary,
        walls=_validate_segment_list(raw_data.get("walls", []), "walls"),
        openings=openings,
        labels=_validate_labels(raw_data.get("labels", [])),
        dimensions=_validate_dimensions(raw_data.get("dimensions", [])),
        objects=_validate_objects(raw_data.get("objects", [])),
        title=str(title) if title is not None else None,
        address=str(address) if address is not None else None,
        date=str(date) if date is not None else None,
        version=1,
    )


def load_plan(filepath: str | Path) -> Plan:
    """Load a plan from a YAML (``.yaml``/``.yml``) or JSON (``.json``) file."""
    path = Path(filepath)
    logger.info("Loading floor plan data from %s", path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("File not found: %s", path)
        raise
    try:
        if path.suffix.lower() == ".json":
            raw_data = json.loads(text)
        else:
            raw_data = yaml.safe_load(text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        logger.error("Parsing error in %s: %s", path, exc)
        raise ValueError(f"Could not parse {path}: {exc}") from exc
    plan = plan_from_dict(raw_data)
    logger.info("Successfully loaded %d rooms from %s", len(plan.rooms), path)
    return plan


def load_floor_plan(filepath: str) -> Tuple[List[Room], Optional[List]]:
    """Legacy shape: return ``(rooms, boundary)`` for a plan file."""
    plan = load_plan(filepath)
    return plan.rooms, plan.boundary


def dump_plan(plan: Plan, filepath: str | Path) -> None:
    """Write a plan to YAML or JSON, chosen by the output suffix."""
    path = Path(filepath)
    data = plan.to_dict()
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
