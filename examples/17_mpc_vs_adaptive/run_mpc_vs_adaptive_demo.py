"""
MPC vs Adaptive PID comparison demo with sensor bias.

This script runs the water-plant simulator twice under identical process disturbances
and a slowly drifting turbidity sensor:

1. Adaptive PID controller (baseline from the project).
2. Reliability-aware MPC controller introduced in this work.

Each run logs the full diagnostics to CSV and a comparison plot is generated that
highlights turbidity response, coagulant usage, and the inferred sensor reliability.
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

# Ensure the project root is importable when executing directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from run_simulation import run_and_log_simulation  # noqa: E402


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ADAPTIVE_LOG = ARTIFACT_DIR / "adaptive_pid_log.csv"
MPC_LOG = ARTIFACT_DIR / "mpc_controller_log.csv"
COMPARISON_FIG = ARTIFACT_DIR / "mpc_vs_adaptive.png"


def demo_disturbance(*, step_index: int, timestamp, quality, inputs) -> Dict[str, float]:
    """Moderate waves plus occasional pulses to stress the dosing loop."""

    wave = 0.4 * math.sin(step_index / 20.0)
    pulse = 0.0
    if 80 <= step_index < 120:
        pulse += 1.2
    if 150 <= step_index < 190:
        pulse -= 0.8
    return {"turbidity": wave + pulse}


def drifting_sensor_bias(
    *,
    step_index: int,
    timestamp,
    true_quality,
    diagnostics,
) -> Dict[str, float]:
    """
    Inject a slowly growing positive bias in the turbidity measurement after 100 steps.

    The bias plateaus at +2.0 NTU, simulating a fouled or mis-calibrated sensor.
    """

    if step_index < 100:
        return {}
    drift = min(2.0, 0.015 * (step_index - 100))
    return {"turbidity": drift, "sensor_bias": drift}


@dataclass
class SeriesData:
    timestamps: List[datetime]
    turbidity: List[float]
    coagulant: List[float]
    reliability: List[float]

    @classmethod
    def from_csv(cls, path: Path) -> "SeriesData":
        timestamps: List[datetime] = []
        turbidity: List[float] = []
        coagulant: List[float] = []
        reliability: List[float] = []

        with path.open("r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                timestamps.append(datetime.fromisoformat(row["timestamp"]))
                turbidity.append(float(row["turbidity"]))
                coagulant.append(float(row["coagulant_dose"]))
                reliability.append(float(row.get("turbidity_reliability", 1.0)))

        return cls(timestamps, turbidity, coagulant, reliability)

    def summary(self) -> Dict[str, float]:
        steps = max(len(self.turbidity), 1)
        return {
            "avg_turbidity": sum(self.turbidity) / steps,
            "final_turbidity": self.turbidity[-1],
            "total_coagulant": sum(self.coagulant),
            "avg_reliability": sum(self.reliability) / len(self.reliability)
            if self.reliability
            else 1.0,
        }


def ensure_artifacts_dir() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def run_comparison(steps: int = 240) -> Tuple[Path, Path]:
    ensure_artifacts_dir()

    adaptive_success = run_and_log_simulation(
        steps=steps,
        log_file=str(ADAPTIVE_LOG),
        turbidity_setpoint=5.0,
        do_setpoint=8.5,
        controller_type="adaptive-pid",
        disturbance_provider=demo_disturbance,
        sensor_provider=drifting_sensor_bias,
    )
    if not adaptive_success:
        raise RuntimeError("Adaptive PID simulation failed.")

    mpc_success = run_and_log_simulation(
        steps=steps,
        log_file=str(MPC_LOG),
        turbidity_setpoint=5.0,
        do_setpoint=8.5,
        controller_type="mpc",
        disturbance_provider=demo_disturbance,
        sensor_provider=drifting_sensor_bias,
    )
    if not mpc_success:
        raise RuntimeError("MPC simulation failed.")

    return ADAPTIVE_LOG, MPC_LOG


def plot_results(adaptive: SeriesData, mpc: SeriesData) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    fig.suptitle("Reliability-Aware MPC vs Adaptive PID", fontsize=16, fontweight="bold")

    axes[0].plot(adaptive.timestamps, adaptive.turbidity, label="Adaptive PID", color="tab:orange")
    axes[0].plot(mpc.timestamps, mpc.turbidity, label="MPC", color="tab:blue")
    axes[0].axhline(5.0, color="tab:green", linestyle=":", label="Turbidity Setpoint")
    axes[0].set_ylabel("Turbidity (NTU)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(adaptive.timestamps, adaptive.coagulant, label="Adaptive PID", color="tab:orange")
    axes[1].plot(mpc.timestamps, mpc.coagulant, label="MPC", color="tab:blue")
    axes[1].set_ylabel("Coagulant Dose")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(
        adaptive.timestamps,
        adaptive.reliability,
        label="Adaptive PID",
        color="tab:orange",
        linestyle="--",
    )
    axes[2].plot(
        mpc.timestamps,
        mpc.reliability,
        label="MPC",
        color="tab:blue",
        linestyle="-",
    )
    axes[2].set_ylabel("Sensor Reliability")
    axes[2].set_xlabel("Time")
    axes[2].set_ylim(0.0, 1.05)
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(COMPARISON_FIG, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"比较图已生成: {COMPARISON_FIG}")


def print_summary(adaptive: SeriesData, mpc: SeriesData) -> None:
    adaptive_summary = adaptive.summary()
    mpc_summary = mpc.summary()

    print("===== 结果概览 =====")
    print("Adaptive PID:")
    for key, value in adaptive_summary.items():
        print(f"  {key}: {value:.3f}")

    print("MPC:")
    for key, value in mpc_summary.items():
        print(f"  {key}: {value:.3f}")

    turbidity_gap = adaptive_summary["final_turbidity"] - mpc_summary["final_turbidity"]
    coagulant_gap = adaptive_summary["total_coagulant"] - mpc_summary["total_coagulant"]

    print("\n关键观察：")
    if turbidity_gap > 0.2:
        print("  - MPC 将末端浊度降低得更彻底，更适合存在长期偏差的场景。")
    elif turbidity_gap < -0.2:
        print("  - 自适应 PID 在末端浊度上更有优势，可继续优化 MPC 模型参数。")
    else:
        print("  - 两种策略在末端浊度上接近，可通过能耗或药剂使用量进一步决策。")

    if coagulant_gap > 0.5:
        print("  - MPC 在传感器偏差阶段显著减少了药剂投加，体现了可信度加权的安全性。")
    elif coagulant_gap < -0.5:
        print("  - 自适应 PID 投加更少，可考虑调低 MPC 的控制力度。")
    else:
        print("  - 药剂使用量相近，可结合能耗和扰动响应来评估。")


def main() -> None:
    adaptive_log, mpc_log = run_comparison()

    adaptive_data = SeriesData.from_csv(adaptive_log)
    mpc_data = SeriesData.from_csv(mpc_log)

    plot_results(adaptive_data, mpc_data)
    print_summary(adaptive_data, mpc_data)


if __name__ == "__main__":
    main()

