#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强的可视化系统。

本模块提供了智能水厂系统的高级可视化功能，包括：
1. 实时监控仪表板
2. 交互式图表和分析工具
3. 性能监控可视化
4. 数据趋势分析
5. 多维数据展示
"""

import time
import threading
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import json
from pathlib import Path
import logging
from datetime import datetime, timedelta

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


@dataclass
class VisualizationConfig:
    """可视化配置类。"""
    update_interval: float = 1.0  # 更新间隔（秒）
    max_data_points: int = 1000   # 最大数据点数
    figure_size: Tuple[int, int] = (12, 8)
    dpi: int = 100
    theme: str = 'default'  # 主题：default, dark, light
    auto_scale: bool = True
    show_grid: bool = True
    show_legend: bool = True
    line_width: float = 2.0
    marker_size: float = 4.0


@dataclass
class DataSeries:
    """数据序列类。"""
    name: str
    data: deque = field(default_factory=lambda: deque(maxlen=1000))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    color: str = 'blue'
    line_style: str = '-'
    marker: str = 'o'
    unit: str = ''
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def add_point(self, value: float, timestamp: Optional[datetime] = None):
        """添加数据点。"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.data.append(value)
        self.timestamps.append(timestamp)
        
        # 更新最值
        if self.min_value is None or value < self.min_value:
            self.min_value = value
        if self.max_value is None or value > self.max_value:
            self.max_value = value
    
    def get_recent_data(self, duration_minutes: int = 60) -> Tuple[List[datetime], List[float]]:
        """获取最近指定时间内的数据。"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        recent_timestamps = []
        recent_data = []
        
        for ts, value in zip(self.timestamps, self.data):
            if ts >= cutoff_time:
                recent_timestamps.append(ts)
                recent_data.append(value)
        
        return recent_timestamps, recent_data


class RealTimeChart:
    """实时图表类。"""
    
    def __init__(self, title: str, ylabel: str, config: VisualizationConfig):
        """初始化实时图表。"""
        self.title = title
        self.ylabel = ylabel
        self.config = config
        self.data_series: Dict[str, DataSeries] = {}
        
        # 创建图表
        self.fig, self.ax = plt.subplots(figsize=config.figure_size, dpi=config.dpi)
        self.ax.set_title(title, fontsize=14, fontweight='bold')
        self.ax.set_ylabel(ylabel, fontsize=12)
        self.ax.set_xlabel('时间', fontsize=12)
        
        if config.show_grid:
            self.ax.grid(True, alpha=0.3)
        
        # 应用主题
        self._apply_theme()
        
        # 线条对象字典
        self.lines: Dict[str, plt.Line2D] = {}
        
        # 动画对象
        self.animation = None
        self.is_running = False
    
    def _apply_theme(self):
        """应用主题样式。"""
        if self.config.theme == 'dark':
            self.fig.patch.set_facecolor('#2E2E2E')
            self.ax.set_facecolor('#3E3E3E')
            self.ax.tick_params(colors='white')
            self.ax.xaxis.label.set_color('white')
            self.ax.yaxis.label.set_color('white')
            self.ax.title.set_color('white')
            self.ax.spines['bottom'].set_color('white')
            self.ax.spines['top'].set_color('white')
            self.ax.spines['right'].set_color('white')
            self.ax.spines['left'].set_color('white')
        elif self.config.theme == 'light':
            self.fig.patch.set_facecolor('white')
            self.ax.set_facecolor('white')
    
    def add_series(self, name: str, color: str = 'blue', line_style: str = '-', 
                   marker: str = 'o', unit: str = '') -> DataSeries:
        """添加数据序列。"""
        series = DataSeries(
            name=name, color=color, line_style=line_style, 
            marker=marker, unit=unit
        )
        self.data_series[name] = series
        
        # 创建线条对象
        line, = self.ax.plot([], [], color=color, linestyle=line_style,
                            marker=marker, markersize=self.config.marker_size,
                            linewidth=self.config.line_width, label=name)
        self.lines[name] = line
        
        if self.config.show_legend:
            self.ax.legend()
        
        return series
    
    def update_data(self, series_name: str, value: float, timestamp: Optional[datetime] = None):
        """更新数据。"""
        if series_name in self.data_series:
            self.data_series[series_name].add_point(value, timestamp)
    
    def _animate(self, frame):
        """动画更新函数。"""
        for name, series in self.data_series.items():
            if len(series.data) > 0:
                timestamps = list(series.timestamps)
                data = list(series.data)
                
                self.lines[name].set_data(timestamps, data)
        
        # 自动调整坐标轴
        if self.config.auto_scale and any(len(s.data) > 0 for s in self.data_series.values()):
            self.ax.relim()
            self.ax.autoscale_view()
        
        return list(self.lines.values())
    
    def start_animation(self):
        """开始动画。"""
        if not self.is_running:
            self.animation = animation.FuncAnimation(
                self.fig, self._animate, interval=int(self.config.update_interval * 1000),
                blit=False, cache_frame_data=False
            )
            self.is_running = True
    
    def stop_animation(self):
        """停止动画。"""
        if self.animation:
            self.animation.event_source.stop()
            self.is_running = False
    
    def save_chart(self, filename: str):
        """保存图表。"""
        self.fig.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')


class PerformanceMonitorWidget:
    """性能监控小部件。"""
    
    def __init__(self, parent, config: VisualizationConfig):
        """初始化性能监控小部件。"""
        self.parent = parent
        self.config = config
        
        # 创建框架
        self.frame = ttk.LabelFrame(parent, text="系统性能监控", padding=10)
        
        # 创建性能指标标签
        self.cpu_label = ttk.Label(self.frame, text="CPU使用率: --")
        self.memory_label = ttk.Label(self.frame, text="内存使用率: --")
        self.disk_label = ttk.Label(self.frame, text="磁盘使用率: --")
        
        # 创建进度条
        self.cpu_progress = ttk.Progressbar(self.frame, length=200, mode='determinate')
        self.memory_progress = ttk.Progressbar(self.frame, length=200, mode='determinate')
        self.disk_progress = ttk.Progressbar(self.frame, length=200, mode='determinate')
        
        # 布局
        self.cpu_label.grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.cpu_progress.grid(row=0, column=1, padx=5, pady=2)
        
        self.memory_label.grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.memory_progress.grid(row=1, column=1, padx=5, pady=2)
        
        self.disk_label.grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.disk_progress.grid(row=2, column=1, padx=5, pady=2)
    
    def update_metrics(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """更新性能指标。"""
        # 更新标签
        self.cpu_label.config(text=f"CPU使用率: {cpu_percent:.1f}%")
        self.memory_label.config(text=f"内存使用率: {memory_percent:.1f}%")
        self.disk_label.config(text=f"磁盘使用率: {disk_percent:.1f}%")
        
        # 更新进度条
        self.cpu_progress['value'] = cpu_percent
        self.memory_progress['value'] = memory_percent
        self.disk_progress['value'] = disk_percent
        
        # 根据使用率设置颜色
        self._update_progress_color(self.cpu_progress, cpu_percent)
        self._update_progress_color(self.memory_progress, memory_percent)
        self._update_progress_color(self.disk_progress, disk_percent)
    
    def _update_progress_color(self, progress_bar, value):
        """根据值更新进度条颜色。"""
        if value > 80:
            progress_bar.configure(style='Red.Horizontal.TProgressbar')
        elif value > 60:
            progress_bar.configure(style='Yellow.Horizontal.TProgressbar')
        else:
            progress_bar.configure(style='Green.Horizontal.TProgressbar')


class RealTimeMonitoringDashboard:
    """实时监控仪表板。"""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        """初始化监控仪表板。"""
        self.config = config or VisualizationConfig()
        self.logger = logging.getLogger(__name__)
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("智能水厂实时监控系统")
        self.root.geometry("1200x800")
        
        # 数据存储
        self.charts: Dict[str, RealTimeChart] = {}
        self.performance_widget: Optional[PerformanceMonitorWidget] = None
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 创建界面
        self._create_ui()
        
        # 设置样式
        self._setup_styles()
    
    def _create_ui(self):
        """创建用户界面。"""
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 控制按钮
        self.start_button = ttk.Button(control_frame, text="开始监控", command=self.start_monitoring)
        self.stop_button = ttk.Button(control_frame, text="停止监控", command=self.stop_monitoring, state='disabled')
        self.save_button = ttk.Button(control_frame, text="保存图表", command=self.save_charts)
        
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(control_frame, text="状态: 未开始")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建水质监控标签页
        self._create_water_quality_tab()
        
        # 创建性能监控标签页
        self._create_performance_tab()
        
        # 创建系统监控标签页
        self._create_system_tab()
    
    def _create_water_quality_tab(self):
        """创建水质监控标签页。"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="水质监控")
        
        # 创建水质图表
        water_chart = RealTimeChart("水质参数实时监控", "数值", self.config)
        water_chart.add_series("浊度", color='blue', unit='NTU')
        water_chart.add_series("溶解氧", color='red', unit='mg/L')
        water_chart.add_series("pH值", color='green', unit='')
        
        self.charts['water_quality'] = water_chart
        
        # 嵌入图表
        canvas = FigureCanvasTkAgg(water_chart.fig, tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_performance_tab(self):
        """创建性能监控标签页。"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="性能监控")
        
        # 创建性能图表
        perf_chart = RealTimeChart("系统性能监控", "使用率 (%)", self.config)
        perf_chart.add_series("CPU使用率", color='orange', unit='%')
        perf_chart.add_series("内存使用率", color='purple', unit='%')
        perf_chart.add_series("磁盘使用率", color='brown', unit='%')
        
        self.charts['performance'] = perf_chart
        
        # 嵌入图表
        canvas = FigureCanvasTkAgg(perf_chart.fig, tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_system_tab(self):
        """创建系统监控标签页。"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="系统状态")
        
        # 创建性能监控小部件
        self.performance_widget = PerformanceMonitorWidget(tab_frame, self.config)
        self.performance_widget.frame.pack(fill=tk.X, pady=10)
        
        # 创建系统信息显示区域
        info_frame = ttk.LabelFrame(tab_frame, text="系统信息", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建文本框显示系统信息
        self.info_text = tk.Text(info_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _setup_styles(self):
        """设置样式。"""
        style = ttk.Style()
        
        # 定义进度条样式
        style.configure('Green.Horizontal.TProgressbar', background='green')
        style.configure('Yellow.Horizontal.TProgressbar', background='yellow')
        style.configure('Red.Horizontal.TProgressbar', background='red')
    
    def start_monitoring(self):
        """开始监控。"""
        if not self.is_monitoring:
            self.is_monitoring = True
            
            # 启动图表动画
            for chart in self.charts.values():
                chart.start_animation()
            
            # 启动监控线程
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            # 更新界面
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.status_label.config(text="状态: 监控中")
            
            self.logger.info("实时监控已启动")
    
    def stop_monitoring(self):
        """停止监控。"""
        if self.is_monitoring:
            self.is_monitoring = False
            
            # 停止图表动画
            for chart in self.charts.values():
                chart.stop_animation()
            
            # 更新界面
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.status_label.config(text="状态: 已停止")
            
            self.logger.info("实时监控已停止")
    
    def _monitoring_loop(self):
        """监控循环。"""
        import psutil
        import random
        
        while self.is_monitoring:
            try:
                # 模拟水质数据
                turbidity = 2.0 + random.gauss(0, 0.5)
                dissolved_oxygen = 8.0 + random.gauss(0, 1.0)
                ph_value = 7.2 + random.gauss(0, 0.3)
                
                # 更新水质图表
                if 'water_quality' in self.charts:
                    self.charts['water_quality'].update_data('浊度', max(0, turbidity))
                    self.charts['water_quality'].update_data('溶解氧', max(0, dissolved_oxygen))
                    self.charts['water_quality'].update_data('pH值', max(0, ph_value))
                
                # 获取系统性能数据
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent
                
                # 更新性能图表
                if 'performance' in self.charts:
                    self.charts['performance'].update_data('CPU使用率', cpu_percent)
                    self.charts['performance'].update_data('内存使用率', memory_percent)
                    self.charts['performance'].update_data('磁盘使用率', disk_percent)
                
                # 更新性能小部件
                if self.performance_widget:
                    self.root.after(0, lambda: self.performance_widget.update_metrics(
                        cpu_percent, memory_percent, disk_percent
                    ))
                
                # 更新系统信息
                info_text = f"""系统监控信息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

水质参数:
  浊度: {turbidity:.2f} NTU
  溶解氧: {dissolved_oxygen:.2f} mg/L
  pH值: {ph_value:.2f}

系统性能:
  CPU使用率: {cpu_percent:.1f}%
  内存使用率: {memory_percent:.1f}%
  磁盘使用率: {disk_percent:.1f}%

进程信息:
  进程ID: {psutil.Process().pid}
  线程数: {psutil.Process().num_threads()}
  内存使用: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB
"""
                
                # 在主线程中更新文本
                self.root.after(0, lambda: self._update_info_text(info_text))
                
                time.sleep(self.config.update_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(1)
    
    def _update_info_text(self, text: str):
        """更新信息文本。"""
        if hasattr(self, 'info_text'):
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, text)
    
    def save_charts(self):
        """保存所有图表。"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for name, chart in self.charts.items():
                filename = f"chart_{name}_{timestamp}.png"
                chart.save_chart(filename)
                self.logger.info(f"图表已保存: {filename}")
            
            messagebox.showinfo("保存成功", f"所有图表已保存，时间戳: {timestamp}")
            
        except Exception as e:
            self.logger.error(f"保存图表失败: {e}")
            messagebox.showerror("保存失败", f"保存图表时发生错误: {e}")
    
    def run(self):
        """运行仪表板。"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop_monitoring()
        finally:
            self.stop_monitoring()


class DataAnalyzer:
    """数据分析器。"""
    
    def __init__(self):
        """初始化数据分析器。"""
        self.logger = logging.getLogger(__name__)
    
    def analyze_trends(self, data_series: DataSeries, window_size: int = 10) -> Dict[str, Any]:
        """分析数据趋势。"""
        if len(data_series.data) < window_size:
            return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0}
        
        # 获取最近的数据
        recent_data = list(data_series.data)[-window_size:]
        x = np.arange(len(recent_data))
        y = np.array(recent_data)
        
        # 线性回归
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        # 计算R²
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # 判断趋势
        if abs(slope) < 0.01:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'slope': slope,
            'r_squared': r_squared,
            'mean': np.mean(recent_data),
            'std': np.std(recent_data),
            'min': np.min(recent_data),
            'max': np.max(recent_data)
        }
    
    def detect_anomalies(self, data_series: DataSeries, threshold: float = 2.0) -> List[Tuple[datetime, float]]:
        """检测异常值。"""
        if len(data_series.data) < 10:
            return []
        
        data = np.array(list(data_series.data))
        mean = np.mean(data)
        std = np.std(data)
        
        anomalies = []
        for timestamp, value in zip(data_series.timestamps, data_series.data):
            z_score = abs(value - mean) / std if std > 0 else 0
            if z_score > threshold:
                anomalies.append((timestamp, value))
        
        return anomalies
    
    def generate_summary_report(self, data_series: Dict[str, DataSeries]) -> Dict[str, Any]:
        """生成汇总报告。"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'series_count': len(data_series),
            'series_analysis': {}
        }
        
        for name, series in data_series.items():
            if len(series.data) > 0:
                trends = self.analyze_trends(series)
                anomalies = self.detect_anomalies(series)
                
                report['series_analysis'][name] = {
                    'data_points': len(series.data),
                    'trends': trends,
                    'anomaly_count': len(anomalies),
                    'latest_value': list(series.data)[-1] if series.data else None,
                    'unit': series.unit
                }
        
        return report


# 便捷函数
def create_monitoring_dashboard(config: Optional[VisualizationConfig] = None) -> RealTimeMonitoringDashboard:
    """创建监控仪表板的便捷函数。"""
    return RealTimeMonitoringDashboard(config)


def create_real_time_chart(title: str, ylabel: str, config: Optional[VisualizationConfig] = None) -> RealTimeChart:
    """创建实时图表的便捷函数。"""
    config = config or VisualizationConfig()
    return RealTimeChart(title, ylabel, config)


def analyze_data_series(data_series: DataSeries) -> Dict[str, Any]:
    """分析数据序列的便捷函数。"""
    analyzer = DataAnalyzer()
    return analyzer.analyze_trends(data_series)