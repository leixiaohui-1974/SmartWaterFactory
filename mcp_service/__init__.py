#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SmartWaterFactory MCP服务包。

Model Context Protocol (MCP)服务，为AI大模型提供水厂仿真和控制能力。

主要模块：
- config: 配置管理
- models: 数据模型
- protocol: MCP协议处理
- registry: 工具注册管理
- session: 会话和并发管理
- tools: 工具实现（仿真、控制、优化等）
- resources: 资源提供
- server: 服务器主入口

使用示例:
    # STDIO模式（用于Claude Desktop）
    python -m mcp_service.server --mode stdio

    # HTTP模式（用于Web应用）
    python -m mcp_service.server --mode http --host 0.0.0.0 --port 8000
"""

__version__ = "1.0.0"
__author__ = "Smart Water Factory Team"

from .server import MCPServer
from .config import get_config, get_service_info
from .registry import get_registry
from .session import get_session_manager

__all__ = [
    'MCPServer',
    'get_config',
    'get_service_info',
    'get_registry',
    'get_session_manager',
]
