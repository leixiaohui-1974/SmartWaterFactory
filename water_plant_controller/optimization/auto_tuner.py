#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PID自动调优统一接口。

提供简单易用的API来自动调优PID参数。
"""

from typing import Optional, Dict, List
from enum import Enum

from .pid_tuner import (
    PIDParameters,
    TuningResult,
    TuningObjective,
    TuningConstraints
)
from .genetic_algorithm import GeneticAlgorithmTuner, GeneticAlgorithmConfig
from .particle_swarm import ParticleSwarmTuner, ParticleSwarmConfig
from .ziegler_nichols import ZieglerNicholsTuner, ZNMethod
from water_plant_controller.models.water_quality import WaterQuality


class TuningMethod(Enum):
    """调优方法类型。"""
    AUTO = "auto"  # 自动选择
    GENETIC_ALGORITHM = "genetic_algorithm"  # 遗传算法
    PARTICLE_SWARM = "particle_swarm"  # 粒子群优化
    ZIEGLER_NICHOLS = "ziegler_nichols"  # Ziegler-Nichols方法
    ALL = "all"  # 运行所有方法并比较


class AutoTuner:
    """PID自动调优器统一接口。"""

    def __init__(
        self,
        initial_quality: WaterQuality,
        setpoint: float,
        objective: TuningObjective = TuningObjective.BALANCED,
        constraints: Optional[TuningConstraints] = None,
        simulation_steps: int = 200,
        reverse_acting: bool = True,
        sim_config: Optional[Dict] = None
    ):
        """初始化自动调优器。

        Args:
            initial_quality: 初始水质
            setpoint: 目标设定值
            objective: 优化目标
            constraints: 参数约束
            simulation_steps: 仿真步数
            reverse_acting: 是否反向作用
            sim_config: 仿真器配置
        """
        self.initial_quality = initial_quality
        self.setpoint = setpoint
        self.objective = objective
        self.constraints = constraints or TuningConstraints()
        self.simulation_steps = simulation_steps
        self.reverse_acting = reverse_acting
        self.sim_config = sim_config or {}

    def tune(
        self,
        method: TuningMethod = TuningMethod.AUTO,
        max_iterations: int = 50,
        **kwargs
    ) -> TuningResult:
        """执行自动调优。

        Args:
            method: 调优方法
            max_iterations: 最大迭代次数
            **kwargs: 方法特定的参数

        Returns:
            调优结果
        """
        if method == TuningMethod.AUTO:
            # 自动选择：优先使用遗传算法
            method = TuningMethod.GENETIC_ALGORITHM

        if method == TuningMethod.GENETIC_ALGORITHM:
            return self._tune_with_ga(max_iterations, **kwargs)

        elif method == TuningMethod.PARTICLE_SWARM:
            return self._tune_with_pso(max_iterations, **kwargs)

        elif method == TuningMethod.ZIEGLER_NICHOLS:
            return self._tune_with_zn(**kwargs)

        elif method == TuningMethod.ALL:
            return self._tune_with_all(max_iterations, **kwargs)

        else:
            raise ValueError(f"未知的调优方法: {method}")

    def _tune_with_ga(
        self,
        max_iterations: int,
        **kwargs
    ) -> TuningResult:
        """使用遗传算法调优。"""
        print("=" * 60)
        print("使用遗传算法进行PID参数调优")
        print("=" * 60)

        # 创建GA配置
        ga_config = kwargs.get('ga_config', GeneticAlgorithmConfig())

        # 创建调优器
        tuner = GeneticAlgorithmTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            objective=self.objective,
            constraints=self.constraints,
            simulation_steps=self.simulation_steps,
            reverse_acting=self.reverse_acting,
            sim_config=self.sim_config,
            ga_config=ga_config
        )

        # 执行调优
        result = tuner.tune(max_iterations=max_iterations)

        print("=" * 60)
        print(result)
        return result

    def _tune_with_pso(
        self,
        max_iterations: int,
        **kwargs
    ) -> TuningResult:
        """使用粒子群优化调优。"""
        print("=" * 60)
        print("使用粒子群优化进行PID参数调优")
        print("=" * 60)

        # 创建PSO配置
        pso_config = kwargs.get('pso_config', ParticleSwarmConfig())

        # 创建调优器
        tuner = ParticleSwarmTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            objective=self.objective,
            constraints=self.constraints,
            simulation_steps=self.simulation_steps,
            reverse_acting=self.reverse_acting,
            sim_config=self.sim_config,
            pso_config=pso_config
        )

        # 执行调优
        result = tuner.tune(max_iterations=max_iterations)

        print("=" * 60)
        print(result)
        return result

    def _tune_with_zn(self, **kwargs) -> TuningResult:
        """使用Ziegler-Nichols方法调优。"""
        print("=" * 60)
        print("使用Ziegler-Nichols方法进行PID参数调优")
        print("=" * 60)

        # 选择ZN方法
        zn_method = kwargs.get('zn_method', ZNMethod.STEP_RESPONSE)

        # 创建调优器
        tuner = ZieglerNicholsTuner(
            initial_quality=self.initial_quality,
            setpoint=self.setpoint,
            objective=self.objective,
            constraints=self.constraints,
            simulation_steps=self.simulation_steps,
            reverse_acting=self.reverse_acting,
            sim_config=self.sim_config,
            method=zn_method
        )

        # 执行调优
        result = tuner.tune()

        print("=" * 60)
        print(result)
        return result

    def _tune_with_all(
        self,
        max_iterations: int,
        **kwargs
    ) -> Dict[str, TuningResult]:
        """使用所有方法调优并比较。"""
        print("\n" + "=" * 60)
        print("运行所有调优方法并比较结果")
        print("=" * 60 + "\n")

        results = {}

        # 1. Ziegler-Nichols
        try:
            results['ziegler_nichols'] = self._tune_with_zn(**kwargs)
        except Exception as e:
            print(f"Ziegler-Nichols方法失败: {e}")

        # 2. 遗传算法
        try:
            results['genetic_algorithm'] = self._tune_with_ga(max_iterations, **kwargs)
        except Exception as e:
            print(f"遗传算法失败: {e}")

        # 3. 粒子群优化
        try:
            results['particle_swarm'] = self._tune_with_pso(max_iterations, **kwargs)
        except Exception as e:
            print(f"粒子群优化失败: {e}")

        # 打印比较结果
        self._print_comparison(results)

        return results

    def _print_comparison(self, results: Dict[str, TuningResult]) -> None:
        """打印调优结果比较。"""
        print("\n" + "=" * 60)
        print("调优方法比较")
        print("=" * 60)

        # 按得分排序
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].best_score
        )

        print(f"\n{'方法':<20} {'得分':<12} {'参数':<40} {'时间(秒)':<10}")
        print("-" * 90)

        for method, result in sorted_results:
            print(f"{method:<20} {result.best_score:<12.6f} "
                  f"{str(result.best_params):<40} {result.execution_time:<10.2f}")

        print("\n最优方法: " + sorted_results[0][0])
        print("最优参数: " + str(sorted_results[0][1].best_params))
        print("=" * 60 + "\n")


def tune_pid(
    initial_quality: WaterQuality,
    setpoint: float,
    method: TuningMethod = TuningMethod.AUTO,
    objective: TuningObjective = TuningObjective.BALANCED,
    constraints: Optional[TuningConstraints] = None,
    simulation_steps: int = 200,
    reverse_acting: bool = True,
    max_iterations: int = 50,
    sim_config: Optional[Dict] = None,
    **kwargs
) -> TuningResult:
    """便捷函数：自动调优PID参数。

    Args:
        initial_quality: 初始水质
        setpoint: 目标设定值
        method: 调优方法
        objective: 优化目标
        constraints: 参数约束
        simulation_steps: 仿真步数
        reverse_acting: 是否反向作用
        max_iterations: 最大迭代次数
        sim_config: 仿真器配置
        **kwargs: 方法特定的参数

    Returns:
        调优结果

    Examples:
        >>> from water_plant_controller.models.water_quality import WaterQuality
        >>> from water_plant_controller.optimization import tune_pid, TuningObjective
        >>>
        >>> # 创建初始水质
        >>> initial_quality = WaterQuality(turbidity=15.0, do_level=6.0)
        >>>
        >>> # 自动调优（使用遗传算法）
        >>> result = tune_pid(
        ...     initial_quality=initial_quality,
        ...     setpoint=5.0,
        ...     objective=TuningObjective.BALANCED
        ... )
        >>>
        >>> print(f"最优参数: {result.best_params}")
        >>> print(f"性能得分: {result.best_score}")
    """
    tuner = AutoTuner(
        initial_quality=initial_quality,
        setpoint=setpoint,
        objective=objective,
        constraints=constraints,
        simulation_steps=simulation_steps,
        reverse_acting=reverse_acting,
        sim_config=sim_config
    )

    return tuner.tune(
        method=method,
        max_iterations=max_iterations,
        **kwargs
    )
