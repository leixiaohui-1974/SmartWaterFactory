import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from config.settings import PID_GAINS

class TestIntegration(unittest.TestCase):
    """
    Integration tests to ensure the controller and simulator work together.
    """

    def test_closed_loop_control(self):
        """
        Test a full closed-loop control scenario where PID controllers
        drive the plant simulator towards setpoints.
        """
        # 1. Initialization
        initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=25.0,  # High initial turbidity
            dissolved_oxygen=4.0  # Low initial DO
        )
        simulator = PlantSimulator(initial_quality)

        # 2. Controller Setup
        turbidity_setpoint = 5.0
        do_setpoint = 8.5

        dosing_gains = PID_GAINS["dosing_controller"]
        aeration_gains = PID_GAINS["aeration_controller"]

        dosing_controller = PIDController(
            Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
            setpoint=turbidity_setpoint, reverse_acting=True
        )
        dosing_controller.set_output_limits(0, 10)
        dosing_controller.set_integral_limits(-5, 5)

        aeration_controller = PIDController(
            Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
            setpoint=do_setpoint
        )
        aeration_controller.set_output_limits(0, 20)
        aeration_controller.set_integral_limits(-15, 15)

        # 3. Simulation Loop
        simulation_steps = 300
        for _ in range(simulation_steps):
            current_quality = simulator.current_quality
            coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
            aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)
            simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

        # 4. Assertions
        final_quality = simulator.current_quality
        self.assertAlmostEqual(final_quality.turbidity, turbidity_setpoint, delta=1.0)
        self.assertAlmostEqual(final_quality.dissolved_oxygen, do_setpoint, delta=0.5)

    def test_pid_anti_windup(self):
        """
        Tests that the integral term does not grow uncontrollably when the output is saturated.
        """
        # High proportional gain to force saturation
        controller = PIDController(Kp=50, Ki=0.1, Kd=0, setpoint=100)
        controller.set_output_limits(0, 10) # Low output limit
        controller.set_integral_limits(-5, 5) # Integral limits

        # Keep feeding a large error to the controller
        for _ in range(100):
            output = controller.calculate(current_value=0)
            self.assertAlmostEqual(output, 10) # Should be saturated at max output

        # The integral term should be clamped at its max limit, not infinity
        self.assertAlmostEqual(controller._integral, 5)

if __name__ == '__main__':
    unittest.main()
