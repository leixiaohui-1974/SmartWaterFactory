#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API认证和速率限制中间件。"""

import time
import logging
from typing import Dict, Optional, Callable, Any
from collections import defaultdict
from datetime import datetime, timedelta
from aiohttp import web

from .api_keys import get_api_key_manager, APIKey

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器。

    使用滑动窗口算法实现速率限制。
    """

    def __init__(self):
        """初始化速率限制器。"""
        # key_id -> [(timestamp, count)]
        self._windows: Dict[str, list] = defaultdict(list)
        self._window_size = 60  # 1分钟窗口

    def check_rate_limit(self, key_id: str, rate_limit: int) -> tuple[bool, Dict[str, Any]]:
        """检查速率限制。

        Args:
            key_id: API密钥ID
            rate_limit: 每分钟允许的请求数

        Returns:
            (是否允许请求, 速率限制信息)
        """
        now = time.time()
        window_start = now - self._window_size

        # 清理过期记录
        self._windows[key_id] = [
            ts for ts in self._windows[key_id]
            if ts > window_start
        ]

        # 检查当前窗口内的请求数
        current_count = len(self._windows[key_id])

        allowed = current_count < rate_limit

        if allowed:
            self._windows[key_id].append(now)
            # 添加请求后重新计算剩余数
            remaining = rate_limit - len(self._windows[key_id])
        else:
            remaining = 0

        info = {
            "limit": rate_limit,
            "remaining": remaining,
            "reset": int(window_start + self._window_size),
            "current": current_count
        }

        return allowed, info

    def get_stats(self, key_id: str) -> Dict[str, Any]:
        """获取速率限制统计信息。

        Args:
            key_id: API密钥ID

        Returns:
            统计信息
        """
        now = time.time()
        window_start = now - self._window_size

        # 清理过期记录
        self._windows[key_id] = [
            ts for ts in self._windows[key_id]
            if ts > window_start
        ]

        return {
            "requests_in_window": len(self._windows[key_id]),
            "window_size_seconds": self._window_size
        }


class AuthMiddleware:
    """认证中间件。

    验证API密钥并实施速率限制。
    """

    # 不需要认证的路径
    PUBLIC_PATHS = {
        "/health",
        "/metrics",
        "/graphiql",
    }

    # 不需要认证的路径前缀
    PUBLIC_PREFIXES = []

    def __init__(self, enabled: bool = True):
        """初始化认证中间件。

        Args:
            enabled: 是否启用认证
        """
        self.enabled = enabled
        self.api_key_manager = get_api_key_manager()
        self.rate_limiter = RateLimiter()

    def _is_public_path(self, path: str) -> bool:
        """检查路径是否为公开路径。

        Args:
            path: 请求路径

        Returns:
            是否为公开路径
        """
        if path in self.PUBLIC_PATHS:
            return True

        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    def _extract_api_key(self, request: web.Request) -> Optional[str]:
        """从请求中提取API密钥。

        支持以下方式:
        1. Authorization header: Bearer <api_key>
        2. X-API-Key header: <api_key>
        3. Query parameter: api_key=<api_key>

        Args:
            request: HTTP请求

        Returns:
            API密钥或None
        """
        # 从Authorization header提取
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        # 从X-API-Key header提取
        api_key_header = request.headers.get("X-API-Key", "")
        if api_key_header:
            return api_key_header

        # 从query parameter提取
        api_key_param = request.query.get("api_key", "")
        if api_key_param:
            return api_key_param

        return None

    async def verify_request(self, request: web.Request) -> tuple[bool, Optional[APIKey], Optional[str]]:
        """验证请求。

        Args:
            request: HTTP请求

        Returns:
            (是否验证通过, APIKey对象, 错误信息)
        """
        # 检查是否为公开路径
        if self._is_public_path(request.path):
            return True, None, None

        # 如果认证未启用，允许所有请求
        if not self.enabled:
            return True, None, None

        # 提取API密钥
        api_key_str = self._extract_api_key(request)
        if not api_key_str:
            return False, None, "Missing API key"

        # 验证API密钥
        api_key = self.api_key_manager.verify_key(api_key_str)
        if not api_key:
            return False, None, "Invalid or expired API key"

        # 检查速率限制
        allowed, rate_info = self.rate_limiter.check_rate_limit(
            api_key.key_id,
            api_key.rate_limit
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for key {api_key.key_id} "
                f"(user: {api_key.user_id})"
            )
            return False, api_key, f"Rate limit exceeded. Limit: {rate_info['limit']}/min"

        # 在request中存储API密钥信息和速率限制信息
        request["api_key"] = api_key
        request["rate_limit_info"] = rate_info

        return True, api_key, None

    @web.middleware
    async def middleware(self, request: web.Request, handler: Callable) -> web.Response:
        """中间件处理函数。

        Args:
            request: HTTP请求
            handler: 请求处理器

        Returns:
            HTTP响应
        """
        # 验证请求
        is_valid, api_key, error_msg = await self.verify_request(request)

        if not is_valid:
            logger.warning(
                f"Authentication failed for {request.path}: {error_msg}"
            )
            return web.json_response(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32001,
                        "message": error_msg
                    },
                    "id": None
                },
                status=401
            )

        # 记录认证成功
        if api_key:
            logger.debug(
                f"Authenticated request from user {api_key.user_id} "
                f"(key: {api_key.key_id})"
            )

        # 调用处理器
        response = await handler(request)

        # 添加速率限制headers
        if api_key and "rate_limit_info" in request:
            info = request["rate_limit_info"]
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response


def create_auth_middleware(enabled: bool = True) -> AuthMiddleware:
    """创建认证中间件实例。

    Args:
        enabled: 是否启用认证

    Returns:
        AuthMiddleware实例
    """
    return AuthMiddleware(enabled=enabled)
