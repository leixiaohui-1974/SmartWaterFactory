from __future__ import annotations

from typing import Dict, Optional
import math

from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.models.wastewater_quality import WastewaterQuality


class PrecisionAerationController:
    """
    Cascade controller for precision aeration in rural A/A/O systems.

    The outer loop regulates dissolved oxygen. The inner loop tracks the
    airflow demand by adjusting blower speed and valve position. A simple
    feed-forward term anticipates oxygen demand from influent COD and NH3-N
    loading, while the energy layer trims excess blower demand when the DO
    margin is healthy.
    """

    def __init__(
        self,
        do_setpoint: float = 2.0,
        *,
        min_blower_speed: float = 25.0,
        max_blower_speed: float = 100.0,
        min_valve_position: float = 20.0,
        max_valve_position: float = 100.0,
        rated_power_kw: float = 15.0,
        cod_feedforward_gain: float = 0.035,
        nh3_feedforward_gain: float = 0.75,
        energy_trim_gain: float = 12.0,
        do_deadband: float = 0.15,
    ) -> None:
        self.outer_pid = PIDController(Kp=18.0, Ki=2.0, Kd=1.5, setpoint=do_setpoint)
        self.outer_pid.set_output_limits(0.0, 100.0)

        self.inner_pid = PIDController(Kp=0.9, Ki=0.12, Kd=0.03, setpoint=0.0)
        self.inner_pid.set_output_limits(-30.0, 30.0)
        self.inner_pid.set_integral_limits(-20.0, 20.0)

        self.do_setpoint = do_setpoint
        self.min_blower_speed = min_blower_speed
        self.max_blower_speed = max_blower_speed
        self.min_valve_position = min_valve_position
        self.max_valve_position = max_valve_position
        self.rated_power_kw = rated_power_kw
        self.cod_feedforward_gain = cod_feedforward_gain
        self.nh3_feedforward_gain = nh3_feedforward_gain
        self.energy_trim_gain = energy_trim_gain
        self.do_deadband = do_deadband

        self.last_airflow = 0.0
        self.last_command: Dict[str, float] = {
            "airflow_command": 0.0,
            "blower_speed": 0.0,
            "valve_position": 0.0,
            "estimated_power_kw": 0.0,
        }
        self.last_diagnostics: Dict[str, float] = {}

    def set_setpoint(self, do_setpoint: float) -> None:
        self.do_setpoint = do_setpoint
        self.outer_pid.setpoint = do_setpoint

    def calculate(
        self,
        measured_do: float,
        *,
        dt: float = 1.0,
        influent_quality: Optional[WastewaterQuality] = None,
        airflow_feedback: Optional[float] = None,
    ) -> Dict[str, float]:
        feedforward = 0.0
        if influent_quality is not None:
            feedforward = (
                influent_quality.COD * self.cod_feedforward_gain
                + influent_quality.NH3_N * self.nh3_feedforward_gain
            )

        outer_demand = self.outer_pid.calculate(measured_do, dt)
        raw_airflow_demand = self._clamp(outer_demand + feedforward, 0.0, 100.0)

        do_margin = measured_do - self.do_setpoint
        energy_trim = 0.0
        if do_margin > self.do_deadband:
            energy_trim = min(
                raw_airflow_demand,
                (do_margin - self.do_deadband) * self.energy_trim_gain,
            )

        minimum_safe_airflow = 0.0 if feedforward < 1.0 else min(100.0, feedforward * 0.55)
        optimized_airflow = max(minimum_safe_airflow, raw_airflow_demand - energy_trim)

        actual_airflow = airflow_feedback if airflow_feedback is not None else self.last_airflow
        self.inner_pid.setpoint = optimized_airflow
        airflow_trim = self.inner_pid.calculate(actual_airflow, dt)
        target_airflow = self._clamp(optimized_airflow + airflow_trim, 0.0, 100.0)

        blower_speed, valve_position = self._split_airflow_command(target_airflow)
        achieved_airflow = blower_speed * valve_position / 100.0
        estimated_power_kw = self.rated_power_kw * math.pow(blower_speed / 100.0, 3.0)

        self.last_airflow = achieved_airflow
        self.last_command = {
            "airflow_command": target_airflow,
            "blower_speed": blower_speed,
            "valve_position": valve_position,
            "estimated_power_kw": estimated_power_kw,
        }
        self.last_diagnostics = {
            "measured_do": measured_do,
            "outer_airflow_demand": outer_demand,
            "feedforward_airflow": feedforward,
            "raw_airflow_demand": raw_airflow_demand,
            "energy_trim": energy_trim,
            "minimum_safe_airflow": minimum_safe_airflow,
            "optimized_airflow": optimized_airflow,
            "actual_airflow_feedback": actual_airflow,
            "inner_loop_trim": airflow_trim,
            "achieved_airflow": achieved_airflow,
            "blower_speed": blower_speed,
            "valve_position": valve_position,
            "estimated_power_kw": estimated_power_kw,
        }
        return dict(self.last_command)

    def reset(self) -> None:
        self.outer_pid.reset()
        self.inner_pid.reset()
        self.last_airflow = 0.0
        self.last_command = {
            "airflow_command": 0.0,
            "blower_speed": 0.0,
            "valve_position": 0.0,
            "estimated_power_kw": 0.0,
        }
        self.last_diagnostics = {}

    def _split_airflow_command(self, airflow_command: float) -> tuple[float, float]:
        if airflow_command <= 0.0:
            return 0.0, 0.0

        blower_speed = max(
            self.min_blower_speed,
            min(self.max_blower_speed, math.sqrt(airflow_command / 100.0) * 100.0),
        )
        valve_position = self._clamp(
            airflow_command / max(blower_speed, 1e-6) * 100.0,
            self.min_valve_position,
            self.max_valve_position,
        )

        if blower_speed * valve_position / 100.0 < airflow_command:
            blower_speed = self._clamp(
                airflow_command * 100.0 / max(valve_position, 1e-6),
                self.min_blower_speed,
                self.max_blower_speed,
            )

        return blower_speed, valve_position

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
