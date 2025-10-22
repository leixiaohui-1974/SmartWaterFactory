#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP控制工具集。

封装控制器相关功能，提供MCP工具接口。
"""

import logging
from typing import Dict, Any, Optional

from ..models.schemas import ToolParameter, ToolParameterType, Tool
from ..registry import get_registry
from ..session import get_session_manager

logger = logging.getLogger(__name__)


async def set_control_parameters_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """设置控制参数的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        设置结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    # 获取会话和仿真
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    simulation = session.simulations.get(simulation_id)
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")

    # 获取参数
    parameters = arguments.get("parameters", {})

    # 保存控制参数到会话数据
    if "control_parameters" not in session.data:
        session.data["control_parameters"] = {}

    session.data["control_parameters"][simulation_id] = parameters

    return {
        "simulation_id": simulation_id,
        "status": "success",
        "message": "Control parameters updated",
        "parameters": parameters
    }


async def get_control_status_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """获取控制状态的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        控制状态信息
    """
    if not session_id:
        raise ValueError("Session ID is required")

    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    # 获取会话和仿真
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    simulation = session.simulations.get(simulation_id)
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")

    # 获取控制参数
    control_params = session.data.get("control_parameters", {}).get(simulation_id, {})

    # 获取最新的仿真结果作为控制状态
    latest_result = None
    if simulation.results:
        latest_result = simulation.results[-1]

    return {
        "simulation_id": simulation_id,
        "control_parameters": control_params,
        "latest_state": latest_result,
        "status": simulation.status
    }


def register_control_tools():
    """注册所有控制工具。"""
    registry = get_registry()

    # 注册 set_control_parameters 工具
    set_params_tool = Tool(
        name="set_control_parameters",
        description="Set control parameters for a simulation",
        parameters=[
            ToolParameter(
                name="simulation_id",
                type=ToolParameterType.STRING,
                description="Simulation ID",
                required=True
            ),
            ToolParameter(
                name="parameters",
                type=ToolParameterType.OBJECT,
                description="Control parameters to set",
                required=True
            ),
        ],
        handler=set_control_parameters_handler,
        category="control",
        version="1.0.0"
    )
    registry.register(set_params_tool)

    # 注册 get_control_status 工具
    status_tool = Tool(
        name="get_control_status",
        description="Get current control status of a simulation",
        parameters=[
            ToolParameter(
                name="simulation_id",
                type=ToolParameterType.STRING,
                description="Simulation ID",
                required=True
            ),
        ],
        handler=get_control_status_handler,
        category="control",
        version="1.0.0"
    )
    registry.register(status_tool)

    logger.info("Registered control tools")
