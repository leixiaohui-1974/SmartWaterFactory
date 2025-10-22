# MCP服务部署指南

## 部署架构

```
┌─────────────────────────────────────────────────────┐
│                  AI客户端                            │
│  (Claude Desktop, Web App, Mobile App)              │
└───────────────┬─────────────────────────────────────┘
                │
                │ MCP Protocol (JSON-RPC 2.0)
                │
┌───────────────▼─────────────────────────────────────┐
│            MCP服务器                                 │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ STDIO Mode   │  │  HTTP Mode   │                │
│  │ (stdin/out)  │  │  (REST API)  │                │
│  └──────┬───────┘  └───────┬──────┘                │
│         └──────────┬────────┘                       │
│                    │                                 │
│         ┌──────────▼──────────┐                    │
│         │  Protocol Handler   │                     │
│         └──────────┬──────────┘                    │
│                    │                                 │
│    ┌───────────────┼───────────────┐               │
│    │               │               │                │
│ ┌──▼───┐  ┌───────▼────┐  ┌──────▼─────┐         │
│ │Tools │  │  Session   │  │  Resources │          │
│ │      │  │  Manager   │  │            │          │
│ └──┬───┘  └───────┬────┘  └──────┬─────┘         │
│    │              │               │                │
│    └──────────────┼───────────────┘               │
│                   │                                 │
│        ┌──────────▼──────────┐                    │
│        │  Simulation Core    │                     │
│        │  (WaterPlant)       │                     │
│        └─────────────────────┘                    │
└─────────────────────────────────────────────────────┘
```

## 部署方式

### 1. 本地部署（开发/测试）

#### 直接运行

```bash
# 安装依赖
pip install -r requirements.txt
pip install -r requirements-mcp.txt

# STDIO模式
python start_mcp_service.py --mode stdio

# HTTP模式
python start_mcp_service.py --mode http --host 127.0.0.1 --port 8000
```

#### 使用systemd（Linux）

创建服务文件 `/etc/systemd/system/mcp-water-factory.service`:

```ini
[Unit]
Description=Smart Water Factory MCP Service
After=network.target

[Service]
Type=simple
User=waterplant
WorkingDirectory=/opt/SmartWaterFactory
Environment="PATH=/opt/SmartWaterFactory/venv/bin"
ExecStart=/opt/SmartWaterFactory/venv/bin/python start_mcp_service.py --mode http --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-water-factory
sudo systemctl start mcp-water-factory
sudo systemctl status mcp-water-factory
```

### 2. Docker部署

#### Dockerfile

创建 `Dockerfile.mcp`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt requirements-mcp.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-mcp.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p logs data/mcp temp/mcp

# 暴露HTTP端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动服务（HTTP模式）
CMD ["python", "start_mcp_service.py", "--mode", "http", "--host", "0.0.0.0", "--port", "8000"]
```

#### 构建和运行

```bash
# 构建镜像
docker build -f Dockerfile.mcp -t smart-water-factory-mcp:latest .

# 运行容器
docker run -d \
  --name mcp-service \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -e MCP_MAX_SESSIONS=200 \
  -e MCP_LOG_LEVEL=INFO \
  smart-water-factory-mcp:latest

# 查看日志
docker logs -f mcp-service
```

#### Docker Compose

创建 `docker-compose.mcp.yml`:

```yaml
version: '3.8'

services:
  mcp-service:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    image: smart-water-factory-mcp:latest
    container_name: mcp-service
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./temp:/app/temp
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000
      - MCP_LOG_LEVEL=INFO
      - MCP_MAX_SESSIONS=200
      - MCP_SESSION_TIMEOUT=30
      - MCP_DEBUG=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 可选：添加Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: mcp-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - mcp-service
    restart: unless-stopped
```

启动：

```bash
docker-compose -f docker-compose.mcp.yml up -d
```

### 3. Kubernetes部署

#### 部署配置

创建 `k8s/mcp-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-service
  labels:
    app: mcp-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-service
  template:
    metadata:
      labels:
        app: mcp-service
    spec:
      containers:
      - name: mcp-service
        image: smart-water-factory-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: MCP_HOST
          value: "0.0.0.0"
        - name: MCP_PORT
          value: "8000"
        - name: MCP_MAX_SESSIONS
          valueFrom:
            configMapKeyRef:
              name: mcp-config
              key: max_sessions
        - name: MCP_LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        - name: data
          mountPath: /app/data
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: mcp-logs-pvc
      - name: data
        persistentVolumeClaim:
          claimName: mcp-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-service
spec:
  selector:
    app: mcp-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
data:
  max_sessions: "200"
  session_timeout: "30"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mcp-logs-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mcp-data-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
```

#### 水平扩展

创建 `k8s/mcp-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 部署到Kubernetes

```bash
# 应用配置
kubectl apply -f k8s/mcp-deployment.yaml
kubectl apply -f k8s/mcp-hpa.yaml

# 查看状态
kubectl get pods -l app=mcp-service
kubectl get svc mcp-service

# 查看日志
kubectl logs -f deployment/mcp-service

# 扩容/缩容
kubectl scale deployment mcp-service --replicas=5
```

### 4. 云平台部署

#### AWS部署

##### ECS Fargate

```bash
# 创建ECR仓库
aws ecr create-repository --repository-name smart-water-factory-mcp

# 构建并推送镜像
docker build -f Dockerfile.mcp -t smart-water-factory-mcp:latest .
docker tag smart-water-factory-mcp:latest \
  <account-id>.dkr.ecr.<region>.amazonaws.com/smart-water-factory-mcp:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/smart-water-factory-mcp:latest

# 创建ECS任务定义和服务（使用AWS Console或CloudFormation）
```

##### EKS部署

```bash
# 创建EKS集群
eksctl create cluster --name mcp-cluster --region us-west-2

# 部署应用
kubectl apply -f k8s/mcp-deployment.yaml
```

#### Azure部署

```bash
# 创建容器注册表
az acr create --name mcpregistry --sku Basic

# 构建并推送镜像
az acr build --registry mcpregistry --image smart-water-factory-mcp:latest .

# 部署到Azure Container Instances
az container create \
  --resource-group myResourceGroup \
  --name mcp-service \
  --image mcpregistry.azurecr.io/smart-water-factory-mcp:latest \
  --ports 8000 \
  --cpu 2 \
  --memory 4
```

#### 阿里云部署

```bash
# 推送到阿里云容器镜像服务
docker tag smart-water-factory-mcp:latest \
  registry.cn-hangzhou.aliyuncs.com/namespace/smart-water-factory-mcp:latest
docker push registry.cn-hangzhou.aliyuncs.com/namespace/smart-water-factory-mcp:latest

# 使用ACK（容器服务Kubernetes版）部署
kubectl apply -f k8s/mcp-deployment.yaml
```

## 负载均衡和高可用

### Nginx配置

创建 `nginx.conf`:

```nginx
upstream mcp_backend {
    least_conn;
    server mcp-service-1:8000 max_fails=3 fail_timeout=30s;
    server mcp-service-2:8000 max_fails=3 fail_timeout=30s;
    server mcp-service-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.smartwaterfactory.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.smartwaterfactory.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;

    # 限流
    limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=60r/m;

    location / {
        limit_req zone=mcp_limit burst=10 nodelay;

        proxy_pass http://mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://mcp_backend/health;
        access_log off;
    }
}
```

## 监控和日志

### Prometheus监控

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-service'
    static_configs:
      - targets: ['mcp-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana仪表盘

导入预配置的仪表盘模板（需要先实现metrics端点）。

### 日志聚合（ELK Stack）

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "mcp-service-%{+yyyy.MM.dd}"
```

## 备份和恢复

### 数据备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/mcp-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

# 备份数据目录
tar -czf $BACKUP_DIR/data.tar.gz /app/data

# 备份日志
tar -czf $BACKUP_DIR/logs.tar.gz /app/logs

# 备份配置
cp /app/.env $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### 定时备份（crontab）

```cron
# 每天凌晨2点备份
0 2 * * * /opt/SmartWaterFactory/scripts/backup.sh
```

## 安全加固

1. **使用HTTPS**: 生产环境必须使用SSL/TLS
2. **API认证**: 启用`MCP_ENABLE_AUTH=true`
3. **限流**: 使用Nginx或API网关限流
4. **防火墙**: 只开放必要端口
5. **定期更新**: 及时更新依赖包
6. **日志审计**: 定期审查访问日志

## 性能调优

### 系统层面

```bash
# 增加文件描述符限制
ulimit -n 65536

# TCP优化
sysctl -w net.core.somaxconn=4096
sysctl -w net.ipv4.tcp_max_syn_backlog=8192
```

### 应用层面

```bash
# 增加并发限制
export MCP_MAX_SESSIONS=500
export MCP_MAX_CONCURRENT_SIMULATIONS=10

# 使用uvloop（Linux/macOS）
pip install uvloop
```

## 故障排查

### 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8000/health"
MAX_RETRIES=3

for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s $HEALTH_URL > /dev/null; then
        echo "Service is healthy"
        exit 0
    fi
    echo "Retry $i/$MAX_RETRIES..."
    sleep 5
done

echo "Service is unhealthy"
exit 1
```

### 常见问题

1. **OOM错误**: 增加内存限制或减少并发会话数
2. **连接超时**: 检查网络和防火墙设置
3. **性能下降**: 检查资源使用情况，考虑扩容

## 运维命令速查

```bash
# 查看服务状态
systemctl status mcp-water-factory

# 重启服务
systemctl restart mcp-water-factory

# 查看实时日志
tail -f /app/logs/mcp_service.log

# 检查端口
netstat -tlnp | grep 8000

# 查看进程
ps aux | grep mcp_service

# Docker相关
docker ps
docker logs -f mcp-service
docker exec -it mcp-service bash

# Kubernetes相关
kubectl get pods
kubectl logs -f deployment/mcp-service
kubectl describe pod <pod-name>
kubectl exec -it <pod-name> -- /bin/bash
```
