#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""控制器基准测试工具。

本模块提供对多个控制器进行基准测试的功能，用于量化对比不同控制策略的性能。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from .performance_metrics import PerformanceMetrics, calculate_metrics


@dataclass
class BenchmarkScenario:
    """基准测试场景配置。"""
    name: str
    description: str
    initial_quality: WaterQuality
    setpoint_turbidity: float
    setpoint_do: float
    simulation_steps: int = 300
    disturbances: Optional[Callable] = None
    sim_config: Optional[Dict] = None


@dataclass
class BenchmarkResult:
    """单个控制器的基准测试结果。"""
    controller_name: str
    controller_type: str
    scenario_name: str

    # 性能指标
    turbidity_metrics: PerformanceMetrics = None
    do_metrics: PerformanceMetrics = None

    # 时间序列数据
    timestamps: List[datetime] = field(default_factory=list)
    turbidity_values: List[float] = field(default_factory=list)
    do_values: List[float] = field(default_factory=list)
    coagulant_outputs: List[float] = field(default_factory=list)
    aeration_outputs: List[float] = field(default_factory=list)
    costs: List[float] = field(default_factory=list)

    # 元数据
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0  # 秒

    def to_dict(self) -> Dict:
        """转换为字典格式。"""
        return {
            'controller_name': self.controller_name,
            'controller_type': self.controller_type,
            'scenario_name': self.scenario_name,
            'turbidity_metrics': self.turbidity_metrics.to_dict() if self.turbidity_metrics else {},
            'do_metrics': self.do_metrics.to_dict() if self.do_metrics else {},
            'execution_time': self.execution_time,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
        }

    def save(self, filepath: str):
        """保存结果到JSON文件。"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class ControllerBenchmark:
    """控制器基准测试工具。"""

    def __init__(self, scenario: BenchmarkScenario):
        """初始化基准测试。

        Args:
            scenario: 测试场景配置
        """
        self.scenario = scenario
        self.results: List[BenchmarkResult] = []

    def run_controller(
        self,
        controller_factory: Callable,
        controller_name: str,
        controller_type: str
    ) -> BenchmarkResult:
        """运行单个控制器的基准测试。

        Args:
            controller_factory: 控制器工厂函数，接受 (setpoint) 返回控制器
            controller_name: 控制器名称
            controller_type: 控制器类型

        Returns:
            基准测试结果
        """
        import time

        result = BenchmarkResult(
            controller_name=controller_name,
            controller_type=controller_type,
            scenario_name=self.scenario.name
        )

        result.start_time = datetime.now()
        start_perf = time.perf_counter()

        # 创建仿真器
        sim_config = self.scenario.sim_config or {}
        simulator = PlantSimulator(
            initial_quality=self.scenario.initial_quality,
            config=sim_config,
            disturbance_provider=self.scenario.disturbances
        )

        # 创建控制器
        turbidity_controller, do_controller = controller_factory(
            turbidity_setpoint=self.scenario.setpoint_turbidity,
            do_setpoint=self.scenario.setpoint_do
        )

        # 运行仿真
        for step in range(self.scenario.simulation_steps):
            # 获取当前状态
            current_quality = simulator.current_quality

            # 计算控制输出
            coagulant_dose = turbidity_controller.calculate(
                current_quality.turbidity,
                dt=1.0
            )
            aeration_rate = do_controller.calculate(
                current_quality.dissolved_oxygen,
                dt=1.0
            )

            # 执行仿真步
            quality = simulator.step(coagulant_dose, aeration_rate)

            # 记录数据
            result.timestamps.append(quality.timestamp)
            result.turbidity_values.append(quality.turbidity)
            result.do_values.append(quality.dissolved_oxygen)
            result.coagulant_outputs.append(coagulant_dose)
            result.aeration_outputs.append(aeration_rate)

            # 估算成本（简化）
            cost = coagulant_dose * 0.5 + aeration_rate * 0.3
            result.costs.append(cost)

        # 计算性能指标
        result.turbidity_metrics = calculate_metrics(
            setpoint=self.scenario.setpoint_turbidity,
            process_values=result.turbidity_values,
            control_outputs=result.coagulant_outputs,
            costs=result.costs,
            controller_type=controller_type,
            dt=1.0
        )

        result.do_metrics = calculate_metrics(
            setpoint=self.scenario.setpoint_do,
            process_values=result.do_values,
            control_outputs=result.aeration_outputs,
            costs=result.costs,
            controller_type=controller_type,
            dt=1.0
        )

        result.end_time = datetime.now()
        result.execution_time = time.perf_counter() - start_perf

        self.results.append(result)
        return result

    def compare_results(self) -> Dict:
        """对比所有控制器的性能。

        Returns:
            对比结果字典
        """
        if not self.results:
            return {}

        comparison = {
            'scenario': self.scenario.name,
            'controllers': [r.controller_name for r in self.results],
            'turbidity_comparison': {},
            'do_comparison': {},
            'summary': {}
        }

        # 浊度指标对比
        turbidity_metrics = [r.turbidity_metrics for r in self.results]
        comparison['turbidity_comparison'] = self._compare_metrics_list(
            turbidity_metrics,
            [r.controller_name for r in self.results]
        )

        # 溶解氧指标对比
        do_metrics = [r.do_metrics for r in self.results]
        comparison['do_comparison'] = self._compare_metrics_list(
            do_metrics,
            [r.controller_name for r in self.results]
        )

        # 综合评分（简化版）
        comparison['summary'] = self._calculate_summary(self.results)

        return comparison

    def _compare_metrics_list(
        self,
        metrics_list: List[PerformanceMetrics],
        controller_names: List[str]
    ) -> Dict:
        """对比指标列表。"""
        comparison = {}

        metric_keys = ['iae', 'ise', 'overshoot', 'settling_time',
                       'steady_state_error', 'total_cost', 'control_effort']

        for key in metric_keys:
            values = [getattr(m, key, None) for m in metrics_list]
            valid_values = [v for v, n in zip(values, controller_names) if v is not None]
            valid_names = [n for v, n in zip(values, controller_names) if v is not None]

            if valid_values:
                best_idx = valid_values.index(min(valid_values))
                worst_idx = valid_values.index(max(valid_values))

                comparison[key] = {
                    'values': dict(zip(controller_names, values)),
                    'best': valid_values[best_idx],
                    'best_controller': valid_names[best_idx],
                    'worst': valid_values[worst_idx],
                    'worst_controller': valid_names[worst_idx],
                }

        return comparison

    def _calculate_summary(self, results: List[BenchmarkResult]) -> Dict:
        """计算综合评分。"""
        scores = {}

        for result in results:
            # 简化评分：IAE越小越好，成本越低越好
            iae_score = 1000 / (result.turbidity_metrics.iae + 1)
            cost_score = 1000 / (result.turbidity_metrics.total_cost + 1)
            settling_score = 1000 / (result.turbidity_metrics.settling_time + 1) if result.turbidity_metrics.settling_time else 0

            total_score = iae_score + cost_score + settling_score
            scores[result.controller_name] = {
                'total_score': total_score,
                'iae_score': iae_score,
                'cost_score': cost_score,
                'settling_score': settling_score
            }

        # 排名
        ranked = sorted(scores.items(), key=lambda x: x[1]['total_score'], reverse=True)
        return {
            'scores': scores,
            'ranking': [name for name, _ in ranked]
        }

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """生成对比报告。

        Args:
            output_path: 输出文件路径（可选）

        Returns:
            报告文本
        """
        comparison = self.compare_results()

        report_lines = [
            "=" * 80,
            f"控制器基准测试报告",
            f"场景: {self.scenario.name}",
            f"描述: {self.scenario.description}",
            "=" * 80,
            "",
            "【参与控制器】",
        ]

        for i, controller in enumerate(comparison['controllers'], 1):
            result = self.results[i-1]
            report_lines.append(
                f"  {i}. {controller} ({result.controller_type}) - "
                f"执行时间: {result.execution_time:.3f}秒"
            )

        report_lines.extend([
            "",
            "【浊度控制性能对比】",
            "-" * 80,
        ])

        turb_comp = comparison['turbidity_comparison']
        for metric, data in turb_comp.items():
            report_lines.append(f"  {metric}:")
            report_lines.append(f"    最优: {data['best']:.4f} ({data['best_controller']})")
            report_lines.append(f"    最差: {data['worst']:.4f} ({data['worst_controller']})")
            for ctrl, val in data['values'].items():
                if val is not None:
                    report_lines.append(f"      {ctrl}: {val:.4f}")

        report_lines.extend([
            "",
            "【综合排名】",
            "-" * 80,
        ])

        for i, controller in enumerate(comparison['summary']['ranking'], 1):
            score_data = comparison['summary']['scores'][controller]
            report_lines.append(
                f"  {i}. {controller} - 总分: {score_data['total_score']:.2f}"
            )

        report_lines.append("=" * 80)

        report = "\n".join(report_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)

        return report


def run_benchmark(
    scenario: BenchmarkScenario,
    controllers: List[Tuple[str, str, Callable]],
    output_dir: Optional[str] = None
) -> ControllerBenchmark:
    """运行基准测试的便捷函数。

    Args:
        scenario: 测试场景
        controllers: 控制器列表，格式为 [(name, type, factory), ...]
        output_dir: 输出目录（可选）

    Returns:
        基准测试对象
    """
    benchmark = ControllerBenchmark(scenario)

    print(f"开始基准测试: {scenario.name}")
    print(f"测试控制器数量: {len(controllers)}")
    print("-" * 60)

    for name, ctrl_type, factory in controllers:
        print(f"  运行: {name} ({ctrl_type})...", end=" ")
        result = benchmark.run_controller(factory, name, ctrl_type)
        print(f"完成 (耗时: {result.execution_time:.3f}秒)")

    print("-" * 60)
    print("所有测试完成！")

    # 生成报告
    report = benchmark.generate_report()
    print("\n" + report)

    # 保存结果
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存报告
        report_file = output_path / f"benchmark_report_{scenario.name}.txt"
        benchmark.generate_report(str(report_file))

        # 保存详细结果
        for result in benchmark.results:
            result_file = output_path / f"{result.controller_name}_{scenario.name}.json"
            result.save(str(result_file))

        print(f"\n结果已保存到: {output_path}")

    return benchmark
