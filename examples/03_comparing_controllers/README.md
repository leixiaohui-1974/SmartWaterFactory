# 示例3：比较控制器性能（PID vs. 开关）

此示例指导您如何使用主项目脚本来运行两种不同类型控制器的模拟—`PID` 和 `开关`—以及如何可视化结果来比较它们的性能。

## 目标

目标是演示复杂控制器（PID）和非常简单控制器（开关）之间的实际差异。此比较突出了为什么PID控制器在需要稳定性和精度的工业工艺中如此广泛使用。

-   **PID控制器**：旨在实现平滑、稳定和精确的响应。
-   **开关控制器**：一个"砰砰"控制器，要么完全开启，要么完全关闭。它很简单，但通常非常低效和不稳定。

## 如何运行比较

此示例使用项目根目录的主脚本。

### 步骤1：运行PID模拟

首先，使用默认的 `pid` 控制器运行模拟。我们将输出定向到特定文件，这样在下一步中就不会覆盖它们。

从项目的根目录运行：
```bash
python3 run_simulation.py --controller-type pid --log-file pid_log.csv
```

### 步骤2：运行开关模拟

接下来，再次运行模拟，但这次选择 `on-off` 控制器。

从项目的根目录运行：
```bash
python3 run_simulation.py --controller-type on-off --log-file on_off_log.csv
```

### 步骤3：可视化两个结果

现在您有两个日志文件，可以为每个生成图表。

为PID控制器生成图表：
```bash
python3 visualize_log.py --log-file pid_log.csv --output-image pid_plot.png
```

为开关控制器生成图表：
```bash
python3 visualize_log.py --log-file on_off_log.csv --output-image on_off_plot.png
```

### 步骤4：比较输出图像

您现在应该在根目录中有两个图像：`pid_plot.png` 和 `on_off_plot.png`。

-   **`pid_plot.png`**：查看PID控制器的图表。您将看到浊度和溶解氧水平都平滑地移动到其设定点，然后保持稳定，误差很小。
-   **`on_off_plot.png`**：现在查看开关控制器的图表。您将看到一个截然不同的结果。工艺变量将在设定点周围不断摆动（振荡），永远不会稳定下来。因为控制器只能是100%开启或100%关闭，它总是过度校正，导致不稳定和低效的系统。

此比较也在主 `DOCUMENTATION.md` 文件中讨论，其中包含这些图表供参考。
