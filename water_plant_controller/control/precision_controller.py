from dataclasses import dataclass
from typing import Optional, Dict

from water_plant_controller.control.pid_controller import PIDController


@dataclass
class ConstraintProfile:
    """
    Defines physical and economic constraints for an actuator.

    Attributes:
        minimum: Lower bound for the control output.
        maximum: Upper bound for the control output.
        ramp_rate: Maximum allowed change per step (absolute value). Optional.
        unit_cost: Cost per unit output (e.g., $/kg or kWh). Optional.
    """

    minimum: float = 0.0
    maximum: float = 100.0
    ramp_rate: Optional[float] = None
    unit_cost: Optional[float] = None

    def clamp(self, value: float, previous: float) -> float:
        """
        Apply min/max and ramp-rate limits to the candidate value.
        """

        constrained = max(self.minimum, min(self.maximum, value))
        if self.ramp_rate is not None:
            delta = constrained - previous
            if abs(delta) > self.ramp_rate:
                constrained = previous + self.ramp_rate * (1 if delta > 0 else -1)
        return constrained

    def cost(self, value: float) -> Optional[float]:
        """
        Compute the instantaneous economic cost for the given output value.
        """

        if self.unit_cost is None:
            return None
        return max(0.0, value) * self.unit_cost


class PrecisionPIDController:
    """
    PID controller with feed-forward compensation and actuator constraints.

    The feed-forward term can utilise disturbance diagnostics supplied by the
    simulator. ConstraintProfile enforces physical limits, ramp-rate and
    approximated economic cost for reporting.
    """

    def __init__(
        self,
        pid: PIDController,
        constraint: ConstraintProfile,
        feedforward_gain: float = 0.0,
        feedforward_key: Optional[str] = None,
    ) -> None:
        self._pid = pid
        self._constraint = constraint
        self._feedforward_gain = feedforward_gain
        self._feedforward_key = feedforward_key
        self._previous_output: float = constraint.minimum
        self.last_diagnostics: Dict[str, float] = {}

    def calculate(
        self,
        current_value: float,
        dt: float,
        disturbances: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Compute constrained control output.

        Args:
            current_value: Latest measurement value.
            dt: Time step between calls.
            disturbances: Optional diagnostics from the simulator (e.g.,
                "turbidity_adjustment") used for feed-forward compensation.
        """

        pid_output = self._pid.calculate(current_value, dt)

        feedforward_term = 0.0
        if self._feedforward_gain != 0.0 and disturbances and self._feedforward_key:
            feedforward_term = self._feedforward_gain * disturbances.get(
                self._feedforward_key, 0.0
            )

        unconstrained = pid_output + feedforward_term
        constrained = self._constraint.clamp(unconstrained, self._previous_output)
        demand_cost = self._constraint.cost(constrained)

        self.last_diagnostics = {
            "pid_output": pid_output,
            "feedforward_term": feedforward_term,
            "unconstrained_output": unconstrained,
            "final_output": constrained,
            "saturated": int(constrained != unconstrained),
        }
        if demand_cost is not None:
            self.last_diagnostics["instantaneous_cost"] = demand_cost

        self._previous_output = constrained
        return constrained

    def reset(self) -> None:
        """
        Reset PID internal state and controller history.
        """

        self._pid.reset()
        self._previous_output = self._constraint.minimum
        self.last_diagnostics = {}

    def apply_output_override(self, value: float) -> float:
        """
        Override the previously computed output after coordination logic.

        The value will be clamped against the actuator constraint, and the
        internal state is updated so subsequent `calculate` calls continue
        from the adjusted operating point.
        """

        constrained = self._constraint.clamp(value, self._previous_output)
        self._previous_output = constrained
        self.last_diagnostics["coordinated_output"] = constrained
        return constrained


@dataclass
class AdaptivePIDProfile:
    """
    Configuration for adaptive gain tuning.

    Attributes:
        kp_min/kp_max: Bounds for the proportional gain.
        ki_min/ki_max: Bounds for the integral gain.
        kp_learning_rate: Step used when increasing/decreasing Kp.
        ki_learning_rate: Step used when increasing/decreasing Ki.
        error_increase_threshold: Magnitude of error above which gains are increased.
        error_decrease_threshold: Magnitude of error below which gains are decreased.
    """

    kp_min: float = 0.01
    kp_max: float = 3.0
    ki_min: float = 0.0
    ki_max: float = 1.0
    kp_learning_rate: float = 0.05
    ki_learning_rate: float = 0.005
    error_increase_threshold: float = 1.0
    error_decrease_threshold: float = 0.2


class AdaptivePIDController(PrecisionPIDController):
    """
    Precision PID controller with simple self-tuning capability.

    The adaptation logic uses measurement error magnitude to adjust the
    proportional and integral gains within configured limits. Larger errors
    drive gains upward while sustained small errors reduce gains to limit
    overshoot and actuator effort.
    """

    def __init__(
        self,
        pid: PIDController,
        constraint: ConstraintProfile,
        adaptation: AdaptivePIDProfile,
        feedforward_gain: float = 0.0,
        feedforward_key: Optional[str] = None,
    ) -> None:
        super().__init__(
            pid=pid,
            constraint=constraint,
            feedforward_gain=feedforward_gain,
            feedforward_key=feedforward_key,
        )
        self._adaptation = adaptation

    def calculate(
        self,
        current_value: float,
        dt: float,
        disturbances: Optional[Dict[str, float]] = None,
    ) -> float:
        output = super().calculate(
            current_value=current_value,
            dt=dt,
            disturbances=disturbances,
        )

        error = self._compute_error(current_value)
        self._apply_adaptation(error)

        self.last_diagnostics.update(
            {
                "adaptive_kp": self._pid.Kp,
                "adaptive_ki": self._pid.Ki,
            }
        )

        return output

    def _compute_error(self, current_value: float) -> float:
        error = self._pid.setpoint - current_value
        if self._pid.reverse_acting:
            error = -error
        return error

    def _apply_adaptation(self, error: float) -> None:
        error_mag = abs(error)
        profile = self._adaptation

        if error_mag > profile.error_increase_threshold:
            self._pid.Kp = min(
                profile.kp_max,
                self._pid.Kp + profile.kp_learning_rate * error_mag,
            )
            self._pid.Ki = min(
                profile.ki_max,
                self._pid.Ki + profile.ki_learning_rate * error_mag,
            )
        elif error_mag < profile.error_decrease_threshold:
            self._pid.Kp = max(
                profile.kp_min,
                self._pid.Kp - profile.kp_learning_rate,
            )
            self._pid.Ki = max(
                profile.ki_min,
                self._pid.Ki - profile.ki_learning_rate,
            )
