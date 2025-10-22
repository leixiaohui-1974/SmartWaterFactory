# 示例 16：长周期对比与报告

该示例连续运行多种控制策略，在较长仿真周期（默认 600 步）下比较水质、能耗和故障表现，并生成汇总报告。

## 运行

```bash
python examples/16_long_run_report/run_long_run_report.py
```

输出内容包括：

- `data/long_run_precision_pid.csv`
- `data/long_run_precision_low_budget.csv`
- `data/long_run_adaptive_pid.csv`
- `data/long_run_summary.md`（表格汇总平均浊度、溶解氧、总成本、故障次数、平均能耗缩放等指标）

终端还会打印简要总结和建议，可用于调试和选型决策。
