import unittest

from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.precision_controller import (
    AdaptivePIDProfile,
    AdaptivePIDController,
    ConstraintProfile,
    PrecisionPIDController,
)


class TestPrecisionPIDController(unittest.TestCase):
    def setUp(self) -> None:
        pid = PIDController(Kp=1.0, Ki=0.0, Kd=0.0, setpoint=10.0)
        constraint = ConstraintProfile(minimum=0.0, maximum=15.0, ramp_rate=5.0, unit_cost=0.2)
        self.controller = PrecisionPIDController(
            pid=pid,
            constraint=constraint,
            feedforward_gain=2.0,
            feedforward_key="turbidity_adjustment",
        )

    def test_basic_pid_output(self):
        output = self.controller.calculate(current_value=5.0, dt=1.0)
        self.assertAlmostEqual(output, 5.0)

    def test_feedforward_application(self):
        output = self.controller.calculate(
            current_value=8.0,
            dt=1.0,
            disturbances={"turbidity_adjustment": 0.5},
        )
        # PID term: (10 - 8) * 1 = 2, feedforward: 2 * 0.5 = 1
        self.assertAlmostEqual(output, 3.0)

    def test_constraint_saturation(self):
        # First call sets previous output to constraint minimum.
        self.controller.calculate(current_value=0.0, dt=1.0)
        # Massive error should saturate at maximum but honour ramp rate (min=0, ramp=5)
        output = self.controller.calculate(current_value=-100.0, dt=1.0)
        self.assertEqual(output, 10.0)
        self.assertEqual(self.controller.last_diagnostics["saturated"], 1)

    def test_cost_reporting(self):
        self.controller.calculate(current_value=5.0, dt=1.0)
        diagnostics = self.controller.last_diagnostics
        self.assertIn("instantaneous_cost", diagnostics)
        self.assertGreaterEqual(diagnostics["instantaneous_cost"], 0.0)

    def test_reset(self):
        self.controller.calculate(current_value=5.0, dt=1.0)
        self.controller.reset()
        self.assertEqual(self.controller._previous_output, self.controller._constraint.minimum)
        self.assertEqual(self.controller.last_diagnostics, {})


class TestAdaptivePIDController(unittest.TestCase):
    def setUp(self) -> None:
        pid = PIDController(Kp=0.5, Ki=0.05, Kd=0.0, setpoint=10.0)
        constraint = ConstraintProfile(minimum=0.0, maximum=20.0)
        profile = AdaptivePIDProfile(
            kp_min=0.1,
            kp_max=2.0,
            ki_min=0.0,
            ki_max=0.5,
            kp_learning_rate=0.1,
            ki_learning_rate=0.01,
            error_increase_threshold=1.0,
            error_decrease_threshold=0.2,
        )
        self.controller = AdaptivePIDController(
            pid=pid,
            constraint=constraint,
            adaptation=profile,
        )

    def test_gain_increase_on_large_error(self):
        initial_kp = self.controller._pid.Kp
        self.controller.calculate(current_value=0.0, dt=1.0)
        self.assertGreater(self.controller._pid.Kp, initial_kp)
        self.assertIn("adaptive_kp", self.controller.last_diagnostics)

    def test_gain_decrease_on_small_error(self):
        # First drive gains up so they can be reduced later
        self.controller.calculate(current_value=0.0, dt=1.0)
        increased_kp = self.controller._pid.Kp
        # Now provide measurements close to setpoint to reduce gains
        for _ in range(5):
            self.controller.calculate(current_value=9.9, dt=1.0)
        self.assertLessEqual(self.controller._pid.Kp, increased_kp)


if __name__ == "__main__":
    unittest.main()
