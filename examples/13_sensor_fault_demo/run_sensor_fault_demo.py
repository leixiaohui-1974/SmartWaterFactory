"""
Sensor fault handling demo.

This script runs the precision PID controller while simulating a temporary
sensor bias fault.  The PlantSimulator detects the fault when the measured
value deviates beyond configured thresholds.  The resulting CSV log captures
the fault flags, which are summarised after the run.  A visual report is also
generated using the existing visualize_log module.
"""

from __future__ import annotations

import csv
import math
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from run_simulation import run_and_log_simulation  # noqa: E402
from visualize_log import visualize_simulation_log  # noqa: E402

ARTIFACT_DIR = PROJECT_ROOT / "examples" / "13_sensor_fault_demo" / "artifacts"
LOG_PATH = ARTIFACT_DIR / "sensor_fault_demo.csv"
PLOT_PATH = ARTIFACT_DIR / "sensor_fault_demo.png"



def sensor_fault_model(
    *,
    step_index: int,
    timestamp: datetime,
    true_quality,
    diagnostics: Dict[str, float],
) -> Dict[str, float]:
    """
    Returns measurement adjustments to emulate sensor noise/faults.

    - Adds small Gaussian noise by default.
    - Injects a bias fault between steps 80-120 to trigger detection.
    """

    noise = random.gauss(0.0, 0.1)
    response: Dict[str, float] = {
        "turbidity": noise,
        "dissolved_oxygen": random.gauss(0.0, 0.05),
    }

    if 80 <= step_index < 120:
        # Large bias to simulate sensor drift/failure
        response["turbidity"] += 6.0
        response["sensor_fault_stage"] = 1

    return response


def redundant_sensor_model(
    *,
    step_index: int,
    timestamp: datetime,
    true_quality,
    diagnostics: Dict[str, float],
) -> Dict[str, float]:
    """
    Secondary turbidity sensor model used for redundancy.

    The redundant probe tracks the true state with mild noise and a slow drift,
    remaining unaffected by the injected primary bias so the fusion layer can
    recover accurate measurements.
    """

    drift = 0.12 * math.sin(step_index / 90.0)
    response: Dict[str, float] = {
        "turbidity": drift + random.gauss(0.0, 0.08),
        "dissolved_oxygen": random.gauss(0.0, 0.03),
    }
    if diagnostics.get("sensor_fault_detected", 0.0) >= 0.5:
        response["redundant_sensor_support"] = 1.0
    return response


def demo_disturbance(
    *,
    step_index: int,
    timestamp: datetime,
    quality,
    inputs,
) -> Dict[str, float]:
    """Background turbidity disturbance for the sensor fault demo."""

    wave = 0.22 * math.sin(step_index / 22.0)
    pulse = 0.0
    if 60 <= step_index < 100:
        pulse = 0.4
    if 140 <= step_index < 170:
        pulse -= 0.3
    return {"turbidity": wave + pulse}

def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    success = run_and_log_simulation(
        steps=200,
        log_file=str(LOG_PATH),
        turbidity_setpoint=5.0,
        do_setpoint=8.5,
        controller_type="precision-pid",
        sensor_provider=sensor_fault_model,
        redundant_sensor_provider=redundant_sensor_model,
        disturbance_provider=demo_disturbance,
    )

    if not success:
        raise RuntimeError("Simulation failed; see console output for details.")

    fault_count = 0
    max_turbidity_error = 0.0
    max_do_error = 0.0
    monitor_trip_count = 0
    redundant_usage = 0
    turbidity_reliability_sum = 0.0
    do_reliability_sum = 0.0
    sample_count = 0

    with LOG_PATH.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if float(row.get("sensor_fault_detected", 0.0)) >= 0.5:
                fault_count += 1
            if (
                max(
                    float(row.get("turbidity_monitor_fault_trip", 0.0)),
                    float(row.get("do_monitor_fault_trip", 0.0)),
                )
                >= 0.5
            ):
                monitor_trip_count += 1
            if float(row.get("redundant_sensor_active", 0.0)) >= 0.5:
                redundant_usage += 1
            max_turbidity_error = max(
                max_turbidity_error,
                abs(float(row.get("sensor_turbidity_error", 0.0))),
            )
            max_do_error = max(
                max_do_error,
                abs(float(row.get("sensor_do_error", 0.0))),
            )
            turbidity_reliability_sum += float(row.get("turbidity_reliability", 0.0))
            do_reliability_sum += float(row.get("dissolved_oxygen_reliability", 0.0))
            sample_count += 1

    avg_turbidity_reliability = (
        turbidity_reliability_sum / sample_count if sample_count else 0.0
    )
    avg_do_reliability = do_reliability_sum / sample_count if sample_count else 0.0

    print("===== Sensor Fault Demo Summary =====")
    print(f"Log file: {LOG_PATH}")
    print(f"Detected fault samples (combined logic): {fault_count}")
    print(f"Monitor cumulative trips: {monitor_trip_count}")
    print(f"Max turbidity measurement error: {max_turbidity_error:.2f} NTU")
    print(f"Max dissolved oxygen measurement error: {max_do_error:.2f} mg/L")
    print(f"Redundant sensor utilised for {redundant_usage} samples")
    print(f"Average turbidity reliability: {avg_turbidity_reliability:.2f}")
    print(f"Average DO reliability: {avg_do_reliability:.2f}")

    visualize_simulation_log(
        log_file=str(LOG_PATH),
        output_image=str(PLOT_PATH),
    )


if __name__ == "__main__":
    random.seed(42)
    main()
