# API接口和远程控制

本示例展示了智能水厂的API接口和远程控制功能，包括RESTful API、WebSocket实时通信和用户认证系统。

## 功能特性

### 1. RESTful API
- **健康检查**: 系统状态监控
- **用户认证**: 登录/登出管理
- **数据查询**: 水质、控制状态、系统状态
- **数据更新**: 远程控制和参数调整
- **数据导出**: 历史数据和报告生成

### 2. WebSocket实时通信
- **实时数据推送**: 水质参数实时更新
- **事件通知**: 系统警报和状态变化
- **双向通信**: 客户端与服务器实时交互

### 3. 安全认证
- **JWT令牌**: 安全的用户认证
- **角色权限**: 管理员、操作员、普通用户
- **速率限制**: 防止API滥用
- **会话管理**: 令牌生成、验证和撤销

## API端点

### 基础端点
```
GET  /api/health          # 健康检查
POST /api/auth/login      # 用户登录
POST /api/auth/logout     # 用户登出
```

### 数据查询
```
GET  /api/data/water-quality    # 获取水质数据
GET  /api/data/control-status   # 获取控制状态
GET  /api/data/system-status    # 获取系统状态
GET  /api/data/all             # 获取所有数据
```

### 数据更新
```
PUT  /api/data/water-quality    # 更新水质数据
PUT  /api/data/control-status   # 更新控制状态
PUT  /api/data/system-status    # 更新系统状态
```

### 数据导出
```
GET  /api/export/water-quality  # 导出水质数据
GET  /api/export/control-logs   # 导出控制日志
GET  /api/export/system-report  # 导出系统报告
```

## WebSocket事件

### 客户端事件
```javascript
// 连接到服务器
socket.connect();

// 订阅数据更新
socket.emit('subscribe', {
    topics: ['water_quality', 'control_status', 'system_alerts']
});

// 发送控制命令
socket.emit('control_command', {
    action: 'set_pump_speed',
    value: 75
});
```

### 服务器事件
```javascript
// 数据更新推送
socket.on('data_update', function(data) {
    console.log('Received update:', data);
});

// 系统警报
socket.on('system_alert', function(alert) {
    console.log('Alert:', alert);
});

// 控制响应
socket.on('control_response', function(response) {
    console.log('Control result:', response);
});
```

## 用户角色和权限

### 管理员 (admin)
- 所有读写权限
- 系统配置管理
- 用户管理
- 完全控制权限

### 操作员 (operator)
- 数据读写权限
- 设备控制权限
- 无系统配置权限

### 普通用户 (user)
- 仅数据读取权限
- 无控制权限

## 配置选项

```python
from utils.api_server import APIConfig

config = APIConfig(
    host='127.0.0.1',              # 服务器地址
    port=5000,                     # 服务器端口
    debug=False,                   # 调试模式
    jwt_secret_key='your-secret',  # JWT密钥
    jwt_expiration_hours=24,       # 令牌过期时间
    enable_authentication=True,    # 启用认证
    enable_websocket=True,         # 启用WebSocket
    rate_limit_per_minute=60       # 速率限制
)
```

## 使用示例

### 1. 启动API服务器
```python
from utils.api_server import create_api_server, APIConfig

# 创建配置
config = APIConfig(
    host='0.0.0.0',
    port=5000,
    debug=True
)

# 创建并启动服务器
server = create_api_server(config)
server.run()
```

### 2. 客户端认证
```python
import requests

# 用户登录
response = requests.post('http://localhost:5000/api/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})

token = response.json()['data']['token']
headers = {'Authorization': f'Bearer {token}'}
```

### 3. 数据查询
```python
# 获取水质数据
response = requests.get(
    'http://localhost:5000/api/data/water-quality',
    headers=headers
)

water_quality = response.json()['data']
print(f"浊度: {water_quality['turbidity']} NTU")
print(f"溶解氧: {water_quality['dissolved_oxygen']} mg/L")
```

### 4. 远程控制
```python
# 更新控制状态
response = requests.put(
    'http://localhost:5000/api/data/control-status',
    headers=headers,
    json={
        'pump_status': 'running',
        'valve_position': 75,
        'flow_rate': 120.5
    }
)

result = response.json()
print(f"控制更新结果: {result['message']}")
```

### 5. WebSocket客户端
```python
import socketio

# 创建Socket.IO客户端
sio = socketio.Client()

@sio.event
def connect():
    print('连接到服务器')
    sio.emit('subscribe', {'topics': ['water_quality']})

@sio.event
def data_update(data):
    print(f'数据更新: {data}')

@sio.event
def disconnect():
    print('断开连接')

# 连接到服务器
sio.connect('http://localhost:5000')
sio.wait()
```

## 安全注意事项

1. **JWT密钥**: 使用强密钥并定期更换
2. **HTTPS**: 生产环境中使用HTTPS
3. **速率限制**: 防止API滥用
4. **输入验证**: 验证所有输入数据
5. **权限检查**: 严格的权限控制

## 错误处理

API使用标准HTTP状态码和统一的错误响应格式：

```json
{
    "success": false,
    "message": "错误描述",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

常见错误码：
- `AUTHENTICATION_FAILED`: 认证失败
- `PERMISSION_DENIED`: 权限不足
- `RATE_LIMIT_EXCEEDED`: 超过速率限制
- `INVALID_INPUT`: 输入数据无效
- `RESOURCE_NOT_FOUND`: 资源不存在

## 性能优化

1. **连接池**: 使用数据库连接池
2. **缓存**: 缓存频繁访问的数据
3. **压缩**: 启用响应压缩
4. **异步处理**: 使用异步I/O
5. **负载均衡**: 多实例部署

## 监控和日志

- **访问日志**: 记录所有API请求
- **错误日志**: 记录错误和异常
- **性能监控**: 监控响应时间和吞吐量
- **安全审计**: 记录认证和授权事件

## 扩展功能

1. **API版本控制**: 支持多版本API
2. **文档生成**: 自动生成API文档
3. **测试工具**: API测试和验证
4. **客户端SDK**: 多语言客户端库
5. **集成支持**: 与第三方系统集成

通过这些API接口，您可以轻松地将智能水厂系统集成到更大的工业自动化平台中，实现远程监控和控制。