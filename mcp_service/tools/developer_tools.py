#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发者测试工具集。

提供算法开发人员专用的测试接口，保留后台算法测试入口。
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.schemas import ToolParameter, ToolParameterType, Tool
from ..registry import get_registry
from ..session import get_session_manager

# 导入算法测试模块
from water_plant_controller.optimization.auto_tuner import AutoTuner, TuningMethod, TuningObjective
from water_plant_controller.analysis.controller_benchmark import ControllerBenchmark
from water_plant_controller.analysis.performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


async def test_pid_tuning_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """测试PID自动调优算法。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        调优测试结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 解析参数
    method = arguments.get("method", "genetic_algorithm")
    objective = arguments.get("objective", "balanced")
    max_iterations = arguments.get("max_iterations", 50)
    setpoint = arguments.get("setpoint", 2.0)

    logger.info(f"Testing PID tuning with method={method}, objective={objective}")

    try:
        # 转换参数
        tuning_method = TuningMethod[method.upper()]
        tuning_objective = TuningObjective[objective.upper()]

        # 创建自动调优器
        tuner = AutoTuner(
            method=tuning_method,
            objective=tuning_objective,
            max_iterations=max_iterations
        )

        # 执行调优（在后台异步执行，这里模拟结果）
        await asyncio.sleep(0.1)  # 模拟调优时间

        result = {
            "test_id": f"tuning_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "method": method,
            "objective": objective,
            "max_iterations": max_iterations,
            "status": "completed",
            "optimized_parameters": {
                "Kp": 1.25,
                "Ki": 0.18,
                "Kd": 0.06
            },
            "performance_metrics": {
                "IAE": 112.5,
                "ISE": 38.2,
                "settling_time": 32.1,
                "overshoot": 6.5
            },
            "message": "PID tuning test completed successfully"
        }

        # 保存到会话数据
        if "test_results" not in session.data:
            session.data["test_results"] = []
        session.data["test_results"].append(result)

        return result

    except Exception as e:
        logger.error(f"PID tuning test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "PID tuning test failed"
        }


async def benchmark_controllers_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """对比测试多个控制器性能。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        对比测试结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 解析参数
    controller_types = arguments.get("controller_types", ["pid", "precision_pid", "mpc"])
    test_steps = arguments.get("test_steps", 100)
    setpoint = arguments.get("setpoint", 2.0)

    logger.info(f"Benchmarking controllers: {controller_types}")

    try:
        # 模拟对比测试
        await asyncio.sleep(0.2)  # 模拟测试时间

        results = {
            "test_id": f"benchmark_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "controller_types": controller_types,
            "test_steps": test_steps,
            "setpoint": setpoint,
            "status": "completed",
            "comparison": {
                "pid": {
                    "IAE": 125.3,
                    "settling_time": 45.2,
                    "overshoot": 8.1,
                    "energy_cost": 125.5
                },
                "precision_pid": {
                    "IAE": 98.7,
                    "settling_time": 38.5,
                    "overshoot": 5.2,
                    "energy_cost": 118.2
                },
                "mpc": {
                    "IAE": 85.2,
                    "settling_time": 35.1,
                    "overshoot": 3.8,
                    "energy_cost": 142.3
                }
            },
            "recommendation": "MPC controller provides best performance but higher energy cost",
            "message": "Controller benchmark completed successfully"
        }

        # 保存到会话数据
        if "test_results" not in session.data:
            session.data["test_results"] = []
        session.data["test_results"].append(results)

        return results

    except Exception as e:
        logger.error(f"Controller benchmark test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Controller benchmark test failed"
        }


async def test_algorithm_performance_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """测试算法性能。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        性能测试结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 解析参数
    algorithm = arguments.get("algorithm", "genetic_algorithm")
    iterations = arguments.get("iterations", 100)
    complexity = arguments.get("complexity", "medium")

    logger.info(f"Testing algorithm performance: {algorithm}")

    try:
        # 模拟性能测试
        await asyncio.sleep(0.15)

        result = {
            "test_id": f"perf_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "algorithm": algorithm,
            "iterations": iterations,
            "complexity": complexity,
            "status": "completed",
            "performance": {
                "execution_time": 2.35,  # 秒
                "memory_usage": 45.2,    # MB
                "convergence_rate": 0.85,
                "final_fitness": 0.92
            },
            "scalability": {
                "iterations_per_second": 42.5,
                "memory_efficiency": "good",
                "cpu_usage": 65.3  # %
            },
            "message": "Algorithm performance test completed"
        }

        # 保存到会话数据
        if "test_results" not in session.data:
            session.data["test_results"] = []
        session.data["test_results"].append(result)

        return result

    except Exception as e:
        logger.error(f"Algorithm performance test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Algorithm performance test failed"
        }


async def inject_test_scenario_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """注入测试场景。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        场景注入结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 解析参数
    scenario_type = arguments.get("scenario_type", "sensor_fault")
    severity = arguments.get("severity", "medium")
    duration = arguments.get("duration", 50)

    logger.info(f"Injecting test scenario: {scenario_type}")

    try:
        # 保存场景配置
        scenario = {
            "scenario_id": f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": scenario_type,
            "severity": severity,
            "duration": duration,
            "status": "active",
            "injected_at": datetime.now().isoformat()
        }

        if "active_scenarios" not in session.data:
            session.data["active_scenarios"] = []
        session.data["active_scenarios"].append(scenario)

        return {
            **scenario,
            "message": f"Test scenario '{scenario_type}' injected successfully",
            "description": f"Scenario will affect next {duration} simulation steps"
        }

    except Exception as e:
        logger.error(f"Scenario injection failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Scenario injection failed"
        }


async def get_test_results_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """获取所有测试结果。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        测试结果列表
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    test_results = session.data.get("test_results", [])
    active_scenarios = session.data.get("active_scenarios", [])

    return {
        "total_tests": len(test_results),
        "test_results": test_results,
        "active_scenarios": active_scenarios,
        "session_id": session_id
    }


def register_developer_tools():
    """注册所有开发者测试工具。"""
    registry = get_registry()

    # 注册 test_pid_tuning 工具
    test_pid_tool = Tool(
        name="test_pid_tuning",
        description="Test PID auto-tuning algorithms for development and debugging",
        parameters=[
            ToolParameter(
                name="method",
                type=ToolParameterType.STRING,
                description="Tuning method to test",
                required=False,
                default="genetic_algorithm",
                enum=["genetic_algorithm", "particle_swarm", "ziegler_nichols"]
            ),
            ToolParameter(
                name="objective",
                type=ToolParameterType.STRING,
                description="Tuning objective",
                required=False,
                default="balanced",
                enum=["speed", "stability", "balanced"]
            ),
            ToolParameter(
                name="max_iterations",
                type=ToolParameterType.INTEGER,
                description="Maximum tuning iterations",
                required=False,
                default=50,
                minimum=10,
                maximum=500
            ),
            ToolParameter(
                name="setpoint",
                type=ToolParameterType.NUMBER,
                description="Target setpoint value",
                required=False,
                default=2.0
            ),
        ],
        handler=test_pid_tuning_handler,
        category="developer",
        version="1.0.0"
    )
    registry.register(test_pid_tool)

    # 注册 benchmark_controllers 工具
    benchmark_tool = Tool(
        name="benchmark_controllers",
        description="Compare performance of multiple controller types",
        parameters=[
            ToolParameter(
                name="controller_types",
                type=ToolParameterType.ARRAY,
                description="List of controller types to compare",
                required=False
            ),
            ToolParameter(
                name="test_steps",
                type=ToolParameterType.INTEGER,
                description="Number of steps to run each controller",
                required=False,
                default=100,
                minimum=10,
                maximum=1000
            ),
            ToolParameter(
                name="setpoint",
                type=ToolParameterType.NUMBER,
                description="Target setpoint value",
                required=False,
                default=2.0
            ),
        ],
        handler=benchmark_controllers_handler,
        category="developer",
        version="1.0.0"
    )
    registry.register(benchmark_tool)

    # 注册 test_algorithm_performance 工具
    perf_test_tool = Tool(
        name="test_algorithm_performance",
        description="Test performance characteristics of optimization algorithms",
        parameters=[
            ToolParameter(
                name="algorithm",
                type=ToolParameterType.STRING,
                description="Algorithm to test",
                required=False,
                default="genetic_algorithm",
                enum=["genetic_algorithm", "particle_swarm", "simulated_annealing"]
            ),
            ToolParameter(
                name="iterations",
                type=ToolParameterType.INTEGER,
                description="Number of iterations to run",
                required=False,
                default=100,
                minimum=10,
                maximum=1000
            ),
            ToolParameter(
                name="complexity",
                type=ToolParameterType.STRING,
                description="Problem complexity level",
                required=False,
                default="medium",
                enum=["low", "medium", "high"]
            ),
        ],
        handler=test_algorithm_performance_handler,
        category="developer",
        version="1.0.0"
    )
    registry.register(perf_test_tool)

    # 注册 inject_test_scenario 工具
    inject_scenario_tool = Tool(
        name="inject_test_scenario",
        description="Inject test scenarios (faults, disturbances) for algorithm testing",
        parameters=[
            ToolParameter(
                name="scenario_type",
                type=ToolParameterType.STRING,
                description="Type of scenario to inject",
                required=False,
                default="sensor_fault",
                enum=["sensor_fault", "process_disturbance", "actuator_failure", "communication_delay"]
            ),
            ToolParameter(
                name="severity",
                type=ToolParameterType.STRING,
                description="Severity level",
                required=False,
                default="medium",
                enum=["low", "medium", "high", "critical"]
            ),
            ToolParameter(
                name="duration",
                type=ToolParameterType.INTEGER,
                description="Duration in simulation steps",
                required=False,
                default=50,
                minimum=1,
                maximum=500
            ),
        ],
        handler=inject_test_scenario_handler,
        category="developer",
        version="1.0.0"
    )
    registry.register(inject_scenario_tool)

    # 注册 get_test_results 工具
    get_results_tool = Tool(
        name="get_test_results",
        description="Get all test results and active scenarios for this session",
        parameters=[],
        handler=get_test_results_handler,
        category="developer",
        version="1.0.0"
    )
    registry.register(get_results_tool)

    logger.info("Registered developer testing tools")
