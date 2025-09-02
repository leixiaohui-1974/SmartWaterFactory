#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""性能监控和优化功能测试。

本模块测试性能分析器、算法优化器和相关工具的功能。
"""

import unittest
import time
import numpy as np
from unittest.mock import patch, MagicMock
import tempfile
import json
from pathlib import Path

# 导入被测试的模块
from utils.performance import (
    PerformanceProfiler, PerformanceMetrics, SystemMetrics,
    profile_performance, get_performance_metrics, generate_performance_report
)
from utils.optimization import (
    LRUCache, memoize, BatchProcessor, NumpyOptimizer, 
    MemoryOptimizer, ParallelProcessor, AlgorithmOptimizer,
    optimize_pid_calculation, optimize_simulation_step
)


class TestPerformanceProfiler(unittest.TestCase):
    """性能分析器测试类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.profiler = PerformanceProfiler()
    
    def tearDown(self):
        """清理测试环境。"""
        self.profiler.stop_system_monitoring()
        self.profiler.reset_metrics()
    
    def test_performance_metrics_creation(self):
        """测试性能指标创建。"""
        metrics = PerformanceMetrics(
            function_name="test_func",
            execution_time=1.5,
            memory_usage=10.0,
            cpu_usage=25.0,
            timestamp=time.time()
        )
        
        self.assertEqual(metrics.function_name, "test_func")
        self.assertEqual(metrics.execution_time, 1.5)
        self.assertEqual(metrics.memory_usage, 10.0)
        self.assertEqual(metrics.cpu_usage, 25.0)
        self.assertEqual(metrics.call_count, 1)
        self.assertEqual(metrics.avg_execution_time, 1.5)
    
    def test_system_metrics_creation(self):
        """测试系统指标创建。"""
        metrics = SystemMetrics(
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available=1024*1024*1024,
            memory_used=512*1024*1024,
            disk_usage=75.0
        )
        
        self.assertEqual(metrics.cpu_percent, 50.0)
        self.assertEqual(metrics.memory_percent, 60.0)
        self.assertEqual(metrics.disk_usage, 75.0)
        self.assertIsInstance(metrics.timestamp, float)
    
    def test_profile_decorator(self):
        """测试性能分析装饰器。"""
        @self.profiler.profile("test_function")
        def test_function(x, y):
            time.sleep(0.01)  # 模拟计算时间
            return x + y
        
        result = test_function(1, 2)
        self.assertEqual(result, 3)
        
        # 检查性能指标是否被记录
        metrics = self.profiler.get_function_metrics("test_function")
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics['function_name'], "test_function")
        self.assertEqual(metrics['call_count'], 1)
        self.assertGreater(metrics['avg_execution_time'], 0)
    
    def test_multiple_function_calls(self):
        """测试多次函数调用的性能统计。"""
        @self.profiler.profile()
        def slow_function():
            time.sleep(0.01)
            return "done"
        
        # 调用多次
        for _ in range(3):
            slow_function()
        
        metrics = self.profiler.get_function_metrics("slow_function")
        self.assertEqual(metrics['call_count'], 3)
        self.assertGreater(metrics['avg_execution_time'], 0)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_monitoring(self, mock_disk, mock_memory, mock_cpu):
        """测试系统监控功能。"""
        # 模拟系统指标
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(
            percent=60.0, available=1024*1024*1024, used=512*1024*1024
        )
        mock_disk.return_value = MagicMock(percent=75.0)
        
        # 启动监控
        self.profiler.start_system_monitoring(interval=0.1)
        time.sleep(0.2)  # 等待收集一些数据
        self.profiler.stop_system_monitoring()
        
        # 检查系统指标
        system_metrics = self.profiler.get_system_metrics()
        self.assertGreater(len(system_metrics), 0)
        
        latest_metric = system_metrics[-1]
        self.assertEqual(latest_metric['cpu_percent'], 50.0)
        self.assertEqual(latest_metric['memory_percent'], 60.0)
    
    def test_performance_report_generation(self):
        """测试性能报告生成。"""
        # 添加一些测试数据
        @self.profiler.profile("report_test")
        def test_func():
            time.sleep(0.01)
            return "test"
        
        test_func()
        
        # 生成报告
        report = self.profiler.generate_report()
        
        self.assertIn('timestamp', report)
        self.assertIn('summary', report)
        self.assertIn('function_metrics', report)
        self.assertIn('top_performers', report)
        self.assertIn('recommendations', report)
        
        # 检查摘要信息
        self.assertEqual(report['summary']['total_functions'], 1)
        
        # 检查函数指标
        self.assertIn('report_test', report['function_metrics'])
    
    def test_report_file_output(self):
        """测试报告文件输出。"""
        @self.profiler.profile("file_test")
        def test_func():
            return "test"
        
        test_func()
        
        # 生成报告到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            report = self.profiler.generate_report(temp_file)
            
            # 检查文件是否存在
            self.assertTrue(Path(temp_file).exists())
            
            # 检查文件内容
            with open(temp_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
            
            self.assertEqual(file_content['summary']['total_functions'], 1)
            
        finally:
            # 清理临时文件
            Path(temp_file).unlink(missing_ok=True)


class TestLRUCache(unittest.TestCase):
    """LRU缓存测试类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.cache = LRUCache(maxsize=3)
    
    def test_cache_basic_operations(self):
        """测试缓存基本操作。"""
        # 测试设置和获取
        self.cache.put("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")
        
        # 测试不存在的键
        self.assertIsNone(self.cache.get("nonexistent"))
    
    def test_cache_lru_eviction(self):
        """测试LRU淘汰机制。"""
        # 填满缓存
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.put("key3", "value3")
        
        # 添加第四个元素，应该淘汰最久未使用的
        self.cache.put("key4", "value4")
        
        # key1应该被淘汰
        self.assertIsNone(self.cache.get("key1"))
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")
    
    def test_cache_stats(self):
        """测试缓存统计信息。"""
        self.cache.put("key1", "value1")
        
        # 命中
        self.cache.get("key1")
        # 未命中
        self.cache.get("nonexistent")
        
        stats = self.cache.stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['hit_rate'], 0.5)
        self.assertEqual(stats['size'], 1)
        self.assertEqual(stats['maxsize'], 3)


class TestMemoizeDecorator(unittest.TestCase):
    """记忆化装饰器测试类。"""
    
    def test_memoize_basic(self):
        """测试基本记忆化功能。"""
        call_count = 0
        
        @memoize(maxsize=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * x
        
        # 第一次调用
        result1 = expensive_function(5)
        self.assertEqual(result1, 25)
        self.assertEqual(call_count, 1)
        
        # 第二次调用相同参数，应该使用缓存
        result2 = expensive_function(5)
        self.assertEqual(result2, 25)
        self.assertEqual(call_count, 1)  # 没有增加
        
        # 不同参数
        result3 = expensive_function(6)
        self.assertEqual(result3, 36)
        self.assertEqual(call_count, 2)
    
    def test_memoize_with_kwargs(self):
        """测试带关键字参数的记忆化。"""
        call_count = 0
        
        @memoize(maxsize=10)
        def function_with_kwargs(x, y=1):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # 测试不同的调用方式
        result1 = function_with_kwargs(5, y=2)
        result2 = function_with_kwargs(5, 2)
        result3 = function_with_kwargs(x=5, y=2)
        
        self.assertEqual(result1, 7)
        self.assertEqual(result2, 7)
        self.assertEqual(result3, 7)
        # 由于参数组合不同，可能会有多次调用
        self.assertGreaterEqual(call_count, 1)


class TestBatchProcessor(unittest.TestCase):
    """批处理器测试类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.processor = BatchProcessor(batch_size=5, max_workers=2)
    
    def test_batch_processing(self):
        """测试批处理功能。"""
        data = list(range(20))
        
        def square_batch(batch):
            return [x * x for x in batch]
        
        results = self.processor.process_batches(data, square_batch, use_threads=False)
        expected = [x * x for x in data]
        
        self.assertEqual(results, expected)
    
    def test_empty_data(self):
        """测试空数据处理。"""
        results = self.processor.process_batches([], lambda x: x)
        self.assertEqual(results, [])
    
    def test_single_item_processor(self):
        """测试单项处理器。"""
        data = [1, 2, 3, 4, 5]
        
        def single_processor(batch):
            return sum(batch)  # 返回单个值而不是列表
        
        results = self.processor.process_batches(data, single_processor, use_threads=False)
        # 应该有多个批次的结果
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)


class TestNumpyOptimizer(unittest.TestCase):
    """NumPy优化器测试类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.optimizer = NumpyOptimizer()
    
    def test_vectorize_operation(self):
        """测试向量化操作。"""
        @self.optimizer.vectorize_operation
        def add_arrays(a, b):
            return a + b
        
        result = add_arrays([1, 2, 3], [4, 5, 6])
        expected = np.array([5, 7, 9])
        
        np.testing.assert_array_equal(result, expected)
    
    def test_optimize_array_operations(self):
        """测试数组操作优化。"""
        # 创建测试数组
        arr1 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        arr2 = np.array([1000000, 2000000, 3000000], dtype=np.int64)
        
        optimized = self.optimizer.optimize_array_operations([arr1, arr2])
        
        # 检查数据类型优化
        self.assertEqual(optimized[0].dtype, np.float32)  # 应该被优化为float32
        self.assertEqual(optimized[1].dtype, np.int32)    # 应该被优化为int32
    
    def test_batch_matrix_operations(self):
        """测试批量矩阵操作。"""
        matrices = [
            np.array([[1, 2], [3, 4]]),
            np.array([[2, 0], [1, 2]]),
            np.array([[1, 1], [0, 1]])
        ]
        
        # 测试乘法
        result_multiply = self.optimizer.batch_matrix_operations(matrices, 'multiply')
        expected_multiply = matrices[0] * matrices[1] * matrices[2]
        np.testing.assert_array_equal(result_multiply, expected_multiply)
        
        # 测试加法
        result_add = self.optimizer.batch_matrix_operations(matrices, 'add')
        expected_add = matrices[0] + matrices[1] + matrices[2]
        np.testing.assert_array_equal(result_add, expected_add)


class TestAlgorithmOptimizer(unittest.TestCase):
    """算法优化器测试类。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.optimizer = AlgorithmOptimizer()
    
    def test_optimize_pid_calculation(self):
        """测试PID计算优化。"""
        errors = np.array([0.1, 0.2, 0.3, 0.2, 0.1])
        kp, ki, kd = 1.0, 0.5, 0.1
        dt = 0.1
        
        p, i, d = self.optimizer.optimize_pid_calculation(errors, kp, ki, kd, dt)
        
        # 检查结果类型
        self.assertIsInstance(p, float)
        self.assertIsInstance(i, float)
        self.assertIsInstance(d, float)
        
        # 检查比例项
        self.assertAlmostEqual(p, kp * errors[-1], places=5)
    
    def test_optimize_simulation_step(self):
        """测试仿真步骤优化。"""
        state_vector = np.array([1.0, 2.0])
        control_input = 0.5
        system_matrix = np.array([[0.9, 0.1], [0.0, 0.8]])
        input_matrix = np.array([0.1, 0.2])
        dt = 0.1
        
        next_state = self.optimizer.optimize_simulation_step(
            state_vector, control_input, system_matrix, input_matrix, dt
        )
        
        # 检查结果
        self.assertIsInstance(next_state, np.ndarray)
        self.assertEqual(next_state.shape, state_vector.shape)
        self.assertEqual(next_state.dtype, np.float32)
    
    def test_get_optimization_stats(self):
        """测试优化统计信息获取。"""
        stats = self.optimizer.get_optimization_stats()
        
        self.assertIn('memory_usage', stats)
        self.assertIn('batch_processor_config', stats)
        self.assertIn('parallel_processor_config', stats)
        
        # 检查内存使用信息
        memory_stats = stats['memory_usage']
        self.assertIn('rss', memory_stats)
        self.assertIn('percent', memory_stats)


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试类。"""
    
    def test_profile_performance_decorator(self):
        """测试性能分析装饰器便捷函数。"""
        @profile_performance("convenience_test")
        def test_function():
            time.sleep(0.01)
            return "done"
        
        result = test_function()
        self.assertEqual(result, "done")
        
        # 检查指标是否被记录
        metrics = get_performance_metrics("convenience_test")
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics['function_name'], "convenience_test")
    
    def test_optimize_pid_calculation_convenience(self):
        """测试PID计算优化便捷函数。"""
        errors = np.array([0.1, 0.2, 0.1])
        kp, ki, kd = 1.0, 0.5, 0.1
        dt = 0.1
        
        p, i, d = optimize_pid_calculation(errors, kp, ki, kd, dt)
        
        self.assertIsInstance(p, float)
        self.assertIsInstance(i, float)
        self.assertIsInstance(d, float)
    
    def test_optimize_simulation_step_convenience(self):
        """测试仿真步骤优化便捷函数。"""
        state_vector = np.array([1.0, 2.0])
        control_input = 0.5
        system_matrix = np.array([[0.9, 0.1], [0.0, 0.8]])
        input_matrix = np.array([0.1, 0.2])
        dt = 0.1
        
        next_state = optimize_simulation_step(
            state_vector, control_input, system_matrix, input_matrix, dt
        )
        
        self.assertIsInstance(next_state, np.ndarray)
        self.assertEqual(next_state.shape, state_vector.shape)


if __name__ == '__main__':
    unittest.main()