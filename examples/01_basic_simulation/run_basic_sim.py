# Add the project root to the Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from config.settings import PID_GAINS

def main():
    """
    This example demonstrates how to set up and run a basic simulation
    of the water plant controller using default settings.
    """
    # 1. Define initial conditions and setpoints for the simulation.
    initial_quality = WaterQuality(
        timestamp=datetime.now(),
        ph=7.0,
        turbidity=25.0,      # High initial turbidity
        dissolved_oxygen=4.0 # Low initial dissolved oxygen
    )
    turbidity_setpoint = 5.0
    do_setpoint = 8.5

    # 2. Initialize the PlantSimulator with the starting water quality.
    # The simulator automatically loads default physical parameters from config/settings.py
    simulator = PlantSimulator(initial_quality)

    # 3. Create and configure the controllers.
    # We will use the PID controllers for this example.
    # The gains (Kp, Ki, Kd) are loaded from the centralized configuration file.
    dosing_gains = PID_GAINS["dosing_controller"]
    aeration_gains = PID_GAINS["aeration_controller"]

    # The dosing controller for turbidity is "reverse-acting" because
    # a higher dose (output) leads to a lower turbidity (measured value).
    dosing_controller = PIDController(
        Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
        setpoint=turbidity_setpoint,
        reverse_acting=True
    )
    dosing_controller.set_output_limits(0, 10) # Max coagulant dose
    dosing_controller.set_integral_limits(-5, 5)

    # The aeration controller for dissolved oxygen is "direct-acting" (default)
    # because a higher aeration rate (output) leads to a higher DO (measured value).
    aeration_controller = PIDController(
        Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
        setpoint=do_setpoint
    )
    aeration_controller.set_output_limits(0, 20) # Max aeration rate
    aeration_controller.set_integral_limits(-15, 15)

    # 4. Run the simulation loop for a fixed number of steps.
    print("--- Running Basic Simulation ---")
    print(f"Initial State: Turbidity={simulator.current_quality.turbidity:.2f}, "
          f"DO={simulator.current_quality.dissolved_oxygen:.2f}\n")

    simulation_steps = 150
    for i in range(simulation_steps):
        # Get the current water quality from the simulator
        current_quality = simulator.current_quality

        # Calculate the required control actions using the controllers
        coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
        aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)

        # Apply the control actions to the simulator to advance it by one step
        simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

        # Print the status at regular intervals
        if (i + 1) % 15 == 0:
            print(f"Step {i+1:3}: Turbidity={simulator.current_quality.turbidity:.2f}, "
                  f"DO={simulator.current_quality.dissolved_oxygen:.2f}")

    print(f"\nFinal State:   Turbidity={simulator.current_quality.turbidity:.2f}, "
          f"DO={simulator.current_quality.dissolved_oxygen:.2f}")
    print("--- Simulation Complete ---")

if __name__ == '__main__':
    main()
