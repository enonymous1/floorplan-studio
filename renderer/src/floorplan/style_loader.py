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

# Sections the renderer actually reads. A style missing one of these
# used to die later with a bare KeyError deep inside drawing; failing
# here, with the file named, is what makes the CLI's no-traceback
# contract hold for custom styles.
_REQUIRED_SECTIONS = ("settings", "line_styles", "text_styles")
_REQUIRED_SETTINGS = ("background_color",)


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
    """Load a style YAML file with all ``@key`` references resolved.

    Raises ValueError (never yaml.YAMLError or KeyError) for a
    malformed file or one missing the sections the renderer needs,
    so the CLI can report it cleanly on stderr.
    """
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as handle:
            style = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"Could not parse style file {path}: {exc}") from exc
    if not isinstance(style, dict):
        raise ValueError("Style root must be a dictionary")
    missing = [s for s in _REQUIRED_SECTIONS if s not in style]
    if missing:
        raise ValueError(
            f"Style file {path} is missing sections: {', '.join(missing)}"
        )
    missing_settings = [k for k in _REQUIRED_SETTINGS if k not in style["settings"]]
    if missing_settings:
        raise ValueError(
            f"Style file {path} settings are missing: {', '.join(missing_settings)}"
        )
    palette = style.get("palette", {})
    if not isinstance(palette, dict):
        raise ValueError("'palette' must be a dictionary")
    resolved = copy.deepcopy(style)
    for section, content in resolved.items():
        if section == "palette":
            continue
        resolved[section] = _resolve(content, palette, 0)
    return resolved
