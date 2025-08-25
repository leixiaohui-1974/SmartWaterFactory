class PIDController:
    """
    A generic PID (Proportional-Integral-Derivative) controller.
    """

    def __init__(self, Kp: float, Ki: float, Kd: float, setpoint: float, reverse_acting: bool = False):
        """
        Initializes the PID controller.
        :param Kp: Proportional gain.
        :param Ki: Integral gain.
        :param Kd: Derivative gain.
        :param setpoint: The target value for the controlled variable.
        :param reverse_acting: If True, the controller is reverse-acting. Defaults to False.
        """
        if not all(isinstance(k, (int, float)) for k in [Kp, Ki, Kd]):
            raise ValueError("PID gains must be numeric.")

        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.reverse_acting = reverse_acting

        self._previous_error = 0.0
        self._integral = 0.0

        # Default output limits can be changed via set_output_limits
        self.output_min = 0.0
        self.output_max = float('inf')
        self.integral_min = -float('inf')
        self.integral_max = float('inf')

    def calculate(self, current_value: float, dt: float = 1.0) -> float:
        """
        Calculates the control variable output.
        :param current_value: The current measured value of the process variable.
        :param dt: The time step duration since the last calculation. Defaults to 1.0.
        :return: The calculated control output.
        """
        error = self.setpoint - current_value
        if self.reverse_acting:
            error = -error

        # Proportional term
        p_term = self.Kp * error

        # Integral term with anti-windup
        self._integral += self.Ki * error * dt
        # Clamp the integral term to prevent windup
        if self.integral_min is not None and self.integral_max is not None:
            self._integral = max(self.integral_min, min(self._integral, self.integral_max))
        i_term = self._integral

        # Derivative term
        if dt > 0:
            derivative = (error - self._previous_error) / dt
        else:
            derivative = 0.0
        d_term = self.Kd * derivative

        # Calculate total output
        output = p_term + i_term + d_term

        # Clamp the final output to its limits
        if self.output_min is not None and self.output_max is not None:
            output = max(self.output_min, min(output, self.output_max))

        # Update state for the next iteration
        self._previous_error = error

        return output

    def set_integral_limits(self, min_val: float, max_val: float):
        """
        Sets the minimum and maximum limits for the integral term.
        This is a key part of anti-windup.
        :param min_val: The minimum value of the integral term.
        :param max_val: The maximum value of the integral term.
        """
        if min_val >= max_val:
            raise ValueError("min_val must be less than max_val.")
        self.integral_min = min_val
        self.integral_max = max_val

    def set_output_limits(self, min_val: float, max_val: float):
        """
        Sets the minimum and maximum limits for the controller's output.
        This is useful for preventing the control variable from exceeding physical limits.
        :param min_val: The minimum output value.
        :param max_val: The maximum output value.
        """
        if min_val >= max_val:
            raise ValueError("min_val must be less than max_val.")
        self.output_min = min_val
        self.output_max = max_val

    def reset(self):
        """
        Resets the controller's internal state (integral and previous error).
        """
        self._previous_error = 0.0
        self._integral = 0.0
