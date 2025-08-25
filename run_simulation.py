import csv
from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from config.settings import PID_GAINS

def run_and_log_simulation(steps: int = 300, log_file: str = 'simulation_log.csv'):
    """
    Runs the water plant simulation and logs the state at each step to a CSV file.

    :param steps: The number of simulation steps to run.
    :param log_file: The path to the CSV file where the log will be saved.
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
    turbidity_setpoint = 5.0
    do_setpoint = 8.5

    dosing_gains = PID_GAINS["dosing_controller"]
    aeration_gains = PID_GAINS["aeration_controller"]

    dosing_controller = PIDController(
        Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
        setpoint=turbidity_setpoint, reverse_acting=True
    )
    dosing_controller.set_output_limits(0, 10)
    dosing_controller.set_integral_limits(-5, 5)

    aeration_controller = PIDController(
        Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
        setpoint=do_setpoint
    )
    aeration_controller.set_output_limits(0, 20)
    aeration_controller.set_integral_limits(-15, 15)

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
    run_and_log_simulation()
