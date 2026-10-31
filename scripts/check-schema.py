"""Validate plan files (YAML/JSON) against schema/plan-v1.json.

CI contract job only — the runtime validators in
renderer/src/floorplan/data_loader.py and editor/modules/plan.js
remain the enforcement point inside the programs. Requires the
``jsonschema`` package (installed in the CI job, not a runtime
dependency of the renderer).
"""

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def main(argv) -> int:
    schema = json.loads((ROOT / "schema" / "plan-v1.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for arg in argv:
        path = Path(arg)
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            location = ".".join(str(p) for p in err.path)
            errors.append(f"{arg}: {location}: {err.message}" if location else f"{arg}: {err.message}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"OK: {len(argv)} plan file(s) match schema/plan-v1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
