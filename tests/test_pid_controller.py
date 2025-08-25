import unittest
import sys
import os

# Add the project root to the Python path to allow importing from water_plant_controller
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.control.pid_controller import PIDController

class TestPIDController(unittest.TestCase):
    """Unit tests for the PIDController class."""

    def test_proportional_only(self):
        """Test the proportional term works as expected."""
        # Kp=0.5, Ki=0, Kd=0. Setpoint=100.
        controller = PIDController(Kp=0.5, Ki=0, Kd=0, setpoint=100)
        controller.set_output_limits(-100, 100)  # Allow negative output for testing
        # Current value is 50, error is 50. Output should be 0.5 * 50 = 25.
        output = controller.calculate(current_value=50)
        self.assertAlmostEqual(output, 25.0)
        # Current value is 100, error is 0. Output should be 0.
        output = controller.calculate(current_value=100)
        self.assertAlmostEqual(output, 0.0)
        # Current value is 120, error is -20. Output should be 0.5 * -20 = -10.
        output = controller.calculate(current_value=120)
        self.assertAlmostEqual(output, -10.0)

    def test_integral_action(self):
        """Test the integral term accumulates error over time."""
        # Kp=0, Ki=0.1, Kd=0. Setpoint=100.
        controller = PIDController(Kp=0, Ki=0.1, Kd=0, setpoint=100)
        # Step 1: current=90, error=10. Integral = 0 + 0.1*10*1 = 1. Output = 1.
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 1.0)
        # Step 2: current=90, error=10. Integral = 1 + 0.1*10*1 = 2. Output = 2.
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 2.0)
        # Step 3: current=110, error=-10. Integral = 2 + 0.1*(-10)*1 = 1. Output = 1.
        output = controller.calculate(current_value=110)
        self.assertAlmostEqual(output, 1.0)

    def test_derivative_action(self):
        """Test the derivative term responds to the rate of change of the error."""
        # Kp=0, Ki=0, Kd=0.2. Setpoint=100.
        controller = PIDController(Kp=0, Ki=0, Kd=0.2, setpoint=100)
        controller.set_output_limits(-100, 100)  # Allow negative output for testing
        # Step 1: current=90, error=10. prev_error=0. derivative=(10-0)/1=10. output=0.2*10=2
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 2.0)
        # Step 2: current=95, error=5. prev_error=10. derivative=(5-10)/1=-5. output=0.2*(-5)=-1
        output = controller.calculate(current_value=95)
        self.assertAlmostEqual(output, -1.0)

    def test_output_clamping(self):
        """Test that the output is correctly clamped within the defined limits."""
        controller = PIDController(Kp=10, Ki=0, Kd=0, setpoint=100)
        controller.set_output_limits(0, 50)
        # Error is 10, P term is 100, but should be clamped to 50.
        output = controller.calculate(current_value=90)
        self.assertAlmostEqual(output, 50.0)
        # Error is -10, P term is -100, but should be clamped to 0.
        controller.set_output_limits(-10, 10)
        output = controller.calculate(current_value=110)
        self.assertAlmostEqual(output, -10.0)

    def test_reset(self):
        """Test that the reset method clears the controller's state."""
        controller = PIDController(Kp=0.5, Ki=0.1, Kd=0.2, setpoint=100)
        controller.calculate(current_value=90) # error=10
        self.assertNotEqual(controller._integral, 0)
        self.assertNotEqual(controller._previous_error, 0)

        controller.reset()
        self.assertEqual(controller._integral, 0)
        self.assertEqual(controller._previous_error, 0)

    def test_reverse_acting(self):
        """Test the reverse_acting flag correctly inverts the error."""
        # Direct acting (default)
        controller_direct = PIDController(Kp=1, Ki=0, Kd=0, setpoint=100)
        controller_direct.set_output_limits(-100, 100)
        # current=120, error=-20, output=-20
        output_direct = controller_direct.calculate(current_value=120)
        self.assertAlmostEqual(output_direct, -20.0)

        # Reverse acting
        controller_reverse = PIDController(Kp=1, Ki=0, Kd=0, setpoint=100, reverse_acting=True)
        controller_reverse.set_output_limits(-100, 100)
        # current=120, error=-20, reversed_error=20, output=20
        output_reverse = controller_reverse.calculate(current_value=120)
        self.assertAlmostEqual(output_reverse, 20.0)

if __name__ == '__main__':
    unittest.main()
