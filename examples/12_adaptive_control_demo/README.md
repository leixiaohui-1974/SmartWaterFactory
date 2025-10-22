# 示例 12：自适应与精细控制对比

本示例演示 `precision-pid` 与 `adaptive-pid` 控制模式在相同扰动条件下的差异。脚本会运行两次仿真，将日志分别保存到 `data/adaptive_precision_precision.csv` 和 `data/adaptive_precision_adaptive.csv`，并生成对比图 `data/adaptive_vs_precision_comparison.png`。

## 快速开始

```bash
python examples/12_adaptive_control_demo/run_adaptive_vs_precision_demo.py
```

执行完成后，终端会给出两种控制策略的平均指标、成本信息以及关键结论。生成的 PNG 图包含浊度和溶解氧的双曲线对比，可视化两种控制策略的收敛速度与稳态差异。

## 输出内容

- `data/adaptive_precision_precision.csv`：精细约束 PID 日志  
- `data/adaptive_precision_adaptive.csv`：自适应 PID 日志  
- `data/adaptive_vs_precision_comparison.png`：同一时间轴下的双曲线对比图（含浊度和溶解氧两行）

可配合 `visualize_log.py` 分别查看两份日志的详细成本与饱和信息。
