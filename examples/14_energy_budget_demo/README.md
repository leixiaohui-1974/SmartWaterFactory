# 示例 14：能耗预算约束

此示例演示能量协调器如何在总预算受限时缩放混凝剂与曝气输出，从而限制即时成本。脚本会将预算降低，并记录缩放系数与成本数据。

## 运行方式

```bash
python examples/14_energy_budget_demo/run_energy_budget_demo.py
```

运行后将生成：

- `data/energy_budget_demo.csv`：包含 `energy_scaling_factor` 等列
- `data/energy_budget_demo.png`：可视化图表，显示成本、饱和、能耗缩放

终端会报告预算设置、缩放统计以及成本总览。脚本会在结束前恢复默认预算配置。
