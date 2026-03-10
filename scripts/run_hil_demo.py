#!/usr/bin/env python3
"""Run a minimal hardware-in-the-loop demo and export snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from water_plant_controller.hil import HILSimulator
from water_plant_controller.models.water_quality import WaterQuality


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a SmartWaterFactory HIL demo.")
    parser.add_argument("--steps", type=int, default=20, help="Number of HIL steps to execute.")
    parser.add_argument(
        "--scenario",
        type=str,
        default="steady",
        help="Initial HIL scenario name.",
    )
    parser.add_argument("--dt", type=float, default=1.0, help="HIL step size in seconds.")
    parser.add_argument("--seed", type=int, default=7, help="Deterministic random seed.")
    parser.add_argument(
        "--coagulant-dose",
        type=float,
        default=4.0,
        help="Coagulant dose command in engineering units.",
    )
    parser.add_argument(
        "--aeration-rate",
        type=float,
        default=8.0,
        help="Aeration command in engineering units.",
    )
    parser.add_argument(
        "--fault-sensor",
        type=str,
        default="",
        help="Optional sensor name for fault injection: ph, turbidity, dissolved_oxygen.",
    )
    parser.add_argument(
        "--fault-mode",
        type=str,
        default="none",
        help="Optional fault mode: none, stuck, bias, dropout.",
    )
    parser.add_argument(
        "--fault-value",
        type=float,
        default=None,
        help="Optional fault fixed value.",
    )
    parser.add_argument(
        "--fault-bias",
        type=float,
        default=0.0,
        help="Optional fault bias value.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/hil_demo_summary.json",
        help="Path to write the JSON summary.",
    )
    return parser


def run_hil_demo(
    *,
    steps: int,
    scenario: str,
    dt: float,
    seed: int,
    coagulant_dose: float,
    aeration_rate: float,
    fault_sensor: str = "",
    fault_mode: str = "none",
    fault_value: float | None = None,
    fault_bias: float = 0.0,
) -> Dict[str, Any]:
    if steps < 1:
        raise ValueError("steps must be at least 1")

    simulator = HILSimulator(
        WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=25.0,
            dissolved_oxygen=4.0,
        ),
        dt_s=dt,
        scenario=scenario,
        random_seed=seed,
    )
    simulator.set_control_command("coagulant_dose", coagulant_dose)
    simulator.set_control_command("aeration_rate", aeration_rate)

    if fault_sensor and fault_mode != "none":
        simulator.inject_sensor_fault(
            fault_sensor,
            fault_mode,
            value=fault_value,
            bias=fault_bias,
        )

    snapshots = [snapshot.to_dict() for snapshot in simulator.run_steps(steps)]
    latest = snapshots[-1]

    summary = {
        "steps": steps,
        "scenario": scenario,
        "dt": dt,
        "seed": seed,
        "controls": {
            "coagulant_dose": coagulant_dose,
            "aeration_rate": aeration_rate,
        },
        "fault": {
            "sensor": fault_sensor or None,
            "mode": fault_mode,
            "value": fault_value,
            "bias": fault_bias,
        },
        "latest_snapshot": latest,
        "snapshots": snapshots,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = run_hil_demo(
        steps=args.steps,
        scenario=args.scenario,
        dt=args.dt,
        seed=args.seed,
        coagulant_dose=args.coagulant_dose,
        aeration_rate=args.aeration_rate,
        fault_sensor=args.fault_sensor,
        fault_mode=args.fault_mode,
        fault_value=args.fault_value,
        fault_bias=args.fault_bias,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    latest = summary["latest_snapshot"]
    print(
        "HIL demo complete:",
        f"scenario={summary['scenario']}",
        f"steps={summary['steps']}",
        f"turbidity={latest['measured_quality']['turbidity']:.3f}",
        f"do={latest['measured_quality']['dissolved_oxygen']:.3f}",
        f"output={output_path}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
