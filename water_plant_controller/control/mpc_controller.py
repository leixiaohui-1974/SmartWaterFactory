from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable

import numpy as np


@dataclass
class LinearisedProcessModel:
    """
    Simple first-order-plus-disturbance model used by the MPC controller.

    Attributes:
        a: State retention factor (0-1 for stable processes).
        b: Control gain translating actuator effort to state change.
        bias: Constant bias/disturbance term added each step.
    """

    a: float
    b: float
    bias: float = 0.0

    def predict(self, state: float, control: float) -> float:
        """Return the next state using the linearised model."""

        return self.a * state + self.b * control + self.bias


@dataclass
class ReliabilityAwareConstraints:
    """
    Constraints applied to the MPC controller output.

    Attributes:
        minimum: Lower bound on the control action.
        maximum: Upper bound on the control action.
        ramp_limit: Maximum allowed change per step (absolute value).
    """

    minimum: float
    maximum: float
    ramp_limit: float | None = None

    def clamp(self, value: float, previous: float) -> float:
        """Apply bounds and optional ramp rate."""

        value = max(self.minimum, min(self.maximum, value))
        if self.ramp_limit is not None:
            delta = value - previous
            if abs(delta) > self.ramp_limit:
                value = previous + np.sign(delta) * self.ramp_limit
        return value


@dataclass
class MPCFaultTolerantController:
    """
    Lightweight MPC controller with sensor reliability awareness.

    The controller assumes a linearised process model and searches a discrete
    control grid to minimise a quadratic cost function. Reliability data from
    the sensor monitor is used to bias the optimisation toward conservative
    actions when the measurement credibility deteriorates.
    """

    setpoint: float
    model: LinearisedProcessModel
    constraints: ReliabilityAwareConstraints
    horizon: int = 6
    control_weight: float = 0.12
    state_weight: float = 1.0
    reliability_penalty: float = 60.0
    candidate_grid: Iterable[float] | None = None
    last_output: float = field(default=0.0, init=False)
    last_diagnostics: Dict[str, float] = field(default_factory=dict, init=False)
    _reliability: float = field(default=1.0, init=False)
    _bias_estimate: float = field(default=0.0, init=False)

    def update_sensor_health(self, reliability: float, bias_estimate: float) -> None:
        """
        Update the sensor reliability metadata used by the optimiser.

        Args:
            reliability: Credibility factor in [0, 1]; higher values indicate
                trustworthy measurements.
            bias_estimate: Bias value returned by the monitoring filter.
        """

        self._reliability = float(np.clip(reliability, 0.0, 1.0))
        self._bias_estimate = float(bias_estimate)

    def calculate(self, measurement: float) -> float:
        """
        Compute the control action using reliability-aware MPC.

        The optimisation searches across a finite candidate grid. When the
        sensor reliability decreases, the cost penalises aggressive dosing to
        prevent over-compensation.
        """

        soft_measurement = measurement - (1.0 - self._reliability) * self._bias_estimate
        soft_measurement = max(0.0, soft_measurement)

        grid = self._build_candidate_grid()

        # Enforce ramp constraints by pruning the grid; always consider the last output.
        feasible_controls = [
            u for u in grid if self._is_within_ramp(u, self.last_output)
        ] or [self.last_output]

        best_control = feasible_controls[0]
        best_cost = float("inf")
        stage_errors = []

        for control in feasible_controls:
            predicted = self._simulate_horizon(soft_measurement, control)
            cost = self._evaluate_cost(predicted, control)
            if cost < best_cost:
                best_cost = cost
                best_control = control
                stage_errors = [state - self.setpoint for state in predicted]

        final_output = self.constraints.clamp(best_control, self.last_output)
        self.last_output = final_output
        self.last_diagnostics = {
            "soft_measurement": soft_measurement,
            "selected_control": final_output,
            "candidate_cost": best_cost,
            "reliability": self._reliability,
            "bias_estimate": self._bias_estimate,
        }
        if stage_errors:
            self.last_diagnostics["terminal_error"] = stage_errors[-1]
            self.last_diagnostics["max_abs_error"] = max(abs(e) for e in stage_errors)

        return final_output

    def _simulate_horizon(self, state: float, control: float) -> list[float]:
        predicted = []
        current = state
        for _ in range(self.horizon):
            current = self.model.predict(current, control)
            predicted.append(current)
        return predicted

    def _evaluate_cost(self, predicted: list[float], control: float) -> float:
        state_cost = sum((x - self.setpoint) ** 2 for x in predicted) * self.state_weight
        control_cost = self.control_weight * control * control
        reliability_cost = (1.0 - self._reliability) * self.reliability_penalty * control * control
        return state_cost + control_cost + reliability_cost

    def _is_within_ramp(self, candidate: float, previous: float) -> bool:
        if self.constraints.ramp_limit is None:
            return True
        return abs(candidate - previous) <= self.constraints.ramp_limit + 1e-6

    def _build_candidate_grid(self) -> np.ndarray:
        if self.candidate_grid is not None:
            unique = np.unique(np.asarray(list(self.candidate_grid), dtype=float))
            return unique

        minimum = float(self.constraints.minimum)
        maximum = float(self.constraints.maximum)
        if maximum <= minimum:
            return np.asarray([minimum])

        low_band = np.linspace(minimum, min(maximum, minimum + 4.0), 25)
        if maximum > minimum + 4.0:
            high_band = np.linspace(minimum + 4.0, maximum, 12)
            grid = np.unique(np.concatenate((low_band, high_band)))
        else:
            grid = low_band
        return grid
