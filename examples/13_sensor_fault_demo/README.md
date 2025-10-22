# 示例 13：传感器故障演示

本示例涵盖主探头漂移、冗余探头融合以及 Kalman 滤波的协同作用，同时跟踪浊度与溶解氧两条测量链路的可信度。

- 主探头在第 80–120 步注入约 6 NTU 的偏置，冗余探头保持轻微漂移与噪声；
- `SensorMonitor` 为每个通道输出软测量（`fused_*`）、可信度和累积故障评分，触发回退或告警；
- CSV 日志新增原始/融合数据、`*_reliability`、`*_monitor_fault_score` 等字段，`visualize_log.py` 会生成包含原始 vs 融合曲线与可信度面板的图像。

## 运行步骤

```bash
python examples/13_sensor_fault_demo/run_sensor_fault_demo.py
```

脚本会：

1. 调用 `run_and_log_simulation`，挂载主/冗余传感器模型与自定义扰动；
2. 在 `examples/13_sensor_fault_demo/artifacts/sensor_fault_demo.csv` 中写出扩展日志；
3. 使用 `visualize_log.py` 生成包含双通道融合与可信度面板的 `sensor_fault_demo.png` 并打印统计摘要。

## 结果解读

- “Sensor Fusion Comparison” 面板可直接对比原始测量与 Kalman+冗余后的软测量；
- “Sensor Reliability & Fault Scores” 面板展示 `*_reliability`、`*_monitor_fault_score` 以及 trip 触发情况；
- 终端摘要会给出故障样本数、冗余启用次数、两条通道的平均可信度，帮助快速评估监测改进效果。
