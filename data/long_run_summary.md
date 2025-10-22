# 长周期运行汇总

| 场景 | 控制器 | 平均浊度 (NTU) | 平均溶解氧 (mg/L) | 总成本 | 混凝剂成本 | 曝气成本 | 故障次数 | 平均能耗缩放 | 最小能耗缩放 | 日志路径 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| precision_pid_baseline | precision-pid | 3.96 | 8.18 | 1632.92 | 17.60 | 1615.32 | 0 | 1.000 | 1.000 | long_run_precision_pid.csv |
| precision_pid_low_budget | precision-pid | 4.91 | 8.18 | 1693.50 | 78.18 | 1615.32 | 0 | 1.000 | 1.000 | long_run_precision_low_budget.csv |
| adaptive_pid_full | adaptive-pid | 0.44 | 8.19 | 1718.04 | 45.00 | 1673.04 | 0 | 1.000 | 1.000 | long_run_adaptive_pid.csv |
