#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP工具包。"""

from .simulation_tools import register_simulation_tools
from .control_tools import register_control_tools
from .optimization_tools import register_optimization_tools
from .developer_tools import register_developer_tools


def register_all_tools(include_developer_tools: bool = True):
    """注册所有MCP工具。

    Args:
        include_developer_tools: 是否包含开发者测试工具
    """
    register_simulation_tools()
    register_control_tools()
    register_optimization_tools()

    if include_developer_tools:
        register_developer_tools()


__all__ = [
    'register_simulation_tools',
    'register_control_tools',
    'register_optimization_tools',
    'register_developer_tools',
    'register_all_tools',
]
