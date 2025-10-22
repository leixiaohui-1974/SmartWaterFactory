#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP服务配置包。"""

from .mcp_config import (
    MCPServerConfig,
    MCPCapabilities,
    MCPServiceInfo,
    MCPConfigManager,
    get_config,
    get_service_info,
    config_manager,
)

__all__ = [
    'MCPServerConfig',
    'MCPCapabilities',
    'MCPServiceInfo',
    'MCPConfigManager',
    'get_config',
    'get_service_info',
    'config_manager',
]
