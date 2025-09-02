#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能水厂控制系统监控脚本
提供系统健康检查、性能监控和告警功能
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import requests
import psutil
from dataclasses import dataclass


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    service: str
    status: str
    response_time: float
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class MetricData:
    """监控指标数据"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    labels: Dict[str, str]


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.logger = self._setup_logging()
        
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "endpoints": {
                "api": "http://localhost:5000",
                "metrics": "http://localhost:9090",
                "grafana": "http://localhost:3000"
            },
            "thresholds": {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "response_time": 5.0
            },
            "alerts": {
                "webhook_url": None,
                "email_smtp": None,
                "slack_webhook": None
            },
            "monitoring": {
                "interval": 60,
                "retention_days": 7
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"警告: 无法加载配置文件 {config_file}: {e}")
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('water_plant_monitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def check_api_health(self) -> HealthCheckResult:
        """检查 API 健康状态"""
        start_time = time.time()
        api_url = self.config['endpoints']['api']
        
        try:
            response = requests.get(
                f"{api_url}/health",
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return HealthCheckResult(
                    service="api",
                    status="healthy",
                    response_time=response_time,
                    details=data,
                    timestamp=datetime.now()
                )
            else:
                return HealthCheckResult(
                    service="api",
                    status="unhealthy",
                    response_time=response_time,
                    details={"status_code": response.status_code},
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthCheckResult(
                service="api",
                status="error",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.now()
            )
    
    def check_database_health(self) -> HealthCheckResult:
        """检查数据库健康状态"""
        start_time = time.time()
        api_url = self.config['endpoints']['api']
        
        try:
            response = requests.get(
                f"{api_url}/health/database",
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return HealthCheckResult(
                    service="database",
                    status="healthy" if data.get('connected') else "unhealthy",
                    response_time=response_time,
                    details=data,
                    timestamp=datetime.now()
                )
            else:
                return HealthCheckResult(
                    service="database",
                    status="unhealthy",
                    response_time=response_time,
                    details={"status_code": response.status_code},
                    timestamp=datetime.now()
                )
        except Exception as e:
            return HealthCheckResult(
                service="database",
                status="error",
                response_time=time.time() - start_time,
                details={"error": str(e)},
                timestamp=datetime.now()
            )
    
    def get_system_metrics(self) -> List[MetricData]:
        """获取系统指标"""
        metrics = []
        timestamp = datetime.now()
        
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(MetricData(
            name="cpu_usage_percent",
            value=cpu_percent,
            unit="percent",
            timestamp=timestamp,
            labels={"host": "localhost"}
        ))
        
        # 内存使用率
        memory = psutil.virtual_memory()
        metrics.append(MetricData(
            name="memory_usage_percent",
            value=memory.percent,
            unit="percent",
            timestamp=timestamp,
            labels={"host": "localhost"}
        ))
        
        metrics.append(MetricData(
            name="memory_usage_bytes",
            value=memory.used,
            unit="bytes",
            timestamp=timestamp,
            labels={"host": "localhost"}
        ))
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        metrics.append(MetricData(
            name="disk_usage_percent",
            value=(disk.used / disk.total) * 100,
            unit="percent",
            timestamp=timestamp,
            labels={"host": "localhost", "mount": "/"}
        ))
        
        # 网络统计
        net_io = psutil.net_io_counters()
        metrics.append(MetricData(
            name="network_bytes_sent",
            value=net_io.bytes_sent,
            unit="bytes",
            timestamp=timestamp,
            labels={"host": "localhost"}
        ))
        
        metrics.append(MetricData(
            name="network_bytes_recv",
            value=net_io.bytes_recv,
            unit="bytes",
            timestamp=timestamp,
            labels={"host": "localhost"}
        ))
        
        return metrics
    
    def get_application_metrics(self) -> List[MetricData]:
        """获取应用指标"""
        metrics = []
        api_url = self.config['endpoints']['api']
        
        try:
            response = requests.get(
                f"{api_url}/metrics",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                timestamp = datetime.now()
                
                # 处理各种应用指标
                for metric_name, metric_value in data.items():
                    if isinstance(metric_value, (int, float)):
                        metrics.append(MetricData(
                            name=f"app_{metric_name}",
                            value=float(metric_value),
                            unit="count",
                            timestamp=timestamp,
                            labels={"service": "water_plant_app"}
                        ))
        except Exception as e:
            self.logger.error(f"获取应用指标失败: {e}")
        
        return metrics
    
    def check_thresholds(self, metrics: List[MetricData]) -> List[Dict[str, Any]]:
        """检查阈值告警"""
        alerts = []
        thresholds = self.config['thresholds']
        
        for metric in metrics:
            threshold_key = metric.name.replace('_percent', '_usage')
            if threshold_key in thresholds:
                threshold = thresholds[threshold_key]
                if metric.value > threshold:
                    alerts.append({
                        "metric": metric.name,
                        "value": metric.value,
                        "threshold": threshold,
                        "severity": "warning" if metric.value < threshold * 1.1 else "critical",
                        "timestamp": metric.timestamp.isoformat(),
                        "message": f"{metric.name} 超过阈值: {metric.value:.2f} > {threshold}"
                    })
        
        return alerts
    
    def send_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """发送告警"""
        if not alerts:
            return
        
        alert_config = self.config['alerts']
        
        # Webhook 告警
        if alert_config.get('webhook_url'):
            try:
                requests.post(
                    alert_config['webhook_url'],
                    json={"alerts": alerts},
                    timeout=10
                )
                self.logger.info(f"已发送 {len(alerts)} 个告警到 Webhook")
            except Exception as e:
                self.logger.error(f"发送 Webhook 告警失败: {e}")
        
        # 控制台输出
        for alert in alerts:
            self.logger.warning(f"告警: {alert['message']}")
    
    def run_health_check(self) -> Dict[str, HealthCheckResult]:
        """运行健康检查"""
        self.logger.info("开始健康检查...")
        
        results = {
            "api": self.check_api_health(),
            "database": self.check_database_health()
        }
        
        # 输出结果
        for service, result in results.items():
            status_emoji = "✅" if result.status == "healthy" else "❌"
            self.logger.info(
                f"{status_emoji} {service}: {result.status} "
                f"(响应时间: {result.response_time:.3f}s)"
            )
        
        return results
    
    def run_metrics_collection(self) -> Dict[str, List[MetricData]]:
        """运行指标收集"""
        self.logger.info("开始收集指标...")
        
        metrics = {
            "system": self.get_system_metrics(),
            "application": self.get_application_metrics()
        }
        
        # 检查告警
        all_metrics = metrics["system"] + metrics["application"]
        alerts = self.check_thresholds(all_metrics)
        
        if alerts:
            self.send_alerts(alerts)
        
        # 输出关键指标
        for metric in metrics["system"]:
            if "usage_percent" in metric.name:
                self.logger.info(f"{metric.name}: {metric.value:.2f}%")
        
        return metrics
    
    def run_continuous_monitoring(self) -> None:
        """运行持续监控"""
        interval = self.config['monitoring']['interval']
        self.logger.info(f"开始持续监控 (间隔: {interval}秒)...")
        
        try:
            while True:
                # 健康检查
                health_results = self.run_health_check()
                
                # 指标收集
                metrics = self.run_metrics_collection()
                
                # 等待下一次检查
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
        except Exception as e:
            self.logger.error(f"监控过程中发生错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能水厂控制系统监控工具")
    parser.add_argument(
        "--config", "-c",
        help="配置文件路径",
        default="config/monitoring.json"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["health", "metrics", "continuous"],
        default="health",
        help="运行模式"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["console", "json"],
        default="console",
        help="输出格式"
    )
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = SystemMonitor(args.config)
    
    try:
        if args.mode == "health":
            results = monitor.run_health_check()
            if args.output == "json":
                print(json.dumps({
                    service: {
                        "status": result.status,
                        "response_time": result.response_time,
                        "details": result.details,
                        "timestamp": result.timestamp.isoformat()
                    }
                    for service, result in results.items()
                }, indent=2, ensure_ascii=False))
        
        elif args.mode == "metrics":
            metrics = monitor.run_metrics_collection()
            if args.output == "json":
                print(json.dumps({
                    category: [
                        {
                            "name": metric.name,
                            "value": metric.value,
                            "unit": metric.unit,
                            "timestamp": metric.timestamp.isoformat(),
                            "labels": metric.labels
                        }
                        for metric in metric_list
                    ]
                    for category, metric_list in metrics.items()
                }, indent=2, ensure_ascii=False))
        
        elif args.mode == "continuous":
            monitor.run_continuous_monitoring()
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()