#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""控制器基准测试示例。

本示例演示如何使用基准测试工具对比不同控制器的性能。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.on_off_controller import OnOffController
from water_plant_controller.control.precision_controller import (
    PrecisionPIDController,
    AdaptivePIDController,
    ConstraintProfile,
    AdaptivePIDProfile
)
from water_plant_controller.analysis.controller_benchmark import (
    BenchmarkScenario,
    run_benchmark
)


def create_pid_controller(turbidity_setpoint: float, do_setpoint: float):
    """创建标准PID控制器。"""
    turbidity_controller = PIDController(
        Kp=0.12,
        Ki=0.001,
        Kd=0.5,
        setpoint=turbidity_setpoint,
        reverse_acting=True
    )
    turbidity_controller.set_output_limits(0.0, 10.0)

    do_controller = PIDController(
        Kp=1.2,
        Ki=0.22,
        Kd=0.1,
        setpoint=do_setpoint,
        reverse_acting=False
    )
    do_controller.set_output_limits(0.0, 15.0)

    return turbidity_controller, do_controller


def create_on_off_controller(turbidity_setpoint: float, do_setpoint: float):
    """创建开关控制器。"""
    turbidity_controller = OnOffController(
        setpoint=turbidity_setpoint,
        hysteresis=0.2,
        output_high=8.0,
        output_low=0.0,
        reverse_acting=True
    )

    do_controller = OnOffController(
        setpoint=do_setpoint,
        hysteresis=0.3,
        output_high=12.0,
        output_low=0.0,
        reverse_acting=False
    )

    return turbidity_controller, do_controller


def create_precision_pid_controller(turbidity_setpoint: float, do_setpoint: float):
    """创建精确PID控制器。"""
    # 浊度控制器
    turbidity_pid = PIDController(
        Kp=0.15,
        Ki=0.002,
        Kd=0.6,
        setpoint=turbidity_setpoint,
        reverse_acting=True
    )

    turbidity_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=10.0,
        ramp_rate=2.0,
        unit_cost=0.5
    )

    turbidity_controller = PrecisionPIDController(
        pid=turbidity_pid,
        constraint=turbidity_constraint,
        feedforward_gain=0.1
    )

    # 溶解氧控制器
    do_pid = PIDController(
        Kp=1.5,
        Ki=0.25,
        Kd=0.15,
        setpoint=do_setpoint,
        reverse_acting=False
    )

    do_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=15.0,
        ramp_rate=3.0,
        unit_cost=0.3
    )

    do_controller = PrecisionPIDController(
        pid=do_pid,
        constraint=do_constraint
    )

    return turbidity_controller, do_controller


def create_adaptive_pid_controller(turbidity_setpoint: float, do_setpoint: float):
    """创建自适应PID控制器。"""
    # 浊度控制器
    turbidity_pid = PIDController(
        Kp=0.1,
        Ki=0.001,
        Kd=0.5,
        setpoint=turbidity_setpoint,
        reverse_acting=True
    )

    turbidity_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=10.0,
        ramp_rate=2.0,
        unit_cost=0.5
    )

    turbidity_adaptation = AdaptivePIDProfile(
        kp_min=0.05,
        kp_max=0.3,
        ki_min=0.0005,
        ki_max=0.005,
        error_increase_threshold=0.5,
        error_decrease_threshold=0.1
    )

    turbidity_controller = AdaptivePIDController(
        pid=turbidity_pid,
        constraint=turbidity_constraint,
        adaptation=turbidity_adaptation
    )

    # 溶解氧控制器（使用精确PID）
    do_pid = PIDController(
        Kp=1.2,
        Ki=0.22,
        Kd=0.1,
        setpoint=do_setpoint,
        reverse_acting=False
    )

    do_constraint = ConstraintProfile(
        minimum=0.0,
        maximum=15.0,
        ramp_rate=3.0,
        unit_cost=0.3
    )

    do_controller = PrecisionPIDController(
        pid=do_pid,
        constraint=do_constraint
    )

    return turbidity_controller, do_controller


def main():
    """主函数。"""
    print("=" * 80)
    print("控制器性能基准测试示例")
    print("=" * 80)
    print()

    # 创建测试场景
    initial_quality = WaterQuality(
        timestamp=datetime.now(),
        ph=7.2,
        turbidity=8.0,  # 初始浊度较高
        dissolved_oxygen=6.0  # 初始DO较低
    )

    scenario = BenchmarkScenario(
        name="step_response",
        description="阶跃响应测试：从高浊度/低DO到目标值",
        initial_quality=initial_quality,
        setpoint_turbidity=2.0,
        setpoint_do=8.0,
        simulation_steps=300
    )

    # 定义要测试的控制器
    controllers = [
        ("Standard_PID", "PID", create_pid_controller),
        ("On_Off", "On-Off", create_on_off_controller),
        ("Precision_PID", "Precision-PID", create_precision_pid_controller),
        ("Adaptive_PID", "Adaptive-PID", create_adaptive_pid_controller),
    ]

    # 运行基准测试
    benchmark = run_benchmark(
        scenario=scenario,
        controllers=controllers,
        output_dir="benchmark_results"
    )

    print("\n" + "=" * 80)
    print("测试完成！")
    print()
    print("【关键发现】")

    # 分析结果
    comparison = benchmark.compare_results()
    ranking = comparison['summary']['ranking']

    print(f"  综合性能最优: {ranking[0]}")
    print(f"  综合性能最差: {ranking[-1]}")

    turb_comp = comparison['turbidity_comparison']
    if 'iae' in turb_comp:
        best_iae = turb_comp['iae']['best_controller']
        print(f"  误差最小: {best_iae} (IAE={turb_comp['iae']['best']:.4f})")

    if 'total_cost' in turb_comp:
        best_cost = turb_comp['total_cost']['best_controller']
        print(f"  成本最低: {best_cost} (Cost={turb_comp['total_cost']['best']:.2f})")

    print()
    print("详细结果已保存到 benchmark_results/ 目录")
    print("=" * 80)


if __name__ == '__main__':
    main()
