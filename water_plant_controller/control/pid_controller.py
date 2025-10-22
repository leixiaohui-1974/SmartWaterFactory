from typing import Optional
import math


class PIDController:
    """
    Generic proportional–integral–derivative (PID) controller.

    The controller computes an output based on the error between the desired
    setpoint and the measured process value. Anti-windup safeguards are
    included for both the integral and output ranges.
    """

    def __init__(
        self,
        Kp: float,
        Ki: float,
        Kd: float,
        setpoint: float,
        reverse_acting: bool = False,
    ) -> None:
        """
        Initialise the controller with the supplied gains and setpoint.

        Args:
            Kp: Proportional gain (non-negative).
            Ki: Integral gain (non-negative).
            Kd: Derivative gain (non-negative).
            setpoint: Target value the controller should maintain.
            reverse_acting: Whether the controller should act in reverse
                (useful for cooling or turbidity reduction loops).

        Raises:
            ValueError: If any of the gains are not numeric or are negative.
        """

        if not all(isinstance(k, (int, float)) for k in (Kp, Ki, Kd)):
            raise ValueError("PID gains must be numeric values.")

        if Kp < 0 or Ki < 0 or Kd < 0:
            raise ValueError("PID gains must be non-negative.")

        self.Kp: float = float(Kp)
        self.Ki: float = float(Ki)
        self.Kd: float = float(Kd)
        self.setpoint: float = float(setpoint)
        self.reverse_acting: bool = reverse_acting

        self._previous_error: float = 0.0
        self._integral: float = 0.0

        self.output_min: Optional[float] = 0.0
        self.output_max: Optional[float] = float("inf")
        self.integral_min: Optional[float] = -float("inf")
        self.integral_max: Optional[float] = float("inf")

    def calculate(self, current_value: float, dt: float = 1.0) -> float:
        """
        Compute the control output for the supplied process value.

        Args:
            current_value: Latest measured value of the process.
            dt: Time step since the previous call.

        Returns:
            Control signal after applying PID logic and saturation limits.

        Raises:
            TypeError: If `current_value` or `dt` is not numeric.
            ValueError: If invalid (NaN/inf) numbers are supplied or `dt` < 0.
        """

        if not isinstance(current_value, (int, float)):
            raise TypeError(
                f"current_value must be numeric, received {type(current_value).__name__}"
            )
        if not isinstance(dt, (int, float)):
            raise TypeError(f"dt must be numeric, received {type(dt).__name__}")

        if dt < 0:
            raise ValueError(f"dt must be non-negative, received {dt}")

        if math.isnan(current_value) or math.isinf(current_value):
            raise ValueError(f"current_value contains an invalid number: {current_value}")
        if math.isnan(dt) or math.isinf(dt):
            raise ValueError(f"dt contains an invalid number: {dt}")

        error = self.setpoint - current_value
        if self.reverse_acting:
            error = -error

        p_term = self.Kp * error

        self._integral += self.Ki * error * dt
        if self.integral_min is not None and self.integral_max is not None:
            self._integral = max(self.integral_min, min(self._integral, self.integral_max))
        i_term = self._integral

        derivative = (error - self._previous_error) / dt if dt > 0 else 0.0
        d_term = self.Kd * derivative

        output = p_term + i_term + d_term
        if self.output_min is not None and self.output_max is not None:
            output = max(self.output_min, min(output, self.output_max))

        self._previous_error = error
        return output

    def set_integral_limits(self, min_val: float, max_val: float) -> None:
        """
        Constrain the integral term to avoid integral wind-up.

        Raises:
            ValueError: If `min_val` is not less than `max_val`.
        """

        if min_val >= max_val:
            raise ValueError("Integral minimum must be less than the maximum.")
        self.integral_min = min_val
        self.integral_max = max_val

    def set_output_limits(self, min_val: float, max_val: float) -> None:
        """
        Clamp the controller output to a finite range.

        Raises:
            ValueError: If `min_val` is not less than `max_val`.
        """

        if min_val >= max_val:
            raise ValueError("Output minimum must be less than the maximum.")
        self.output_min = min_val
        self.output_max = max_val

    def reset(self) -> None:
        """Clear integral accumulation and derivative history."""

        self._previous_error = 0.0
        self._integral = 0.0
