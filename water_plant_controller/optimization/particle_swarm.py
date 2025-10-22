#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于粒子群优化的PID参数自动调优。

使用粒子群优化算法(PSO)优化PID参数，通过模拟鸟群觅食行为找到最优参数组合。
"""

from typing import List, Optional, Dict
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
class Particle:
    """粒子类。"""
    position: PIDParameters  # 当前位置（参数）
    velocity: np.ndarray  # 速度
    best_position: PIDParameters  # 历史最优位置
    best_score: float = float('inf')  # 历史最优得分


@dataclass
class ParticleSwarmConfig:
    """粒子群优化配置。"""
    swarm_size: int = 30  # 粒子群大小
    inertia_weight: float = 0.7  # 惯性权重
    cognitive_weight: float = 1.5  # 认知权重（个体学习因子）
    social_weight: float = 1.5  # 社会权重（群体学习因子）
    max_velocity: float = 1.0  # 最大速度
    convergence_threshold: float = 1e-6  # 收敛阈值
    convergence_iterations: int = 10  # 收敛判断的迭代次数


class ParticleSwarmTuner(PIDTuner):
    """基于粒子群优化的PID调优器。"""

    def __init__(
        self,
        initial_quality: WaterQuality,
        setpoint: float,
        objective: TuningObjective = TuningObjective.BALANCED,
        constraints: Optional[TuningConstraints] = None,
        simulation_steps: int = 200,
        reverse_acting: bool = True,
        sim_config: Optional[Dict] = None,
        pso_config: Optional[ParticleSwarmConfig] = None
    ):
        """初始化粒子群优化调优器。

        Args:
            initial_quality: 初始水质
            setpoint: 目标设定值
            objective: 优化目标
            constraints: 参数约束
            simulation_steps: 仿真步数
            reverse_acting: 是否反向作用
            sim_config: 仿真器配置
            pso_config: PSO配置
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
        self.pso_config = pso_config or ParticleSwarmConfig()

        # 粒子群和全局最优
        self.swarm: List[Particle] = []
        self.global_best_position: Optional[PIDParameters] = None
        self.global_best_score: float = float('inf')

    def _initialize_swarm(self) -> None:
        """初始化粒子群。"""
        self.swarm = []
        bounds = self.constraints.get_bounds()

        for _ in range(self.pso_config.swarm_size):
            # 随机初始化位置
            kp = np.random.uniform(bounds[0][0], bounds[0][1])
            ki = np.random.uniform(bounds[1][0], bounds[1][1])
            kd = np.random.uniform(bounds[2][0], bounds[2][1])
            position = PIDParameters(kp, ki, kd)

            # 随机初始化速度
            velocity = np.random.uniform(
                -self.pso_config.max_velocity,
                self.pso_config.max_velocity,
                size=3
            )

            # 创建粒子
            particle = Particle(
                position=position,
                velocity=velocity,
                best_position=position,
                best_score=float('inf')
            )

            self.swarm.append(particle)

    def _evaluate_swarm(self) -> None:
        """评估粒子群。"""
        for particle in self.swarm:
            # 评估当前位置
            score = self.evaluate_parameters(particle.position)

            # 更新个体最优
            if score < particle.best_score:
                particle.best_score = score
                particle.best_position = particle.position

            # 更新全局最优
            if score < self.global_best_score:
                self.global_best_score = score
                self.global_best_position = particle.position

    def _update_velocity(self, particle: Particle) -> np.ndarray:
        """更新粒子速度。

        Args:
            particle: 粒子

        Returns:
            新速度
        """
        # 当前参数
        current = particle.position.to_array()

        # 个体最优
        pbest = particle.best_position.to_array()

        # 全局最优
        gbest = self.global_best_position.to_array()

        # 随机因子
        r1 = np.random.random(3)
        r2 = np.random.random(3)

        # 速度更新公式
        velocity = (
            self.pso_config.inertia_weight * particle.velocity +
            self.pso_config.cognitive_weight * r1 * (pbest - current) +
            self.pso_config.social_weight * r2 * (gbest - current)
        )

        # 限制最大速度
        velocity = np.clip(
            velocity,
            -self.pso_config.max_velocity,
            self.pso_config.max_velocity
        )

        return velocity

    def _update_position(self, particle: Particle) -> PIDParameters:
        """更新粒子位置。

        Args:
            particle: 粒子

        Returns:
            新位置
        """
        # 更新速度
        particle.velocity = self._update_velocity(particle)

        # 更新位置
        new_position_array = particle.position.to_array() + particle.velocity
        new_position = PIDParameters.from_array(new_position_array)

        # 确保在约束范围内
        return self.constraints.clip(new_position)

    def _update_swarm(self) -> None:
        """更新整个粒子群。"""
        for particle in self.swarm:
            particle.position = self._update_position(particle)

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
        if len(convergence_history) < self.pso_config.convergence_iterations:
            return False

        recent_scores = convergence_history[-self.pso_config.convergence_iterations:]
        variance = np.var(recent_scores)

        return variance < self.pso_config.convergence_threshold

    def tune(self, max_iterations: int = 50) -> TuningResult:
        """执行粒子群优化调优。

        Args:
            max_iterations: 最大迭代次数

        Returns:
            调优结果
        """
        start_time = time.time()

        # 初始化
        self._initialize_swarm()
        self._evaluate_swarm()

        convergence_history = []
        parameter_history = []

        # 迭代优化
        for iteration in range(max_iterations):
            # 记录当前全局最优
            convergence_history.append(self.global_best_score)
            parameter_history.append(self.global_best_position)

            print(f"迭代 {iteration + 1}/{max_iterations}: "
                  f"最优得分 = {self.global_best_score:.6f}, "
                  f"参数 = {self.global_best_position}")

            # 检查收敛
            if self._check_convergence(convergence_history):
                print(f"在第 {iteration + 1} 次迭代收敛")
                break

            # 更新粒子群
            self._update_swarm()
            self._evaluate_swarm()

        execution_time = time.time() - start_time

        # 创建结果
        result = self._create_result(
            best_params=self.global_best_position,
            best_score=self.global_best_score,
            iterations=iteration + 1,
            convergence_history=convergence_history,
            parameter_history=parameter_history,
            execution_time=execution_time,
            algorithm="Particle Swarm Optimization",
            swarm_size=self.pso_config.swarm_size,
            inertia_weight=self.pso_config.inertia_weight,
            cognitive_weight=self.pso_config.cognitive_weight,
            social_weight=self.pso_config.social_weight
        )

        return result
