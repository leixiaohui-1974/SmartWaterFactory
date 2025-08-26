# Add the project root to the Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from config.settings import PID_GAINS, SIMULATION_DEFAULTS

def main():
    """
    This example demonstrates how to run a simulation with advanced
    features like time delay and non-linearity enabled.
    """
    # 1. Define a custom simulation configuration.
    # We start with the defaults and override the ones we want to change.
    advanced_sim_config = SIMULATION_DEFAULTS.copy()
    advanced_sim_config.update({
        "time_delay_steps": 15,         # A significant 15-step delay
        "aeration_non_linearity": 2.0   # A more pronounced non-linear effect
    })

    print("--- Running Advanced Simulation ---")
    print(f"--- Using Custom Config: Time Delay={advanced_sim_config['time_delay_steps']} steps, "
          f"Non-linearity={advanced_sim_config['aeration_non_linearity']} ---")

    # 2. Initialize the simulator, passing in our custom config.
    initial_quality = WaterQuality(
        timestamp=datetime.now(),
        ph=7.0,
        turbidity=25.0,
        dissolved_oxygen=4.0
    )
    simulator = PlantSimulator(initial_quality, config=advanced_sim_config)

    # 3. Set up the controllers as usual.
    # Note: A system with long delays is much harder to control. The default
    # PID gains might not be optimal, but we will use them to see the effect.
    turbidity_setpoint = 5.0
    do_setpoint = 8.5
    dosing_gains = PID_GAINS["dosing_controller"]
    aeration_gains = PID_GAINS["aeration_controller"]

    dosing_controller = PIDController(
        Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
        setpoint=turbidity_setpoint,
        reverse_acting=True
    )
    dosing_controller.set_output_limits(0, 10)
    dosing_controller.set_integral_limits(-5, 5)

    aeration_controller = PIDController(
        Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
        setpoint=do_setpoint
    )
    aeration_controller.set_output_limits(0, 20)
    aeration_controller.set_integral_limits(-15, 15)

    # 4. Run the simulation loop.
    print(f"\nInitial State: Turbidity={simulator.current_quality.turbidity:.2f}, "
          f"DO={simulator.current_quality.dissolved_oxygen:.2f}\n")

    simulation_steps = 200
    for i in range(simulation_steps):
        current_quality = simulator.current_quality
        coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
        aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)
        simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

        if (i + 1) % 20 == 0:
            print(f"Step {i+1:3}: Turbidity={simulator.current_quality.turbidity:.2f}, "
                  f"DO={simulator.current_quality.dissolved_oxygen:.2f}")

    print(f"\nFinal State:   Turbidity={simulator.current_quality.turbidity:.2f}, "
          f"DO={simulator.current_quality.dissolved_oxygen:.2f}")
    print("--- Simulation Complete ---")

if __name__ == '__main__':
    main()
