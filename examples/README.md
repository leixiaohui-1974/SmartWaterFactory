# 智能水厂控制系统示例集合

本目录包含了智能水厂控制系统的各种使用示例，帮助开发者快速上手和理解系统功能。

## 📁 示例目录结构

```
examples/
├── 01_basic_simulation/           # 基础仿真示例
│   ├── simple_simulation.py       # 简单仿真运行
│   ├── water_quality_monitoring.py # 水质监控示例
│   └── README.md                  # 基础示例说明
├── 02_tuning_pid_controller/      # PID控制器调优示例
│   ├── pid_tuning_example.py      # PID参数调优
│   ├── performance_analysis.py    # 控制性能分析
│   └── README.md                  # PID调优说明
├── 03_api_integration/            # API集成示例
│   ├── api_client_example.py      # API客户端示例
│   ├── websocket_client.py        # WebSocket客户端
│   └── README.md                  # API集成说明
├── 04_data_analysis/              # 数据分析示例
│   ├── trend_analysis.py          # 趋势分析
│   ├── anomaly_detection.py       # 异常检测
│   └── README.md                  # 数据分析说明
├── 05_custom_controllers/         # 自定义控制器示例
│   ├── fuzzy_controller.py        # 模糊控制器
│   ├── adaptive_controller.py     # 自适应控制器
│   └── README.md                  # 自定义控制器说明
└── README.md                      # 本文件
```

## 🚀 快速开始

### 环境准备

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境**
   ```bash
   # 复制配置文件
   cp config/development.json.example config/development.json
   
   # 根据需要修改配置
   vim config/development.json
   ```

3. **启动系统**
   ```bash
   # 启动基础仿真
   python run_simulation.py
   
   # 或启动带API服务器的仿真
   python run_simulation.py --api-server
   ```

### 运行示例

每个示例目录都包含独立的示例代码，可以直接运行：

```bash
# 运行基础仿真示例
cd examples/01_basic_simulation
python simple_simulation.py

# 运行PID调优示例
cd examples/02_tuning_pid_controller
python pid_tuning_example.py

# 运行API客户端示例
cd examples/03_api_integration
python api_client_example.py
```

## 📚 详细示例说明

### 1. 基础仿真示例 (01_basic_simulation)

**适用人群**: 初学者

- **simple_simulation.py**: 演示如何创建和运行基本的水厂仿真
  - 初始化仿真环境
  - 配置基本参数
  - 运行仿真循环
  - 数据收集和可视化

- **water_quality_monitoring.py**: 展示水质监控功能
  - 实时水质数据采集
  - 阈值监控和报警
  - 历史数据记录
  - 趋势分析

### 2. PID控制器调优示例 (02_tuning_pid_controller)

**适用人群**: 中级用户

- **pid_tuning_example.py**: PID参数优化实战
  - 自动调优算法
  - 手动调优指导
  - 性能指标评估
  - 参数敏感性分析

- **performance_analysis.py**: 控制性能深度分析
  - 阶跃响应测试
  - 频域分析
  - 稳定性评估
  - 鲁棒性测试

### 3. API集成示例 (03_api_integration)

**适用人群**: 开发者

- **api_client_example.py**: 完整的API客户端实现
  - 用户认证和授权
  - RESTful API调用
  - 数据获取和控制
  - 错误处理和重试

- **websocket_client.py**: 实时通信示例
  - WebSocket连接管理
  - 实时数据订阅
  - 命令发送和响应
  - 连接断线重连

### 4. 数据分析示例 (04_data_analysis)

**适用人群**: 数据分析师

- **trend_analysis.py**: 数据趋势分析
  - 时间序列分析
  - 季节性检测
  - 预测模型
  - 可视化展示

- **anomaly_detection.py**: 异常检测算法
  - 统计方法检测
  - 机器学习方法
  - 实时异常监控
  - 报警机制

### 5. 自定义控制器示例 (05_custom_controllers)

**适用人群**: 高级用户

- **fuzzy_controller.py**: 模糊控制器实现
  - 模糊规则设计
  - 隶属函数定义
  - 推理引擎
  - 性能对比

- **adaptive_controller.py**: 自适应控制器
  - 参数自适应算法
  - 模型辨识
  - 在线学习
  - 稳定性保证

## 🛠️ 开发工具

### 调试工具

```bash
# 启用调试模式
export DEBUG=1
python examples/01_basic_simulation/simple_simulation.py

# 使用性能分析
python -m cProfile examples/02_tuning_pid_controller/pid_tuning_example.py
```

### 可视化工具

```bash
# 启动可视化界面
python -m water_plant_controller.visualization.dashboard

# 生成性能报告
python scripts/generate_report.py --input data/simulation_results.json
```

## 🧪 测试建议

### 单元测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定示例的测试
python -m pytest tests/examples/test_basic_simulation.py

# 生成覆盖率报告
python -m pytest --cov=water_plant_controller tests/
```

### 集成测试

```bash
# 端到端测试
python tests/integration/test_full_system.py

# API测试
python tests/integration/test_api_endpoints.py
```

## ⚙️ 配置管理

### 环境配置

```bash
# 开发环境
export ENVIRONMENT=development

# 生产环境
export ENVIRONMENT=production

# 测试环境
export ENVIRONMENT=testing
```

### 配置文件

- `config/development.json`: 开发环境配置
- `config/production.json`: 生产环境配置
- `config/testing.json`: 测试环境配置

## 📖 进阶学习

### 推荐阅读

1. **控制理论基础**
   - PID控制原理
   - 现代控制理论
   - 鲁棒控制

2. **水处理工艺**
   - 水质参数
   - 处理流程
   - 设备原理

3. **系统集成**
   - SCADA系统
   - 工业通信协议
   - 数据采集

### 在线资源

- [项目文档](../docs/README.md)
- [API参考](../docs/api.md)
- [开发者指南](../docs/developer_guide.md)
- [部署指南](../docs/deployment_guide.md)

## 🤝 贡献指南

### 添加新示例

1. **创建示例目录**
   ```bash
   mkdir examples/06_your_example
   cd examples/06_your_example
   ```

2. **编写示例代码**
   - 遵循项目编码规范
   - 添加详细注释
   - 包含错误处理

3. **创建README文档**
   - 示例目的和适用场景
   - 运行步骤
   - 预期结果
   - 故障排除

4. **添加测试**
   ```bash
   # 创建测试文件
   touch tests/examples/test_your_example.py
   ```

### 提交流程

1. **Fork项目**
2. **创建特性分支**
   ```bash
   git checkout -b feature/new-example
   ```
3. **提交更改**
   ```bash
   git commit -m "Add new example: your_example"
   ```
4. **推送分支**
   ```bash
   git push origin feature/new-example
   ```
5. **创建Pull Request**

## 📞 获取帮助

### 常见问题

**Q: 示例运行失败怎么办？**
A: 检查依赖安装、配置文件、环境变量设置

**Q: 如何修改仿真参数？**
A: 编辑配置文件或在代码中直接修改参数

**Q: 如何添加新的传感器？**
A: 参考05_custom_controllers示例，扩展传感器类

### 技术支持

- **GitHub Issues**: [提交问题](https://github.com/your-repo/issues)
- **讨论区**: [参与讨论](https://github.com/your-repo/discussions)
- **邮件支持**: support@smartwaterfactory.com

---

**开始您的智能水厂控制系统开发之旅！** 🚀
