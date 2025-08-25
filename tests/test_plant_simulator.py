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
        """Test that coagulant dose reduces turbidity."""
        initial_turbidity = self.simulator.current_quality.turbidity
        # Apply a dose of 1.0. Reduction should be 0.05 * 1.0 * 10.0 = 0.5
        self.simulator.step(coagulant_dose=1.0, aeration_rate=0)
        new_turbidity = self.simulator.current_quality.turbidity
        self.assertAlmostEqual(new_turbidity, 9.5)
        self.assertLess(new_turbidity, initial_turbidity)

    def test_do_increase_and_decrease(self):
        """Test that aeration increases DO and consumption decreases it."""
        # Case 1: Only aeration
        simulator = PlantSimulator(self.initial_quality)
        simulator._do_consumption_rate = 0 # Disable consumption for this part
        initial_do = simulator.current_quality.dissolved_oxygen # 5.0
        # Saturation is 9.0. Gap is 4.0. Increase is 0.01 * 10 * 4.0 = 0.4
        simulator.step(coagulant_dose=0, aeration_rate=10)
        self.assertAlmostEqual(simulator.current_quality.dissolved_oxygen, 5.4)

        # Case 2: Only consumption
        simulator = PlantSimulator(self.initial_quality)
        initial_do = simulator.current_quality.dissolved_oxygen # 5.0
        # Consumption is 0.02 * 5.0 = 0.1. New DO = 5.0 - 0.1 = 4.9
        simulator.step(coagulant_dose=0, aeration_rate=0)
        self.assertAlmostEqual(simulator.current_quality.dissolved_oxygen, 4.9)

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
