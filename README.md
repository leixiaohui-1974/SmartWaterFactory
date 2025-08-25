# Water Plant Process Controller

## Overview

This project provides a simple, product-oriented framework for simulating and controlling water treatment processes, specifically focusing on precise chemical dosing and aeration. It includes a basic water plant simulator and a reusable PID controller, demonstrating a closed-loop control system.

This project was built to showcase a structured approach to developing control algorithms, including simulation, control, and testing.

## Project Structure

The repository is organized as follows:

- `water_plant_controller/`: The main Python package for the project.
  - `models/`: Contains data models, such as `water_quality.py`.
  - `simulation/`: Contains the process simulator, `plant_simulator.py`.
  - `control/`: Contains control algorithms, such as the generic `pid_controller.py`.
- `tests/`: Contains all unit and integration tests.
  - `test_water_quality.py`: Unit tests for the data model.
  - `test_pid_controller.py`: Unit tests for the PID controller.
  - `test_plant_simulator.py`: Unit tests for the simulator.
  - `test_integration.py`: Integration test for the closed-loop system.
- `config/`: Contains configuration files, such as `settings.py` for simulation and controller parameters.
- `data/`: (Placeholder) For simulation data.

## Configuration

The core parameters for the simulation and PID controllers are stored in `config/settings.py`. You can modify this file to tune the system's behavior without changing the source code.

## Installation

Currently, the project has no external dependencies. You can clone the repository and run the tests directly.

```bash
git clone <repository-url>
cd <repository-name>
```

## Usage

### Running Tests

To verify that the system is working correctly, you can run all the tests from the root directory:

```bash
python3 -m unittest discover tests
```
This command will automatically find and run all tests in the `tests` directory.

### Example: Running a Simulation

Here is a basic example of how to set up and run a closed-loop simulation, similar to the integration test. You can save this code as `example.py` in the root directory and run it with `python3 example.py`.

```python
from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from config.settings import PID_GAINS

# 1. Define initial conditions and setpoints
initial_quality = WaterQuality(
    timestamp=datetime.now(),
    ph=7.0,
    turbidity=25.0,
    dissolved_oxygen=4.0
)
turbidity_setpoint = 5.0
do_setpoint = 8.5

# 2. Initialize the simulator
# The simulator now loads default parameters from config/settings.py
simulator = PlantSimulator(initial_quality)

# 3. Create and configure controllers
# Load gains from the centralized configuration file
dosing_gains = PID_GAINS["dosing_controller"]
aeration_gains = PID_GAINS["aeration_controller"]

# Use reverse_acting=True for turbidity control
dosing_controller = PIDController(
    Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
    setpoint=turbidity_setpoint,
    reverse_acting=True
)
dosing_controller.set_output_limits(0, 10)
dosing_controller.set_integral_limits(-5, 5) # Set integral limits for anti-windup

# Use direct-acting (default) for DO control
aeration_controller = PIDController(
    Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
    setpoint=do_setpoint
)
aeration_controller.set_output_limits(0, 20)
aeration_controller.set_integral_limits(-10, 10) # Set integral limits for anti-windup


# 4. Run the simulation loop
print(f"Initial State: Turbidity={simulator.current_quality.turbidity:.2f}, DO={simulator.current_quality.dissolved_oxygen:.2f}")

for i in range(150):
    current_quality = simulator.current_quality

    coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
    aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)

    simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)

    if (i + 1) % 15 == 0:
        print(f"Step {i+1:3}: Turbidity={simulator.current_quality.turbidity:.2f}, DO={simulator.current_quality.dissolved_oxygen:.2f}")

print(f"Final State:   Turbidity={simulator.current_quality.turbidity:.2f}, DO={simulator.current_quality.dissolved_oxygen:.2f}")
```

## Key Components

### `WaterQuality`
A simple dataclass located in `water_plant_controller/models/water_quality.py` that represents the state of water at a point in time.

### `PlantSimulator`
Located in `water_plant_controller/simulation/plant_simulator.py`. This class simulates the response of a water body to coagulant dosing and aeration based on a simple physics model.

### `PIDController`
A generic PID controller in `water_plant_controller/control/pid_controller.py`. It is reusable and can be configured for both direct-acting (e.g., heating) and reverse-acting (e.g., cooling, turbidity reduction) control loops.
