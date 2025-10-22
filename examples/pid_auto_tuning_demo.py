#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PID自动调优示例。

演示如何使用各种调优算法自动优化PID参数。
"""

import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.optimization import (
    tune_pid,
    TuningMethod,
    TuningObjective,
    TuningConstraints,
    GeneticAlgorithmConfig,
    ParticleSwarmConfig,
    ZNMethod,
)
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController


def test_tuned_controller(params, initial_quality, setpoint, steps=200):
    """测试调优后的控制器。

    Args:
        params: PID参数
        initial_quality: 初始水质
        setpoint: 目标设定值
        steps: 仿真步数

    Returns:
        时间序列、过程值序列、控制输出序列
    """
    simulator = PlantSimulator(initial_quality=initial_quality)
    controller = PIDController(
        Kp=params.Kp,
        Ki=params.Ki,
        Kd=params.Kd,
        setpoint=setpoint,
        reverse_acting=True
    )
    controller.set_output_limits(0.0, 20.0)

    times = []
    values = []
    outputs = []

    for step in range(steps):
        times.append(step)
        current_value = simulator.current_quality.turbidity
        control_output = controller.calculate(current_value, dt=1.0)

        values.append(current_value)
        outputs.append(control_output)

        simulator.step(control_output, 0.0)

    return times, values, outputs


def demo_simple_tuning():
    """示例1：简单的自动调优。"""
    print("\n" + "=" * 60)
    print("示例1：简单的自动调优（使用默认设置）")
    print("=" * 60)

    # 创建初始水质
    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    # 执行自动调优（默认使用遗传算法）
    result = tune_pid(
        initial_quality=initial_quality,
        setpoint=setpoint,
        max_iterations=30
    )

    print(f"\n调优完成！")
    print(f"最优参数: {result.best_params}")
    print(f"性能得分: {result.best_score:.6f}")
    print(f"执行时间: {result.execution_time:.2f}秒")

    return result


def demo_genetic_algorithm():
    """示例2：使用遗传算法调优。"""
    print("\n" + "=" * 60)
    print("示例2：使用遗传算法调优（自定义参数）")
    print("=" * 60)

    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    # 自定义遗传算法配置
    ga_config = GeneticAlgorithmConfig(
        population_size=40,
        elite_size=4,
        mutation_rate=0.15,
        crossover_rate=0.85,
        convergence_threshold=1e-5
    )

    # 自定义参数约束
    constraints = TuningConstraints(
        kp_min=0.0, kp_max=8.0,
        ki_min=0.0, ki_max=1.5,
        kd_min=0.0, kd_max=4.0
    )

    result = tune_pid(
        initial_quality=initial_quality,
        setpoint=setpoint,
        method=TuningMethod.GENETIC_ALGORITHM,
        objective=TuningObjective.MINIMIZE_IAE,
        constraints=constraints,
        max_iterations=40,
        ga_config=ga_config
    )

    print(f"\n调优完成！")
    print(result)

    return result


def demo_particle_swarm():
    """示例3：使用粒子群优化调优。"""
    print("\n" + "=" * 60)
    print("示例3：使用粒子群优化调优")
    print("=" * 60)

    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    # 自定义PSO配置
    pso_config = ParticleSwarmConfig(
        swarm_size=25,
        inertia_weight=0.7,
        cognitive_weight=1.5,
        social_weight=1.5,
        max_velocity=1.2
    )

    result = tune_pid(
        initial_quality=initial_quality,
        setpoint=setpoint,
        method=TuningMethod.PARTICLE_SWARM,
        objective=TuningObjective.BALANCED,
        max_iterations=35,
        pso_config=pso_config
    )

    print(f"\n调优完成！")
    print(result)

    return result


def demo_ziegler_nichols():
    """示例4：使用Ziegler-Nichols方法调优。"""
    print("\n" + "=" * 60)
    print("示例4：使用Ziegler-Nichols方法调优")
    print("=" * 60)

    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    result = tune_pid(
        initial_quality=initial_quality,
        setpoint=setpoint,
        method=TuningMethod.ZIEGLER_NICHOLS,
        zn_method=ZNMethod.STEP_RESPONSE
    )

    print(f"\n调优完成！")
    print(result)

    return result


def demo_compare_all_methods():
    """示例5：比较所有调优方法。"""
    print("\n" + "=" * 60)
    print("示例5：比较所有调优方法")
    print("=" * 60)

    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    from water_plant_controller.optimization import AutoTuner

    tuner = AutoTuner(
        initial_quality=initial_quality,
        setpoint=setpoint,
        objective=TuningObjective.BALANCED
    )

    # 运行所有方法
    results = tuner.tune(
        method=TuningMethod.ALL,
        max_iterations=25
    )

    return results


def demo_different_objectives():
    """示例6：不同优化目标的对比。"""
    print("\n" + "=" * 60)
    print("示例6：不同优化目标的对比")
    print("=" * 60)

    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    objectives = [
        TuningObjective.MINIMIZE_IAE,
        TuningObjective.MINIMIZE_OVERSHOOT,
        TuningObjective.MINIMIZE_SETTLING_TIME,
        TuningObjective.BALANCED
    ]

    results = {}
    for obj in objectives:
        print(f"\n优化目标: {obj.value}")
        result = tune_pid(
            initial_quality=initial_quality,
            setpoint=setpoint,
            objective=obj,
            max_iterations=25
        )
        results[obj.value] = result

    # 打印比较
    print("\n" + "=" * 60)
    print("不同优化目标的结果比较")
    print("=" * 60)
    print(f"{'优化目标':<25} {'Kp':<8} {'Ki':<8} {'Kd':<8} {'得分':<12}")
    print("-" * 70)
    for obj_name, result in results.items():
        params = result.best_params
        print(f"{obj_name:<25} {params.Kp:<8.4f} {params.Ki:<8.4f} "
              f"{params.Kd:<8.4f} {result.best_score:<12.6f}")

    return results


def visualize_tuning_results(result, initial_quality, setpoint):
    """可视化调优结果。

    Args:
        result: 调优结果
        initial_quality: 初始水质
        setpoint: 目标设定值
    """
    # 测试调优后的控制器
    times, values, outputs = test_tuned_controller(
        result.best_params,
        initial_quality,
        setpoint
    )

    # 创建图表
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # 子图1: 过程值
    axes[0].plot(times, values, 'b-', linewidth=2, label='浊度')
    axes[0].axhline(y=setpoint, color='r', linestyle='--', label='目标值')
    axes[0].set_ylabel('浊度 (NTU)')
    axes[0].set_title(f'PID自动调优结果 - {result.metadata.get("algorithm", "Unknown")}')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 子图2: 控制输出
    axes[1].plot(times, outputs, 'g-', linewidth=2, label='混凝剂投加量')
    axes[1].set_ylabel('投加量 (mg/L)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # 子图3: 收敛历史
    if result.convergence_history:
        axes[2].plot(result.convergence_history, 'r-', linewidth=2)
        axes[2].set_xlabel('迭代次数')
        axes[2].set_ylabel('性能得分')
        axes[2].set_title('优化收敛过程')
        axes[2].grid(True, alpha=0.3)

    # 添加参数文本
    param_text = (f"最优参数:\n"
                  f"Kp = {result.best_params.Kp:.4f}\n"
                  f"Ki = {result.best_params.Ki:.4f}\n"
                  f"Kd = {result.best_params.Kd:.4f}\n"
                  f"得分 = {result.best_score:.6f}")

    fig.text(0.15, 0.02, param_text, fontsize=10,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig('pid_tuning_result.png', dpi=150, bbox_inches='tight')
    print("\n图表已保存至: pid_tuning_result.png")
    plt.show()


def main():
    """主函数。"""
    print("\n" + "=" * 60)
    print("PID自动调优示例程序")
    print("=" * 60)

    # 运行示例
    print("\n请选择要运行的示例:")
    print("1. 简单的自动调优")
    print("2. 遗传算法调优（自定义参数）")
    print("3. 粒子群优化调优")
    print("4. Ziegler-Nichols方法")
    print("5. 比较所有调优方法")
    print("6. 不同优化目标对比")
    print("7. 运行所有示例")

    choice = input("\n请输入选择 (1-7, 默认为1): ").strip() or "1"

    initial_quality = WaterQuality(timestamp=datetime.now(), ph=7.0, turbidity=15.0, dissolved_oxygen=6.0)
    setpoint = 5.0

    if choice == "1":
        result = demo_simple_tuning()
        visualize_tuning_results(result, initial_quality, setpoint)

    elif choice == "2":
        result = demo_genetic_algorithm()
        visualize_tuning_results(result, initial_quality, setpoint)

    elif choice == "3":
        result = demo_particle_swarm()
        visualize_tuning_results(result, initial_quality, setpoint)

    elif choice == "4":
        result = demo_ziegler_nichols()
        visualize_tuning_results(result, initial_quality, setpoint)

    elif choice == "5":
        results = demo_compare_all_methods()
        # 可视化最优结果
        if results:
            best_method = min(results.items(), key=lambda x: x[1].best_score)
            print(f"\n最优方法: {best_method[0]}")
            visualize_tuning_results(best_method[1], initial_quality, setpoint)

    elif choice == "6":
        results = demo_different_objectives()
        # 可视化平衡优化的结果
        if 'balanced' in results:
            visualize_tuning_results(results['balanced'], initial_quality, setpoint)

    elif choice == "7":
        print("\n运行所有示例...")
        demo_simple_tuning()
        demo_genetic_algorithm()
        demo_particle_swarm()
        demo_ziegler_nichols()
        demo_different_objectives()

    else:
        print("无效的选择！")


if __name__ == "__main__":
    main()
