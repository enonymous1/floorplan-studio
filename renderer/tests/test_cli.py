import subprocess
import sys

from floorplan.cli import main


def test_cli_render_and_convert(tmp_path, example_files):
    plan_path, style_path = example_files
    out_dir = tmp_path / "out"
    assert main(["render", str(plan_path), "--style", str(style_path),
                 "--output-dir", str(out_dir)]) == 0
    assert (out_dir / "floor_plan.svg").exists()

    converted = tmp_path / "plan.json"
    assert main(["convert", str(plan_path), str(converted)]) == 0
    assert main(["render", str(converted), "--output-dir", str(tmp_path / "out2")]) == 0

    # Bad input exits 1, without a traceback.
    assert main(["render", str(tmp_path / "missing.yaml")]) == 1


def test_cli_bad_style_exits_1_without_traceback(tmp_path, example_files, capsys):
    import yaml

    plan_path, _ = example_files
    style_path = tmp_path / "bad-style.yaml"
    style_path.write_text(yaml.safe_dump({"settings": {}}), encoding="utf-8")
    assert main(["render", str(plan_path), "--style", str(style_path),
                 "--output-dir", str(tmp_path / "out")]) == 1
    captured = capsys.readouterr()
    assert "floorplan: error:" in captured.err
    assert "Traceback" not in captured.err


def test_cli_entry_point_from_fresh_cwd(tmp_path, example_files):
    # Exercise the installed console script path via `python -m floorplan`.
    plan_path, _ = example_files
    result = subprocess.run(
        [sys.executable, "-m", "floorplan", "render", str(plan_path),
         "--output-dir", str(tmp_path / "out")],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out" / "floor_plan.svg").exists()
