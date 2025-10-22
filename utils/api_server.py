#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能水厂API服务器模块。

本模块提供RESTful API和WebSocket接口，支持远程控制和监控功能。
包括：
1. RESTful API端点
2. WebSocket实时通信
3. 认证和授权
4. 数据序列化
5. 错误处理
"""

import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

try:
    from flask import Flask, request, jsonify, Response
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit, join_room, leave_room
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None
    SocketIO = None

try:
    import jwt as _pyjwt  # type: ignore
except ImportError:
    _pyjwt = None

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    bcrypt = None

_required_jwt_attrs = ("encode", "decode", "ExpiredSignatureError", "InvalidTokenError")
if _pyjwt is not None and all(hasattr(_pyjwt, attr) for attr in _required_jwt_attrs):
    jwt = _pyjwt  # type: ignore[assignment]
    JWT_AVAILABLE = True
else:
    JWT_AVAILABLE = False

    class _MockJWTModule:
        """Fallback JWT-like object when PyJWT is unavailable."""

        class ExpiredSignatureError(Exception):
            """Raised when a token is considered expired."""

        class InvalidTokenError(Exception):
            """Raised when a token is invalid."""

        @staticmethod
        def encode(*args, **kwargs):  # type: ignore[unused-argument]
            raise NotImplementedError("PyJWT is not installed.")

        @staticmethod
        def decode(*args, **kwargs):  # type: ignore[unused-argument]
            raise NotImplementedError("PyJWT is not installed.")

    jwt = _MockJWTModule()


@dataclass
class APIConfig:
    """API配置类。"""
    host: str = '127.0.0.1'
    port: int = 5000
    debug: bool = False
    secret_key: str = 'smart-water-factory-secret-key'
    jwt_expiration_hours: int = 24
    cors_origins: str = '*'
    max_connections: int = 100
    rate_limit_per_minute: int = 60
    enable_authentication: bool = True
    enable_websocket: bool = True
    log_level: str = 'INFO'


@dataclass
class APIResponse:
    """API响应数据结构。"""
    success: bool
    data: Any = None
    message: str = ''
    timestamp: str = ''
    error_code: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)


@dataclass
class UserCredentials:
    """用户凭证。"""
    username: str
    password_hash: str  # 存储哈希后的密码
    role: str = 'user'  # user, admin, operator
    permissions: List[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = self._get_default_permissions()

    def _get_default_permissions(self) -> List[str]:
        """获取默认权限。"""
        if self.role == 'admin':
            return ['read', 'write', 'control', 'config', 'user_management']
        elif self.role == 'operator':
            return ['read', 'write', 'control']
        else:
            return ['read']

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码。"""
        if BCRYPT_AVAILABLE:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            # 如果bcrypt不可用，使用简单的哈希（不推荐用于生产）
            import hashlib
            return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def verify_password(self, password: str) -> bool:
        """验证密码。"""
        if BCRYPT_AVAILABLE:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        else:
            # 简单哈希验证
            import hashlib
            return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()


class AuthenticationManager:
    """认证管理器。"""
    
    def __init__(self, secret_key: str, expiration_hours: int = 24):
        self.secret_key = secret_key
        self.expiration_hours = expiration_hours
        self.users: Dict[str, UserCredentials] = {}
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
        
        # 添加默认用户
        self._add_default_users()
    
    def _add_default_users(self):
        """添加默认用户（从环境变量读取）。

        警告: 默认密码仅用于开发环境！
        生产环境必须通过环境变量设置安全密码。
        """
        import os

        # 从环境变量读取用户配置，如果未设置则使用默认值（仅开发环境）
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')

        operator_username = os.getenv('OPERATOR_USERNAME', 'operator')
        operator_password = os.getenv('OPERATOR_PASSWORD', 'op123')

        user_username = os.getenv('USER_USERNAME', 'user')
        user_password = os.getenv('USER_PASSWORD', 'user123')

        # 检查是否使用了默认密码（安全警告）
        if admin_password == 'admin123' or operator_password == 'op123' or user_password == 'user123':
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "⚠️  检测到使用默认密码！这在生产环境中是不安全的。"
                "请通过环境变量设置: ADMIN_PASSWORD, OPERATOR_PASSWORD, USER_PASSWORD"
            )

        # 创建用户（密码将被哈希存储）
        self.users[admin_username] = UserCredentials(
            admin_username,
            UserCredentials.hash_password(admin_password),
            'admin'
        )
        self.users[operator_username] = UserCredentials(
            operator_username,
            UserCredentials.hash_password(operator_password),
            'operator'
        )
        self.users[user_username] = UserCredentials(
            user_username,
            UserCredentials.hash_password(user_password),
            'user'
        )
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证。

        Args:
            username: 用户名
            password: 密码

        Returns:
            JWT token或None
        """
        # 首先验证用户名和密码
        if username not in self.users:
            return None

        user = self.users[username]
        if not user.verify_password(password):
            return None
        
        # 密码验证已通过，生成token
        if not JWT_AVAILABLE:
            token = 'mock_token_' + username
            # 在mock模式下也记录活跃token
            self.active_tokens[token] = {
                'username': username,
                'created_at': datetime.now(),
                'last_used': datetime.now()
            }
            return token

        # 使用JWT生成token
        payload = {
            'username': username,
            'role': user.role,
            'permissions': user.permissions,
            'exp': datetime.utcnow() + timedelta(hours=self.expiration_hours)
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')

        # 记录活跃token
        self.active_tokens[token] = {
            'username': username,
            'created_at': datetime.now(),
            'last_used': datetime.now()
        }

        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证token。
        
        Args:
            token: JWT token
        
        Returns:
            用户信息或None
        """
        if not JWT_AVAILABLE:
            if token.startswith('mock_token_') and token in self.active_tokens:
                username = token.replace('mock_token_', '')
                if username in self.users:
                    user = self.users[username]
                    return {
                        'username': username,
                        'role': user.role,
                        'permissions': user.permissions
                    }
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # 更新最后使用时间
            if token in self.active_tokens:
                self.active_tokens[token]['last_used'] = datetime.now()
            
            return payload
        except jwt.ExpiredSignatureError:
            # 清理过期token
            if token in self.active_tokens:
                del self.active_tokens[token]
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token: str) -> bool:
        """撤销token。"""
        if token in self.active_tokens:
            del self.active_tokens[token]
            return True
        return False
    
    def check_permission(self, user_info: Dict[str, Any], required_permission: str) -> bool:
        """检查权限。"""
        return required_permission in user_info.get('permissions', [])


class RateLimiter:
    """速率限制器。"""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求。"""
        now = time.time()
        minute_ago = now - 60
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # 清理过期请求
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # 检查是否超过限制
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # 记录当前请求
        self.requests[client_id].append(now)
        return True


class WaterPlantAPIServer:
    """智能水厂API服务器。"""
    
    def __init__(self, config: APIConfig = None):
        self.config = config or APIConfig()
        self.logger = self._setup_logger()
        
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for API server. Install with: pip install flask flask-cors flask-socketio")
        
        # 初始化Flask应用
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = self.config.secret_key
        
        # 启用CORS
        CORS(self.app, origins=self.config.cors_origins)
        
        # 初始化SocketIO
        if self.config.enable_websocket:
            self.socketio = SocketIO(
                self.app,
                cors_allowed_origins=self.config.cors_origins,
                async_mode='threading'
            )
        else:
            self.socketio = None
        
        # 初始化组件
        self.auth_manager = AuthenticationManager(
            self.config.secret_key,
            self.config.jwt_expiration_hours
        )
        self.rate_limiter = RateLimiter(self.config.rate_limit_per_minute)
        
        # 数据存储
        self.plant_data: Dict[str, Any] = {
            'water_quality': {
                'turbidity': 2.1,
                'dissolved_oxygen': 8.2,
                'ph': 7.3,
                'temperature': 22.5,
                'last_updated': datetime.now().isoformat()
            },
            'control_status': {
                'pump_status': 'running',
                'valve_position': 75,
                'flow_rate': 150.0,
                'pressure': 2.8,
                'last_updated': datetime.now().isoformat()
            },
            'system_status': {
                'status': 'normal',
                'alerts': [],
                'uptime': '72:15:30',
                'last_updated': datetime.now().isoformat()
            }
        }
        
        # WebSocket连接管理
        self.websocket_clients: Dict[str, Dict[str, Any]] = {}
        
        # 注册路由
        self._register_routes()
        
        # 注册WebSocket事件
        if self.socketio:
            self._register_websocket_events()
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器。"""
        logger = logging.getLogger('api_server')
        logger.setLevel(getattr(logging, self.config.log_level))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _get_client_id(self) -> str:
        """获取客户端ID。"""
        return request.remote_addr or 'unknown'
    
    def _check_rate_limit(self) -> Optional[Response]:
        """检查速率限制。"""
        client_id = self._get_client_id()
        if not self.rate_limiter.is_allowed(client_id):
            response = APIResponse(
                success=False,
                message='Rate limit exceeded',
                error_code='RATE_LIMIT_EXCEEDED'
            )
            return jsonify(response.to_dict()), 429
        return None
    
    def _authenticate_request(self, required_permission: str = 'read') -> Optional[Response]:
        """认证请求。"""
        if not self.config.enable_authentication:
            return None
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            response = APIResponse(
                success=False,
                message='Authentication required',
                error_code='AUTH_REQUIRED'
            )
            return jsonify(response.to_dict()), 401
        
        token = auth_header.split(' ')[1]
        user_info = self.auth_manager.verify_token(token)
        
        if not user_info:
            response = APIResponse(
                success=False,
                message='Invalid or expired token',
                error_code='INVALID_TOKEN'
            )
            return jsonify(response.to_dict()), 401
        
        if not self.auth_manager.check_permission(user_info, required_permission):
            response = APIResponse(
                success=False,
                message='Insufficient permissions',
                error_code='INSUFFICIENT_PERMISSIONS'
            )
            return jsonify(response.to_dict()), 403
        
        # 将用户信息添加到请求上下文
        request.user_info = user_info
        return None
    
    def _register_routes(self):
        """注册API路由。"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """健康检查端点。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            response = APIResponse(
                success=True,
                data={
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0'
                },
                message='API server is running'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/auth/login', methods=['POST'])
        def login():
            """用户登录。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            data = request.get_json()
            if not data or 'username' not in data or 'password' not in data:
                response = APIResponse(
                    success=False,
                    message='Username and password required',
                    error_code='INVALID_CREDENTIALS'
                )
                return jsonify(response.to_dict()), 400
            
            token = self.auth_manager.authenticate(data['username'], data['password'])
            if token:
                user = self.auth_manager.users.get(data['username'])
                response = APIResponse(
                    success=True,
                    data={
                        'token': token,
                        'user': {
                            'username': user.username,
                            'role': user.role,
                            'permissions': user.permissions
                        }
                    },
                    message='Login successful'
                )
                return jsonify(response.to_dict())
            else:
                response = APIResponse(
                    success=False,
                    message='Invalid credentials',
                    error_code='INVALID_CREDENTIALS'
                )
                return jsonify(response.to_dict()), 401
        
        @self.app.route('/api/auth/logout', methods=['POST'])
        def logout():
            """用户登出。"""
            auth_response = self._authenticate_request()
            if auth_response:
                return auth_response
            
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                self.auth_manager.revoke_token(token)
            
            response = APIResponse(
                success=True,
                message='Logout successful'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/water-quality', methods=['GET'])
        def get_water_quality():
            """获取水质数据。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            auth_response = self._authenticate_request('read')
            if auth_response:
                return auth_response
            
            response = APIResponse(
                success=True,
                data=self.plant_data['water_quality'],
                message='Water quality data retrieved'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/water-quality', methods=['POST'])
        def update_water_quality():
            """更新水质数据。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            auth_response = self._authenticate_request('write')
            if auth_response:
                return auth_response
            
            data = request.get_json()
            if not data:
                response = APIResponse(
                    success=False,
                    message='No data provided',
                    error_code='NO_DATA'
                )
                return jsonify(response.to_dict()), 400
            
            # 更新水质数据
            self.plant_data['water_quality'].update(data)
            self.plant_data['water_quality']['last_updated'] = datetime.now().isoformat()
            
            # 通过WebSocket广播更新
            if self.socketio:
                self.socketio.emit('water_quality_update', self.plant_data['water_quality'])
            
            response = APIResponse(
                success=True,
                data=self.plant_data['water_quality'],
                message='Water quality data updated'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/control', methods=['GET'])
        def get_control_status():
            """获取控制状态。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            auth_response = self._authenticate_request('read')
            if auth_response:
                return auth_response
            
            response = APIResponse(
                success=True,
                data=self.plant_data['control_status'],
                message='Control status retrieved'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/control', methods=['POST'])
        def update_control():
            """更新控制参数。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            auth_response = self._authenticate_request('control')
            if auth_response:
                return auth_response
            
            data = request.get_json()
            if not data:
                response = APIResponse(
                    success=False,
                    message='No control data provided',
                    error_code='NO_DATA'
                )
                return jsonify(response.to_dict()), 400
            
            # 验证控制参数
            valid_params = ['pump_status', 'valve_position', 'flow_rate']
            invalid_params = [key for key in data.keys() if key not in valid_params]
            
            if invalid_params:
                response = APIResponse(
                    success=False,
                    message=f'Invalid control parameters: {invalid_params}',
                    error_code='INVALID_PARAMS'
                )
                return jsonify(response.to_dict()), 400
            
            # 更新控制状态
            self.plant_data['control_status'].update(data)
            self.plant_data['control_status']['last_updated'] = datetime.now().isoformat()
            
            # 记录控制操作
            self.logger.info(f"Control update by {getattr(request, 'user_info', {}).get('username', 'unknown')}: {data}")
            
            # 通过WebSocket广播更新
            if self.socketio:
                self.socketio.emit('control_update', self.plant_data['control_status'])
            
            response = APIResponse(
                success=True,
                data=self.plant_data['control_status'],
                message='Control parameters updated'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/system-status', methods=['GET'])
        def get_system_status():
            """获取系统状态。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            auth_response = self._authenticate_request('read')
            if auth_response:
                return auth_response
            
            response = APIResponse(
                success=True,
                data=self.plant_data['system_status'],
                message='System status retrieved'
            )
            return jsonify(response.to_dict())
        
        @self.app.route('/api/data/export', methods=['GET'])
        def export_data():
            """导出所有数据。"""
            rate_limit_response = self._check_rate_limit()
            if rate_limit_response:
                return rate_limit_response
            
            auth_response = self._authenticate_request('read')
            if auth_response:
                return auth_response
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'plant_data': self.plant_data
            }
            
            response = APIResponse(
                success=True,
                data=export_data,
                message='Data exported successfully'
            )
            return jsonify(response.to_dict())
    
    def _register_websocket_events(self):
        """注册WebSocket事件。"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接事件。"""
            client_id = request.sid
            self.websocket_clients[client_id] = {
                'connected_at': datetime.now(),
                'last_ping': datetime.now(),
                'subscriptions': []
            }
            
            self.logger.info(f"WebSocket client connected: {client_id}")
            emit('connected', {'message': 'Connected to Smart Water Factory API'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开事件。"""
            client_id = request.sid
            if client_id in self.websocket_clients:
                del self.websocket_clients[client_id]
            
            self.logger.info(f"WebSocket client disconnected: {client_id}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """订阅数据更新。"""
            client_id = request.sid
            if client_id not in self.websocket_clients:
                return
            
            topic = data.get('topic')
            if topic in ['water_quality', 'control_status', 'system_status']:
                if topic not in self.websocket_clients[client_id]['subscriptions']:
                    self.websocket_clients[client_id]['subscriptions'].append(topic)
                
                join_room(topic)
                emit('subscribed', {'topic': topic, 'message': f'Subscribed to {topic}'})
                
                # 发送当前数据
                emit(f'{topic}_update', self.plant_data[topic])
            else:
                emit('error', {'message': f'Invalid topic: {topic}'})
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """取消订阅。"""
            client_id = request.sid
            if client_id not in self.websocket_clients:
                return
            
            topic = data.get('topic')
            if topic in self.websocket_clients[client_id]['subscriptions']:
                self.websocket_clients[client_id]['subscriptions'].remove(topic)
                leave_room(topic)
                emit('unsubscribed', {'topic': topic, 'message': f'Unsubscribed from {topic}'})
        
        @self.socketio.on('ping')
        def handle_ping():
            """心跳检测。"""
            client_id = request.sid
            if client_id in self.websocket_clients:
                self.websocket_clients[client_id]['last_ping'] = datetime.now()
            
            emit('pong', {'timestamp': datetime.now().isoformat()})
    
    def _start_background_tasks(self):
        """启动后台任务。"""
        def simulate_data_updates():
            """模拟数据更新。"""
            import random
            
            while True:
                try:
                    # 模拟水质数据变化
                    self.plant_data['water_quality'].update({
                        'turbidity': max(0, 2.1 + random.gauss(0, 0.2)),
                        'dissolved_oxygen': max(0, 8.2 + random.gauss(0, 0.3)),
                        'ph': max(0, 7.3 + random.gauss(0, 0.1)),
                        'temperature': max(0, 22.5 + random.gauss(0, 1.0)),
                        'last_updated': datetime.now().isoformat()
                    })
                    
                    # 通过WebSocket广播
                    if self.socketio:
                        self.socketio.emit('water_quality_update', self.plant_data['water_quality'])
                    
                    time.sleep(5)  # 每5秒更新一次
                    
                except Exception as e:
                    self.logger.error(f"Background task error: {e}")
                    time.sleep(10)
        
        # 启动后台线程
        background_thread = threading.Thread(target=simulate_data_updates, daemon=True)
        background_thread.start()
    
    def run(self, host: str = None, port: int = None, debug: bool = None):
        """运行API服务器。"""
        host = host or self.config.host
        port = port or self.config.port
        debug = debug if debug is not None else self.config.debug
        
        self.logger.info(f"Starting Smart Water Factory API Server on {host}:{port}")
        
        if self.socketio:
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        else:
            self.app.run(host=host, port=port, debug=debug)


# 便利函数
def create_api_server(config: APIConfig = None) -> WaterPlantAPIServer:
    """创建API服务器实例。"""
    return WaterPlantAPIServer(config)


def run_api_server(host: str = '127.0.0.1', port: int = 5000, debug: bool = False) -> None:
    """快速启动API服务器。"""
    config = APIConfig(host=host, port=port, debug=debug)
    server = create_api_server(config)
    server.run()


if __name__ == '__main__':
    # 直接运行时启动服务器
    run_api_server(debug=True)
