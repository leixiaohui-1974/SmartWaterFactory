# 更新日志 (Changelog)

本文档记录 SmartWaterFactory 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Added - 新增
- 创建 `requirements-dev.txt` - 完整的开发依赖配置
  - 测试框架 (pytest, coverage)
  - 代码质量工具 (black, pylint, mypy, flake8)
  - 安全检查工具 (bandit, safety)
  - 文档生成工具 (sphinx)
  - 开发工具 (ipython, jupyter)

- 创建 `setup.py` - 支持通过 pip 安装项目
  - 定义包元数据和依赖关系
  - 配置命令行入口点
  - 支持开发模式安装 (`pip install -e .`)

- 创建 `.env.example` - 环境变量配置模板
  - 完整的配置项说明和示例
  - 应用、API、数据库、日志等全面配置
  - 安全提醒和最佳实践

- 创建 `docker-compose.full.yml` - 完整版 Docker Compose 配置
  - 包含所有服务（数据库、缓存、监控等）
  - 保留原有的完整配置作为可选项

- 创建 `CHANGELOG.md` - 项目变更日志
- 创建 `PROJECT_ANALYSIS_REPORT.md` - 完整的项目分析报告

### Changed - 变更

- **重大变更**: `requirements.txt` - 补充所有缺失的依赖
  - 添加 Flask 及相关组件 (flask-cors, flask-socketio, python-socketio)
  - 添加认证和安全组件 (PyJWT>=2.8.0, bcrypt>=4.0.0)
  - 添加 HTTP 客户端 (requests>=2.31.0)
  - 添加数据库支持 (redis>=5.0.0, psycopg2-binary>=2.9.0)
  - 添加任务队列 (celery>=5.3.0)
  - 添加数据处理 (pandas>=2.0.0)
  - 更新 matplotlib 和 numpy 版本要求

- **重大变更**: `.gitignore` - 大幅扩展忽略规则
  - 添加虚拟环境目录 (venv/, env/, .venv/)
  - 添加 IDE 配置 (.vscode/, .idea/, *.swp)
  - 添加环境变量文件 (.env, .env.local)
  - 添加构建产物 (dist/, build/, *.egg-info/)
  - 添加测试缓存 (.pytest_cache/, .coverage, htmlcov/)
  - 添加日志文件 (*.log, logs/)
  - 添加数据库文件 (*.db, *.sqlite)
  - 添加 SSL 证书目录

- **安全变更**: `utils/api_server.py` - 修复硬编码密码问题
  - 从环境变量读取用户密码配置
  - 实现 bcrypt 密码哈希存储
  - 修改 `UserCredentials` 类使用 `password_hash` 而非明文密码
  - 添加密码验证方法 `verify_password()`
  - 添加默认密码使用警告日志
  - 改进认证流程的安全性

- **Docker 优化**: `Dockerfile`
  - 安装 curl 用于健康检查
  - 修复健康检查命令（使用 curl 替代 requests）
  - 更新健康检查端点为 `/api/health`

- **Docker Compose 简化**: `docker-compose.yml`
  - 简化为仅包含核心服务
  - 将数据库、Redis、监控服务改为可选（注释形式）
  - 添加详细的使用说明和配置注释
  - 改进环境变量配置
  - 添加健康检查配置

### Security - 安全

- 🔒 **移除硬编码密码** - 所有用户密码现在通过环境变量配置
- 🔒 **密码哈希存储** - 使用 bcrypt 对密码进行哈希存储
- 🔒 **环境变量隔离** - 敏感信息通过 .env 文件管理（不提交到仓库）
- 🔒 **安全警告** - 使用默认密码时会输出警告日志
- 🔒 **HTTPS 支持** - docker-compose 配置包含 SSL 证书目录

### Fixed - 修复

- 修复 `requirements.txt` 缺少关键依赖导致无法安装的问题
- 修复 `Dockerfile` 健康检查依赖 requests 库但未安装的问题
- 修复 `utils/api_server.py` 硬编码密码的安全隐患
- 修复 `.gitignore` 过于简单导致提交不必要文件的问题
- 修复 `docker-compose.yml` 配置过于复杂且部分服务未实现的问题

---

## [1.0.0] - 2025-10-22 (之前版本)

### 项目初始功能

#### 核心功能
- ✅ 水处理过程仿真系统
- ✅ 多种控制策略实现
  - PID 控制器
  - 精确 PID 控制器（前馈 + 约束）
  - 自适应 PID 控制器
  - MPC 模型预测控制器
  - 开关控制器
- ✅ 传感器融合和容错
  - 卡尔曼滤波
  - 双传感器冗余
  - 故障检测和降级
- ✅ REST API + WebSocket 服务
- ✅ 可视化工具
- ✅ 17 个完整示例教程

#### 工程化
- ✅ Docker 容器化支持
- ✅ Kubernetes 部署配置
- ✅ 完整的测试套件（17个测试文件）
- ✅ 详细的中英文文档（42个文档）
- ✅ 多环境配置管理
- ✅ 性能监控工具
- ✅ 日志系统

---

## 升级指南

### 从旧版本升级

#### 1. 更新依赖

```bash
# 安装新的依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt

# 或者使用 setup.py 安装
pip install -e .
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置安全的密码
# 重要：必须修改以下配置
# - SECRET_KEY
# - ADMIN_PASSWORD
# - OPERATOR_PASSWORD
# - USER_PASSWORD
```

#### 3. 数据迁移

如果你使用了旧版本的用户数据，需要注意：
- 用户密码现在使用 bcrypt 哈希存储
- 建议重置所有用户密码

#### 4. Docker 部署更新

```bash
# 使用简化版配置（推荐）
docker-compose up -d

# 使用完整版配置（包含数据库、监控等）
docker-compose -f docker-compose.full.yml up -d
```

---

## 破坏性变更 (Breaking Changes)

### v1.0.0 → Unreleased

1. **用户认证系统变更** (utils/api_server.py)
   - `UserCredentials.password` 字段改名为 `password_hash`
   - 密码验证方法从直接比较改为哈希验证
   - 如果你的代码直接访问了 `password` 字段，需要更新

2. **环境变量要求**
   - 生产环境现在强制要求通过环境变量配置密码
   - 不再支持硬编码的默认密码（开发环境除外）

3. **Docker Compose 配置**
   - 默认的 `docker-compose.yml` 已简化，仅包含核心服务
   - 如需完整服务，使用 `docker-compose.full.yml`

---

## 贡献者

感谢以下贡献者：
- Claude AI - 项目分析和基础设施改进

---

## 相关链接

- [项目分析报告](PROJECT_ANALYSIS_REPORT.md)
- [完整文档](DOCUMENTATION.md)
- [README](README.md)
- [GitHub 仓库](https://github.com/leixiaohui-1974/SmartWaterFactory)

---

**注意**: 本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。
