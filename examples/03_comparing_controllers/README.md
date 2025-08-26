# Example 3: Comparing Controller Performance (PID vs. On-Off)

This example guides you on how to use the main project scripts to run simulations with two different types of controllers—`PID` and `On-Off`—and how to visualize the results to compare their performance.

## The Goal

The goal is to demonstrate the practical difference between a sophisticated controller (PID) and a very simple one (On-Off). This comparison highlights why PID controllers are so widely used in industrial processes that require stability and precision.

-   **PID Controller**: Aims for a smooth, stable, and precise response.
-   **On-Off Controller**: A "bang-bang" controller that is either fully on or fully off. It is simple but typically very inefficient and unstable.

## How to Run the Comparison

This example uses the main scripts from the root of the project.

### Step 1: Run the PID Simulation

First, run the simulation using the default `pid` controller. We will direct the output to specific files so we don't overwrite them in the next step.

From the project's root directory, run:
```bash
python3 run_simulation.py --controller-type pid --log-file pid_log.csv
```

### Step 2: Run the On-Off Simulation

Next, run the simulation again, but this time select the `on-off` controller.

From the project's root directory, run:
```bash
python3 run_simulation.py --controller-type on-off --log-file on_off_log.csv
```

### Step 3: Visualize Both Results

Now that you have two log files, you can generate a plot for each one.

Generate the plot for the PID controller:
```bash
python3 visualize_log.py --log-file pid_log.csv --output-image pid_plot.png
```

Generate the plot for the On-Off controller:
```bash
python3 visualize_log.py --log-file on_off_log.csv --output-image on_off_plot.png
```

### Step 4: Compare the Output Images

You should now have two images in your root directory: `pid_plot.png` and `on_off_plot.png`.

-   **`pid_plot.png`**: Look at the plot for the PID controller. You will see that both the turbidity and dissolved oxygen levels move smoothly towards their setpoints and then hold steady with very little error.
-   **`on_off_plot.png`**: Now look at the On-Off controller's plot. You will see a dramatically different result. The process variables will constantly swing (oscillate) around the setpoint, never settling down. Because the controller can only be 100% on or 100% off, it is always over-correcting, leading to an unstable and inefficient system.

This comparison is also discussed in the main `DOCUMENTATION.md` file, which includes these plots for reference.
