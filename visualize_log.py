import argparse
import csv
import os
from datetime import datetime
from itertools import accumulate
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _safe_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _safe_int(row: Dict[str, str], key: str, default: int = 0) -> int:
    return int(_safe_float(row, key, float(default)))


def visualize_simulation_log(
    log_file: str,
    output_image: str,
    figsize: Tuple[int, int] = (12, 18),
    show_setpoints: bool = True,
) -> Optional[plt.Figure]:
    """
    Visualise the simulation CSV output produced by ``run_simulation.py``.

    The resulting figure contains six stacked subplots:
      1. Turbidity vs setpoint.
      2. Dissolved oxygen vs setpoint.
      3. Raw vs fused measurements (turbidity & dissolved oxygen).
      4. Sensor reliability and fault scores.
      5. Controller outputs with disturbances.
      6. Cumulative operating cost with actuator saturation indicators.
    """

    if not isinstance(log_file, str):
        raise TypeError("log_file must be a string")
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Log file not found: {log_file}")

    timestamps: List[datetime] = []
    turbidity: List[float] = []
    dissolved_oxygen: List[float] = []
    turbidity_setpoint: List[float] = []
    do_setpoint: List[float] = []
    coagulant_dose: List[float] = []
    aeration_rate: List[float] = []
    turbidity_disturbance: List[float] = []
    filtered_turbidity: List[float] = []
    filtered_do: List[float] = []
    turbidity_raw: List[float] = []
    turbidity_fused: List[float] = []
    turbidity_reliability_series: List[float] = []
    turbidity_monitor_score: List[float] = []
    turbidity_monitor_trip: List[float] = []
    do_raw: List[float] = []
    do_fused: List[float] = []
    do_reliability_series: List[float] = []
    do_monitor_score: List[float] = []
    do_monitor_trip: List[float] = []
    energy_scaling: List[float] = []
    energy_budget: List[float] = []
    sensor_fault_flags: List[float] = []
    sensor_turbidity_error: List[float] = []
    sensor_do_error: List[float] = []
    sensor_bias_estimate: List[float] = []
    sensor_bias_threshold: List[float] = []
    sensor_fault_likelihood: List[float] = []
    coagulant_saturation: List[int] = []
    aeration_saturation: List[int] = []
    coagulant_cost: List[float] = []
    aeration_cost: List[float] = []

    try:
        with open(log_file, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                timestamps.append(datetime.fromisoformat(row["timestamp"]))
                turbidity_soft = _safe_float(row, "turbidity")
                turbidity.append(turbidity_soft)
                dissolved_oxygen_soft = _safe_float(row, "dissolved_oxygen")
                dissolved_oxygen.append(dissolved_oxygen_soft)
                turbidity_setpoint.append(
                    _safe_float(row, "turbidity_setpoint", turbidity[-1])
                )
                do_setpoint.append(_safe_float(row, "do_setpoint", dissolved_oxygen[-1]))
                coagulant_dose.append(_safe_float(row, "coagulant_dose"))
                aeration_rate.append(_safe_float(row, "aeration_rate"))
                turbidity_disturbance.append(
                    _safe_float(row, "turbidity_disturbance")
                )
                filtered_turbidity.append(
                    _safe_float(row, "filtered_turbidity", turbidity_soft)
                )
                filtered_do.append(
                    _safe_float(row, "filtered_dissolved_oxygen", dissolved_oxygen_soft)
                )
                turbidity_raw.append(
                    _safe_float(row, "turbidity_raw_measurement", turbidity_soft)
                )
                turbidity_fused.append(
                    _safe_float(row, "fused_turbidity", turbidity_soft)
                )
                turbidity_reliability_series.append(
                    _safe_float(row, "turbidity_reliability", 1.0)
                )
                turbidity_monitor_score.append(
                    _safe_float(row, "turbidity_monitor_fault_score", 0.0)
                )
                turbidity_monitor_trip.append(
                    _safe_float(row, "turbidity_monitor_fault_trip", 0.0)
                )
                do_raw.append(
                    _safe_float(
                        row, "raw_dissolved_oxygen_measurement", dissolved_oxygen_soft
                    )
                )
                do_fused.append(
                    _safe_float(row, "fused_dissolved_oxygen", dissolved_oxygen_soft)
                )
                do_reliability_series.append(
                    _safe_float(row, "dissolved_oxygen_reliability", 1.0)
                )
                do_monitor_score.append(
                    _safe_float(row, "do_monitor_fault_score", 0.0)
                )
                do_monitor_trip.append(
                    _safe_float(row, "do_monitor_fault_trip", 0.0)
                )
                energy_scaling.append(
                    _safe_float(row, "energy_scaling_factor", 1.0)
                )
                energy_budget.append(
                    _safe_float(row, "energy_budget", 0.0)
                )
                coagulant_saturation.append(
                    _safe_int(row, "coagulant_saturated")
                )
                aeration_saturation.append(
                    _safe_int(row, "aeration_saturated")
                )
                coagulant_cost.append(_safe_float(row, "coagulant_cost"))
                aeration_cost.append(_safe_float(row, "aeration_cost"))
                sensor_fault_flags.append(
                    _safe_float(row, "sensor_fault_detected")
                )
                sensor_turbidity_error.append(
                    _safe_float(row, "sensor_turbidity_error")
                )
                sensor_do_error.append(
                    _safe_float(row, "sensor_do_error")
                )
                sensor_bias_estimate.append(
                    _safe_float(row, "sensor_bias_estimate")
                )
                sensor_bias_threshold.append(
                    _safe_float(row, "sensor_bias_threshold")
                )
                sensor_fault_likelihood.append(
                    _safe_float(row, "sensor_fault_likelihood")
                )
    except (IOError, FileNotFoundError) as exc:
        print(f"Unable to read log file '{log_file}': {exc}")
        return None
    except (ValueError, KeyError) as exc:
        print(f"Failed to parse log file '{log_file}': {exc}")
        return None

    if not timestamps:
        print(f"Warning: log file '{log_file}' contained no data. No figure created.")
        return None

    cumulative_coagulant_cost = list(accumulate(coagulant_cost))
    cumulative_aeration_cost = list(accumulate(aeration_cost))
    combined_monitor_trip = [
        max(t_trip, d_trip)
        for t_trip, d_trip in zip(turbidity_monitor_trip, do_monitor_trip)
    ]

    fig, axes = plt.subplots(6, 1, figsize=figsize, sharex=True)
    ax1, ax2, ax3, ax4, ax5, ax6 = axes
    fig.suptitle("Water Plant Simulation", fontsize=16, fontweight="bold")

    _plot_turbidity(
        ax1,
        timestamps,
        turbidity,
        turbidity_setpoint,
        show_setpoints,
        filtered_turbidity,
    )
    _plot_dissolved_oxygen(
        ax2,
        timestamps,
        dissolved_oxygen,
        do_setpoint,
        show_setpoints,
        filtered_do,
    )
    _plot_fusion_panel(
        ax3,
        timestamps,
        turbidity_raw,
        turbidity_fused,
        turbidity,
        do_raw,
        do_fused,
        dissolved_oxygen,
    )
    _plot_reliability_panel(
        ax4,
        timestamps,
        turbidity_reliability_series,
        do_reliability_series,
        turbidity_monitor_score,
        do_monitor_score,
        turbidity_monitor_trip,
        do_monitor_trip,
    )
    _plot_control_and_disturbance(
        ax5,
        timestamps,
        coagulant_dose,
        aeration_rate,
        turbidity_disturbance,
        sensor_bias_estimate,
        sensor_bias_threshold,
    )
    _plot_cost_and_saturation(
        ax6,
        timestamps,
        cumulative_coagulant_cost,
        cumulative_aeration_cost,
        coagulant_saturation,
        aeration_saturation,
        sensor_fault_flags,
        energy_scaling,
        combined_monitor_trip,
    )

    _print_summary(
        turbidity,
        dissolved_oxygen,
        coagulant_cost,
        aeration_cost,
        coagulant_saturation,
        aeration_saturation,
        sensor_fault_flags,
        sensor_turbidity_error,
        sensor_bias_estimate,
        sensor_bias_threshold,
        sensor_fault_likelihood,
        sensor_do_error,
        energy_scaling,
        energy_budget,
        turbidity_reliability_series,
        do_reliability_series,
        combined_monitor_trip,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    try:
        plt.savefig(output_image, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Figure saved to {output_image}")
    except Exception as exc:  # pragma: no cover - plotting backend dependent
        print(f"Failed to save figure: {exc}")
        return None

    return fig


def _plot_turbidity(
    ax,
    timestamps,
    turbidity,
    turbidity_setpoint,
    show_setpoints: bool,
    filtered_turbidity: List[float],
) -> None:
    ax.plot(
        timestamps,
        turbidity,
        label="Soft turbidity (controller input)",
        color="tab:blue",
        linewidth=2,
    )
    if show_setpoints and turbidity_setpoint:
        ax.plot(
            timestamps,
            turbidity_setpoint,
            label="Turbidity setpoint",
            color="tab:blue",
            linestyle="--",
            linewidth=1,
        )
    if filtered_turbidity and any(
        abs(ft - tp) > 1e-3 for ft, tp in zip(filtered_turbidity, turbidity)
    ):
        ax.plot(
            timestamps,
            filtered_turbidity,
            label="Kalman estimate (turbidity)",
            color="tab:cyan",
            linestyle="-.",
            linewidth=1.5,
        )
    ax.set_ylabel("Turbidity (NTU)", fontsize=12)
    ax.set_title("Turbidity Control", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    turbidity_mean = sum(turbidity) / len(turbidity)
    turbidity_std = (
        sum((value - turbidity_mean) ** 2 for value in turbidity) / len(turbidity)
    ) ** 0.5
    turbidity_stats = f"Mean: {turbidity_mean:.2f}, Std: {turbidity_std:.2f}"
    ax.text(
        0.02,
        0.98,
        turbidity_stats,
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )


def _plot_dissolved_oxygen(
    ax,
    timestamps,
    dissolved_oxygen,
    do_setpoint,
    show_setpoints: bool,
    filtered_do: List[float],
) -> None:
    ax.plot(
        timestamps,
        dissolved_oxygen,
        label="Soft DO (controller input)",
        color="tab:red",
        linewidth=2,
    )
    if show_setpoints and do_setpoint:
        ax.plot(
            timestamps,
            do_setpoint,
            label="DO setpoint",
            color="tab:red",
            linestyle="--",
            linewidth=1,
        )
    if filtered_do and any(
        abs(fd - do) > 1e-3 for fd, do in zip(filtered_do, dissolved_oxygen)
    ):
        ax.plot(
            timestamps,
            filtered_do,
            label="Kalman estimate (DO)",
            color="tab:pink",
            linestyle="-.",
            linewidth=1.5,
        )
    ax.set_ylabel("Dissolved oxygen (mg/L)", fontsize=12)
    ax.set_title("Dissolved Oxygen Control", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    do_mean = sum(dissolved_oxygen) / len(dissolved_oxygen)
    do_std = (
        sum((value - do_mean) ** 2 for value in dissolved_oxygen) / len(dissolved_oxygen)
    ) ** 0.5
    do_stats = f"Mean: {do_mean:.2f}, Std: {do_std:.2f}"
    ax.text(
        0.02,
        0.98,
        do_stats,
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.5),
    )


def _plot_fusion_panel(
    ax,
    timestamps,
    turbidity_raw,
    turbidity_fused,
    turbidity_soft,
    do_raw,
    do_fused,
    do_soft,
) -> None:
    if not timestamps:
        return

    turbidity_lines = [
        ax.plot(
            timestamps,
            turbidity_raw,
            label="Turbidity raw",
            color="tab:gray",
            alpha=0.5,
            linewidth=1.2,
        )[0],
        ax.plot(
            timestamps,
            turbidity_fused,
            label="Turbidity fused",
            color="tab:blue",
            linewidth=2,
        )[0],
        ax.plot(
            timestamps,
            turbidity_soft,
            label="Turbidity soft",
            color="tab:cyan",
            linestyle="--",
            linewidth=1.5,
        )[0],
    ]
    ax.set_ylabel("Turbidity (NTU)", fontsize=12)
    ax.set_title("Sensor Fusion Comparison", fontsize=14)
    ax.grid(True, alpha=0.3)

    ax_do = ax.twinx()
    do_lines = [
        ax_do.plot(
            timestamps,
            do_raw,
            label="DO raw",
            color="tab:olive",
            alpha=0.5,
            linewidth=1.2,
        )[0],
        ax_do.plot(
            timestamps,
            do_fused,
            label="DO fused",
            color="tab:green",
            linewidth=2,
        )[0],
        ax_do.plot(
            timestamps,
            do_soft,
            label="DO soft",
            color="tab:orange",
            linestyle="--",
            linewidth=1.5,
        )[0],
    ]
    ax_do.set_ylabel("Dissolved oxygen (mg/L)", fontsize=12)

    handles = turbidity_lines + do_lines
    labels = [line.get_label() for line in handles]
    ax.legend(handles, labels, loc="upper left", ncol=2)


def _plot_reliability_panel(
    ax,
    timestamps,
    turbidity_reliability,
    do_reliability,
    turbidity_fault_score,
    do_fault_score,
    turbidity_trip,
    do_trip,
) -> None:
    if not timestamps:
        return

    rel_lines = []
    if turbidity_reliability:
        rel_lines.append(
            ax.plot(
                timestamps,
                turbidity_reliability,
                label="Turbidity reliability",
                color="tab:blue",
                linewidth=2,
            )[0]
        )
    if do_reliability:
        rel_lines.append(
            ax.plot(
                timestamps,
                do_reliability,
                label="DO reliability",
                color="tab:green",
                linewidth=2,
            )[0]
        )

    ax.set_ylabel("Reliability", fontsize=12)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Sensor Reliability & Fault Scores", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.axhline(0.5, color="tab:gray", linestyle=":", linewidth=1, alpha=0.7)

    ax_fault = ax.twinx()
    fault_lines = []
    if turbidity_fault_score:
        fault_lines.append(
            ax_fault.plot(
                timestamps,
                turbidity_fault_score,
                label="Turbidity fault score",
                color="tab:purple",
                linestyle="--",
                linewidth=1.5,
            )[0]
        )
    if do_fault_score:
        fault_lines.append(
            ax_fault.plot(
                timestamps,
                do_fault_score,
                label="DO fault score",
                color="tab:orange",
                linestyle="--",
                linewidth=1.5,
            )[0]
        )
    if turbidity_trip and any(flag >= 0.5 for flag in turbidity_trip):
        fault_lines.append(
            ax_fault.step(
                timestamps,
                turbidity_trip,
                label="Turbidity trip",
                color="tab:blue",
                alpha=0.7,
                linewidth=1.5,
                where="post",
            )[0]
        )
    if do_trip and any(flag >= 0.5 for flag in do_trip):
        fault_lines.append(
            ax_fault.step(
                timestamps,
                do_trip,
                label="DO trip",
                color="tab:green",
                alpha=0.7,
                linewidth=1.5,
                where="post",
            )[0]
        )
    ax_fault.set_ylabel("Fault score / trip", fontsize=12)
    ax_fault.set_ylim(-0.05, 1.05)

    handles = rel_lines + fault_lines
    if handles:
        ax.legend(handles, [h.get_label() for h in handles], loc="upper right", ncol=2)


def _plot_control_and_disturbance(
    ax,
    timestamps,
    coagulant_dose,
    aeration_rate,
    turbidity_disturbance,
    sensor_bias,
    sensor_threshold,
) -> None:
    control_lines = []
    control_lines.append(
        ax.plot(
            timestamps,
            coagulant_dose,
            label="Coagulant dose",
            color="tab:orange",
            linewidth=2,
        )[0]
    )
    control_lines.append(
        ax.plot(
            timestamps,
            aeration_rate,
            label="Aeration rate",
            color="tab:green",
            linewidth=2,
        )[0]
    )

    ax.set_ylabel("Control output", fontsize=12)
    ax.set_title("Control Inputs and Disturbances", fontsize=14)
    ax.grid(True, alpha=0.3)

    ax_dist = ax.twinx()
    disturbance_lines = []

    if any(abs(value) > 1e-6 for value in turbidity_disturbance):
        disturbance_lines.append(
            ax_dist.plot(
                timestamps,
                turbidity_disturbance,
                label="Turbidity disturbance",
                color="tab:purple",
                linestyle="--",
                linewidth=1.5,
            )[0]
        )

    if any(abs(err) > 1e-6 for err in sensor_bias):
        disturbance_lines.append(
            ax_dist.plot(
                timestamps,
                sensor_bias,
                label="Sensor bias (turbidity)",
                color="tab:red",
                linestyle=":",
                linewidth=1.5,
            )[0]
        )
    if any(th > 0 for th in sensor_threshold):
        disturbance_lines.append(
            ax_dist.plot(
                timestamps,
                sensor_threshold,
                label="Bias threshold",
                color="tab:pink",
                linestyle="--",
                linewidth=1.2,
            )[0]
        )

    ax_dist.set_ylabel("Disturbance / sensor error (NTU)", fontsize=12)

    if control_lines:
        ax.legend(control_lines, [line.get_label() for line in control_lines], loc="upper left")
    if disturbance_lines:
        ax_dist.legend(
            disturbance_lines, [line.get_label() for line in disturbance_lines], loc="upper right"
        )


def _plot_cost_and_saturation(
    ax,
    timestamps,
    cumulative_coagulant_cost,
    cumulative_aeration_cost,
    coagulant_saturation,
    aeration_saturation,
    sensor_fault_flags,
    energy_scaling,
    monitor_trip_flags,
) -> None:
    ax.plot(
        timestamps,
        cumulative_coagulant_cost,
        label="Cumulative coagulant cost",
        color="tab:orange",
        linewidth=2,
    )
    ax.plot(
        timestamps,
        cumulative_aeration_cost,
        label="Cumulative aeration cost",
        color="tab:green",
        linewidth=2,
    )
    ax.set_ylabel("Cumulative Cost", fontsize=12)
    ax.set_title("Cost and Actuator Saturation", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")

    ax_sat = ax.twinx()
    ax_sat.step(
        timestamps,
        coagulant_saturation,
        label="Coagulant saturation",
        color="tab:red",
        alpha=0.3,
        linewidth=1.5,
        where="post",
    )
    ax_sat.step(
        timestamps,
        aeration_saturation,
        label="Aeration saturation",
        color="tab:blue",
        alpha=0.3,
        linewidth=1.5,
        where="post",
    )
    ax_sat.set_ylabel("Saturation (0/1)", fontsize=12)
    ax_sat.set_ylim(-0.1, 1.1)
    ax_sat.legend(loc="upper right")

    if any(sensor_fault_flags):
        ax_sat.step(
            timestamps,
            sensor_fault_flags,
            label="Sensor fault",
            color="tab:gray",
            alpha=0.6,
            linewidth=1.5,
            where="post",
        )
        ax_sat.legend(loc="upper right")
    if any(flag >= 0.5 for flag in monitor_trip_flags):
        ax_sat.step(
            timestamps,
            monitor_trip_flags,
            label="Monitor trip (any channel)",
            color="tab:purple",
            alpha=0.6,
            linewidth=1.5,
            where="post",
        )
        ax_sat.legend(loc="upper right")
    if any(scale != 1.0 for scale in energy_scaling):
        ax_sat.plot(
            timestamps,
            energy_scaling,
            label="Energy scaling factor",
            color="tab:brown",
            linestyle="--",
            linewidth=1.2,
        )
        ax_sat.legend(loc="upper right")


def _print_summary(
    turbidity: List[float],
    dissolved_oxygen: List[float],
    coagulant_cost: List[float],
    aeration_cost: List[float],
    coagulant_saturation: List[int],
    aeration_saturation: List[int],
    sensor_fault_flags: List[float],
    sensor_turbidity_error: List[float],
    sensor_bias_estimate: List[float],
    sensor_bias_threshold: List[float],
    sensor_fault_likelihood: List[float],
    sensor_do_error: List[float],
    energy_scaling: List[float],
    energy_budget: List[float],
    turbidity_reliability: List[float],
    do_reliability: List[float],
    monitor_trip_flags: List[float],
) -> None:
    total_coagulant_cost = sum(coagulant_cost)
    total_aeration_cost = sum(aeration_cost)
    total_cost = total_coagulant_cost + total_aeration_cost

    coagulant_sat_rate = (
        sum(coagulant_saturation) / len(coagulant_saturation) if coagulant_saturation else 0.0
    )
    aeration_sat_rate = (
        sum(aeration_saturation) / len(aeration_saturation) if aeration_saturation else 0.0
    )

    print("----- Precision Control Summary -----")
    print(f"Average turbidity: {sum(turbidity)/len(turbidity):.2f} NTU")
    print(f"Average dissolved oxygen: {sum(dissolved_oxygen)/len(dissolved_oxygen):.2f} mg/L")
    print(f"Total coagulant cost: {total_coagulant_cost:.2f}")
    print(f"Total aeration cost: {total_aeration_cost:.2f}")
    print(f"Combined operating cost: {total_cost:.2f}")
    print(f"Coagulant saturation rate: {coagulant_sat_rate*100:.1f}%")
    print(f"Aeration saturation rate: {aeration_sat_rate*100:.1f}%")
    total_faults = int(sum(1 for flag in sensor_fault_flags if flag >= 0.5))
    avg_turbidity_error = (
        sum(sensor_turbidity_error) / len(sensor_turbidity_error)
        if sensor_turbidity_error
        else 0.0
    )
    avg_do_error = (
        sum(sensor_do_error) / len(sensor_do_error)
        if sensor_do_error
        else 0.0
    )
    avg_bias = (
        sum(abs(bias) for bias in sensor_bias_estimate) / len(sensor_bias_estimate)
        if sensor_bias_estimate
        else 0.0
    )
    max_bias = max((abs(bias) for bias in sensor_bias_estimate), default=0.0)
    avg_threshold = (
        sum(sensor_bias_threshold) / len(sensor_bias_threshold)
        if sensor_bias_threshold
        else 0.0
    )
    peak_likelihood = max(sensor_fault_likelihood or [0.0])

    print(f"Sensor fault events: {total_faults}")
    print(f"Average sensor turbidity error: {avg_turbidity_error:.3f}")
    print(f"Average bias (filtered): {avg_bias:.3f} (max {max_bias:.3f})")
    if sensor_bias_threshold:
        print(f"Average bias threshold: {avg_threshold:.3f}")
    if sensor_fault_likelihood:
        print(f"Peak fault likelihood: {peak_likelihood:.2f}")
    print(f"Average sensor DO error: {avg_do_error:.3f}")
    if turbidity_reliability:
        avg_turbidity_reliability = sum(turbidity_reliability) / len(turbidity_reliability)
        print(f"Average turbidity reliability: {avg_turbidity_reliability:.3f}")
    if do_reliability:
        avg_do_reliability = sum(do_reliability) / len(do_reliability)
        print(f"Average DO reliability: {avg_do_reliability:.3f}")
    monitor_events = sum(1 for flag in monitor_trip_flags if flag >= 0.5)
    if monitor_events:
        print(f"Monitor trip samples: {monitor_events}")
    if energy_scaling:
        avg_scale = sum(energy_scaling) / len(energy_scaling)
        min_scale = min(energy_scaling)
        budget = energy_budget[0] if energy_budget else 0.0
        print(f"Energy budget per step: {budget:.2f}")
        print(f"Average energy scaling factor: {avg_scale:.3f}")
        print(f"Minimum energy scaling factor: {min_scale:.3f}")
    print("-------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualise the simulation log.")
    parser.add_argument(
        "--log-file",
        type=str,
        default="simulation_log.csv",
        help="Path to the simulation CSV file.",
    )
    parser.add_argument(
        "--output-image",
        type=str,
        default="simulation_plot.png",
        help="Destination file for the rendered figure.",
    )

    args = parser.parse_args()

    visualize_simulation_log(
        log_file=args.log_file,
        output_image=args.output_image,
    )
