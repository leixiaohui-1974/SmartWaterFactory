"""Precision dosing controller — carbon source and coagulant dosing.

精准加药控制器：
- 碳源投加 (醋酸钠/甲醇) → 辅助反硝化脱氮
- 絮凝剂投加 (PAC/PAM) → 强化除磷
- 前馈 + 反馈复合控制
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class DosingParams:
    """Dosing system parameters."""

    # Carbon source (sodium acetate)
    carbon_unit_price: float = 2.5         # ¥/kg
    carbon_cod_equiv: float = 1.07         # kg COD/kg sodium acetate
    carbon_dn_ratio: float = 5.0           # C/N ratio for denitrification
    carbon_max_dose: float = 50.0          # max dosage (mg/L)

    # Coagulant (PAC - Polyaluminium Chloride)
    pac_unit_price: float = 1.8            # ¥/kg
    pac_p_removal_ratio: float = 3.0       # mg PAC / mg P removed
    pac_max_dose: float = 30.0             # max dosage (mg/L)

    # Flow
    Q_m3_h: float = 10.0                   # treatment flow (m³/h)


class DosingController:
    """Feedforward + feedback dosing controller.

    精准加药控制：
    - 前馈：根据进水水质估算理论投加量
    - 反馈：根据出水水质PID调节
    """

    def __init__(self, params: DosingParams | None = None):
        self.params = params or DosingParams()

        # Carbon source PID
        self._c_kp = 2.0
        self._c_ki = 0.3
        self._c_integral = 0.0

        # PAC PID
        self._p_kp = 3.0
        self._p_ki = 0.5
        self._p_integral = 0.0

    def calc_carbon_dose(
        self,
        TN_in: float,
        TN_out: float,
        TN_target: float = 15.0,
        COD_available: float = 0.0,
        dt: float = 0.1,
    ) -> Dict[str, float]:
        """Calculate carbon source dosage.

        Args:
            TN_in: Influent TN (mg/L).
            TN_out: Current effluent TN (mg/L).
            TN_target: Target effluent TN (mg/L).
            COD_available: Available COD for denitrification (mg/L).
            dt: Time step (hours).

        Returns:
            Dosage info dict.
        """
        p = self.params

        # Feedforward: estimate N to remove
        delta_N = max(0, TN_in - TN_target)
        cod_needed = delta_N * p.carbon_dn_ratio
        cod_deficit = max(0, cod_needed - COD_available)
        ff_dose = cod_deficit / p.carbon_cod_equiv  # mg/L of sodium acetate

        # Feedback: PID on effluent TN
        tn_error = TN_out - TN_target
        self._c_integral += tn_error * dt
        self._c_integral = max(-20.0, min(20.0, self._c_integral))
        fb_dose = self._c_kp * tn_error + self._c_ki * self._c_integral

        total_dose = max(0.0, min(p.carbon_max_dose, ff_dose + fb_dose))
        cost_per_hour = total_dose * p.Q_m3_h / 1000 * p.carbon_unit_price

        return {
            "carbon_dose_mg_L": round(total_dose, 2),
            "feedforward_mg_L": round(ff_dose, 2),
            "feedback_mg_L": round(fb_dose, 2),
            "cost_yuan_h": round(cost_per_hour, 3),
            "TN_error": round(tn_error, 2),
        }

    def calc_pac_dose(
        self,
        TP_in: float,
        TP_out: float,
        TP_target: float = 0.5,
        dt: float = 0.1,
    ) -> Dict[str, float]:
        """Calculate PAC coagulant dosage for phosphorus removal.

        Args:
            TP_in: Influent TP (mg/L).
            TP_out: Current effluent TP (mg/L).
            TP_target: Target effluent TP (mg/L).
            dt: Time step (hours).

        Returns:
            Dosage info dict.
        """
        p = self.params

        # Feedforward
        delta_P = max(0, TP_in - TP_target)
        ff_dose = delta_P * p.pac_p_removal_ratio

        # Feedback
        tp_error = TP_out - TP_target
        self._p_integral += tp_error * dt
        self._p_integral = max(-10.0, min(10.0, self._p_integral))
        fb_dose = self._p_kp * tp_error + self._p_ki * self._p_integral

        total_dose = max(0.0, min(p.pac_max_dose, ff_dose + fb_dose))
        cost_per_hour = total_dose * p.Q_m3_h / 1000 * p.pac_unit_price

        return {
            "pac_dose_mg_L": round(total_dose, 2),
            "feedforward_mg_L": round(ff_dose, 2),
            "feedback_mg_L": round(fb_dose, 2),
            "cost_yuan_h": round(cost_per_hour, 3),
            "TP_error": round(tp_error, 2),
        }

    def simulate(
        self,
        TN_in_profile: List[float] | None = None,
        TP_in_profile: List[float] | None = None,
        dt: float = 0.1,
        steps: int = 100,
    ) -> Dict[str, Any]:
        """Run dosing simulation.

        Returns time series with dosage, cost, and effluent quality estimates.
        """
        self._c_integral = 0.0
        self._p_integral = 0.0

        if TN_in_profile is None:
            TN_in_profile = [40.0] * steps
        if TP_in_profile is None:
            TP_in_profile = [4.0] * steps

        TN_eff = 25.0  # initial effluent TN
        TP_eff = 3.0   # initial effluent TP
        history: List[Dict[str, Any]] = []
        total_cost = 0.0

        for i in range(steps):
            TN_in = TN_in_profile[min(i, len(TN_in_profile) - 1)]
            TP_in = TP_in_profile[min(i, len(TP_in_profile) - 1)]

            carbon = self.calc_carbon_dose(TN_in, TN_eff, dt=dt)
            pac = self.calc_pac_dose(TP_in, TP_eff, dt=dt)

            # Simplified effluent response to dosing
            # TN decreases with carbon dosing
            removal_boost_tn = carbon["carbon_dose_mg_L"] * 0.08
            TN_eff = max(1.0, TN_eff - removal_boost_tn * dt + (TN_in * 0.01) * dt)

            # TP decreases with PAC dosing
            removal_boost_tp = pac["pac_dose_mg_L"] * 0.05
            TP_eff = max(0.05, TP_eff - removal_boost_tp * dt + (TP_in * 0.005) * dt)

            step_cost = carbon["cost_yuan_h"] + pac["cost_yuan_h"]
            total_cost += step_cost * dt

            history.append({
                "t": round(i * dt, 3),
                "TN_in": TN_in,
                "TN_eff": round(TN_eff, 2),
                "TP_in": TP_in,
                "TP_eff": round(TP_eff, 2),
                **{f"carbon_{k}": v for k, v in carbon.items()},
                **{f"pac_{k}": v for k, v in pac.items()},
            })

        return {
            "success": True,
            "method": "FF_FB_Dosing",
            "total_cost_yuan": round(total_cost, 2),
            "final_TN_eff": round(TN_eff, 2),
            "final_TP_eff": round(TP_eff, 2),
            "steps": steps,
            "history": history,
        }
