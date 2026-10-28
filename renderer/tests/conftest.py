from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.fixture()
def example_files():
    return EXAMPLES / "floor_plan.yaml", EXAMPLES / "floor_plan_style.yaml"
