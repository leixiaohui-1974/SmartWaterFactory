from typing import Dict, Any, Union


def validate_config(sim_config: Dict[str, Any], pid_gains: Dict[str, Dict[str, float]]) -> None:
    """
    验证模拟配置和PID增益是否包含所有必需的键和正确的数据类型。
    
    该函数执行全面的配置验证，确保所有必需的参数都存在且类型正确，
    这有助于在仿真开始前捕获配置错误。
    
    Args:
        sim_config (Dict[str, Any]): 模拟配置字典，应包含：
            - do_saturation (float): 溶解氧饱和浓度
            - do_consumption_rate (float): 溶解氧消耗速率
            - turbidity_decay_factor (float): 浊度衰减系数
            - do_increase_rate (float): 溶解氧增加速率
            - aeration_non_linearity (float): 曝气非线性系数
            - time_delay_steps (int): 时间延迟步数
        pid_gains (Dict[str, Dict[str, float]]): 包含PID控制器增益的嵌套字典，
                                               应包含'dosing_controller'和'aeration_controller'键，
                                               每个包含'Kp', 'Ki', 'Kd'子键
    
    Raises:
        ValueError: 当缺少必需的键、类型不正确或值超出合理范围时抛出
        TypeError: 当参数类型不正确时抛出
    
    Example:
        >>> sim_config = {
        ...     'do_saturation': 10.0,
        ...     'do_consumption_rate': 0.1,
        ...     'turbidity_decay_factor': 0.05,
        ...     'do_increase_rate': 0.2,
        ...     'aeration_non_linearity': 1.5,
        ...     'time_delay_steps': 5
        ... }
        >>> gains = {
        ...     'dosing_controller': {'Kp': 1.0, 'Ki': 0.1, 'Kd': 0.05},
        ...     'aeration_controller': {'Kp': 0.8, 'Ki': 0.05, 'Kd': 0.02}
        ... }
        >>> validate_config(sim_config, gains)
    """
    # 输入类型检查
    if not isinstance(sim_config, dict):
        raise TypeError("sim_config必须是字典类型")
    if not isinstance(pid_gains, dict):
        raise TypeError("pid_gains必须是字典类型")
    
    # --- 验证模拟配置 ---
    required_sim_keys = {
        "do_saturation": (int, float),
        "do_consumption_rate": (int, float),
        "turbidity_decay_factor": (int, float),
        "do_increase_rate": (int, float),
        "time_delay_steps": int,
        "aeration_non_linearity": (int, float),
    }

    for key, expected_type in required_sim_keys.items():
        if key not in sim_config:
            raise ValueError(f"配置中缺少必需的模拟参数：'{key}'")
        
        # 检查数值类型和范围
        value = sim_config[key]
        if key == 'time_delay_steps':
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"'{key}' 必须是非负整数，得到 {value}")
            if value > 100:  # 合理的上限
                raise ValueError(f"'{key}' 值过大 (>{100})，得到 {value}")
        else:
            if not isinstance(value, expected_type):
                raise ValueError(f"模拟参数 '{key}' 类型不正确。"
                                 f"期望 {expected_type}，得到 {type(value)}。")
            if value < 0:
                raise ValueError(f"'{key}' 必须是非负数，得到 {value}")
            # 特定参数的合理性检查
            if key == 'do_saturation':
                if value <= 0:
                    raise ValueError(f"do_saturation必须为正数，得到 {value}")
                if value > 50:
                    raise ValueError(f"溶解氧饱和度过高 (>{50})，得到 {value}")
            if key in ['do_consumption_rate', 'turbidity_decay_factor', 'do_increase_rate'] and value > 10:
                raise ValueError(f"'{key}' 值过高 (>{10})，得到 {value}")

    # --- 验证PID增益配置 ---
    required_controllers = ["dosing_controller", "aeration_controller"]
    for controller in required_controllers:
        if controller not in pid_gains:
            raise ValueError(f"缺少必需的PID控制器：'{controller}'")

    required_pid_keys = {
        "Kp": (int, float),
        "Ki": (int, float),
        "Kd": (int, float),
    }

    for controller_name, gains in pid_gains.items():
        if not isinstance(gains, dict):
            raise ValueError(f"'{controller_name}' 的PID增益必须是字典类型")
        
        for key, expected_type in required_pid_keys.items():
            if key not in gains:
                raise ValueError(f"配置中 '{controller_name}' 缺少必需的PID增益 '{key}'。")
            
            gain_value = gains[key]
            if not isinstance(gain_value, expected_type):
                raise ValueError(f"'{controller_name}' 的PID增益 '{key}' 类型不正确。"
                                 f"期望 {expected_type}，得到 {type(gain_value)}。")
            if gain_value < 0:
                raise ValueError(f"PID增益必须为非负值，得到 {controller_name}.{key}={gain_value}")
            # PID增益合理性检查
            if gain_value > 100:
                raise ValueError(f"'{controller_name}' 的PID增益 '{key}' 过高 (>{100})，得到 {gain_value}")
            
        # 检查PID增益组合的合理性
        kp, ki, kd = gains['Kp'], gains['Ki'], gains['Kd']
        if kp == 0 and ki == 0 and kd == 0:
            raise ValueError(f"控制器 '{controller_name}' 的所有PID增益不能同时为零")
    
    # 检查所有控制器的PID增益是否全部为零
    all_zero = True
    for controller_name, gains in pid_gains.items():
        if gains.get('Kp', 0) != 0 or gains.get('Ki', 0) != 0 or gains.get('Kd', 0) != 0:
            all_zero = False
            break
    
    if all_zero:
        raise ValueError("PID增益不能全部为零")

    print("配置验证成功。")
