"""Precision aeration controller — cascade DO control with energy optimization.

精准曝气控制器：DO 级联控制 + 风量-能耗优化。
支持：
- NH3-N/DO 级联控制 (外环 NH3-N → 内环 DO)
- 风量 → 能耗映射 (鼓风机特性曲线)
- 节能优化模式 (最低 DO 满足出水标准)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class BlowerParams:
    """Blower characteristic parameters."""
    rated_flow: float = 100.0       # m³/min
    rated_power: float = 30.0       # kW
    efficiency: float = 0.65        # blower efficiency
    min_flow_ratio: float = 0.3     # minimum turndown ratio


class AerationController:
    """Cascade DO control: outer loop NH3-N → inner loop DO → blower flow.

    精准曝气控制器：
    - 外环：NH3-N PID → DO 设定值
    - 内环：DO PID → 风量
    - 节能：最低 DO 策略
    """

    def __init__(
        self,
        DO_setpoint: float = 2.0,
        NH3_N_setpoint: float = 3.0,
        blower: BlowerParams | None = None,
    ):
        self.DO_setpoint = DO_setpoint
        self.NH3_N_setpoint = NH3_N_setpoint
        self.blower = blower or BlowerParams()

        # Inner loop PID (DO control)
        self._do_kp = 5.0
        self._do_ki = 0.5
        self._do_kd = 0.1
        self._do_integral = 0.0
        self._do_prev_error = 0.0

        # Outer loop PI (NH3-N → DO setpoint)
        self._nh3_kp = 0.3
        self._nh3_ki = 0.05
        self._nh3_integral = 0.0

    def _calc_blower_power(self, flow_ratio: float) -> float:
        """Estimate blower power from flow ratio using affinity laws.

        Power ∝ flow³ (fan affinity law, simplified).
        """
        ratio = max(self.blower.min_flow_ratio, min(1.0, flow_ratio))
        return self.blower.rated_power * (ratio ** 2.5) / self.blower.efficiency

    def step(
        self,
        DO_measured: float,
        NH3_N_measured: float,
        dt: float = 0.1,
        cascade: bool = True,
    ) -> Dict[str, float]:
        """Execute one control step.

        Args:
            DO_measured: Current DO measurement (mg/L).
            NH3_N_measured: Current NH3-N measurement (mg/L).
            dt: Time step (hours).
            cascade: If True, outer loop adjusts DO setpoint.

        Returns:
            Dict with DO_setpoint, flow_ratio, power_kw, etc.
        """
        # Outer loop: NH3-N → DO setpoint adjustment
        if cascade:
            nh3_error = NH3_N_measured - self.NH3_N_setpoint
            self._nh3_integral += nh3_error * dt
            self._nh3_integral = max(-5.0, min(5.0, self._nh3_integral))
            do_adjust = self._nh3_kp * nh3_error + self._nh3_ki * self._nh3_integral
            self.DO_setpoint = max(0.5, min(5.0, 2.0 + do_adjust))

        # Inner loop: DO PID → blower flow
        do_error = self.DO_setpoint - DO_measured
        self._do_integral += do_error * dt
        self._do_integral = max(-20.0, min(20.0, self._do_integral))
        do_derivative = (do_error - self._do_prev_error) / dt if dt > 0 else 0.0
        self._do_prev_error = do_error

        flow_ratio = (
            self._do_kp * do_error
            + self._do_ki * self._do_integral
            + self._do_kd * do_derivative
        )
        flow_ratio = max(self.blower.min_flow_ratio, min(1.0, flow_ratio / 10.0 + 0.5))

        air_flow = flow_ratio * self.blower.rated_flow
        power_kw = self._calc_blower_power(flow_ratio)

        return {
            "DO_setpoint": round(self.DO_setpoint, 3),
            "DO_measured": round(DO_measured, 3),
            "DO_error": round(do_error, 3),
            "NH3_N_measured": round(NH3_N_measured, 3),
            "flow_ratio": round(flow_ratio, 4),
            "air_flow_m3_min": round(air_flow, 2),
            "power_kw": round(power_kw, 2),
        }

    def simulate(
        self,
        DO_initial: float = 0.5,
        NH3_N_profile: List[float] | None = None,
        dt: float = 0.1,
        steps: int = 100,
        cascade: bool = True,
    ) -> Dict[str, Any]:
        """Run aeration control simulation.

        Args:
            DO_initial: Initial DO (mg/L).
            NH3_N_profile: NH3-N measurements over time. If None, uses constant.
            dt: Time step (hours).
            steps: Number of steps.
            cascade: Enable cascade control.

        Returns:
            Dict with time series and energy summary.
        """
        self._do_integral = 0.0
        self._do_prev_error = 0.0
        self._nh3_integral = 0.0

        if NH3_N_profile is None:
            NH3_N_profile = [self.NH3_N_setpoint * 2.0] * steps

        DO = DO_initial
        history: List[Dict[str, float]] = []
        total_energy = 0.0

        for i in range(steps):
            nh3 = NH3_N_profile[min(i, len(NH3_N_profile) - 1)]
            result = self.step(DO, nh3, dt=dt, cascade=cascade)
            history.append({"t": round(i * dt, 3), **result})

            # Simple DO dynamics: DO approaches setpoint via aeration
            # dDO/dt = KLa * (DO_sat - DO) - OUR
            kla = result["flow_ratio"] * 8.0  # simplified KLa ∝ air flow
            DO_sat = 8.0  # mg/L at ~20°C
            OUR = 2.0  # oxygen uptake rate mg/L/h
            DO += (kla * (DO_sat - DO) - OUR) * dt
            DO = max(0.0, min(DO_sat, DO))

            total_energy += result["power_kw"] * dt  # kWh

        return {
            "success": True,
            "method": "CascadeDO_Aeration",
            "total_energy_kwh": round(total_energy, 2),
            "avg_power_kw": round(total_energy / (steps * dt) if steps > 0 else 0, 2),
            "final_DO": round(DO, 3),
            "DO_setpoint": round(self.DO_setpoint, 3),
            "steps": steps,
            "history": history,
        }
