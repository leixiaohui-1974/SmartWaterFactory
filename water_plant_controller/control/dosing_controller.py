from __future__ import annotations

from typing import Dict, Optional

from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.models.wastewater_quality import WastewaterQuality


class PrecisionDosingController:
    """
    Precision chemical dosing controller for denitrification and phosphorus removal.

    Carbon-source dosing uses measured nitrate and a target C/N ratio, while
    coagulant dosing combines TP feedback with influent TP feed-forward. The
    controller exposes alarm thresholds and saturates both dosing channels to
    stay inside operator-defined safety limits.
    """

    CARBON_COD_EQUIVALENT = {
        "methanol": 1.50,
        "acetate": 1.07,
    }

    def __init__(
        self,
        *,
        nitrate_target: float = 2.0,
        tp_target: float = 0.3,
        target_cn_ratio: float = 4.0,
        carbon_max_dose: float = 120.0,
        coagulant_max_dose: float = 100.0,
        nitrate_alarm_threshold: float = 12.0,
        tp_alarm_threshold: float = 1.0,
        readily_biodegradable_fraction: float = 0.18,
        coagulant_ff_ratio: float = 18.0,
    ) -> None:
        self.nitrate_target = nitrate_target
        self.tp_target = tp_target
        self.target_cn_ratio = target_cn_ratio
        self.carbon_max_dose = carbon_max_dose
        self.coagulant_max_dose = coagulant_max_dose
        self.nitrate_alarm_threshold = nitrate_alarm_threshold
        self.tp_alarm_threshold = tp_alarm_threshold
        self.readily_biodegradable_fraction = readily_biodegradable_fraction
        self.coagulant_ff_ratio = coagulant_ff_ratio

        self.carbon_pid = PIDController(
            Kp=4.5,
            Ki=0.35,
            Kd=0.05,
            setpoint=nitrate_target,
            reverse_acting=True,
        )
        self.carbon_pid.set_output_limits(0.0, carbon_max_dose)

        self.coagulant_pid = PIDController(
            Kp=8.0,
            Ki=0.6,
            Kd=0.05,
            setpoint=tp_target,
            reverse_acting=True,
        )
        self.coagulant_pid.set_output_limits(0.0, coagulant_max_dose)

        self.last_command: Dict[str, float] = {
            "carbon_dose_mg_l": 0.0,
            "coagulant_dose_mg_l": 0.0,
            "carbon_mass_flow_kg_h": 0.0,
            "coagulant_mass_flow_kg_h": 0.0,
        }
        self.last_diagnostics: Dict[str, float | list[str] | str] = {}

    def calculate(
        self,
        nitrate_n: float,
        tp: float,
        flow_rate: float,
        *,
        influent_quality: Optional[WastewaterQuality] = None,
        carbon_source: str = "methanol",
        dt: float = 1.0,
    ) -> Dict[str, float]:
        cod_equivalent = self.CARBON_COD_EQUIVALENT.get(
            carbon_source.lower(),
            self.CARBON_COD_EQUIVALENT["methanol"],
        )

        available_biodegradable_cod = 0.0
        influent_tp = tp
        if influent_quality is not None:
            available_biodegradable_cod = (
                influent_quality.COD * self.readily_biodegradable_fraction
            )
            influent_tp = influent_quality.TP

        nitrate_excess = max(0.0, nitrate_n - self.nitrate_target)
        required_external_cod = max(
            0.0,
            nitrate_excess * self.target_cn_ratio - available_biodegradable_cod,
        )
        carbon_feedforward = required_external_cod / cod_equivalent if cod_equivalent > 0.0 else 0.0
        carbon_feedback = self.carbon_pid.calculate(nitrate_n, dt)
        carbon_dose = min(self.carbon_max_dose, carbon_feedforward + carbon_feedback)

        tp_excess = max(0.0, influent_tp - self.tp_target)
        coagulant_feedforward = tp_excess * self.coagulant_ff_ratio
        coagulant_feedback = self.coagulant_pid.calculate(tp, dt)
        coagulant_dose = min(self.coagulant_max_dose, coagulant_feedforward + coagulant_feedback)

        carbon_mass_flow = carbon_dose * flow_rate / 24.0 / 1000.0
        coagulant_mass_flow = coagulant_dose * flow_rate / 24.0 / 1000.0

        alarms = []
        if nitrate_n >= self.nitrate_alarm_threshold:
            alarms.append("high_nitrate")
        if tp >= self.tp_alarm_threshold:
            alarms.append("high_tp")
        if carbon_dose >= self.carbon_max_dose:
            alarms.append("carbon_dose_high_limit")
        if coagulant_dose >= self.coagulant_max_dose:
            alarms.append("coagulant_dose_high_limit")
        if flow_rate <= 0.0:
            alarms.append("invalid_flow")

        self.last_command = {
            "carbon_dose_mg_l": carbon_dose,
            "coagulant_dose_mg_l": coagulant_dose,
            "carbon_mass_flow_kg_h": carbon_mass_flow,
            "coagulant_mass_flow_kg_h": coagulant_mass_flow,
        }
        self.last_diagnostics = {
            "nitrate_n": nitrate_n,
            "tp": tp,
            "flow_rate_m3_d": flow_rate,
            "available_biodegradable_cod_mg_l": available_biodegradable_cod,
            "carbon_feedforward_mg_l": carbon_feedforward,
            "carbon_feedback_mg_l": carbon_feedback,
            "coagulant_feedforward_mg_l": coagulant_feedforward,
            "coagulant_feedback_mg_l": coagulant_feedback,
            "carbon_source": carbon_source.lower(),
            "alarms": alarms,
        }
        return dict(self.last_command)

    def reset(self) -> None:
        self.carbon_pid.reset()
        self.coagulant_pid.reset()
        self.last_command = {
            "carbon_dose_mg_l": 0.0,
            "coagulant_dose_mg_l": 0.0,
            "carbon_mass_flow_kg_h": 0.0,
            "coagulant_mass_flow_kg_h": 0.0,
        }
        self.last_diagnostics = {}
