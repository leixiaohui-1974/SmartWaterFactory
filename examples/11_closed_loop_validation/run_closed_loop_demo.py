"""
Closed-loop validation demo for the Smart Water Factory project.

This example runs a short PID-controlled simulation and writes the resulting
trajectory to ``data/closed_loop_validation.csv`` so it can be visualised with
``visualize_log.py``.  The run finishes with an assert style check to make sure
the turbidity and dissolved oxygen approach their respective setpoints within
reasonable tolerances.
"""

from __future__ import annotations

import csv
from datetime import datetime
import math
from pathlib import Path
from typing import Optional

from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from config.settings import PID_GAINS


def _create_pid_controllers(
    turbidity_setpoint: float,
    do_setpoint: float,
) -> tuple[PIDController, PIDController]:
    """Configure PID controllers for coagulant dosing and aeration."""
    dosing_gains = PID_GAINS["dosing_controller"]
    aeration_gains = PID_GAINS["aeration_controller"]

    dosing_controller = PIDController(
        Kp=dosing_gains["Kp"],
        Ki=dosing_gains["Ki"],
        Kd=dosing_gains["Kd"],
        setpoint=turbidity_setpoint,
        reverse_acting=True,
    )
    dosing_controller.set_output_limits(0, 10)
    dosing_controller.set_integral_limits(-5, 5)

    aeration_controller = PIDController(
        Kp=aeration_gains["Kp"],
        Ki=aeration_gains["Ki"],
        Kd=aeration_gains["Kd"],
        setpoint=do_setpoint,
    )
    aeration_controller.set_output_limits(0, 20)
    aeration_controller.set_integral_limits(-15, 15)

    return dosing_controller, aeration_controller


def _turbidity_disturbance(step_index: int) -> float:
    """
    Synthetic disturbance profile representing influent fluctuations.

    The profile combines a slow sine wave (seasonal drift) and two pulses
    (e.g., short-lived spikes in turbidity).  Values are expressed in NTU.
    """
    slow_wave = 0.3 * math.sin(step_index / 20.0)
    pulse = 0.0
    if 40 <= step_index < 55:
        pulse = 2.0
    elif 110 <= step_index < 125:
        pulse = 1.0
    return slow_wave + pulse


def run_closed_loop_demo(
    steps: int = 200,
    turbidity_setpoint: float = 5.0,
    do_setpoint: float = 8.5,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Execute a closed-loop simulation run and persist the results to CSV.

    Args:
        steps: Number of minutes to simulate.
        turbidity_setpoint: Target turbidity in NTU.
        do_setpoint: Target dissolved oxygen in mg/L.
        output_path: Optional override for the CSV destination file.

    Returns:
        Path to the CSV log file that was generated.

    Raises:
        AssertionError: If the final values do not fall within the expected
            tolerances.  This provides a quick smoke-test style validation.
    """
    output_path = output_path or Path("data/closed_loop_validation.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    initial_quality = WaterQuality(
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        ph=7.0,
        turbidity=25.0,
        dissolved_oxygen=4.0,
    )
    simulator = PlantSimulator(initial_quality)
    dosing_controller, aeration_controller = _create_pid_controllers(
        turbidity_setpoint=turbidity_setpoint,
        do_setpoint=do_setpoint,
    )

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "timestamp",
                "turbidity",
                "dissolved_oxygen",
                "turbidity_setpoint",
                "do_setpoint",
                "coagulant_dose",
                "aeration_rate",
                "turbidity_disturbance",
            ]
        )

        for step_index in range(steps):
            current_quality = simulator.current_quality
            coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
            aeration_rate = aeration_controller.calculate(
                current_quality.dissolved_oxygen
            )
            new_quality = simulator.step(
                coagulant_dose=coagulant_dose,
                aeration_rate=aeration_rate,
            )

            disturbance = _turbidity_disturbance(step_index)
            if disturbance != 0.0:
                disturbed_quality = WaterQuality(
                    timestamp=new_quality.timestamp,
                    ph=new_quality.ph,
                    turbidity=max(0.0, new_quality.turbidity + disturbance),
                    dissolved_oxygen=new_quality.dissolved_oxygen,
                )
                simulator.current_quality = disturbed_quality
            else:
                disturbed_quality = new_quality

            writer.writerow(
                [
                    disturbed_quality.timestamp.isoformat(),
                    disturbed_quality.turbidity,
                    disturbed_quality.dissolved_oxygen,
                    turbidity_setpoint,
                    do_setpoint,
                    coagulant_dose,
                    aeration_rate,
                    disturbance,
                ]
            )

    final_quality = simulator.current_quality
    turbidity_error = abs(final_quality.turbidity - turbidity_setpoint)
    do_error = abs(final_quality.dissolved_oxygen - do_setpoint)

    if turbidity_error > 2.0:
        raise AssertionError(
            f"Turbidity out of tolerance: {final_quality.turbidity:.2f} "
            f"(error={turbidity_error:.2f}, limit=2.0)"
        )
    if do_error > 0.3:
        raise AssertionError(
            f"Dissolved oxygen out of tolerance: {final_quality.dissolved_oxygen:.2f} "
            f"(error={do_error:.2f}, limit=0.3)"
        )

    print(
        f"收敛成功：Turbidity={final_quality.turbidity:.2f} NTU, "
        f"DO={final_quality.dissolved_oxygen:.2f} mg/L"
    )
    print(
        f"残余误差：|ΔTurbidity|={turbidity_error:.2f} NTU, "
        f"|ΔDO|={do_error:.2f} mg/L"
    )
    print(f"日志已写入: {output_path}")
    return output_path


if __name__ == "__main__":
    run_closed_loop_demo()
