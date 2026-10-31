"""Floor plan renderer: YAML/JSON plans to print-ready SVG/PDF/PNG."""

from importlib.metadata import PackageNotFoundError, version

# Single source of truth is the version in renderer/pyproject.toml.
# (Not setuptools' `attr` dynamic version: that would import this
# package at build time, and this module imports matplotlib.)
try:
    __version__ = version("floorplan-studio")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"  # source-tree run, package not installed

from floorplan.data_loader import load_plan
from floorplan.drawing import draw_floor_plan
from floorplan.models import Plan
from floorplan.room import Room, get_window_wall_info
from floorplan.style_loader import load_style

__all__ = [
    "__version__",
    "Plan",
    "Room",
    "draw_floor_plan",
    "get_window_wall_info",
    "load_plan",
    "load_style",
]
