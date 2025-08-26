import csv
import argparse
from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.on_off_controller import OnOffController
from config.settings import PID_GAINS

def run_and_log_simulation(steps: int, log_file: str, turbidity_setpoint: float, do_setpoint: float, controller_type: str):
    """
    Runs the water plant simulation and logs the state at each step to a CSV file.

    :param steps: The number of simulation steps to run.
    :param log_file: The path to the CSV file where the log will be saved.
    :param turbidity_setpoint: The target turbidity value.
    :param do_setpoint: The target dissolved oxygen value.
    :param controller_type: The type of controller to use ('pid' or 'on-off').
    """
    # 1. Initialization
    initial_quality = WaterQuality(
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        ph=7.0,
        turbidity=25.0,
        dissolved_oxygen=4.0
    )
    simulator = PlantSimulator(initial_quality)

    # 2. Controller Setup
    if controller_type == 'pid':
        dosing_gains = PID_GAINS["dosing_controller"]
        aeration_gains = PID_GAINS["aeration_controller"]

        dosing_controller = PIDController(
            Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
            setpoint=turbidity_setpoint, reverse_acting=True
        )
        dosing_controller.set_integral_limits(-5, 5)

        aeration_controller = PIDController(
            Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
            setpoint=do_setpoint
        )
        aeration_controller.set_integral_limits(-15, 15)

    elif controller_type == 'on-off':
        dosing_controller = OnOffController(setpoint=turbidity_setpoint, reverse_acting=True)
        aeration_controller = OnOffController(setpoint=do_setpoint)

    else:
        raise ValueError(f"Unknown controller type: {controller_type}")

    dosing_controller.set_output_limits(0, 10)
    aeration_controller.set_output_limits(0, 20)

    # 3. Setup CSV Logging
    with open(log_file, 'w', newline='') as csvfile:
        fieldnames = [
            'timestamp', 'turbidity', 'dissolved_oxygen',
            'turbidity_setpoint', 'do_setpoint',
            'coagulant_dose', 'aeration_rate'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # 4. Simulation Loop
        print(f"Running simulation for {steps} steps... Logging to {log_file}")
        for i in range(steps):
            current_quality = simulator.current_quality

            # Calculate control actions
            coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
            aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)

            # Apply actions to the simulator
            simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

            # Log data
            writer.writerow({
                'timestamp': current_quality.timestamp.isoformat(),
                'turbidity': current_quality.turbidity,
                'dissolved_oxygen': current_quality.dissolved_oxygen,
                'turbidity_setpoint': turbidity_setpoint,
                'do_setpoint': do_setpoint,
                'coagulant_dose': coagulant_dose,
                'aeration_rate': aeration_rate
            })

    print("Simulation finished.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the Water Plant Simulation.")
    parser.add_argument('--steps', type=int, default=300, help='Number of simulation steps to run.')
    parser.add_argument('--log-file', type=str, default='simulation_log.csv', help='Path to the output CSV log file.')
    parser.add_argument('--turbidity-setpoint', type=float, default=5.0, help='Setpoint for turbidity.')
    parser.add_argument('--do-setpoint', type=float, default=8.5, help='Setpoint for dissolved oxygen.')
    parser.add_argument('--controller-type', type=str, default='pid', choices=['pid', 'on-off'], help='Type of controller to use.')

    args = parser.parse_args()

    run_and_log_simulation(
        steps=args.steps,
        log_file=args.log_file,
        turbidity_setpoint=args.turbidity_setpoint,
        do_setpoint=args.do_setpoint,
        controller_type=args.controller_type
    )
