# 示例 11：闭环控制验证

本示例演示如何通过 PID 控制器驱动仿真模型，使浊度和溶解氧在较短时间内收敛到目标值，并将运行结果导出为 CSV 以便后续可视化。

## 快速开始

```bash
python examples/11_closed_loop_validation/run_closed_loop_demo.py
```

脚本会在 `data/closed_loop_validation.csv` 中生成模拟日志，并在终端输出最终的收敛情况。当最终浊度偏差超过 ±0.5 NTU 或溶解氧偏差超过 ±0.3 mg/L 时，脚本会触发 `AssertionError`，可作为快速冒烟测试。

## 可视化结果

运行模拟后，可借助现有的可视化脚本查看趋势：

```bash
python visualize_log.py --log-file data/closed_loop_validation.csv --output-image data/closed_loop_validation.png
```

生成的图像会显示浊度、溶解氧及其设定值随时间的变化情况，帮助确认控制回路的稳定性。
