# 示例1：基础模拟

此示例提供了一个简单、自包含的演示，展示如何设置和运行水厂控制器的基础模拟。

## 目标

此示例的目标是展示框架基本组件的实际运行：
1.  初始化 `PlantSimulator`。
2.  为我们的两个工艺变量（浊度和溶解氧）创建 `PIDController` 实例。
3.  运行控制器和模拟器交互的模拟循环。
4.  将结果打印到控制台。

## 代码：`run_basic_sim.py`

代码有详细的注释，具有自解释性。以下是 `main()` 函数中关键部分的分解：

### 1. 初始化
```python
initial_quality = WaterQuality(...)
turbidity_setpoint = 5.0
do_setpoint = 8.5
```
我们首先定义水的初始条件和控制器的期望**设定点**（目标值）。

### 2. 模拟器设置
```python
simulator = PlantSimulator(initial_quality)
```
我们创建 `PlantSimulator` 的实例，传入初始水质。模拟器自动从主项目配置文件 `config/settings.py` 加载其物理参数（如反应速率、时间延迟等）。

### 3. 控制器配置
```python
dosing_gains = PID_GAINS["dosing_controller"]
dosing_controller = PIDController(...)

aeration_gains = PID_GAINS["aeration_controller"]
aeration_controller = PIDController(...)
```
我们创建两个 `PIDController` 实例，一个用于管理浊度（通过混凝剂剂量），一个用于管理溶解氧（通过曝气）。

-   **增益（`Kp`、`Ki`、`Kd`）**：控制器的调优参数从 `config/settings.py` 加载。
-   **`reverse_acting=True`**：注意，投加控制器设置为"反作用"。这是因为其输出（混凝剂剂量）导致测量变量（浊度）*降低*。这与曝气控制器相反，其中更多输出（曝气）导致测量值（溶解氧）*增加*。

### 4. 模拟循环
```python
for i in range(simulation_steps):
    # 获取当前状态
    current_quality = simulator.current_quality

    # 计算控制动作
    coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
    aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)

    # 将动作应用到模拟器
    simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)
```
这是闭环系统的核心。在每次迭代中，我们：
1.  从模拟器获取水的当前状态。
2.  将测量值（`turbidity` 和 `dissolved_oxygen`）输入到各自的控制器。
3.  控制器`calculate()`计算适当的输出动作。
4.  我们`step()`向前推进模拟器，应用计算出的动作。

## 如何运行此示例

导航到项目的根目录并直接运行脚本：
```bash
python3 examples/01_basic_simulation/run_basic_sim.py
```
您将看到模拟状态打印到控制台，显示系统将浊度和溶解氧驱动到其设定点。
