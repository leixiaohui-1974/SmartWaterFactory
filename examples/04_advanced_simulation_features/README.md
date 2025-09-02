# 示例4：高级模拟功能

此示例演示如何启用和配置 `PlantSimulator` 的高级功能，以创建更现实和具有挑战性的控制环境。

## 目标

目标是展示如何覆盖默认模拟参数来建模两种常见的现实世界现象：
1.  **时间延迟**：控制动作对工艺产生可测量效果所需的时间。例如，化学剂量通过管道到达传感器所需的时间。
2.  **非线性**：许多现实世界的工艺不是完全线性的。在我们的案例中，我们建模曝气效率随着水变得更饱和氧气而降低。

控制具有这些功能的系统明显更困难，通常需要更仔细的PID调优。

## 代码：`run_advanced_sim.py`

### 1. 自定义配置
```python
advanced_sim_config = SIMULATION_DEFAULTS.copy()
advanced_sim_config.update({
    "time_delay_steps": 15,
    "aeration_non_linearity": 2.0
})
```
此示例的关键部分是创建自定义配置字典。我们首先从主设置文件复制 `SIMULATION_DEFAULTS`，然后我们用想要更改的参数`update()`它。

-   **`time_delay_steps`**：我们将其设置为 `15`。这意味着控制器采取的任何动作（如应用剂量或改变曝气速率）在动作采取后15步*之前*不会对模拟产生任何影响。
-   **`aeration_non_linearity`**：我们将其增加到 `2.0`（默认值为1.5）。这使得随着溶解氧水平更接近其饱和点，曝气效率的降低更加明显。

### 2. 初始化模拟器
```python
simulator = PlantSimulator(initial_quality, config=advanced_sim_config)
```
当我们创建 `PlantSimulator` 实例时，我们只需将 `advanced_sim_config` 字典传递给它。模拟器将使用这些值而不是其默认值。

### 3. 运行模拟
脚本的其余部分与基础示例非常相似。我们使用默认增益设置PID控制器并运行模拟循环。

## 如何运行此示例

导航到项目的根目录并直接运行脚本：
```bash
python3 examples/04_advanced_simulation_features/run_advanced_sim.py
```
当您运行此示例时，请密切关注输出。您会注意到模拟开始时有一个显著的"滞后"。在前15步中，浊度和溶解氧水平不会改变，因为控制器的初始动作由于时间延迟仍然"在管道中"。这演示了延迟如何使系统更难控制，这是为现实世界应用调优控制器时需要考虑的关键因素。
