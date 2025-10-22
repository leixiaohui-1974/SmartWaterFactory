#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认证和API密钥管理系统测试。"""

import unittest
import asyncio
import json
from datetime import datetime, timedelta
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from mcp_service.auth import (
    APIKey,
    APIKeyManager,
    get_api_key_manager,
    AuthMiddleware,
    RateLimiter,
)
from mcp_service.api import setup_key_routes


class TestAPIKey(unittest.TestCase):
    """测试APIKey数据类。"""

    def setUp(self):
        """设置测试环境。"""
        self.api_key = APIKey(
            key_id="test_key_001",
            key_hash="hash123",
            user_id="user001",
            name="Test Key",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            is_active=True,
            permissions=["read", "write"],
            rate_limit=60
        )

    def test_is_valid(self):
        """测试密钥有效性检查。"""
        self.assertTrue(self.api_key.is_valid())

    def test_is_expired(self):
        """测试密钥过期检查。"""
        self.assertFalse(self.api_key.is_expired())

        # 测试已过期的密钥
        expired_key = APIKey(
            key_id="expired_key",
            key_hash="hash456",
            user_id="user001",
            name="Expired Key",
            created_at=datetime.now() - timedelta(days=60),
            expires_at=datetime.now() - timedelta(days=1),
        )
        self.assertTrue(expired_key.is_expired())
        self.assertFalse(expired_key.is_valid())

    def test_is_inactive(self):
        """测试未激活的密钥。"""
        inactive_key = APIKey(
            key_id="inactive_key",
            key_hash="hash789",
            user_id="user001",
            name="Inactive Key",
            created_at=datetime.now(),
            is_active=False
        )
        self.assertFalse(inactive_key.is_valid())

    def test_to_dict(self):
        """测试转换为字典。"""
        data = self.api_key.to_dict()

        self.assertEqual(data["key_id"], "test_key_001")
        self.assertEqual(data["user_id"], "user001")
        self.assertEqual(data["name"], "Test Key")
        self.assertEqual(data["is_active"], True)
        self.assertNotIn("key_hash", data)

        # 测试包含哈希值
        data_with_hash = self.api_key.to_dict(include_hash=True)
        self.assertIn("key_hash", data_with_hash)
        self.assertEqual(data_with_hash["key_hash"], "hash123")


class TestAPIKeyManager(unittest.TestCase):
    """测试API密钥管理器。"""

    def setUp(self):
        """设置测试环境。"""
        self.manager = APIKeyManager()

    def test_generate_key(self):
        """测试密钥生成。"""
        key = APIKeyManager.generate_key()

        self.assertTrue(key.startswith("swf_"))
        self.assertEqual(len(key), 36)  # swf_ + 32字符

    def test_hash_key(self):
        """测试密钥哈希。"""
        key = "swf_test123456789012345678901234"
        hash1 = APIKeyManager.hash_key(key)
        hash2 = APIKeyManager.hash_key(key)

        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256

    def test_create_key(self):
        """测试创建密钥。"""
        raw_key, api_key = self.manager.create_key(
            user_id="user001",
            name="Test Key",
            expires_in_days=30,
            permissions=["read", "write"],
            rate_limit=100
        )

        self.assertTrue(raw_key.startswith("swf_"))
        self.assertEqual(api_key.user_id, "user001")
        self.assertEqual(api_key.name, "Test Key")
        self.assertEqual(api_key.permissions, ["read", "write"])
        self.assertEqual(api_key.rate_limit, 100)
        self.assertIsNotNone(api_key.expires_at)

    def test_verify_key(self):
        """测试密钥验证。"""
        raw_key, api_key = self.manager.create_key(
            user_id="user001",
            name="Test Key"
        )

        # 验证有效密钥
        verified_key = self.manager.verify_key(raw_key)
        self.assertIsNotNone(verified_key)
        self.assertEqual(verified_key.key_id, api_key.key_id)

        # 验证无效密钥
        invalid_key = self.manager.verify_key("swf_invalid_key_12345678901234")
        self.assertIsNone(invalid_key)

    def test_revoke_key(self):
        """测试撤销密钥。"""
        raw_key, api_key = self.manager.create_key(
            user_id="user001",
            name="Test Key"
        )

        # 撤销密钥
        success = self.manager.revoke_key(api_key.key_id)
        self.assertTrue(success)

        # 验证已撤销的密钥
        verified_key = self.manager.verify_key(raw_key)
        self.assertIsNone(verified_key)

    def test_delete_key(self):
        """测试删除密钥。"""
        raw_key, api_key = self.manager.create_key(
            user_id="user001",
            name="Test Key"
        )

        # 删除密钥
        success = self.manager.delete_key(api_key.key_id)
        self.assertTrue(success)

        # 验证已删除的密钥
        retrieved_key = self.manager.get_key(api_key.key_id)
        self.assertIsNone(retrieved_key)

    def test_list_user_keys(self):
        """测试列出用户密钥。"""
        # 创建多个密钥
        for i in range(3):
            self.manager.create_key(
                user_id="user001",
                name=f"Test Key {i}"
            )

        # 列出密钥
        keys = self.manager.list_user_keys("user001")
        self.assertEqual(len(keys), 3)

        # 撤销一个密钥
        self.manager.revoke_key(keys[0].key_id)

        # 列出活跃密钥
        active_keys = self.manager.list_user_keys("user001", include_inactive=False)
        self.assertEqual(len(active_keys), 2)

        # 列出所有密钥
        all_keys = self.manager.list_user_keys("user001", include_inactive=True)
        self.assertEqual(len(all_keys), 3)

    def test_cleanup_expired(self):
        """测试清理过期密钥。"""
        # 创建过期密钥
        for i in range(3):
            raw_key = self.manager.generate_key()
            key_hash = self.manager.hash_key(raw_key)
            key_id = f"key_{i}"

            api_key = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                user_id="user001",
                name=f"Expired Key {i}",
                created_at=datetime.now() - timedelta(days=60),
                expires_at=datetime.now() - timedelta(days=1)
            )

            self.manager._keys[key_id] = api_key
            self.manager._hash_to_id[key_hash] = key_id
            if "user001" not in self.manager._user_keys:
                self.manager._user_keys["user001"] = []
            self.manager._user_keys["user001"].append(key_id)

        # 清理过期密钥
        cleaned = self.manager.cleanup_expired()
        self.assertEqual(cleaned, 3)

    def test_get_stats(self):
        """测试获取统计信息。"""
        # 创建密钥
        self.manager.create_key(user_id="user001", name="Key 1")
        self.manager.create_key(user_id="user002", name="Key 2")
        raw_key, api_key = self.manager.create_key(user_id="user001", name="Key 3")

        # 撤销一个密钥
        self.manager.revoke_key(api_key.key_id)

        # 获取统计信息
        stats = self.manager.get_stats()

        self.assertEqual(stats["total_keys"], 3)
        self.assertEqual(stats["active_keys"], 2)
        self.assertEqual(stats["total_users"], 2)


class TestRateLimiter(unittest.TestCase):
    """测试速率限制器。"""

    def setUp(self):
        """设置测试环境。"""
        self.limiter = RateLimiter()

    def test_rate_limit(self):
        """测试速率限制。"""
        key_id = "test_key"
        rate_limit = 5

        # 发送5个请求（应该都通过）
        for i in range(5):
            allowed, info = self.limiter.check_rate_limit(key_id, rate_limit)
            self.assertTrue(allowed)
            self.assertEqual(info["remaining"], 5 - i - 1)

        # 第6个请求应该被拒绝
        allowed, info = self.limiter.check_rate_limit(key_id, rate_limit)
        self.assertFalse(allowed)
        self.assertEqual(info["remaining"], 0)

    def test_get_stats(self):
        """测试获取统计信息。"""
        key_id = "test_key"
        rate_limit = 10

        # 发送3个请求
        for i in range(3):
            self.limiter.check_rate_limit(key_id, rate_limit)

        # 获取统计信息
        stats = self.limiter.get_stats(key_id)
        self.assertEqual(stats["requests_in_window"], 3)
        self.assertEqual(stats["window_size_seconds"], 60)


class TestAuthMiddleware(AioHTTPTestCase):
    """测试认证中间件。"""

    async def get_application(self):
        """创建测试应用。"""
        from mcp_service.auth import create_auth_middleware

        # 创建认证中间件
        auth_middleware = create_auth_middleware(enabled=True)

        app = web.Application(middlewares=[auth_middleware.middleware])

        # 添加测试路由
        async def protected_handler(request):
            api_key = request.get("api_key")
            return web.json_response({
                "success": True,
                "user_id": api_key.user_id if api_key else None
            })

        async def public_handler(request):
            return web.json_response({"success": True})

        app.router.add_get("/protected", protected_handler)
        app.router.add_get("/health", public_handler)

        return app

    @unittest_run_loop
    async def test_public_endpoint(self):
        """测试公开端点。"""
        resp = await self.client.get("/health")
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertTrue(data["success"])

    @unittest_run_loop
    async def test_missing_api_key(self):
        """测试缺少API密钥。"""
        resp = await self.client.get("/protected")
        self.assertEqual(resp.status, 401)

        data = await resp.json()
        # 中间件返回JSON-RPC错误格式
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -32001)

    @unittest_run_loop
    async def test_valid_api_key(self):
        """测试有效的API密钥。"""
        # 创建API密钥
        manager = get_api_key_manager()
        raw_key, api_key = manager.create_key(
            user_id="test_user",
            name="Test Key"
        )

        # 使用API密钥访问
        resp = await self.client.get(
            "/protected",
            headers={"Authorization": f"Bearer {raw_key}"}
        )
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user_id"], "test_user")

    @unittest_run_loop
    async def test_rate_limit_headers(self):
        """测试速率限制响应头。"""
        # 创建API密钥
        manager = get_api_key_manager()
        raw_key, api_key = manager.create_key(
            user_id="test_user",
            name="Test Key",
            rate_limit=10
        )

        # 发送请求
        resp = await self.client.get(
            "/protected",
            headers={"Authorization": f"Bearer {raw_key}"}
        )

        # 检查响应头
        self.assertIn("X-RateLimit-Limit", resp.headers)
        self.assertIn("X-RateLimit-Remaining", resp.headers)
        self.assertIn("X-RateLimit-Reset", resp.headers)

        self.assertEqual(resp.headers["X-RateLimit-Limit"], "10")


def run_async_test():
    """运行异步测试。"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuthMiddleware)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    # 运行同步测试
    unittest.main(verbosity=2, exit=False)

    # 运行异步测试
    print("\n" + "=" * 70)
    print("Running async tests...")
    print("=" * 70)
    run_async_test()
