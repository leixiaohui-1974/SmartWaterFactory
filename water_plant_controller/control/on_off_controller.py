class OnOffController:
    """
    A simple On-Off (or bang-bang) controller.
    This controller switches the output to its maximum or minimum value
    based on whether the measured value is above or below the setpoint.
    """

    def __init__(self, setpoint: float, reverse_acting: bool = False):
        """
        Initializes the On-Off controller.

        :param setpoint: The target value for the controlled variable.
        :param reverse_acting: If True, the controller is reverse-acting.
                               (e.g., for cooling or turbidity reduction).
        """
        self.setpoint = setpoint
        self.reverse_acting = reverse_acting
        self.output_min = 0.0
        self.output_max = 1.0  # Default to a 0-1 range

    def calculate(self, current_value: float) -> float:
        """
        Calculates the control variable output.

        :param current_value: The current measured value of the process variable.
        :return: The calculated control output (either min or max).
        """
        error = self.setpoint - current_value

        # Invert error for reverse-acting control
        if self.reverse_acting:
            error = -error

        if error > 0:
            return self.output_max
        else:
            return self.output_min

    def set_output_limits(self, min_val: float, max_val: float):
        """
        Sets the minimum and maximum limits for the controller's output.

        :param min_val: The minimum output value (e.g., 0 for 'off').
        :param max_val: The maximum output value (e.g., 100 for 'on').
        """
        if min_val >= max_val:
            raise ValueError("min_val must be less than max_val.")
        self.output_min = min_val
        self.output_max = max_val

    def reset(self):
        """
        Resets the controller's state. (No state to reset for this controller).
        """
        pass
