#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP协议处理器。

实现Model Context Protocol (MCP)的核心协议处理逻辑。
支持JSON-RPC 2.0格式的请求和响应。
"""

import json
import logging
from typing import Dict, Any, Optional

from ..models.schemas import (
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPErrorCode
)
from ..registry import get_registry
from ..session import get_session_manager
from ..config import get_service_info

logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """MCP协议处理器。

    处理MCP协议的各种方法调用，包括：
    - initialize: 初始化连接
    - tools/list: 列出可用工具
    - tools/call: 调用工具
    - resources/list: 列出可用资源
    - resources/read: 读取资源
    - prompts/list: 列出提示词模板
    """

    def __init__(self):
        """初始化协议处理器。"""
        self.tool_registry = get_registry()
        self.session_manager = get_session_manager()
        self.service_info = get_service_info()

    async def handle_request(
        self,
        request_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> MCPResponse:
        """处理MCP请求。

        Args:
            request_data: 请求数据（JSON-RPC格式）
            session_id: 可选的会话ID

        Returns:
            MCP响应对象
        """
        try:
            # 解析请求
            request = self._parse_request(request_data)

            # 路由到对应的处理方法
            method = request.method
            params = request.params

            logger.info(f"Handling MCP method: {method}")

            if method == "initialize":
                result = await self._handle_initialize(params, session_id)
            elif method == "tools/list":
                result = await self._handle_tools_list(params, session_id)
            elif method == "tools/call":
                result = await self._handle_tools_call(params, session_id)
            elif method == "resources/list":
                result = await self._handle_resources_list(params, session_id)
            elif method == "resources/read":
                result = await self._handle_resources_read(params, session_id)
            elif method == "prompts/list":
                result = await self._handle_prompts_list(params, session_id)
            elif method == "prompts/get":
                result = await self._handle_prompts_get(params, session_id)
            elif method == "session/info":
                result = await self._handle_session_info(params, session_id)
            elif method == "session/stats":
                result = await self._handle_session_stats(params, session_id)
            else:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": MCPErrorCode.METHOD_NOT_FOUND,
                        "message": f"Method '{method}' not found"
                    }
                )

            return MCPResponse(id=request.id, result=result)

        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return MCPResponse(
                id=request_data.get("id"),
                error={
                    "code": MCPErrorCode.INTERNAL_ERROR,
                    "message": str(e)
                }
            )

    def _parse_request(self, data: Dict[str, Any]) -> MCPRequest:
        """解析MCP请求。"""
        if not isinstance(data, dict):
            raise ValueError("Request must be a JSON object")

        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")

        return MCPRequest(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method", ""),
            params=data.get("params", {})
        )

    async def _handle_initialize(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理初始化请求。"""
        protocol_version = params.get("protocolVersion", "2024-11-05")
        client_info = params.get("clientInfo", {})

        logger.info(f"Client connected: {client_info}")

        return {
            "protocolVersion": protocol_version,
            "serverInfo": self.service_info.to_dict(),
            "instructions": "Smart Water Factory MCP Service - Use tools to control and simulate water treatment processes"
        }

    async def _handle_tools_list(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理工具列表请求。"""
        category = params.get("category")
        tools_schema = self.tool_registry.get_tools_schema(category)

        return {
            "tools": tools_schema
        }

    async def _handle_tools_call(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理工具调用请求。"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Tool name is required")

        # 调用工具
        result = await self.tool_registry.call_tool(
            tool_name,
            arguments,
            session_id=session_id
        )

        # 转换为MCP响应格式
        if result.success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result.data, indent=2, ensure_ascii=False)
                    }
                ],
                "isError": False
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {result.error}"
                    }
                ],
                "isError": True
            }

    async def _handle_resources_list(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理资源列表请求。"""
        # 返回可用资源列表
        resources = [
            {
                "uri": "config://simulation",
                "name": "Simulation Configuration",
                "description": "Default simulation parameters and settings",
                "mimeType": "application/json"
            },
            {
                "uri": "config://controllers",
                "name": "Controller Configuration",
                "description": "PID controller gains and settings",
                "mimeType": "application/json"
            },
            {
                "uri": "data://session_info",
                "name": "Session Information",
                "description": "Current session data and statistics",
                "mimeType": "application/json"
            }
        ]

        return {
            "resources": resources
        }

    async def _handle_resources_read(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理资源读取请求。"""
        uri = params.get("uri")

        if not uri:
            raise ValueError("Resource URI is required")

        # 根据URI返回对应资源
        if uri == "config://simulation":
            from config.settings import SIMULATION_DEFAULTS
            content = json.dumps(SIMULATION_DEFAULTS, indent=2)
        elif uri == "config://controllers":
            from config.settings import PID_GAINS
            content = json.dumps(PID_GAINS, indent=2)
        elif uri == "data://session_info" and session_id:
            session = self.session_manager.get_session(session_id)
            if session:
                content = json.dumps(session.to_info().to_dict(), indent=2)
            else:
                raise ValueError(f"Session {session_id} not found")
        else:
            raise ValueError(f"Unknown resource URI: {uri}")

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": content
                }
            ]
        }

    async def _handle_prompts_list(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理提示词模板列表请求。"""
        prompts = [
            {
                "name": "run_simulation",
                "description": "Template for running a water plant simulation",
                "arguments": [
                    {"name": "duration", "description": "Simulation duration in steps", "required": False},
                    {"name": "scenario", "description": "Scenario type", "required": False}
                ]
            },
            {
                "name": "optimize_pid",
                "description": "Template for optimizing PID controller parameters",
                "arguments": [
                    {"name": "method", "description": "Optimization method", "required": False},
                    {"name": "objective", "description": "Optimization objective", "required": False}
                ]
            }
        ]

        return {
            "prompts": prompts
        }

    async def _handle_prompts_get(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理获取提示词模板请求。"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "run_simulation":
            duration = arguments.get("duration", "100")
            scenario = arguments.get("scenario", "normal")
            prompt = f"""Please run a water plant simulation with the following parameters:
- Duration: {duration} steps
- Scenario: {scenario}

Use the start_simulation tool to begin the simulation, then monitor its progress using get_simulation_status."""

        elif name == "optimize_pid":
            method = arguments.get("method", "genetic_algorithm")
            objective = arguments.get("objective", "balanced")
            prompt = f"""Please optimize the PID controller parameters using:
- Method: {method}
- Objective: {objective}

Use the optimize_controller tool to perform the optimization."""

        else:
            raise ValueError(f"Unknown prompt: {name}")

        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt
                    }
                }
            ]
        }

    async def _handle_session_info(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理会话信息请求。"""
        if not session_id:
            raise ValueError("Session ID is required")

        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        return session.to_info().to_dict()

    async def _handle_session_stats(
        self,
        params: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """处理会话统计请求。"""
        return self.session_manager.get_stats()
