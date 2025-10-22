#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PID参数自动调优基类。

提供PID参数优化的通用框架和接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Tuple, Callable, Optional, Dict, List, Any
from enum import Enum
import numpy as np
from datetime import datetime

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.analysis.performance_metrics import calculate_metrics


class TuningObjective(Enum):
    """调优目标类型。"""
    MINIMIZE_IAE = "minimize_iae"  # 最小化IAE
    MINIMIZE_ISE = "minimize_ise"  # 最小化ISE
    MINIMIZE_ITAE = "minimize_itae"  # 最小化ITAE
    MINIMIZE_OVERSHOOT = "minimize_overshoot"  # 最小化超调
    MINIMIZE_SETTLING_TIME = "minimize_settling_time"  # 最小化调节时间
    BALANCED = "balanced"  # 平衡多个目标
    MINIMIZE_COST = "minimize_cost"  # 最小化成本


@dataclass
class PIDParameters:
    """PID参数。"""
    Kp: float
    Ki: float
    Kd: float

    def to_array(self) -> np.ndarray:
        """转换为数组。"""
        return np.array([self.Kp, self.Ki, self.Kd])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'PIDParameters':
        """从数组创建。"""
        return cls(Kp=float(arr[0]), Ki=float(arr[1]), Kd=float(arr[2]))

    def __str__(self):
        return f"Kp={self.Kp:.4f}, Ki={self.Ki:.4f}, Kd={self.Kd:.4f}"


@dataclass
class TuningConstraints:
    """调优约束条件。"""
    kp_min: float = 0.0
    kp_max: float = 10.0
    ki_min: float = 0.0
    ki_max: float = 2.0
    kd_min: float = 0.0
    kd_max: float = 5.0

    def clip(self, params: PIDParameters) -> PIDParameters:
        """将参数裁剪到约束范围内。"""
        return PIDParameters(
            Kp=np.clip(params.Kp, self.kp_min, self.kp_max),
            Ki=np.clip(params.Ki, self.ki_min, self.ki_max),
            Kd=np.clip(params.Kd, self.kd_min, self.kd_max)
        )

    def get_bounds(self) -> List[Tuple[float, float]]:
        """获取边界元组列表。"""
        return [
            (self.kp_min, self.kp_max),
            (self.ki_min, self.ki_max),
            (self.kd_min, self.kd_max)
        ]


@dataclass
class TuningResult:
    """调优结果。"""
    best_params: PIDParameters
    best_score: float
    objective: TuningObjective
    iterations: int
    evaluation_count: int
    convergence_history: List[float] = field(default_factory=list)
    parameter_history: List[PIDParameters] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"""
调优结果:
  最优参数: {self.best_params}
  最优得分: {self.best_score:.6f}
  目标函数: {self.objective.value}
  迭代次数: {self.iterations}
  评估次数: {self.evaluation_count}
  执行时间: {self.execution_time:.2f}秒
"""


class PIDTuner(ABC):
    """PID调优器基类。"""

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
        """初始化调优器。

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

        # 统计信息
        self.evaluation_count = 0
        self.best_score = float('inf')
        self.best_params: Optional[PIDParameters] = None

    def evaluate_parameters(self, params: PIDParameters) -> float:
        """评估PID参数的性能。

        Args:
            params: PID参数

        Returns:
            性能得分（越小越好）
        """
        self.evaluation_count += 1

        # 确保参数在约束范围内
        params = self.constraints.clip(params)

        # 创建仿真器
        simulator = PlantSimulator(
            initial_quality=self.initial_quality,
            config=self.sim_config
        )

        # 创建控制器
        controller = PIDController(
            Kp=params.Kp,
            Ki=params.Ki,
            Kd=params.Kd,
            setpoint=self.setpoint,
            reverse_acting=self.reverse_acting
        )
        controller.set_output_limits(0.0, 20.0)

        # 运行仿真
        process_values = []
        control_outputs = []

        for _ in range(self.simulation_steps):
            current_value = simulator.current_quality.turbidity
            control_output = controller.calculate(current_value, dt=1.0)
            simulator.step(control_output, 0.0)  # 只控制浊度

            process_values.append(current_value)
            control_outputs.append(control_output)

        # 计算性能指标
        metrics = calculate_metrics(
            setpoint=self.setpoint,
            process_values=process_values,
            control_outputs=control_outputs,
            dt=1.0
        )

        # 根据目标计算得分
        score = self._calculate_score(metrics)

        # 更新最优结果
        if score < self.best_score:
            self.best_score = score
            self.best_params = params

        return score

    def _calculate_score(self, metrics) -> float:
        """根据目标计算得分。"""
        if self.objective == TuningObjective.MINIMIZE_IAE:
            return metrics.iae
        elif self.objective == TuningObjective.MINIMIZE_ISE:
            return metrics.ise
        elif self.objective == TuningObjective.MINIMIZE_ITAE:
            return metrics.itae
        elif self.objective == TuningObjective.MINIMIZE_OVERSHOOT:
            return metrics.overshoot + metrics.iae * 0.1
        elif self.objective == TuningObjective.MINIMIZE_SETTLING_TIME:
            settling = metrics.settling_time if metrics.settling_time else 1000
            return settling + metrics.overshoot * 0.1
        elif self.objective == TuningObjective.MINIMIZE_COST:
            return metrics.total_cost + metrics.iae * 0.1
        else:  # BALANCED
            # 平衡多个目标
            iae_norm = metrics.iae / 100.0
            overshoot_norm = metrics.overshoot / 100.0
            settling = metrics.settling_time if metrics.settling_time else 200
            settling_norm = settling / 200.0
            return iae_norm + overshoot_norm * 0.5 + settling_norm * 0.3

    @abstractmethod
    def tune(self, max_iterations: int = 50) -> TuningResult:
        """执行参数调优。

        Args:
            max_iterations: 最大迭代次数

        Returns:
            调优结果
        """
        pass

    def _create_result(
        self,
        best_params: PIDParameters,
        best_score: float,
        iterations: int,
        convergence_history: List[float],
        parameter_history: List[PIDParameters],
        execution_time: float,
        **metadata
    ) -> TuningResult:
        """创建调优结果对象。"""
        return TuningResult(
            best_params=best_params,
            best_score=best_score,
            objective=self.objective,
            iterations=iterations,
            evaluation_count=self.evaluation_count,
            convergence_history=convergence_history,
            parameter_history=parameter_history,
            execution_time=execution_time,
            metadata=metadata
        )
