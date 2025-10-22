#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API密钥管理路由。

提供API密钥的CRUD操作接口。
"""

import logging
from typing import Dict, Any, Optional
from aiohttp import web

from ..auth.api_keys import get_api_key_manager, APIKey
from ..models.schemas import SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)


class KeyManagementRoutes:
    """API密钥管理路由。"""

    def __init__(self):
        """初始化路由。"""
        self.api_key_manager = get_api_key_manager()

    async def create_key(self, request: web.Request) -> web.Response:
        """创建新的API密钥。

        POST /api/keys
        Body: {
            "user_id": "user123",
            "name": "My API Key",
            "expires_in_days": 30,  // 可选
            "permissions": ["read", "write"],  // 可选
            "rate_limit": 60,  // 可选，默认60
            "metadata": {}  // 可选
        }

        Returns:
            {
                "success": true,
                "data": {
                    "key": "swf_xxxxx",  // 原始密钥，仅显示一次
                    "key_id": "key_xxxxx",
                    "user_id": "user123",
                    "name": "My API Key",
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": "2024-01-31T00:00:00",
                    "rate_limit": 60,
                    "permissions": ["read", "write"]
                }
            }
        """
        try:
            data = await request.json()

            # 验证必需参数
            if "user_id" not in data or "name" not in data:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error="Missing required fields: user_id, name"
                    ).__dict__,
                    status=400
                )

            # 提取参数
            user_id = data["user_id"]
            name = data["name"]
            expires_in_days = data.get("expires_in_days")
            permissions = data.get("permissions")
            rate_limit = data.get("rate_limit", 60)
            metadata = data.get("metadata")

            # 创建密钥
            raw_key, api_key = self.api_key_manager.create_key(
                user_id=user_id,
                name=name,
                expires_in_days=expires_in_days,
                permissions=permissions,
                rate_limit=rate_limit,
                metadata=metadata
            )

            # 返回结果（包含原始密钥）
            result = api_key.to_dict()
            result["key"] = raw_key  # 原始密钥仅在创建时返回一次

            return web.json_response(
                SuccessResponse(
                    success=True,
                    data=result
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )

    async def list_keys(self, request: web.Request) -> web.Response:
        """列出API密钥。

        GET /api/keys?user_id=user123&include_inactive=false

        Returns:
            {
                "success": true,
                "data": {
                    "keys": [
                        {
                            "key_id": "key_xxxxx",
                            "user_id": "user123",
                            "name": "My API Key",
                            "created_at": "2024-01-01T00:00:00",
                            ...
                        }
                    ],
                    "total": 1
                }
            }
        """
        try:
            # 获取查询参数
            user_id = request.query.get("user_id")
            include_inactive = request.query.get("include_inactive", "false").lower() == "true"

            if not user_id:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error="Missing required parameter: user_id"
                    ).__dict__,
                    status=400
                )

            # 获取密钥列表
            keys = self.api_key_manager.list_user_keys(
                user_id=user_id,
                include_inactive=include_inactive
            )

            # 转换为字典列表
            keys_data = [key.to_dict() for key in keys]

            return web.json_response(
                SuccessResponse(
                    success=True,
                    data={
                        "keys": keys_data,
                        "total": len(keys_data)
                    }
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )

    async def get_key(self, request: web.Request) -> web.Response:
        """获取API密钥详情。

        GET /api/keys/{key_id}

        Returns:
            {
                "success": true,
                "data": {
                    "key_id": "key_xxxxx",
                    ...
                }
            }
        """
        try:
            key_id = request.match_info.get("key_id")

            if not key_id:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error="Missing key_id"
                    ).__dict__,
                    status=400
                )

            # 获取密钥
            api_key = self.api_key_manager.get_key(key_id)

            if not api_key:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error=f"API key not found: {key_id}"
                    ).__dict__,
                    status=404
                )

            return web.json_response(
                SuccessResponse(
                    success=True,
                    data=api_key.to_dict()
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )

    async def revoke_key(self, request: web.Request) -> web.Response:
        """撤销API密钥。

        POST /api/keys/{key_id}/revoke

        Returns:
            {
                "success": true,
                "message": "API key revoked successfully"
            }
        """
        try:
            key_id = request.match_info.get("key_id")

            if not key_id:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error="Missing key_id"
                    ).__dict__,
                    status=400
                )

            # 撤销密钥
            success = self.api_key_manager.revoke_key(key_id)

            if not success:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error=f"API key not found: {key_id}"
                    ).__dict__,
                    status=404
                )

            return web.json_response(
                SuccessResponse(
                    success=True,
                    message="API key revoked successfully"
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )

    async def delete_key(self, request: web.Request) -> web.Response:
        """删除API密钥。

        DELETE /api/keys/{key_id}

        Returns:
            {
                "success": true,
                "message": "API key deleted successfully"
            }
        """
        try:
            key_id = request.match_info.get("key_id")

            if not key_id:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error="Missing key_id"
                    ).__dict__,
                    status=400
                )

            # 删除密钥
            success = self.api_key_manager.delete_key(key_id)

            if not success:
                return web.json_response(
                    ErrorResponse(
                        success=False,
                        error=f"API key not found: {key_id}"
                    ).__dict__,
                    status=404
                )

            return web.json_response(
                SuccessResponse(
                    success=True,
                    message="API key deleted successfully"
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )

    async def get_stats(self, request: web.Request) -> web.Response:
        """获取API密钥统计信息。

        GET /api/keys/stats

        Returns:
            {
                "success": true,
                "data": {
                    "total_keys": 10,
                    "active_keys": 8,
                    "expired_keys": 2,
                    "total_users": 5
                }
            }
        """
        try:
            stats = self.api_key_manager.get_stats()

            return web.json_response(
                SuccessResponse(
                    success=True,
                    data=stats
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )

    async def cleanup_expired(self, request: web.Request) -> web.Response:
        """清理过期的API密钥。

        POST /api/keys/cleanup

        Returns:
            {
                "success": true,
                "data": {
                    "cleaned": 3
                }
            }
        """
        try:
            cleaned = self.api_key_manager.cleanup_expired()

            return web.json_response(
                SuccessResponse(
                    success=True,
                    data={"cleaned": cleaned}
                ).__dict__
            )

        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}")
            return web.json_response(
                ErrorResponse(
                    success=False,
                    error=str(e)
                ).__dict__,
                status=500
            )


def setup_key_routes(app: web.Application) -> None:
    """设置API密钥管理路由。

    Args:
        app: aiohttp应用
    """
    routes = KeyManagementRoutes()

    app.router.add_post("/api/keys", routes.create_key)
    app.router.add_get("/api/keys", routes.list_keys)
    app.router.add_get("/api/keys/stats", routes.get_stats)
    app.router.add_get("/api/keys/{key_id}", routes.get_key)
    app.router.add_post("/api/keys/{key_id}/revoke", routes.revoke_key)
    app.router.add_delete("/api/keys/{key_id}", routes.delete_key)
    app.router.add_post("/api/keys/cleanup", routes.cleanup_expired)

    logger.info("API key management routes configured")
