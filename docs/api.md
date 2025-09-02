# 智能水厂控制系统 API 文档

## 目录

1. [概述](#概述)
2. [认证](#认证)
3. [基础接口](#基础接口)
4. [水质监控接口](#水质监控接口)
5. [控制系统接口](#控制系统接口)
6. [仿真管理接口](#仿真管理接口)
7. [数据分析接口](#数据分析接口)
8. [系统管理接口](#系统管理接口)
9. [WebSocket 接口](#websocket-接口)
10. [错误处理](#错误处理)
11. [限流和配额](#限流和配额)
12. [SDK 和示例](#sdk-和示例)

## 概述

智能水厂控制系统提供完整的 RESTful API 和 WebSocket 接口，支持实时监控、控制操作、数据分析等功能。

### 基础信息

- **基础 URL**: `http://localhost:5000/api/v1`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8
- **API 版本**: v1

### 通用响应格式

#### 成功响应

```json
{
    "success": true,
    "data": {},
    "message": "操作成功",
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
}
```

#### 错误响应

```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "参数无效",
        "details": "pH 值必须在 6.0-9.0 范围内"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

## 认证

### JWT Token 认证

API 使用 JWT (JSON Web Token) 进行身份认证。

#### 获取 Token

```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

响应：
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 3600,
        "token_type": "Bearer"
    }
}
```

#### 使用 Token

在请求头中包含 Authorization 字段：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 刷新 Token

```http
POST /auth/refresh
Content-Type: application/json

{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## 基础接口

### 健康检查

检查系统健康状态。

```http
GET /health
```

**响应示例：**

```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "uptime": 3600,
    "components": {
        "database": "healthy",
        "redis": "healthy",
        "simulation": "running"
    }
}
```

### 系统信息

获取系统基本信息。

```http
GET /api/v1/system/info
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "name": "智能水厂控制系统",
        "version": "1.0.0",
        "build_time": "2024-01-01T10:00:00Z",
        "environment": "production",
        "features": [
            "real_time_monitoring",
            "automatic_control",
            "data_analysis",
            "alert_system"
        ]
    }
}
```

### 系统状态

获取系统运行状态。

```http
GET /api/v1/system/status
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "simulation_running": true,
        "control_mode": "automatic",
        "current_time": "2024-01-01T12:00:00Z",
        "system_load": 0.65,
        "memory_usage": 0.45,
        "cpu_usage": 0.32,
        "active_connections": 15
    }
}
```

## 水质监控接口

### 获取当前水质

获取最新的水质监测数据。

```http
GET /api/v1/water-quality/current
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "ph": 7.2,
        "turbidity": 5.0,
        "dissolved_oxygen": 9.5,
        "temperature": 22.0,
        "chlorine": 1.2,
        "conductivity": 450.0,
        "timestamp": "2024-01-01T12:00:00Z",
        "quality_grade": "excellent",
        "alerts": []
    }
}
```

### 获取历史水质数据

获取指定时间范围内的历史水质数据。

```http
GET /api/v1/water-quality/history
```

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| start | string | 是 | 开始时间 (ISO 8601) |
| end | string | 是 | 结束时间 (ISO 8601) |
| interval | string | 否 | 数据间隔 (1m, 5m, 1h, 1d) |
| parameters | string | 否 | 参数列表，逗号分隔 |
| limit | integer | 否 | 最大记录数 (默认 100) |
| offset | integer | 否 | 偏移量 (默认 0) |

**请求示例：**

```http
GET /api/v1/water-quality/history?start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z&interval=1h&parameters=ph,turbidity&limit=24
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "records": [
            {
                "ph": 7.2,
                "turbidity": 5.0,
                "timestamp": "2024-01-01T00:00:00Z"
            },
            {
                "ph": 7.1,
                "turbidity": 5.2,
                "timestamp": "2024-01-01T01:00:00Z"
            }
        ],
        "total": 24,
        "page": 1,
        "per_page": 24,
        "has_next": false
    }
}
```

### 获取水质统计

获取指定时间范围内的水质统计信息。

```http
GET /api/v1/water-quality/statistics
```

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| start | string | 是 | 开始时间 |
| end | string | 是 | 结束时间 |
| parameters | string | 否 | 参数列表 |

**响应示例：**

```json
{
    "success": true,
    "data": {
        "ph": {
            "min": 6.8,
            "max": 7.5,
            "avg": 7.2,
            "std": 0.15,
            "count": 1440
        },
        "turbidity": {
            "min": 3.2,
            "max": 8.1,
            "avg": 5.4,
            "std": 1.2,
            "count": 1440
        }
    }
}
```

### 设置水质阈值

设置水质参数的报警阈值。

```http
PUT /api/v1/water-quality/thresholds
Content-Type: application/json
Authorization: Bearer <token>

{
    "ph": {
        "min": 6.5,
        "max": 8.5,
        "warning_min": 6.8,
        "warning_max": 8.2
    },
    "turbidity": {
        "max": 10.0,
        "warning_max": 8.0
    }
}
```

**响应示例：**

```json
{
    "success": true,
    "message": "水质阈值设置成功",
    "data": {
        "updated_parameters": ["ph", "turbidity"],
        "effective_time": "2024-01-01T12:00:00Z"
    }
}
```

## 控制系统接口

### 获取控制器状态

获取当前控制器的运行状态。

```http
GET /api/v1/control/status
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "mode": "automatic",
        "controller_type": "pid",
        "enabled": true,
        "setpoint": 7.0,
        "current_value": 7.2,
        "output": 45.5,
        "error": -0.2,
        "parameters": {
            "kp": 1.0,
            "ki": 0.1,
            "kd": 0.05
        },
        "performance": {
            "settling_time": 120.5,
            "overshoot": 2.1,
            "steady_state_error": 0.05
        },
        "last_update": "2024-01-01T12:00:00Z"
    }
}
```

### 更新控制参数

更新控制器的参数设置。

```http
PUT /api/v1/control/parameters
Content-Type: application/json
Authorization: Bearer <token>

{
    "controller_type": "pid",
    "parameters": {
        "kp": 1.2,
        "ki": 0.15,
        "kd": 0.08
    },
    "setpoint": 7.5,
    "limits": {
        "output_min": 0.0,
        "output_max": 100.0
    }
}
```

**响应示例：**

```json
{
    "success": true,
    "message": "控制参数更新成功",
    "data": {
        "controller_type": "pid",
        "parameters": {
            "kp": 1.2,
            "ki": 0.15,
            "kd": 0.08
        },
        "setpoint": 7.5,
        "effective_time": "2024-01-01T12:00:00Z"
    }
}
```

### 切换控制模式

在自动和手动控制模式之间切换。

```http
POST /api/v1/control/mode
Content-Type: application/json
Authorization: Bearer <token>

{
    "mode": "manual",
    "manual_output": 60.0
}
```

**响应示例：**

```json
{
    "success": true,
    "message": "控制模式切换成功",
    "data": {
        "previous_mode": "automatic",
        "current_mode": "manual",
        "manual_output": 60.0,
        "switch_time": "2024-01-01T12:00:00Z"
    }
}
```

### 获取设备状态

获取水厂设备的运行状态。

```http
GET /api/v1/control/devices
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "pumps": [
            {
                "id": "pump_001",
                "name": "主水泵",
                "status": "running",
                "speed": 75.5,
                "flow_rate": 120.3,
                "power_consumption": 15.2,
                "temperature": 45.0,
                "vibration": 2.1,
                "last_maintenance": "2024-01-01T00:00:00Z"
            }
        ],
        "valves": [
            {
                "id": "valve_001",
                "name": "进水阀",
                "status": "open",
                "position": 85.0,
                "flow_rate": 95.2,
                "pressure_upstream": 2.5,
                "pressure_downstream": 2.1
            }
        ],
        "sensors": [
            {
                "id": "sensor_ph_001",
                "name": "pH传感器",
                "status": "normal",
                "value": 7.2,
                "calibration_date": "2024-01-01T00:00:00Z",
                "next_calibration": "2024-04-01T00:00:00Z"
            }
        ]
    }
}
```

### 控制设备

控制特定设备的运行。

```http
POST /api/v1/control/devices/{device_id}/command
Content-Type: application/json
Authorization: Bearer <token>

{
    "command": "set_speed",
    "parameters": {
        "speed": 80.0
    },
    "confirm": true
}
```

**响应示例：**

```json
{
    "success": true,
    "message": "设备控制命令执行成功",
    "data": {
        "device_id": "pump_001",
        "command": "set_speed",
        "previous_value": 75.5,
        "new_value": 80.0,
        "execution_time": "2024-01-01T12:00:00Z",
        "estimated_completion": "2024-01-01T12:00:30Z"
    }
}
```

## 仿真管理接口

### 获取仿真状态

获取仿真系统的运行状态。

```http
GET /api/v1/simulation/status
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "running": true,
        "start_time": "2024-01-01T10:00:00Z",
        "current_time": "2024-01-01T12:00:00Z",
        "time_scale": 1.0,
        "step_size": 1.0,
        "total_steps": 7200,
        "performance": {
            "steps_per_second": 10.5,
            "cpu_usage": 0.25,
            "memory_usage": 0.15
        }
    }
}
```

### 控制仿真

启动、停止或重置仿真。

```http
POST /api/v1/simulation/control
Content-Type: application/json
Authorization: Bearer <token>

{
    "action": "start",
    "parameters": {
        "time_scale": 1.0,
        "step_size": 1.0,
        "duration": 3600
    }
}
```

**响应示例：**

```json
{
    "success": true,
    "message": "仿真启动成功",
    "data": {
        "action": "start",
        "start_time": "2024-01-01T12:00:00Z",
        "estimated_end_time": "2024-01-01T13:00:00Z",
        "parameters": {
            "time_scale": 1.0,
            "step_size": 1.0,
            "duration": 3600
        }
    }
}
```

### 设置仿真参数

配置仿真的初始条件和参数。

```http
PUT /api/v1/simulation/parameters
Content-Type: application/json
Authorization: Bearer <token>

{
    "initial_conditions": {
        "water_quality": {
            "ph": 7.0,
            "turbidity": 5.0,
            "dissolved_oxygen": 8.0,
            "temperature": 20.0
        },
        "tank_level": 75.0,
        "flow_rate": 100.0
    },
    "disturbances": {
        "enable_random_noise": true,
        "noise_level": 0.1,
        "enable_step_changes": false
    }
}
```

## 数据分析接口

### 获取趋势分析

获取水质参数的趋势分析结果。

```http
GET /api/v1/analysis/trends
```

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| parameter | string | 是 | 分析参数 |
| period | string | 是 | 分析周期 (1d, 7d, 30d) |
| method | string | 否 | 分析方法 (linear, polynomial) |

**响应示例：**

```json
{
    "success": true,
    "data": {
        "parameter": "ph",
        "period": "7d",
        "trend": {
            "direction": "stable",
            "slope": 0.002,
            "r_squared": 0.85,
            "confidence": 0.95
        },
        "forecast": {
            "next_24h": [
                {"time": "2024-01-02T00:00:00Z", "value": 7.2, "confidence_interval": [7.0, 7.4]},
                {"time": "2024-01-02T01:00:00Z", "value": 7.2, "confidence_interval": [7.0, 7.4]}
            ]
        }
    }
}
```

### 获取异常检测结果

获取系统异常检测的结果。

```http
GET /api/v1/analysis/anomalies
```

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| start | string | 否 | 开始时间 |
| end | string | 否 | 结束时间 |
| severity | string | 否 | 严重程度 (low, medium, high) |
| status | string | 否 | 状态 (active, resolved) |

**响应示例：**

```json
{
    "success": true,
    "data": {
        "anomalies": [
            {
                "id": "anomaly_001",
                "type": "outlier",
                "parameter": "ph",
                "severity": "medium",
                "status": "active",
                "detected_at": "2024-01-01T11:30:00Z",
                "value": 8.5,
                "expected_range": [6.8, 7.5],
                "confidence": 0.92,
                "description": "pH值异常偏高",
                "suggested_actions": [
                    "检查pH传感器校准",
                    "检查加药系统"
                ]
            }
        ],
        "summary": {
            "total": 1,
            "active": 1,
            "resolved": 0,
            "by_severity": {
                "high": 0,
                "medium": 1,
                "low": 0
            }
        }
    }
}
```

### 生成报告

生成系统运行报告。

```http
POST /api/v1/analysis/reports
Content-Type: application/json
Authorization: Bearer <token>

{
    "type": "daily",
    "date": "2024-01-01",
    "sections": [
        "water_quality_summary",
        "control_performance",
        "equipment_status",
        "anomalies"
    ],
    "format": "pdf"
}
```

**响应示例：**

```json
{
    "success": true,
    "message": "报告生成成功",
    "data": {
        "report_id": "report_20240101_001",
        "type": "daily",
        "date": "2024-01-01",
        "format": "pdf",
        "download_url": "/api/v1/reports/report_20240101_001/download",
        "expires_at": "2024-01-08T00:00:00Z",
        "size": 2048576
    }
}
```

## 系统管理接口

### 获取系统配置

获取系统配置信息。

```http
GET /api/v1/admin/config
Authorization: Bearer <admin_token>
```

**响应示例：**

```json
{
    "success": true,
    "data": {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "waterplant",
            "pool_size": 10
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0
        },
        "api": {
            "rate_limit": 1000,
            "timeout": 30,
            "cors_enabled": true
        },
        "logging": {
            "level": "INFO",
            "format": "json",
            "rotation": "daily"
        }
    }
}
```

### 更新系统配置

更新系统配置（需要管理员权限）。

```http
PUT /api/v1/admin/config
Content-Type: application/json
Authorization: Bearer <admin_token>

{
    "api": {
        "rate_limit": 1500,
        "timeout": 45
    },
    "logging": {
        "level": "DEBUG"
    }
}
```

### 系统维护

执行系统维护操作。

```http
POST /api/v1/admin/maintenance
Content-Type: application/json
Authorization: Bearer <admin_token>

{
    "action": "cleanup_logs",
    "parameters": {
        "older_than_days": 30
    }
}
```

## WebSocket 接口

### 连接建立

WebSocket 端点：`ws://localhost:5000/ws`

```javascript
// 建立连接
const ws = new WebSocket('ws://localhost:5000/ws');

// 认证
ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your_jwt_token'
    }));
};
```

### 订阅实时数据

```javascript
// 订阅水质数据
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'water_quality',
    parameters: ['ph', 'turbidity', 'dissolved_oxygen']
}));

// 订阅控制器状态
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'controller_status'
}));
```

### 接收实时数据

```javascript
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'water_quality':
            console.log('水质数据:', data.payload);
            break;
        case 'controller_status':
            console.log('控制器状态:', data.payload);
            break;
        case 'alert':
            console.log('报警:', data.payload);
            break;
    }
};
```

### 发送控制命令

```javascript
// 发送控制命令
ws.send(JSON.stringify({
    type: 'control_command',
    action: 'set_setpoint',
    parameters: {
        controller: 'ph_controller',
        setpoint: 7.5
    }
}));
```

### 消息格式

#### 水质数据推送

```json
{
    "type": "water_quality",
    "timestamp": "2024-01-01T12:00:00Z",
    "payload": {
        "ph": 7.2,
        "turbidity": 5.0,
        "dissolved_oxygen": 9.5,
        "temperature": 22.0
    }
}
```

#### 报警推送

```json
{
    "type": "alert",
    "timestamp": "2024-01-01T12:00:00Z",
    "payload": {
        "id": "alert_001",
        "severity": "high",
        "parameter": "ph",
        "value": 8.5,
        "threshold": 8.0,
        "message": "pH值超出正常范围"
    }
}
```

## 错误处理

### 错误代码

| 错误代码 | HTTP状态码 | 说明 |
|----------|------------|------|
| INVALID_PARAMETER | 400 | 请求参数无效 |
| MISSING_PARAMETER | 400 | 缺少必需参数 |
| UNAUTHORIZED | 401 | 未授权访问 |
| FORBIDDEN | 403 | 禁止访问 |
| NOT_FOUND | 404 | 资源不存在 |
| METHOD_NOT_ALLOWED | 405 | 方法不允许 |
| CONFLICT | 409 | 资源冲突 |
| RATE_LIMITED | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 503 | 服务不可用 |
| SIMULATION_ERROR | 500 | 仿真系统错误 |
| CONTROLLER_ERROR | 500 | 控制器错误 |
| DATABASE_ERROR | 500 | 数据库错误 |

### 错误响应示例

```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "pH值必须在6.0-9.0范围内",
        "details": {
            "parameter": "ph",
            "value": 10.5,
            "valid_range": [6.0, 9.0]
        },
        "suggestion": "请检查输入的pH值是否正确"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
}
```

## 限流和配额

### 限流规则

| 接口类型 | 限制 | 时间窗口 |
|----------|------|----------|
| 认证接口 | 10次 | 1分钟 |
| 查询接口 | 1000次 | 1小时 |
| 控制接口 | 100次 | 1小时 |
| 管理接口 | 50次 | 1小时 |

### 限流响应头

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

### 超限响应

```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMITED",
        "message": "请求频率超出限制",
        "details": {
            "limit": 1000,
            "window": 3600,
            "reset_time": "2024-01-01T13:00:00Z"
        }
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## SDK 和示例

### Python SDK

```python
from water_plant_api import WaterPlantClient

# 创建客户端
client = WaterPlantClient(
    base_url='http://localhost:5000/api/v1',
    username='admin',
    password='password123'
)

# 获取当前水质
water_quality = client.get_current_water_quality()
print(f"当前pH值: {water_quality.ph}")

# 更新控制参数
client.update_controller_parameters(
    controller_type='pid',
    parameters={'kp': 1.2, 'ki': 0.15, 'kd': 0.08},
    setpoint=7.5
)

# 获取历史数据
history = client.get_water_quality_history(
    start='2024-01-01T00:00:00Z',
    end='2024-01-02T00:00:00Z',
    interval='1h'
)
```

### JavaScript SDK

```javascript
import { WaterPlantAPI } from 'water-plant-api';

// 创建API实例
const api = new WaterPlantAPI({
    baseURL: 'http://localhost:5000/api/v1',
    username: 'admin',
    password: 'password123'
});

// 获取当前水质
const waterQuality = await api.getCurrentWaterQuality();
console.log(`当前pH值: ${waterQuality.ph}`);

// 订阅实时数据
const ws = api.createWebSocket();
ws.subscribe('water_quality', (data) => {
    console.log('实时水质数据:', data);
});
```

### cURL 示例

```bash
# 获取访问令牌
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'

# 获取当前水质
curl -X GET http://localhost:5000/api/v1/water-quality/current \
  -H "Authorization: Bearer <token>"

# 更新控制参数
curl -X PUT http://localhost:5000/api/v1/control/parameters \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "controller_type": "pid",
    "parameters": {"kp": 1.2, "ki": 0.15, "kd": 0.08},
    "setpoint": 7.5
  }'
```

---

## 更新日志

### v1.0.0 (2024-01-01)

- 初始版本发布
- 基础水质监控接口
- PID控制器接口
- WebSocket实时数据推送
- 用户认证和授权

### v1.1.0 (计划中)

- 增加设备管理接口
- 支持多种控制算法
- 增强数据分析功能
- 移动端API优化

---

如有问题或建议，请联系：

- 📧 邮箱：api-support@waterplant.com
- 📚 文档：https://docs.waterplant.com
- 🐛 问题报告：https://github.com/your-org/SmartWaterFactory/issues