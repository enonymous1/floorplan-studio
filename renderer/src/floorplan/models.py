"""Shared plan model.

A plan is the interchange format between the browser editor
(``editor/``) and this renderer. All coordinates are in feet, with
(0, 0) at the bottom-left and y increasing upwards -- the opposite
vertical direction from the editor canvas, which is flipped at the
editor boundary (see ``editor/modules/plan.js``).

Plan shape (version 1)::

    {
      "version": 1,
      "title": "Residential Floor Plan",
      "address": "123 Main Street",
      "date": "2025-09-19",
      "boundary": [[0, 0], [32, 0], [32, 27], [0, 27]],
      "rooms": [
        {"name": "Living Room", "rect": [0, 0, 20, 15],
         "doors": [{"pos": [[10, 0], [13, 0]], "swing": "in"}],
         "windows": [{"pos": [[2, 15], [8, 15]]}]}
      ],
      "walls": [{"pos": [[0, 0], [10, 0]]}],
      "openings": [{"kind": "door", "pos": [[5, 0], [8, 0]], "swing": "in"}],
      "labels": [{"text": "North", "point": [16, 13], "rotation": 0}],
      "dimensions": [{"pos": [[0, 0], [20, 0]], "label": "20.00'"}],
      "objects": [{"kind": "stairs", "rect": [0, 0, 3, 10], "label": null}]
    }

Only ``rooms`` is required to be present (it may be an empty list when
a plan holds only walls/labels). Every other section is optional.
``openings`` holds door/window segments that do not lie on a room
edge; ``walls`` holds standalone wall segments. Editor-only fields
(``swing_direction``/``hinge_at_start``) may ride along on a door
under an ``editor`` key and are ignored by the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from floorplan.room import Room

Point = list[float]
Segment = list[Point]


@dataclass
class Plan:
    rooms: list[Room] = field(default_factory=list)
    boundary: list[Point] | None = None
    walls: list[dict[str, Any]] = field(default_factory=list)
    openings: list[dict[str, Any]] = field(default_factory=list)
    labels: list[dict[str, Any]] = field(default_factory=list)
    dimensions: list[dict[str, Any]] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    title: str | None = None
    address: str | None = None
    date: str | None = None
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to the plain-dict plan shape."""
        data: dict[str, Any] = {"version": self.version}
        if self.title is not None:
            data["title"] = self.title
        if self.address is not None:
            data["address"] = self.address
        if self.date is not None:
            data["date"] = self.date
        if self.boundary is not None:
            data["boundary"] = [list(p) for p in self.boundary]
        data["rooms"] = [
            {
                "name": room.name,
                "rect": list(room.rect),
                "doors": [dict(d) for d in room.doors],
                "windows": [dict(w) for w in room.windows],
            }
            for room in self.rooms
        ]
        if self.walls:
            data["walls"] = [dict(w) for w in self.walls]
        if self.openings:
            data["openings"] = [dict(o) for o in self.openings]
        if self.labels:
            data["labels"] = [dict(label) for label in self.labels]
        if self.dimensions:
            data["dimensions"] = [dict(d) for d in self.dimensions]
        if self.objects:
            data["objects"] = [dict(o) for o in self.objects]
        return data
