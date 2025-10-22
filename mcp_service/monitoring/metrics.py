#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prometheus监控指标导出模块。"""

import time
from typing import Dict, Any
from collections import defaultdict


class PrometheusMetrics:
    """Prometheus指标收集器。

    收集MCP服务的关键性能指标，用于Prometheus监控。
    """

    def __init__(self):
        """初始化指标收集器。"""
        self.metrics = defaultdict(lambda: defaultdict(int))
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.start_time = time.time()

    def increment_counter(self, metric_name: str, labels: Dict[str, str] = None, value: float = 1.0):
        """增加计数器指标。

        Args:
            metric_name: 指标名称
            labels: 标签字典
            value: 增加的值
        """
        label_str = self._format_labels(labels)
        self.metrics[metric_name][label_str] += value

    def set_gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """设置仪表盘指标。

        Args:
            metric_name: 指标名称
            value: 指标值
            labels: 标签字典
        """
        label_str = self._format_labels(labels)
        key = f"{metric_name}{label_str}"
        self.gauges[key] = value

    def observe_histogram(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """观察直方图指标。

        Args:
            metric_name: 指标名称
            value: 观察值
            labels: 标签字典
        """
        label_str = self._format_labels(labels)
        key = f"{metric_name}{label_str}"
        self.histograms[key].append(value)

    def _format_labels(self, labels: Dict[str, str] = None) -> str:
        """格式化标签。

        Args:
            labels: 标签字典

        Returns:
            格式化后的标签字符串
        """
        if not labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"

    def export_prometheus_format(self) -> str:
        """导出Prometheus格式的指标。

        Returns:
            Prometheus文本格式的指标
        """
        lines = []

        # 计数器指标
        for metric_name, label_values in self.metrics.items():
            lines.append(f"# HELP {metric_name} {metric_name} counter")
            lines.append(f"# TYPE {metric_name} counter")
            for label_str, value in label_values.items():
                lines.append(f"{metric_name}{label_str} {value}")

        # 仪表盘指标
        lines.append(f"# HELP process_uptime_seconds Process uptime in seconds")
        lines.append(f"# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {time.time() - self.start_time}")

        for key, value in self.gauges.items():
            metric_name = key.split("{")[0]
            lines.append(f"# HELP {metric_name} {metric_name} gauge")
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{key} {value}")

        # 直方图指标
        for key, values in self.histograms.items():
            if not values:
                continue

            metric_name = key.split("{")[0]
            lines.append(f"# HELP {metric_name} {metric_name} histogram")
            lines.append(f"# TYPE {metric_name} histogram")

            # 计算分位数
            sorted_values = sorted(values)
            count = len(values)
            total = sum(values)

            percentiles = [0.5, 0.9, 0.95, 0.99]
            for p in percentiles:
                idx = int(count * p)
                if idx < count:
                    value = sorted_values[idx]
                    lines.append(f"{key}_bucket{{le=\"{p}\"}} {idx + 1}")

            lines.append(f"{key}_sum {total}")
            lines.append(f"{key}_count {count}")

        return "\n".join(lines) + "\n"

    def get_metrics_dict(self) -> Dict[str, Any]:
        """获取指标字典格式。

        Returns:
            指标字典
        """
        return {
            "counters": dict(self.metrics),
            "gauges": dict(self.gauges),
            "histograms": {k: {"count": len(v), "sum": sum(v), "values": v[:100]}
                          for k, v in self.histograms.items()},
            "uptime": time.time() - self.start_time
        }


# 全局指标收集器实例
_global_metrics = PrometheusMetrics()


def get_metrics() -> PrometheusMetrics:
    """获取全局指标收集器。"""
    return _global_metrics


def record_tool_call(tool_name: str, success: bool, execution_time: float):
    """记录工具调用指标。

    Args:
        tool_name: 工具名称
        success: 是否成功
        execution_time: 执行时间
    """
    metrics = get_metrics()

    # 计数器
    metrics.increment_counter(
        "mcp_tool_calls_total",
        {"tool": tool_name, "status": "success" if success else "error"}
    )

    # 执行时间直方图
    metrics.observe_histogram(
        "mcp_tool_execution_seconds",
        execution_time,
        {"tool": tool_name}
    )


def record_session_metrics(active_sessions: int, total_simulations: int):
    """记录会话指标。

    Args:
        active_sessions: 活跃会话数
        total_simulations: 总仿真数
    """
    metrics = get_metrics()
    metrics.set_gauge("mcp_active_sessions", active_sessions)
    metrics.set_gauge("mcp_total_simulations", total_simulations)


def record_http_request(method: str, path: str, status_code: int, duration: float):
    """记录HTTP请求指标。

    Args:
        method: HTTP方法
        path: 请求路径
        status_code: 状态码
        duration: 请求时长
    """
    metrics = get_metrics()

    metrics.increment_counter(
        "mcp_http_requests_total",
        {"method": method, "path": path, "status": str(status_code)}
    )

    metrics.observe_histogram(
        "mcp_http_request_duration_seconds",
        duration,
        {"method": method, "path": path}
    )
