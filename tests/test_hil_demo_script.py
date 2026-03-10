import json
from pathlib import Path

from scripts.run_hil_demo import main, run_hil_demo


def test_run_hil_demo_returns_expected_summary() -> None:
    summary = run_hil_demo(
        steps=3,
        scenario="steady",
        dt=1.0,
        seed=11,
        coagulant_dose=4.0,
        aeration_rate=8.0,
        fault_sensor="turbidity",
        fault_mode="stuck",
        fault_value=42.0,
    )

    assert summary["steps"] == 3
    assert summary["latest_snapshot"]["measured_quality"]["turbidity"] == 42.0
    assert len(summary["snapshots"]) == 3


def test_hil_demo_main_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "hil_demo.json"
    exit_code = main(
        [
            "--steps",
            "2",
            "--scenario",
            "turbidity_spike",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["steps"] == 2
    assert payload["scenario"] == "turbidity_spike"
    assert "latest_snapshot" in payload
