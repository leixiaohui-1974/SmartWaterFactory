# Example 1: Basic Simulation

This example provides a simple, self-contained demonstration of how to set up and run a basic simulation of the water plant controller.

## The Goal

The goal of this example is to show the fundamental components of the framework in action:
1.  Initializing the `PlantSimulator`.
2.  Creating `PIDController` instances for our two process variables (turbidity and dissolved oxygen).
3.  Running a simulation loop where the controllers and simulator interact.
4.  Printing the results to the console.

## The Code: `run_basic_sim.py`

The code is heavily commented to be self-explanatory. Here is a breakdown of the key sections in the `main()` function:

### 1. Initialization
```python
initial_quality = WaterQuality(...)
turbidity_setpoint = 5.0
do_setpoint = 8.5
```
We start by defining the initial conditions of the water and the desired **setpoints** (target values) for our controllers.

### 2. Simulator Setup
```python
simulator = PlantSimulator(initial_quality)
```
We create an instance of the `PlantSimulator`, passing in the initial water quality. The simulator automatically loads its physical parameters (like reaction rates, time delays, etc.) from the main project configuration file at `config/settings.py`.

### 3. Controller Configuration
```python
dosing_gains = PID_GAINS["dosing_controller"]
dosing_controller = PIDController(...)

aeration_gains = PID_GAINS["aeration_controller"]
aeration_controller = PIDController(...)
```
We create two instances of the `PIDController`, one for managing turbidity (via a coagulant dose) and one for managing dissolved oxygen (via aeration).

-   **Gains (`Kp`, `Ki`, `Kd`)**: The tuning parameters for the controllers are loaded from `config/settings.py`.
-   **`reverse_acting=True`**: Note that the dosing controller is set to be "reverse-acting". This is because its output (coagulant dose) causes the measured variable (turbidity) to *decrease*. This is the opposite of the aeration controller, where more output (aeration) causes the measurement (dissolved oxygen) to *increase*.

### 4. The Simulation Loop
```python
for i in range(simulation_steps):
    # Get current state
    current_quality = simulator.current_quality

    # Calculate control actions
    coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
    aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)

    # Apply actions to the simulator
    simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)
```
This is the core of the closed-loop system. In each iteration, we:
1.  Get the current state of the water from the simulator.
2.  Feed the measured values (`turbidity` and `dissolved_oxygen`) to their respective controllers.
3.  The controllers `calculate()` the appropriate output action.
4.  We `step()` the simulator forward, applying the calculated actions.

## How to Run This Example

Navigate to the root directory of the project and run the script directly:
```bash
python3 examples/01_basic_simulation/run_basic_sim.py
```
You will see the simulation status printed to the console, showing the system driving the turbidity and dissolved oxygen towards their setpoints.
