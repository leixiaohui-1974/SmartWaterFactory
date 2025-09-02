from typing import Optional, Union


class PIDController:
    """
    一个通用的PID（比例-积分-微分）控制器。
    
    PID控制器是工业控制系统中最常用的控制算法之一。它通过计算
    设定值与测量值之间的误差，并基于比例、积分和微分项来产生
    控制输出。
    
    控制算法：
        output = Kp * error + Ki * ∫error*dt + Kd * d(error)/dt
    
    Attributes:
        Kp (float): 比例增益，控制响应速度
        Ki (float): 积分增益，消除稳态误差
        Kd (float): 微分增益，减少超调和振荡
        setpoint (float): 目标设定值
        reverse_acting (bool): 是否为反作用控制器
    
    Example:
        >>> controller = PIDController(Kp=1.0, Ki=0.1, Kd=0.05, setpoint=50.0)
        >>> controller.set_output_limits(0, 100)
        >>> output = controller.calculate(current_value=45.0)
    """

    def __init__(
        self, 
        Kp: float, 
        Ki: float, 
        Kd: float, 
        setpoint: float, 
        reverse_acting: bool = False
    ) -> None:
        """
        初始化PID控制器。
        
        Args:
            Kp (float): 比例增益，必须为非负数
            Ki (float): 积分增益，必须为非负数
            Kd (float): 微分增益，必须为非负数
            setpoint (float): 受控变量的目标值
            reverse_acting (bool): 如果为True，控制器为反作用控制器。
                                 反作用控制器用于冷却或浊度降低等场景。
                                 默认为False（正作用）。
        
        Raises:
            ValueError: 当PID增益不是数值类型时抛出异常
        """
        if not all(isinstance(k, (int, float)) for k in [Kp, Ki, Kd]):
            raise ValueError("PID增益必须是数值。")
        
        if Kp < 0 or Ki < 0 or Kd < 0:
            raise ValueError("PID增益必须为非负数。")

        self.Kp: float = float(Kp)
        self.Ki: float = float(Ki)
        self.Kd: float = float(Kd)
        self.setpoint: float = float(setpoint)
        self.reverse_acting: bool = reverse_acting

        # 内部状态变量
        self._previous_error: float = 0.0
        self._integral: float = 0.0

        # 输出限制（默认值可以通过set_output_limits更改）
        self.output_min: Optional[float] = 0.0
        self.output_max: Optional[float] = float('inf')
        self.integral_min: Optional[float] = -float('inf')
        self.integral_max: Optional[float] = float('inf')

    def calculate(self, current_value: float, dt: float = 1.0) -> float:
        """
        计算控制变量输出。
        
        基于当前测量值与设定值的误差，计算PID控制器的输出。
        该方法实现了标准的PID算法，包括积分饱和保护。
        
        Args:
            current_value (float): 工艺变量的当前测量值
            dt (float): 自上次计算以来的时间步长，默认为1.0秒
        
        Returns:
            float: 计算出的控制输出，已应用输出限制
            
        Raises:
            TypeError: 当输入参数类型不正确时
            ValueError: 当输入参数包含无效数值时
        
        Note:
            - 积分项包含防积分饱和保护
            - 微分项在dt=0时自动设为0以避免除零错误
            - 输出会自动限制在设定的最小值和最大值之间
        """
        # 输入验证
        if not isinstance(current_value, (int, float)):
            raise TypeError(f"current_value必须是数值类型，得到: {type(current_value).__name__}")
        if not isinstance(dt, (int, float)):
            raise TypeError(f"dt必须是数值类型，得到: {type(dt).__name__}")
            
        if dt < 0:
            raise ValueError(f"时间步长dt必须为非负值，得到: {dt}")
            
        # 检查数值有效性
        import math
        if math.isnan(current_value) or math.isinf(current_value):
            raise ValueError(f"current_value包含无效数值: {current_value}")
        if math.isnan(dt) or math.isinf(dt):
            raise ValueError(f"dt包含无效数值: {dt}")
        error = self.setpoint - current_value
        if self.reverse_acting:
            error = -error

        # 比例项
        p_term = self.Kp * error

        # 积分项（带防积分饱和）
        self._integral += self.Ki * error * dt
        # 限制积分项以防止积分饱和
        if self.integral_min is not None and self.integral_max is not None:
            self._integral = max(self.integral_min, min(self._integral, self.integral_max))
        i_term = self._integral

        # 微分项
        if dt > 0:
            derivative = (error - self._previous_error) / dt
        else:
            derivative = 0.0
        d_term = self.Kd * derivative

        # 计算总输出
        output = p_term + i_term + d_term

        # 将最终输出限制在其限制范围内
        if self.output_min is not None and self.output_max is not None:
            output = max(self.output_min, min(output, self.output_max))

        # 更新下一次迭代的状态
        self._previous_error = error

        return output

    def set_integral_limits(self, min_val: float, max_val: float) -> None:
        """
        设置积分项的最小和最大限制。
        
        这是防积分饱和的关键部分。当控制器输出达到饱和时，
        积分项会继续累积，导致系统响应变慢。通过限制积分项
        的范围可以有效防止这种现象。
        
        Args:
            min_val (float): 积分项的最小值
            max_val (float): 积分项的最大值
        
        Raises:
            ValueError: 当min_val >= max_val时抛出异常
        """
        if min_val >= max_val:
            raise ValueError("min_val必须小于max_val。")
        self.integral_min = min_val
        self.integral_max = max_val

    def set_output_limits(self, min_val: float, max_val: float) -> None:
        """
        设置控制器输出的最小和最大限制。
        
        这对于防止控制变量超过物理限制很有用，例如阀门开度
        不能超过100%，泵的转速不能为负值等。
        
        Args:
            min_val (float): 最小输出值（例如：0表示完全关闭）
            max_val (float): 最大输出值（例如：100表示完全开启）
        
        Raises:
            ValueError: 当min_val >= max_val时抛出异常
        """
        if min_val >= max_val:
            raise ValueError("min_val必须小于max_val。")
        self.output_min = min_val
        self.output_max = max_val

    def reset(self) -> None:
        """
        重置控制器的内部状态。
        
        清除积分累积值和先前的误差值，将控制器恢复到初始状态。
        通常在系统启动、设定值大幅变化或切换控制模式时调用。
        
        Note:
            重置后的第一次calculate调用的微分项将为0
        """
        self._previous_error = 0.0
        self._integral = 0.0
