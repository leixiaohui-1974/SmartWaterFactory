import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator


class TestPlantSimulator(unittest.TestCase):
    """Unit tests for the PlantSimulator."""

    def setUp(self) -> None:
        self.initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=10.0,
            dissolved_oxygen=5.0,
        )
        self.simulator = PlantSimulator(self.initial_quality)

    def test_initialization(self):
        self.assertEqual(self.simulator.current_quality, self.initial_quality)

    def test_turbidity_reduction(self):
        initial_turbidity = self.simulator.current_quality.turbidity
        delay = self.simulator._delay_steps

        self.simulator.step(coagulant_dose=1.0, aeration_rate=0.0)
        for _ in range(delay):
            self.simulator.step(coagulant_dose=0.0, aeration_rate=0.0)

        self.assertLess(self.simulator.current_quality.turbidity, initial_turbidity)

    def test_do_increase_and_decrease(self):
        delay = self.simulator._delay_steps

        simulator = PlantSimulator(self.initial_quality)
        simulator._do_consumption_rate = 0.0
        initial_do = simulator.current_quality.dissolved_oxygen

        simulator.step(coagulant_dose=0.0, aeration_rate=10.0)
        for _ in range(delay):
            simulator.step(coagulant_dose=0.0, aeration_rate=0.0)

        self.assertGreater(simulator.current_quality.dissolved_oxygen, initial_do)

        simulator = PlantSimulator(self.initial_quality)
        initial_do = simulator.current_quality.dissolved_oxygen
        simulator.step(coagulant_dose=0.0, aeration_rate=0.0)
        self.assertLess(simulator.current_quality.dissolved_oxygen, initial_do)

    def test_bounds(self):
        self.simulator.step(coagulant_dose=1000.0, aeration_rate=0.0)
        self.assertGreaterEqual(self.simulator.current_quality.turbidity, 0.0)

        self.simulator.step(coagulant_dose=0.0, aeration_rate=1000.0)
        self.assertLessEqual(self.simulator.current_quality.dissolved_oxygen, 9.0)

    def test_disturbance_provider(self):
        def disturbance(**kwargs):
            return {
                "turbidity": 0.5,
                "dissolved_oxygen": -0.2,
                "inflow_turbidity": 40.0,
            }

        simulator = PlantSimulator(
            self.initial_quality,
            disturbance_provider=disturbance,
        )
        result = simulator.step(coagulant_dose=0.0, aeration_rate=0.0)
        self.assertAlmostEqual(result.turbidity, 10.5)
        self.assertAlmostEqual(result.dissolved_oxygen, 4.7)
        self.assertEqual(simulator.step_index, 1)
        self.assertIn("inflow_turbidity", simulator.last_diagnostics)

    def test_sensor_provider_fault_detection(self):
        def sensor_noise(**kwargs):
            return {
                "turbidity": 5.0,
                "dissolved_oxygen": -0.5,
                "sensor_fault_code": 42,
            }

        simulator = PlantSimulator(
            self.initial_quality,
            sensor_provider=sensor_noise,
        )
        result = simulator.step(coagulant_dose=0.0, aeration_rate=0.0)

        # True quality remains close to original, measurement shifted by sensor model
        self.assertNotAlmostEqual(result.turbidity, simulator.true_quality.turbidity)
        self.assertAlmostEqual(result.turbidity - simulator.true_quality.turbidity, 5.0)
        self.assertEqual(simulator.last_diagnostics["sensor_fault_detected"], 1.0)
        self.assertIn("sensor_fault_code", simulator.last_diagnostics)

    def test_redundant_sensor_switches_when_primary_faults(self):
        def primary_fault(**kwargs):
            return {"turbidity": 5.0}

        def secondary_sensor(**kwargs):
            return {"turbidity": 0.0, "dissolved_oxygen": 0.0}

        simulator = PlantSimulator(
            self.initial_quality,
            sensor_provider=primary_fault,
            redundant_sensor_provider=secondary_sensor,
        )

        result = simulator.step(coagulant_dose=0.0, aeration_rate=0.0)

        # Redundant sensor measurement should be used, keeping turbidity aligned with true quality.
        self.assertAlmostEqual(result.turbidity, simulator.true_quality.turbidity)
        self.assertEqual(simulator.last_diagnostics["redundant_sensor_active"], 1.0)
        self.assertEqual(simulator.last_diagnostics["primary_sensor_fault"], 1.0)
        self.assertEqual(simulator.last_diagnostics["secondary_sensor_fault"], 0.0)


if __name__ == "__main__":
    unittest.main()
