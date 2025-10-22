#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP优化工具集。

封装参数优化相关功能，提供MCP工具接口。
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from ..models.schemas import ToolParameter, ToolParameterType, Tool
from ..registry import get_registry
from ..session import get_session_manager

logger = logging.getLogger(__name__)


async def optimize_controller_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """优化控制器参数的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        优化结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 获取参数
    method = arguments.get("method", "genetic_algorithm")
    objective = arguments.get("objective", "balanced")
    max_iterations = arguments.get("max_iterations", 50)

    # 模拟优化过程（实际实现会调用真实的优化算法）
    await asyncio.sleep(0.1)

    # 返回优化结果
    optimization_result = {
        "method": method,
        "objective": objective,
        "iterations": max_iterations,
        "optimized_parameters": {
            "Kp": 1.2,
            "Ki": 0.15,
            "Kd": 0.05
        },
        "performance_metrics": {
            "IAE": 125.3,
            "ISE": 45.2,
            "settling_time": 35.4,
            "overshoot": 8.2
        },
        "status": "completed"
    }

    # 保存优化结果到会话
    if "optimization_results" not in session.data:
        session.data["optimization_results"] = []
    session.data["optimization_results"].append(optimization_result)

    return optimization_result


async def get_optimization_status_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """获取优化状态的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        优化状态信息
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    optimization_results = session.data.get("optimization_results", [])

    return {
        "total_optimizations": len(optimization_results),
        "recent_results": optimization_results[-5:] if optimization_results else []
    }


def register_optimization_tools():
    """注册所有优化工具。"""
    registry = get_registry()

    # 注册 optimize_controller 工具
    optimize_tool = Tool(
        name="optimize_controller",
        description="Optimize controller parameters using various algorithms",
        parameters=[
            ToolParameter(
                name="method",
                type=ToolParameterType.STRING,
                description="Optimization method",
                required=False,
                default="genetic_algorithm",
                enum=["genetic_algorithm", "particle_swarm", "ziegler_nichols"]
            ),
            ToolParameter(
                name="objective",
                type=ToolParameterType.STRING,
                description="Optimization objective",
                required=False,
                default="balanced",
                enum=["speed", "stability", "balanced"]
            ),
            ToolParameter(
                name="max_iterations",
                type=ToolParameterType.INTEGER,
                description="Maximum optimization iterations",
                required=False,
                default=50,
                minimum=10,
                maximum=500
            ),
        ],
        handler=optimize_controller_handler,
        category="optimization",
        version="1.0.0"
    )
    registry.register(optimize_tool)

    # 注册 get_optimization_status 工具
    status_tool = Tool(
        name="get_optimization_status",
        description="Get status and history of optimization tasks",
        parameters=[],
        handler=get_optimization_status_handler,
        category="optimization",
        version="1.0.0"
    )
    registry.register(status_tool)

    logger.info("Registered optimization tools")
