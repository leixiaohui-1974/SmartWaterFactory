#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可视化增强功能演示脚本。

本脚本演示智能水厂系统的增强可视化功能，包括：
1. 实时监控仪表板
2. 交互式图表展示
3. 数据分析和趋势检测
4. 性能监控可视化
5. 主题和样式定制
"""

import sys
import os
import time
import random
import numpy as np
import threading
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.visualization import (
    VisualizationConfig, DataSeries, RealTimeChart,
    RealTimeMonitoringDashboard, DataAnalyzer,
    create_real_time_chart, create_monitoring_dashboard,
    analyze_data_series
)
from utils.performance import PerformanceProfiler
from utils.logging_system import get_logger

# 设置日志
logger = get_logger("visualization_demo")


def demo_basic_chart():
    """演示基本图表功能。"""
    print("\n" + "="*60)
    print("1. 基本图表功能演示")
    print("="*60)
    
    # 创建配置
    config = VisualizationConfig(
        update_interval=0.5,
        theme='default',
        figure_size=(10, 6),
        show_grid=True
    )
    
    # 创建图表
    chart = create_real_time_chart("水质参数监控", "浓度", config)
    
    # 添加数据序列
    turbidity_series = chart.add_series("浊度", color='blue', unit='NTU')
    do_series = chart.add_series("溶解氧", color='red', unit='mg/L')
    ph_series = chart.add_series("pH值", color='green', unit='')
    
    print("已创建图表，包含3个数据序列：")
    print(f"  - 浊度 (蓝色, {turbidity_series.unit})")
    print(f"  - 溶解氧 (红色, {do_series.unit})")
    print(f"  - pH值 (绿色, {ph_series.unit})")
    
    # 模拟数据更新
    print("\n开始模拟数据更新...")
    for i in range(20):
        timestamp = datetime.now() + timedelta(seconds=i)
        
        # 模拟水质数据
        turbidity = 2.0 + random.gauss(0, 0.3)
        dissolved_oxygen = 8.0 + random.gauss(0, 0.5)
        ph_value = 7.2 + random.gauss(0, 0.2)
        
        # 更新数据
        chart.update_data("浊度", max(0, turbidity), timestamp)
        chart.update_data("溶解氧", max(0, dissolved_oxygen), timestamp)
        chart.update_data("pH值", max(0, ph_value), timestamp)
        
        if i % 5 == 0:
            print(f"  第{i+1}次更新: 浊度={turbidity:.2f}, 溶解氧={dissolved_oxygen:.2f}, pH={ph_value:.2f}")
        
        time.sleep(0.1)
    
    # 保存图表
    chart_filename = "water_quality_chart.png"
    chart.save_chart(chart_filename)
    print(f"\n图表已保存为: {chart_filename}")
    
    # 显示数据统计
    print("\n数据统计:")
    for name, series in chart.data_series.items():
        if len(series.data) > 0:
            print(f"  {name}: {len(series.data)}个数据点, 范围[{series.min_value:.2f}, {series.max_value:.2f}] {series.unit}")


def demo_data_analysis():
    """演示数据分析功能。"""
    print("\n" + "="*60)
    print("2. 数据分析功能演示")
    print("="*60)
    
    # 创建数据分析器
    analyzer = DataAnalyzer()
    
    # 创建测试数据序列
    print("创建测试数据序列...")
    
    # 1. 上升趋势数据
    increasing_series = DataSeries(name="上升趋势", unit="units")
    for i in range(50):
        value = 10 + i * 0.5 + random.gauss(0, 1.0)
        timestamp = datetime.now() + timedelta(minutes=i)
        increasing_series.add_point(value, timestamp)
    
    # 2. 下降趋势数据
    decreasing_series = DataSeries(name="下降趋势", unit="units")
    for i in range(50):
        value = 50 - i * 0.3 + random.gauss(0, 0.8)
        timestamp = datetime.now() + timedelta(minutes=i)
        decreasing_series.add_point(value, timestamp)
    
    # 3. 稳定数据（带异常值）
    stable_series = DataSeries(name="稳定数据", unit="units")
    for i in range(50):
        if i == 25:  # 添加异常值
            value = 100.0
        else:
            value = 30.0 + random.gauss(0, 2.0)
        timestamp = datetime.now() + timedelta(minutes=i)
        stable_series.add_point(value, timestamp)
    
    # 分析各个数据序列
    test_series = {
        "上升趋势": increasing_series,
        "下降趋势": decreasing_series,
        "稳定数据": stable_series
    }
    
    print("\n趋势分析结果:")
    for name, series in test_series.items():
        trends = analyzer.analyze_trends(series, window_size=20)
        print(f"\n  {name}:")
        print(f"    趋势: {trends['trend']}")
        print(f"    斜率: {trends['slope']:.4f}")
        print(f"    拟合度(R²): {trends['r_squared']:.4f}")
        print(f"    均值: {trends['mean']:.2f}")
        print(f"    标准差: {trends['std']:.2f}")
        print(f"    范围: [{trends['min']:.2f}, {trends['max']:.2f}]")
    
    # 异常检测
    print("\n异常检测结果:")
    for name, series in test_series.items():
        anomalies = analyzer.detect_anomalies(series, threshold=2.0)
        print(f"\n  {name}: 检测到 {len(anomalies)} 个异常值")
        
        if anomalies:
            for timestamp, value in anomalies[:3]:  # 只显示前3个
                print(f"    异常值: {value:.2f} (时间: {timestamp.strftime('%H:%M:%S')})")
    
    # 生成汇总报告
    print("\n生成汇总报告...")
    report = analyzer.generate_summary_report(test_series)
    
    print(f"\n汇总报告 (生成时间: {report['timestamp'][:19]}):")
    print(f"  数据序列数量: {report['series_count']}")
    
    for name, analysis in report['series_analysis'].items():
        print(f"\n  {name}:")
        print(f"    数据点数: {analysis['data_points']}")
        print(f"    趋势: {analysis['trends']['trend']}")
        print(f"    异常值数量: {analysis['anomaly_count']}")
        print(f"    最新值: {analysis['latest_value']:.2f} {analysis['unit']}")


def demo_theme_customization():
    """演示主题定制功能。"""
    print("\n" + "="*60)
    print("3. 主题定制功能演示")
    print("="*60)
    
    themes = ['default', 'dark', 'light']
    
    for theme in themes:
        print(f"\n创建 {theme} 主题图表...")
        
        # 创建主题配置
        config = VisualizationConfig(
            theme=theme,
            figure_size=(8, 5),
            line_width=2.5,
            marker_size=5.0
        )
        
        # 创建图表
        chart = create_real_time_chart(f"{theme.title()} 主题演示", "数值", config)
        
        # 添加数据序列
        series1 = chart.add_series("数据1", color='blue', line_style='-')
        series2 = chart.add_series("数据2", color='red', line_style='--')
        series3 = chart.add_series("数据3", color='green', line_style='-.')
        
        # 添加示例数据
        for i in range(30):
            timestamp = datetime.now() + timedelta(seconds=i)
            chart.update_data("数据1", 10 + 5 * np.sin(i * 0.2) + random.gauss(0, 0.5), timestamp)
            chart.update_data("数据2", 15 + 3 * np.cos(i * 0.3) + random.gauss(0, 0.3), timestamp)
            chart.update_data("数据3", 12 + 2 * np.sin(i * 0.1) + random.gauss(0, 0.4), timestamp)
        
        # 保存图表
        filename = f"theme_{theme}_demo.png"
        chart.save_chart(filename)
        print(f"  {theme} 主题图表已保存为: {filename}")
        
        # 显示配置信息
        print(f"  配置: 主题={config.theme}, 尺寸={config.figure_size}, 线宽={config.line_width}")


def demo_performance_integration():
    """演示性能监控集成。"""
    print("\n" + "="*60)
    print("4. 性能监控集成演示")
    print("="*60)
    
    # 创建性能分析器
    profiler = PerformanceProfiler()
    
    # 创建性能监控图表
    config = VisualizationConfig(
        update_interval=1.0,
        theme='dark',
        figure_size=(12, 6)
    )
    
    perf_chart = create_real_time_chart("系统性能监控", "使用率 (%)", config)
    
    # 添加性能指标序列
    cpu_series = perf_chart.add_series("CPU使用率", color='orange', unit='%')
    memory_series = perf_chart.add_series("内存使用率", color='purple', unit='%')
    
    print("启动性能监控...")
    profiler.start_system_monitoring(interval=0.5)
    
    # 模拟一些计算任务
    @profiler.profile()
    def cpu_intensive_task():
        """CPU密集型任务。"""
        result = sum(i**2 for i in range(10000))
        return result
    
    @profiler.profile()
    def memory_intensive_task():
        """内存密集型任务。"""
        data = [random.random() for _ in range(100000)]
        return sum(data)
    
    print("执行性能测试任务...")
    
    # 收集性能数据
    for i in range(10):
        # 执行任务
        if i % 2 == 0:
            cpu_intensive_task()
        else:
            memory_intensive_task()
        
        # 获取系统指标
        system_metrics = profiler.get_system_metrics()
        if system_metrics:
            latest_metric = system_metrics[-1]
            timestamp = datetime.now()
            
            # 更新图表
            perf_chart.update_data("CPU使用率", latest_metric['cpu_percent'], timestamp)
            perf_chart.update_data("内存使用率", latest_metric['memory_percent'], timestamp)
            
            print(f"  第{i+1}次: CPU={latest_metric['cpu_percent']:.1f}%, 内存={latest_metric['memory_percent']:.1f}%")
        
        time.sleep(1)
    
    # 停止监控
    profiler.stop_system_monitoring()
    
    # 保存性能图表
    perf_filename = "performance_monitoring.png"
    perf_chart.save_chart(perf_filename)
    print(f"\n性能监控图表已保存为: {perf_filename}")
    
    # 显示性能统计
    function_metrics = profiler.get_function_metrics()
    if function_metrics:
        print("\n函数性能统计:")
        for func_name, metrics in function_metrics.items():
            print(f"  {func_name}:")
            print(f"    调用次数: {metrics['call_count']}")
            print(f"    平均执行时间: {metrics['avg_execution_time']:.4f}秒")
            print(f"    内存使用: {metrics['memory_usage']:.2f}MB")


def demo_interactive_dashboard():
    """演示交互式仪表板。"""
    print("\n" + "="*60)
    print("5. 交互式仪表板演示")
    print("="*60)
    
    print("准备启动实时监控仪表板...")
    print("\n仪表板功能:")
    print("  - 水质监控标签页: 实时显示浊度、溶解氧、pH值")
    print("  - 性能监控标签页: 系统CPU、内存、磁盘使用率")
    print("  - 系统状态标签页: 详细的系统信息和进程状态")
    print("\n控制操作:")
    print("  - 点击'开始监控'按钮启动实时数据更新")
    print("  - 点击'停止监控'按钮暂停数据更新")
    print("  - 点击'保存图表'按钮导出当前图表")
    print("  - 关闭窗口退出仪表板")
    
    # 询问用户是否启动仪表板
    response = input("\n是否启动交互式仪表板? (y/n): ").lower().strip()
    
    if response == 'y' or response == 'yes':
        try:
            print("\n启动仪表板...")
            
            # 创建配置
            config = VisualizationConfig(
                update_interval=1.0,
                theme='default',
                figure_size=(10, 6)
            )
            
            # 创建并运行仪表板
            dashboard = create_monitoring_dashboard(config)
            
            print("仪表板已启动！请在弹出的窗口中操作。")
            print("关闭窗口或按Ctrl+C退出。")
            
            # 运行仪表板（这会阻塞直到窗口关闭）
            dashboard.run()
            
            print("\n仪表板已关闭。")
            
        except ImportError as e:
            print(f"\n无法启动仪表板: {e}")
            print("请确保已安装tkinter: pip install tkinter")
        except Exception as e:
            print(f"\n启动仪表板时发生错误: {e}")
    else:
        print("\n跳过交互式仪表板演示。")


def demo_advanced_analysis():
    """演示高级分析功能。"""
    print("\n" + "="*60)
    print("6. 高级分析功能演示")
    print("="*60)
    
    # 创建复杂的测试数据
    print("生成复杂测试数据...")
    
    # 1. 周期性数据
    periodic_series = DataSeries(name="周期性数据", unit="units")
    for i in range(100):
        # 添加周期性成分、趋势和噪声
        periodic_component = 10 * np.sin(2 * np.pi * i / 20)
        trend_component = 0.1 * i
        noise_component = random.gauss(0, 1.0)
        value = 50 + periodic_component + trend_component + noise_component
        
        timestamp = datetime.now() + timedelta(minutes=i)
        periodic_series.add_point(value, timestamp)
    
    # 2. 带突变的数据
    step_series = DataSeries(name="突变数据", unit="units")
    for i in range(100):
        if i < 30:
            base_value = 20
        elif i < 70:
            base_value = 35  # 突变
        else:
            base_value = 25  # 回落
        
        value = base_value + random.gauss(0, 2.0)
        timestamp = datetime.now() + timedelta(minutes=i)
        step_series.add_point(value, timestamp)
    
    # 3. 带多个异常值的数据
    anomaly_series = DataSeries(name="异常数据", unit="units")
    for i in range(100):
        if i in [15, 45, 75]:  # 添加异常值
            value = 100 + random.gauss(0, 5.0)
        else:
            value = 30 + random.gauss(0, 3.0)
        
        timestamp = datetime.now() + timedelta(minutes=i)
        anomaly_series.add_point(value, timestamp)
    
    # 创建分析器
    analyzer = DataAnalyzer()
    
    # 分析各种数据模式
    test_data = {
        "周期性数据": periodic_series,
        "突变数据": step_series,
        "异常数据": anomaly_series
    }
    
    print("\n高级分析结果:")
    
    for name, series in test_data.items():
        print(f"\n=== {name} ===")
        
        # 短期趋势分析
        short_trends = analyzer.analyze_trends(series, window_size=10)
        print(f"短期趋势 (10点窗口):")
        print(f"  趋势: {short_trends['trend']}")
        print(f"  斜率: {short_trends['slope']:.4f}")
        print(f"  拟合度: {short_trends['r_squared']:.4f}")
        
        # 长期趋势分析
        long_trends = analyzer.analyze_trends(series, window_size=30)
        print(f"长期趋势 (30点窗口):")
        print(f"  趋势: {long_trends['trend']}")
        print(f"  斜率: {long_trends['slope']:.4f}")
        print(f"  拟合度: {long_trends['r_squared']:.4f}")
        
        # 异常检测（不同阈值）
        strict_anomalies = analyzer.detect_anomalies(series, threshold=2.0)
        loose_anomalies = analyzer.detect_anomalies(series, threshold=3.0)
        
        print(f"异常检测:")
        print(f"  严格阈值(2σ): {len(strict_anomalies)} 个异常")
        print(f"  宽松阈值(3σ): {len(loose_anomalies)} 个异常")
        
        # 时间窗口分析
        recent_timestamps, recent_data = series.get_recent_data(30)  # 最近30分钟
        if recent_data:
            recent_mean = np.mean(recent_data)
            recent_std = np.std(recent_data)
            print(f"最近30分钟统计:")
            print(f"  均值: {recent_mean:.2f}")
            print(f"  标准差: {recent_std:.2f}")
            print(f"  数据点数: {len(recent_data)}")
    
    # 生成综合报告
    print("\n生成综合分析报告...")
    comprehensive_report = analyzer.generate_summary_report(test_data)
    
    print(f"\n=== 综合分析报告 ===")
    print(f"报告时间: {comprehensive_report['timestamp'][:19]}")
    print(f"分析序列数: {comprehensive_report['series_count']}")
    
    # 汇总统计
    total_anomalies = sum(analysis['anomaly_count'] for analysis in comprehensive_report['series_analysis'].values())
    trend_summary = {}
    
    for analysis in comprehensive_report['series_analysis'].values():
        trend = analysis['trends']['trend']
        trend_summary[trend] = trend_summary.get(trend, 0) + 1
    
    print(f"\n总体统计:")
    print(f"  总异常值数量: {total_anomalies}")
    print(f"  趋势分布: {dict(trend_summary)}")
    
    # 保存分析结果
    import json
    report_filename = "advanced_analysis_report.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n详细报告已保存为: {report_filename}")


def main():
    """主函数。"""
    print("智能水厂可视化增强功能演示")
    print("="*60)
    
    try:
        # 设置matplotlib后端
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        
        # 运行各个演示
        demo_basic_chart()
        demo_data_analysis()
        demo_theme_customization()
        demo_performance_integration()
        demo_advanced_analysis()
        
        # 最后运行交互式仪表板（如果用户选择）
        demo_interactive_dashboard()
        
        print("\n" + "="*60)
        print("演示完成！")
        print("="*60)
        
        print("\n生成的文件:")
        generated_files = [
            "water_quality_chart.png",
            "theme_default_demo.png",
            "theme_dark_demo.png",
            "theme_light_demo.png",
            "performance_monitoring.png",
            "advanced_analysis_report.json"
        ]
        
        for filename in generated_files:
            if os.path.exists(filename):
                print(f"  ✓ {filename}")
            else:
                print(f"  ✗ {filename} (未生成)")
        
        print("\n功能特性总结:")
        print("  ✓ 实时图表和数据更新")
        print("  ✓ 多主题支持 (默认/深色/浅色)")
        print("  ✓ 数据趋势分析和异常检测")
        print("  ✓ 性能监控集成")
        print("  ✓ 交互式监控仪表板")
        print("  ✓ 高级数据分析和报告生成")
        
    except KeyboardInterrupt:
        print("\n\n演示被用户中断。")
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        print(f"\n错误: {e}")
        print("请检查依赖项是否正确安装。")
    finally:
        print("\n感谢使用智能水厂可视化系统！")


if __name__ == '__main__':
    main()