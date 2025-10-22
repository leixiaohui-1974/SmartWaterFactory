import math


class OnOffController:
    """
    Simple bang-bang (on/off) controller.

    The controller switches between two output levels depending on whether the
    process variable is above or below the setpoint. The behaviour can be
    inverted with the ``reverse_acting`` flag.
    """

    def __init__(self, setpoint: float, reverse_acting: bool = False) -> None:
        """
        Args:
            setpoint: Target value for the controlled variable.
            reverse_acting: If ``True`` the controller outputs the maximum when
                the measurement exceeds the setpoint (useful for cooling or
                turbidity reduction scenarios).
        """

        self.setpoint: float = float(setpoint)
        self.reverse_acting: bool = reverse_acting
        self.output_min: float = 0.0
        self.output_max: float = 1.0

    def calculate(self, current_value: float) -> float:
        """
        Return either ``output_min`` or ``output_max`` based on the process value.

        Raises:
            TypeError: If ``current_value`` is not numeric.
            ValueError: If ``current_value`` is NaN or infinite.
        """

        if not isinstance(current_value, (int, float)):
            raise TypeError(
                f"current_value must be numeric, received {type(current_value).__name__}"
            )

        if math.isnan(current_value) or math.isinf(current_value):
            raise ValueError(f"current_value contains an invalid number: {current_value}")

        error = self.setpoint - current_value
        if self.reverse_acting:
            error = -error

        return self.output_max if error > 0 else self.output_min

    def set_output_limits(self, min_val: float, max_val: float) -> None:
        """
        Configure the minimum and maximum output produced by the controller.

        Raises:
            ValueError: If ``min_val`` is not less than ``max_val``.
        """

        if min_val >= max_val:
            raise ValueError("Output minimum must be less than the maximum.")
        self.output_min = min_val
        self.output_max = max_val

    def reset(self) -> None:
        """Provided for interface compatibility; the controller has no internal state."""

        return None
