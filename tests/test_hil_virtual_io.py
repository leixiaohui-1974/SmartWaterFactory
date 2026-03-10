from random import Random

import pytest

from water_plant_controller.hil import (
    ActuatorConfig,
    SensorConfig,
    VirtualActuator,
    VirtualSensor,
)


def test_virtual_sensor_applies_dead_time_and_scales_to_milliamps() -> None:
    sensor = VirtualSensor(
        SensorConfig(
            name="DO",
            unit="mg/L",
            tau_s=0.0,
            noise_std=0.0,
            drift_rate=0.0,
            dead_time_s=2.0,
            range_min=0.0,
            range_max=20.0,
        ),
        dt_s=1.0,
        rng=Random(0),
    )
    sensor.reset(0.0)

    assert sensor.measure(10.0) == pytest.approx(0.0)
    assert sensor.measure(10.0) == pytest.approx(0.0)
    assert sensor.measure(10.0) == pytest.approx(10.0)
    assert sensor.to_milliamps(10.0) == pytest.approx(12.0)


def test_virtual_sensor_fault_modes_are_switchable() -> None:
    sensor = VirtualSensor(
        SensorConfig(
            name="NTU",
            unit="NTU",
            tau_s=0.0,
            noise_std=0.0,
            drift_rate=0.0,
            dead_time_s=0.0,
            range_min=0.0,
            range_max=100.0,
        ),
        dt_s=1.0,
        rng=Random(1),
    )
    sensor.reset(10.0)

    sensor.inject_fault("bias", bias=5.0)
    assert sensor.measure(20.0) == pytest.approx(25.0)

    sensor.inject_fault("stuck", value=42.0)
    assert sensor.measure(5.0) == pytest.approx(42.0)

    sensor.inject_fault("dropout", value=0.0)
    assert sensor.measure(30.0) == pytest.approx(0.0)

    sensor.clear_fault()
    assert sensor.measure(30.0) == pytest.approx(30.0)


def test_virtual_actuator_respects_deadband_and_rate_limit() -> None:
    actuator = VirtualActuator(
        ActuatorConfig(
            rate_limit=2.0,
            deadband=0.5,
            noise_std=0.0,
            lag_tau_s=0.0,
            min_val=0.0,
            max_val=10.0,
        ),
        dt_s=1.0,
        rng=Random(2),
    )

    actuator.set_command(0.2)
    assert actuator.command == pytest.approx(0.0)

    actuator.set_command(8.0)
    assert actuator.step() == pytest.approx(2.0)
    assert actuator.step() == pytest.approx(4.0)
    assert actuator.step() == pytest.approx(6.0)


def test_virtual_actuator_accepts_4_20ma_commands() -> None:
    actuator = VirtualActuator(
        ActuatorConfig(
            rate_limit=100.0,
            deadband=0.0,
            noise_std=0.0,
            lag_tau_s=0.0,
            min_val=0.0,
            max_val=20.0,
        ),
        dt_s=1.0,
        rng=Random(3),
    )

    actuator.set_command_from_milliamps(12.0)
    assert actuator.command == pytest.approx(10.0)
    assert actuator.step() == pytest.approx(10.0)
    assert actuator.to_milliamps() == pytest.approx(12.0)


def test_invalid_virtual_io_configuration_raises() -> None:
    with pytest.raises(ValueError):
        VirtualSensor(SensorConfig(name="bad", unit="u", range_min=5.0, range_max=5.0))

    with pytest.raises(ValueError):
        VirtualActuator(ActuatorConfig(min_val=2.0, max_val=2.0))
