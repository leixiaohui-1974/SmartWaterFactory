#!/usr/bin/env python3
"""Generate summary artefacts for the logging demo outputs."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


LOG_PATTERN = re.compile(r"\[(?P<timestamp>[\d\-\s:.]+)] \[(?P<level>[A-Z]+)]")


def parse_levels(log_path: Path) -> Counter:
    counts: Counter[str] = Counter()
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = LOG_PATTERN.search(line)
            if match:
                counts[match.group("level")] += 1
    return counts


def main() -> None:
    artifacts = Path(__file__).resolve().parents[1] / "examples" / "08_logging_system" / "artifacts"
    error_log = artifacts / "demo_error.log"
    perf_log = artifacts / "demo_performance.log"

    if not error_log.exists():
        raise SystemExit("demo_error.log not found – run the logging demo first.")

    level_counts = parse_levels(error_log)
    csv_path = artifacts / "logging_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["level", "count"])
        for level, count in sorted(level_counts.items()):
            writer.writerow([level, count])

    levels = list(sorted(level_counts.keys()))
    values = [level_counts[level] for level in levels]

    if levels:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(levels, values, color="tab:purple")
        ax.set_title("日志级别分布")
        ax.set_ylabel("记录数量")
        for idx, value in enumerate(values):
            ax.text(idx, value + 0.05, str(value), ha="center", va="bottom")
        ax.set_ylim(0, max(values) * 1.2)
        fig.tight_layout()
        fig.savefig(artifacts / "logging_summary.png", dpi=200)
        plt.close(fig)

    report_lines = [
        "# 日志系统演示结果",
        "",
        f"- 总记录数：{sum(level_counts.values())}",
        "",
        "## 各级别计数",
    ]
    for level, count in sorted(level_counts.items()):
        report_lines.append(f"- {level}：{count}")
    if perf_log.exists():
        report_lines.append("")
        report_lines.append("- 性能日志示例已保存在 `demo_performance.log`。")

    (artifacts / "logging_summary.md").write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
