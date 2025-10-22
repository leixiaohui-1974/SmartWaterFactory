import numpy as np

from water_plant_controller.control.mpc_controller import (
    LinearisedProcessModel,
    MPCFaultTolerantController,
    ReliabilityAwareConstraints,
)


def _build_controller() -> MPCFaultTolerantController:
    model = LinearisedProcessModel(a=0.82, b=-0.45)
    constraints = ReliabilityAwareConstraints(minimum=0.0, maximum=15.0, ramp_limit=4.0)
    controller = MPCFaultTolerantController(
        setpoint=5.0,
        model=model,
        constraints=constraints,
        horizon=5,
        control_weight=0.08,
        state_weight=1.2,
        reliability_penalty=40.0,
    )
    return controller


def test_mpc_controller_respects_constraints() -> None:
    controller = _build_controller()
    controller.update_sensor_health(reliability=1.0, bias_estimate=0.0)
    output = controller.calculate(measurement=25.0)
    assert controller.constraints.minimum <= output <= controller.constraints.maximum


def test_reliability_penalty_reduces_output() -> None:
    controller = _build_controller()
    controller.update_sensor_health(reliability=1.0, bias_estimate=0.0)
    aggressive_output = controller.calculate(measurement=25.0)

    controller.update_sensor_health(reliability=0.0, bias_estimate=4.0)
    conservative_output = controller.calculate(measurement=25.0)

    assert conservative_output <= aggressive_output


def test_ramp_limit_applied_between_steps() -> None:
    controller = _build_controller()
    controller.last_output = controller.constraints.maximum
    controller.update_sensor_health(reliability=1.0, bias_estimate=0.0)
    output = controller.calculate(measurement=4.5)

    assert abs(output - controller.constraints.maximum) <= controller.constraints.ramp_limit + 1e-6


def test_default_candidate_grid_focuses_operating_band() -> None:
    controller = _build_controller()
    controller.candidate_grid = None
    grid = controller._build_candidate_grid()

    assert np.isclose(grid[0], controller.constraints.minimum)
    assert np.isclose(grid[-1], controller.constraints.maximum)
    assert len(grid) >= 30

    low_band = grid[grid <= controller.constraints.minimum + 4.0]
    high_band = grid[grid > controller.constraints.minimum + 4.0]
    assert len(low_band) >= len(high_band)
