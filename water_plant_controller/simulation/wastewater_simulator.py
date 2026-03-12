from __future__ import annotations

from typing import Any, Dict, Optional
import math

from water_plant_controller.models.wastewater_quality import WastewaterQuality


class WastewaterSimulator:
    """
    Simplified rural wastewater simulator for an A/A/O treatment train.

    The simulator tracks equalisation, anaerobic-anoxic-aerobic reactions,
    sedimentation, aeration dynamics, carbon dosing, phosphorus precipitation,
    sludge production, mixed-liquor recycle effects, and hydraulic retention time.
    """

    DEFAULT_CONFIG: Dict[str, float] = {
        "dt_hours": 0.25,
        "equalization_tau_hours": 2.0,
        "anaerobic_volume_m3": 10.0,
        "anoxic_volume_m3": 14.0,
        "aerobic_volume_m3": 22.0,
        "sedimentation_volume_m3": 8.0,
        "internal_recycle_ratio": 2.0,
        "organic_n_baseline": 3.0,
        "readily_biodegradable_fraction": 0.22,
        "anaerobic_cod_hydrolysis_rate": 0.10,
        "anaerobic_tp_release_rate": 0.04,
        "anoxic_max_denit_rate": 0.32,
        "denit_half_velocity_no3": 1.5,
        "denit_half_velocity_cod": 25.0,
        "denit_temp_coefficient": 1.07,
        "nitrification_max_rate": 0.24,
        "nitrification_half_velocity_nh3": 1.0,
        "nitrification_half_velocity_do": 1.2,
        "nitrification_temp_coefficient": 1.08,
        "cod_oxidation_rate": 0.18,
        "kla_max": 3.2,
        "do_consumption_factor": 0.045,
        "nitrification_oxygen_factor": 0.18,
        "denit_cod_factor": 2.86,
        "methanol_cod_equivalent": 1.50,
        "acetate_cod_equivalent": 1.07,
        "bio_p_uptake_rate": 0.08,
        "chemical_p_removal_factor": 0.015,
        "base_ss_capture": 0.72,
        "coagulant_ss_gain": 0.002,
        "particulate_cod_capture_fraction": 0.10,
        "biomass_yield": 0.35,
        "chemical_sludge_factor": 0.75,
        "sludge_decay_factor": 0.015,
    }

    def __init__(
        self,
        initial_quality: Optional[WastewaterQuality] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.config: Dict[str, float] = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

        self.influent_quality = initial_quality or WastewaterQuality.from_rural_typical()
        self.current_quality = self.influent_quality
        self.equalized_quality = self.influent_quality

        self.time_hours = 0.0
        self.cumulative_sludge_kg = 0.0
        self.last_sludge_production_kg = 0.0
        self.hrt_hours = self._calculate_hrt(self.current_quality.flow_rate)
        self.last_diagnostics: Dict[str, float] = {}

        self.nitrate_n = self._estimate_nitrate(self.current_quality)
        self._working_nitrate_n = self.nitrate_n
        self._step_metrics: Dict[str, float] = {}

    def step(
        self,
        blower_signal: float,
        carbon_dose: float,
        coagulant_dose: float,
        influent: Optional[WastewaterQuality] = None,
        *,
        carbon_source: str = "methanol",
    ) -> WastewaterQuality:
        """
        Advance the process by one discrete simulation step.
        """

        if influent is not None:
            self.influent_quality = influent

        blower_signal = self._clamp(blower_signal, 0.0, 100.0)
        carbon_dose = max(0.0, carbon_dose)
        coagulant_dose = max(0.0, coagulant_dose)

        self._step_metrics = {
            "blower_signal": blower_signal,
            "carbon_dose": carbon_dose,
            "coagulant_dose": coagulant_dose,
        }
        self._working_nitrate_n = self.nitrate_n

        regulated = self.inflow_regulation(self.influent_quality)
        anaerobic = self.anaerobic_zone(regulated)
        anoxic = self.anoxic_zone(anaerobic, carbon_dose, carbon_source)
        aerobic = self.aerobic_zone(anoxic, blower_signal)
        effluent = self.sedimentation(aerobic, coagulant_dose)

        self.current_quality = effluent
        self.equalized_quality = regulated
        self.nitrate_n = self._working_nitrate_n
        self.time_hours += self.config["dt_hours"]
        self.hrt_hours = self._calculate_hrt(effluent.flow_rate)
        self._step_metrics["hrt_hours"] = self.hrt_hours
        self._step_metrics["cumulative_sludge_kg"] = self.cumulative_sludge_kg
        self.last_diagnostics = dict(self._step_metrics)
        return effluent

    def inflow_regulation(self, influent: WastewaterQuality) -> WastewaterQuality:
        alpha = self._first_order_blend_factor(self.config["equalization_tau_hours"])
        previous = self.equalized_quality

        regulated = WastewaterQuality(
            COD=self._blend(previous.COD, influent.COD, alpha),
            NH3_N=self._blend(previous.NH3_N, influent.NH3_N, alpha),
            TN=self._blend(previous.TN, influent.TN, alpha),
            TP=self._blend(previous.TP, influent.TP, alpha),
            SS=self._blend(previous.SS, influent.SS, alpha),
            DO=self._blend(previous.DO, influent.DO, alpha),
            pH=self._blend(previous.pH, influent.pH, alpha),
            temperature=self._blend(previous.temperature, influent.temperature, alpha),
            flow_rate=self._blend(previous.flow_rate, influent.flow_rate, alpha),
        )

        self._working_nitrate_n = self._blend(
            self._working_nitrate_n,
            self._estimate_nitrate(influent),
            alpha,
        )
        self._step_metrics["regulated_flow_m3_d"] = regulated.flow_rate
        self._step_metrics["equalization_alpha"] = alpha
        return regulated

    def anaerobic_zone(self, quality: WastewaterQuality) -> WastewaterQuality:
        dt = self.config["dt_hours"]
        cod_hydrolysis = quality.COD * self.config["anaerobic_cod_hydrolysis_rate"] * dt
        tp_release = quality.TP * self.config["anaerobic_tp_release_rate"] * dt

        effluent = WastewaterQuality(
            COD=max(0.0, quality.COD - cod_hydrolysis),
            NH3_N=quality.NH3_N,
            TN=quality.TN,
            TP=max(0.0, quality.TP + tp_release),
            SS=max(0.0, quality.SS * (1.0 - 0.01 * dt)),
            DO=max(0.05, quality.DO * 0.25),
            pH=self._clamp(quality.pH - 0.03 * dt, 6.0, 8.8),
            temperature=quality.temperature,
            flow_rate=quality.flow_rate,
        )

        self._step_metrics["anaerobic_cod_hydrolysis_mg_l"] = cod_hydrolysis
        self._step_metrics["anaerobic_tp_release_mg_l"] = tp_release
        return effluent

    def anoxic_zone(
        self,
        quality: WastewaterQuality,
        carbon_dose: float,
        carbon_source: str,
    ) -> WastewaterQuality:
        dt = self.config["dt_hours"]
        recycle_ratio = self.config["internal_recycle_ratio"]
        incoming_nitrate = self._estimate_nitrate(quality)
        organic_n = max(0.0, quality.TN - quality.NH3_N - incoming_nitrate)

        recycled_nitrate = self.nitrate_n * recycle_ratio / (1.0 + recycle_ratio)
        available_nitrate = incoming_nitrate + recycled_nitrate
        external_cod = carbon_dose * self._carbon_cod_equivalent(carbon_source)
        readily_biodegradable_cod = quality.COD * self.config["readily_biodegradable_fraction"]
        available_cod = readily_biodegradable_cod + external_cod

        denit_rate = self.config["anoxic_max_denit_rate"] * self._temperature_factor(
            self.config["denit_temp_coefficient"],
            quality.temperature,
        )
        denit_rate *= self._monod(available_nitrate, self.config["denit_half_velocity_no3"])
        denit_rate *= self._monod(available_cod, self.config["denit_half_velocity_cod"])
        denit_fraction = 1.0 - math.exp(-denit_rate * dt)
        denit_removed = min(available_nitrate, available_nitrate * denit_fraction)

        cod_needed = denit_removed * self.config["denit_cod_factor"]
        cod_consumed = min(available_cod, cod_needed)
        residual_external_cod = max(
            0.0,
            external_cod - max(0.0, cod_consumed - readily_biodegradable_cod),
        )
        resulting_cod = max(0.0, quality.COD - min(quality.COD, cod_consumed) + residual_external_cod)

        self._working_nitrate_n = max(0.0, available_nitrate - denit_removed)
        effluent = WastewaterQuality(
            COD=resulting_cod,
            NH3_N=quality.NH3_N,
            TN=max(0.0, organic_n + quality.NH3_N + self._working_nitrate_n),
            TP=quality.TP,
            SS=max(0.0, quality.SS * (1.0 - 0.015 * dt)),
            DO=max(0.05, quality.DO * 0.55),
            pH=self._clamp(quality.pH + 0.02 * dt, 6.0, 8.8),
            temperature=quality.temperature,
            flow_rate=quality.flow_rate,
        )

        self._step_metrics["anoxic_recycled_nitrate_mg_l"] = recycled_nitrate
        self._step_metrics["anoxic_denitrified_n_mg_l"] = denit_removed
        self._step_metrics["anoxic_external_cod_mg_l"] = external_cod
        self._step_metrics["anoxic_cod_consumed_mg_l"] = cod_consumed
        return effluent

    def aerobic_zone(self, quality: WastewaterQuality, blower_signal: float) -> WastewaterQuality:
        dt = self.config["dt_hours"]
        do_saturation = self._oxygen_saturation(quality.temperature)
        blower_fraction = blower_signal / 100.0
        kla = self.config["kla_max"] * blower_fraction

        incoming_nitrate = self._working_nitrate_n
        organic_n = max(0.0, quality.TN - quality.NH3_N - incoming_nitrate)

        nitrification_rate = self.config["nitrification_max_rate"] * self._temperature_factor(
            self.config["nitrification_temp_coefficient"],
            quality.temperature,
        )
        nitrification_rate *= self._monod(
            quality.NH3_N,
            self.config["nitrification_half_velocity_nh3"],
        )
        nitrification_rate *= self._monod(
            max(quality.DO, 0.05),
            self.config["nitrification_half_velocity_do"],
        )
        nitrification_fraction = 1.0 - math.exp(-nitrification_rate * dt)
        nh3_removed = min(quality.NH3_N, quality.NH3_N * nitrification_fraction)

        cod_oxidation_rate = self.config["cod_oxidation_rate"] * self._monod(
            max(quality.DO, 0.05),
            self.config["nitrification_half_velocity_do"],
        )
        cod_removed = min(quality.COD, quality.COD * (1.0 - math.exp(-cod_oxidation_rate * dt)))

        oxygen_transfer = kla * max(0.0, do_saturation - quality.DO) * dt
        oxygen_demand = (
            cod_removed * self.config["do_consumption_factor"]
            + nh3_removed * self.config["nitrification_oxygen_factor"]
        )
        resulting_do = self._clamp(
            quality.DO + oxygen_transfer - oxygen_demand,
            0.1,
            do_saturation,
        )

        bio_p_uptake = min(
            quality.TP,
            quality.TP * self.config["bio_p_uptake_rate"] * blower_fraction * dt,
        )
        self._working_nitrate_n = max(0.0, incoming_nitrate + nh3_removed)

        effluent = WastewaterQuality(
            COD=max(0.0, quality.COD - cod_removed),
            NH3_N=max(0.0, quality.NH3_N - nh3_removed),
            TN=max(0.0, organic_n + max(0.0, quality.NH3_N - nh3_removed) + self._working_nitrate_n),
            TP=max(0.0, quality.TP - bio_p_uptake),
            SS=max(0.0, quality.SS * (1.0 - 0.02 * dt)),
            DO=resulting_do,
            pH=self._clamp(quality.pH - 0.04 * dt, 6.0, 8.8),
            temperature=quality.temperature,
            flow_rate=quality.flow_rate,
        )

        self._step_metrics["aerobic_nitrified_n_mg_l"] = nh3_removed
        self._step_metrics["aerobic_cod_removed_mg_l"] = cod_removed
        self._step_metrics["aerobic_oxygen_transfer_mg_l"] = oxygen_transfer
        self._step_metrics["aerobic_oxygen_demand_mg_l"] = oxygen_demand
        self._step_metrics["aerobic_do_saturation_mg_l"] = do_saturation
        return effluent

    def sedimentation(self, quality: WastewaterQuality, coagulant_dose: float) -> WastewaterQuality:
        dt = self.config["dt_hours"]
        capture_efficiency = self._clamp(
            self.config["base_ss_capture"] + coagulant_dose * self.config["coagulant_ss_gain"],
            0.0,
            0.96,
        )
        captured_ss = quality.SS * capture_efficiency
        particulate_cod_removed = (
            quality.COD * self.config["particulate_cod_capture_fraction"] * capture_efficiency
        )
        chemical_p_removed = min(
            quality.TP,
            coagulant_dose * self.config["chemical_p_removal_factor"],
        )

        effluent = WastewaterQuality(
            COD=max(0.0, quality.COD - particulate_cod_removed),
            NH3_N=quality.NH3_N,
            TN=max(0.0, quality.TN),
            TP=max(0.0, quality.TP - chemical_p_removed),
            SS=max(0.0, quality.SS - captured_ss),
            DO=max(0.1, quality.DO - 0.05 * dt),
            pH=self._clamp(quality.pH - 0.002 * coagulant_dose, 6.0, 8.8),
            temperature=quality.temperature,
            flow_rate=quality.flow_rate,
        )

        sludge_kg = self._sludge_production(
            cod_removed=particulate_cod_removed
            + self._step_metrics.get("aerobic_cod_removed_mg_l", 0.0),
            captured_ss=captured_ss,
            coagulant_dose=coagulant_dose,
            flow_rate=quality.flow_rate,
        )
        self.last_sludge_production_kg = sludge_kg
        self.cumulative_sludge_kg += sludge_kg

        self._step_metrics["sedimentation_ss_removed_mg_l"] = captured_ss
        self._step_metrics["sedimentation_tp_removed_mg_l"] = chemical_p_removed
        self._step_metrics["sludge_production_kg"] = sludge_kg
        self._step_metrics["effluent_compliant"] = float(effluent.is_discharge_compliant())
        return effluent

    def _sludge_production(
        self,
        *,
        cod_removed: float,
        captured_ss: float,
        coagulant_dose: float,
        flow_rate: float,
    ) -> float:
        flow_step_m3 = flow_rate * self.config["dt_hours"] / 24.0
        organic_sludge = cod_removed * self.config["biomass_yield"] * flow_step_m3 / 1000.0
        solids_sludge = captured_ss * flow_step_m3 / 1000.0
        chemical_sludge = (
            coagulant_dose
            * self.config["chemical_sludge_factor"]
            * flow_step_m3
            / 1000.0
        )
        decay = max(
            0.0,
            self.cumulative_sludge_kg
            * self.config["sludge_decay_factor"]
            * self.config["dt_hours"],
        )
        return max(0.0, organic_sludge + solids_sludge + chemical_sludge - decay)

    def _calculate_hrt(self, flow_rate: float) -> float:
        total_volume = (
            self.config["anaerobic_volume_m3"]
            + self.config["anoxic_volume_m3"]
            + self.config["aerobic_volume_m3"]
            + self.config["sedimentation_volume_m3"]
        )
        hourly_flow = max(flow_rate / 24.0, 1e-6)
        return total_volume / hourly_flow

    def _estimate_nitrate(self, quality: WastewaterQuality) -> float:
        return max(0.0, quality.TN - quality.NH3_N - self.config["organic_n_baseline"])

    def _carbon_cod_equivalent(self, carbon_source: str) -> float:
        source = carbon_source.lower()
        if source == "acetate":
            return self.config["acetate_cod_equivalent"]
        return self.config["methanol_cod_equivalent"]

    @staticmethod
    def _blend(previous: float, current: float, alpha: float) -> float:
        return previous + alpha * (current - previous)

    def _first_order_blend_factor(self, tau_hours: float) -> float:
        tau_hours = max(tau_hours, self.config["dt_hours"])
        return self.config["dt_hours"] / tau_hours

    @staticmethod
    def _monod(substrate: float, half_velocity: float) -> float:
        return substrate / (half_velocity + substrate) if substrate > 0.0 else 0.0

    @staticmethod
    def _temperature_factor(theta: float, temperature: float, reference: float = 20.0) -> float:
        return theta ** (temperature - reference)

    @staticmethod
    def _oxygen_saturation(temperature: float) -> float:
        return max(7.5, 14.6 - 0.4 * temperature + 0.008 * temperature * temperature)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
