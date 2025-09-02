#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""性能分析和监控工具。

本模块提供了用于性能分析和监控的工具，包括：
1. 函数执行时间测量
2. 内存使用监控
3. 性能分析装饰器
4. 系统资源监控
5. 性能报告生成
"""

import time
import psutil
import functools
import threading
import tracemalloc
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path
import logging


@dataclass
class PerformanceMetrics:
    """性能指标数据类。"""
    function_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    timestamp: float
    call_count: int = 1
    max_memory: float = 0.0
    min_memory: float = float('inf')
    avg_execution_time: float = 0.0
    
    def __post_init__(self):
        """初始化后处理。"""
        self.avg_execution_time = self.execution_time
        self.max_memory = max(self.max_memory, self.memory_usage)
        self.min_memory = min(self.min_memory, self.memory_usage)


@dataclass
class SystemMetrics:
    """系统性能指标。"""
    cpu_percent: float
    memory_percent: float
    memory_available: int
    memory_used: int
    disk_usage: float
    network_io: Dict[str, int] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class PerformanceProfiler:
    """性能分析器。"""
    
    def __init__(self):
        """初始化性能分析器。"""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.system_metrics: List[SystemMetrics] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(__name__)
        
        # 启动内存跟踪
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def profile(self, func_name: Optional[str] = None):
        """性能分析装饰器。
        
        Args:
            func_name: 自定义函数名称，如果不提供则使用函数的实际名称
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                name = func_name or func.__name__
                
                # 记录开始时间和内存
                start_time = time.perf_counter()
                start_memory = self._get_memory_usage()
                start_cpu = psutil.cpu_percent()
                
                try:
                    # 执行函数
                    result = func(*args, **kwargs)
                    
                    # 记录结束时间和内存
                    end_time = time.perf_counter()
                    end_memory = self._get_memory_usage()
                    end_cpu = psutil.cpu_percent()
                    
                    # 计算性能指标
                    execution_time = end_time - start_time
                    memory_delta = end_memory - start_memory
                    cpu_usage = (start_cpu + end_cpu) / 2
                    
                    # 更新或创建性能指标
                    self._update_metrics(
                        name, execution_time, memory_delta, cpu_usage
                    )
                    
                    return result
                    
                except Exception as e:
                    self.logger.error(f"函数 {name} 执行时发生错误: {e}")
                    raise
                    
            return wrapper
        return decorator
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）。"""
        try:
            current, peak = tracemalloc.get_traced_memory()
            return current / 1024 / 1024  # 转换为MB
        except Exception:
            # 如果tracemalloc不可用，使用psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
    
    def _update_metrics(self, func_name: str, execution_time: float, 
                       memory_usage: float, cpu_usage: float):
        """更新性能指标。"""
        timestamp = time.time()
        
        if func_name in self.metrics:
            # 更新现有指标
            metric = self.metrics[func_name]
            metric.call_count += 1
            metric.avg_execution_time = (
                (metric.avg_execution_time * (metric.call_count - 1) + execution_time) 
                / metric.call_count
            )
            metric.max_memory = max(metric.max_memory, memory_usage)
            metric.min_memory = min(metric.min_memory, memory_usage)
            metric.execution_time = execution_time
            metric.memory_usage = memory_usage
            metric.cpu_usage = cpu_usage
            metric.timestamp = timestamp
        else:
            # 创建新指标
            self.metrics[func_name] = PerformanceMetrics(
                function_name=func_name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                timestamp=timestamp
            )
    
    def start_system_monitoring(self, interval: float = 1.0):
        """开始系统监控。
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.monitoring_active:
            self.logger.warning("系统监控已经在运行")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_system, args=(interval,), daemon=True
        )
        self.monitor_thread.start()
        self.logger.info(f"系统监控已启动，间隔: {interval}秒")
    
    def stop_system_monitoring(self):
        """停止系统监控。"""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        self.logger.info("系统监控已停止")
    
    def _monitor_system(self, interval: float):
        """系统监控线程函数。"""
        while self.monitoring_active:
            try:
                # 获取系统指标
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # 网络IO（如果可用）
                network_io = {}
                try:
                    net_io = psutil.net_io_counters()
                    network_io = {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv,
                        'packets_sent': net_io.packets_sent,
                        'packets_recv': net_io.packets_recv
                    }
                except Exception:
                    pass
                
                # 创建系统指标
                system_metric = SystemMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_available=memory.available,
                    memory_used=memory.used,
                    disk_usage=disk.percent,
                    network_io=network_io
                )
                
                self.system_metrics.append(system_metric)
                
                # 限制历史记录数量
                if len(self.system_metrics) > 1000:
                    self.system_metrics = self.system_metrics[-500:]
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"系统监控错误: {e}")
                time.sleep(interval)
    
    def get_function_metrics(self, func_name: Optional[str] = None) -> Dict[str, Any]:
        """获取函数性能指标。
        
        Args:
            func_name: 函数名称，如果为None则返回所有函数的指标
        
        Returns:
            性能指标字典
        """
        if func_name:
            if func_name in self.metrics:
                metric = self.metrics[func_name]
                return {
                    'function_name': metric.function_name,
                    'call_count': metric.call_count,
                    'avg_execution_time': metric.avg_execution_time,
                    'last_execution_time': metric.execution_time,
                    'memory_usage': metric.memory_usage,
                    'max_memory': metric.max_memory,
                    'min_memory': metric.min_memory,
                    'cpu_usage': metric.cpu_usage,
                    'last_timestamp': metric.timestamp
                }
            else:
                return {}
        else:
            return {
                name: {
                    'function_name': metric.function_name,
                    'call_count': metric.call_count,
                    'avg_execution_time': metric.avg_execution_time,
                    'last_execution_time': metric.execution_time,
                    'memory_usage': metric.memory_usage,
                    'max_memory': metric.max_memory,
                    'min_memory': metric.min_memory,
                    'cpu_usage': metric.cpu_usage,
                    'last_timestamp': metric.timestamp
                }
                for name, metric in self.metrics.items()
            }
    
    def get_system_metrics(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取系统性能指标。
        
        Args:
            last_n: 返回最近的N条记录，如果为None则返回所有记录
        
        Returns:
            系统指标列表
        """
        metrics = self.system_metrics[-last_n:] if last_n else self.system_metrics
        return [
            {
                'cpu_percent': metric.cpu_percent,
                'memory_percent': metric.memory_percent,
                'memory_available': metric.memory_available,
                'memory_used': metric.memory_used,
                'disk_usage': metric.disk_usage,
                'network_io': metric.network_io,
                'timestamp': metric.timestamp
            }
            for metric in metrics
        ]
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """生成性能报告。
        
        Args:
            output_file: 输出文件路径，如果提供则保存到文件
        
        Returns:
            性能报告字典
        """
        report = {
            'timestamp': time.time(),
            'summary': {
                'total_functions': len(self.metrics),
                'total_system_records': len(self.system_metrics)
            },
            'function_metrics': self.get_function_metrics(),
            'system_metrics_summary': self._get_system_summary(),
            'top_performers': self._get_top_performers(),
            'recommendations': self._get_recommendations()
        }
        
        if output_file:
            try:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"性能报告已保存到: {output_path}")
            except Exception as e:
                self.logger.error(f"保存性能报告失败: {e}")
        
        return report
    
    def _get_system_summary(self) -> Dict[str, Any]:
        """获取系统指标摘要。"""
        if not self.system_metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in self.system_metrics]
        memory_values = [m.memory_percent for m in self.system_metrics]
        
        return {
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'latest': {
                'cpu_percent': self.system_metrics[-1].cpu_percent,
                'memory_percent': self.system_metrics[-1].memory_percent,
                'disk_usage': self.system_metrics[-1].disk_usage
            }
        }
    
    def _get_top_performers(self) -> Dict[str, Any]:
        """获取性能最佳和最差的函数。"""
        if not self.metrics:
            return {}
        
        # 按平均执行时间排序
        sorted_by_time = sorted(
            self.metrics.items(), 
            key=lambda x: x[1].avg_execution_time
        )
        
        # 按内存使用排序
        sorted_by_memory = sorted(
            self.metrics.items(), 
            key=lambda x: x[1].max_memory, 
            reverse=True
        )
        
        return {
            'fastest_functions': [
                {
                    'name': name,
                    'avg_time': metric.avg_execution_time,
                    'call_count': metric.call_count
                }
                for name, metric in sorted_by_time[:5]
            ],
            'slowest_functions': [
                {
                    'name': name,
                    'avg_time': metric.avg_execution_time,
                    'call_count': metric.call_count
                }
                for name, metric in sorted_by_time[-5:]
            ],
            'memory_intensive_functions': [
                {
                    'name': name,
                    'max_memory': metric.max_memory,
                    'avg_memory': metric.memory_usage
                }
                for name, metric in sorted_by_memory[:5]
            ]
        }
    
    def _get_recommendations(self) -> List[str]:
        """生成性能优化建议。"""
        recommendations = []
        
        if not self.metrics:
            return recommendations
        
        # 检查慢函数
        slow_functions = [
            name for name, metric in self.metrics.items()
            if metric.avg_execution_time > 1.0  # 超过1秒
        ]
        
        if slow_functions:
            recommendations.append(
                f"以下函数执行时间较长，建议优化: {', '.join(slow_functions)}"
            )
        
        # 检查内存使用
        memory_intensive = [
            name for name, metric in self.metrics.items()
            if metric.max_memory > 100  # 超过100MB
        ]
        
        if memory_intensive:
            recommendations.append(
                f"以下函数内存使用较高，建议检查内存泄漏: {', '.join(memory_intensive)}"
            )
        
        # 检查系统资源
        if self.system_metrics:
            latest = self.system_metrics[-1]
            if latest.cpu_percent > 80:
                recommendations.append("CPU使用率较高，建议检查计算密集型操作")
            if latest.memory_percent > 80:
                recommendations.append("内存使用率较高，建议优化内存使用")
        
        return recommendations
    
    def reset_metrics(self):
        """重置所有性能指标。"""
        self.metrics.clear()
        self.system_metrics.clear()
        self.logger.info("性能指标已重置")
    
    def __enter__(self):
        """上下文管理器入口。"""
        self.start_system_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""
        self.stop_system_monitoring()


# 全局性能分析器实例
profiler = PerformanceProfiler()


# 便捷装饰器
def profile_performance(func_name: Optional[str] = None):
    """性能分析装饰器的便捷函数。"""
    return profiler.profile(func_name)


def get_performance_metrics(func_name: Optional[str] = None) -> Dict[str, Any]:
    """获取性能指标的便捷函数。"""
    return profiler.get_function_metrics(func_name)


def generate_performance_report(output_file: Optional[str] = None) -> Dict[str, Any]:
    """生成性能报告的便捷函数。"""
    return profiler.generate_report(output_file)


def start_monitoring(interval: float = 1.0):
    """开始系统监控的便捷函数。"""
    profiler.start_system_monitoring(interval)


def stop_monitoring():
    """停止系统监控的便捷函数。"""
    profiler.stop_system_monitoring()