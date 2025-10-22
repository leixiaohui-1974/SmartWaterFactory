#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP工具注册和管理模块。

负责管理所有可用的MCP工具，包括注册、查询、调用等功能。
"""

import time
import logging
from typing import Dict, List, Any, Optional, Callable
from functools import wraps

from ..models.schemas import (
    Tool,
    ToolParameter,
    ToolCallResult,
    MCPError,
    MCPErrorCode
)

try:
    from ..monitoring import record_tool_call
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表。

    管理所有已注册的MCP工具，提供工具的注册、查询、调用等功能。
    支持工具分类、版本管理和权限控制。
    """

    def __init__(self):
        """初始化工具注册表。"""
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}
        self._tool_stats: Dict[str, Dict[str, Any]] = {}

    def register(self, tool: Tool, allow_override: bool = False) -> None:
        """注册工具。

        Args:
            tool: 要注册的工具对象
            allow_override: 是否允许覆盖已存在的工具

        Raises:
            ValueError: 如果工具名称已存在且不允许覆盖
        """
        if tool.name in self._tools:
            if not allow_override:
                logger.warning(f"Tool '{tool.name}' already registered, skipping")
                return
            else:
                logger.info(f"Overriding existing tool '{tool.name}'")

        self._tools[tool.name] = tool

        # 添加到分类索引
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)

        # 初始化统计信息
        self._tool_stats[tool.name] = {
            'call_count': 0,
            'success_count': 0,
            'error_count': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0
        }

        logger.info(f"Registered tool: {tool.name} (category: {tool.category})")

    def unregister(self, tool_name: str) -> bool:
        """注销工具。

        Args:
            tool_name: 工具名称

        Returns:
            是否成功注销
        """
        if tool_name not in self._tools:
            return False

        tool = self._tools[tool_name]

        # 从分类索引中移除
        if tool.category in self._categories:
            if tool_name in self._categories[tool.category]:
                self._categories[tool.category].remove(tool_name)
            if not self._categories[tool.category]:
                del self._categories[tool.category]

        # 删除工具和统计信息
        del self._tools[tool_name]
        if tool_name in self._tool_stats:
            del self._tool_stats[tool_name]

        logger.info(f"Unregistered tool: {tool_name}")
        return True

    def clear(self) -> None:
        """清空所有已注册的工具。

        主要用于测试环境。
        """
        self._tools.clear()
        self._categories.clear()
        self._tool_stats.clear()
        logger.info("Cleared all registered tools")

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具。

        Args:
            tool_name: 工具名称

        Returns:
            工具对象，如果不存在则返回None
        """
        return self._tools.get(tool_name)

    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """列出所有工具。

        Args:
            category: 可选的分类过滤

        Returns:
            工具列表
        """
        if category:
            tool_names = self._categories.get(category, [])
            return [self._tools[name] for name in tool_names]
        return list(self._tools.values())

    def get_tools_schema(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取工具的Schema列表。

        Args:
            category: 可选的分类过滤

        Returns:
            工具Schema列表
        """
        tools = self.list_tools(category)
        return [tool.get_schema() for tool in tools]

    def list_categories(self) -> List[str]:
        """列出所有工具分类。

        Returns:
            分类列表
        """
        return list(self._categories.keys())

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> ToolCallResult:
        """调用工具。

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            session_id: 可选的会话ID

        Returns:
            工具调用结果
        """
        start_time = time.time()

        # 更新调用统计
        if tool_name in self._tool_stats:
            self._tool_stats[tool_name]['call_count'] += 1

        # 检查工具是否存在
        tool = self.get_tool(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)
            if tool_name in self._tool_stats:
                self._tool_stats[tool_name]['error_count'] += 1
            return ToolCallResult(
                success=False,
                error=error_msg,
                execution_time=time.time() - start_time
            )

        # 验证参数
        validation_error = self._validate_arguments(tool, arguments)
        if validation_error:
            logger.error(f"Parameter validation failed for {tool_name}: {validation_error}")
            if tool_name in self._tool_stats:
                self._tool_stats[tool_name]['error_count'] += 1
            return ToolCallResult(
                success=False,
                error=validation_error,
                execution_time=time.time() - start_time
            )

        # 调用工具处理函数
        try:
            logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")

            # 如果处理器是异步函数
            import inspect
            if inspect.iscoroutinefunction(tool.handler):
                result_data = await tool.handler(arguments, session_id=session_id)
            else:
                result_data = tool.handler(arguments, session_id=session_id)

            execution_time = time.time() - start_time

            # 更新统计信息
            self._tool_stats[tool_name]['success_count'] += 1
            self._tool_stats[tool_name]['total_execution_time'] += execution_time
            self._tool_stats[tool_name]['avg_execution_time'] = (
                self._tool_stats[tool_name]['total_execution_time'] /
                self._tool_stats[tool_name]['success_count']
            )

            # 记录监控指标
            if MONITORING_AVAILABLE:
                record_tool_call(tool_name, True, execution_time)

            logger.info(f"Tool {tool_name} executed successfully in {execution_time:.3f}s")

            return ToolCallResult(
                success=True,
                data=result_data,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Tool execution error: {str(e)}"
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)

            # 更新错误统计
            self._tool_stats[tool_name]['error_count'] += 1

            # 记录监控指标
            if MONITORING_AVAILABLE:
                record_tool_call(tool_name, False, execution_time)

            return ToolCallResult(
                success=False,
                error=error_msg,
                execution_time=execution_time
            )

    def _validate_arguments(self, tool: Tool, arguments: Dict[str, Any]) -> Optional[str]:
        """验证工具参数。

        Args:
            tool: 工具对象
            arguments: 参数字典

        Returns:
            错误信息，如果验证通过则返回None
        """
        # 检查必需参数
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                return f"Missing required parameter: {param.name}"

        # 检查参数类型和范围
        for param in tool.parameters:
            if param.name in arguments:
                value = arguments[param.name]

                # 类型检查（简化版）
                if param.type.value == "number" and not isinstance(value, (int, float)):
                    return f"Parameter '{param.name}' must be a number"
                elif param.type.value == "integer" and not isinstance(value, int):
                    return f"Parameter '{param.name}' must be an integer"
                elif param.type.value == "string" and not isinstance(value, str):
                    return f"Parameter '{param.name}' must be a string"
                elif param.type.value == "boolean" and not isinstance(value, bool):
                    return f"Parameter '{param.name}' must be a boolean"

                # 范围检查
                if isinstance(value, (int, float)):
                    if param.minimum is not None and value < param.minimum:
                        return f"Parameter '{param.name}' must be >= {param.minimum}"
                    if param.maximum is not None and value > param.maximum:
                        return f"Parameter '{param.name}' must be <= {param.maximum}"

                # 枚举检查
                if param.enum and value not in param.enum:
                    return f"Parameter '{param.name}' must be one of {param.enum}"

        return None

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计信息。

        Args:
            tool_name: 可选的工具名称，如果不指定则返回所有工具的统计

        Returns:
            统计信息字典
        """
        if tool_name:
            return self._tool_stats.get(tool_name, {})
        return self._tool_stats.copy()


# 全局工具注册表实例
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局工具注册表。"""
    return _global_registry


def register_tool(
    name: str,
    description: str,
    parameters: List[ToolParameter],
    category: str = "general",
    version: str = "1.0.0"
):
    """工具注册装饰器。

    使用示例:
        @register_tool(
            name="my_tool",
            description="My tool description",
            parameters=[
                ToolParameter(name="param1", type=ToolParameterType.STRING, required=True)
            ]
        )
        def my_tool_handler(arguments, session_id=None):
            return {"result": "success"}
    """
    def decorator(handler: Callable):
        @wraps(handler)
        def wrapper(*args, **kwargs):
            return handler(*args, **kwargs)

        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            category=category,
            version=version
        )
        _global_registry.register(tool)
        return wrapper

    return decorator
