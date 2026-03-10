from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import sin, tau
from random import Random
from typing import Any, Dict, Mapping

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator

from .virtual_io import ActuatorConfig, SensorConfig, VirtualActuator, VirtualSensor


@dataclass(frozen=True)
class HILScenario:
    name: str
    turbidity_offset: float = 0.0
    dissolved_oxygen_offset: float = 0.0
    turbidity_wave_amplitude: float = 0.0
    dissolved_oxygen_wave_amplitude: float = 0.0
    wave_period_steps: int = 20
    step_changes: Mapping[int, Mapping[str, float]] = field(default_factory=dict)

    def disturbance_for_step(self, step_index: int) -> Dict[str, float]:
        disturbance = {
            "turbidity": self.turbidity_offset,
            "dissolved_oxygen": self.dissolved_oxygen_offset,
        }

        if self.wave_period_steps > 0:
            phase = tau * (step_index % self.wave_period_steps) / self.wave_period_steps
            disturbance["turbidity"] += self.turbidity_wave_amplitude * sin(phase)
            disturbance["dissolved_oxygen"] += self.dissolved_oxygen_wave_amplitude * sin(phase)

        step_override = self.step_changes.get(step_index)
        if step_override:
            disturbance.update(step_override)

        disturbance["scenario_name"] = self.name
        return disturbance


DEFAULT_HIL_SCENARIOS: Dict[str, HILScenario] = {
    "steady": HILScenario(name="steady"),
    "turbidity_spike": HILScenario(
        name="turbidity_spike",
        step_changes={0: {"turbidity": 12.0}, 1: {"turbidity": 8.0}, 2: {"turbidity": 4.0}},
    ),
    "oxygen_sag": HILScenario(
        name="oxygen_sag",
        step_changes={0: {"dissolved_oxygen": -1.0}, 1: {"dissolved_oxygen": -0.8}},
    ),
    "cyclic_load": HILScenario(
        name="cyclic_load",
        turbidity_wave_amplitude=2.5,
        dissolved_oxygen_wave_amplitude=-0.3,
        wave_period_steps=12,
    ),
}


@dataclass(frozen=True)
class HILSnapshot:
    step_index: int
    timestamp: datetime
    scenario: str
    true_quality: WaterQuality
    measured_quality: WaterQuality
    sensor_outputs: Dict[str, float]
    sensor_currents_ma: Dict[str, float]
    actuator_outputs: Dict[str, float]
    actuator_currents_ma: Dict[str, float]
    diagnostics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "timestamp": self.timestamp.isoformat(),
            "scenario": self.scenario,
            "true_quality": {
                "timestamp": self.true_quality.timestamp.isoformat(),
                "ph": self.true_quality.ph,
                "turbidity": self.true_quality.turbidity,
                "dissolved_oxygen": self.true_quality.dissolved_oxygen,
            },
            "measured_quality": {
                "timestamp": self.measured_quality.timestamp.isoformat(),
                "ph": self.measured_quality.ph,
                "turbidity": self.measured_quality.turbidity,
                "dissolved_oxygen": self.measured_quality.dissolved_oxygen,
            },
            "sensor_outputs": dict(self.sensor_outputs),
            "sensor_currents_ma": dict(self.sensor_currents_ma),
            "actuator_outputs": dict(self.actuator_outputs),
            "actuator_currents_ma": dict(self.actuator_currents_ma),
            "diagnostics": dict(self.diagnostics),
        }


class HILSimulator:
    def __init__(
        self,
        initial_quality: WaterQuality,
        *,
        dt_s: float = 1.0,
        scenario: str = "steady",
        plant_config: Dict[str, Any] | None = None,
        sensor_configs: Mapping[str, SensorConfig] | None = None,
        actuator_configs: Mapping[str, ActuatorConfig] | None = None,
        random_seed: int | None = None,
    ) -> None:
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")

        self.dt_s = float(dt_s)
        self._rng = Random(random_seed)
        self.scenarios = dict(DEFAULT_HIL_SCENARIOS)
        if scenario not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")

        self._active_scenario = scenario
        self._scenario_step_index = 0

        self.plant = PlantSimulator(
            initial_quality,
            config=plant_config,
            disturbance_provider=self._disturbance_provider,
        )
        self.sensors = self._build_sensors(sensor_configs)
        self.actuators = self._build_actuators(actuator_configs)

    @property
    def active_scenario(self) -> str:
        return self._active_scenario

    def register_scenario(self, scenario: HILScenario) -> None:
        self.scenarios[scenario.name] = scenario

    def set_scenario(self, scenario_name: str) -> None:
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        self._active_scenario = scenario_name
        self._scenario_step_index = 0

    def set_control_command(self, actuator_name: str, value: float) -> None:
        self._require_actuator(actuator_name).set_command(value)

    def set_control_command_from_milliamps(self, actuator_name: str, current_ma: float) -> None:
        self._require_actuator(actuator_name).set_command_from_milliamps(current_ma)

    def inject_sensor_fault(
        self,
        sensor_name: str,
        mode: str,
        *,
        value: float | None = None,
        bias: float = 0.0,
    ) -> None:
        self._require_sensor(sensor_name).inject_fault(mode, value=value, bias=bias)

    def clear_sensor_fault(self, sensor_name: str) -> None:
        self._require_sensor(sensor_name).clear_fault()

    def step(self) -> HILSnapshot:
        actuator_outputs = {
            name: actuator.step() for name, actuator in self.actuators.items()
        }
        actuator_currents = {
            name: self.actuators[name].to_milliamps(value)
            for name, value in actuator_outputs.items()
        }

        measured_by_plant = self.plant.step(
            coagulant_dose=actuator_outputs["coagulant_dose"],
            aeration_rate=actuator_outputs["aeration_rate"],
        )
        true_quality = self.plant.true_quality

        sensor_outputs = {
            "ph": self.sensors["ph"].measure(true_quality.ph),
            "turbidity": self.sensors["turbidity"].measure(true_quality.turbidity),
            "dissolved_oxygen": self.sensors["dissolved_oxygen"].measure(
                true_quality.dissolved_oxygen
            ),
        }
        sensor_currents = {
            name: self.sensors[name].to_milliamps(value)
            for name, value in sensor_outputs.items()
        }

        measured_quality = WaterQuality(
            timestamp=measured_by_plant.timestamp,
            ph=sensor_outputs["ph"],
            turbidity=sensor_outputs["turbidity"],
            dissolved_oxygen=sensor_outputs["dissolved_oxygen"],
        )

        diagnostics = dict(self.plant.last_diagnostics)
        diagnostics.update(
            {
                "scenario_name": self._active_scenario,
                "scenario_step_index": self._scenario_step_index,
                "true_ph": true_quality.ph,
                "true_turbidity": true_quality.turbidity,
                "true_dissolved_oxygen": true_quality.dissolved_oxygen,
            }
        )

        snapshot = HILSnapshot(
            step_index=self.plant.step_index,
            timestamp=true_quality.timestamp,
            scenario=self._active_scenario,
            true_quality=true_quality,
            measured_quality=measured_quality,
            sensor_outputs=sensor_outputs,
            sensor_currents_ma=sensor_currents,
            actuator_outputs=actuator_outputs,
            actuator_currents_ma=actuator_currents,
            diagnostics=diagnostics,
        )
        self._scenario_step_index += 1
        return snapshot

    def run_steps(self, num_steps: int) -> list[HILSnapshot]:
        if num_steps < 0:
            raise ValueError("num_steps must be non-negative")
        return [self.step() for _ in range(num_steps)]

    def _build_sensors(
        self,
        sensor_configs: Mapping[str, SensorConfig] | None,
    ) -> Dict[str, VirtualSensor]:
        configs = dict(sensor_configs or self._default_sensor_configs())
        return {
            name: VirtualSensor(config, dt_s=self.dt_s, rng=Random(self._rng.random()))
            for name, config in configs.items()
        }

    def _build_actuators(
        self,
        actuator_configs: Mapping[str, ActuatorConfig] | None,
    ) -> Dict[str, VirtualActuator]:
        configs = dict(actuator_configs or self._default_actuator_configs())
        return {
            name: VirtualActuator(config, dt_s=self.dt_s, rng=Random(self._rng.random()))
            for name, config in configs.items()
        }

    def _disturbance_provider(
        self,
        *,
        step_index: int,
        timestamp: datetime,
        quality: WaterQuality,
        inputs: Dict[str, float],
    ) -> Dict[str, float]:
        del timestamp, quality, inputs
        scenario = self.scenarios[self._active_scenario]
        return scenario.disturbance_for_step(self._scenario_step_index)

    def _require_sensor(self, sensor_name: str) -> VirtualSensor:
        try:
            return self.sensors[sensor_name]
        except KeyError as exc:
            raise KeyError(f"Unknown sensor: {sensor_name}") from exc

    def _require_actuator(self, actuator_name: str) -> VirtualActuator:
        try:
            return self.actuators[actuator_name]
        except KeyError as exc:
            raise KeyError(f"Unknown actuator: {actuator_name}") from exc

    @staticmethod
    def _default_sensor_configs() -> Dict[str, SensorConfig]:
        return {
            "ph": SensorConfig(
                name="pH",
                unit="pH",
                tau_s=2.0,
                noise_std=0.0,
                drift_rate=0.0,
                dead_time_s=0.0,
                range_min=0.0,
                range_max=14.0,
            ),
            "turbidity": SensorConfig(
                name="Turbidity",
                unit="NTU",
                tau_s=1.0,
                noise_std=0.0,
                drift_rate=0.0,
                dead_time_s=0.0,
                range_min=0.0,
                range_max=200.0,
            ),
            "dissolved_oxygen": SensorConfig(
                name="DO",
                unit="mg/L",
                tau_s=1.0,
                noise_std=0.0,
                drift_rate=0.0,
                dead_time_s=0.0,
                range_min=0.0,
                range_max=20.0,
            ),
        }

    @staticmethod
    def _default_actuator_configs() -> Dict[str, ActuatorConfig]:
        return {
            "coagulant_dose": ActuatorConfig(
                rate_limit=20.0,
                deadband=0.0,
                noise_std=0.0,
                lag_tau_s=0.0,
                min_val=0.0,
                max_val=20.0,
            ),
            "aeration_rate": ActuatorConfig(
                rate_limit=20.0,
                deadband=0.0,
                noise_std=0.0,
                lag_tau_s=0.0,
                min_val=0.0,
                max_val=20.0,
            ),
        }
