#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""控制器性能指标计算模块。

本模块提供各种控制性能指标的计算方法，用于量化评估控制器的性能。

性能指标包括：
1. 误差指标：IAE, ISE, ITAE, ITSE
2. 时域指标：超调量、调节时间、上升时间
3. 稳态指标：稳态误差
4. 成本指标：能耗、化学品用量
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np


@dataclass
class PerformanceMetrics:
    """控制器性能指标数据类。"""

    # 误差积分指标
    iae: float = 0.0  # Integral Absolute Error
    ise: float = 0.0  # Integral Square Error
    itae: float = 0.0  # Integral Time Absolute Error
    itse: float = 0.0  # Integral Time Square Error

    # 时域特性
    overshoot: float = 0.0  # 超调量 (%)
    overshoot_count: int = 0  # 超调次数
    settling_time: Optional[float] = None  # 调节时间
    rise_time: Optional[float] = None  # 上升时间
    peak_time: Optional[float] = None  # 峰值时间

    # 稳态性能
    steady_state_error: float = 0.0  # 稳态误差
    steady_state_variance: float = 0.0  # 稳态方差

    # 成本指标
    total_energy: float = 0.0  # 总能耗
    total_chemical: float = 0.0  # 总化学品用量
    total_cost: float = 0.0  # 总成本

    # 控制输出统计
    control_effort: float = 0.0  # 控制努力度
    control_variance: float = 0.0  # 控制方差
    saturation_count: int = 0  # 饱和次数

    # 其他指标
    settling_count: int = 0  # 达到稳态次数
    violation_count: int = 0  # 违规次数（超出安全范围）

    # 元数据
    simulation_steps: int = 0
    simulation_time: float = 0.0
    controller_type: str = ""

    def to_dict(self) -> Dict:
        """转换为字典格式。"""
        return {
            'iae': self.iae,
            'ise': self.ise,
            'itae': self.itae,
            'itse': self.itse,
            'overshoot': self.overshoot,
            'overshoot_count': self.overshoot_count,
            'settling_time': self.settling_time,
            'rise_time': self.rise_time,
            'peak_time': self.peak_time,
            'steady_state_error': self.steady_state_error,
            'steady_state_variance': self.steady_state_variance,
            'total_energy': self.total_energy,
            'total_chemical': self.total_chemical,
            'total_cost': self.total_cost,
            'control_effort': self.control_effort,
            'control_variance': self.control_variance,
            'saturation_count': self.saturation_count,
            'settling_count': self.settling_count,
            'violation_count': self.violation_count,
            'simulation_steps': self.simulation_steps,
            'simulation_time': self.simulation_time,
            'controller_type': self.controller_type,
        }


def calculate_iae(errors: List[float], dt: float = 1.0) -> float:
    """计算积分绝对误差 (IAE)。

    Args:
        errors: 误差序列
        dt: 时间步长

    Returns:
        IAE值
    """
    return float(np.sum(np.abs(errors)) * dt)


def calculate_ise(errors: List[float], dt: float = 1.0) -> float:
    """计算积分平方误差 (ISE)。

    Args:
        errors: 误差序列
        dt: 时间步长

    Returns:
        ISE值
    """
    return float(np.sum(np.square(errors)) * dt)


def calculate_itae(errors: List[float], dt: float = 1.0) -> float:
    """计算积分时间绝对误差 (ITAE)。

    Args:
        errors: 误差序列
        dt: 时间步长

    Returns:
        ITAE值
    """
    times = np.arange(len(errors)) * dt
    return float(np.sum(times * np.abs(errors)) * dt)


def calculate_itse(errors: List[float], dt: float = 1.0) -> float:
    """计算积分时间平方误差 (ITSE)。

    Args:
        errors: 误差序列
        dt: 时间步长

    Returns:
        ITSE值
    """
    times = np.arange(len(errors)) * dt
    return float(np.sum(times * np.square(errors)) * dt)


def calculate_overshoot(
    values: List[float],
    setpoint: float,
    initial_value: Optional[float] = None
) -> Tuple[float, int]:
    """计算超调量和超调次数。

    Args:
        values: 过程值序列
        setpoint: 设定值
        initial_value: 初始值（如果未提供则使用第一个值）

    Returns:
        (最大超调百分比, 超调次数)
    """
    if not values:
        return 0.0, 0

    values_arr = np.array(values)
    if initial_value is None:
        initial_value = values_arr[0]

    # 计算变化方向
    change = setpoint - initial_value
    if abs(change) < 1e-6:
        return 0.0, 0

    # 寻找超过设定值的点
    if change > 0:  # 上升过程
        overshoots = values_arr > setpoint
        if np.any(overshoots):
            max_overshoot = float(np.max(values_arr[overshoots]) - setpoint)
            overshoot_percent = (max_overshoot / abs(change)) * 100
        else:
            overshoot_percent = 0.0
    else:  # 下降过程
        overshoots = values_arr < setpoint
        if np.any(overshoots):
            max_overshoot = float(setpoint - np.min(values_arr[overshoots]))
            overshoot_percent = (max_overshoot / abs(change)) * 100
        else:
            overshoot_percent = 0.0

    # 计算超调次数（穿越设定值的次数）
    crossings = np.diff(np.sign(values_arr - setpoint))
    overshoot_count = int(np.sum(np.abs(crossings)) / 2)

    return overshoot_percent, overshoot_count


def calculate_settling_time(
    values: List[float],
    setpoint: float,
    tolerance: float = 0.02,
    min_duration: int = 10,
    dt: float = 1.0
) -> Optional[float]:
    """计算调节时间（2%或5%误差带）。

    Args:
        values: 过程值序列
        setpoint: 设定值
        tolerance: 误差容限（默认2%）
        min_duration: 最小稳定持续步数
        dt: 时间步长

    Returns:
        调节时间（如果找到）或None
    """
    if not values or len(values) < min_duration:
        return None

    values_arr = np.array(values)
    errors = np.abs(values_arr - setpoint)
    threshold = abs(setpoint) * tolerance if setpoint != 0 else tolerance

    # 从后向前找第一个超出误差带的点
    for i in range(len(values) - min_duration, -1, -1):
        if errors[i] > threshold:
            settling_time = (i + 1) * dt
            return float(settling_time)

    # 如果一直都在误差带内
    return 0.0


def calculate_rise_time(
    values: List[float],
    setpoint: float,
    initial_value: Optional[float] = None,
    lower_percent: float = 0.1,
    upper_percent: float = 0.9,
    dt: float = 1.0
) -> Optional[float]:
    """计算上升时间（10%到90%）。

    Args:
        values: 过程值序列
        setpoint: 设定值
        initial_value: 初始值
        lower_percent: 下限百分比（默认10%）
        upper_percent: 上限百分比（默认90%）
        dt: 时间步长

    Returns:
        上升时间或None
    """
    if not values:
        return None

    if initial_value is None:
        initial_value = values[0]

    change = setpoint - initial_value
    if abs(change) < 1e-6:
        return None

    lower_threshold = initial_value + change * lower_percent
    upper_threshold = initial_value + change * upper_percent

    values_arr = np.array(values)

    # 找到第一次达到10%的时间
    if change > 0:
        lower_indices = np.where(values_arr >= lower_threshold)[0]
        upper_indices = np.where(values_arr >= upper_threshold)[0]
    else:
        lower_indices = np.where(values_arr <= lower_threshold)[0]
        upper_indices = np.where(values_arr <= upper_threshold)[0]

    if len(lower_indices) == 0 or len(upper_indices) == 0:
        return None

    t_lower = lower_indices[0] * dt
    t_upper = upper_indices[0] * dt

    return float(t_upper - t_lower)


def calculate_steady_state_error(
    values: List[float],
    setpoint: float,
    last_n: int = 50
) -> float:
    """计算稳态误差（最后N个点的平均误差）。

    Args:
        values: 过程值序列
        setpoint: 设定值
        last_n: 用于计算稳态的最后N个点

    Returns:
        稳态误差
    """
    if not values:
        return 0.0

    steady_values = np.array(values[-last_n:])
    return float(np.mean(steady_values - setpoint))


def calculate_metrics(
    setpoint: float,
    process_values: List[float],
    control_outputs: Optional[List[float]] = None,
    costs: Optional[List[float]] = None,
    dt: float = 1.0,
    controller_type: str = "",
    safety_range: Optional[Tuple[float, float]] = None
) -> PerformanceMetrics:
    """计算完整的性能指标集。

    Args:
        setpoint: 设定值
        process_values: 过程值序列
        control_outputs: 控制输出序列（可选）
        costs: 成本序列（可选）
        dt: 时间步长
        controller_type: 控制器类型
        safety_range: 安全范围 (min, max)

    Returns:
        完整的性能指标对象
    """
    if not process_values:
        return PerformanceMetrics(controller_type=controller_type)

    metrics = PerformanceMetrics(controller_type=controller_type)

    # 计算误差序列
    errors = [pv - setpoint for pv in process_values]

    # 误差积分指标
    metrics.iae = calculate_iae(errors, dt)
    metrics.ise = calculate_ise(errors, dt)
    metrics.itae = calculate_itae(errors, dt)
    metrics.itse = calculate_itse(errors, dt)

    # 时域特性
    overshoot, overshoot_count = calculate_overshoot(process_values, setpoint)
    metrics.overshoot = overshoot
    metrics.overshoot_count = overshoot_count

    metrics.settling_time = calculate_settling_time(process_values, setpoint, dt=dt)
    metrics.rise_time = calculate_rise_time(process_values, setpoint, dt=dt)

    # 峰值时间
    if overshoot > 0:
        peak_idx = int(np.argmax(np.abs(np.array(process_values) - setpoint)))
        metrics.peak_time = peak_idx * dt

    # 稳态性能
    metrics.steady_state_error = calculate_steady_state_error(process_values, setpoint)
    steady_values = process_values[-50:]
    if len(steady_values) > 1:
        metrics.steady_state_variance = float(np.var(steady_values))

    # 控制输出统计
    if control_outputs:
        controls_arr = np.array(control_outputs)
        metrics.control_effort = float(np.sum(np.abs(controls_arr)) * dt)
        metrics.control_variance = float(np.var(controls_arr))

        # 计算饱和次数（假设控制输出范围0-100）
        # 可以根据实际情况调整阈值
        metrics.saturation_count = int(np.sum((controls_arr <= 0.01) | (controls_arr >= 99.99)))

    # 成本指标
    if costs:
        metrics.total_cost = float(np.sum(costs))

    # 违规次数
    if safety_range:
        min_val, max_val = safety_range
        violations = [(pv < min_val or pv > max_val) for pv in process_values]
        metrics.violation_count = sum(violations)

    # 元数据
    metrics.simulation_steps = len(process_values)
    metrics.simulation_time = len(process_values) * dt

    return metrics


def compare_metrics(metrics_list: List[PerformanceMetrics]) -> Dict:
    """对比多个性能指标。

    Args:
        metrics_list: 性能指标列表

    Returns:
        对比结果字典
    """
    if not metrics_list:
        return {}

    comparison = {
        'controllers': [m.controller_type for m in metrics_list],
        'metrics': {}
    }

    # 提取所有指标进行对比
    metric_names = [
        'iae', 'ise', 'itae', 'itse',
        'overshoot', 'settling_time', 'rise_time',
        'steady_state_error', 'total_cost',
        'control_effort', 'violation_count'
    ]

    for metric_name in metric_names:
        values = [getattr(m, metric_name, None) for m in metrics_list]
        valid_values = [v for v in values if v is not None]

        if valid_values:
            comparison['metrics'][metric_name] = {
                'values': values,
                'best': min(valid_values),
                'worst': max(valid_values),
                'average': np.mean(valid_values),
                'best_controller': metrics_list[values.index(min(valid_values))].controller_type
            }

    return comparison


def format_metrics_report(metrics: PerformanceMetrics) -> str:
    """格式化性能指标报告。

    Args:
        metrics: 性能指标对象

    Returns:
        格式化的文本报告
    """
    report = f"""
{'='*60}
控制器性能报告 - {metrics.controller_type}
{'='*60}

【误差指标】
  IAE  (积分绝对误差):     {metrics.iae:.4f}
  ISE  (积分平方误差):     {metrics.ise:.4f}
  ITAE (积分时间绝对误差): {metrics.itae:.4f}
  ITSE (积分时间平方误差): {metrics.itse:.4f}

【时域特性】
  超调量:       {metrics.overshoot:.2f}%
  超调次数:     {metrics.overshoot_count}
  调节时间:     {metrics.settling_time:.2f} (如果有) if metrics.settling_time else "未达到"
  上升时间:     {metrics.rise_time:.2f} (如果有) if metrics.rise_time else "未计算"

【稳态性能】
  稳态误差:     {metrics.steady_state_error:.4f}
  稳态方差:     {metrics.steady_state_variance:.6f}

【控制性能】
  控制努力度:   {metrics.control_effort:.4f}
  控制方差:     {metrics.control_variance:.4f}
  饱和次数:     {metrics.saturation_count}

【成本指标】
  总成本:       {metrics.total_cost:.2f}

【仿真信息】
  仿真步数:     {metrics.simulation_steps}
  仿真时间:     {metrics.simulation_time:.2f}
  违规次数:     {metrics.violation_count}

{'='*60}
"""
    return report
