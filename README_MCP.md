# Smart Water Factory - MCP Service

> 基于Model Context Protocol的智能水厂仿真和控制服务 - 让AI大模型直接操控水处理系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/protocol-MCP%202024--11--05-green)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌟 项目亮点

- **🤖 AI原生**: 完整实现MCP协议，可被Claude等AI大模型直接调用
- **⚡ 多用户并发**: 会话隔离，支持数百用户同时使用
- **🎯 生产就绪**: 完善的错误处理、日志、监控和部署方案
- **🔧 灵活接口**: 支持STDIO、HTTP等多种连接方式
- **📊 实时仿真**: 高精度水处理过程仿真和控制
- **🚀 可扩展**: 易于添加新工具和功能

## 📋 功能特性

### 核心功能

| 功能类别 | 工具名称 | 说明 |
|---------|---------|------|
| **仿真管理** | `start_simulation` | 启动水厂仿真 |
| | `get_simulation_status` | 获取仿真状态 |
| | `stop_simulation` | 停止仿真 |
| | `get_simulation_results` | 获取仿真结果 |
| **控制器** | `set_control_parameters` | 设置控制参数 |
| | `get_control_status` | 获取控制状态 |
| **优化** | `optimize_controller` | 自动参数调优 |
| | `get_optimization_status` | 获取优化状态 |

### 资源类型

- **config://**: 配置资源（仿真参数、控制器配置）
- **data://**: 数据资源（会话信息、实时数据）
- **model://**: 模型资源（训练好的控制器、优化结果）

## 🚀 快速开始

### 前置要求

- Python 3.8+
- pip包管理器

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/SmartWaterFactory.git
cd SmartWaterFactory

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-mcp.txt

# 配置环境变量（可选）
cp .env.mcp .env
```

### 启动服务

#### STDIO模式（推荐用于Claude Desktop）

```bash
python start_mcp_service.py --mode stdio
```

#### HTTP模式（推荐用于Web应用）

```bash
python start_mcp_service.py --mode http --host 0.0.0.0 --port 8000
```

## 🔌 集成Claude Desktop

### 配置步骤

1. 打开Claude Desktop配置文件：
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. 添加MCP服务配置：

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

3. 重启Claude Desktop

4. 在对话中尝试：

```
请帮我运行一个100步的水厂仿真，浊度目标2.0 NTU，溶解氧目标8.0 mg/L
```

## 💡 使用示例

### 示例1: 基础仿真

```
用户: 请启动一个水厂仿真，参数如下：
- 仿真步数: 200步
- 浊度目标: 2.5 NTU
- 溶解氧目标: 7.5 mg/L
- 使用PID控制器

Claude: 好的，我现在为您启动仿真...
[调用 start_simulation 工具]
仿真已启动，ID: abc-123-def
当前进度: 0/200 步

[定期查询状态]
仿真进行中: 50/200 步 (25%)
仿真进行中: 100/200 步 (50%)
...
仿真完成！

[获取并分析结果]
根据仿真结果，系统表现良好：
- 平均浊度: 2.51 NTU (目标 2.5)
- 平均溶解氧: 7.48 mg/L (目标 7.5)
- 调节时间: 45步
- 超调量: 8.2%
```

### 示例2: 参数优化

```
用户: 请使用遗传算法优化PID控制器参数，目标是平衡速度和稳定性

Claude: 我将使用遗传算法为您优化PID参数...
[调用 optimize_controller 工具]

优化完成！结果如下：
- 优化方法: genetic_algorithm
- 优化目标: balanced
- 最优参数:
  - Kp: 1.2
  - Ki: 0.15
  - Kd: 0.05
- 性能指标:
  - IAE: 125.3
  - 调节时间: 35.4步
  - 超调量: 5.1%

相比初始参数，调节时间减少了25%，超调量降低了40%。
```

## 🏗️ 架构设计

```
mcp_service/
├── config/           # 配置管理
│   ├── mcp_config.py
│   └── __init__.py
├── models/           # 数据模型
│   ├── schemas.py
│   └── __init__.py
├── protocol/         # MCP协议处理
│   ├── handler.py
│   └── __init__.py
├── registry/         # 工具注册
│   ├── tool_registry.py
│   └── __init__.py
├── session/          # 会话管理
│   ├── manager.py
│   └── __init__.py
├── tools/            # 工具实现
│   ├── simulation_tools.py
│   ├── control_tools.py
│   ├── optimization_tools.py
│   └── __init__.py
├── resources/        # 资源提供
│   ├── provider.py
│   └── __init__.py
└── server.py         # 服务器主入口
```

## 🧪 测试

```bash
# 运行所有测试
python tests/test_mcp_service.py

# 运行特定测试
python -m unittest tests.test_mcp_service.TestMCPModels -v

# 使用pytest
pytest tests/test_mcp_service.py -v --cov=mcp_service
```

## 📚 文档

- [MCP服务使用指南](docs/MCP_SERVICE_GUIDE.md) - 完整的功能说明和API文档
- [部署指南](docs/MCP_DEPLOYMENT.md) - Docker、K8s等部署方案
- [开发指南](docs/developer_guide.md) - 原有项目的开发文档

## 🔧 配置选项

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MCP_HOST` | HTTP服务器地址 | 127.0.0.1 |
| `MCP_PORT` | HTTP服务器端口 | 8000 |
| `MCP_LOG_LEVEL` | 日志级别 | INFO |
| `MCP_MAX_SESSIONS` | 最大并发会话数 | 100 |
| `MCP_SESSION_TIMEOUT` | 会话超时（分钟） | 30 |
| `MCP_MAX_SIMULATION_STEPS` | 单次仿真最大步数 | 10000 |

完整配置见 [.env.mcp](.env.mcp)

## 🐳 Docker部署

```bash
# 构建镜像
docker build -f Dockerfile.mcp -t smart-water-factory-mcp:latest .

# 运行容器
docker run -d \
  --name mcp-service \
  -p 8000:8000 \
  -e MCP_MAX_SESSIONS=200 \
  smart-water-factory-mcp:latest

# 使用Docker Compose
docker-compose -f docker-compose.mcp.yml up -d
```

## ☸️ Kubernetes部署

```bash
# 部署到K8s
kubectl apply -f k8s/mcp-deployment.yaml

# 查看状态
kubectl get pods -l app=mcp-service

# 扩容
kubectl scale deployment mcp-service --replicas=5
```

## 📊 监控和运维

### 健康检查

```bash
# HTTP模式
curl http://localhost:8000/health

# 响应示例
{
  "status": "healthy",
  "service": "SmartWaterFactory MCP Service",
  "version": "1.0.0"
}
```

### 日志查看

```bash
# 实时日志
tail -f logs/mcp_service.log

# 搜索错误
grep ERROR logs/mcp_service.log

# Docker日志
docker logs -f mcp-service
```

### 性能指标

服务提供以下关键指标：
- 活跃会话数
- 工具调用统计
- 仿真执行时间
- 错误率和成功率

## 🤝 贡献

欢迎贡献代码、报告问题或提出新功能建议！

### 开发流程

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 代码规范

- 遵循PEP 8规范
- 添加类型注解
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP协议规范
- [Anthropic Claude](https://www.anthropic.com/claude) - AI助手
- 所有贡献者

## 📞 联系方式

- 项目主页: https://github.com/yourusername/SmartWaterFactory
- 问题反馈: https://github.com/yourusername/SmartWaterFactory/issues
- 邮箱: your.email@example.com

## 🗺️ 路线图

- [x] MCP核心协议实现
- [x] 多用户会话管理
- [x] 基础仿真工具
- [x] 控制器管理工具
- [x] 参数优化工具
- [x] HTTP/STDIO双模式
- [x] Docker/K8s部署
- [ ] GraphQL接口
- [ ] WebSocket实时推送
- [ ] Prometheus指标导出
- [ ] 更多优化算法
- [ ] 自定义控制器插件系统
- [ ] 分布式仿真支持

---

**让AI直接操控工业过程 - 开启智能制造新篇章！** 🚀
