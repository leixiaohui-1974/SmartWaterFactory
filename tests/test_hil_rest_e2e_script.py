import json
from pathlib import Path

from scripts.run_hil_rest_e2e import build_parser


def test_hil_rest_e2e_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 5056
    assert args.scenario == "steady"
    assert args.fault_sensor == "turbidity"
    assert args.output.endswith("hil_rest_e2e_summary.json")


def test_hil_rest_e2e_parser_custom_values(tmp_path: Path) -> None:
    out = tmp_path / "rest_e2e.json"
    args = build_parser().parse_args(
        [
            "--host", "0.0.0.0",
            "--port", "6000",
            "--scenario", "turbidity_spike",
            "--steps-before-fault", "5",
            "--steps-after-fault", "2",
            "--output", str(out),
            "--reuse-server",
        ]
    )
    assert args.host == "0.0.0.0"
    assert args.port == 6000
    assert args.scenario == "turbidity_spike"
    assert args.steps_before_fault == 5
    assert args.steps_after_fault == 2
    assert args.reuse_server is True
    assert Path(args.output) == out
