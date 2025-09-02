# --- 模拟参数 ---

# 这些参数定义了水处理厂模拟器的行为。
# 它们旨在成为常数，但可以为不同场景进行调整。

SIMULATION_DEFAULTS = {
    "do_saturation": 9.0,           # 溶解氧饱和浓度 (mg/L)
    "do_consumption_rate": 0.02,    # 生物质自然消耗DO的速率
    "turbidity_decay_factor": 0.05, # 混凝剂降低浊度的有效性
    "do_increase_rate": 0.05,       # 曝气增加DO的有效性
    "time_delay_steps": 5,          # 延迟控制动作的步数
    "aeration_non_linearity": 1.5,  # 非线性曝气效率因子
}


# --- PID控制器增益 ---

# 这些是PID控制器的默认调优参数（增益）。
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
