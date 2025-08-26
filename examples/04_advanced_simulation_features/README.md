# Example 4: Advanced Simulation Features

This example demonstrates how to enable and configure the advanced features of the `PlantSimulator` to create a more realistic and challenging control environment.

## The Goal

The goal is to show how to override the default simulation parameters to model two common real-world phenomena:
1.  **Time Delay**: The time it takes for a control action to have a measurable effect on the process. For example, the time it takes for a chemical dose to travel through a pipe to the sensor.
2.  **Non-Linearity**: Many real-world processes are not perfectly linear. In our case, we model that the efficiency of aeration decreases as the water becomes more saturated with oxygen.

Controlling a system with these features is significantly more difficult and often requires more careful PID tuning.

## The Code: `run_advanced_sim.py`

### 1. Custom Configuration
```python
advanced_sim_config = SIMULATION_DEFAULTS.copy()
advanced_sim_config.update({
    "time_delay_steps": 15,
    "aeration_non_linearity": 2.0
})
```
The key part of this example is the creation of a custom configuration dictionary. We start by copying the `SIMULATION_DEFAULTS` from the main settings file, and then we `update()` it with the parameters we want to change.

-   **`time_delay_steps`**: We set this to `15`. This means any action taken by the controllers (like applying a dose or changing the aeration rate) will not have any effect on the simulation until 15 steps *after* the action was taken.
-   **`aeration_non_linearity`**: We increase this to `2.0` (the default is 1.5). This makes the decrease in aeration efficiency more pronounced as the dissolved oxygen level gets closer to its saturation point.

### 2. Initializing the Simulator
```python
simulator = PlantSimulator(initial_quality, config=advanced_sim_config)
```
When we create the `PlantSimulator` instance, we simply pass our `advanced_sim_config` dictionary to it. The simulator will use these values instead of its defaults.

### 3. Running the Simulation
The rest of the script is very similar to the basic example. We set up the PID controllers with the default gains and run the simulation loop.

## How to Run This Example

Navigate to the root directory of the project and run the script directly:
```bash
python3 examples/04_advanced_simulation_features/run_advanced_sim.py
```
When you run this example, pay close attention to the output. You will notice a significant "lag" at the beginning of the simulation. For the first 15 steps, the turbidity and dissolved oxygen levels will not change, because the initial actions of the controllers are still "in the pipeline" due to the time delay. This demonstrates how delays can make a system much harder to control and is a critical factor to consider when tuning controllers for real-world applications.
