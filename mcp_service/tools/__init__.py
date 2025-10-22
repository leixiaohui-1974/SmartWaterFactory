#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP工具包。"""

from .simulation_tools import register_simulation_tools
from .control_tools import register_control_tools
from .optimization_tools import register_optimization_tools


def register_all_tools():
    """注册所有MCP工具。"""
    register_simulation_tools()
    register_control_tools()
    register_optimization_tools()


__all__ = [
    'register_simulation_tools',
    'register_control_tools',
    'register_optimization_tools',
    'register_all_tools',
]
