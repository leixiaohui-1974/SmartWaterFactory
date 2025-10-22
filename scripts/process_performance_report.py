#!/usr/bin/env python3
"""Post-process the performance demo JSON output into CSV/PNG/Markdown artefacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    directory = Path(__file__).resolve().parents[1] / "examples" / "07_performance_optimization" / "artifacts"
    report_json = directory / "performance_report.json"
    if not report_json.exists():
        raise SystemExit(f"{report_json} does not exist – run the performance demo first.")

    with report_json.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    metrics = data.get("function_metrics", {})
    csv_path = directory / "performance_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["function", "call_count", "avg_execution_time", "last_execution_time", "cpu_usage"]
        )
        for name, payload in metrics.items():
            writer.writerow(
                [
                    name,
                    payload.get("call_count", 0),
                    payload.get("avg_execution_time", 0.0),
                    payload.get("last_execution_time", 0.0),
                    payload.get("cpu_usage", 0.0),
                ]
            )

    functions = list(metrics.keys())
    avg_times = [metrics[name].get("avg_execution_time", 0.0) for name in functions]
    call_counts = [metrics[name].get("call_count", 0) for name in functions]

    if functions:
        fig, ax1 = plt.subplots(figsize=(8, 5))
        ax2 = ax1.twinx()
        ax1.bar(functions, avg_times, color="tab:blue", alpha=0.7, label="平均执行时间 (s)")
        ax2.plot(functions, call_counts, color="tab:orange", marker="o", label="调用次数")
        ax1.set_ylabel("平均执行时间 (s)")
        ax2.set_ylabel("调用次数")
        ax1.set_title("性能监控摘要")
        for idx, value in enumerate(avg_times):
            ax1.text(idx, value, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
        ax1.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        plot_path = directory / "performance_metrics.png"
        fig.savefig(plot_path, dpi=200)
        plt.close(fig)

    summary_lines = [
        "# 性能优化演示结果",
        "",
        f"- 记录时间戳：{data.get('timestamp')}",
        f"- 函数总数：{data.get('summary', {}).get('total_functions', 0)}",
        f"- 系统记录数：{data.get('summary', {}).get('total_system_records', 0)}",
        "",
        "## 函数摘要",
    ]
    for name, payload in metrics.items():
        summary_lines.extend(
            [
                f"### {name}",
                f"- 调用次数：{payload.get('call_count', 0)}",
                f"- 平均执行时间：{payload.get('avg_execution_time', 0.0):.4f} s",
                f"- 最后一次执行时间：{payload.get('last_execution_time', 0.0):.4f} s",
                f"- CPU 使用率：{payload.get('cpu_usage', 0.0):.2f}%",
                "",
            ]
        )

    summary_path = directory / "performance_report.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
