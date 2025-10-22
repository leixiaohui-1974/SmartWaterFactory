"""
Long-run energy and disturbance comparison.

This script executes several scenarios (precision PID baseline, precision PID under a
strict energy budget, and adaptive PID) over a long simulation horizon.  It
collects key metrics and writes a Markdown summary table for quick comparison.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import ENERGY_COORDINATION  # noqa: E402
from run_simulation import run_and_log_simulation  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"
SUMMARY_PATH = DATA_DIR / "long_run_summary.md"


@dataclass
class ScenarioConfig:
    name: str
    controller_type: str
    log_name: str
    steps: int = 600
    energy_budget: Optional[float] = None
    sensor_provider: Optional[Callable[..., Dict[str, float]]] = None


@dataclass
class ScenarioResult:
    name: str
    controller_type: str
    log_path: Path
    average_turbidity: float
    average_dissolved_oxygen: float
    total_cost: float
    coagulant_cost: float
    aeration_cost: float
    fault_events: int
    average_energy_scale: float
    min_energy_scale: float


def sensor_with_disturbance(**kwargs) -> Dict[str, float]:
    """
    Mild sensor noise; occasional bias around certain timestamps.
    """
    step_index = kwargs.get("step_index", 0)
    result = {
        "turbidity": 0.0,
        "dissolved_oxygen": 0.0,
    }
    if 300 <= step_index < 360:
        result["turbidity"] = 1.5
    return result


SCENARIOS: List[ScenarioConfig] = [
    ScenarioConfig(
        name="precision_pid_baseline",
        controller_type="precision-pid",
        log_name="long_run_precision_pid.csv",
    ),
    ScenarioConfig(
        name="precision_pid_low_budget",
        controller_type="precision-pid",
        log_name="long_run_precision_low_budget.csv",
        energy_budget=20.0,
        sensor_provider=sensor_with_disturbance,
    ),
    ScenarioConfig(
        name="adaptive_pid_full",
        controller_type="adaptive-pid",
        log_name="long_run_adaptive_pid.csv",
    ),
]


def run_scenario(config: ScenarioConfig) -> ScenarioResult:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DATA_DIR / config.log_name

    original_budget = ENERGY_COORDINATION.get("budget_per_step", 0.0)
    original_enabled = ENERGY_COORDINATION.get("enabled", False)

    if config.energy_budget is not None:
        ENERGY_COORDINATION["enabled"] = True
        ENERGY_COORDINATION["budget_per_step"] = config.energy_budget

    try:
        success = run_and_log_simulation(
            steps=config.steps,
            log_file=str(log_path),
            turbidity_setpoint=5.0,
            do_setpoint=8.5,
            controller_type=config.controller_type,
            sensor_provider=config.sensor_provider,
        )
        if not success:
            raise RuntimeError(f"Scenario {config.name} failed to complete.")
    finally:
        ENERGY_COORDINATION["enabled"] = original_enabled
        ENERGY_COORDINATION["budget_per_step"] = original_budget

    with log_path.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    turbidity = [float(r["turbidity"]) for r in rows]
    dissolved_oxygen = [float(r["dissolved_oxygen"]) for r in rows]
    coagulant_cost = [float(r["coagulant_cost"]) for r in rows]
    aeration_cost = [float(r["aeration_cost"]) for r in rows]
    energy_scale = [float(r["energy_scaling_factor"]) for r in rows]
    fault_events = sum(1 for r in rows if float(r["sensor_fault_detected"]) >= 0.5)

    result = ScenarioResult(
        name=config.name,
        controller_type=config.controller_type,
        log_path=log_path,
        average_turbidity=sum(turbidity) / len(turbidity),
        average_dissolved_oxygen=sum(dissolved_oxygen) / len(dissolved_oxygen),
        total_cost=sum(coagulant_cost) + sum(aeration_cost),
        coagulant_cost=sum(coagulant_cost),
        aeration_cost=sum(aeration_cost),
        fault_events=fault_events,
        average_energy_scale=sum(energy_scale) / len(energy_scale),
        min_energy_scale=min(energy_scale),
    )
    return result


def write_summary(results: List[ScenarioResult]) -> None:
    lines = [
        "# 长周期运行汇总",
        "",
        "| 场景 | 控制器 | 平均浊度 (NTU) | 平均溶解氧 (mg/L) | 总成本 | 混凝剂成本 | 曝气成本 | 故障次数 | 平均能耗缩放 | 最小能耗缩放 | 日志路径 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for r in results:
        lines.append(
            f"| {r.name} | {r.controller_type} | {r.average_turbidity:.2f} | "
            f"{r.average_dissolved_oxygen:.2f} | {r.total_cost:.2f} | {r.coagulant_cost:.2f} | "
            f"{r.aeration_cost:.2f} | {r.fault_events} | {r.average_energy_scale:.3f} | "
            f"{r.min_energy_scale:.3f} | {r.log_path.name} |"
        )

    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    results: List[ScenarioResult] = []
    for scenario in SCENARIOS:
        print(f"运行场景: {scenario.name} ({scenario.controller_type})")
        result = run_scenario(scenario)
        results.append(result)
        print(
            f"  平均浊度: {result.average_turbidity:.2f} NTU, "
            f"平均 DO: {result.average_dissolved_oxygen:.2f} mg/L, "
            f"总成本: {result.total_cost:.2f}, "
            f"故障次数: {result.fault_events}"
        )

    write_summary(results)
    print(f"\n汇总报告已生成: {SUMMARY_PATH}")
    for r in results:
        if r.min_energy_scale < 0.9:
            print(
                f"- {r.name}: 能耗预算紧张（最小缩放 {r.min_energy_scale:.2f}），"
                "可考虑提升预算或调整参数。"
            )
        if r.fault_events > 0:
            print(f"- {r.name}: 共检测到 {r.fault_events} 次传感器故障，请检查容错策略。")


if __name__ == "__main__":
    main()
