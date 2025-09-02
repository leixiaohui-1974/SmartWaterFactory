#!/bin/bash

# 智能水厂控制系统部署脚本
# 支持 Docker Compose 和 Kubernetes 部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
智能水厂控制系统部署脚本

用法: $0 [选项] <部署模式>

部署模式:
  docker-compose    使用 Docker Compose 部署
  kubernetes        使用 Kubernetes 部署
  local            本地开发环境部署

选项:
  -e, --env ENV     指定环境 (dev|staging|prod)
  -h, --help        显示此帮助信息
  -v, --verbose     详细输出
  --no-build        跳过镜像构建
  --no-migrate      跳过数据库迁移
  --cleanup         清理现有部署

示例:
  $0 docker-compose -e prod
  $0 kubernetes -e staging --verbose
  $0 local -e dev --no-build
EOF
}

# 检查依赖
check_dependencies() {
    local mode=$1
    
    log_info "检查部署依赖..."
    
    # 通用依赖
    if ! command -v git &> /dev/null; then
        log_error "Git 未安装"
        exit 1
    fi
    
    case $mode in
        "docker-compose")
            if ! command -v docker &> /dev/null; then
                log_error "Docker 未安装"
                exit 1
            fi
            if ! command -v docker-compose &> /dev/null; then
                log_error "Docker Compose 未安装"
                exit 1
            fi
            ;;
        "kubernetes")
            if ! command -v kubectl &> /dev/null; then
                log_error "kubectl 未安装"
                exit 1
            fi
            if ! command -v helm &> /dev/null; then
                log_warning "Helm 未安装，某些功能可能不可用"
            fi
            ;;
        "local")
            if ! command -v python3 &> /dev/null; then
                log_error "Python 3 未安装"
                exit 1
            fi
            if ! command -v pip &> /dev/null; then
                log_error "pip 未安装"
                exit 1
            fi
            ;;
    esac
    
    log_success "依赖检查完成"
}

# 构建 Docker 镜像
build_image() {
    local env=$1
    
    if [ "$NO_BUILD" = "true" ]; then
        log_info "跳过镜像构建"
        return
    fi
    
    log_info "构建 Docker 镜像..."
    
    # 构建主应用镜像
    docker build -t water-plant-app:$env .
    
    # 如果是生产环境，打标签
    if [ "$env" = "prod" ]; then
        docker tag water-plant-app:$env water-plant-app:latest
    fi
    
    log_success "镜像构建完成"
}

# Docker Compose 部署
deploy_docker_compose() {
    local env=$1
    
    log_info "使用 Docker Compose 部署 ($env 环境)..."
    
    # 选择配置文件
    local compose_file="docker-compose.yml"
    if [ -f "docker-compose.$env.yml" ]; then
        compose_file="docker-compose.$env.yml"
    fi
    
    # 清理现有部署
    if [ "$CLEANUP" = "true" ]; then
        log_info "清理现有部署..."
        docker-compose -f $compose_file down -v
    fi
    
    # 构建镜像
    build_image $env
    
    # 启动服务
    log_info "启动服务..."
    docker-compose -f $compose_file up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 健康检查
    check_health_docker_compose
    
    log_success "Docker Compose 部署完成"
}

# Kubernetes 部署
deploy_kubernetes() {
    local env=$1
    
    log_info "使用 Kubernetes 部署 ($env 环境)..."
    
    # 检查集群连接
    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到 Kubernetes 集群"
        exit 1
    fi
    
    # 创建命名空间
    log_info "创建命名空间..."
    kubectl apply -f k8s/namespace.yaml
    
    # 应用配置
    log_info "应用配置和密钥..."
    kubectl apply -f k8s/configmap.yaml
    
    # 部署应用
    log_info "部署应用..."
    kubectl apply -f k8s/deployment.yaml
    
    # 等待部署完成
    log_info "等待部署完成..."
    kubectl rollout status deployment/water-plant-app -n water-plant --timeout=300s
    
    # 健康检查
    check_health_kubernetes
    
    log_success "Kubernetes 部署完成"
}

# 本地部署
deploy_local() {
    local env=$1
    
    log_info "本地环境部署 ($env 环境)..."
    
    # 安装依赖
    if [ "$NO_BUILD" != "true" ]; then
        log_info "安装 Python 依赖..."
        pip install -r requirements.txt
    fi
    
    # 设置环境变量
    export ENVIRONMENT=$env
    export PYTHONPATH=$(pwd)
    
    # 启动应用
    log_info "启动应用..."
    python run_simulation.py --api-server --host 127.0.0.1 --port 5000 &
    
    # 保存进程ID
    echo $! > .local_deploy.pid
    
    # 等待启动
    sleep 10
    
    # 健康检查
    check_health_local
    
    log_success "本地部署完成"
    log_info "应用运行在: http://127.0.0.1:5000"
    log_info "停止应用: kill \$(cat .local_deploy.pid)"
}

# Docker Compose 健康检查
check_health_docker_compose() {
    log_info "执行健康检查..."
    
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:5000/health &> /dev/null; then
            log_success "应用健康检查通过"
            return 0
        fi
        
        log_info "健康检查失败，重试 ($attempt/$max_attempts)..."
        sleep 10
        ((attempt++))
    done
    
    log_error "健康检查失败"
    return 1
}

# Kubernetes 健康检查
check_health_kubernetes() {
    log_info "执行健康检查..."
    
    # 检查 Pod 状态
    local ready_pods=$(kubectl get pods -n water-plant -l app=water-plant-app --field-selector=status.phase=Running --no-headers | wc -l)
    local total_pods=$(kubectl get pods -n water-plant -l app=water-plant-app --no-headers | wc -l)
    
    if [ $ready_pods -eq $total_pods ] && [ $ready_pods -gt 0 ]; then
        log_success "所有 Pod 运行正常 ($ready_pods/$total_pods)"
    else
        log_warning "部分 Pod 未就绪 ($ready_pods/$total_pods)"
    fi
    
    # 检查服务
    if kubectl get service water-plant-app-service -n water-plant &> /dev/null; then
        log_success "服务创建成功"
    else
        log_error "服务创建失败"
    fi
}

# 本地健康检查
check_health_local() {
    log_info "执行健康检查..."
    
    if curl -f http://127.0.0.1:5000/health &> /dev/null; then
        log_success "应用健康检查通过"
    else
        log_error "健康检查失败"
    fi
}

# 主函数
main() {
    # 默认值
    local env="dev"
    local mode=""
    local verbose=false
    NO_BUILD=false
    NO_MIGRATE=false
    CLEANUP=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--env)
                env="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --no-build)
                NO_BUILD=true
                shift
                ;;
            --no-migrate)
                NO_MIGRATE=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
                shift
                ;;
            docker-compose|kubernetes|local)
                mode="$1"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查必需参数
    if [ -z "$mode" ]; then
        log_error "请指定部署模式"
        show_help
        exit 1
    fi
    
    # 验证环境
    if [[ ! "$env" =~ ^(dev|staging|prod)$ ]]; then
        log_error "无效的环境: $env"
        exit 1
    fi
    
    # 启用详细输出
    if [ "$verbose" = true ]; then
        set -x
    fi
    
    log_info "开始部署智能水厂控制系统"
    log_info "部署模式: $mode"
    log_info "环境: $env"
    
    # 检查依赖
    check_dependencies $mode
    
    # 执行部署
    case $mode in
        "docker-compose")
            deploy_docker_compose $env
            ;;
        "kubernetes")
            deploy_kubernetes $env
            ;;
        "local")
            deploy_local $env
            ;;
    esac
    
    log_success "部署完成！"
}

# 执行主函数
main "$@"