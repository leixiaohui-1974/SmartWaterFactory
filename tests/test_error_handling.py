import math
from datetime import datetime

import pytest

from config.settings import SIMULATION_DEFAULTS
from water_plant_controller.control.on_off_controller import OnOffController
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator


class TestErrorHandling:
    def setup_method(self) -> None:
        initial_quality = WaterQuality(
            timestamp=datetime.now(),
            ph=7.0,
            turbidity=25.0,
            dissolved_oxygen=4.0,
        )
        self.simulator = PlantSimulator(initial_quality, SIMULATION_DEFAULTS)
        self.pid_controller = PIDController(Kp=1.0, Ki=0.1, Kd=0.05, setpoint=10.0)
        self.onoff_controller = OnOffController(setpoint=10.0)

    def test_plant_simulator_negative_coagulant_dose(self):
        with pytest.raises(ValueError, match="coagulant_dose must be non-negative"):
            self.simulator.step(-1.0, 5.0)

    def test_plant_simulator_negative_aeration_rate(self):
        with pytest.raises(ValueError, match="aeration_rate must be non-negative"):
            self.simulator.step(5.0, -1.0)

    def test_plant_simulator_invalid_coagulant_type(self):
        with pytest.raises(TypeError, match="coagulant_dose must be numeric"):
            self.simulator.step("invalid", 5.0)

    def test_plant_simulator_invalid_aeration_type(self):
        with pytest.raises(TypeError, match="aeration_rate must be numeric"):
            self.simulator.step(5.0, "invalid")

    def test_plant_simulator_extreme_coagulant_dose(self):
        with pytest.raises(ValueError, match="coagulant_dose too large"):
            self.simulator.step(1500.0, 5.0)

    def test_plant_simulator_extreme_aeration_rate(self):
        with pytest.raises(ValueError, match="aeration_rate too large"):
            self.simulator.step(5.0, 1500.0)

    def test_plant_simulator_nan_coagulant_dose(self):
        with pytest.raises(ValueError, match="coagulant_dose contains an invalid number"):
            self.simulator.step(float("nan"), 5.0)

    def test_plant_simulator_inf_aeration_rate(self):
        with pytest.raises(ValueError, match="aeration_rate too large"):
            self.simulator.step(5.0, float("inf"))

    def test_pid_controller_invalid_current_value_type(self):
        with pytest.raises(TypeError, match="current_value must be numeric"):
            self.pid_controller.calculate("invalid")

    def test_pid_controller_invalid_dt_type(self):
        with pytest.raises(TypeError, match="dt must be numeric"):
            self.pid_controller.calculate(10.0, "invalid")

    def test_pid_controller_negative_dt(self):
        with pytest.raises(ValueError, match="dt must be non-negative"):
            self.pid_controller.calculate(10.0, -1.0)

    def test_pid_controller_nan_current_value(self):
        with pytest.raises(ValueError, match="current_value contains an invalid number"):
            self.pid_controller.calculate(float("nan"))

    def test_pid_controller_inf_dt(self):
        with pytest.raises(ValueError, match="dt contains an invalid number"):
            self.pid_controller.calculate(10.0, float("inf"))

    def test_pid_controller_negative_gains(self):
        with pytest.raises(ValueError, match="PID gains must be non-negative"):
            PIDController(Kp=-1.0, Ki=0.1, Kd=0.05, setpoint=10.0)

    def test_onoff_controller_invalid_current_value_type(self):
        with pytest.raises(TypeError, match="current_value must be numeric"):
            self.onoff_controller.calculate("invalid")

    def test_onoff_controller_nan_current_value(self):
        with pytest.raises(ValueError, match="current_value contains an invalid number"):
            self.onoff_controller.calculate(float("nan"))

    def test_onoff_controller_inf_current_value(self):
        with pytest.raises(ValueError, match="current_value contains an invalid number"):
            self.onoff_controller.calculate(float("inf"))

    def test_plant_simulator_zero_inputs(self):
        result = self.simulator.step(0.0, 0.0)
        assert isinstance(result, WaterQuality)
        assert result.turbidity >= 0
        assert result.dissolved_oxygen >= 0

    def test_plant_simulator_maximum_valid_inputs(self):
        result = self.simulator.step(999.0, 999.0)
        assert isinstance(result, WaterQuality)
        assert result.turbidity >= 0
        assert result.dissolved_oxygen >= 0

    def test_pid_controller_zero_dt(self):
        result = self.pid_controller.calculate(10.0, 0.0)
        assert isinstance(result, (int, float))
        assert math.isfinite(result)

    def test_pid_controller_very_large_error(self):
        result = self.pid_controller.calculate(1_000_000.0)
        assert isinstance(result, (int, float))
        assert math.isfinite(result)

    def test_onoff_controller_boundary_values(self):
        result = self.onoff_controller.calculate(10.0)
        assert result == self.onoff_controller.output_min

        result = self.onoff_controller.calculate(9.999)
        assert result == self.onoff_controller.output_max

        result = self.onoff_controller.calculate(10.001)
        assert result == self.onoff_controller.output_min
