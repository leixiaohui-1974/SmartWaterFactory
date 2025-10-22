#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于Ziegler-Nichols方法的PID参数调优。

实现经典的Ziegler-Nichols调优方法，包括阶跃响应法和临界增益法。
"""

from typing import Optional, Dict, Tuple, List
import numpy as np
import time
from enum import Enum

from .pid_tuner import (
    PIDTuner,
    PIDParameters,
    TuningResult,
    TuningObjective,
    TuningConstraints
)
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController


class ZNMethod(Enum):
    """Ziegler-Nichols方法类型。"""
    STEP_RESPONSE = "step_response"  # 阶跃响应法（开环）
    ULTIMATE_GAIN = "ultimate_gain"  # 临界增益法（闭环）


class ZieglerNicholsTuner(PIDTuner):
    """基于Ziegler-Nichols方法的PID调优器。"""

    def __init__(
        self,
        initial_quality: WaterQuality,
        setpoint: float,
        objective: TuningObjective = TuningObjective.BALANCED,
        constraints: Optional[TuningConstraints] = None,
        simulation_steps: int = 200,
        reverse_acting: bool = True,
        sim_config: Optional[Dict] = None,
        method: ZNMethod = ZNMethod.STEP_RESPONSE
    ):
        """初始化Ziegler-Nichols调优器。

        Args:
            initial_quality: 初始水质
            setpoint: 目标设定值
            objective: 优化目标
            constraints: 参数约束
            simulation_steps: 仿真步数
            reverse_acting: 是否反向作用
            sim_config: 仿真器配置
            method: ZN方法类型
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
        self.method = method

    def _identify_step_response(self) -> Tuple[float, float, float]:
        """通过阶跃响应识别系统参数。

        Returns:
            (K, L, T): 系统增益、延迟时间、时间常数
        """
        # 创建仿真器
        simulator = PlantSimulator(
            initial_quality=self.initial_quality,
            config=self.sim_config
        )

        # 施加阶跃输入
        step_input = 10.0  # 阶跃幅值
        initial_value = simulator.current_quality.turbidity

        # 运行开环仿真
        time_values = []
        output_values = []

        for step in range(self.simulation_steps):
            time_values.append(step)
            output_values.append(simulator.current_quality.turbidity)
            simulator.step(step_input, 0.0)

        # 分析阶跃响应
        final_value = np.mean(output_values[-20:])  # 稳态值
        K = (final_value - initial_value) / step_input  # 系统增益

        # 找到响应到达63.2%的时间点（时间常数）
        target_63 = initial_value + 0.632 * (final_value - initial_value)
        T = 0
        for i, val in enumerate(output_values):
            if val >= target_63:
                T = i
                break

        # 使用切线法估计延迟时间
        # 找到最大斜率点
        slopes = np.diff(output_values)
        max_slope_idx = np.argmax(slopes)
        max_slope = slopes[max_slope_idx]

        # 计算切线与初值和终值的交点
        if abs(max_slope) > 1e-6:
            L = max_slope_idx - (output_values[max_slope_idx] - initial_value) / max_slope
            L = max(0, L)
        else:
            L = 0

        # 时间常数修正
        T = max(T - L, 1)

        return abs(K), L, T

    def _find_ultimate_gain(self) -> Tuple[float, float]:
        """通过临界增益法识别系统参数。

        Returns:
            (Ku, Tu): 临界增益、临界周期
        """
        # 从小Kp开始逐步增加
        Kp = 0.1
        Kp_step = 0.1
        max_Kp = self.constraints.kp_max

        best_Ku = 1.0
        best_Tu = 10.0

        while Kp < max_Kp:
            # 创建仿真器
            simulator = PlantSimulator(
                initial_quality=self.initial_quality,
                config=self.sim_config
            )

            # 创建纯P控制器
            controller = PIDController(
                Kp=Kp,
                Ki=0.0,
                Kd=0.0,
                setpoint=self.setpoint,
                reverse_acting=self.reverse_acting
            )
            controller.set_output_limits(0.0, 20.0)

            # 运行仿真
            values = []
            for _ in range(self.simulation_steps):
                current_value = simulator.current_quality.turbidity
                control_output = controller.calculate(current_value, dt=1.0)
                simulator.step(control_output, 0.0)
                values.append(current_value)

            # 检测振荡
            if self._is_sustained_oscillation(values):
                # 计算振荡周期
                Tu = self._calculate_oscillation_period(values)
                best_Ku = Kp
                best_Tu = Tu
                print(f"找到临界增益: Ku = {Kp:.4f}, Tu = {Tu:.2f}")
                break

            Kp += Kp_step

        return best_Ku, best_Tu

    def _is_sustained_oscillation(self, values: List[float]) -> bool:
        """检测是否存在持续振荡。

        Args:
            values: 过程值序列

        Returns:
            是否存在持续振荡
        """
        if len(values) < 50:
            return False

        # 检查后半段数据
        recent_values = values[-100:]

        # 计算标准差
        std = np.std(recent_values)

        # 如果标准差太小，说明没有振荡
        if std < 0.5:
            return False

        # 统计过零点次数
        mean = np.mean(recent_values)
        crossings = 0
        for i in range(1, len(recent_values)):
            if (recent_values[i-1] - mean) * (recent_values[i] - mean) < 0:
                crossings += 1

        # 如果过零点足够多，说明有振荡
        return crossings >= 4

    def _calculate_oscillation_period(self, values: List[float]) -> float:
        """计算振荡周期。

        Args:
            values: 过程值序列

        Returns:
            振荡周期
        """
        # 使用FFT分析主频率
        fft = np.fft.fft(values[-100:])
        freqs = np.fft.fftfreq(len(fft))

        # 找到主频率（排除直流分量）
        magnitudes = np.abs(fft)
        magnitudes[0] = 0  # 移除直流分量

        peak_idx = np.argmax(magnitudes)
        peak_freq = abs(freqs[peak_idx])

        if peak_freq > 0:
            period = 1.0 / peak_freq
        else:
            period = 10.0  # 默认值

        return period

    def _calculate_zn_parameters_from_step(
        self,
        K: float,
        L: float,
        T: float
    ) -> PIDParameters:
        """根据阶跃响应参数计算ZN参数。

        Args:
            K: 系统增益
            L: 延迟时间
            T: 时间常数

        Returns:
            PID参数
        """
        # Ziegler-Nichols阶跃响应法公式
        if L > 0 and T > 0:
            Kp = 1.2 * T / (K * L)
            Ki = 0.6 / (K * L)
            Kd = 0.6 * T / K
        else:
            # 如果参数无效，使用默认值
            Kp = 1.0
            Ki = 0.1
            Kd = 0.1

        params = PIDParameters(Kp=Kp, Ki=Ki, Kd=Kd)
        return self.constraints.clip(params)

    def _calculate_zn_parameters_from_ultimate(
        self,
        Ku: float,
        Tu: float
    ) -> PIDParameters:
        """根据临界增益参数计算ZN参数。

        Args:
            Ku: 临界增益
            Tu: 临界周期

        Returns:
            PID参数
        """
        # Ziegler-Nichols临界增益法公式（PID控制）
        Kp = 0.6 * Ku
        Ki = 2 * Kp / Tu
        Kd = Kp * Tu / 8

        params = PIDParameters(Kp=Kp, Ki=Ki, Kd=Kd)
        return self.constraints.clip(params)

    def tune(self, max_iterations: int = 50) -> TuningResult:
        """执行Ziegler-Nichols调优。

        Args:
            max_iterations: 参数（本方法不使用迭代）

        Returns:
            调优结果
        """
        start_time = time.time()

        print(f"使用Ziegler-Nichols {self.method.value}方法进行调优...")

        if self.method == ZNMethod.STEP_RESPONSE:
            # 阶跃响应法
            K, L, T = self._identify_step_response()
            print(f"系统参数: K = {K:.4f}, L = {L:.2f}, T = {T:.2f}")

            initial_params = self._calculate_zn_parameters_from_step(K, L, T)
            metadata = {
                "system_gain": K,
                "delay_time": L,
                "time_constant": T
            }

        else:
            # 临界增益法
            Ku, Tu = self._find_ultimate_gain()
            print(f"临界参数: Ku = {Ku:.4f}, Tu = {Tu:.2f}")

            initial_params = self._calculate_zn_parameters_from_ultimate(Ku, Tu)
            metadata = {
                "ultimate_gain": Ku,
                "ultimate_period": Tu
            }

        print(f"ZN建议参数: {initial_params}")

        # 评估初始参数
        initial_score = self.evaluate_parameters(initial_params)

        # 尝试微调（简单的网格搜索）
        print("进行微调优化...")
        best_params = initial_params
        best_score = initial_score

        # 在ZN建议值附近搜索
        for kp_factor in [0.8, 0.9, 1.0, 1.1, 1.2]:
            for ki_factor in [0.8, 0.9, 1.0, 1.1, 1.2]:
                for kd_factor in [0.8, 0.9, 1.0, 1.1, 1.2]:
                    test_params = PIDParameters(
                        Kp=initial_params.Kp * kp_factor,
                        Ki=initial_params.Ki * ki_factor,
                        Kd=initial_params.Kd * kd_factor
                    )
                    test_params = self.constraints.clip(test_params)
                    score = self.evaluate_parameters(test_params)

                    if score < best_score:
                        best_score = score
                        best_params = test_params

        execution_time = time.time() - start_time

        print(f"微调后参数: {best_params}")
        print(f"性能得分: {initial_score:.6f} -> {best_score:.6f}")

        # 创建结果
        result = self._create_result(
            best_params=best_params,
            best_score=best_score,
            iterations=1,
            convergence_history=[initial_score, best_score],
            parameter_history=[initial_params, best_params],
            execution_time=execution_time,
            algorithm=f"Ziegler-Nichols ({self.method.value})",
            initial_params=str(initial_params),
            **metadata
        )

        return result
