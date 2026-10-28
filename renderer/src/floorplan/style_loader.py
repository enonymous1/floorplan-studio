"""Load a style file and resolve ``@palette`` references.

References may appear anywhere in the style mapping (nested dicts
and lists included) and may chain through other references. An
unknown reference is an error instead of silently becoming ``None``,
which is what the original one-level resolver did.
"""

import copy
from pathlib import Path
from typing import Any

import yaml

_MAX_DEPTH = 10


def _resolve(value: Any, palette: dict, depth: int) -> Any:
    if depth > _MAX_DEPTH:
        raise ValueError("Palette reference chain is too deep (possible cycle)")
    if isinstance(value, str) and value.startswith("@"):
        key = value[1:]
        if key not in palette:
            raise ValueError(f"Unknown palette reference '@{key}'")
        return _resolve(palette[key], palette, depth + 1)
    if isinstance(value, dict):
        return {k: _resolve(v, palette, depth) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, palette, depth) for v in value]
    return value


def load_style(filepath: str | Path) -> dict:
    """Load a style YAML file with all ``@key`` references resolved."""
    path = Path(filepath)
    with path.open("r", encoding="utf-8") as handle:
        style = yaml.safe_load(handle)
    if not isinstance(style, dict):
        raise ValueError("Style root must be a dictionary")
    palette = style.get("palette", {})
    if not isinstance(palette, dict):
        raise ValueError("'palette' must be a dictionary")
    resolved = copy.deepcopy(style)
    for section, content in resolved.items():
        if section == "palette":
            continue
        resolved[section] = _resolve(content, palette, 0)
    return resolved
