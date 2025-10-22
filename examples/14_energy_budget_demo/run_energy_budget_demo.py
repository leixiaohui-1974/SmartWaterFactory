"""
Energy budget coordination demo.

This script temporarily lowers the global energy budget and runs the precision
PID controller to illustrate the scaling behaviour implemented by the
EnergyCoordinator.  It produces a CSV log and visualization containing the
`energy_scaling_factor` series.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import ENERGY_COORDINATION  # noqa: E402
from run_simulation import run_and_log_simulation  # noqa: E402
from visualize_log import visualize_simulation_log  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"
LOG_PATH = DATA_DIR / "energy_budget_demo.csv"
FIG_PATH = DATA_DIR / "energy_budget_demo.png"


def run_demo(steps: int = 200, low_budget: float = 15.0) -> Tuple[float, float]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    original_enabled = ENERGY_COORDINATION.get("enabled", False)
    original_budget = ENERGY_COORDINATION.get("budget_per_step", 0.0)

    ENERGY_COORDINATION["enabled"] = True
    ENERGY_COORDINATION["budget_per_step"] = low_budget

    try:
        success = run_and_log_simulation(
            steps=steps,
            log_file=str(LOG_PATH),
            turbidity_setpoint=5.0,
            do_setpoint=8.5,
            controller_type="precision-pid",
        )

        if not success:
            raise RuntimeError("Simulation failed; inspect console output for details.")
    finally:
        ENERGY_COORDINATION["enabled"] = original_enabled
        ENERGY_COORDINATION["budget_per_step"] = original_budget

    with LOG_PATH.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        scaling = [float(row["energy_scaling_factor"]) for row in reader]

    min_scale = min(scaling)
    avg_scale = sum(scaling) / len(scaling)

    visualize_simulation_log(
        log_file=str(LOG_PATH),
        output_image=str(FIG_PATH),
    )

    return min_scale, avg_scale


def main() -> None:
    min_scale, avg_scale = run_demo()
    print("===== Energy Budget Demo =====")
    print(f"Log file: {LOG_PATH}")
    print(f"Figure: {FIG_PATH}")
    print(f"Minimum scaling factor: {min_scale:.3f}")
    print(f"Average scaling factor: {avg_scale:.3f}")
    if min_scale < 0.99:
        print("Budget constraint active: actuators were scaled to respect the limit.")
    else:
        print("Budget constraint inactive: outputs remained at requested levels.")


if __name__ == "__main__":
    main()
