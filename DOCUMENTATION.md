# Project Documentation: Water Plant Process Controller

## 1. Introduction

Welcome to the detailed documentation for the Water Plant Process Controller project. This document provides a comprehensive overview of the system's architecture, components, and usage.

This project is a Python-based simulation framework for a water treatment process. It is designed to demonstrate a closed-loop control system using a generic PID (Proportional-Integral-Derivative) controller to manage water quality parameters, such as turbidity and dissolved oxygen.

The primary goals of this project are:
- To provide a clear, well-structured example of control system implementation.
- To offer a reusable and configurable framework for simulating and testing control algorithms.
- To serve as an educational tool for understanding PID control and process simulation.

---

## 2. System Architecture

The project is designed with a clear separation of concerns, dividing the system into three main parts: **Models**, the **Simulator**, and the **Controller**.

```
+-----------------+      +--------------------+      +--------------------+
|   User / Test   |----->|   PID Controller   |----->|  Plant Simulator   |
|     Script      |      | (Control Algorithm)|      | (Physical Process) |
+-----------------+      +--------------------+      +--------------------+
        ^                        |                             |
        |                        |                             |
        +------------------------+-----------------------------+
                                 |
                          (Measurement)
```

1.  **Plant Simulator**: Represents the physical water treatment plant. It maintains the current state of the water (`WaterQuality`) and simulates how it changes over time in response to control actions (e.g., chemical dosing, aeration).
2.  **PID Controller**: The brain of the operation. It calculates the necessary control actions by comparing the current measured value of a water quality parameter to its desired **setpoint**.
3.  **Models**: Simple data structures (like `WaterQuality`) that define the state of the system.
4.  **User/Test Script**: The entry point that initializes the simulator and controllers, and runs the simulation loop, connecting the output of the simulator (current state) back to the input of the controller.

---

## 3. Component Deep Dive

### 3.1. `WaterQuality` Model
- **Location**: `water_plant_controller/models/water_quality.py`
- **Description**: A simple dataclass that acts as a snapshot of the water's state at a specific time.
- **Attributes**:
    - `timestamp`: `datetime` - The time of the measurement.
    - `ph`: `float` - The pH level (currently constant in the simulation).
    - `turbidity`: `float` - A measure of water cloudiness (NTU).
    - `dissolved_oxygen`: `float` - The concentration of dissolved oxygen (mg/L).

### 3.2. `PlantSimulator`
- **Location**: `water_plant_controller/simulation/plant_simulator.py`
- **Description**: Simulates the physics of the water treatment process. The `step()` method advances the simulation by one time step.
- **Key Logic**:
    - **Turbidity Reduction**: The addition of a coagulant reduces turbidity. The rate of reduction is proportional to the current turbidity and the coagulant dose.
    - **Dissolved Oxygen (DO)**: The DO level is affected by two main factors:
        1.  **Aeration**: Increases DO, pushing it towards a natural saturation point. The rate of increase is proportional to the aeration rate and the current "DO deficit" (`saturation - current_do`).
        2.  **Consumption**: Natural processes consume DO at a constant rate.
- **Configuration**: The simulator's physical parameters (e.g., `do_increase_rate`, `turbidity_decay_factor`) are loaded from `config/settings.py`.

### 3.3. `PIDController`
- **Location**: `water_plant_controller/control/pid_controller.py`
- **Description**: A generic and reusable PID controller.
- **Core Parameters (`__init__`)**:
    - `Kp`: Proportional gain. Reacts to the current error.
    - `Ki`: Integral gain. Corrects for past, cumulative error and eliminates steady-state error.
    - `Kd`: Derivative gain. Responds to the rate of change of the error, helping to dampen oscillations.
    - `setpoint`: The target value for the process variable.
    - `reverse_acting`: A boolean that inverts the controller's response. Set to `True` for processes where an increase in output should cause a decrease in the measured variable (e.g., turbidity control).
- **Key Methods**:
    - `calculate(current_value)`: Computes the control output based on the current measured value.
    - `set_output_limits(min, max)`: Constrains the controller's output to a realistic range (e.g., a valve cannot be more than 100% open).
    - `set_integral_limits(min, max)`: A crucial part of **anti-windup**. This prevents the integral term from accumulating excessively when the controller output is saturated, which would otherwise cause significant overshoot.

---

## 4. Configuration

All key parameters are centralized in `config/settings.py`. This allows for easy tuning and experimentation without modifying the core logic.

- **`SIMULATION_DEFAULTS`**: A dictionary containing the physical constants for the `PlantSimulator`.
- **`PID_GAINS`**: A dictionary containing the `Kp`, `Ki`, and `Kd` gains for each controller used in the system.

---

## 5. How to Run and Extend the Project

### 5.1. Running Tests
To verify the integrity of the system, run all tests from the root directory:
```bash
python3 -m unittest discover tests
```

### 5.2. Running a Simulation
The example in `README.md` provides a clear template for setting up and running a closed-loop simulation. You can save it as a Python file and run it directly.

### 5.3. Extending the Project
This project is designed to be extensible. Here are some ideas for future improvements:
- **Data Logging and Visualization**: Implement logging of simulation data to a file and create scripts to plot the results.
- **Advanced Simulation**: Introduce time delays, non-linear effects, or noise to the simulator for more realism.
- **Command-Line Interface (CLI)**: Create a CLI to run simulations with different parameters without editing code.
- **New Controller Types**: Implement and compare other control strategies, such as an On-Off controller.

---
This concludes the detailed documentation. For a quick start guide, please refer to `README.md`.
