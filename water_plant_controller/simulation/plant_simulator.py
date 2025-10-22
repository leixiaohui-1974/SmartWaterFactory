from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Protocol, runtime_checkable
import math

from water_plant_controller.models.water_quality import WaterQuality
from config.settings import SIMULATION_DEFAULTS


@runtime_checkable
class DisturbanceProvider(Protocol):
    def __call__(
        self,
        *,
        step_index: int,
        timestamp: datetime,
        quality: WaterQuality,
        inputs: Dict[str, float],
    ) -> Dict[str, float]:
        ...


@runtime_checkable
class SensorModel(Protocol):
    def __call__(
        self,
        *,
        step_index: int,
        timestamp: datetime,
        true_quality: WaterQuality,
        diagnostics: Dict[str, float],
    ) -> Dict[str, float]:
        ...


class PlantSimulator:
    """
    Simplified water-treatment plant process model with disturbance and sensor hooks.

    The simulator models how coagulant dosing and aeration influence turbidity
    and dissolved oxygen while supporting non-linear response, saturation,
    transport delay, user-defined disturbances, and measurement noise/fault modelling.
    """

    def __init__(
        self,
        initial_quality: WaterQuality,
        config: Optional[Dict[str, Any]] = None,
        *,
        disturbance_provider: Optional[DisturbanceProvider] = None,
        sensor_provider: Optional[SensorModel] = None,
        redundant_sensor_provider: Optional[SensorModel] = None,
    ) -> None:
        if not isinstance(initial_quality, WaterQuality):
            raise TypeError("initial_quality must be a WaterQuality instance")

        self.true_quality: WaterQuality = initial_quality
        self.current_quality: WaterQuality = initial_quality
        self.simulation_time: datetime = initial_quality.timestamp

        self.config: Dict[str, Any] = SIMULATION_DEFAULTS.copy()
        if config:
            self.config.update(config)

        self._do_saturation: float = self.config["do_saturation"]
        self._do_consumption_rate: float = self.config["do_consumption_rate"]
        self._turbidity_decay_factor: float = self.config["turbidity_decay_factor"]
        self._do_increase_rate: float = self.config["do_increase_rate"]
        self._aeration_non_linearity: float = self.config["aeration_non_linearity"]
        self._sensor_thresholds: Dict[str, float] = self.config.get(
            "sensor_fault_thresholds",
            {"turbidity": 3.0, "dissolved_oxygen": 1.0},
        )

        self._delay_steps: int = int(self.config.get("time_delay_steps", 0))
        if self._delay_steps > 0:
            self._coagulant_pipeline: deque[float] = deque(
                [0.0] * self._delay_steps, maxlen=self._delay_steps
            )
            self._aeration_pipeline: deque[float] = deque(
                [0.0] * self._delay_steps, maxlen=self._delay_steps
            )

        self._disturbance_provider: Optional[DisturbanceProvider] = disturbance_provider
        self._sensor_provider: Optional[SensorModel] = sensor_provider
        self._redundant_sensor_provider: Optional[SensorModel] = redundant_sensor_provider
        redundant_defaults = self.config.get(
            "redundant_sensor_weights",
            {"primary": 1.0, "secondary": 0.0},
        )
        self._redundant_weights: Dict[str, float] = {
            "primary": float(redundant_defaults.get("primary", 1.0)),
            "secondary": float(redundant_defaults.get("secondary", 0.0)),
        }
        if self._redundant_weights["primary"] < 0 or self._redundant_weights["secondary"] < 0:
            raise ValueError("redundant sensor weights must be non-negative")
        self.step_index: int = 0
        self.last_diagnostics: Dict[str, float] = {}

    def step(self, coagulant_dose: float, aeration_rate: float) -> WaterQuality:
        if not isinstance(coagulant_dose, (int, float)):
            raise TypeError(
                f"coagulant_dose must be numeric, received {type(coagulant_dose).__name__}"
            )
        if not isinstance(aeration_rate, (int, float)):
            raise TypeError(
                f"aeration_rate must be numeric, received {type(aeration_rate).__name__}"
            )

        if coagulant_dose < 0:
            raise ValueError(f"coagulant_dose must be non-negative, received {coagulant_dose}")
        if aeration_rate < 0:
            raise ValueError(f"aeration_rate must be non-negative, received {aeration_rate}")

        if coagulant_dose > 1000:
            raise ValueError(f"coagulant_dose too large for stable simulation: {coagulant_dose}")
        if aeration_rate > 1000:
            raise ValueError(f"aeration_rate too large for stable simulation: {aeration_rate}")

        if not math.isfinite(coagulant_dose):
            raise ValueError(f"coagulant_dose contains an invalid number: {coagulant_dose}")
        if not math.isfinite(aeration_rate):
            raise ValueError(f"aeration_rate contains an invalid number: {aeration_rate}")

        if self._delay_steps > 0:
            delayed_coagulant = self._coagulant_pipeline.popleft()
            self._coagulant_pipeline.append(coagulant_dose)

            delayed_aeration = self._aeration_pipeline.popleft()
            self._aeration_pipeline.append(aeration_rate)
        else:
            delayed_coagulant = coagulant_dose
            delayed_aeration = aeration_rate

        self.simulation_time += timedelta(minutes=1)

        turbidity_reduction = (
            self._turbidity_decay_factor * delayed_coagulant * self.current_quality.turbidity
        )
        new_turbidity = self.current_quality.turbidity - turbidity_reduction

        current_do = self.current_quality.dissolved_oxygen
        do_deficit = self._do_saturation - current_do
        if self._do_saturation > 0:
            efficiency_factor = (do_deficit / self._do_saturation) ** (
                self._aeration_non_linearity - 1
            )
        else:
            efficiency_factor = 1.0

        effective_increase_rate = self._do_increase_rate * efficiency_factor
        do_increase = effective_increase_rate * delayed_aeration * do_deficit
        do_decrease = self._do_consumption_rate * current_do
        new_do = current_do + do_increase - do_decrease

        turbidity_adjustment = 0.0
        dissolved_oxygen_adjustment = 0.0
        diagnostics: Dict[str, float] = {
            "coagulant_dose": coagulant_dose,
            "aeration_rate": aeration_rate,
            "delayed_coagulant": delayed_coagulant,
            "delayed_aeration": delayed_aeration,
        }

        if self._disturbance_provider is not None:
            disturbance = self._disturbance_provider(
                step_index=self.step_index,
                timestamp=self.simulation_time,
                quality=self.current_quality,
                inputs={
                    "coagulant_dose": coagulant_dose,
                    "aeration_rate": aeration_rate,
                    "delayed_coagulant": delayed_coagulant,
                    "delayed_aeration": delayed_aeration,
                },
            )
            if disturbance:
                turbidity_adjustment = disturbance.get("turbidity", 0.0)
                dissolved_oxygen_adjustment = disturbance.get("dissolved_oxygen", 0.0)
                diagnostics.update({k: v for k, v in disturbance.items() if k not in diagnostics})

        true_quality = WaterQuality(
            timestamp=self.simulation_time,
            ph=self.current_quality.ph,
            turbidity=max(0.0, new_turbidity + turbidity_adjustment),
            dissolved_oxygen=max(
                0.0,
                min(self._do_saturation, new_do + dissolved_oxygen_adjustment),
            ),
        )

        diagnostics.update(
            {
                "turbidity_adjustment": turbidity_adjustment,
                "dissolved_oxygen_adjustment": dissolved_oxygen_adjustment,
                "raw_turbidity": new_turbidity,
                "raw_dissolved_oxygen": new_do,
                "true_turbidity": true_quality.turbidity,
                "true_dissolved_oxygen": true_quality.dissolved_oxygen,
            }
        )

        turbidity_threshold = self._sensor_thresholds.get("turbidity", float("inf"))
        dissolved_oxygen_threshold = self._sensor_thresholds.get("dissolved_oxygen", float("inf"))

        def _compute_sensor_measurement(
            provider: SensorModel,
        ) -> tuple[Dict[str, float], Dict[str, float]]:
            measurement = {
                "turbidity": true_quality.turbidity,
                "dissolved_oxygen": true_quality.dissolved_oxygen,
            }
            diag: Dict[str, float] = {}

            response = provider(
                step_index=self.step_index,
                timestamp=self.simulation_time,
                true_quality=true_quality,
                diagnostics=diagnostics.copy(),
            )
            if response:
                measurement["turbidity"] += response.get("turbidity", 0.0)
                measurement["dissolved_oxygen"] += response.get("dissolved_oxygen", 0.0)
                diag.update(
                    {
                        k: v
                        for k, v in response.items()
                        if k not in {"turbidity", "dissolved_oxygen"}
                    }
                )

            measurement["turbidity"] = max(0.0, measurement["turbidity"])
            measurement["dissolved_oxygen"] = max(0.0, measurement["dissolved_oxygen"])
            return measurement, diag

        if self._sensor_provider is not None:
            primary_measurement, primary_diag = _compute_sensor_measurement(self._sensor_provider)
        else:
            primary_measurement = {
                "turbidity": true_quality.turbidity,
                "dissolved_oxygen": true_quality.dissolved_oxygen,
            }
            primary_diag = {}

        secondary_measurement: Optional[Dict[str, float]] = None
        secondary_diag: Dict[str, float] = {}
        if self._redundant_sensor_provider is not None:
            secondary_measurement, secondary_diag = _compute_sensor_measurement(
                self._redundant_sensor_provider
            )

        primary_turbidity_error = abs(primary_measurement["turbidity"] - true_quality.turbidity)
        primary_do_error = abs(
            primary_measurement["dissolved_oxygen"] - true_quality.dissolved_oxygen
        )
        primary_fault = (
            primary_turbidity_error > turbidity_threshold or primary_do_error > dissolved_oxygen_threshold
        )

        secondary_turbidity_error = 0.0
        secondary_do_error = 0.0
        secondary_fault = False
        if secondary_measurement is not None:
            secondary_turbidity_error = abs(
                secondary_measurement["turbidity"] - true_quality.turbidity
            )
            secondary_do_error = abs(
                secondary_measurement["dissolved_oxygen"] - true_quality.dissolved_oxygen
            )
            secondary_fault = (
                secondary_turbidity_error > turbidity_threshold
                or secondary_do_error > dissolved_oxygen_threshold
            )

        fused_turbidity = primary_measurement["turbidity"]
        fused_do = primary_measurement["dissolved_oxygen"]
        redundant_active = 0.0

        if secondary_measurement is not None:
            if primary_fault and not secondary_fault:
                fused_turbidity = secondary_measurement["turbidity"]
                fused_do = secondary_measurement["dissolved_oxygen"]
                redundant_active = 1.0
            elif not primary_fault and not secondary_fault:
                primary_weight = self._redundant_weights["primary"]
                secondary_weight = self._redundant_weights["secondary"]
                weight_sum = primary_weight + secondary_weight
                if weight_sum > 0.0:
                    fused_turbidity = (
                        primary_measurement["turbidity"] * primary_weight
                        + secondary_measurement["turbidity"] * secondary_weight
                    ) / weight_sum
                    fused_do = (
                        primary_measurement["dissolved_oxygen"] * primary_weight
                        + secondary_measurement["dissolved_oxygen"] * secondary_weight
                    ) / weight_sum
            # If the secondary sensor is faulty or both sensors fault, rely on primary measurement.

        fused_turbidity = max(0.0, fused_turbidity)
        fused_do = max(0.0, fused_do)

        measured_quality = WaterQuality(
            timestamp=true_quality.timestamp,
            ph=true_quality.ph,
            turbidity=fused_turbidity,
            dissolved_oxygen=fused_do,
        )

        turbidity_error = abs(fused_turbidity - true_quality.turbidity)
        do_error = abs(fused_do - true_quality.dissolved_oxygen)
        turbidity_fault = float(turbidity_error > turbidity_threshold)
        do_fault = float(do_error > dissolved_oxygen_threshold)
        sensor_fault_detected = 1.0 if (turbidity_fault or do_fault) else 0.0
        secondary_fault_flag = float(secondary_fault) if secondary_measurement is not None else 0.0

        diagnostics.update(
            {
                "measured_turbidity": fused_turbidity,
                "measured_dissolved_oxygen": fused_do,
                "sensor_turbidity_error": turbidity_error,
                "sensor_do_error": do_error,
                "sensor_fault_detected": sensor_fault_detected,
                "sensor_turbidity_fault": turbidity_fault,
                "sensor_do_fault": do_fault,
                "primary_sensor_fault": float(primary_fault),
                "secondary_sensor_fault": secondary_fault_flag,
                "redundant_sensor_active": redundant_active,
                "primary_turbidity_error": primary_turbidity_error,
                "primary_do_error": primary_do_error,
            }
        )

        diagnostics.update(
            {
                "primary_sensor_turbidity": primary_measurement["turbidity"],
                "primary_sensor_dissolved_oxygen": primary_measurement["dissolved_oxygen"],
            }
        )

        if secondary_measurement is not None:
            diagnostics.update(
                {
                    "secondary_sensor_turbidity": secondary_measurement["turbidity"],
                    "secondary_sensor_dissolved_oxygen": secondary_measurement["dissolved_oxygen"],
                    "secondary_turbidity_error": secondary_turbidity_error,
                    "secondary_do_error": secondary_do_error,
                }
            )

        diagnostics.update(primary_diag)
        if secondary_diag:
            diagnostics.update({f"redundant_{k}": v for k, v in secondary_diag.items()})

        self.true_quality = true_quality
        self.current_quality = measured_quality
        self.last_diagnostics = diagnostics
        self.step_index += 1
        return self.current_quality
