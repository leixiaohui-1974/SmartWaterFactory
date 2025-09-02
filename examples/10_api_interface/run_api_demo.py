#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API接口演示脚本。

演示智能水厂API接口的各种功能，包括：
1. RESTful API服务器
2. 用户认证和权限管理
3. 数据查询和更新
4. WebSocket实时通信
5. 客户端示例
"""

import sys
import time
import json
import threading
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.api_server import create_api_server, APIConfig
    from utils.performance import PerformanceProfiler
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所需的依赖包")
    sys.exit(1)

# 检查Flask是否可用
try:
    import flask
    import requests
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("警告: Flask或requests未安装，将跳过实际的API服务器演示")


def demonstrate_api_config():
    """演示API配置功能。"""
    print("\n=== API配置演示 ===")
    
    # 默认配置
    default_config = APIConfig()
    print(f"默认配置:")
    print(f"  主机: {default_config.host}")
    print(f"  端口: {default_config.port}")
    print(f"  调试模式: {default_config.debug}")
    print(f"  启用认证: {default_config.enable_authentication}")
    print(f"  启用WebSocket: {default_config.enable_websocket}")
    print(f"  JWT过期时间: {default_config.jwt_expiration_hours}小时")
    print(f"  速率限制: {default_config.rate_limit_per_minute}次/分钟")
    
    # 自定义配置
    custom_config = APIConfig(
        host='0.0.0.0',
        port=8080,
        debug=True,
        jwt_expiration_hours=12,
        rate_limit_per_minute=120
    )
    print(f"\n自定义配置:")
    print(f"  主机: {custom_config.host}")
    print(f"  端口: {custom_config.port}")
    print(f"  调试模式: {custom_config.debug}")
    print(f"  JWT过期时间: {custom_config.jwt_expiration_hours}小时")
    print(f"  速率限制: {custom_config.rate_limit_per_minute}次/分钟")


def demonstrate_authentication():
    """演示认证功能。"""
    print("\n=== 认证系统演示 ===")
    
    if not FLASK_AVAILABLE:
        print("跳过认证演示（Flask不可用）")
        return
    
    try:
        from utils.api_server import AuthenticationManager
        
        # 创建认证管理器
        auth_manager = AuthenticationManager('demo_secret', 1)
        
        print("\n1. 用户登录测试")
        
        # 测试不同用户登录
        test_users = [
            ('admin', 'admin123', '管理员'),
            ('operator', 'operator123', '操作员'),
            ('user', 'user123', '普通用户'),
            ('invalid', 'wrong', '无效用户')
        ]
        
        tokens = {}
        
        for username, password, description in test_users:
            token = auth_manager.authenticate(username, password)
            if token:
                tokens[username] = token
                print(f"  ✓ {description}({username})登录成功")
                
                # 验证token
                user_info = auth_manager.verify_token(token)
                if user_info:
                    print(f"    角色: {user_info['role']}")
                    print(f"    权限: {', '.join(user_info['permissions'])}")
            else:
                print(f"  ✗ {description}({username})登录失败")
        
        print("\n2. 权限检查测试")
        
        # 测试权限检查
        permissions_to_test = ['read', 'write', 'control', 'config', 'user_management']
        
        for username, token in tokens.items():
            user_info = auth_manager.verify_token(token)
            if user_info:
                print(f"\n  {username}的权限:")
                for permission in permissions_to_test:
                    has_permission = auth_manager.check_permission(user_info, permission)
                    status = "✓" if has_permission else "✗"
                    print(f"    {status} {permission}")
        
        print("\n3. Token撤销测试")
        
        # 撤销admin的token
        if 'admin' in tokens:
            admin_token = tokens['admin']
            print(f"  撤销admin的token...")
            
            # 撤销前验证
            user_info = auth_manager.verify_token(admin_token)
            print(f"  撤销前验证: {'有效' if user_info else '无效'}")
            
            # 撤销token
            revoked = auth_manager.revoke_token(admin_token)
            print(f"  撤销结果: {'成功' if revoked else '失败'}")
            
            # 撤销后验证
            user_info = auth_manager.verify_token(admin_token)
            print(f"  撤销后验证: {'有效' if user_info else '无效'}")
    
    except Exception as e:
        print(f"认证演示出错: {e}")


def demonstrate_rate_limiting():
    """演示速率限制功能。"""
    print("\n=== 速率限制演示 ===")
    
    if not FLASK_AVAILABLE:
        print("跳过速率限制演示（Flask不可用）")
        return
    
    try:
        from utils.api_server import RateLimiter
        
        # 创建速率限制器（每分钟5次请求）
        rate_limiter = RateLimiter(max_requests_per_minute=5)
        
        client_id = 'demo_client'
        
        print(f"测试客户端: {client_id}")
        print(f"限制: 每分钟5次请求")
        print("\n请求测试:")
        
        # 测试请求
        for i in range(8):
            allowed = rate_limiter.is_allowed(client_id)
            status = "允许" if allowed else "拒绝"
            print(f"  请求 {i+1}: {status}")
            
            if not allowed:
                break
        
        print("\n不同客户端测试:")
        
        # 测试不同客户端
        clients = ['client_1', 'client_2', 'client_3']
        
        for client in clients:
            allowed_count = 0
            for i in range(6):
                if rate_limiter.is_allowed(client):
                    allowed_count += 1
                else:
                    break
            
            print(f"  {client}: 允许 {allowed_count} 次请求")
    
    except Exception as e:
        print(f"速率限制演示出错: {e}")


def demonstrate_api_server():
    """演示API服务器功能。"""
    print("\n=== API服务器演示 ===")
    
    if not FLASK_AVAILABLE:
        print("跳过API服务器演示（Flask不可用）")
        return
    
    try:
        # 创建API服务器配置
        config = APIConfig(
            host='127.0.0.1',
            port=5001,  # 使用不同端口避免冲突
            debug=True,
            enable_websocket=False,  # 简化演示
            rate_limit_per_minute=30
        )
        
        print(f"创建API服务器:")
        print(f"  地址: {config.host}:{config.port}")
        print(f"  调试模式: {config.debug}")
        print(f"  认证: {config.enable_authentication}")
        print(f"  WebSocket: {config.enable_websocket}")
        
        # 创建服务器实例
        server = create_api_server(config)
        
        print(f"\n服务器组件:")
        print(f"  Flask应用: {'已创建' if server.app else '未创建'}")
        print(f"  认证管理器: {'已创建' if server.auth_manager else '未创建'}")
        print(f"  速率限制器: {'已创建' if server.rate_limiter else '未创建'}")
        print(f"  WebSocket: {'已启用' if server.socketio else '未启用'}")
        
        # 显示初始数据
        print(f"\n初始数据结构:")
        print(f"  水质数据: {list(server.plant_data['water_quality'].keys())}")
        print(f"  控制状态: {list(server.plant_data['control_status'].keys())}")
        print(f"  系统状态: {list(server.plant_data['system_status'].keys())}")
        
        # 模拟数据更新
        print(f"\n模拟数据更新:")
        original_turbidity = server.plant_data['water_quality']['turbidity']
        server.plant_data['water_quality']['turbidity'] = 2.8
        server.plant_data['water_quality']['last_updated'] = datetime.now().isoformat()
        
        print(f"  浊度: {original_turbidity} → {server.plant_data['water_quality']['turbidity']} NTU")
        print(f"  更新时间: {server.plant_data['water_quality']['last_updated']}")
        
        print("\n注意: 实际的API服务器需要调用 server.run() 来启动")
        print("      在生产环境中，建议使用 Gunicorn 或 uWSGI 等WSGI服务器")
    
    except Exception as e:
        print(f"API服务器演示出错: {e}")


def demonstrate_client_simulation():
    """演示客户端模拟。"""
    print("\n=== 客户端模拟演示 ===")
    
    # 模拟API响应
    print("\n1. 模拟API响应格式")
    
    from utils.api_server import APIResponse
    
    # 成功响应
    success_response = APIResponse(
        success=True,
        data={
            'turbidity': 2.5,
            'dissolved_oxygen': 8.2,
            'ph': 7.1,
            'temperature': 22.5
        },
        message='数据获取成功'
    )
    
    print("成功响应:")
    print(json.dumps(success_response.to_dict(), indent=2, ensure_ascii=False))
    
    # 错误响应
    error_response = APIResponse(
        success=False,
        message='认证失败',
        error_code='AUTHENTICATION_FAILED'
    )
    
    print("\n错误响应:")
    print(json.dumps(error_response.to_dict(), indent=2, ensure_ascii=False))
    
    # 模拟客户端请求
    print("\n2. 模拟客户端请求")
    
    # 模拟登录请求
    login_request = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    print("登录请求:")
    print(f"POST /api/auth/login")
    print(json.dumps(login_request, indent=2, ensure_ascii=False))
    
    # 模拟数据查询请求
    print("\n数据查询请求:")
    print(f"GET /api/data/water-quality")
    print(f"Headers: Authorization: Bearer <token>")
    
    # 模拟控制请求
    control_request = {
        'pump_status': 'running',
        'valve_position': 75,
        'flow_rate': 120.5
    }
    
    print("\n控制请求:")
    print(f"PUT /api/data/control-status")
    print(f"Headers: Authorization: Bearer <token>")
    print(json.dumps(control_request, indent=2, ensure_ascii=False))


def demonstrate_websocket_simulation():
    """演示WebSocket模拟。"""
    print("\n=== WebSocket模拟演示 ===")
    
    print("\n1. 客户端连接事件")
    
    # 模拟连接事件
    connect_event = {
        'event': 'connect',
        'timestamp': datetime.now().isoformat(),
        'client_id': 'client_12345'
    }
    
    print("连接事件:")
    print(json.dumps(connect_event, indent=2, ensure_ascii=False))
    
    print("\n2. 订阅事件")
    
    # 模拟订阅事件
    subscribe_event = {
        'event': 'subscribe',
        'topics': ['water_quality', 'control_status', 'system_alerts'],
        'client_id': 'client_12345'
    }
    
    print("订阅请求:")
    print(json.dumps(subscribe_event, indent=2, ensure_ascii=False))
    
    print("\n3. 数据推送事件")
    
    # 模拟数据推送
    data_update_event = {
        'event': 'data_update',
        'topic': 'water_quality',
        'data': {
            'turbidity': 2.3,
            'dissolved_oxygen': 8.5,
            'ph': 7.2,
            'temperature': 23.1,
            'timestamp': datetime.now().isoformat()
        }
    }
    
    print("数据更新推送:")
    print(json.dumps(data_update_event, indent=2, ensure_ascii=False))
    
    print("\n4. 系统警报事件")
    
    # 模拟系统警报
    alert_event = {
        'event': 'system_alert',
        'alert': {
            'level': 'warning',
            'message': '浊度超出正常范围',
            'value': 5.2,
            'threshold': 5.0,
            'timestamp': datetime.now().isoformat()
        }
    }
    
    print("系统警报:")
    print(json.dumps(alert_event, indent=2, ensure_ascii=False))
    
    print("\n5. 控制命令事件")
    
    # 模拟控制命令
    control_command = {
        'event': 'control_command',
        'command': {
            'action': 'set_pump_speed',
            'value': 85,
            'user': 'admin',
            'timestamp': datetime.now().isoformat()
        }
    }
    
    print("控制命令:")
    print(json.dumps(control_command, indent=2, ensure_ascii=False))
    
    # 模拟控制响应
    control_response = {
        'event': 'control_response',
        'response': {
            'success': True,
            'action': 'set_pump_speed',
            'old_value': 75,
            'new_value': 85,
            'message': '泵速度设置成功',
            'timestamp': datetime.now().isoformat()
        }
    }
    
    print("\n控制响应:")
    print(json.dumps(control_response, indent=2, ensure_ascii=False))


def demonstrate_performance_integration():
    """演示性能监控集成。"""
    print("\n=== 性能监控集成演示 ===")
    
    # 创建性能分析器
    profiler = PerformanceProfiler()
    
    @profiler.profile()
    def simulate_api_request():
        """模拟API请求处理。"""
        # 模拟数据库查询
        time.sleep(0.01)
        
        # 模拟数据处理
        data = {
            'turbidity': 2.5 + (time.time() % 10) * 0.1,
            'dissolved_oxygen': 8.0 + (time.time() % 5) * 0.2,
            'ph': 7.0 + (time.time() % 3) * 0.1,
            'temperature': 20.0 + (time.time() % 15)
        }
        
        # 模拟响应生成
        time.sleep(0.005)
        
        return data
    
    @profiler.profile()
    def simulate_websocket_broadcast():
        """模拟WebSocket广播。"""
        # 模拟数据准备
        time.sleep(0.002)
        
        # 模拟广播到多个客户端
        for i in range(5):
            time.sleep(0.001)
        
        return True
    
    print("执行性能测试...")
    
    # 执行多次API请求模拟
    for i in range(10):
        data = simulate_api_request()
        if i == 0:
            print(f"API请求示例数据: {data}")
    
    # 执行WebSocket广播模拟
    for i in range(5):
        simulate_websocket_broadcast()
    
    # 获取性能指标
    metrics = profiler.get_function_metrics()
    
    print(f"\n性能指标:")
    for func_name, stats in metrics.items():
        print(f"\n{func_name}:")
        print(f"  调用次数: {stats['call_count']}")
        print(f"  平均执行时间: {stats['avg_execution_time']:.4f}秒")
        print(f"  最后执行时间: {stats['last_execution_time']:.4f}秒")
        print(f"  内存使用: {stats['memory_usage']:.2f}MB")
        print(f"  最大内存: {stats['max_memory']:.2f}MB")
        print(f"  最小内存: {stats['min_memory']:.2f}MB")
        print(f"  CPU使用: {stats['cpu_usage']:.1f}%")


def demonstrate_security_features():
    """演示安全功能。"""
    print("\n=== 安全功能演示 ===")
    
    print("\n1. 输入验证示例")
    
    # 模拟输入验证
    def validate_water_quality_data(data):
        """验证水质数据输入。"""
        errors = []
        
        # 检查必需字段
        required_fields = ['turbidity', 'dissolved_oxygen', 'ph', 'temperature']
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查数据范围
        if 'turbidity' in data:
            if not (0 <= data['turbidity'] <= 100):
                errors.append("浊度值超出有效范围 (0-100 NTU)")
        
        if 'dissolved_oxygen' in data:
            if not (0 <= data['dissolved_oxygen'] <= 20):
                errors.append("溶解氧值超出有效范围 (0-20 mg/L)")
        
        if 'ph' in data:
            if not (0 <= data['ph'] <= 14):
                errors.append("pH值超出有效范围 (0-14)")
        
        if 'temperature' in data:
            if not (-10 <= data['temperature'] <= 50):
                errors.append("温度值超出有效范围 (-10-50°C)")
        
        return errors
    
    # 测试有效数据
    valid_data = {
        'turbidity': 2.5,
        'dissolved_oxygen': 8.2,
        'ph': 7.1,
        'temperature': 22.5
    }
    
    errors = validate_water_quality_data(valid_data)
    print(f"有效数据验证: {'通过' if not errors else '失败'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
    
    # 测试无效数据
    invalid_data = {
        'turbidity': 150,  # 超出范围
        'dissolved_oxygen': -5,  # 负值
        'ph': 15,  # 超出范围
        # 缺少temperature字段
    }
    
    errors = validate_water_quality_data(invalid_data)
    print(f"\n无效数据验证: {'通过' if not errors else '失败'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
    
    print("\n2. 安全配置建议")
    
    security_recommendations = [
        "使用强JWT密钥（至少32字符）",
        "启用HTTPS加密传输",
        "设置合理的速率限制",
        "定期轮换JWT密钥",
        "记录所有API访问日志",
        "实施IP白名单（如适用）",
        "使用安全的会话管理",
        "定期安全审计和漏洞扫描"
    ]
    
    for i, recommendation in enumerate(security_recommendations, 1):
        print(f"  {i}. {recommendation}")
    
    print("\n3. 错误处理示例")
    
    # 模拟错误响应
    error_examples = [
        {
            'code': 'AUTHENTICATION_FAILED',
            'message': '用户名或密码错误',
            'status': 401
        },
        {
            'code': 'PERMISSION_DENIED',
            'message': '权限不足，无法执行此操作',
            'status': 403
        },
        {
            'code': 'RATE_LIMIT_EXCEEDED',
            'message': '请求频率过高，请稍后重试',
            'status': 429
        },
        {
            'code': 'INVALID_INPUT',
            'message': '输入数据格式错误',
            'status': 400
        }
    ]
    
    for error in error_examples:
        print(f"  {error['status']} - {error['code']}: {error['message']}")


def main():
    """主函数。"""
    print("智能水厂API接口演示")
    print("=" * 50)
    
    try:
        # 演示各个功能模块
        demonstrate_api_config()
        demonstrate_authentication()
        demonstrate_rate_limiting()
        demonstrate_api_server()
        demonstrate_client_simulation()
        demonstrate_websocket_simulation()
        demonstrate_performance_integration()
        demonstrate_security_features()
        
        print("\n=== 演示总结 ===")
        print("✓ API配置管理")
        print("✓ 用户认证和权限控制")
        print("✓ 速率限制和安全防护")
        print("✓ RESTful API服务器")
        print("✓ 客户端交互模拟")
        print("✓ WebSocket实时通信")
        print("✓ 性能监控集成")
        print("✓ 安全功能和最佳实践")
        
        if not FLASK_AVAILABLE:
            print("\n注意: 部分功能需要安装Flask和相关依赖")
            print("安装命令: pip install flask flask-cors flask-socketio pyjwt requests")
        
        print("\n演示完成！")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()