# 示例 17：MPC 与自适应 PID 对比

本示例展示了可靠度加权的 MPC 控制器在传感器漂移场景下的表现，并与项目中已有的自适应 PID 控制器进行对比。我们人为加入了一个缓慢增长的浊度传感器偏差（最多 +2 NTU），并在同一套扰动条件下分别运行两种控制策略。

## 如何运行

```bash
python examples/17_mpc_vs_adaptive/run_mpc_vs_adaptive_demo.py
```

脚本在 `examples/17_mpc_vs_adaptive/artifacts/` 目录下生成：

- `adaptive_pid_log.csv`：自适应 PID 仿真日志；
- `mpc_controller_log.csv`：MPC 仿真日志；
- `mpc_vs_adaptive.png`：并排比较图，包含浊度、投加量和传感器可信度曲线。

## 观察要点

- 当传感器偏差加剧时，MPC 会根据 Kalman 软测量推断的可信度降低投加量，从而避免过量投加；
- 图像和终端汇总中包含平均/末端浊度、累计药剂量与平均可信度，可作为评估策略的依据；
- 调整 `run_mpc_vs_adaptive_demo.py` 中的扰动或偏差模型，可进一步探索不同工况下的策略优劣。
