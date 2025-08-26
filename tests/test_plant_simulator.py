import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator

class TestPlantSimulator(unittest.TestCase):
    """Unit tests for the PlantSimulator class."""

    def setUp(self):
        """Set up a default simulator for each test."""
        self.initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=10.0,
            dissolved_oxygen=5.0
        )
        self.simulator = PlantSimulator(self.initial_quality)

    def test_initialization(self):
        """Test that the simulator initializes with the correct state."""
        self.assertEqual(self.simulator.current_quality, self.initial_quality)

    def test_turbidity_reduction(self):
        """Test that coagulant dose reduces turbidity after the delay."""
        initial_turbidity = self.simulator.current_quality.turbidity
        delay = self.simulator._delay_steps

        # Apply a dose and then zeros to flush the pipeline
        self.simulator.step(coagulant_dose=1.0, aeration_rate=0)
        for _ in range(delay):
            self.simulator.step(coagulant_dose=0, aeration_rate=0)

        new_turbidity = self.simulator.current_quality.turbidity
        self.assertLess(new_turbidity, initial_turbidity)

    def test_do_increase_and_decrease(self):
        """Test that aeration increases DO and consumption decreases it after the delay."""
        delay = self.simulator._delay_steps

        # Case 1: Only aeration
        simulator = PlantSimulator(self.initial_quality)
        simulator._do_consumption_rate = 0 # Disable consumption for this part
        initial_do = simulator.current_quality.dissolved_oxygen

        simulator.step(coagulant_dose=0, aeration_rate=10)
        for _ in range(delay):
            simulator.step(coagulant_dose=0, aeration_rate=0)

        self.assertGreater(simulator.current_quality.dissolved_oxygen, initial_do)

        # Case 2: Only consumption (delay doesn't affect this)
        simulator = PlantSimulator(self.initial_quality)
        initial_do = simulator.current_quality.dissolved_oxygen
        simulator.step(coagulant_dose=0, aeration_rate=0)
        self.assertLess(simulator.current_quality.dissolved_oxygen, initial_do)

    def test_bounds(self):
        """Test that water quality parameters stay within logical bounds."""
        # High dose to force turbidity to zero
        self.simulator.step(coagulant_dose=1000, aeration_rate=0)
        self.assertGreaterEqual(self.simulator.current_quality.turbidity, 0)

        # High aeration to force DO to saturation
        self.simulator.step(coagulant_dose=0, aeration_rate=1000)
        # after one step, it should be closer to saturation, but not over it
        self.assertLessEqual(self.simulator.current_quality.dissolved_oxygen, 9.0)

if __name__ == '__main__':
    unittest.main()
