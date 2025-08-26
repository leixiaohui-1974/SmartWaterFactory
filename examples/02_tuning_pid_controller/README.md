# Example 2: PID Controller Tuning

This example demonstrates the critical concept of **PID tuning** and how different gain values (`Kp`, `Ki`, `Kd`) can dramatically affect the performance of a control system.

## The Goal

The goal is to visually show the difference between an "aggressively" tuned controller and a "conservatively" tuned controller.
-   **Aggressive Tuning**: Often results in a fast response, but can lead to **overshoot** (where the process variable goes past the setpoint) and **oscillation** (swinging back and forth around the setpoint).
-   **Conservative Tuning**: Typically results in a smoother, more stable response with less overshoot, but may be slower to reach the setpoint.

## The Code: `run_tuning_sim.py`

This script runs two separate simulations of the turbidity controller, each with a different set of PID gains.

### The `run_simulation_with_gains` Function
This helper function takes `Kp`, `Ki`, and `Kd` as arguments and runs a simulation using them. This allows us to easily test different tuning profiles. Note that in this example, we are only focused on the turbidity controller; the dissolved oxygen controller is replaced with a "dummy" that does nothing.

### Simulation 1: Aggressive Tuning
```python
run_simulation_with_gains(
    name="Aggressive Tuning",
    Kp=0.2,
    Ki=0.1, # High integral gain
    Kd=0.1
)
```
In this first run, we use a relatively high integral gain (`Ki = 0.1`). The integral term accumulates past errors, and if this gain is too high, it can "wind up" and push the controller to keep applying a strong action even when the error is getting small. This is what causes overshoot.

### Simulation 2: Conservative Tuning
```python
run_simulation_with_gains(
    name="Conservative Tuning",
    Kp=0.1,
    Ki=0.01, # Lower integral gain
    Kd=0.5   # Higher derivative gain
)
```
In the second run, we do two things to make the controller more stable:
1.  **Lower `Ki`**: We reduce the integral gain to `0.01`, which lessens the impact of past errors and reduces the tendency to overshoot.
2.  **Higher `Kd`**: We increase the derivative gain to `0.5`. The derivative term acts as a "brake" by reacting to how fast the error is changing. A higher `Kd` makes the controller more proactive in preventing overshoot, leading to a more dampened and stable response.

## How to Run This Example

Navigate to the root directory of the project and run the script directly:
```bash
python3 examples/02_tuning_pid_controller/run_tuning_sim.py
```
Observe the output from the two simulations. You should see that the "Aggressive" run causes the turbidity to drop well below the setpoint of 5.0 before recovering, while the "Conservative" run approaches the setpoint more smoothly. This illustrates the fundamental trade-off in control tuning between speed and stability.
