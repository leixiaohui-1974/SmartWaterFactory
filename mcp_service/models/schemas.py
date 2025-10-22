#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP服务数据模型和Schema定义。

基于Model Context Protocol (MCP)规范，定义工具、资源和提示词的数据结构。
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime


class ToolParameterType(str, Enum):
    """工具参数类型枚举。"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class ResourceType(str, Enum):
    """资源类型枚举。"""
    CONFIG = "config"
    DATA = "data"
    MODEL = "model"
    LOG = "log"


@dataclass
class ToolParameter:
    """工具参数定义。"""
    name: str
    type: ToolParameterType
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（JSON Schema格式）。"""
        schema = {
            "type": self.type.value,
            "description": self.description
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class Tool:
    """MCP工具定义。"""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Any  # 实际的处理函数
    category: str = "general"
    version: str = "1.0.0"

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的JSON Schema。"""
        required_params = [p.name for p in self.parameters if p.required]
        properties = {p.name: p.to_dict() for p in self.parameters}

        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required_params
            }
        }


@dataclass
class Resource:
    """MCP资源定义。"""
    uri: str
    name: str
    description: str
    mime_type: str
    resource_type: ResourceType
    provider: Any  # 资源提供函数
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_schema(self) -> Dict[str, Any]:
        """获取资源的Schema。"""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
            "type": self.resource_type.value,
            "metadata": self.metadata
        }


@dataclass
class PromptTemplate:
    """MCP提示词模板。"""
    name: str
    description: str
    template: str
    arguments: List[ToolParameter] = field(default_factory=list)

    def get_schema(self) -> Dict[str, Any]:
        """获取提示词模板的Schema。"""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [
                {"name": arg.name, "description": arg.description, "required": arg.required}
                for arg in self.arguments
            ]
        }

    def render(self, **kwargs) -> str:
        """渲染提示词模板。"""
        return self.template.format(**kwargs)


@dataclass
class MCPRequest:
    """MCP请求数据结构。"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    """MCP响应数据结构。"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        response = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            response["id"] = self.id
        if self.result is not None:
            response["result"] = self.result
        if self.error is not None:
            response["error"] = self.error
        return response


@dataclass
class MCPError:
    """MCP错误定义。"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# 标准MCP错误码
class MCPErrorCode:
    """MCP标准错误码。"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # 自定义错误码
    TOOL_NOT_FOUND = -32001
    RESOURCE_NOT_FOUND = -32002
    SESSION_NOT_FOUND = -32003
    PERMISSION_DENIED = -32004
    RATE_LIMIT_EXCEEDED = -32005
    SIMULATION_ERROR = -32100
    CONTROLLER_ERROR = -32101
    OPTIMIZATION_ERROR = -32102


@dataclass
class SessionInfo:
    """会话信息。"""
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ToolCallResult:
    """工具调用结果。"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        result = {
            "success": self.success,
            "execution_time": self.execution_time
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class SimulationConfig:
    """仿真配置。"""
    steps: int
    turbidity_setpoint: float
    do_setpoint: float
    controller_type: str
    enable_faults: bool = False
    enable_disturbances: bool = False
    log_interval: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationConfig':
        """从字典创建。"""
        return cls(**data)


@dataclass
class ControllerConfig:
    """控制器配置。"""
    controller_type: str
    setpoints: Dict[str, float]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)


@dataclass
class OptimizationConfig:
    """优化配置。"""
    method: str
    objective: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 100
    tolerance: float = 1e-6

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)


@dataclass
class SuccessResponse:
    """成功响应。"""
    success: bool
    data: Any = None
    message: Optional[str] = None

    def __dict__(self) -> Dict[str, Any]:
        """转换为字典。"""
        result = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.message is not None:
            result["message"] = self.message
        return result


@dataclass
class ErrorResponse:
    """错误响应。"""
    success: bool
    error: str
    code: Optional[str] = None

    def __dict__(self) -> Dict[str, Any]:
        """转换为字典。"""
        result = {
            "success": self.success,
            "error": self.error
        }
        if self.code is not None:
            result["code"] = self.code
        return result
