from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from random import Random
from typing import Deque


@dataclass(frozen=True)
class SensorConfig:
    name: str
    unit: str
    tau_s: float = 1.0
    noise_std: float = 0.0
    drift_rate: float = 0.0
    dead_time_s: float = 0.0
    range_min: float = 0.0
    range_max: float = 100.0


@dataclass(frozen=True)
class ActuatorConfig:
    rate_limit: float = 5.0
    deadband: float = 0.01
    noise_std: float = 0.0
    lag_tau_s: float = 2.0
    min_val: float = 0.0
    max_val: float = 100.0


DEFAULT_SENSOR_CONFIGS = {
    "DO_aerobic": SensorConfig(
        name="DO_aerobic",
        unit="mg/L",
        tau_s=30.0,
        noise_std=0.005,
        drift_rate=0.002,
        dead_time_s=5.0,
        range_min=0.0,
        range_max=20.0,
    ),
    "pH": SensorConfig(
        name="pH",
        unit="pH",
        tau_s=10.0,
        noise_std=0.003,
        drift_rate=0.001,
        dead_time_s=2.0,
        range_min=4.0,
        range_max=10.0,
    ),
    "NTU": SensorConfig(
        name="Turbidity",
        unit="NTU",
        tau_s=15.0,
        noise_std=0.010,
        drift_rate=0.003,
        dead_time_s=8.0,
        range_min=0.0,
        range_max=200.0,
    ),
    "NH4": SensorConfig(
        name="NH4",
        unit="mg/L",
        tau_s=300.0,
        noise_std=0.020,
        drift_rate=0.005,
        dead_time_s=300.0,
        range_min=0.0,
        range_max=100.0,
    ),
}


class VirtualSensor:
    def __init__(self, config: SensorConfig, dt_s: float = 0.1, rng: Random | None = None):
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")
        if config.range_max <= config.range_min:
            raise ValueError("range_max must be greater than range_min")
        if config.tau_s < 0 or config.dead_time_s < 0:
            raise ValueError("tau_s and dead_time_s must be non-negative")

        self.config = config
        self.dt_s = float(dt_s)
        self.rng = rng or Random()
        self._delay_steps = int(round(config.dead_time_s / self.dt_s))
        self._delay_buffer: Deque[float] = deque()
        self._filtered_value = config.range_min
        self._drift = 0.0
        self._fault_mode = "none"
        self._fault_value: float | None = None
        self._fault_bias = 0.0
        self.reset(config.range_min)

    def reset(self, initial_value: float | None = None) -> None:
        value = self._clip(initial_value if initial_value is not None else self.config.range_min)
        self._filtered_value = value
        self._drift = 0.0
        self._delay_buffer = deque([value] * self._delay_steps, maxlen=self._delay_steps or None)

    def measure(self, true_value: float) -> float:
        if self._fault_mode == "stuck":
            stuck_value = self._fault_value if self._fault_value is not None else self._filtered_value
            return self._clip(stuck_value)

        delayed_value = self._apply_delay(true_value)
        filtered_value = self._apply_lag(delayed_value)

        noise_abs = self.config.noise_std * (self.config.range_max - self.config.range_min)
        noise = self.rng.gauss(0.0, noise_abs) if noise_abs else 0.0
        self._drift += self.config.drift_rate * self.dt_s / 3600.0

        measured = filtered_value + noise + self._drift
        if self._fault_mode == "bias":
            measured += self._fault_bias
        elif self._fault_mode == "dropout":
            dropout_value = self._fault_value if self._fault_value is not None else self.config.range_min
            return self._clip(dropout_value)

        return self._clip(measured)

    def inject_fault(self, mode: str, value: float | None = None, bias: float = 0.0) -> None:
        supported_modes = {"none", "stuck", "bias", "dropout"}
        if mode not in supported_modes:
            raise ValueError(f"Unsupported fault mode: {mode}")

        self._fault_mode = mode
        self._fault_value = value
        self._fault_bias = bias

    def clear_fault(self) -> None:
        self.inject_fault("none")

    def to_milliamps(self, value: float | None = None) -> float:
        current_value = self._filtered_value if value is None else value
        span = self.config.range_max - self.config.range_min
        ratio = (self._clip(current_value) - self.config.range_min) / span
        return 4.0 + 16.0 * ratio

    def _apply_delay(self, true_value: float) -> float:
        clipped_value = self._clip(true_value)
        if self._delay_steps <= 0:
            return clipped_value

        delayed_value = self._delay_buffer.popleft()
        self._delay_buffer.append(clipped_value)
        return delayed_value

    def _apply_lag(self, delayed_value: float) -> float:
        if self.config.tau_s == 0:
            self._filtered_value = delayed_value
            return self._filtered_value

        alpha = self.dt_s / (self.config.tau_s + self.dt_s)
        self._filtered_value = alpha * delayed_value + (1.0 - alpha) * self._filtered_value
        return self._filtered_value

    def _clip(self, value: float) -> float:
        return max(self.config.range_min, min(self.config.range_max, float(value)))


class VirtualActuator:
    def __init__(self, config: ActuatorConfig, dt_s: float = 0.1, rng: Random | None = None):
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")
        if config.max_val <= config.min_val:
            raise ValueError("max_val must be greater than min_val")
        if config.rate_limit < 0 or config.lag_tau_s < 0 or config.deadband < 0:
            raise ValueError("rate_limit, lag_tau_s, and deadband must be non-negative")

        self.config = config
        self.dt_s = float(dt_s)
        self.rng = rng or Random()
        self._command = config.min_val
        self._actual = config.min_val

    @property
    def command(self) -> float:
        return self._command

    @property
    def actual(self) -> float:
        return self._actual

    def set_command(self, command: float) -> None:
        candidate = self._clip(command)
        if abs(candidate - self._command) < self.config.deadband:
            return
        self._command = candidate

    def set_command_from_milliamps(self, current_ma: float) -> None:
        if current_ma < 4.0 or current_ma > 20.0:
            raise ValueError("current_ma must be within 4-20mA")
        span = self.config.max_val - self.config.min_val
        ratio = (current_ma - 4.0) / 16.0
        self.set_command(self.config.min_val + ratio * span)

    def step(self) -> float:
        if self.config.lag_tau_s == 0:
            desired = self._command
        else:
            alpha = self.dt_s / (self.config.lag_tau_s + self.dt_s)
            desired = alpha * self._command + (1.0 - alpha) * self._actual

        noise_scale = max(abs(desired), 1.0)
        if self.config.noise_std:
            desired += self.rng.gauss(0.0, self.config.noise_std * noise_scale)

        max_delta = self.config.rate_limit * self.dt_s
        delta = desired - self._actual
        if delta > max_delta:
            desired = self._actual + max_delta
        elif delta < -max_delta:
            desired = self._actual - max_delta

        self._actual = self._clip(desired)
        return self._actual

    def to_milliamps(self, value: float | None = None) -> float:
        current_value = self._actual if value is None else value
        span = self.config.max_val - self.config.min_val
        ratio = (self._clip(current_value) - self.config.min_val) / span
        return 4.0 + 16.0 * ratio

    def _clip(self, value: float) -> float:
        return max(self.config.min_val, min(self.config.max_val, float(value)))
