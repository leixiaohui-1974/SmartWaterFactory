#!/usr/bin/env python3
"""Generate artefacts for examples that do not have automated demos."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.environments import ConfigManager, Environment



@dataclass
class EndpointMetric:
    name: str
    method: str
    latency_ms: float
    success_rate: float


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, headers: Iterable[str], rows: Iterable[Iterable]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(headers))
        for row in rows:
            writer.writerow(list(row))


def save_bar_chart(path: Path, labels: List[str], values: List[float], title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color="tab:blue")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    for idx, value in enumerate(values):
        ax.text(idx, value, f"{value:.2f}", ha="center", va="bottom")
    ax.set_ylim(0, max(values) * 1.2 if values else 1)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def generate_config_management_outputs() -> None:
    artifacts = PROJECT_ROOT / "examples" / "06_config_management" / "artifacts"
    ensure_dir(artifacts)

    manager = ConfigManager()
    rows = []
    for env in (Environment.DEVELOPMENT, Environment.TESTING, Environment.PRODUCTION):
        manager._current_environment = env  # type: ignore[attr-defined]
        config = manager.get_config()
        rows.append(
            (
                env.value,
                config.debug,
                config.database.host,
                config.logging.level,
                config.simulation.default_steps,
            )
        )

    csv_path = artifacts / "config_summary.csv"
    write_csv(
        csv_path,
        ["environment", "debug", "db_host", "log_level", "default_steps"],
        rows,
    )

    labels = [row[0] for row in rows]
    steps = [row[4] for row in rows]
    save_bar_chart(
        artifacts / "config_default_steps.png",
        labels,
        steps,
        "Default Simulation Steps by Environment",
        "Default Steps",
    )

    lines = [
        "# Configuration Management Summary",
        "",
        "| Environment | Debug | Database Host | Log Level | Default Steps |",
        "| --- | --- | --- | --- | --- |",
    ]
    for env, debug, host, level, default_steps in rows:
        lines.append(f"| {env} | {debug} | {host} | {level} | {default_steps} |")
    (artifacts / "config_summary.md").write_text("\n".join(lines), encoding="utf-8")


def generate_api_integration_outputs() -> None:
    artifacts = PROJECT_ROOT / "examples" / "03_api_integration" / "artifacts"
    ensure_dir(artifacts)

    endpoints = [
        EndpointMetric("GET /api/v1/system/status", "GET", 42.5, 0.997),
        EndpointMetric("GET /api/v1/water-quality/current", "GET", 38.7, 0.995),
        EndpointMetric("POST /api/v1/controller/command", "POST", 65.2, 0.982),
        EndpointMetric("GET /api/v1/anomalies", "GET", 55.1, 0.989),
        EndpointMetric("GET /ws/stream", "WS", 28.4, 0.975),
    ]

    write_csv(
        artifacts / "api_endpoints.csv",
        ["endpoint", "method", "avg_latency_ms", "success_rate"],
        [(e.name, e.method, f"{e.latency_ms:.1f}", f"{e.success_rate:.3f}") for e in endpoints],
    )

    save_bar_chart(
        artifacts / "api_latency.png",
        [e.method for e in endpoints],
        [e.latency_ms for e in endpoints],
        "Example API Latency",
        "Latency (ms)",
    )

    lines = [
        "# API Integration Snapshot",
        "",
        "| Endpoint | Method | Avg Latency (ms) | Success Rate |",
        "| --- | --- | --- | --- |",
    ]
    for e in endpoints:
        lines.append(
            f"| {e.name} | {e.method} | {e.latency_ms:.1f} | {e.success_rate:.2%} |"
        )
    lines.extend(
        [
            "",
            "The numbers above are synthetic sample data to illustrate expected API performance characteristics.",
        ]
    )
    (artifacts / "api_summary.md").write_text("\n".join(lines), encoding="utf-8")


def generate_api_interface_outputs() -> None:
    artifacts = PROJECT_ROOT / "examples" / "10_api_interface" / "artifacts"
    ensure_dir(artifacts)

    endpoints = [
        ("GET /health", 12.3, 0.999),
        ("GET /api/v1/metrics", 58.4, 0.992),
        ("POST /api/v1/controller/pid", 73.0, 0.978),
        ("POST /api/v1/simulation/run", 181.2, 0.961),
    ]

    write_csv(
        artifacts / "api_interface_metrics.csv",
        ["endpoint", "avg_latency_ms", "success_rate"],
        [(name, f"{lat:.1f}", f"{rate:.3f}") for name, lat, rate in endpoints],
    )

    save_bar_chart(
        artifacts / "api_interface_latency.png",
        list(range(1, len(endpoints) + 1)),
        [lat for _, lat, _ in endpoints],
        "API Interface Latency Distribution",
        "Latency (ms)",
    )

    lines = [
        "# API Interface Demo Snapshot",
        "",
        "| Endpoint | Avg Latency (ms) | Success Rate |",
        "| --- | --- | --- |",
    ]
    for name, lat, rate in endpoints:
        lines.append(f"| {name} | {lat:.1f} | {rate:.2%} |")
    lines.extend(
        [
            "",
            "These figures are illustrative and intended for documentation or UI integration examples.」",
        ]
    )
    (artifacts / "api_interface_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    random.seed(42)
    generate_config_management_outputs()
    generate_api_integration_outputs()
    generate_api_interface_outputs()


if __name__ == "__main__":
    main()
