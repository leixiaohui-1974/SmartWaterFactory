import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController

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
        # Controller for turbidity (dosing)
        turbidity_setpoint = 5.0
        # Note: We want to drive turbidity DOWN. This is a reverse-acting loop.
        # Tuning gains to be less aggressive to avoid overshoot.
        dosing_controller = PIDController(Kp=0.1, Ki=0.01, Kd=0.1, setpoint=turbidity_setpoint, reverse_acting=True)
        dosing_controller.set_output_limits(0, 10)  # Max dose of 10

        # Controller for Dissolved Oxygen (aeration)
        do_setpoint = 8.5
        aeration_controller = PIDController(Kp=0.8, Ki=0.1, Kd=0.1, setpoint=do_setpoint)
        aeration_controller.set_output_limits(0, 20)  # Max aeration rate of 20

        # 3. Simulation Loop
        simulation_steps = 300  # Increased steps to allow settling
        for _ in range(simulation_steps):
            current_quality = simulator.current_quality

            # Calculate control actions
            coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
            aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)

            # Apply actions to the simulator
            simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

        # 4. Assertions
        final_quality = simulator.current_quality

        # Check that the system has moved towards the setpoints
        initial_turbidity_error = abs(initial_quality.turbidity - turbidity_setpoint)
        final_turbidity_error = abs(final_quality.turbidity - turbidity_setpoint)
        self.assertLess(final_turbidity_error, initial_turbidity_error, "Turbidity should be closer to the setpoint.")

        initial_do_error = abs(initial_quality.dissolved_oxygen - do_setpoint)
        final_do_error = abs(final_quality.dissolved_oxygen - do_setpoint)
        self.assertLess(final_do_error, initial_do_error, "Dissolved Oxygen should be closer to the setpoint.")

        # Also assert that we are reasonably close to the target.
        # The PID tuning is not perfect, so we use a generous delta.
        self.assertAlmostEqual(final_quality.turbidity, turbidity_setpoint, delta=4.0)
        self.assertAlmostEqual(final_quality.dissolved_oxygen, do_setpoint, delta=1.0)

if __name__ == '__main__':
    unittest.main()
