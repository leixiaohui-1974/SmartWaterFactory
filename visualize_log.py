import csv
import argparse
import matplotlib.pyplot as plt
from datetime import datetime

def visualize_simulation_log(log_file: str, output_image: str):
    """
    Reads a simulation log file and generates a plot of the results.

    :param log_file: Path to the input CSV log file.
    :param output_image: Path to save the output plot image.
    """
    # Data lists
    timestamps = []
    turbidity = []
    dissolved_oxygen = []
    turbidity_setpoint = []
    do_setpoint = []

    # Read data from CSV
    with open(log_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            timestamps.append(datetime.fromisoformat(row['timestamp']))
            turbidity.append(float(row['turbidity']))
            dissolved_oxygen.append(float(row['dissolved_oxygen']))
            turbidity_setpoint.append(float(row['turbidity_setpoint']))
            do_setpoint.append(float(row['do_setpoint']))

    # Create plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    fig.suptitle('Water Plant Simulation Results', fontsize=16)

    # Plot 1: Turbidity
    ax1.plot(timestamps, turbidity, label='Measured Turbidity', color='b')
    ax1.plot(timestamps, turbidity_setpoint, label='Turbidity Setpoint', color='b', linestyle='--')
    ax1.set_ylabel('Turbidity (NTU)')
    ax1.legend()
    ax1.grid(True)

    # Plot 2: Dissolved Oxygen
    ax2.plot(timestamps, dissolved_oxygen, label='Measured Dissolved Oxygen', color='r')
    ax2.plot(timestamps, do_setpoint, label='DO Setpoint', color='r', linestyle='--')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Dissolved Oxygen (mg/L)')
    ax2.legend()
    ax2.grid(True)

    # Save the plot
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_image)
    print(f"Plot saved to {output_image}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Visualize simulation log data.")
    parser.add_argument('--log-file', type=str, default='simulation_log.csv', help='Path to the input CSV log file.')
    parser.add_argument('--output-image', type=str, default='simulation_plot.png', help='Path to save the output plot image.')

    args = parser.parse_args()

    visualize_simulation_log(
        log_file=args.log_file,
        output_image=args.output_image
    )
