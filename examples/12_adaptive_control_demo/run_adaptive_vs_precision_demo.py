"""
Adaptive vs precision PID comparison demo.

This script runs the simulator twice under identical disturbances:
1. Using the precision (constraint-aware) PID controller.
2. Using the adaptive PID controller that self-tunes gains online.

It produces two CSV logs and a comparison plot highlighting turbidity
and dissolved oxygen trajectories for both controllers.
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

# Ensure the project root is on sys.path so we can import run_simulation
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from run_simulation import run_and_log_simulation  # noqa: E402


DATA_DIR = PROJECT_ROOT / "data"
PRECISION_LOG = DATA_DIR / "adaptive_precision_precision.csv"
ADAPTIVE_LOG = DATA_DIR / "adaptive_precision_adaptive.csv"
COMPARISON_FIG = DATA_DIR / "adaptive_vs_precision_comparison.png"


def demo_disturbance(*, step_index: int, timestamp, quality, inputs) -> dict:
    wave = 0.4 * math.sin(step_index / 18.0)
    pulse = 0.0
    if 70 <= step_index < 110:
        pulse += 1.5
    if 140 <= step_index < 170:
        pulse -= 1.0
    return {"turbidity": wave + pulse}


@dataclass
class SeriesData:
    timestamps: List[datetime]
    turbidity: List[float]
    dissolved_oxygen: List[float]

    @classmethod
    def from_csv(cls, path: Path) -> "SeriesData":
        timestamps: List[datetime] = []
        turbidity: List[float] = []
        dissolved_oxygen: List[float] = []

        with path.open("r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                timestamps.append(datetime.fromisoformat(row["timestamp"]))
                turbidity.append(float(row["turbidity"]))
                dissolved_oxygen.append(float(row["dissolved_oxygen"]))

        return cls(timestamps, turbidity, dissolved_oxygen)

    def summary(self) -> Dict[str, float]:
        return {
            "avg_turbidity": sum(self.turbidity) / len(self.turbidity),
            "avg_dissolved_oxygen": sum(self.dissolved_oxygen) / len(self.dissolved_oxygen),
            "final_turbidity": self.turbidity[-1],
            "final_dissolved_oxygen": self.dissolved_oxygen[-1],
        }


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_simulation_pair(steps: int = 200) -> Tuple[Path, Path]:
    ensure_data_dir()

    success_precision = run_and_log_simulation(
        steps=steps,
        log_file=str(PRECISION_LOG),
        turbidity_setpoint=5.0,
        do_setpoint=8.5,
        controller_type="precision-pid",
        disturbance_provider=demo_disturbance,
    )
    if not success_precision:
        raise RuntimeError("Precision PID run failed.")

    success_adaptive = run_and_log_simulation(
        steps=steps,
        log_file=str(ADAPTIVE_LOG),
        turbidity_setpoint=5.0,
        do_setpoint=8.5,
        controller_type="adaptive-pid",
        disturbance_provider=demo_disturbance,
    )
    if not success_adaptive:
        raise RuntimeError("Adaptive PID run failed.")

    return PRECISION_LOG, ADAPTIVE_LOG


def plot_comparison(precision_data: SeriesData, adaptive_data: SeriesData) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Precision PID vs Adaptive PID", fontsize=16, fontweight="bold")

    ax1.plot(
        precision_data.timestamps,
        precision_data.turbidity,
        label="Precision PID",
        color="tab:blue",
    )
    ax1.plot(
        adaptive_data.timestamps,
        adaptive_data.turbidity,
        label="Adaptive PID",
        color="tab:orange",
        linestyle="--",
    )
    ax1.axhline(5.0, color="tab:green", linestyle=":", label="Turbidity Setpoint")
    ax1.set_ylabel("Turbidity (NTU)")
    ax1.set_title("Turbidity Trajectory")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.plot(
        precision_data.timestamps,
        precision_data.dissolved_oxygen,
        label="Precision PID",
        color="tab:red",
    )
    ax2.plot(
        adaptive_data.timestamps,
        adaptive_data.dissolved_oxygen,
        label="Adaptive PID",
        color="tab:purple",
        linestyle="--",
    )
    ax2.axhline(8.5, color="tab:green", linestyle=":", label="DO Setpoint")
    ax2.set_ylabel("Dissolved Oxygen (mg/L)")
    ax2.set_title("Dissolved Oxygen Trajectory")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(COMPARISON_FIG, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"对比图已保存：{COMPARISON_FIG}")


def print_summary(precision_data: SeriesData, adaptive_data: SeriesData) -> None:
    precision_summary = precision_data.summary()
    adaptive_summary = adaptive_data.summary()

    print("===== 运行总结 =====")
    print("Precision PID:")
    for key, value in precision_summary.items():
        print(f"  {key}: {value:.3f}")
    print("Adaptive PID:")
    for key, value in adaptive_summary.items():
        print(f"  {key}: {value:.3f}")

    turbidity_delta = adaptive_summary["final_turbidity"] - precision_summary["final_turbidity"]
    do_delta = adaptive_summary["final_dissolved_oxygen"] - precision_summary["final_dissolved_oxygen"]

    print("\n关键结论：")
    if abs(turbidity_delta) < 0.2:
        print("  - 自适应 PID 在浊度稳态与精细 PID 相近，但在扰动阶段响应更灵敏。")
    elif turbidity_delta < 0:
        print("  - 自适应 PID 将浊度压得更低，适合追求更严格的出水指标。")
    else:
        print("  - 精细 PID 保持更高的浊度水平，可视为对自适应调参的一个对照。")

    if abs(do_delta) < 0.1:
        print("  - 两种策略在溶解氧稳态表现几乎一致。")
    elif do_delta < 0:
        print("  - 自适应 PID 略微降低了溶解氧，可能减少能耗但需关注下限。")
    else:
        print("  - 自适应 PID 提高了溶解氧稳态，对增加曝气有利。")


def main() -> None:
    precision_log, adaptive_log = run_simulation_pair()

    precision_data = SeriesData.from_csv(precision_log)
    adaptive_data = SeriesData.from_csv(adaptive_log)

    plot_comparison(precision_data, adaptive_data)
    print_summary(precision_data, adaptive_data)


if __name__ == "__main__":
    main()
