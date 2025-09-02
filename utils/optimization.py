#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""算法优化工具。

本模块提供了用于算法优化的工具，包括：
1. 数值计算优化
2. 缓存机制
3. 批处理优化
4. 并行计算支持
5. 内存优化策略
"""

import numpy as np
import functools
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Callable, Tuple
from collections import OrderedDict
import time
import weakref
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging


class LRUCache:
    """线程安全的LRU缓存实现。"""
    
    def __init__(self, maxsize: int = 128):
        """初始化LRU缓存。
        
        Args:
            maxsize: 缓存最大大小
        """
        self.maxsize = maxsize
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: Any) -> Any:
        """获取缓存值。"""
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            else:
                self.misses += 1
                return None
    
    def put(self, key: Any, value: Any):
        """设置缓存值。"""
        with self.lock:
            if key in self.cache:
                # 更新现有值
                self.cache.pop(key)
            elif len(self.cache) >= self.maxsize:
                # 删除最久未使用的项
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def clear(self):
        """清空缓存。"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'size': len(self.cache),
                'maxsize': self.maxsize
            }


def memoize(maxsize: int = 128, typed: bool = False):
    """记忆化装饰器，用于缓存函数结果。
    
    Args:
        maxsize: 缓存最大大小
        typed: 是否区分参数类型
    """
    def decorator(func: Callable) -> Callable:
        cache = LRUCache(maxsize)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 创建缓存键
            key = _make_key(args, kwargs, typed)
            
            # 尝试从缓存获取
            result = cache.get(key)
            if result is not None:
                return result
            
            # 计算结果并缓存
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        # 添加缓存管理方法
        wrapper.cache_info = cache.stats
        wrapper.cache_clear = cache.clear
        
        return wrapper
    return decorator


def _make_key(args: tuple, kwargs: dict, typed: bool) -> tuple:
    """创建缓存键。"""
    key = args
    if kwargs:
        key += tuple(sorted(kwargs.items()))
    if typed:
        key += tuple(type(arg) for arg in args)
        if kwargs:
            key += tuple(type(v) for v in kwargs.values())
    return key


class BatchProcessor:
    """批处理器，用于优化批量数据处理。"""
    
    def __init__(self, batch_size: int = 100, max_workers: int = None):
        """初始化批处理器。
        
        Args:
            batch_size: 批处理大小
            max_workers: 最大工作线程数
        """
        self.batch_size = batch_size
        self.max_workers = max_workers or min(32, (multiprocessing.cpu_count() or 1) + 4)
        self.logger = logging.getLogger(__name__)
    
    def process_batches(self, data: List[Any], processor: Callable, 
                       use_threads: bool = True) -> List[Any]:
        """批量处理数据。
        
        Args:
            data: 要处理的数据列表
            processor: 处理函数
            use_threads: 是否使用线程池
        
        Returns:
            处理结果列表
        """
        if not data:
            return []
        
        # 分割数据为批次
        batches = [data[i:i + self.batch_size] 
                  for i in range(0, len(data), self.batch_size)]
        
        results = []
        
        if use_threads and len(batches) > 1:
            # 使用线程池处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                batch_results = list(executor.map(processor, batches))
                
            # 合并结果
            for batch_result in batch_results:
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
        else:
            # 串行处理
            for batch in batches:
                batch_result = processor(batch)
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
        
        return results


class NumpyOptimizer:
    """NumPy数值计算优化器。"""
    
    @staticmethod
    def vectorize_operation(func: Callable) -> Callable:
        """向量化操作装饰器。"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 尝试向量化输入
            vectorized_args = []
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    vectorized_args.append(np.array(arg))
                else:
                    vectorized_args.append(arg)
            
            return func(*vectorized_args, **kwargs)
        
        return wrapper
    
    @staticmethod
    def optimize_array_operations(arrays: List[np.ndarray]) -> List[np.ndarray]:
        """优化数组操作。
        
        Args:
            arrays: 数组列表
        
        Returns:
            优化后的数组列表
        """
        optimized = []
        
        for arr in arrays:
            if not isinstance(arr, np.ndarray):
                arr = np.array(arr)
            
            # 确保使用最优数据类型
            if arr.dtype == np.float64 and np.all(np.abs(arr) < 1e6):
                arr = arr.astype(np.float32)
            elif arr.dtype == np.int64 and np.all(np.abs(arr) < 2**31):
                arr = arr.astype(np.int32)
            
            # 确保内存连续性
            if not arr.flags['C_CONTIGUOUS']:
                arr = np.ascontiguousarray(arr)
            
            optimized.append(arr)
        
        return optimized
    
    @staticmethod
    def batch_matrix_operations(matrices: List[np.ndarray], 
                              operation: str = 'multiply') -> np.ndarray:
        """批量矩阵操作。
        
        Args:
            matrices: 矩阵列表
            operation: 操作类型 ('multiply', 'add', 'subtract')
        
        Returns:
            操作结果
        """
        if not matrices:
            return np.array([])
        
        # 堆叠矩阵进行批量操作
        stacked = np.stack(matrices)
        
        if operation == 'multiply':
            return np.prod(stacked, axis=0)
        elif operation == 'add':
            return np.sum(stacked, axis=0)
        elif operation == 'subtract':
            result = stacked[0]
            for matrix in stacked[1:]:
                result = result - matrix
            return result
        else:
            raise ValueError(f"不支持的操作类型: {operation}")


class MemoryOptimizer:
    """内存优化器。"""
    
    def __init__(self):
        """初始化内存优化器。"""
        self.weak_refs = weakref.WeakSet()
        self.logger = logging.getLogger(__name__)
    
    def register_object(self, obj: Any):
        """注册对象用于内存管理。"""
        self.weak_refs.add(obj)
    
    def optimize_data_structures(self, data: Any) -> Any:
        """优化数据结构。
        
        Args:
            data: 要优化的数据
        
        Returns:
            优化后的数据
        """
        if isinstance(data, list):
            # 对于大列表，考虑使用numpy数组
            if len(data) > 1000 and all(isinstance(x, (int, float)) for x in data):
                return np.array(data)
            return data
        
        elif isinstance(data, dict):
            # 优化字典结构
            if len(data) > 1000:
                # 对于大字典，考虑使用更紧凑的表示
                return {k: self.optimize_data_structures(v) for k, v in data.items()}
            return data
        
        elif isinstance(data, np.ndarray):
            # 优化numpy数组
            return self._optimize_numpy_array(data)
        
        return data
    
    def _optimize_numpy_array(self, arr: np.ndarray) -> np.ndarray:
        """优化numpy数组。"""
        # 检查是否可以使用更小的数据类型
        if arr.dtype == np.float64:
            if np.allclose(arr, arr.astype(np.float32)):
                return arr.astype(np.float32)
        
        elif arr.dtype == np.int64:
            if np.all(arr >= np.iinfo(np.int32).min) and np.all(arr <= np.iinfo(np.int32).max):
                return arr.astype(np.int32)
        
        # 确保内存连续性
        if not arr.flags['C_CONTIGUOUS']:
            return np.ascontiguousarray(arr)
        
        return arr
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况。"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent(),
            'registered_objects': len(self.weak_refs)
        }


class ParallelProcessor:
    """并行处理器。"""
    
    def __init__(self, max_workers: int = None, use_processes: bool = False):
        """初始化并行处理器。
        
        Args:
            max_workers: 最大工作者数量
            use_processes: 是否使用进程池而不是线程池
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.use_processes = use_processes
        self.logger = logging.getLogger(__name__)
    
    def parallel_map(self, func: Callable, iterable: List[Any], 
                    chunk_size: int = None) -> List[Any]:
        """并行映射函数。
        
        Args:
            func: 要应用的函数
            iterable: 可迭代对象
            chunk_size: 块大小
        
        Returns:
            结果列表
        """
        if not iterable:
            return []
        
        if len(iterable) < 10:  # 对于小数据集，直接串行处理
            return [func(item) for item in iterable]
        
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        try:
            with executor_class(max_workers=self.max_workers) as executor:
                if chunk_size:
                    results = list(executor.map(func, iterable, chunksize=chunk_size))
                else:
                    results = list(executor.map(func, iterable))
            return results
        except Exception as e:
            self.logger.error(f"并行处理失败: {e}")
            # 回退到串行处理
            return [func(item) for item in iterable]
    
    def parallel_reduce(self, func: Callable, iterable: List[Any], 
                       initializer: Any = None) -> Any:
        """并行归约操作。
        
        Args:
            func: 归约函数
            iterable: 可迭代对象
            initializer: 初始值
        
        Returns:
            归约结果
        """
        if not iterable:
            return initializer
        
        if len(iterable) == 1:
            return iterable[0] if initializer is None else func(initializer, iterable[0])
        
        # 分割数据进行并行处理
        chunk_size = max(1, len(iterable) // self.max_workers)
        chunks = [iterable[i:i + chunk_size] 
                 for i in range(0, len(iterable), chunk_size)]
        
        # 并行处理每个块
        def reduce_chunk(chunk):
            result = chunk[0] if initializer is None else initializer
            for item in chunk[1:] if initializer is None else chunk:
                result = func(result, item)
            return result
        
        chunk_results = self.parallel_map(reduce_chunk, chunks)
        
        # 合并块结果
        final_result = chunk_results[0]
        for result in chunk_results[1:]:
            final_result = func(final_result, result)
        
        return final_result


class AlgorithmOptimizer:
    """算法优化器主类。"""
    
    def __init__(self):
        """初始化算法优化器。"""
        self.memory_optimizer = MemoryOptimizer()
        self.numpy_optimizer = NumpyOptimizer()
        self.batch_processor = BatchProcessor()
        self.parallel_processor = ParallelProcessor()
        self.logger = logging.getLogger(__name__)
    
    def optimize_pid_calculation(self, errors: np.ndarray, kp: float, 
                               ki: float, kd: float, dt: float) -> Tuple[float, float, float]:
        """优化PID计算。
        
        Args:
            errors: 误差数组
            kp: 比例增益
            ki: 积分增益
            kd: 微分增益
            dt: 时间步长
        
        Returns:
            (比例项, 积分项, 微分项)
        """
        # 确保输入是numpy数组
        errors = np.asarray(errors, dtype=np.float32)
        
        # 向量化计算
        proportional = kp * errors[-1] if len(errors) > 0 else 0.0
        
        # 积分项 (使用梯形积分)
        integral = ki * np.trapezoid(errors, dx=dt) if len(errors) > 1 else 0.0
        
        # 使用numpy的梯度计算微分
        if len(errors) > 1:
            derivative = kd * np.gradient(errors, dt)[-1]
        else:
            derivative = 0.0
        
        return float(proportional), float(integral), float(derivative)
    
    def optimize_simulation_step(self, state_vector: np.ndarray, 
                               control_input: float, 
                               system_matrix: np.ndarray,
                               input_matrix: np.ndarray,
                               dt: float) -> np.ndarray:
        """优化仿真步骤计算。
        
        Args:
            state_vector: 状态向量
            control_input: 控制输入
            system_matrix: 系统矩阵
            input_matrix: 输入矩阵
            dt: 时间步长
        
        Returns:
            下一步状态向量
        """
        # 确保所有输入都是优化的numpy数组
        state_vector = np.asarray(state_vector, dtype=np.float32)
        system_matrix = np.asarray(system_matrix, dtype=np.float32)
        input_matrix = np.asarray(input_matrix, dtype=np.float32)
        
        # 使用矩阵运算进行状态更新
        state_derivative = (system_matrix @ state_vector + 
                          input_matrix * control_input)
        
        # 使用欧拉方法进行积分
        next_state = state_vector + state_derivative * dt
        
        return next_state
    
    def batch_optimize_data(self, data_list: List[Any], 
                          optimization_func: Callable) -> List[Any]:
        """批量优化数据。
        
        Args:
            data_list: 数据列表
            optimization_func: 优化函数
        
        Returns:
            优化后的数据列表
        """
        return self.batch_processor.process_batches(data_list, optimization_func)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息。"""
        return {
            'memory_usage': self.memory_optimizer.get_memory_usage(),
            'batch_processor_config': {
                'batch_size': self.batch_processor.batch_size,
                'max_workers': self.batch_processor.max_workers
            },
            'parallel_processor_config': {
                'max_workers': self.parallel_processor.max_workers,
                'use_processes': self.parallel_processor.use_processes
            }
        }


# 全局优化器实例
optimizer = AlgorithmOptimizer()


# 便捷函数
def optimize_pid_calculation(errors: np.ndarray, kp: float, ki: float, 
                           kd: float, dt: float) -> Tuple[float, float, float]:
    """优化PID计算的便捷函数。"""
    return optimizer.optimize_pid_calculation(errors, kp, ki, kd, dt)


def optimize_simulation_step(state_vector: np.ndarray, control_input: float,
                           system_matrix: np.ndarray, input_matrix: np.ndarray,
                           dt: float) -> np.ndarray:
    """优化仿真步骤的便捷函数。"""
    return optimizer.optimize_simulation_step(
        state_vector, control_input, system_matrix, input_matrix, dt
    )


def parallel_map(func: Callable, iterable: List[Any]) -> List[Any]:
    """并行映射的便捷函数。"""
    return optimizer.parallel_processor.parallel_map(func, iterable)