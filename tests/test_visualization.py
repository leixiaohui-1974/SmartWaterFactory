#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可视化系统测试。

本模块测试可视化系统的各种功能，包括：
1. 实时图表功能
2. 数据序列管理
3. 数据分析功能
4. 配置管理
"""

import unittest
import time
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path

# 添加项目根目录到Python路径
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.visualization import (
    VisualizationConfig, DataSeries, RealTimeChart,
    DataAnalyzer, create_real_time_chart, analyze_data_series
)


class TestVisualizationConfig(unittest.TestCase):
    """测试可视化配置类。"""
    
    def test_default_config(self):
        """测试默认配置。"""
        config = VisualizationConfig()
        
        self.assertEqual(config.update_interval, 1.0)
        self.assertEqual(config.max_data_points, 1000)
        self.assertEqual(config.figure_size, (12, 8))
        self.assertEqual(config.dpi, 100)
        self.assertEqual(config.theme, 'default')
        self.assertTrue(config.auto_scale)
        self.assertTrue(config.show_grid)
        self.assertTrue(config.show_legend)
        self.assertEqual(config.line_width, 2.0)
        self.assertEqual(config.marker_size, 4.0)
    
    def test_custom_config(self):
        """测试自定义配置。"""
        config = VisualizationConfig(
            update_interval=0.5,
            max_data_points=500,
            theme='dark',
            auto_scale=False
        )
        
        self.assertEqual(config.update_interval, 0.5)
        self.assertEqual(config.max_data_points, 500)
        self.assertEqual(config.theme, 'dark')
        self.assertFalse(config.auto_scale)


class TestDataSeries(unittest.TestCase):
    """测试数据序列类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.series = DataSeries(
            name="test_series",
            color="blue",
            unit="test_unit"
        )
    
    def test_initialization(self):
        """测试初始化。"""
        self.assertEqual(self.series.name, "test_series")
        self.assertEqual(self.series.color, "blue")
        self.assertEqual(self.series.unit, "test_unit")
        self.assertEqual(len(self.series.data), 0)
        self.assertEqual(len(self.series.timestamps), 0)
        self.assertIsNone(self.series.min_value)
        self.assertIsNone(self.series.max_value)
    
    def test_add_point(self):
        """测试添加数据点。"""
        timestamp = datetime.now()
        self.series.add_point(10.5, timestamp)
        
        self.assertEqual(len(self.series.data), 1)
        self.assertEqual(len(self.series.timestamps), 1)
        self.assertEqual(self.series.data[0], 10.5)
        self.assertEqual(self.series.timestamps[0], timestamp)
        self.assertEqual(self.series.min_value, 10.5)
        self.assertEqual(self.series.max_value, 10.5)
    
    def test_add_multiple_points(self):
        """测试添加多个数据点。"""
        values = [5.0, 15.0, 8.0, 12.0]
        
        for value in values:
            self.series.add_point(value)
        
        self.assertEqual(len(self.series.data), 4)
        self.assertEqual(self.series.min_value, 5.0)
        self.assertEqual(self.series.max_value, 15.0)
    
    def test_add_point_without_timestamp(self):
        """测试不提供时间戳时添加数据点。"""
        before_time = datetime.now()
        self.series.add_point(7.5)
        after_time = datetime.now()
        
        self.assertEqual(len(self.series.data), 1)
        self.assertEqual(self.series.data[0], 7.5)
        self.assertTrue(before_time <= self.series.timestamps[0] <= after_time)
    
    def test_get_recent_data(self):
        """测试获取最近数据。"""
        now = datetime.now()
        
        # 添加一些旧数据
        old_time = now - timedelta(hours=2)
        self.series.add_point(1.0, old_time)
        
        # 添加一些新数据
        recent_time = now - timedelta(minutes=30)
        self.series.add_point(2.0, recent_time)
        self.series.add_point(3.0, now)
        
        # 获取最近60分钟的数据
        recent_timestamps, recent_data = self.series.get_recent_data(60)
        
        self.assertEqual(len(recent_data), 2)
        self.assertIn(2.0, recent_data)
        self.assertIn(3.0, recent_data)
        self.assertNotIn(1.0, recent_data)
    
    def test_maxlen_behavior(self):
        """测试最大长度限制。"""
        # 创建一个最大长度为5的数据序列
        series = DataSeries(name="test", data=__import__('collections').deque(maxlen=5))
        series.timestamps = __import__('collections').deque(maxlen=5)
        
        # 添加6个数据点
        for i in range(6):
            series.add_point(float(i))
        
        # 应该只保留最后5个
        self.assertEqual(len(series.data), 5)
        self.assertEqual(list(series.data), [1.0, 2.0, 3.0, 4.0, 5.0])


class TestRealTimeChart(unittest.TestCase):
    """测试实时图表类。"""
    
    def setUp(self):
        """设置测试环境。"""
        # 使用Agg后端避免GUI依赖
        import matplotlib
        matplotlib.use('Agg')
        
        self.config = VisualizationConfig()
        self.chart = RealTimeChart("Test Chart", "Test Y-axis", self.config)
    
    def test_initialization(self):
        """测试初始化。"""
        self.assertEqual(self.chart.title, "Test Chart")
        self.assertEqual(self.chart.ylabel, "Test Y-axis")
        self.assertEqual(len(self.chart.data_series), 0)
        self.assertEqual(len(self.chart.lines), 0)
        self.assertFalse(self.chart.is_running)
    
    def test_add_series(self):
        """测试添加数据序列。"""
        series = self.chart.add_series("test_series", color="red", unit="units")
        
        self.assertIsInstance(series, DataSeries)
        self.assertEqual(series.name, "test_series")
        self.assertEqual(series.color, "red")
        self.assertEqual(series.unit, "units")
        self.assertIn("test_series", self.chart.data_series)
        self.assertIn("test_series", self.chart.lines)
    
    def test_update_data(self):
        """测试更新数据。"""
        series = self.chart.add_series("test_series")
        
        timestamp = datetime.now()
        self.chart.update_data("test_series", 10.5, timestamp)
        
        self.assertEqual(len(series.data), 1)
        self.assertEqual(series.data[0], 10.5)
        self.assertEqual(series.timestamps[0], timestamp)
    
    def test_update_nonexistent_series(self):
        """测试更新不存在的数据序列。"""
        # 这应该不会引发错误，只是被忽略
        self.chart.update_data("nonexistent", 5.0)
        self.assertEqual(len(self.chart.data_series), 0)
    
    def test_save_chart(self):
        """测试保存图表。"""
        with patch.object(self.chart.fig, 'savefig') as mock_savefig:
            self.chart.save_chart("test_chart.png")
            mock_savefig.assert_called_once()
    
    def test_theme_application(self):
        """测试主题应用。"""
        # 测试深色主题
        dark_config = VisualizationConfig(theme='dark')
        dark_chart = RealTimeChart("Dark Chart", "Y-axis", dark_config)
        
        # 检查是否应用了深色主题（允许一定的浮点误差）
        bg_color = dark_chart.fig.get_facecolor()
        self.assertAlmostEqual(bg_color[0], 0.18, places=1)  # R分量
        self.assertAlmostEqual(bg_color[1], 0.18, places=1)  # G分量
        self.assertAlmostEqual(bg_color[2], 0.18, places=1)  # B分量
        
        # 测试浅色主题
        light_config = VisualizationConfig(theme='light')
        light_chart = RealTimeChart("Light Chart", "Y-axis", light_config)
        
        # 检查是否应用了浅色主题
        bg_color = light_chart.fig.get_facecolor()
        self.assertAlmostEqual(bg_color[0], 1.0, places=1)  # R分量
        self.assertAlmostEqual(bg_color[1], 1.0, places=1)  # G分量
        self.assertAlmostEqual(bg_color[2], 1.0, places=1)  # B分量


class TestDataAnalyzer(unittest.TestCase):
    """测试数据分析器类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.analyzer = DataAnalyzer()
        self.series = DataSeries(name="test_series")
    
    def test_analyze_trends_insufficient_data(self):
        """测试数据不足时的趋势分析。"""
        # 添加少量数据
        for i in range(5):
            self.series.add_point(float(i))
        
        result = self.analyzer.analyze_trends(self.series, window_size=10)
        
        self.assertEqual(result['trend'], 'insufficient_data')
        self.assertEqual(result['slope'], 0)
        self.assertEqual(result['r_squared'], 0)
    
    def test_analyze_trends_increasing(self):
        """测试上升趋势分析。"""
        # 添加上升趋势数据
        for i in range(20):
            self.series.add_point(float(i))
        
        result = self.analyzer.analyze_trends(self.series, window_size=10)
        
        self.assertEqual(result['trend'], 'increasing')
        self.assertGreater(result['slope'], 0.5)
        self.assertGreater(result['r_squared'], 0.9)
    
    def test_analyze_trends_decreasing(self):
        """测试下降趋势分析。"""
        # 添加下降趋势数据
        for i in range(20):
            self.series.add_point(float(20 - i))
        
        result = self.analyzer.analyze_trends(self.series, window_size=10)
        
        self.assertEqual(result['trend'], 'decreasing')
        self.assertLess(result['slope'], -0.5)
        self.assertGreater(result['r_squared'], 0.9)
    
    def test_analyze_trends_stable(self):
        """测试稳定趋势分析。"""
        # 添加稳定数据
        for i in range(20):
            self.series.add_point(5.0 + np.random.normal(0, 0.001))  # 很小的噪声
        
        result = self.analyzer.analyze_trends(self.series, window_size=10)
        
        self.assertEqual(result['trend'], 'stable')
        self.assertLess(abs(result['slope']), 0.01)
    
    def test_detect_anomalies(self):
        """测试异常检测。"""
        # 添加正常数据
        for i in range(50):
            self.series.add_point(5.0 + np.random.normal(0, 0.5))
        
        # 添加异常值
        self.series.add_point(15.0)  # 明显的异常值
        
        anomalies = self.analyzer.detect_anomalies(self.series, threshold=2.0)
        
        self.assertGreater(len(anomalies), 0)
        # 检查异常值是否被检测到
        anomaly_values = [value for _, value in anomalies]
        self.assertIn(15.0, anomaly_values)
    
    def test_detect_anomalies_insufficient_data(self):
        """测试数据不足时的异常检测。"""
        # 添加少量数据
        for i in range(5):
            self.series.add_point(float(i))
        
        anomalies = self.analyzer.detect_anomalies(self.series)
        
        self.assertEqual(len(anomalies), 0)
    
    def test_generate_summary_report(self):
        """测试生成汇总报告。"""
        # 创建多个数据序列
        series1 = DataSeries(name="series1", unit="unit1")
        series2 = DataSeries(name="series2", unit="unit2")
        
        # 添加数据
        for i in range(20):
            series1.add_point(float(i))
            series2.add_point(float(i * 2))
        
        data_series = {"series1": series1, "series2": series2}
        
        report = self.analyzer.generate_summary_report(data_series)
        
        self.assertIn('timestamp', report)
        self.assertEqual(report['series_count'], 2)
        self.assertIn('series_analysis', report)
        
        # 检查每个序列的分析结果
        for name in ["series1", "series2"]:
            self.assertIn(name, report['series_analysis'])
            analysis = report['series_analysis'][name]
            
            self.assertIn('data_points', analysis)
            self.assertIn('trends', analysis)
            self.assertIn('anomaly_count', analysis)
            self.assertIn('latest_value', analysis)
            self.assertIn('unit', analysis)
            
            self.assertEqual(analysis['data_points'], 20)
    
    def test_generate_summary_report_empty_series(self):
        """测试空数据序列的汇总报告。"""
        empty_series = DataSeries(name="empty")
        data_series = {"empty": empty_series}
        
        report = self.analyzer.generate_summary_report(data_series)
        
        self.assertEqual(report['series_count'], 1)
        # 空序列不应该出现在分析结果中
        self.assertEqual(len(report['series_analysis']), 0)


class TestConvenienceFunctions(unittest.TestCase):
    """测试便捷函数。"""
    
    def setUp(self):
        """设置测试环境。"""
        # 使用Agg后端避免GUI依赖
        import matplotlib
        matplotlib.use('Agg')
    
    def test_create_real_time_chart(self):
        """测试创建实时图表便捷函数。"""
        chart = create_real_time_chart("Test Chart", "Y-axis")
        
        self.assertIsInstance(chart, RealTimeChart)
        self.assertEqual(chart.title, "Test Chart")
        self.assertEqual(chart.ylabel, "Y-axis")
    
    def test_create_real_time_chart_with_config(self):
        """测试使用配置创建实时图表。"""
        config = VisualizationConfig(theme='dark')
        chart = create_real_time_chart("Test Chart", "Y-axis", config)
        
        self.assertIsInstance(chart, RealTimeChart)
        self.assertEqual(chart.config.theme, 'dark')
    
    def test_analyze_data_series(self):
        """测试分析数据序列便捷函数。"""
        series = DataSeries(name="test")
        
        # 添加上升趋势数据
        for i in range(20):
            series.add_point(float(i))
        
        result = analyze_data_series(series)
        
        self.assertIn('trend', result)
        self.assertIn('slope', result)
        self.assertIn('r_squared', result)
        self.assertEqual(result['trend'], 'increasing')


class TestIntegration(unittest.TestCase):
    """集成测试。"""
    
    def setUp(self):
        """设置测试环境。"""
        # 使用Agg后端避免GUI依赖
        import matplotlib
        matplotlib.use('Agg')
    
    def test_complete_workflow(self):
        """测试完整的工作流程。"""
        # 创建配置
        config = VisualizationConfig(update_interval=0.1, max_data_points=100)
        
        # 创建图表
        chart = create_real_time_chart("Integration Test", "Values", config)
        
        # 添加数据序列
        series1 = chart.add_series("series1", color="blue", unit="units")
        series2 = chart.add_series("series2", color="red", unit="units")
        
        # 模拟数据更新
        for i in range(50):
            timestamp = datetime.now() + timedelta(seconds=i)
            chart.update_data("series1", float(i), timestamp)
            chart.update_data("series2", float(i * 2), timestamp)
        
        # 验证数据
        self.assertEqual(len(series1.data), 50)
        self.assertEqual(len(series2.data), 50)
        
        # 分析数据
        analyzer = DataAnalyzer()
        trends1 = analyzer.analyze_trends(series1)
        trends2 = analyzer.analyze_trends(series2)
        
        self.assertEqual(trends1['trend'], 'increasing')
        self.assertEqual(trends2['trend'], 'increasing')
        
        # 生成报告
        report = analyzer.generate_summary_report({
            "series1": series1,
            "series2": series2
        })
        
        self.assertEqual(report['series_count'], 2)
        self.assertEqual(len(report['series_analysis']), 2)
        
        # 保存图表（使用mock避免实际文件操作）
        with patch.object(chart.fig, 'savefig') as mock_savefig:
            chart.save_chart("test_workflow.png")
            mock_savefig.assert_called_once()


if __name__ == '__main__':
    unittest.main()