# 智能水厂控制系统部署指南

## 概述

本指南提供了智能水厂控制系统的完整部署方案，支持多种部署方式：
- Docker Compose 部署（推荐用于开发和测试）
- Kubernetes 部署（推荐用于生产环境）
- 本地开发环境部署

## 系统要求

### 最低硬件要求
- CPU: 2核心
- 内存: 4GB RAM
- 存储: 20GB 可用空间
- 网络: 稳定的网络连接

### 推荐硬件配置
- CPU: 4核心或更多
- 内存: 8GB RAM 或更多
- 存储: 50GB SSD
- 网络: 千兆网络

### 软件依赖
- Python 3.8+
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.20+ (生产环境)
- PostgreSQL 13+
- Redis 6.0+

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/SmartWaterFactory.git
cd SmartWaterFactory
```

### 2. 环境配置

复制并编辑配置文件：

```bash
# 开发环境
cp config/development.json.example config/development.json

# 生产环境
cp config/production.json.example config/production.json
```

### 3. 选择部署方式

#### Docker Compose 部署（推荐）

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f water-plant-app
```

#### 本地开发部署

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python run_simulation.py --api-server
```

## Docker Compose 部署详解

### 服务架构

```yaml
# docker-compose.yml 包含以下服务：
- water-plant-app: 主应用服务
- postgres: PostgreSQL 数据库
- redis: Redis 缓存
- nginx: 反向代理和负载均衡
- prometheus: 监控数据收集
- grafana: 监控数据可视化
- fluentd: 日志收集
```

### 部署步骤

1. **环境准备**
   ```bash
   # 创建必要的目录
   mkdir -p logs data config
   
   # 设置权限
   chmod 755 logs data
   ```

2. **配置文件设置**
   ```bash
   # 编辑数据库配置
   vim config/production.json
   
   # 设置环境变量
   export POSTGRES_PASSWORD=your_secure_password
   export JWT_SECRET=your_jwt_secret
   ```

3. **启动服务**
   ```bash
   # 后台启动所有服务
   docker-compose up -d
   
   # 等待服务启动完成
   sleep 30
   
   # 检查服务健康状态
   curl http://localhost:5000/health
   ```

4. **验证部署**
   ```bash
   # 检查所有容器状态
   docker-compose ps
   
   # 测试 API 接口
   curl http://localhost:5000/api/status
   
   # 访问监控界面
   # Grafana: http://localhost:3000 (admin/admin)
   # Prometheus: http://localhost:9090
   ```

### 常用命令

```bash
# 查看日志
docker-compose logs -f [service_name]

# 重启服务
docker-compose restart [service_name]

# 更新服务
docker-compose pull
docker-compose up -d

# 停止所有服务
docker-compose down

# 完全清理（包括数据卷）
docker-compose down -v
```

## Kubernetes 部署详解

### 集群要求

- Kubernetes 1.20+
- kubectl 配置正确
- 至少 3 个工作节点（生产环境）
- 支持 LoadBalancer 类型的服务

### 部署步骤

1. **创建命名空间**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **应用配置和密钥**
   ```bash
   # 更新密钥（使用实际的加密值）
   kubectl create secret generic water-plant-secrets \
     --from-literal=database-url="postgresql://user:pass@host:5432/db" \
     --from-literal=redis-url="redis://host:6379/0" \
     --from-literal=jwt-secret="your-secret-key" \
     -n water-plant
   
   # 应用配置映射
   kubectl apply -f k8s/configmap.yaml
   ```

3. **部署应用**
   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```

4. **验证部署**
   ```bash
   # 检查 Pod 状态
   kubectl get pods -n water-plant
   
   # 检查服务
   kubectl get services -n water-plant
   
   # 查看日志
   kubectl logs -f deployment/water-plant-app -n water-plant
   ```

### 扩缩容

```bash
# 手动扩容
kubectl scale deployment water-plant-app --replicas=5 -n water-plant

# 自动扩缩容（HPA）
kubectl autoscale deployment water-plant-app \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n water-plant
```

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/water-plant-app \
  water-plant-app=water-plant-app:v2.0 \
  -n water-plant

# 查看更新状态
kubectl rollout status deployment/water-plant-app -n water-plant

# 回滚到上一版本
kubectl rollout undo deployment/water-plant-app -n water-plant
```

## 监控和告警

### Prometheus 配置

监控指标包括：
- 应用性能指标
- 系统资源使用率
- 水质监控数据
- 控制系统状态

### Grafana 仪表板

预配置的仪表板：
- 系统概览
- 应用性能
- 水质监控
- 告警状态

访问地址：http://localhost:3000
默认账号：admin/admin

### 告警规则

主要告警项：
- 应用不可用
- CPU/内存使用率过高
- 磁盘空间不足
- 数据库连接失败
- 水质参数异常

## 备份和恢复

### 自动备份

使用提供的备份脚本：

```bash
# 完整备份
python scripts/backup.py --action full-backup --env prod

# 仅备份数据库
python scripts/backup.py --action backup-db --env prod

# 设置定时备份
python scripts/backup.py --action schedule
```

### 手动备份

```bash
# 数据库备份
pg_dump -h localhost -U postgres waterplant > backup.sql

# 配置文件备份
tar -czf config_backup.tar.gz config/

# 数据文件备份
tar -czf data_backup.tar.gz data/
```

### 恢复操作

```bash
# 恢复数据库
python scripts/backup.py --action restore-db --file /path/to/backup.sql

# 手动恢复
psql -h localhost -U postgres waterplant < backup.sql
```

## 安全配置

### 网络安全

1. **防火墙配置**
   ```bash
   # 仅开放必要端口
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 22/tcp
   ufw enable
   ```

2. **SSL/TLS 配置**
   - 使用 Let's Encrypt 证书
   - 配置 HTTPS 重定向
   - 启用 HSTS

### 应用安全

1. **身份认证**
   - JWT 令牌认证
   - 密码强度要求
   - 登录失败限制

2. **API 安全**
   - 请求频率限制
   - 输入验证
   - SQL 注入防护

### 数据安全

1. **数据库安全**
   - 加密连接
   - 定期备份
   - 访问权限控制

2. **敏感数据保护**
   - 密钥管理
   - 数据加密
   - 审计日志

## 性能优化

### 应用优化

1. **缓存策略**
   - Redis 缓存配置
   - 查询结果缓存
   - 静态资源缓存

2. **数据库优化**
   - 索引优化
   - 查询优化
   - 连接池配置

### 系统优化

1. **资源配置**
   ```yaml
   # Kubernetes 资源限制
   resources:
     requests:
       memory: "512Mi"
       cpu: "250m"
     limits:
       memory: "1Gi"
       cpu: "500m"
   ```

2. **负载均衡**
   - Nginx 配置优化
   - 健康检查配置
   - 会话保持

## 故障排除

### 常见问题

1. **应用启动失败**
   ```bash
   # 检查日志
   docker-compose logs water-plant-app
   
   # 检查配置
   python -c "import json; print(json.load(open('config/production.json')))"
   ```

2. **数据库连接失败**
   ```bash
   # 测试数据库连接
   psql -h localhost -U postgres -d waterplant
   
   # 检查数据库状态
   docker-compose exec postgres pg_isready
   ```

3. **性能问题**
   ```bash
   # 查看资源使用
   docker stats
   
   # 分析慢查询
   kubectl logs -f deployment/water-plant-app -n water-plant | grep "slow"
   ```

### 日志分析

```bash
# 应用日志
tail -f logs/water_plant.log

# 错误日志
grep "ERROR" logs/water_plant.log

# 性能日志
grep "performance" logs/water_plant.log
```

### 健康检查

```bash
# 使用监控脚本
python scripts/monitor.py --mode health

# 手动检查
curl http://localhost:5000/health
curl http://localhost:5000/health/database
```

## 维护操作

### 定期维护

1. **系统更新**
   ```bash
   # 更新系统包
   apt update && apt upgrade
   
   # 更新 Docker 镜像
   docker-compose pull
   docker-compose up -d
   ```

2. **数据清理**
   ```bash
   # 清理旧日志
   find logs/ -name "*.log" -mtime +30 -delete
   
   # 清理旧备份
   python scripts/backup.py --action cleanup
   ```

3. **性能监控**
   ```bash
   # 生成性能报告
   python scripts/monitor.py --mode metrics --output json > performance_report.json
   ```

### 版本升级

1. **准备工作**
   - 备份当前数据
   - 阅读升级说明
   - 准备回滚计划

2. **升级步骤**
   ```bash
   # 停止服务
   docker-compose down
   
   # 更新代码
   git pull origin main
   
   # 重新构建
   docker-compose build
   
   # 启动服务
   docker-compose up -d
   ```

3. **验证升级**
   ```bash
   # 检查服务状态
   docker-compose ps
   
   # 运行健康检查
   python scripts/monitor.py --mode health
   ```

## 联系支持

如果遇到问题，请通过以下方式获取支持：

- 📧 邮箱：support@waterplant.com
- 📱 电话：+86-xxx-xxxx-xxxx
- 💬 在线支持：https://support.waterplant.com
- 📖 文档：https://docs.waterplant.com
- 🐛 问题报告：https://github.com/your-org/SmartWaterFactory/issues

## 附录

### A. 配置文件模板

详见 `config/` 目录下的示例文件。

### B. API 接口文档

详见 `docs/api.md`。

### C. 监控指标说明

详见 `docs/monitoring.md`。

### D. 安全检查清单

详见 `docs/security_checklist.md`。