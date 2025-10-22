#!/usr/bin/env python3
"""
Batch runner that generates artefacts (CSV log, PNG plot, Markdown report)
for the key simulation-oriented examples in the SmartWaterFactory project.

The script focuses on the examples that are fully self-contained in code and
do not require external services (e.g. API server).  Each run reuses the
core `run_and_log_simulation` helper to ensure consistent diagnostics while
mirroring the configuration that the example documentation describes.
"""

from __future__ import annotations

import csv
import math
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Ensure imports resolve even when the script is launched directly.
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings  # noqa: E402
from run_simulation import run_and_log_simulation  # noqa: E402
from visualize_log import visualize_simulation_log  # noqa: E402


SensorProvider = Callable[..., Dict[str, float]]
DisturbanceProvider = Callable[..., Dict[str, float]]


@contextmanager
def _temporary_mapping_patch(mapping: Dict, updates: Dict):
    """Temporarily patch a mapping object and restore previous values."""

    original = {}
    sentinel = object()
    try:
        for key, value in updates.items():
            original[key] = mapping.get(key, sentinel)
            mapping[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is sentinel:
                mapping.pop(key, None)
            else:
                mapping[key] = value


def _summarise_csv(csv_path: Path) -> Dict[str, float]:
    """Compute basic statistics from a simulation CSV log."""
    timestamps: list[datetime] = []
    turbidity: list[float] = []
    dissolved_oxygen: list[float] = []
    coagulant: list[float] = []
    aeration: list[float] = []
    faults: int = 0
    redundant_active: int = 0

    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamps.append(datetime.fromisoformat(row["timestamp"]))
            turbidity.append(float(row["turbidity"]))
            dissolved_oxygen.append(float(row["dissolved_oxygen"]))
            coagulant.append(float(row.get("coagulant_dose", 0.0)))
            aeration.append(float(row.get("aeration_rate", 0.0)))
            faults += 1 if float(row.get("sensor_fault_detected", 0.0)) >= 0.5 else 0
            redundant_active += 1 if float(row.get("redundant_sensor_active", 0.0)) >= 0.5 else 0

    def _avg(values: Iterable[float]) -> float:
        seq = list(values)
        return sum(seq) / len(seq) if seq else float("nan")

    return {
        "steps": len(timestamps),
        "avg_turbidity": _avg(turbidity),
        "avg_dissolved_oxygen": _avg(dissolved_oxygen),
        "final_turbidity": turbidity[-1] if turbidity else float("nan"),
        "final_dissolved_oxygen": dissolved_oxygen[-1] if dissolved_oxygen else float("nan"),
        "avg_coagulant_dose": _avg(coagulant),
        "avg_aeration_rate": _avg(aeration),
        "fault_samples": faults,
        "redundant_active_samples": redundant_active,
    }


def _write_report(report_path: Path, title: str, summary: Dict[str, float]) -> None:
    """Persist a short Markdown report summarising the run."""

    lines = [
        f"# {title}",
        "",
        f"- 运行步数：{int(summary['steps'])}",
        f"- 平均浊度：{summary['avg_turbidity']:.2f} NTU",
        f"- 平均溶解氧：{summary['avg_dissolved_oxygen']:.2f} mg/L",
        f"- 末尾浊度：{summary['final_turbidity']:.2f} NTU",
        f"- 末尾溶解氧：{summary['final_dissolved_oxygen']:.2f} mg/L",
        f"- 平均混凝剂投加：{summary['avg_coagulant_dose']:.2f} 单位",
        f"- 平均曝气速率：{summary['avg_aeration_rate']:.2f} 单位",
        f"- 传感器故障样本数：{int(summary['fault_samples'])}",
        f"- 冗余传感器启用样本数：{int(summary['redundant_active_samples'])}",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


@dataclass
class ExampleRun:
    name: str
    directory: Path
    log_filename: str
    plot_filename: str
    report_filename: str
    steps: int
    controller_type: str
    turbidity_setpoint: float = 5.0
    do_setpoint: float = 8.5
    sensor_provider: Optional[SensorProvider] = None
    redundant_sensor_provider: Optional[SensorProvider] = None
    disturbance_provider: Optional[DisturbanceProvider] = None
    settings_patch: Optional[Dict[str, Dict]] = None

    def execute(self) -> None:
        """Run the simulation, generate artefacts, and persist a summary."""

        self.directory.mkdir(parents=True, exist_ok=True)
        log_path = self.directory / self.log_filename
        plot_path = self.directory / self.plot_filename
        report_path = self.directory / self.report_filename

        patch = self.settings_patch or {}
        context_managers = []

        if patch:
            for target_name, updates in patch.items():
                target_mapping = getattr(settings, target_name)
                context_managers.append(_temporary_mapping_patch(target_mapping, updates))

        with _nested(context_managers):
            success = run_and_log_simulation(
                steps=self.steps,
                log_file=str(log_path),
                turbidity_setpoint=self.turbidity_setpoint,
                do_setpoint=self.do_setpoint,
                controller_type=self.controller_type,
                sensor_provider=self.sensor_provider,
                redundant_sensor_provider=self.redundant_sensor_provider,
                disturbance_provider=self.disturbance_provider,
            )
        if not success:
            raise RuntimeError(f"{self.name} simulation failed to complete")

        visualize_simulation_log(
            log_file=str(log_path),
            output_image=str(plot_path),
        )

        summary = _summarise_csv(log_path)
        _write_report(report_path, self.name, summary)
        print(f"[ok] {self.name} artefacts已生成：{log_path.name}, {plot_path.name}, {report_path.name}")


@contextmanager
def _nested(managers: Iterable):
    """Utility to enter multiple context managers and exit them safely."""
    exits = []
    try:
        for manager in managers:
            exits.append(manager.__exit__)
            manager.__enter__()
        yield
    finally:
        for exit_func in reversed(exits):
            exit_func(None, None, None)


def sensor_fault_model(*, step_index: int, **_) -> Dict[str, float]:
    """Bias turbidity measurements between steps 80-120 to trigger redundancy."""
    bias = 0.0
    if 80 <= step_index < 120:
        bias = 6.0
    noise = math.sin(step_index / 18.0) * 0.1
    return {"turbidity": bias + noise, "dissolved_oxygen": 0.0}


def redundant_sensor(*, step_index: int, true_quality, **_) -> Dict[str, float]:
    """Secondary sensor that drifts mildly but stays within tolerance."""
    return {
        "turbidity": math.sin(step_index / 40.0) * 0.05,
        "dissolved_oxygen": math.cos(step_index / 50.0) * 0.03,
    }


def _make_disturbance(
    sine_amplitude: float,
    sine_period: float,
    pulses: list[tuple[int, int, float]],
) -> DisturbanceProvider:
    """Factory returning a disturbance provider composed of sine + pulses."""

    def disturbance(
        *,
        step_index: int,
        timestamp,
        quality,
        inputs,
    ) -> Dict[str, float]:
        value = sine_amplitude * math.sin(step_index / sine_period)
        for start, end, offset in pulses:
            if start <= step_index < end:
                value += offset
        return {"turbidity": value}

    return disturbance


BASELINE_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.2,
    sine_period=22.0,
    pulses=[(80, 120, 0.6)],
)

PID_AGGRESSIVE_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.25,
    sine_period=18.0,
    pulses=[(50, 90, 0.9), (130, 150, -0.4)],
)

PID_CONSERVATIVE_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.18,
    sine_period=24.0,
    pulses=[(60, 110, 0.5)],
)

ADVANCED_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.35,
    sine_period=16.0,
    pulses=[(40, 70, 1.2), (120, 160, -0.8)],
)

def adaptive_demo_disturbance(
    *,
    step_index: int,
    timestamp,
    quality,
    inputs,
) -> Dict[str, float]:
    """Shared disturbance profile for the adaptive vs precision comparison."""

    wave = 0.4 * math.sin(step_index / 18.0)
    pulse = 0.0
    if 70 <= step_index < 110:
        pulse += 1.5
    if 140 <= step_index < 170:
        pulse -= 1.0
    return {"turbidity": wave + pulse}


def closed_loop_validation_disturbance(*, step_index: int, timestamp, quality, inputs) -> dict:
    """Disturbance pattern for the closed-loop validation example."""

    slow_wave = 0.3 * math.sin(step_index / 20.0)
    pulse = 0.0
    if 40 <= step_index < 55:
        pulse = 2.0
    elif 110 <= step_index < 125:
        pulse = 1.0
    return {"turbidity": slow_wave + pulse}


SENSOR_FAULT_BASE_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.22,
    sine_period=20.0,
    pulses=[(60, 100, 0.4)],
)

ENERGY_BUDGET_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.3,
    sine_period=26.0,
    pulses=[(70, 130, -0.6), (150, 180, 0.7)],
)

LONG_RUN_DISTURBANCE = _make_disturbance(
    sine_amplitude=0.25,
    sine_period=30.0,
    pulses=[(120, 200, 0.5), (300, 360, -0.4), (420, 460, 0.6)],
)


def build_runs() -> list[ExampleRun]:
    """Prepare the list of example scenarios to execute."""

    return [
        ExampleRun(
            name="基础仿真示例",
            directory=PROJECT_ROOT / "examples" / "01_basic_simulation" / "artifacts",
            log_filename="basic_simulation.csv",
            plot_filename="basic_simulation.png",
            report_filename="basic_simulation_report.md",
            steps=180,
            controller_type="pid",
            disturbance_provider=BASELINE_DISTURBANCE,
        ),
        ExampleRun(
            name="PID 调参对比 - 激进参数",
            directory=PROJECT_ROOT / "examples" / "02_tuning_pid_controller" / "artifacts",
            log_filename="pid_aggressive.csv",
            plot_filename="pid_aggressive.png",
            report_filename="pid_aggressive_report.md",
            steps=180,
            controller_type="pid",
            disturbance_provider=PID_AGGRESSIVE_DISTURBANCE,
            settings_patch={
                "PID_GAINS": {
                    "dosing_controller": {"Kp": 0.2, "Ki": 0.1, "Kd": 0.1},
                }
            },
        ),
        ExampleRun(
            name="PID 调参对比 - 温和参数",
            directory=PROJECT_ROOT / "examples" / "02_tuning_pid_controller" / "artifacts",
            log_filename="pid_conservative.csv",
            plot_filename="pid_conservative.png",
            report_filename="pid_conservative_report.md",
            steps=180,
            controller_type="pid",
            disturbance_provider=PID_CONSERVATIVE_DISTURBANCE,
            settings_patch={
                "PID_GAINS": {
                    "dosing_controller": {"Kp": 0.1, "Ki": 0.01, "Kd": 0.5},
                }
            },
        ),
        ExampleRun(
            name="高级仿真（延迟+非线性）",
            directory=PROJECT_ROOT / "examples" / "04_advanced_simulation_features" / "artifacts",
            log_filename="advanced_simulation.csv",
            plot_filename="advanced_simulation.png",
            report_filename="advanced_simulation_report.md",
            steps=220,
            controller_type="pid",
            disturbance_provider=ADVANCED_DISTURBANCE,
            settings_patch={
                "SIMULATION_DEFAULTS": {
                    "time_delay_steps": 15,
                    "aeration_non_linearity": 2.0,
                }
            },
        ),
        ExampleRun(
            name="闭环验证演示",
            directory=PROJECT_ROOT / "examples" / "11_closed_loop_validation" / "artifacts",
            log_filename="closed_loop_validation.csv",
            plot_filename="closed_loop_validation.png",
            report_filename="closed_loop_validation_report.md",
            steps=220,
            controller_type="pid",
     
            disturbance_provider=closed_loop_validation_disturbance,
        ),
        ExampleRun(
            name="自适应 vs 精细 PID（精细模式）",
            directory=PROJECT_ROOT / "examples" / "12_adaptive_control_demo" / "artifacts",
            log_filename="precision_pid.csv",
            plot_filename="precision_pid.png",
            report_filename="precision_pid_report.md",
            steps=220,
            controller_type="precision-pid",
            disturbance_provider=adaptive_demo_disturbance,
        ),
        ExampleRun(
            name="自适应 vs 精细 PID（自适应模式）",
            directory=PROJECT_ROOT / "examples" / "12_adaptive_control_demo" / "artifacts",
            log_filename="adaptive_pid.csv",
            plot_filename="adaptive_pid.png",
            report_filename="adaptive_pid_report.md",
            steps=220,
            controller_type="adaptive-pid",
            disturbance_provider=adaptive_demo_disturbance,
        ),
        ExampleRun(
            name="冗余传感器与降级演示",
            directory=PROJECT_ROOT / "examples" / "13_sensor_fault_demo" / "artifacts",
            log_filename="sensor_fault_demo.csv",
            plot_filename="sensor_fault_demo.png",
            report_filename="sensor_fault_demo_report.md",
            steps=220,
            controller_type="precision-pid",
            sensor_provider=sensor_fault_model,
            disturbance_provider=SENSOR_FAULT_BASE_DISTURBANCE,
            redundant_sensor_provider=redundant_sensor,
        ),
        ExampleRun(
            name="能耗协调示例",
            directory=PROJECT_ROOT / "examples" / "14_energy_budget_demo" / "artifacts",
            log_filename="energy_budget_demo.csv",
            plot_filename="energy_budget_demo.png",
            report_filename="energy_budget_demo_report.md",
            steps=220,
            controller_type="precision-pid",
            disturbance_provider=ENERGY_BUDGET_DISTURBANCE,
            settings_patch={
                "ENERGY_COORDINATION": {
                    "enabled": True,
                    "budget_per_step": 5.0,
                }
            },
        ),
        ExampleRun(
            name="长周期运行总结",
            directory=PROJECT_ROOT / "examples" / "16_long_run_report" / "artifacts",
            log_filename="long_run_demo.csv",
            plot_filename="long_run_demo.png",
            report_filename="long_run_demo_report.md",
            steps=600,
            controller_type="adaptive-pid",
            disturbance_provider=LONG_RUN_DISTURBANCE,
        ),
    ]


def main() -> None:
    runs = build_runs()
    for run in runs:
        run.execute()


if __name__ == "__main__":
    main()
