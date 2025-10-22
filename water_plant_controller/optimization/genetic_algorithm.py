#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于遗传算法的PID参数自动调优。

使用遗传算法优化PID参数，通过模拟自然选择过程找到最优参数组合。
"""

from typing import List, Tuple, Optional, Dict
import numpy as np
import time
from dataclasses import dataclass

from .pid_tuner import (
    PIDTuner,
    PIDParameters,
    TuningResult,
    TuningObjective,
    TuningConstraints
)
from water_plant_controller.models.water_quality import WaterQuality


@dataclass
class GeneticAlgorithmConfig:
    """遗传算法配置。"""
    population_size: int = 50  # 种群大小
    elite_size: int = 5  # 精英个体数量
    mutation_rate: float = 0.1  # 变异率
    crossover_rate: float = 0.8  # 交叉率
    tournament_size: int = 3  # 锦标赛选择大小
    convergence_threshold: float = 1e-6  # 收敛阈值
    convergence_generations: int = 10  # 收敛判断的代数


class GeneticAlgorithmTuner(PIDTuner):
    """基于遗传算法的PID调优器。"""

    def __init__(
        self,
        initial_quality: WaterQuality,
        setpoint: float,
        objective: TuningObjective = TuningObjective.BALANCED,
        constraints: Optional[TuningConstraints] = None,
        simulation_steps: int = 200,
        reverse_acting: bool = True,
        sim_config: Optional[Dict] = None,
        ga_config: Optional[GeneticAlgorithmConfig] = None
    ):
        """初始化遗传算法调优器。

        Args:
            initial_quality: 初始水质
            setpoint: 目标设定值
            objective: 优化目标
            constraints: 参数约束
            simulation_steps: 仿真步数
            reverse_acting: 是否反向作用
            sim_config: 仿真器配置
            ga_config: 遗传算法配置
        """
        super().__init__(
            initial_quality=initial_quality,
            setpoint=setpoint,
            objective=objective,
            constraints=constraints,
            simulation_steps=simulation_steps,
            reverse_acting=reverse_acting,
            sim_config=sim_config
        )
        self.ga_config = ga_config or GeneticAlgorithmConfig()

        # 种群和适应度
        self.population: List[PIDParameters] = []
        self.fitness: List[float] = []

    def _initialize_population(self) -> None:
        """初始化种群。"""
        self.population = []
        bounds = self.constraints.get_bounds()

        for _ in range(self.ga_config.population_size):
            # 在约束范围内随机生成参数
            kp = np.random.uniform(bounds[0][0], bounds[0][1])
            ki = np.random.uniform(bounds[1][0], bounds[1][1])
            kd = np.random.uniform(bounds[2][0], bounds[2][1])
            self.population.append(PIDParameters(kp, ki, kd))

    def _evaluate_population(self) -> None:
        """评估种群适应度。"""
        self.fitness = []
        for params in self.population:
            score = self.evaluate_parameters(params)
            self.fitness.append(score)

    def _tournament_selection(self) -> PIDParameters:
        """锦标赛选择。

        Returns:
            选中的个体
        """
        # 随机选择若干个体
        indices = np.random.choice(
            len(self.population),
            size=self.ga_config.tournament_size,
            replace=False
        )

        # 选择适应度最好的
        best_idx = min(indices, key=lambda i: self.fitness[i])
        return self.population[best_idx]

    def _crossover(
        self,
        parent1: PIDParameters,
        parent2: PIDParameters
    ) -> Tuple[PIDParameters, PIDParameters]:
        """单点交叉操作。

        Args:
            parent1: 父代1
            parent2: 父代2

        Returns:
            两个子代
        """
        if np.random.random() > self.ga_config.crossover_rate:
            # 不进行交叉，直接返回父代
            return parent1, parent2

        # 转换为数组
        p1 = parent1.to_array()
        p2 = parent2.to_array()

        # 随机选择交叉点
        crossover_point = np.random.randint(1, 3)

        # 创建子代
        c1 = np.concatenate([p1[:crossover_point], p2[crossover_point:]])
        c2 = np.concatenate([p2[:crossover_point], p1[crossover_point:]])

        child1 = PIDParameters.from_array(c1)
        child2 = PIDParameters.from_array(c2)

        return child1, child2

    def _mutate(self, params: PIDParameters) -> PIDParameters:
        """变异操作。

        Args:
            params: 待变异的参数

        Returns:
            变异后的参数
        """
        if np.random.random() > self.ga_config.mutation_rate:
            # 不进行变异
            return params

        arr = params.to_array()
        bounds = self.constraints.get_bounds()

        # 随机选择一个参数进行变异
        gene_idx = np.random.randint(0, 3)

        # 高斯变异
        mutation_strength = 0.1 * (bounds[gene_idx][1] - bounds[gene_idx][0])
        arr[gene_idx] += np.random.normal(0, mutation_strength)

        # 确保在范围内
        mutated = PIDParameters.from_array(arr)
        return self.constraints.clip(mutated)

    def _get_elites(self) -> List[PIDParameters]:
        """获取精英个体。

        Returns:
            精英个体列表
        """
        elite_indices = np.argsort(self.fitness)[:self.ga_config.elite_size]
        return [self.population[i] for i in elite_indices]

    def _create_next_generation(self) -> None:
        """创建下一代种群。"""
        # 保留精英
        next_population = self._get_elites()

        # 生成新个体直到种群满
        while len(next_population) < self.ga_config.population_size:
            # 选择父代
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()

            # 交叉
            child1, child2 = self._crossover(parent1, parent2)

            # 变异
            child1 = self._mutate(child1)
            child2 = self._mutate(child2)

            # 添加到新种群
            next_population.append(child1)
            if len(next_population) < self.ga_config.population_size:
                next_population.append(child2)

        self.population = next_population

    def _check_convergence(
        self,
        convergence_history: List[float]
    ) -> bool:
        """检查是否收敛。

        Args:
            convergence_history: 历史最优值

        Returns:
            是否收敛
        """
        if len(convergence_history) < self.ga_config.convergence_generations:
            return False

        recent_scores = convergence_history[-self.ga_config.convergence_generations:]
        variance = np.var(recent_scores)

        return variance < self.ga_config.convergence_threshold

    def tune(self, max_iterations: int = 50) -> TuningResult:
        """执行遗传算法调优。

        Args:
            max_iterations: 最大迭代代数

        Returns:
            调优结果
        """
        start_time = time.time()

        # 初始化
        self._initialize_population()
        self._evaluate_population()

        convergence_history = []
        parameter_history = []

        # 迭代进化
        for generation in range(max_iterations):
            # 记录当前最优
            best_idx = np.argmin(self.fitness)
            best_score = self.fitness[best_idx]
            best_params = self.population[best_idx]

            convergence_history.append(best_score)
            parameter_history.append(best_params)

            print(f"代数 {generation + 1}/{max_iterations}: "
                  f"最优得分 = {best_score:.6f}, "
                  f"参数 = {best_params}")

            # 检查收敛
            if self._check_convergence(convergence_history):
                print(f"在第 {generation + 1} 代收敛")
                break

            # 创建下一代
            self._create_next_generation()
            self._evaluate_population()

        # 获取最终最优结果
        best_idx = np.argmin(self.fitness)
        final_best_score = self.fitness[best_idx]
        final_best_params = self.population[best_idx]

        execution_time = time.time() - start_time

        # 创建结果
        result = self._create_result(
            best_params=final_best_params,
            best_score=final_best_score,
            iterations=generation + 1,
            convergence_history=convergence_history,
            parameter_history=parameter_history,
            execution_time=execution_time,
            algorithm="Genetic Algorithm",
            population_size=self.ga_config.population_size,
            mutation_rate=self.ga_config.mutation_rate,
            crossover_rate=self.ga_config.crossover_rate
        )

        return result
