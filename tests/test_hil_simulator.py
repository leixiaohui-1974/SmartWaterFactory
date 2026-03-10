from datetime import datetime

import pytest

from water_plant_controller.hil import HILScenario, HILSimulator
from water_plant_controller.models.water_quality import WaterQuality


def _initial_quality() -> WaterQuality:
    return WaterQuality(
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        ph=7.0,
        turbidity=10.0,
        dissolved_oxygen=5.0,
    )


def test_hil_simulator_generates_snapshot_with_io_mappings() -> None:
    simulator = HILSimulator(_initial_quality(), random_seed=7)
    simulator.set_control_command("coagulant_dose", 6.0)
    simulator.set_control_command_from_milliamps("aeration_rate", 12.0)

    snapshot = simulator.step()

    assert snapshot.step_index == 1
    assert snapshot.scenario == "steady"
    assert snapshot.actuator_outputs["coagulant_dose"] == pytest.approx(6.0)
    assert snapshot.actuator_outputs["aeration_rate"] == pytest.approx(10.0)
    assert snapshot.actuator_currents_ma["coagulant_dose"] == pytest.approx(8.8)
    assert 4.0 <= snapshot.sensor_currents_ma["turbidity"] <= 20.0


def test_hil_simulator_switches_scenarios_and_applies_disturbance() -> None:
    simulator = HILSimulator(_initial_quality(), random_seed=11)
    baseline = simulator.step()

    simulator.set_scenario("turbidity_spike")
    disturbed = simulator.step()

    assert disturbed.scenario == "turbidity_spike"
    assert disturbed.true_quality.turbidity > baseline.true_quality.turbidity
    assert disturbed.diagnostics["scenario_name"] == "turbidity_spike"


def test_hil_simulator_supports_fault_injection() -> None:
    simulator = HILSimulator(_initial_quality(), random_seed=13)
    simulator.inject_sensor_fault("turbidity", "stuck", value=42.0)

    snapshot = simulator.step()

    assert snapshot.measured_quality.turbidity == pytest.approx(42.0)
    simulator.clear_sensor_fault("turbidity")
    recovered = simulator.step()
    assert recovered.measured_quality.turbidity != pytest.approx(42.0)


def test_hil_simulator_registers_custom_scenario() -> None:
    simulator = HILSimulator(_initial_quality(), random_seed=17)
    simulator.register_scenario(
        HILScenario(name="custom", dissolved_oxygen_offset=-0.4)
    )
    simulator.set_scenario("custom")

    snapshot = simulator.step()

    assert snapshot.scenario == "custom"
    assert snapshot.true_quality.dissolved_oxygen < 5.0


def test_hil_simulator_rejects_unknown_interfaces() -> None:
    simulator = HILSimulator(_initial_quality(), random_seed=19)

    with pytest.raises(KeyError):
        simulator.set_control_command("unknown", 1.0)

    with pytest.raises(KeyError):
        simulator.inject_sensor_fault("unknown", "stuck", value=1.0)

    with pytest.raises(ValueError):
        simulator.set_scenario("missing")
