# 示例5：扩展模拟器

本指南提供了关于如何用新的物理参数和行为扩展 `PlantSimulator` 的逐步教程。这是最高级的示例，适用于想要为特定需求自定义模拟的用户。

## 目标

我们的目标是修改模拟器以包含**水温**的影响。我们将使"自然溶解氧消耗"依赖于温度，基于生物活性在较暖水中增加的想法。

我们将逐步介绍需要更改的四个关键文件：
1.  `water_plant_controller/models/water_quality.py`（数据模型）
2.  `config/settings.py`（配置）
3.  `config/validator.py`（配置验证器）
4.  `water_plant_controller/simulation/plant_simulator.py`（模拟器本身）

---

## 步骤1：更新 `WaterQuality` 模型

首先，我们需要在数据模型中添加 `temperature`。

-   **要编辑的文件**：`water_plant_controller/models/water_quality.py`

在 `WaterQuality` 数据类中添加新的属性 `temperature`。

**之前：**
```python
@dataclass
class WaterQuality:
    timestamp: datetime
    ph: float
    turbidity: float
    dissolved_oxygen: float
```

**之后：**
```python
@dataclass
class WaterQuality:
    timestamp: datetime
    ph: float
    turbidity: float
    dissolved_oxygen: float
    temperature: float = 15.0 # 默认为15°C
```
我们为其提供一个默认值以便利。

---

## 步骤2：更新配置

接下来，我们需要在设置文件中有一个新参数来定义温度和氧气消耗之间的关系。我们将添加一个 `temp_factor`，它决定消耗速率在基础温度以上每度变化多少。

-   **要编辑的文件**：`config/settings.py`

在 `SIMULATION_DEFAULTS` 字典中添加新的键 `do_consumption_temp_factor`。

```python
SIMULATION_DEFAULTS = {
    # ... 现有参数
    "aeration_non_linearity": 1.5,
    "base_temp_for_consumption": 15.0, # 基础速率适用的温度
    "do_consumption_temp_factor": 0.001, # 每度消耗增加多少
}
```

---

## 步骤3：更新配置验证器

由于我们添加了新的配置参数，我们必须更新验证器来检查它们。这确保模拟不会在配置不完整的情况下运行。

-   **要编辑的文件**：`config/validator.py`

在 `required_sim_keys` 字典中添加新的键。

```python
required_sim_keys = {
    # ... 现有键
    "aeration_non_linearity": (int, float),
    "base_temp_for_consumption": (int, float),
    "do_consumption_temp_factor": (int, float),
}
```

---

## 步骤4：更新 `PlantSimulator`

这是最后也是最重要的一步，我们在这里实现新逻辑。

-   **要编辑的文件**：`water_plant_controller/simulation/plant_simulator.py`

**4.1：在 `__init__` 中加载新参数**
首先，在 `__init__` 方法中加载新的配置值。

```python
class PlantSimulator:
    def __init__(self, ...):
        # ... 现有代码
        self._aeration_non_linearity = self.config["aeration_non_linearity"]
        self._base_temp = self.config["base_temp_for_consumption"]
        self._temp_factor = self.config["do_consumption_temp_factor"]
        # ... 现有代码
```

**4.2：在 `step` 中更新模拟逻辑**
现在，修改 `step` 方法中 `do_decrease` 的计算以包含温度的影响。

**之前：**
```python
# 自然消耗的影响
do_decrease = self._do_consumption_rate * current_do
```

**之后：**
```python
# 自然消耗的影响（现在依赖于温度）
temp_difference = self.current_quality.temperature - self._base_temp
dynamic_consumption_rate = self._do_consumption_rate + (temp_difference * self._temp_factor)
do_decrease = dynamic_consumption_rate * current_do
```

**4.3：更新 `WaterQuality` 对象创建**
最后，确保在 `step` 方法末尾创建新的 `WaterQuality` 状态对象时传递新的温度。

**之前：**
```python
self.current_quality = WaterQuality(
    timestamp=self.simulation_time,
    ph=self.current_quality.ph,
    # ...
)
```

**之后：**
```python
self.current_quality = WaterQuality(
    timestamp=self.simulation_time,
    ph=self.current_quality.ph,
    temperature=self.current_quality.temperature, # 传递温度
    # ...
)
```
*（对于更高级的模拟，您也可以使温度随时间变化！）*

---

## 结论

就是这样！通过遵循这四个步骤，您已成功用新的物理行为扩展了模拟器。您还需要更新受此更改影响的任何测试，但核心修改已完成。这种结构化方法—模型、配置、验证器、模拟器—使项目易于安全地扩展。
