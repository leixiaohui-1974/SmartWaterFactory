# Add the project root to the Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController

def run_simulation_with_gains(name: str, Kp: float, Ki: float, Kd: float):
    """
    A helper function to run a simulation with a specific set of PID gains
    for the turbidity controller.
    """
    print(f"\n--- Running Simulation: {name} ---")
    print(f"--- Gains: Kp={Kp}, Ki={Ki}, Kd={Kd} ---\n")

    initial_quality = WaterQuality(
        timestamp=datetime.now(),
        ph=7.0,
        turbidity=25.0,
        dissolved_oxygen=4.0
    )
    turbidity_setpoint = 5.0
    simulator = PlantSimulator(initial_quality)

    # Use custom gains for the dosing controller
    dosing_controller = PIDController(
        Kp=Kp, Ki=Ki, Kd=Kd,
        setpoint=turbidity_setpoint,
        reverse_acting=True
    )
    dosing_controller.set_output_limits(0, 10)
    dosing_controller.set_integral_limits(-5, 5)

    # We are not focused on the DO controller in this example, so we will
    # create a dummy controller that does nothing.
    class DummyController:
        def calculate(self, _): return 0.0
    aeration_controller = DummyController()

    simulation_steps = 150
    for i in range(simulation_steps):
        current_quality = simulator.current_quality
        coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
        aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)
        simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)
        if (i + 1) % 15 == 0:
            print(f"Step {i+1:3}: Turbidity={simulator.current_quality.turbidity:.2f}")

    print(f"\nFinal State: Turbidity={simulator.current_quality.turbidity:.2f}")
    print(f"--- {name} Complete ---")


def main():
    """
    This example demonstrates the effect of PID tuning by running two
    simulations with different gains for the turbidity controller.
    """
    # Simulation 1: Aggressive Tuning
    # A high integral gain (Ki) can cause the controller to overshoot the
    # setpoint and oscillate before settling.
    run_simulation_with_gains(
        name="Aggressive Tuning",
        Kp=0.2,
        Ki=0.1, # High integral gain
        Kd=0.1
    )

    # Simulation 2: Conservative Tuning
    # A smaller integral gain and a larger derivative gain (Kd) can help
    # to dampen the response, resulting in a smoother approach to the setpoint
    # with less overshoot.
    run_simulation_with_gains(
        name="Conservative Tuning",
        Kp=0.1,
        Ki=0.01, # Lower integral gain
        Kd=0.5   # Higher derivative gain
    )

if __name__ == '__main__':
    main()
