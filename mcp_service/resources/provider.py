#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP资源提供者。

管理MCP资源的注册和访问。
"""

import logging
from typing import Dict, Any, Optional, Callable

from ..models.schemas import Resource, ResourceType

logger = logging.getLogger(__name__)


class ResourceProvider:
    """资源提供者。

    管理所有可用的MCP资源，提供资源的注册、查询、读取等功能。
    """

    def __init__(self):
        """初始化资源提供者。"""
        self._resources: Dict[str, Resource] = {}

    def register(self, resource: Resource) -> None:
        """注册资源。

        Args:
            resource: 要注册的资源对象

        Raises:
            ValueError: 如果资源URI已存在
        """
        if resource.uri in self._resources:
            raise ValueError(f"Resource '{resource.uri}' already registered")

        self._resources[resource.uri] = resource
        logger.info(f"Registered resource: {resource.uri}")

    def unregister(self, uri: str) -> bool:
        """注销资源。

        Args:
            uri: 资源URI

        Returns:
            是否成功注销
        """
        if uri not in self._resources:
            return False

        del self._resources[uri]
        logger.info(f"Unregistered resource: {uri}")
        return True

    def get_resource(self, uri: str) -> Optional[Resource]:
        """获取资源。

        Args:
            uri: 资源URI

        Returns:
            资源对象，如果不存在则返回None
        """
        return self._resources.get(uri)

    def list_resources(self, resource_type: Optional[ResourceType] = None) -> list:
        """列出所有资源。

        Args:
            resource_type: 可选的资源类型过滤

        Returns:
            资源列表
        """
        if resource_type:
            return [r for r in self._resources.values() if r.resource_type == resource_type]
        return list(self._resources.values())

    def get_resources_schema(self, resource_type: Optional[ResourceType] = None) -> list:
        """获取资源的Schema列表。

        Args:
            resource_type: 可选的资源类型过滤

        Returns:
            资源Schema列表
        """
        resources = self.list_resources(resource_type)
        return [r.get_schema() for r in resources]

    async def read_resource(self, uri: str, **kwargs) -> Any:
        """读取资源。

        Args:
            uri: 资源URI
            **kwargs: 额外参数

        Returns:
            资源内容
        """
        resource = self.get_resource(uri)
        if not resource:
            raise ValueError(f"Resource '{uri}' not found")

        # 调用资源提供函数
        try:
            import inspect
            if inspect.iscoroutinefunction(resource.provider):
                return await resource.provider(**kwargs)
            else:
                return resource.provider(**kwargs)
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            raise


# 全局资源提供者实例
_global_provider = ResourceProvider()


def get_resource_provider() -> ResourceProvider:
    """获取全局资源提供者。"""
    return _global_provider
