# 智能水厂控制系统运维手册

## 目录

1. [系统概述](#系统概述)
2. [日常运维](#日常运维)
3. [监控告警](#监控告警)
4. [故障处理](#故障处理)
5. [性能调优](#性能调优)
6. [安全管理](#安全管理)
7. [备份恢复](#备份恢复)
8. [变更管理](#变更管理)
9. [应急预案](#应急预案)
10. [运维工具](#运维工具)

## 系统概述

### 系统架构

智能水厂控制系统采用微服务架构，主要组件包括：

- **应用层**：水厂控制应用、API 服务
- **数据层**：PostgreSQL 数据库、Redis 缓存
- **监控层**：Prometheus、Grafana、日志系统
- **基础设施层**：Docker、Kubernetes、Nginx

### 服务清单

| 服务名称 | 端口 | 用途 | 健康检查 |
|---------|------|------|----------|
| water-plant-app | 5000 | 主应用服务 | /health |
| postgres | 5432 | 数据库 | pg_isready |
| redis | 6379 | 缓存 | ping |
| nginx | 80/443 | 反向代理 | /nginx_status |
| prometheus | 9090 | 监控数据收集 | /-/healthy |
| grafana | 3000 | 监控可视化 | /api/health |

## 日常运维

### 每日检查清单

#### 系统状态检查

```bash
# 1. 检查所有服务状态
python scripts/monitor.py --mode health

# 2. 检查系统资源使用
python scripts/monitor.py --mode metrics

# 3. 检查应用日志
tail -f logs/water_plant.log | grep -E "ERROR|CRITICAL"

# 4. 检查数据库连接
psql -h localhost -U postgres -d waterplant -c "SELECT 1;"

# 5. 检查 Redis 状态
redis-cli ping
```

#### 性能指标检查

```bash
# CPU 使用率（应 < 80%）
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

# 内存使用率（应 < 85%）
free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'

# 磁盘使用率（应 < 90%）
df -h | grep -E "/$|/data|/logs" | awk '{print $5}'

# 网络连接数
netstat -an | grep :5000 | wc -l
```

#### 业务指标检查

```bash
# 水质参数检查
curl -s http://localhost:5000/api/water-quality/current | jq '.'

# 控制系统状态
curl -s http://localhost:5000/api/control/status | jq '.'

# API 响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/health
```

### 每周维护任务

#### 系统清理

```bash
# 1. 清理旧日志文件
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
find logs/ -name "*.log.gz" -mtime +30 -delete

# 2. 清理 Docker 资源
docker system prune -f
docker volume prune -f

# 3. 清理临时文件
find /tmp -name "water_plant_*" -mtime +1 -delete
```

#### 数据库维护

```bash
# 1. 数据库统计信息更新
psql -h localhost -U postgres -d waterplant -c "ANALYZE;"

# 2. 检查数据库大小
psql -h localhost -U postgres -d waterplant -c "
  SELECT pg_size_pretty(pg_database_size('waterplant')) as db_size;"

# 3. 检查慢查询
psql -h localhost -U postgres -d waterplant -c "
  SELECT query, mean_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC LIMIT 10;"
```

#### 安全检查

```bash
# 1. 检查失败登录尝试
grep "authentication failed" logs/water_plant.log | tail -20

# 2. 检查异常 API 调用
grep "rate limit exceeded" logs/water_plant.log | tail -10

# 3. 检查系统用户
who
last | head -20
```

### 每月维护任务

#### 系统更新

```bash
# 1. 系统包更新
sudo apt update && sudo apt list --upgradable

# 2. Docker 镜像更新
docker-compose pull

# 3. Python 依赖更新检查
pip list --outdated
```

#### 容量规划

```bash
# 1. 数据增长趋势分析
psql -h localhost -U postgres -d waterplant -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
  FROM pg_tables 
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# 2. 日志增长趋势
du -sh logs/* | sort -hr

# 3. 备份空间使用
du -sh backups/* | sort -hr
```

## 监控告警

### 告警级别定义

| 级别 | 描述 | 响应时间 | 处理方式 |
|------|------|----------|----------|
| Critical | 系统不可用 | 5分钟 | 立即处理 |
| Warning | 性能下降 | 30分钟 | 计划处理 |
| Info | 一般信息 | 24小时 | 记录跟踪 |

### 关键监控指标

#### 系统指标

```yaml
# CPU 使用率
- alert: HighCPUUsage
  expr: cpu_usage_percent > 80
  for: 5m
  severity: warning

# 内存使用率
- alert: HighMemoryUsage
  expr: memory_usage_percent > 85
  for: 5m
  severity: warning

# 磁盘使用率
- alert: HighDiskUsage
  expr: disk_usage_percent > 90
  for: 5m
  severity: critical
```

#### 应用指标

```yaml
# 应用可用性
- alert: ApplicationDown
  expr: up{job="water-plant-app"} == 0
  for: 1m
  severity: critical

# API 响应时间
- alert: HighResponseTime
  expr: http_request_duration_seconds > 5
  for: 5m
  severity: warning

# 错误率
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  for: 5m
  severity: warning
```

#### 业务指标

```yaml
# 水质异常
- alert: WaterQualityAbnormal
  expr: water_ph < 6.5 or water_ph > 8.5
  for: 2m
  severity: critical

# 控制系统故障
- alert: ControlSystemFailure
  expr: pump_status == 0 and pump_should_run == 1
  for: 1m
  severity: critical
```

### 告警处理流程

#### Critical 级别告警

1. **立即响应**（5分钟内）
   - 确认告警真实性
   - 评估影响范围
   - 启动应急预案

2. **问题定位**
   ```bash
   # 检查系统状态
   python scripts/monitor.py --mode health
   
   # 查看错误日志
   tail -100 logs/water_plant_error.log
   
   # 检查资源使用
   top -bn1
   df -h
   ```

3. **快速恢复**
   ```bash
   # 重启服务
   docker-compose restart water-plant-app
   
   # 或者回滚到上一版本
   kubectl rollout undo deployment/water-plant-app -n water-plant
   ```

#### Warning 级别告警

1. **分析原因**
   - 查看监控图表
   - 分析历史趋势
   - 确定根本原因

2. **制定解决方案**
   - 评估解决方案
   - 制定实施计划
   - 准备回滚方案

3. **实施修复**
   - 在维护窗口执行
   - 监控修复效果
   - 更新文档

## 故障处理

### 常见故障及处理方法

#### 应用无法启动

**症状**：应用容器启动失败或立即退出

**排查步骤**：
```bash
# 1. 查看容器日志
docker-compose logs water-plant-app

# 2. 检查配置文件
python -c "import json; json.load(open('config/production.json'))"

# 3. 检查端口占用
netstat -tlnp | grep :5000

# 4. 检查文件权限
ls -la logs/ data/ config/
```

**解决方案**：
```bash
# 修复配置文件
vim config/production.json

# 修复权限
chmod 755 logs/ data/
chown -R app:app logs/ data/

# 重启服务
docker-compose restart water-plant-app
```

#### 数据库连接失败

**症状**：应用无法连接到数据库

**排查步骤**：
```bash
# 1. 检查数据库状态
docker-compose exec postgres pg_isready

# 2. 测试连接
psql -h localhost -U postgres -d waterplant

# 3. 检查网络
telnet localhost 5432

# 4. 查看数据库日志
docker-compose logs postgres
```

**解决方案**：
```bash
# 重启数据库
docker-compose restart postgres

# 检查连接池配置
vim config/production.json

# 重建数据库连接
docker-compose restart water-plant-app
```

#### 内存不足

**症状**：系统响应缓慢，OOM 错误

**排查步骤**：
```bash
# 1. 检查内存使用
free -h
top -o %MEM

# 2. 检查进程内存
ps aux --sort=-%mem | head -10

# 3. 检查容器资源
docker stats
```

**解决方案**：
```bash
# 清理缓存
echo 3 > /proc/sys/vm/drop_caches

# 重启高内存使用的服务
docker-compose restart water-plant-app

# 调整内存限制
vim docker-compose.yml
```

#### 磁盘空间不足

**症状**：写入失败，日志停止更新

**排查步骤**：
```bash
# 1. 检查磁盘使用
df -h
du -sh /* | sort -hr

# 2. 查找大文件
find / -size +100M -type f 2>/dev/null

# 3. 检查日志文件
du -sh logs/*
```

**解决方案**：
```bash
# 清理旧日志
find logs/ -name "*.log" -mtime +7 -delete

# 清理 Docker 资源
docker system prune -af

# 压缩大文件
gzip logs/*.log
```

### 故障处理记录模板

```markdown
## 故障报告

**故障时间**：2024-01-01 10:00:00
**发现方式**：监控告警 / 用户报告
**影响范围**：具体描述
**故障级别**：Critical / Warning / Info

### 故障现象
- 具体症状描述
- 错误信息
- 影响的功能

### 排查过程
1. 检查项目1
2. 检查项目2
3. 定位到根本原因

### 解决方案
1. 临时解决方案
2. 永久解决方案
3. 预防措施

### 经验教训
- 改进点1
- 改进点2
- 流程优化建议
```

## 性能调优

### 应用性能优化

#### 数据库优化

```sql
-- 1. 创建必要的索引
CREATE INDEX CONCURRENTLY idx_water_quality_timestamp 
ON water_quality_data(timestamp);

CREATE INDEX CONCURRENTLY idx_control_events_type 
ON control_events(event_type, timestamp);

-- 2. 分析查询性能
EXPLAIN ANALYZE SELECT * FROM water_quality_data 
WHERE timestamp > NOW() - INTERVAL '1 hour';

-- 3. 更新统计信息
ANALYZE;
```

#### 缓存优化

```python
# Redis 配置优化
# config/production.json
{
  "redis": {
    "host": "redis-service",
    "port": 6379,
    "db": 0,
    "max_connections": 50,
    "socket_keepalive": true,
    "socket_keepalive_options": {},
    "connection_pool_kwargs": {
      "max_connections": 50,
      "retry_on_timeout": true
    }
  }
}
```

#### 应用配置优化

```yaml
# docker-compose.yml 资源限制
services:
  water-plant-app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 系统性能优化

#### 内核参数调优

```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
vm.swappiness = 10
vm.dirty_ratio = 15

# 应用配置
sysctl -p
```

#### Nginx 优化

```nginx
# nginx.conf
worker_processes auto;
worker_connections 4096;

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;
    
    upstream water_plant_app {
        least_conn;
        server water-plant-app:5000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }
}
```

## 安全管理

### 访问控制

#### 用户权限管理

```bash
# 1. 创建运维用户
sudo useradd -m -s /bin/bash ops-user
sudo usermod -aG docker ops-user

# 2. 配置 SSH 密钥认证
sudo mkdir -p /home/ops-user/.ssh
sudo cp authorized_keys /home/ops-user/.ssh/
sudo chown -R ops-user:ops-user /home/ops-user/.ssh
sudo chmod 700 /home/ops-user/.ssh
sudo chmod 600 /home/ops-user/.ssh/authorized_keys

# 3. 禁用密码登录
sudo vim /etc/ssh/sshd_config
# PasswordAuthentication no
# PubkeyAuthentication yes
```

#### 防火墙配置

```bash
# 1. 配置 UFW 防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 2. 限制特定端口访问
sudo ufw allow from 192.168.1.0/24 to any port 5432
sudo ufw allow from 192.168.1.0/24 to any port 6379
```

### 安全监控

#### 入侵检测

```bash
# 1. 监控登录失败
grep "Failed password" /var/log/auth.log | tail -20

# 2. 监控异常连接
netstat -an | grep :22 | grep ESTABLISHED

# 3. 检查系统完整性
sudo aide --check
```

#### 安全扫描

```bash
# 1. 端口扫描
nmap -sS -O localhost

# 2. 漏洞扫描
sudo lynis audit system

# 3. 容器安全扫描
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image water-plant-app:latest
```

### 证书管理

#### SSL 证书更新

```bash
# 1. Let's Encrypt 证书续期
sudo certbot renew --dry-run

# 2. 手动更新证书
sudo certbot certonly --webroot -w /var/www/html -d yourdomain.com

# 3. 重新加载 Nginx
sudo nginx -t && sudo systemctl reload nginx
```

## 备份恢复

### 备份策略

#### 自动备份配置

```bash
# 1. 配置定时任务
crontab -e

# 每日凌晨 2 点备份数据库
0 2 * * * /usr/bin/python3 /app/scripts/backup.py --action backup-db --env prod

# 每周日凌晨 3 点完整备份
0 3 * * 0 /usr/bin/python3 /app/scripts/backup.py --action full-backup --env prod

# 每日凌晨 4 点清理过期备份
0 4 * * * /usr/bin/python3 /app/scripts/backup.py --action cleanup
```

#### 备份验证

```bash
# 1. 验证备份文件完整性
python scripts/backup.py --action list

# 2. 测试恢复流程
python scripts/backup.py --action restore-db --file /path/to/test_backup.sql

# 3. 验证数据一致性
psql -h localhost -U postgres -d waterplant -c "SELECT COUNT(*) FROM water_quality_data;"
```

### 灾难恢复

#### 恢复流程

```bash
# 1. 停止所有服务
docker-compose down

# 2. 恢复数据库
python scripts/backup.py --action restore-db --file /path/to/latest_backup.sql

# 3. 恢复配置文件
tar -xzf config_backup.tar.gz -C /

# 4. 恢复数据文件
tar -xzf data_backup.tar.gz -C /

# 5. 启动服务
docker-compose up -d

# 6. 验证恢复
python scripts/monitor.py --mode health
```

## 变更管理

### 变更流程

#### 变更分类

| 类型 | 描述 | 审批级别 | 测试要求 |
|------|------|----------|----------|
| 紧急变更 | 安全漏洞修复 | 技术负责人 | 生产验证 |
| 标准变更 | 功能更新 | 项目经理 | 完整测试 |
| 常规变更 | 配置调整 | 运维负责人 | 基本测试 |

#### 变更实施

```bash
# 1. 变更前准备
# - 创建变更分支
git checkout -b change/update-config

# - 备份当前状态
python scripts/backup.py --action full-backup

# - 准备回滚方案
cp docker-compose.yml docker-compose.yml.backup

# 2. 实施变更
# - 应用配置变更
vim config/production.json

# - 重启相关服务
docker-compose restart water-plant-app

# 3. 变更验证
# - 功能测试
curl http://localhost:5000/health

# - 性能测试
python scripts/monitor.py --mode metrics

# - 业务验证
curl http://localhost:5000/api/water-quality/current
```

### 版本管理

#### 发布流程

```bash
# 1. 代码合并
git checkout main
git merge feature/new-feature

# 2. 创建发布标签
git tag -a v2.1.0 -m "Release version 2.1.0"
git push origin v2.1.0

# 3. 构建镜像
docker build -t water-plant-app:v2.1.0 .
docker tag water-plant-app:v2.1.0 water-plant-app:latest

# 4. 部署到生产环境
kubectl set image deployment/water-plant-app \
  water-plant-app=water-plant-app:v2.1.0 \
  -n water-plant

# 5. 验证部署
kubectl rollout status deployment/water-plant-app -n water-plant
```

## 应急预案

### 应急响应流程

#### 事件分级

| 级别 | 影响范围 | 响应时间 | 处理团队 |
|------|----------|----------|----------|
| P0 | 系统完全不可用 | 15分钟 | 全体技术团队 |
| P1 | 核心功能受影响 | 1小时 | 运维+开发 |
| P2 | 部分功能受影响 | 4小时 | 运维团队 |
| P3 | 性能下降 | 24小时 | 值班人员 |

#### P0 级别应急处理

```bash
# 1. 立即响应（5分钟内）
# - 确认故障
python scripts/monitor.py --mode health

# - 通知相关人员
# - 启动应急指挥

# 2. 快速恢复（15分钟内）
# - 尝试重启服务
docker-compose restart

# - 如果重启失败，回滚到上一版本
kubectl rollout undo deployment/water-plant-app -n water-plant

# - 切换到备用系统（如果有）

# 3. 根因分析
# - 收集日志和监控数据
# - 分析故障原因
# - 制定永久解决方案
```

### 联系方式

#### 应急联系人

| 角色 | 姓名 | 电话 | 邮箱 | 备注 |
|------|------|------|------|------|
| 技术负责人 | 张三 | 138xxxx0001 | zhang@company.com | 24小时待命 |
| 运维负责人 | 李四 | 138xxxx0002 | li@company.com | 工作时间 |
| 开发负责人 | 王五 | 138xxxx0003 | wang@company.com | 工作时间 |
| 值班工程师 | 轮值 | 138xxxx0004 | oncall@company.com | 24小时轮值 |

#### 外部支持

| 服务商 | 联系方式 | 服务内容 |
|--------|----------|----------|
| 云服务商 | 400-xxx-xxxx | 基础设施支持 |
| 数据库厂商 | 400-xxx-xxxx | 数据库技术支持 |
| 网络运营商 | 10000 | 网络连接问题 |

## 运维工具

### 脚本工具

#### 监控脚本

```bash
# 健康检查
python scripts/monitor.py --mode health

# 性能监控
python scripts/monitor.py --mode metrics

# 持续监控
python scripts/monitor.py --mode continuous
```

#### 备份脚本

```bash
# 数据库备份
python scripts/backup.py --action backup-db

# 完整备份
python scripts/backup.py --action full-backup

# 恢复数据
python scripts/backup.py --action restore-db --file backup.sql
```

#### 部署脚本

```bash
# Docker Compose 部署
bash scripts/deploy.sh docker-compose --env prod

# Kubernetes 部署
bash scripts/deploy.sh kubernetes --env prod

# 本地部署
bash scripts/deploy.sh local --env dev
```

### 监控工具

#### Grafana 仪表板

- **系统概览**：http://localhost:3000/d/system-overview
- **应用性能**：http://localhost:3000/d/app-performance
- **业务监控**：http://localhost:3000/d/business-metrics
- **告警状态**：http://localhost:3000/d/alerts

#### Prometheus 查询

```promql
# CPU 使用率
rate(cpu_usage_total[5m]) * 100

# 内存使用率
(memory_used_bytes / memory_total_bytes) * 100

# API 请求率
rate(http_requests_total[5m])

# 错误率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### 日志分析

#### 常用日志查询

```bash
# 查看错误日志
grep "ERROR" logs/water_plant.log | tail -50

# 查看性能日志
grep "slow query" logs/water_plant.log

# 查看访问日志
grep "POST /api" logs/water_plant.log | tail -20

# 实时监控日志
tail -f logs/water_plant.log | grep -E "ERROR|WARN"
```

#### 日志分析工具

```bash
# 使用 jq 分析 JSON 日志
cat logs/water_plant.log | jq 'select(.level == "ERROR")'

# 统计错误类型
grep "ERROR" logs/water_plant.log | awk '{print $4}' | sort | uniq -c

# 分析响应时间
grep "response_time" logs/water_plant.log | awk '{sum+=$6; count++} END {print "Average:", sum/count}'
```

---

## 附录

### A. 运维检查清单

- [ ] 每日系统状态检查
- [ ] 每日性能指标检查
- [ ] 每日业务指标检查
- [ ] 每周系统清理
- [ ] 每周数据库维护
- [ ] 每周安全检查
- [ ] 每月系统更新
- [ ] 每月容量规划

### B. 故障处理模板

详见故障处理记录模板部分。

### C. 应急联系方式

详见应急预案部分。

### D. 监控指标说明

详见监控告警部分。