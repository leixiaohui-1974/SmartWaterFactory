from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Optional, Any
from water_plant_controller.models.water_quality import WaterQuality
from config.settings import SIMULATION_DEFAULTS

class PlantSimulator:
    """
    模拟水处理厂的行为。
    
    该类实现了一个简化的水处理厂数学模型，模拟混凝剂剂量和曝气速率
    对水质参数（浊度和溶解氧）的影响。模型包含时间延迟、非线性效应
    和物理约束等真实工厂的特征。
    
    模型特点：
    - 混凝剂影响浊度降低（一阶动力学）
    - 曝气影响溶解氧增加（带饱和效应和非线性）
    - 可配置的时间延迟模拟管道传输时间
    - 自然消耗过程模拟
    
    Attributes:
        current_quality (WaterQuality): 当前水质状态
        simulation_time (datetime): 当前仿真时间
        _turbidity_decay_factor (float): 浊度衰减系数
        _do_saturation (float): 溶解氧饱和浓度
        _do_increase_rate (float): 溶解氧增加速率
        _do_consumption_rate (float): 溶解氧消耗速率
        _aeration_non_linearity (float): 曝气非线性系数
        _delay_steps (int): 延迟步数
        _coagulant_pipeline (deque): 混凝剂延迟管道
        _aeration_pipeline (deque): 曝气延迟管道
    
    Example:
        >>> initial_quality = WaterQuality(
        ...     timestamp=datetime.now(),
        ...     ph=7.0, turbidity=10.0, dissolved_oxygen=5.0
        ... )
        >>> simulator = PlantSimulator(initial_quality)
        >>> new_quality = simulator.step(coagulant_dose=2.0, aeration_rate=1.5)
    """

    def __init__(self, initial_quality: WaterQuality, config: Optional[Dict[str, Any]] = None) -> None:
        """
        使用起始水质初始化模拟器。

        Args:
            initial_quality (WaterQuality): 初始WaterQuality状态，包含pH、浊度和溶解氧等参数
            config (Optional[Dict[str, Any]]): 用于覆盖默认值的模拟参数字典。
                                             支持的配置项包括：
                                             - do_saturation: 溶解氧饱和浓度
                                             - do_consumption_rate: 溶解氧消耗速率
                                             - turbidity_decay_factor: 浊度衰减系数
                                             - do_increase_rate: 溶解氧增加速率
                                             - aeration_non_linearity: 曝气非线性系数
                                             - time_delay_steps: 时间延迟步数
        
        Raises:
            TypeError: 当initial_quality不是WaterQuality实例时抛出
        """
        if not isinstance(initial_quality, WaterQuality):
            raise TypeError("initial_quality must be a WaterQuality instance")
            
        self.current_quality: WaterQuality = initial_quality
        self.simulation_time: datetime = initial_quality.timestamp

        # 加载默认设置并使用提供的配置覆盖
        self.config: Dict[str, Any] = SIMULATION_DEFAULTS.copy()
        if config:
            self.config.update(config)

        self._do_saturation: float = self.config["do_saturation"]
        self._do_consumption_rate: float = self.config["do_consumption_rate"]
        self._turbidity_decay_factor: float = self.config["turbidity_decay_factor"]
        self._do_increase_rate: float = self.config["do_increase_rate"]
        self._aeration_non_linearity: float = self.config["aeration_non_linearity"]

        # 初始化延迟管道
        self._delay_steps: int = int(self.config.get("time_delay_steps", 0))
        if self._delay_steps > 0:
            self._coagulant_pipeline: deque = deque([0.0] * self._delay_steps, maxlen=self._delay_steps)
            self._aeration_pipeline: deque = deque([0.0] * self._delay_steps, maxlen=self._delay_steps)

    def step(self, coagulant_dose: float, aeration_rate: float) -> WaterQuality:
        """
        将模拟推进一个时间步长（例如，1分钟）。
        
        该方法实现了水处理厂的一步仿真，包括：
        1. 处理时间延迟（通过管道队列）
        2. 计算浊度变化（混凝剂效应）
        3. 计算溶解氧变化（曝气效应和自然消耗）
        4. 更新仿真时间和水质状态

        Args:
            coagulant_dose (float): 添加的混凝剂量（例如，以mg/L为单位），非负值
            aeration_rate (float): 曝气速率（例如，以m^3/hr为单位），非负值

        Returns:
            WaterQuality: 步骤后的新WaterQuality状态，包含新的时间戳和参数值
            
        Raises:
            ValueError: 当输入参数无效时（负值或非数值）
            TypeError: 当输入参数类型不正确时
            
        Note:
            - 浊度不会低于0
            - 溶解氧被限制在0到饱和浓度之间
            - 仿真时间每步增加1分钟
        """
        # 输入验证
        if not isinstance(coagulant_dose, (int, float)):
            raise TypeError(f"coagulant_dose必须是数值类型，得到: {type(coagulant_dose).__name__}")
        if not isinstance(aeration_rate, (int, float)):
            raise TypeError(f"aeration_rate必须是数值类型，得到: {type(aeration_rate).__name__}")
            
        if coagulant_dose < 0:
            raise ValueError(f"coagulant_dose必须为非负值，得到: {coagulant_dose}")
        if aeration_rate < 0:
            raise ValueError(f"aeration_rate必须为非负值，得到: {aeration_rate}")
            
        # 检查极端值
        if coagulant_dose > 1000:  # 合理的上限
            raise ValueError(f"coagulant_dose过大，可能导致不稳定: {coagulant_dose}")
        if aeration_rate > 1000:  # 合理的上限
            raise ValueError(f"aeration_rate过大，可能导致不稳定: {aeration_rate}")
            
        # 检查数值有效性
        import math
        if math.isnan(coagulant_dose) or math.isinf(coagulant_dose):
            raise ValueError(f"coagulant_dose包含无效数值: {coagulant_dose}")
        if math.isnan(aeration_rate) or math.isinf(aeration_rate):
            raise ValueError(f"aeration_rate包含无效数值: {aeration_rate}")
        # 如果配置了时间延迟，则应用
        if self._delay_steps > 0:
            delayed_coagulant = self._coagulant_pipeline.popleft()
            self._coagulant_pipeline.append(coagulant_dose)

            delayed_aeration = self._aeration_pipeline.popleft()
            self._aeration_pipeline.append(aeration_rate)
        else:
            delayed_coagulant = coagulant_dose
            delayed_aeration = aeration_rate

        # --- 更新模拟时间 ---
        self.simulation_time += timedelta(minutes=1)

        # --- 模拟浊度变化 ---
        # 模型：混凝剂导致浊度降低。
        turbidity_reduction = self._turbidity_decay_factor * delayed_coagulant * self.current_quality.turbidity
        new_turbidity = self.current_quality.turbidity - turbidity_reduction

        # --- 模拟溶解氧（DO）变化 ---
        # 模型：曝气将DO增加到饱和点，而自然过程消耗它。
        current_do = self.current_quality.dissolved_oxygen

        # 曝气效果（带非线性效率）
        do_deficit = self._do_saturation - current_do
        if self._do_saturation > 0:
            # 当DO接近饱和时，曝气效率降低
            efficiency_factor = (do_deficit / self._do_saturation) ** (self._aeration_non_linearity - 1)
        else:
            efficiency_factor = 1.0

        effective_increase_rate = self._do_increase_rate * efficiency_factor
        do_increase = effective_increase_rate * delayed_aeration * do_deficit

        # 自然消耗效果
        do_decrease = self._do_consumption_rate * current_do

        new_do = current_do + do_increase - do_decrease

        # --- 更新状态 ---
        # （pH和温度在此简单模型中假设为常数）
        self.current_quality = WaterQuality(
            timestamp=self.simulation_time,
            ph=self.current_quality.ph,
            turbidity=max(0, new_turbidity),  # 确保浊度不为负
            dissolved_oxygen=max(0, min(self._do_saturation, new_do)) # 确保DO在范围内
        )

        return self.current_quality
