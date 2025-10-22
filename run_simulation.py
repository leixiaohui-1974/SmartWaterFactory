import argparse
import csv
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from config.settings import ENERGY_COORDINATION, FAULT_TOLERANCE, PID_GAINS, SIMULATION_DEFAULTS
from config.validator import validate_config
from water_plant_controller.control.on_off_controller import OnOffController
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.precision_controller import (
    AdaptivePIDController,
    AdaptivePIDProfile,
    ConstraintProfile,
    PrecisionPIDController,
)
from water_plant_controller.control.mpc_controller import (
    LinearisedProcessModel,
    MPCFaultTolerantController,
    ReliabilityAwareConstraints,
)
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.energy_manager import EnergyCoordinator
from utils.sensor_monitor import SensorMonitor
if TYPE_CHECKING:
    from water_plant_controller.simulation.plant_simulator import DisturbanceProvider, SensorModel
from water_plant_controller.models.water_quality import WaterQuality


def run_and_log_simulation(
    steps: int,
    log_file: str,
    turbidity_setpoint: float,
    do_setpoint: float,
    controller_type: str,
    sensor_provider: Optional["SensorModel"] = None,
    redundant_sensor_provider: Optional["SensorModel"] = None,
    disturbance_provider: Optional["DisturbanceProvider"] = None,
) -> bool:
    """
    Run the plant simulator and write each step to a CSV log file.

    Args:
        steps: Number of simulation iterations to execute.
        log_file: Destination CSV filepath.
        turbidity_setpoint: Desired turbidity value (NTU).
        do_setpoint: Desired dissolved oxygen value (mg/L).
        controller_type: Controller implementation to use.
        sensor_provider: Optional callable that injects noise/faults for the primary sensor.
        redundant_sensor_provider: Optional callable used to model a redundant sensor for fault tolerance.
        disturbance_provider: Optional callable for process disturbances (e.g., turbidity spikes).

    Returns:
        True when the simulation completes without error, False otherwise.
    """

    try:
        _validate_simulation_inputs(
            steps, log_file, turbidity_setpoint, do_setpoint, controller_type
        )
    except ValueError as exc:
        print(f"Invalid input parameters: {exc}")
        return False

    try:
        validate_config(SIMULATION_DEFAULTS, PID_GAINS)
    except (ValueError, TypeError) as exc:
        print(f"Configuration validation failed: {exc}")
        return False

    try:
        initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=25.0,
            dissolved_oxygen=4.0,
        )
        simulator = PlantSimulator(
            initial_quality,
            sensor_provider=sensor_provider,
            redundant_sensor_provider=redundant_sensor_provider,
            disturbance_provider=disturbance_provider,
        )
        turbidity_monitor = SensorMonitor()
        turbidity_monitor.filter.estimate = simulator.current_quality.turbidity
        do_monitor = SensorMonitor(
            process_var=0.05,
            measurement_var=1.2,
            min_threshold=0.3,
            cross_tolerance=0.8,
        )
        do_monitor.filter.estimate = simulator.current_quality.dissolved_oxygen
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Failed to initialise simulator: {exc}")
        return False

    try:
        controllers = _create_controllers(
            controller_type, turbidity_setpoint, do_setpoint
        )
    except Exception as exc:
        print(f"Failed to initialise controllers: {exc}")
        return False

    try:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        with open(log_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "timestamp",
                "turbidity",
                "dissolved_oxygen",
                "turbidity_setpoint",
                "do_setpoint",
                "coagulant_dose",
                "aeration_rate",
                "turbidity_disturbance",
                "coagulant_saturated",
                "aeration_saturated",
                "coagulant_cost",
                "aeration_cost",
                "sensor_fault_detected",
                "sensor_turbidity_error",
                "sensor_do_error",
                "filtered_turbidity",
                "sensor_bias_estimate",
                "sensor_bias_threshold",
                "sensor_fault_likelihood",
                "turbidity_reliability",
                "turbidity_soft_measurement",
                "turbidity_measurement_used",
                "primary_sensor_fault",
                "secondary_sensor_fault",
                "redundant_sensor_active",
                "energy_scaling_factor",
                "energy_budget",
                "coagulant_energy_scale",
                "aeration_energy_scale",
                "fault_fallback_active",
                "active_sensor",
                "turbidity_raw_measurement",
                "fused_turbidity",
                "turbidity_monitor_fault_score",
                "turbidity_monitor_fault_trip",
                "primary_sensor_turbidity",
                "secondary_sensor_turbidity",
                "redundant_reliability",
                "dual_sensor_delta",
                "raw_dissolved_oxygen_measurement",
                "fused_dissolved_oxygen",
                "do_monitor_fault_score",
                "do_monitor_fault_trip",
                "dissolved_oxygen_reliability",
                "dissolved_oxygen_soft_measurement",
                "dissolved_oxygen_measurement_used",
                "do_redundant_reliability",
                "do_dual_sensor_delta",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            print(f"Running simulation for {steps} steps; logging to {log_file}")
            energy_coordinator = None
            if ENERGY_COORDINATION.get("enabled"):
                energy_coordinator = EnergyCoordinator(
                    budget_per_step=ENERGY_COORDINATION.get("budget_per_step", 0.0),
                    weights=ENERGY_COORDINATION.get("weights", {}),
                )
            fault_enabled = FAULT_TOLERANCE.get("enabled", False)
            fault_threshold = int(FAULT_TOLERANCE.get("consecutive_fault_threshold", 3))
            fault_state = {
                "count": 0,
                "active": False,
                "coagulant_output": 0.0,
                "aeration_output": 0.0,
                "coagulant_diag": {"saturated": 0, "instantaneous_cost": 0.0},
                "aeration_diag": {"saturated": 0, "instantaneous_cost": 0.0},
            }
            measurement_state = {
                "turbidity_soft_measurement": simulator.current_quality.turbidity,
                "turbidity_reliability": 1.0,
                "turbidity_bias_estimate": 0.0,
                "do_soft_measurement": simulator.current_quality.dissolved_oxygen,
                "do_reliability": 1.0,
                "do_bias_estimate": 0.0,
            }

            for step_index in range(steps):
                current_quality = simulator.current_quality
                turbidity_measurement = measurement_state.get(
                    "turbidity_soft_measurement", current_quality.turbidity
                )
                turbidity_reliability = measurement_state.get("turbidity_reliability", 1.0)
                turbidity_bias_estimate = measurement_state.get("turbidity_bias_estimate", 0.0)
                do_measurement = measurement_state.get(
                    "do_soft_measurement", current_quality.dissolved_oxygen
                )
                do_reliability = measurement_state.get("do_reliability", 1.0)
                do_bias_estimate = measurement_state.get("do_bias_estimate", 0.0)

                disturbances_source = simulator.last_diagnostics or {}
                disturbances = disturbances_source.copy() if isinstance(disturbances_source, dict) else {}
                disturbances.setdefault("turbidity_measurement_raw", current_quality.turbidity)
                disturbances["turbidity_soft_measurement"] = turbidity_measurement
                disturbances["turbidity_measurement_reliability"] = turbidity_reliability
                disturbances["turbidity_measurement_bias"] = turbidity_bias_estimate
                disturbances.setdefault(
                    "dissolved_oxygen_measurement_raw", current_quality.dissolved_oxygen
                )
                disturbances["dissolved_oxygen_soft_measurement"] = do_measurement
                disturbances["dissolved_oxygen_measurement_reliability"] = do_reliability
                disturbances["dissolved_oxygen_measurement_bias"] = do_bias_estimate

                fault_fallback_active = 0
                if fault_state["active"]:
                    coagulant_dose = fault_state["coagulant_output"]
                    aeration_rate = fault_state["aeration_output"]
                    coagulant_diag = fault_state["coagulant_diag"].copy()
                    aeration_diag = fault_state["aeration_diag"].copy()
                    fault_fallback_active = 1
                    active_sensor_name = fault_state.get("active_sensor", "primary")
                else:
                    dosing_controller = controllers["dosing"]
                    if hasattr(dosing_controller, "update_sensor_health"):
                        dosing_controller.update_sensor_health(
                            reliability=turbidity_reliability,
                            bias_estimate=turbidity_bias_estimate,
                        )
                    try:
                        coagulant_dose, coagulant_diag = _compute_controller_output(
                            dosing_controller,
                            measurement=turbidity_measurement,
                            disturbances=disturbances,
                        )
                        aeration_rate, aeration_diag = _compute_controller_output(
                            controllers["aeration"],
                            measurement=do_measurement,
                            disturbances=disturbances,
                        )
                    except Exception as exc:
                        print(f"Controller error at step {step_index + 1}: {exc}")
                        return False

                try:
                    new_quality = simulator.step(
                        coagulant_dose=coagulant_dose,
                        aeration_rate=aeration_rate,
                    )
                except Exception as exc:
                    print(f"Simulator error at step {step_index + 1}: {exc}")
                    return False

                energy_scale_map = {"coagulant": 1.0, "aeration": 1.0}
                if (
                    energy_coordinator
                    and not fault_state["active"]
                    and all(hasattr(ctrl, "apply_output_override") for ctrl in controllers.values())
                ):
                    energy_scale_map = energy_coordinator.coordinate(
                        [
                            ("coagulant", controllers["dosing"], coagulant_dose, coagulant_diag),
                            ("aeration", controllers["aeration"], aeration_rate, aeration_diag),
                        ]
                    )
                    coagulant_dose = controllers["dosing"].last_diagnostics.get(
                        "coordinated_output", coagulant_dose
                    )
                    aeration_rate = controllers["aeration"].last_diagnostics.get(
                        "coordinated_output", aeration_rate
                    )

                sensor_diag = simulator.last_diagnostics or {}

                raw_turbidity = sensor_diag.get("measured_turbidity", new_quality.turbidity)
                primary_raw = sensor_diag.get("primary_sensor_turbidity", raw_turbidity)
                secondary_raw = sensor_diag.get("secondary_sensor_turbidity")
                turbidity_metrics = turbidity_monitor.update(
                    primary_raw,
                    redundant_measurement=secondary_raw,
                )
                fused_turbidity = turbidity_metrics.get("fused_measurement", raw_turbidity)
                reliability_next = turbidity_metrics.get(
                    "sensor_reliability", turbidity_reliability
                )
                soft_measurement_next = turbidity_metrics.get(
                    "soft_measurement", fused_turbidity
                )
                measurement_state["turbidity_soft_measurement"] = soft_measurement_next
                measurement_state["turbidity_reliability"] = reliability_next
                measurement_state["turbidity_bias_estimate"] = turbidity_metrics.get(
                    "sensor_bias_estimate", turbidity_bias_estimate
                )
                sensor_diag["filtered_turbidity"] = turbidity_metrics.get(
                    "filtered_turbidity",
                    sensor_diag.get("filtered_turbidity", fused_turbidity),
                )
                sensor_diag["sensor_bias_estimate"] = turbidity_metrics.get(
                    "sensor_bias_estimate",
                    sensor_diag.get("sensor_bias_estimate", turbidity_bias_estimate),
                )
                sensor_diag["sensor_bias_threshold"] = turbidity_metrics.get(
                    "sensor_bias_threshold",
                    sensor_diag.get("sensor_bias_threshold", 0.0),
                )
                sensor_diag["sensor_fault_likelihood"] = turbidity_metrics.get(
                    "sensor_fault_likelihood",
                    sensor_diag.get("sensor_fault_likelihood", 0.0),
                )
                sensor_diag["turbidity_reliability"] = reliability_next
                sensor_diag["turbidity_soft_measurement"] = soft_measurement_next
                sensor_diag["turbidity_measurement_used"] = turbidity_measurement
                sensor_diag["fused_turbidity"] = fused_turbidity
                sensor_diag["raw_turbidity_measurement"] = raw_turbidity
                sensor_diag["turbidity_monitor_fault_score"] = turbidity_metrics.get("fault_score", 0.0)
                sensor_diag["turbidity_monitor_fault_trip"] = turbidity_metrics.get("fault_trip", 0.0)
                sensor_diag["redundant_reliability"] = turbidity_metrics.get(
                    "redundant_reliability", 0.0
                )
                sensor_diag["dual_sensor_delta"] = turbidity_metrics.get("dual_sensor_delta", 0.0)

                raw_do = sensor_diag.get(
                    "measured_dissolved_oxygen", new_quality.dissolved_oxygen
                )
                primary_do_raw = sensor_diag.get(
                    "primary_sensor_dissolved_oxygen", raw_do
                )
                secondary_do_raw = sensor_diag.get(
                    "secondary_sensor_dissolved_oxygen"
                )
                do_metrics = do_monitor.update(
                    primary_do_raw,
                    redundant_measurement=secondary_do_raw,
                )
                fused_do = do_metrics.get("fused_measurement", raw_do)
                do_reliability_next = do_metrics.get("sensor_reliability", do_reliability)
                do_soft_measurement_next = do_metrics.get(
                    "soft_measurement", fused_do
                )
                measurement_state["do_soft_measurement"] = do_soft_measurement_next
                measurement_state["do_reliability"] = do_reliability_next
                measurement_state["do_bias_estimate"] = do_metrics.get(
                    "sensor_bias_estimate", do_bias_estimate
                )
                sensor_diag["filtered_dissolved_oxygen"] = do_metrics.get(
                    "filtered_turbidity",
                    sensor_diag.get("filtered_dissolved_oxygen", fused_do),
                )
                sensor_diag["do_bias_estimate"] = do_metrics.get(
                    "sensor_bias_estimate",
                    sensor_diag.get("do_bias_estimate", do_bias_estimate),
                )
                sensor_diag["do_bias_threshold"] = do_metrics.get(
                    "sensor_bias_threshold",
                    sensor_diag.get("do_bias_threshold", 0.0),
                )
                sensor_diag["do_fault_likelihood"] = do_metrics.get(
                    "sensor_fault_likelihood",
                    sensor_diag.get("do_fault_likelihood", 0.0),
                )
                sensor_diag["dissolved_oxygen_reliability"] = do_reliability_next
                sensor_diag["dissolved_oxygen_soft_measurement"] = do_soft_measurement_next
                sensor_diag["dissolved_oxygen_measurement_used"] = do_measurement
                sensor_diag["fused_dissolved_oxygen"] = fused_do
                sensor_diag["raw_dissolved_oxygen_measurement"] = raw_do
                sensor_diag["do_monitor_fault_score"] = do_metrics.get("fault_score", 0.0)
                sensor_diag["do_monitor_fault_trip"] = do_metrics.get("fault_trip", 0.0)
                sensor_diag["do_redundant_reliability"] = do_metrics.get(
                    "redundant_reliability", 0.0
                )
                sensor_diag["do_dual_sensor_delta"] = do_metrics.get("dual_sensor_delta", 0.0)

                true_quality_state = getattr(simulator, "true_quality", new_quality)
                true_turbidity = true_quality_state.turbidity
                true_do = true_quality_state.dissolved_oxygen
                sensor_diag["sensor_turbidity_error"] = abs(fused_turbidity - true_turbidity)
                sensor_diag["sensor_do_error"] = abs(fused_do - true_do)

                turbidity_disturbance = sensor_diag.get("turbidity_adjustment", 0.0)

                if fault_enabled:
                    monitor_trip = max(
                        sensor_diag.get("turbidity_monitor_fault_trip", 0.0),
                        sensor_diag.get("do_monitor_fault_trip", 0.0),
                    )
                    redundant_reliability = sensor_diag.get("redundant_reliability", 0.0)
                    do_redundant_reliability = sensor_diag.get("do_redundant_reliability", 1.0)
                    combined_redundant_reliability = min(redundant_reliability, do_redundant_reliability)
                    redundant_active = sensor_diag.get("redundant_sensor_active", 0.0)
                    fault_detected = sensor_diag.get("sensor_fault_detected", 0.0) >= 0.5
                    if (
                        not fault_detected
                        and monitor_trip >= 0.5
                        and combined_redundant_reliability < 0.5
                        and redundant_active < 0.5
                    ):
                        fault_detected = True
                    sensor_diag["sensor_fault_detected"] = float(fault_detected)
                    if fault_detected:
                        fault_state["count"] += 1
                    else:
                        fault_state["count"] = 0
                        fault_state["active"] = False

                    if fault_state["count"] >= fault_threshold:
                        fault_state["active"] = True
                        fault_state["coagulant_output"] = coagulant_dose
                        fault_state["aeration_output"] = aeration_rate
                        fault_state["coagulant_diag"] = coagulant_diag.copy()
                        fault_state["aeration_diag"] = aeration_diag.copy()
                        fault_state["active_sensor"] = "secondary"
                else:
                    fault_state["active"] = False
                    fault_state["count"] = 0
                    fault_state["active_sensor"] = "primary"

                active_sensor_name = fault_state.get("active_sensor", "primary")
                if (
                    not fault_state["active"]
                    and sensor_diag.get("redundant_sensor_active", 0.0) >= 0.5
                ):
                    active_sensor_name = "secondary"

                writer.writerow(
                    {
                        "timestamp": new_quality.timestamp.isoformat(),
                        "turbidity": soft_measurement_next,
                        "dissolved_oxygen": do_soft_measurement_next,
                        "turbidity_setpoint": turbidity_setpoint,
                        "do_setpoint": do_setpoint,
                        "coagulant_dose": coagulant_dose,
                        "aeration_rate": aeration_rate,
                        "turbidity_disturbance": turbidity_disturbance,
                        "coagulant_saturated": coagulant_diag.get("saturated", 0),
                        "aeration_saturated": aeration_diag.get("saturated", 0),
                        "coagulant_cost": coagulant_diag.get("instantaneous_cost", 0.0),
                        "aeration_cost": aeration_diag.get("instantaneous_cost", 0.0),
                        "sensor_fault_detected": sensor_diag.get("sensor_fault_detected", 0.0),
                        "sensor_turbidity_error": sensor_diag.get("sensor_turbidity_error", 0.0),
                        "sensor_do_error": sensor_diag.get("sensor_do_error", 0.0),
                        "filtered_turbidity": sensor_diag.get("filtered_turbidity", new_quality.turbidity),
                        "sensor_bias_estimate": sensor_diag.get("sensor_bias_estimate", 0.0),
                        "sensor_bias_threshold": sensor_diag.get("sensor_bias_threshold", 0.0),
                        "sensor_fault_likelihood": sensor_diag.get("sensor_fault_likelihood", 0.0),
                        "turbidity_reliability": sensor_diag.get(
                            "turbidity_reliability", turbidity_reliability
                        ),
                        "turbidity_soft_measurement": sensor_diag.get(
                            "turbidity_soft_measurement",
                            measurement_state.get(
                                "turbidity_soft_measurement", new_quality.turbidity
                            ),
                        ),
                        "turbidity_measurement_used": sensor_diag.get(
                            "turbidity_measurement_used", turbidity_measurement
                        ),
                        "dissolved_oxygen_reliability": sensor_diag.get(
                            "dissolved_oxygen_reliability", do_reliability
                        ),
                        "dissolved_oxygen_soft_measurement": sensor_diag.get(
                            "dissolved_oxygen_soft_measurement",
                            measurement_state.get(
                                "do_soft_measurement", new_quality.dissolved_oxygen
                            ),
                        ),
                        "dissolved_oxygen_measurement_used": sensor_diag.get(
                            "dissolved_oxygen_measurement_used", do_measurement
                        ),
                        "primary_sensor_fault": sensor_diag.get("primary_sensor_fault", 0.0),
                        "secondary_sensor_fault": sensor_diag.get("secondary_sensor_fault", 0.0),
                        "redundant_sensor_active": sensor_diag.get("redundant_sensor_active", 0.0),
                        "energy_scaling_factor": min(energy_scale_map.values())
                        if energy_scale_map
                        else 1.0,
                        "energy_budget": ENERGY_COORDINATION.get("budget_per_step", 0.0)
                        if energy_coordinator
                        else 0.0,
                        "coagulant_energy_scale": energy_scale_map.get("coagulant", 1.0),
                        "aeration_energy_scale": energy_scale_map.get("aeration", 1.0),
                        "fault_fallback_active": fault_fallback_active,
                        "active_sensor": active_sensor_name,
                        "turbidity_raw_measurement": sensor_diag.get(
                            "raw_turbidity_measurement", raw_turbidity
                        ),
                        "fused_turbidity": sensor_diag.get("fused_turbidity", fused_turbidity),
                        "turbidity_monitor_fault_score": sensor_diag.get(
                            "turbidity_monitor_fault_score", 0.0
                        ),
                        "turbidity_monitor_fault_trip": sensor_diag.get(
                            "turbidity_monitor_fault_trip", 0.0
                        ),
                        "primary_sensor_turbidity": sensor_diag.get(
                            "primary_sensor_turbidity", primary_raw
                        ),
                        "secondary_sensor_turbidity": sensor_diag.get(
                            "secondary_sensor_turbidity", secondary_raw if secondary_raw is not None else 0.0
                        ),
                        "redundant_reliability": sensor_diag.get("redundant_reliability", 0.0),
                        "dual_sensor_delta": sensor_diag.get("dual_sensor_delta", 0.0),
                        "raw_dissolved_oxygen_measurement": sensor_diag.get(
                            "raw_dissolved_oxygen_measurement", raw_do
                        ),
                        "fused_dissolved_oxygen": sensor_diag.get(
                            "fused_dissolved_oxygen", fused_do
                        ),
                        "do_monitor_fault_score": sensor_diag.get("do_monitor_fault_score", 0.0),
                        "do_monitor_fault_trip": sensor_diag.get("do_monitor_fault_trip", 0.0),
                        "do_redundant_reliability": sensor_diag.get("do_redundant_reliability", 0.0),
                        "do_dual_sensor_delta": sensor_diag.get("do_dual_sensor_delta", 0.0),
                    }
                )

                if (step_index + 1) % 50 == 0:
                    print(f"Completed {step_index + 1}/{steps} steps")

        print("Simulation finished successfully.")
        return True

    except PermissionError:
        print(f"Permission denied when writing '{log_file}'")
        return False
    except IOError as exc:
        print(f"Unable to write log file '{log_file}': {exc}")
        return False
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Unexpected error while writing the log: {exc}")
        return False


def _create_controllers(
    controller_type: str, turbidity_setpoint: float, do_setpoint: float
) -> Dict[str, object]:
    """
    Build the dosing and aeration controllers according to the requested type.
    """

    if controller_type == "pid":
        dosing_gains = PID_GAINS["dosing_controller"]
        aeration_gains = PID_GAINS["aeration_controller"]

        dosing_controller = PIDController(
            Kp=dosing_gains["Kp"],
            Ki=dosing_gains["Ki"],
            Kd=dosing_gains["Kd"],
            setpoint=turbidity_setpoint,
            reverse_acting=True,
        )
        dosing_controller.set_integral_limits(-5, 5)

        aeration_controller = PIDController(
            Kp=aeration_gains["Kp"],
            Ki=aeration_gains["Ki"],
            Kd=aeration_gains["Kd"],
            setpoint=do_setpoint,
        )
        aeration_controller.set_integral_limits(-15, 15)
    elif controller_type == "on-off":
        dosing_controller = OnOffController(setpoint=turbidity_setpoint, reverse_acting=True)
        dosing_controller.set_output_limits(0, 10)

        aeration_controller = OnOffController(setpoint=do_setpoint)
        aeration_controller.set_output_limits(0, 20)
    elif controller_type == "precision-pid":
        dosing_controller, aeration_controller = _create_precision_controllers(
            turbidity_setpoint,
            do_setpoint,
        )
    elif controller_type == "adaptive-pid":
        dosing_controller, aeration_controller = _create_adaptive_controllers(
            turbidity_setpoint,
            do_setpoint,
        )
    elif controller_type == "mpc":
        dosing_controller, aeration_controller = _create_mpc_controllers(
            turbidity_setpoint,
            do_setpoint,
        )
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")

    if controller_type == "pid":
        dosing_controller.set_output_limits(0, 10)
        aeration_controller.set_output_limits(0, 20)

    return {"dosing": dosing_controller, "aeration": aeration_controller}


def _create_precision_controllers(
    turbidity_setpoint: float,
    do_setpoint: float,
) -> tuple[PrecisionPIDController, PrecisionPIDController]:
    dosing_pid = PIDController(
        Kp=PID_GAINS["dosing_controller"]["Kp"],
        Ki=PID_GAINS["dosing_controller"]["Ki"],
        Kd=PID_GAINS["dosing_controller"]["Kd"],
        setpoint=turbidity_setpoint,
        reverse_acting=True,
    )
    dosing_pid.set_integral_limits(-5, 5)
    dosing_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=10.0,
        ramp_rate=1.0,
        unit_cost=0.45,
    )
    dosing_controller = PrecisionPIDController(
        pid=dosing_pid,
        constraint=dosing_constraint,
        feedforward_gain=-5.0,
        feedforward_key="turbidity_adjustment",
    )

    aeration_pid = PIDController(
        Kp=PID_GAINS["aeration_controller"]["Kp"],
        Ki=PID_GAINS["aeration_controller"]["Ki"],
        Kd=PID_GAINS["aeration_controller"]["Kd"],
        setpoint=do_setpoint,
    )
    aeration_pid.set_integral_limits(-15, 15)
    aeration_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=20.0,
        ramp_rate=2.0,
        unit_cost=0.18,
    )
    aeration_controller = PrecisionPIDController(
        pid=aeration_pid,
        constraint=aeration_constraint,
        feedforward_gain=1.5,
        feedforward_key="dissolved_oxygen_adjustment",
    )

    return dosing_controller, aeration_controller


def _create_adaptive_controllers(
    turbidity_setpoint: float,
    do_setpoint: float,
) -> tuple[AdaptivePIDController, AdaptivePIDController]:
    dosing_pid = PIDController(
        Kp=PID_GAINS["dosing_controller"]["Kp"],
        Ki=PID_GAINS["dosing_controller"]["Ki"],
        Kd=PID_GAINS["dosing_controller"]["Kd"],
        setpoint=turbidity_setpoint,
        reverse_acting=True,
    )
    dosing_pid.set_integral_limits(-5, 5)
    dosing_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=10.0,
        ramp_rate=1.0,
        unit_cost=0.45,
    )
    dosing_profile = AdaptivePIDProfile(
        kp_min=0.05,
        kp_max=1.0,
        ki_min=0.0005,
        ki_max=0.02,
        kp_learning_rate=0.05,
        ki_learning_rate=0.001,
        error_increase_threshold=0.5,
        error_decrease_threshold=0.1,
    )
    dosing_controller = AdaptivePIDController(
        pid=dosing_pid,
        constraint=dosing_constraint,
        adaptation=dosing_profile,
        feedforward_gain=-5.0,
        feedforward_key="turbidity_adjustment",
    )

    aeration_pid = PIDController(
        Kp=PID_GAINS["aeration_controller"]["Kp"],
        Ki=PID_GAINS["aeration_controller"]["Ki"],
        Kd=PID_GAINS["aeration_controller"]["Kd"],
        setpoint=do_setpoint,
    )
    aeration_pid.set_integral_limits(-15, 15)
    aeration_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=20.0,
        ramp_rate=2.0,
        unit_cost=0.18,
    )
    aeration_profile = AdaptivePIDProfile(
        kp_min=0.2,
        kp_max=3.0,
        ki_min=0.01,
        ki_max=0.25,
        kp_learning_rate=0.1,
        ki_learning_rate=0.01,
        error_increase_threshold=0.7,
        error_decrease_threshold=0.2,
    )
    aeration_controller = AdaptivePIDController(
        pid=aeration_pid,
        constraint=aeration_constraint,
        adaptation=aeration_profile,
        feedforward_gain=1.5,
        feedforward_key="dissolved_oxygen_adjustment",
    )

    return dosing_controller, aeration_controller


def _create_mpc_controllers(
    turbidity_setpoint: float,
    do_setpoint: float,
) -> tuple[MPCFaultTolerantController, AdaptivePIDController]:
    turbidity_decay = float(SIMULATION_DEFAULTS.get("turbidity_decay_factor", 0.05))
    time_delay_steps = int(SIMULATION_DEFAULTS.get("time_delay_steps", 0))
    nominal_turbidity = max(turbidity_setpoint + 1.5, 4.0)
    nominal_dose = 1.8

    a_coeff = 1.0 - turbidity_decay * nominal_dose
    a_coeff = max(0.65, min(0.97, a_coeff))
    b_coeff = -turbidity_decay * nominal_turbidity
    steady_bias = max(
        0.0,
        turbidity_decay * (nominal_turbidity - turbidity_setpoint) * 0.4,
    )

    model = LinearisedProcessModel(
        a=a_coeff,
        b=b_coeff,
        bias=steady_bias,
    )
    constraints = ReliabilityAwareConstraints(
        minimum=0.0,
        maximum=10.0,
        ramp_limit=1.0,
    )

    prediction_horizon = max(5, min(12, time_delay_steps + 5))

    dosing_controller = MPCFaultTolerantController(
        setpoint=turbidity_setpoint,
        model=model,
        constraints=constraints,
        horizon=prediction_horizon,
        control_weight=0.08,
        state_weight=1.1,
        reliability_penalty=80.0,
    )

    aeration_pid = PIDController(
        Kp=PID_GAINS["aeration_controller"]["Kp"],
        Ki=PID_GAINS["aeration_controller"]["Ki"],
        Kd=PID_GAINS["aeration_controller"]["Kd"],
        setpoint=do_setpoint,
    )
    aeration_pid.set_integral_limits(-15, 15)
    aeration_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=20.0,
        ramp_rate=2.0,
        unit_cost=0.18,
    )
    aeration_profile = AdaptivePIDProfile(
        kp_min=0.2,
        kp_max=3.0,
        ki_min=0.01,
        ki_max=0.25,
        kp_learning_rate=0.1,
        ki_learning_rate=0.01,
        error_increase_threshold=0.7,
        error_decrease_threshold=0.2,
    )
    aeration_controller = AdaptivePIDController(
        pid=aeration_pid,
        constraint=aeration_constraint,
        adaptation=aeration_profile,
        feedforward_gain=1.5,
        feedforward_key="dissolved_oxygen_adjustment",
    )

    return dosing_controller, aeration_controller


def _compute_controller_output(
    controller: object,
    *,
    measurement: float,
    disturbances: Dict[str, float],
) -> tuple[float, Dict[str, float]]:
    if isinstance(controller, PrecisionPIDController):
        output = controller.calculate(
            current_value=measurement,
            dt=1.0,
            disturbances=disturbances,
        )
        diagnostics = controller.last_diagnostics.copy()
    elif isinstance(controller, PIDController):
        output = controller.calculate(measurement)
        diagnostics = {"saturated": 0}
    elif isinstance(controller, OnOffController):
        output = controller.calculate(measurement)
        diagnostics = {"saturated": 0}
    else:  # fallback for custom controllers
        output = controller.calculate(measurement)
        diagnostics = {"saturated": 0}
        if hasattr(controller, "last_diagnostics"):
            last_diag = getattr(controller, "last_diagnostics") or {}
            if isinstance(last_diag, dict):
                diagnostics.update(last_diag)

    return output, diagnostics


def _validate_simulation_inputs(
    steps: int,
    log_file: str,
    turbidity_setpoint: float,
    do_setpoint: float,
    controller_type: str,
) -> None:
    """Validate CLI or API inputs before running the simulation."""

    if not isinstance(steps, int) or steps <= 0:
        raise ValueError(f"steps must be a positive integer, received {steps}")

    if not isinstance(log_file, str) or not log_file.strip():
        raise ValueError("log_file must be a non-empty string")

    if not isinstance(turbidity_setpoint, (int, float)) or turbidity_setpoint <= 0:
        raise ValueError(
            f"turbidity_setpoint must be a positive number, received {turbidity_setpoint}"
        )

    if not isinstance(do_setpoint, (int, float)) or do_setpoint <= 0:
        raise ValueError(f"do_setpoint must be a positive number, received {do_setpoint}")

    if controller_type not in ["pid", "on-off", "precision-pid", "adaptive-pid", "mpc"]:
        raise ValueError(
            f"controller_type must be 'pid', 'on-off', 'precision-pid', 'adaptive-pid', or 'mpc', received {controller_type}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the water plant simulator.")
    parser.add_argument("--steps", type=int, default=300, help="Number of simulation steps.")
    parser.add_argument(
        "--log-file",
        type=str,
        default="simulation_log.csv",
        help="Destination CSV file for the simulation log.",
    )
    parser.add_argument(
        "--turbidity-setpoint",
        type=float,
        default=5.0,
        help="Desired turbidity (NTU).",
    )
    parser.add_argument(
        "--do-setpoint",
        type=float,
        default=8.5,
        help="Desired dissolved oxygen (mg/L).",
    )
    parser.add_argument(
        "--controller-type",
        type=str,
        default="pid",
        choices=["pid", "on-off", "precision-pid", "adaptive-pid", "mpc"],
        help="Controller implementation to use.",
    )

    args = parser.parse_args()

    success = run_and_log_simulation(
        steps=args.steps,
        log_file=args.log_file,
        turbidity_setpoint=args.turbidity_setpoint,
        do_setpoint=args.do_setpoint,
        controller_type=args.controller_type,
    )

    sys.exit(0 if success else 1)
