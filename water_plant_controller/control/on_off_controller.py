from typing import Union


class OnOffController:
    """
    一个简单的开关（或砰砰）控制器。
    
    开关控制器是最简单的控制算法之一，它根据测量值是否
    达到设定点来切换输出状态。当测量值低于设定点时输出
    最大值，高于设定点时输出最小值（正作用），反作用则相反。
    
    这种控制器常用于温度控制、液位控制等不需要精确控制
    但需要简单可靠的场合。
    
    Attributes:
        setpoint (float): 目标设定值
        reverse_acting (bool): 是否为反作用控制器
        output_min (float): 最小输出值
        output_max (float): 最大输出值
    
    Example:
        >>> controller = OnOffController(setpoint=25.0, reverse_acting=True)
        >>> controller.set_output_limits(0, 100)
        >>> output = controller.calculate(current_value=30.0)
    """

    def __init__(self, setpoint: float, reverse_acting: bool = False) -> None:
        """
        初始化开关控制器。

        Args:
            setpoint (float): 受控变量的目标值
            reverse_acting (bool): 如果为True，控制器为反作用控制器。
                                 反作用控制器用于冷却或浊度降低等场景，
                                 当测量值高于设定点时输出最大值。
                                 默认为False（正作用）。
        """
        self.setpoint: float = float(setpoint)
        self.reverse_acting: bool = reverse_acting
        self.output_min: float = 0.0
        self.output_max: float = 1.0  # 默认为0-1范围

    def calculate(self, current_value: float) -> float:
        """
        计算控制变量输出。

        根据当前测量值与设定值的比较，返回最大值或最小值。
        
        Args:
            current_value (float): 工艺变量的当前测量值
        
        Returns:
            float: 计算出的控制输出（output_min或output_max）
            
        Raises:
            TypeError: 当输入参数类型不正确时
            ValueError: 当输入参数包含无效数值时
        
        Note:
            - 正作用：测量值 < 设定值时输出最大值
            - 反作用：测量值 > 设定值时输出最大值
        """
        # 输入验证
        if not isinstance(current_value, (int, float)):
            raise TypeError(f"current_value必须是数值类型，得到: {type(current_value).__name__}")
            
        # 检查数值有效性
        import math
        if math.isnan(current_value) or math.isinf(current_value):
            raise ValueError(f"current_value包含无效数值: {current_value}")
        error = self.setpoint - current_value

        # 对于反作用控制，反转误差
        if self.reverse_acting:
            error = -error

        if error > 0:
            return self.output_max
        else:
            return self.output_min

    def set_output_limits(self, min_val: float, max_val: float) -> None:
        """
        设置控制器输出的最小和最大限制。

        Args:
            min_val (float): 最小输出值（例如，0表示"关闭"）
            max_val (float): 最大输出值（例如，100表示"开启"）
        
        Raises:
            ValueError: 当min_val >= max_val时抛出异常
        """
        if min_val >= max_val:
            raise ValueError("min_val必须小于max_val。")
        self.output_min = min_val
        self.output_max = max_val

    def reset(self) -> None:
        """
        重置控制器状态。
        
        对于开关控制器，这实际上什么都不做，因为它没有内部状态。
        包含此方法是为了与PIDController保持一致的接口。
        
        Note:
            此方法为了接口一致性而存在，实际不执行任何操作
        """
        pass
