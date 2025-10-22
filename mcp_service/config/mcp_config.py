#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP服务配置模块。

管理MCP服务的配置参数，包括服务器设置、资源限制、安全配置等。
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class MCPServerConfig:
    """MCP服务器配置。"""
    # 服务器基础配置
    host: str = '127.0.0.1'
    port: int = 8000
    name: str = 'SmartWaterFactory MCP Service'
    version: str = '1.0.0'
    debug: bool = False

    # 协议配置
    protocol_version: str = '2024-11-05'
    enable_stdio: bool = True  # 支持标准输入输出模式
    enable_http: bool = True   # 支持HTTP模式
    enable_sse: bool = True    # 支持Server-Sent Events

    # 安全配置
    enable_authentication: bool = True
    api_key_required: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ['*'])
    max_request_size: int = 10 * 1024 * 1024  # 10MB

    @property
    def enable_auth(self) -> bool:
        """认证启用状态（enable_authentication的别名）。"""
        return self.enable_authentication

    # 性能配置
    max_concurrent_sessions: int = 100
    session_timeout_minutes: int = 30
    tool_execution_timeout_seconds: int = 300
    rate_limit_per_minute: int = 60

    # 资源限制
    max_simulation_steps: int = 10000
    max_simulation_duration_minutes: int = 60
    max_concurrent_simulations_per_user: int = 5

    # 日志配置
    log_level: str = 'INFO'
    log_file: str = 'logs/mcp_service.log'
    enable_request_logging: bool = True
    enable_tool_call_logging: bool = True

    # 存储配置
    data_dir: str = 'data/mcp'
    temp_dir: str = 'temp/mcp'
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300


@dataclass
class MCPCapabilities:
    """MCP服务能力声明。"""
    tools: Dict[str, Any] = field(default_factory=lambda: {
        "listChanged": True  # 支持工具列表变更通知
    })
    resources: Dict[str, Any] = field(default_factory=lambda: {
        "subscribe": True,   # 支持资源订阅
        "listChanged": True  # 支持资源列表变更通知
    })
    prompts: Dict[str, Any] = field(default_factory=lambda: {
        "listChanged": True  # 支持提示词模板列表变更通知
    })
    logging: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "tools": self.tools,
            "resources": self.resources,
            "prompts": self.prompts,
            "logging": self.logging
        }


@dataclass
class MCPServiceInfo:
    """MCP服务信息。"""
    name: str
    version: str
    description: str = "Smart Water Factory MCP Service - AI-powered water treatment process control"
    author: str = "Smart Water Factory Team"
    homepage: str = "https://github.com/smartwaterfactory/mcp-service"
    capabilities: MCPCapabilities = field(default_factory=MCPCapabilities)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities.to_dict()
        }


class MCPConfigManager:
    """MCP配置管理器。"""

    _instance = None
    _config: Optional[MCPServerConfig] = None

    def __new__(cls):
        """单例模式。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器。"""
        if self._config is None:
            self._config = self._load_config()

    def _load_config(self) -> MCPServerConfig:
        """从环境变量加载配置。"""
        config = MCPServerConfig()

        # 从环境变量覆盖配置
        config.host = os.getenv('MCP_HOST', config.host)
        config.port = int(os.getenv('MCP_PORT', config.port))
        config.debug = os.getenv('MCP_DEBUG', str(config.debug)).lower() == 'true'

        config.enable_authentication = os.getenv(
            'MCP_ENABLE_AUTH',
            str(config.enable_authentication)
        ).lower() == 'true'

        config.max_concurrent_sessions = int(os.getenv(
            'MCP_MAX_SESSIONS',
            config.max_concurrent_sessions
        ))

        config.session_timeout_minutes = int(os.getenv(
            'MCP_SESSION_TIMEOUT',
            config.session_timeout_minutes
        ))

        config.log_level = os.getenv('MCP_LOG_LEVEL', config.log_level)

        # 确保必要的目录存在
        Path(config.data_dir).mkdir(parents=True, exist_ok=True)
        Path(config.temp_dir).mkdir(parents=True, exist_ok=True)
        Path(os.path.dirname(config.log_file)).mkdir(parents=True, exist_ok=True)

        return config

    @property
    def config(self) -> MCPServerConfig:
        """获取当前配置。"""
        return self._config

    def update_config(self, **kwargs):
        """更新配置。"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def get_service_info(self) -> MCPServiceInfo:
        """获取服务信息。"""
        return MCPServiceInfo(
            name=self._config.name,
            version=self._config.version
        )


# 全局配置实例
config_manager = MCPConfigManager()


def get_config() -> MCPServerConfig:
    """获取MCP服务配置。"""
    return config_manager.config


def get_service_info() -> MCPServiceInfo:
    """获取MCP服务信息。"""
    return config_manager.get_service_info()
