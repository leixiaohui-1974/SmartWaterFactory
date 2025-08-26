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

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Install dependencies:**
    This project requires `matplotlib` for visualization. Install it using the provided `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

This project includes scripts to run the simulation, log the results, and visualize the output.

### 1. Running the Simulation
To run the simulation and generate a `simulation_log.csv` file, execute the following command from the root directory:
```bash
python3 run_simulation.py
```
This will run a default simulation of 300 steps. You can also customize the simulation with command-line arguments:
```bash
python3 run_simulation.py --steps 500 --turbidity-setpoint 4.5 --log-file custom_log.csv
```
You can also choose the controller type (`pid` or `on-off`):
```bash
python3 run_simulation.py --controller-type on-off
```

### 2. Visualizing the Results
After running the simulation, you can generate a plot of the results:
```bash
python3 visualize_log.py
```
This script reads `simulation_log.csv` and saves the output as `simulation_plot.png`. You can specify different input and output files:
```bash
python3 visualize_log.py --log-file custom_log.csv --output-image custom_plot.png
```

### 3. Running Tests
To verify that the system is working correctly, you can run all the tests from the root directory:
```bash
python3 -m unittest discover tests
```

## Examples and Tutorials

This project includes a comprehensive set of examples that serve as a beginner-to-advanced development guide. You can find them in the `/examples` directory.

Each example is self-contained in its own folder and includes a `README.md` file that explains the concepts and the code.

-   **[Example 1: Basic Simulation](./examples/01_basic_simulation/README.md)**
-   **[Example 2: PID Controller Tuning](./examples/02_tuning_pid_controller/README.md)**
-   **[Example 3: Controller Comparison](./examples/03_comparing_controllers/README.md)**
-   **[Example 4: Advanced Simulation Features](./examples/04_advanced_simulation_features/README.md)**
-   **[Example 5: Extending the Simulator Guide](./examples/05_extending_the_simulator/README.md)**

## Key Components

### `WaterQuality`
A simple dataclass located in `water_plant_controller/models/water_quality.py` that represents the state of water at a point in time.

### `PlantSimulator`
Located in `water_plant_controller/simulation/plant_simulator.py`. This class simulates the response of a water body to coagulant dosing and aeration based on a simple physics model.

### `PIDController`
A generic PID controller in `water_plant_controller/control/pid_controller.py`. It is reusable and can be configured for both direct-acting (e.g., heating) and reverse-acting (e.g., cooling, turbidity reduction) control loops.
