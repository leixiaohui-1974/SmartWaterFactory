# --- 模拟参数 ---

# 这些参数定义了水处理厂模拟器的行为。
# 它们旨在成为常数，但可以为不同场景进行调整。

SIMULATION_DEFAULTS = {
    "do_saturation": 9.0,           # 溶解氧饱和浓度 (mg/L)
    "do_consumption_rate": 0.02,    # 生物质自然消耗 DO 的速率
    "turbidity_decay_factor": 0.05, # 混凝剂降低浊度的有效系数
    "do_increase_rate": 0.05,       # 曝气增加 DO 的有效系数
    "time_delay_steps": 5,          # 延迟控制动作的步数
    "aeration_non_linearity": 1.5,  # 非线性曝气效率因子
    "sensor_fault_thresholds": {    # 传感器故障检测阈值
        "turbidity": 3.0,
        "dissolved_oxygen": 1.0,
    },
    "redundant_sensor_weights": {   # 冗余传感器融合权重
        "primary": 1.0,
        "secondary": 0.5,
    },
}


# --- 能耗协调参数 ---

ENERGY_COORDINATION = {
    "enabled": True,
    "budget_per_step": 50.0,  # 每步允许的最大能耗/成本
    "weights": {
        "coagulant": 0.4,
        "aeration": 0.6,
    },
}

# --- 传感器容错策略 ---

FAULT_TOLERANCE = {
    "enabled": True,
    "consecutive_fault_threshold": 3,  # 连续故障次数后触发降级
    "redundant_sensor_weights": {
        "primary": 1.0,
        "secondary": 0.5,
    },
}


# --- PID 控制器增益 ---

# 这些是 PID 控制器的默认调优参数（增益）。
# 它们提供了稳定的起点，但可能需要根据
# 操作条件进行调整以获得最佳性能。

PID_GAINS = {
    "dosing_controller": {
        "Kp": 0.12,
        "Ki": 0.001,
        "Kd": 0.5,
    },
    "aeration_controller": {
        "Kp": 1.2,
        "Ki": 0.22,
        "Kd": 0.1,
    },
}
