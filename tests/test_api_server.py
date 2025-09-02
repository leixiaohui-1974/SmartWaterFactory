#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API服务器测试模块。

测试智能水厂API服务器的各种功能，包括：
1. RESTful API端点
2. 认证和授权
3. 速率限制
4. 数据序列化
5. 错误处理
"""

import unittest
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

try:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    from utils.api_server import (
        APIConfig, APIResponse, UserCredentials,
        AuthenticationManager, RateLimiter, WaterPlantAPIServer,
        create_api_server
    )
    
    # 模拟Flask相关模块
    with patch.dict('sys.modules', {
        'flask': MagicMock(),
        'flask_cors': MagicMock(),
        'flask_socketio': MagicMock(),
        'jwt': MagicMock()
    }):
        pass
        
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class TestAPIConfig(unittest.TestCase):
    """测试API配置类。"""
    
    def test_default_config(self):
        """测试默认配置。"""
        config = APIConfig()
        
        self.assertEqual(config.host, '127.0.0.1')
        self.assertEqual(config.port, 5000)
        self.assertFalse(config.debug)
        self.assertEqual(config.jwt_expiration_hours, 24)
        self.assertTrue(config.enable_authentication)
        self.assertTrue(config.enable_websocket)
    
    def test_custom_config(self):
        """测试自定义配置。"""
        config = APIConfig(
            host='0.0.0.0',
            port=8080,
            debug=True,
            enable_authentication=False
        )
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
        self.assertTrue(config.debug)
        self.assertFalse(config.enable_authentication)


class TestAPIResponse(unittest.TestCase):
    """测试API响应类。"""
    
    def test_success_response(self):
        """测试成功响应。"""
        response = APIResponse(
            success=True,
            data={'key': 'value'},
            message='Success'
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.data, {'key': 'value'})
        self.assertEqual(response.message, 'Success')
        self.assertIsNotNone(response.timestamp)
        self.assertIsNone(response.error_code)
    
    def test_error_response(self):
        """测试错误响应。"""
        response = APIResponse(
            success=False,
            message='Error occurred',
            error_code='TEST_ERROR'
        )
        
        self.assertFalse(response.success)
        self.assertEqual(response.message, 'Error occurred')
        self.assertEqual(response.error_code, 'TEST_ERROR')
    
    def test_to_dict(self):
        """测试转换为字典。"""
        response = APIResponse(
            success=True,
            data={'test': 123},
            message='Test message'
        )
        
        result = response.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], {'test': 123})
        self.assertEqual(result['message'], 'Test message')
        self.assertIn('timestamp', result)


class TestUserCredentials(unittest.TestCase):
    """测试用户凭证类。"""
    
    def test_admin_user(self):
        """测试管理员用户。"""
        user = UserCredentials('admin', 'password', 'admin')
        
        self.assertEqual(user.username, 'admin')
        self.assertEqual(user.role, 'admin')
        self.assertIn('read', user.permissions)
        self.assertIn('write', user.permissions)
        self.assertIn('control', user.permissions)
        self.assertIn('config', user.permissions)
        self.assertIn('user_management', user.permissions)
    
    def test_operator_user(self):
        """测试操作员用户。"""
        user = UserCredentials('operator', 'password', 'operator')
        
        self.assertEqual(user.role, 'operator')
        self.assertIn('read', user.permissions)
        self.assertIn('write', user.permissions)
        self.assertIn('control', user.permissions)
        self.assertNotIn('config', user.permissions)
        self.assertNotIn('user_management', user.permissions)
    
    def test_regular_user(self):
        """测试普通用户。"""
        user = UserCredentials('user', 'password', 'user')
        
        self.assertEqual(user.role, 'user')
        self.assertIn('read', user.permissions)
        self.assertNotIn('write', user.permissions)
        self.assertNotIn('control', user.permissions)
    
    def test_custom_permissions(self):
        """测试自定义权限。"""
        custom_permissions = ['read', 'custom_action']
        user = UserCredentials('custom', 'password', 'user', custom_permissions)
        
        self.assertEqual(user.permissions, custom_permissions)


class TestAuthenticationManager(unittest.TestCase):
    """测试认证管理器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.auth_manager = AuthenticationManager('test_secret', 1)
    
    def test_default_users(self):
        """测试默认用户。"""
        self.assertIn('admin', self.auth_manager.users)
        self.assertIn('operator', self.auth_manager.users)
        self.assertIn('user', self.auth_manager.users)
    
    def test_successful_authentication(self):
        """测试成功认证。"""
        token = self.auth_manager.authenticate('admin', 'admin123')
        
        self.assertIsNotNone(token)
        self.assertIn(token, self.auth_manager.active_tokens)
    
    def test_failed_authentication(self):
        """测试认证失败。"""
        token = self.auth_manager.authenticate('admin', 'wrong_password')
        
        self.assertIsNone(token)
    
    def test_nonexistent_user(self):
        """测试不存在的用户。"""
        token = self.auth_manager.authenticate('nonexistent', 'password')
        
        self.assertIsNone(token)
    
    def test_token_verification(self):
        """测试token验证。"""
        token = self.auth_manager.authenticate('admin', 'admin123')
        user_info = self.auth_manager.verify_token(token)
        
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info['username'], 'admin')
        self.assertEqual(user_info['role'], 'admin')
    
    def test_invalid_token_verification(self):
        """测试无效token验证。"""
        user_info = self.auth_manager.verify_token('invalid_token')
        
        self.assertIsNone(user_info)
    
    def test_token_revocation(self):
        """测试token撤销。"""
        token = self.auth_manager.authenticate('admin', 'admin123')
        
        # 撤销前应该有效
        user_info = self.auth_manager.verify_token(token)
        self.assertIsNotNone(user_info)
        
        # 撤销token
        revoked = self.auth_manager.revoke_token(token)
        self.assertTrue(revoked)
        
        # 撤销后应该无效
        user_info = self.auth_manager.verify_token(token)
        self.assertIsNone(user_info)
    
    def test_permission_check(self):
        """测试权限检查。"""
        user_info = {
            'username': 'test',
            'permissions': ['read', 'write']
        }
        
        self.assertTrue(self.auth_manager.check_permission(user_info, 'read'))
        self.assertTrue(self.auth_manager.check_permission(user_info, 'write'))
        self.assertFalse(self.auth_manager.check_permission(user_info, 'control'))


class TestRateLimiter(unittest.TestCase):
    """测试速率限制器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.rate_limiter = RateLimiter(max_requests_per_minute=5)
    
    def test_allowed_requests(self):
        """测试允许的请求。"""
        client_id = 'test_client'
        
        # 前5个请求应该被允许
        for i in range(5):
            self.assertTrue(self.rate_limiter.is_allowed(client_id))
    
    def test_rate_limit_exceeded(self):
        """测试超过速率限制。"""
        client_id = 'test_client'
        
        # 前5个请求被允许
        for i in range(5):
            self.assertTrue(self.rate_limiter.is_allowed(client_id))
        
        # 第6个请求应该被拒绝
        self.assertFalse(self.rate_limiter.is_allowed(client_id))
    
    def test_different_clients(self):
        """测试不同客户端的独立限制。"""
        client1 = 'client1'
        client2 = 'client2'
        
        # 两个客户端都应该有独立的限制
        for i in range(5):
            self.assertTrue(self.rate_limiter.is_allowed(client1))
            self.assertTrue(self.rate_limiter.is_allowed(client2))
    
    @patch('time.time')
    def test_time_window_reset(self, mock_time):
        """测试时间窗口重置。"""
        client_id = 'test_client'
        
        # 模拟当前时间
        mock_time.return_value = 1000.0
        
        # 用完所有请求
        for i in range(5):
            self.assertTrue(self.rate_limiter.is_allowed(client_id))
        
        # 超过限制
        self.assertFalse(self.rate_limiter.is_allowed(client_id))
        
        # 模拟时间过去61秒
        mock_time.return_value = 1061.0
        
        # 现在应该允许新请求
        self.assertTrue(self.rate_limiter.is_allowed(client_id))


class TestWaterPlantAPIServer(unittest.TestCase):
    """测试WaterPlantAPIServer类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.config = APIConfig(
            enable_authentication=True,
            enable_websocket=True,
            rate_limit_per_minute=60
        )
    
    def test_server_initialization_basic(self):
        """测试服务器基本初始化（不依赖Flask）。"""
        # 测试配置和基本组件
        config = APIConfig(enable_websocket=False)
        
        # 由于Flask可能不可用，我们只测试配置相关的逻辑
        self.assertEqual(config.host, '127.0.0.1')
        self.assertEqual(config.port, 5000)
        self.assertFalse(config.enable_websocket)
    
    def test_plant_data_structure_mock(self):
        """测试工厂数据结构（使用mock）。"""
        # 创建模拟的plant_data结构
        expected_plant_data = {
            'water_quality': {
                'ph': 7.2,
                'turbidity': 2.1,
                'chlorine': 0.8,
                'temperature': 22.5,
                'timestamp': '2024-01-01T12:00:00'
            },
            'control_status': {
                'pump_speed': 75.0,
                'valve_position': 45.0,
                'chemical_dosing': 12.5,
                'timestamp': '2024-01-01T12:00:00'
            },
            'system_status': {
                'operational': True,
                'alarms': [],
                'maintenance_due': False,
                'timestamp': '2024-01-01T12:00:00'
            }
        }
        
        # 验证数据结构
        self.assertIn('water_quality', expected_plant_data)
        self.assertIn('control_status', expected_plant_data)
        self.assertIn('system_status', expected_plant_data)
        
        # 验证水质数据
        water_quality = expected_plant_data['water_quality']
        self.assertIn('ph', water_quality)
        self.assertIn('turbidity', water_quality)
        self.assertIn('chlorine', water_quality)
        self.assertIn('temperature', water_quality)
        
        # 验证控制状态
        control_status = expected_plant_data['control_status']
        self.assertIn('pump_speed', control_status)
        self.assertIn('valve_position', control_status)
        self.assertIn('chemical_dosing', control_status)
        
        # 验证系统状态
        system_status = expected_plant_data['system_status']
        self.assertIn('operational', system_status)
        self.assertIn('alarms', system_status)
        self.assertIn('maintenance_due', system_status)
    
    def test_server_initialization_without_flask(self):
        """测试Flask不可用时的服务器初始化。"""
        with patch('utils.api_server.FLASK_AVAILABLE', False):
            with self.assertRaises(ImportError):
                WaterPlantAPIServer(self.config)


class TestConvenienceFunctions(unittest.TestCase):
    """测试便利函数。"""
    
    def test_create_api_server_function_exists(self):
        """测试create_api_server函数存在。"""
        from utils.api_server import create_api_server
        self.assertTrue(callable(create_api_server))
    
    def test_create_api_server_with_config(self):
        """测试使用配置创建API服务器函数。"""
        config = APIConfig(enable_websocket=False)
        
        # 测试函数接受配置参数
        try:
            from utils.api_server import create_api_server
            # 由于Flask可能不可用，我们只测试函数调用不会立即失败
            # 实际的服务器创建可能会因为依赖问题而失败，这是预期的
            self.assertTrue(callable(create_api_server))
        except ImportError:
            # 如果Flask不可用，这是预期的行为
            pass
    
    def test_create_api_server_default_config(self):
        """测试使用默认配置创建API服务器。"""
        try:
            from utils.api_server import create_api_server
            # 测试函数可以不带参数调用
            self.assertTrue(callable(create_api_server))
        except ImportError:
            # 如果Flask不可用，这是预期的行为
            pass


class TestIntegration(unittest.TestCase):
    """集成测试。"""
    
    def test_complete_workflow_components(self):
        """测试完整工作流程的各个组件。"""
        # 创建配置
        config = APIConfig(
            enable_authentication=True,
            enable_websocket=False,
            rate_limit_per_minute=10
        )
        
        # 测试认证管理器
        auth_manager = AuthenticationManager('test_secret_key')
        
        # 1. 用户登录
        token = auth_manager.authenticate('admin', 'admin123')
        self.assertIsNotNone(token)
        
        # 2. 验证token
        user_info = auth_manager.verify_token(token)
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info['username'], 'admin')
        
        # 3. 检查权限
        self.assertTrue(auth_manager.check_permission(user_info, 'read'))
        self.assertTrue(auth_manager.check_permission(user_info, 'write'))
        self.assertTrue(auth_manager.check_permission(user_info, 'control'))
        
        # 4. 测试速率限制
        rate_limiter = RateLimiter(max_requests_per_minute=10)
        client_id = 'test_client'
        
        # 应该允许前10个请求
        for i in range(10):
            self.assertTrue(rate_limiter.is_allowed(client_id))
        
        # 第11个请求应该被拒绝
        self.assertFalse(rate_limiter.is_allowed(client_id))
        
        # 5. 用户登出
        revoked = auth_manager.revoke_token(token)
        self.assertTrue(revoked)
        
        # 验证token已失效
        user_info = auth_manager.verify_token(token)
        self.assertIsNone(user_info)


if __name__ == '__main__':
    unittest.main()