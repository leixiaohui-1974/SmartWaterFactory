# Smart Water Factory MCP服务指南

## 概述

Smart Water Factory MCP服务是基于Model Context Protocol (MCP)的智能水厂仿真和控制服务，可以被AI大模型（如Claude）直接调用，实现智能化的水处理过程控制和优化。

## 功能特性

### 1. 核心功能
- ✅ **水厂仿真**: 启动、监控、停止水处理过程仿真
- ✅ **控制器管理**: 支持多种控制器（PID、MPC、自适应PID）
- ✅ **参数优化**: 自动调优控制器参数
- ✅ **多用户并发**: 支持多用户同时使用，会话隔离
- ✅ **资源管理**: 配置、数据、模型资源的统一管理

### 2. 接口模式
- **STDIO模式**: 用于Claude Desktop等本地AI助手
- **HTTP模式**: 用于Web应用和REST API集成

## 快速开始

### 1. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装MCP服务额外依赖
pip install -r requirements-mcp.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.mcp .env

# 编辑配置（可选）
nano .env
```

### 3. 启动服务

#### STDIO模式（Claude Desktop）

```bash
python start_mcp_service.py --mode stdio
```

或者直接使用Python模块：

```bash
python -m mcp_service.server --mode stdio
```

#### HTTP模式（Web应用）

```bash
python start_mcp_service.py --mode http --host 0.0.0.0 --port 8000
```

### 4. Claude Desktop集成

将以下配置添加到Claude Desktop的配置文件中：

**位置**:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**配置内容**:

```json
{
  "mcpServers": {
    "smart-water-factory": {
      "command": "python",
      "args": [
        "/path/to/SmartWaterFactory/start_mcp_service.py",
        "--mode",
        "stdio"
      ],
      "env": {
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## MCP工具说明

### 仿真工具

#### 1. start_simulation
启动水厂仿真。

**参数**:
- `steps` (integer, 可选): 仿真步数，默认100，范围1-10000
- `turbidity_setpoint` (number, 可选): 浊度目标值(NTU)，默认2.0
- `do_setpoint` (number, 可选): 溶解氧目标值(mg/L)，默认8.0
- `controller_type` (string, 可选): 控制器类型，可选值: pid, precision_pid, mpc, adaptive
- `enable_faults` (boolean, 可选): 启用传感器故障模拟
- `enable_disturbances` (boolean, 可选): 启用过程扰动

**返回**:
```json
{
  "simulation_id": "uuid",
  "status": "started",
  "message": "Simulation started with 100 steps",
  "parameters": {...}
}
```

**使用示例**（在Claude中）:
```
请启动一个100步的水厂仿真，浊度目标2.0 NTU，溶解氧目标8.0 mg/L
```

#### 2. get_simulation_status
获取仿真状态。

**参数**:
- `simulation_id` (string, 必需): 仿真ID

**返回**:
```json
{
  "simulation_id": "uuid",
  "status": "running",
  "current_step": 45,
  "total_steps": 100,
  "progress": 45.0,
  "elapsed_time": 12.5
}
```

#### 3. stop_simulation
停止运行中的仿真。

**参数**:
- `simulation_id` (string, 必需): 仿真ID

#### 4. get_simulation_results
获取仿真结果数据。

**参数**:
- `simulation_id` (string, 必需): 仿真ID
- `start_step` (integer, 可选): 起始步数
- `end_step` (integer, 可选): 结束步数
- `limit` (integer, 可选): 最大返回数量，默认1000

### 控制工具

#### 1. set_control_parameters
设置控制参数。

**参数**:
- `simulation_id` (string, 必需): 仿真ID
- `parameters` (object, 必需): 控制参数对象

#### 2. get_control_status
获取控制状态。

**参数**:
- `simulation_id` (string, 必需): 仿真ID

### 优化工具

#### 1. optimize_controller
优化控制器参数。

**参数**:
- `method` (string, 可选): 优化方法，可选值: genetic_algorithm, particle_swarm, ziegler_nichols
- `objective` (string, 可选): 优化目标，可选值: speed, stability, balanced
- `max_iterations` (integer, 可选): 最大迭代次数，默认50

**返回**:
```json
{
  "method": "genetic_algorithm",
  "objective": "balanced",
  "optimized_parameters": {
    "Kp": 1.2,
    "Ki": 0.15,
    "Kd": 0.05
  },
  "performance_metrics": {
    "IAE": 125.3,
    "settling_time": 35.4
  }
}
```

#### 2. get_optimization_status
获取优化状态和历史。

## MCP资源说明

### 配置资源

#### config://simulation
仿真配置参数。

```json
{
  "do_saturation": 9.0,
  "do_consumption_rate": 0.02,
  "turbidity_decay_factor": 0.05,
  ...
}
```

#### config://controllers
控制器配置参数。

```json
{
  "dosing_controller": {
    "Kp": 0.12,
    "Ki": 0.001,
    "Kd": 0.5
  },
  ...
}
```

### 数据资源

#### data://session_info
当前会话信息。

```json
{
  "session_id": "uuid",
  "user_id": "user",
  "created_at": "2024-01-01T12:00:00",
  "last_active": "2024-01-01T12:30:00"
}
```

## 使用示例

### 示例1: 运行基础仿真

在Claude中输入：

```
请帮我运行一个水厂仿真，参数如下：
- 仿真步数: 200步
- 浊度目标: 2.5 NTU
- 溶解氧目标: 7.5 mg/L
- 控制器类型: PID

运行后请告诉我仿真状态和初步结果。
```

Claude会调用`start_simulation`工具，然后监控仿真状态，最后获取并分析结果。

### 示例2: 优化控制器参数

```
请使用遗传算法优化PID控制器参数，优化目标是平衡速度和稳定性。
优化完成后，请用优化后的参数运行一个100步的仿真，验证效果。
```

### 示例3: 故障场景分析

```
请运行一个包含传感器故障的仿真场景：
- 步数: 300
- 启用传感器故障
- 启用过程扰动

分析系统在故障情况下的表现，包括控制器响应和系统稳定性。
```

## HTTP API使用

### 创建会话

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "metadata": {"client": "web_app"}
  }'
```

**响应**:
```json
{
  "session_id": "uuid",
  "user_id": "user123",
  "created_at": "2024-01-01T12:00:00"
}
```

### 调用MCP方法

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: your-session-id" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/list",
    "params": {}
  }'
```

### 调用工具

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID": your-session-id" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/call",
    "params": {
      "name": "start_simulation",
      "arguments": {
        "steps": 100,
        "turbidity_setpoint": 2.0,
        "do_setpoint": 8.0
      }
    }
  }'
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| MCP_HOST | HTTP服务器主机地址 | 127.0.0.1 |
| MCP_PORT | HTTP服务器端口 | 8000 |
| MCP_DEBUG | 调试模式 | false |
| MCP_LOG_LEVEL | 日志级别 | INFO |
| MCP_MAX_SESSIONS | 最大并发会话数 | 100 |
| MCP_SESSION_TIMEOUT | 会话超时时间（分钟） | 30 |
| MCP_MAX_SIMULATION_STEPS | 最大仿真步数 | 10000 |

### 资源限制

- 每用户最大并发仿真数: 5
- 单次仿真最大步数: 10000
- API调用速率限制: 60次/分钟
- 会话超时: 30分钟

## 故障排查

### 常见问题

#### 1. 导入错误

**问题**: `ModuleNotFoundError: No module named 'mcp_service'`

**解决**:
```bash
# 确保在项目根目录
cd /path/to/SmartWaterFactory

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-mcp.txt
```

#### 2. 端口占用

**问题**: HTTP模式启动失败，端口被占用

**解决**:
```bash
# 使用不同端口
python start_mcp_service.py --mode http --port 8001

# 或者找到并关闭占用端口的进程
lsof -i :8000
kill -9 <PID>
```

#### 3. 会话过期

**问题**: Session not found错误

**解决**: 会话30分钟未活动会自动清理，需要重新创建会话。

### 日志查看

```bash
# 查看实时日志
tail -f logs/mcp_service.log

# 搜索错误
grep ERROR logs/mcp_service.log

# 查看特定会话的日志
grep "session_id" logs/mcp_service.log
```

## 测试

```bash
# 运行所有测试
python tests/test_mcp_service.py

# 运行特定测试
python -m unittest tests.test_mcp_service.TestMCPModels

# 使用pytest（如果安装）
pytest tests/test_mcp_service.py -v
```

## 性能优化

### 1. 使用uvloop（Linux/macOS）

```bash
pip install uvloop
```

服务会自动检测并使用uvloop以提升性能。

### 2. 调整并发限制

根据服务器资源调整配置：

```bash
# 高性能服务器
export MCP_MAX_SESSIONS=500
export MCP_MAX_CONCURRENT_SIMULATIONS=10

# 低资源环境
export MCP_MAX_SESSIONS=50
export MCP_MAX_CONCURRENT_SIMULATIONS=3
```

## 安全建议

1. **生产环境**: 启用认证 `MCP_ENABLE_AUTH=true`
2. **网络隔离**: HTTP模式不要暴露到公网，使用反向代理
3. **资源限制**: 根据实际情况调整资源配额
4. **日志审计**: 定期检查日志文件

## 下一步计划

- [ ] 添加GraphQL接口支持
- [ ] 实现WebSocket实时数据推送
- [ ] 集成Prometheus监控指标
- [ ] 添加更多优化算法（强化学习等）
- [ ] 支持自定义控制器插件
- [ ] 实现分布式部署支持

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

[项目许可证信息]
