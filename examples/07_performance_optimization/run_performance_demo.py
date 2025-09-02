#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""性能优化和监控演示脚本。

本脚本演示智能水厂系统的性能优化功能，包括：
1. 性能分析和监控
2. 算法优化技术
3. 缓存和记忆化
4. 批处理和并行计算
5. NumPy向量化优化
"""

import sys
import os
import time
import numpy as np
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.performance import (
    PerformanceProfiler, profile_performance, 
    get_performance_metrics, generate_performance_report
)
from utils.optimization import (
    LRUCache, memoize, BatchProcessor, NumpyOptimizer,
    AlgorithmOptimizer, optimize_pid_calculation, optimize_simulation_step
)


def demo_basic_performance_monitoring():
    """演示基本性能监控功能。"""
    print("\n" + "="*60)
    print("1. 基本性能监控演示")
    print("="*60)
    
    # 创建性能分析器
    profiler = PerformanceProfiler()
    
    # 定义一些模拟函数
    @profiler.profile("water_treatment_simulation")
    def simulate_water_treatment(volume: float, treatment_time: float) -> dict:
        """模拟水处理过程。"""
        # 模拟计算密集型操作
        time.sleep(treatment_time)
        
        # 模拟一些计算
        efficiency = 0.95 - (volume / 10000) * 0.05  # 体积越大效率略降
        treated_volume = volume * efficiency
        
        return {
            'input_volume': volume,
            'treated_volume': treated_volume,
            'efficiency': efficiency,
            'treatment_time': treatment_time
        }
    
    @profiler.profile("quality_analysis")
    def analyze_water_quality(samples: list) -> dict:
        """分析水质数据。"""
        time.sleep(0.05)  # 模拟分析时间
        
        # 模拟质量分析计算
        ph_values = [sample.get('ph', 7.0) for sample in samples]
        temp_values = [sample.get('temperature', 20.0) for sample in samples]
        
        return {
            'avg_ph': np.mean(ph_values),
            'avg_temperature': np.mean(temp_values),
            'sample_count': len(samples),
            'quality_score': np.mean(ph_values) * 10 + np.mean(temp_values)
        }
    
    # 执行一些操作
    print("执行水处理仿真...")
    for i in range(5):
        volume = 1000 + i * 200
        treatment_time = 0.02 + i * 0.01
        result = simulate_water_treatment(volume, treatment_time)
        print(f"  处理 {volume}L 水，效率: {result['efficiency']:.3f}")
    
    print("\n执行水质分析...")
    for i in range(3):
        samples = [
            {'ph': 7.0 + np.random.normal(0, 0.1), 'temperature': 20 + np.random.normal(0, 2)}
            for _ in range(10 + i * 5)
        ]
        result = analyze_water_quality(samples)
        print(f"  分析 {result['sample_count']} 个样本，质量评分: {result['quality_score']:.2f}")
    
    # 显示性能指标
    print("\n性能指标:")
    for func_name in ["water_treatment_simulation", "quality_analysis"]:
        metrics = profiler.get_function_metrics(func_name)
        if metrics:
            print(f"  {func_name}:")
            print(f"    调用次数: {metrics['call_count']}")
            print(f"    平均执行时间: {metrics['avg_execution_time']:.4f}秒")
            print(f"    最后执行时间: {metrics['last_execution_time']:.4f}秒")
    
    return profiler


def demo_system_monitoring(profiler):
    """演示系统资源监控。"""
    print("\n" + "="*60)
    print("2. 系统资源监控演示")
    print("="*60)
    
    print("启动系统监控...")
    profiler.start_system_monitoring(interval=0.5)
    
    # 执行一些计算密集型任务
    print("执行计算密集型任务...")
    
    @profiler.profile("intensive_calculation")
    def intensive_calculation(size: int) -> np.ndarray:
        """计算密集型任务。"""
        # 创建大矩阵并进行运算
        matrix_a = np.random.rand(size, size)
        matrix_b = np.random.rand(size, size)
        
        # 矩阵乘法
        result = np.dot(matrix_a, matrix_b)
        
        # 一些额外计算
        eigenvalues = np.linalg.eigvals(result[:min(100, size), :min(100, size)])
        
        return eigenvalues
    
    for i in range(3):
        size = 200 + i * 100
        print(f"  计算 {size}x{size} 矩阵运算...")
        result = intensive_calculation(size)
        print(f"    特征值数量: {len(result)}")
        time.sleep(0.5)
    
    # 停止监控
    profiler.stop_system_monitoring()
    
    # 显示系统指标
    system_metrics = profiler.get_system_metrics()
    if system_metrics:
        print("\n系统资源使用情况:")
        for i, metric in enumerate(system_metrics[-5:]):  # 显示最后5个指标
            timestamp = time.strftime('%H:%M:%S', time.localtime(metric['timestamp']))
            print(f"  [{timestamp}] CPU: {metric['cpu_percent']:.1f}%, "
                  f"内存: {metric['memory_percent']:.1f}%, "
                  f"可用内存: {metric['memory_available']/(1024**3):.2f}GB")


def demo_caching_and_memoization():
    """演示缓存和记忆化功能。"""
    print("\n" + "="*60)
    print("3. 缓存和记忆化演示")
    print("="*60)
    
    # LRU缓存演示
    print("LRU缓存演示:")
    cache = LRUCache(maxsize=5)
    
    # 模拟传感器数据缓存
    sensor_data = {
        "temp_001": {"value": 25.5, "timestamp": time.time(), "status": "normal"},
        "ph_002": {"value": 7.2, "timestamp": time.time(), "status": "normal"},
        "flow_003": {"value": 150.0, "timestamp": time.time(), "status": "normal"},
        "pressure_004": {"value": 2.5, "timestamp": time.time(), "status": "normal"},
        "turbidity_005": {"value": 0.8, "timestamp": time.time(), "status": "normal"},
        "chlorine_006": {"value": 1.2, "timestamp": time.time(), "status": "normal"},
    }
    
    # 添加数据到缓存
    for sensor_id, data in sensor_data.items():
        cache.put(sensor_id, data)
        print(f"  缓存传感器数据: {sensor_id} = {data['value']}")
    
    # 访问一些数据
    print("\n访问缓存数据:")
    for sensor_id in ["temp_001", "ph_002", "nonexistent", "flow_003"]:
        data = cache.get(sensor_id)
        if data:
            print(f"  {sensor_id}: {data['value']} (命中)")
        else:
            print(f"  {sensor_id}: 未找到 (未命中)")
    
    # 显示缓存统计
    stats = cache.stats()
    print(f"\n缓存统计: 命中率 {stats['hit_rate']:.2f}, "
          f"命中 {stats['hits']}, 未命中 {stats['misses']}, "
          f"大小 {stats['size']}/{stats['maxsize']}")
    
    # 记忆化演示
    print("\n记忆化装饰器演示:")
    
    @memoize(maxsize=20)
    def expensive_water_analysis(sample_id: str, analysis_type: str) -> dict:
        """模拟昂贵的水质分析计算。"""
        print(f"    执行分析: {sample_id} - {analysis_type}")
        time.sleep(0.1)  # 模拟计算时间
        
        # 模拟分析结果
        if analysis_type == "chemical":
            return {"ph": 7.2, "chlorine": 1.1, "fluoride": 0.8}
        elif analysis_type == "biological":
            return {"bacteria": 10, "virus": 0, "algae": 5}
        else:
            return {"turbidity": 0.5, "color": "clear", "odor": "none"}
    
    # 第一次调用 - 会执行计算
    print("  第一次调用 (会执行计算):")
    start_time = time.time()
    result1 = expensive_water_analysis("sample_001", "chemical")
    time1 = time.time() - start_time
    print(f"    结果: {result1}, 耗时: {time1:.3f}秒")
    
    # 第二次调用相同参数 - 使用缓存
    print("  第二次调用相同参数 (使用缓存):")
    start_time = time.time()
    result2 = expensive_water_analysis("sample_001", "chemical")
    time2 = time.time() - start_time
    print(f"    结果: {result2}, 耗时: {time2:.3f}秒")
    
    print(f"  性能提升: {time1/time2:.1f}倍")


def demo_batch_processing():
    """演示批处理功能。"""
    print("\n" + "="*60)
    print("4. 批处理和并行计算演示")
    print("="*60)
    
    # 创建批处理器
    processor = BatchProcessor(batch_size=20, max_workers=4)
    
    # 生成大量传感器读数
    sensor_readings = []
    for i in range(100):
        reading = {
            'sensor_id': f"sensor_{i:03d}",
            'value': 20 + np.random.normal(0, 5),  # 温度读数
            'timestamp': time.time() - i * 60,  # 每分钟一个读数
            'quality': np.random.choice(['good', 'fair', 'poor'], p=[0.8, 0.15, 0.05])
        }
        sensor_readings.append(reading)
    
    def process_sensor_batch(batch):
        """处理传感器数据批次。"""
        processed = []
        for reading in batch:
            # 模拟数据处理
            time.sleep(0.001)  # 模拟处理时间
            
            # 数据校准和过滤
            calibrated_value = reading['value'] * 1.02 + 0.5  # 校准
            
            # 质量评分
            quality_score = {
                'good': 1.0,
                'fair': 0.8,
                'poor': 0.5
            }[reading['quality']]
            
            processed_reading = {
                'sensor_id': reading['sensor_id'],
                'original_value': reading['value'],
                'calibrated_value': calibrated_value,
                'quality_score': quality_score,
                'timestamp': reading['timestamp']
            }
            processed.append(processed_reading)
        
        return processed
    
    # 串行处理
    print("串行批处理:")
    start_time = time.time()
    serial_results = processor.process_batches(
        sensor_readings, process_sensor_batch, use_threads=False
    )
    serial_time = time.time() - start_time
    print(f"  处理了 {len(serial_results)} 个读数，耗时: {serial_time:.3f}秒")
    
    # 并行处理
    print("\n并行批处理:")
    start_time = time.time()
    parallel_results = processor.process_batches(
        sensor_readings, process_sensor_batch, use_threads=True
    )
    parallel_time = time.time() - start_time
    print(f"  处理了 {len(parallel_results)} 个读数，耗时: {parallel_time:.3f}秒")
    
    if parallel_time > 0:
        speedup = serial_time / parallel_time
        print(f"  并行加速比: {speedup:.2f}倍")
    
    # 显示一些处理结果
    print("\n处理结果示例:")
    for i, result in enumerate(parallel_results[:3]):
        print(f"  {result['sensor_id']}: "
              f"{result['original_value']:.2f} -> {result['calibrated_value']:.2f} "
              f"(质量: {result['quality_score']})")


def demo_numpy_optimization():
    """演示NumPy优化功能。"""
    print("\n" + "="*60)
    print("5. NumPy向量化优化演示")
    print("="*60)
    
    optimizer = NumpyOptimizer()
    
    # 向量化操作演示
    print("向量化操作演示:")
    
    @optimizer.vectorize_operation
    def water_quality_index(temperature, ph, dissolved_oxygen, turbidity):
        """计算综合水质指数。"""
        # 标准化各项指标 (0-100分)
        temp_score = np.clip((temperature - 15) / 10 * 100, 0, 100)
        ph_score = np.clip((8 - np.abs(ph - 7)) / 1 * 100, 0, 100)
        do_score = np.clip(dissolved_oxygen / 10 * 100, 0, 100)
        turb_score = np.clip((2 - turbidity) / 2 * 100, 0, 100)
        
        # 加权平均
        return (temp_score * 0.2 + ph_score * 0.3 + do_score * 0.3 + turb_score * 0.2)
    
    # 生成测试数据
    n_samples = 1000
    temperatures = np.random.normal(22, 3, n_samples)
    ph_values = np.random.normal(7.2, 0.3, n_samples)
    do_values = np.random.normal(8.5, 1.0, n_samples)
    turbidity_values = np.random.exponential(0.5, n_samples)
    
    # 向量化计算
    print(f"  计算 {n_samples} 个样本的水质指数...")
    start_time = time.time()
    quality_indices = water_quality_index(temperatures, ph_values, do_values, turbidity_values)
    vectorized_time = time.time() - start_time
    
    print(f"  向量化计算耗时: {vectorized_time:.4f}秒")
    print(f"  平均水质指数: {np.mean(quality_indices):.2f}")
    print(f"  水质指数范围: {np.min(quality_indices):.2f} - {np.max(quality_indices):.2f}")
    
    # 对比非向量化计算
    def scalar_water_quality_index(temp, ph, do, turb):
        """标量版本的水质指数计算。"""
        temp_score = max(0, min(100, (temp - 15) / 10 * 100))
        ph_score = max(0, min(100, (8 - abs(ph - 7)) / 1 * 100))
        do_score = max(0, min(100, do / 10 * 100))
        turb_score = max(0, min(100, (2 - turb) / 2 * 100))
        return temp_score * 0.2 + ph_score * 0.3 + do_score * 0.3 + turb_score * 0.2
    
    print("\n  对比标量计算:")
    start_time = time.time()
    scalar_results = []
    for i in range(min(100, n_samples)):  # 只计算部分样本以节省时间
        result = scalar_water_quality_index(
            temperatures[i], ph_values[i], do_values[i], turbidity_values[i]
        )
        scalar_results.append(result)
    scalar_time = time.time() - start_time
    
    print(f"  标量计算 {len(scalar_results)} 个样本耗时: {scalar_time:.4f}秒")
    if scalar_time > 0:
        estimated_full_scalar_time = scalar_time * (n_samples / len(scalar_results))
        speedup = estimated_full_scalar_time / vectorized_time
        print(f"  估计向量化加速比: {speedup:.1f}倍")
    
    # 数组优化演示
    print("\n数组优化演示:")
    test_arrays = [
        np.array(temperatures, dtype=np.float64),
        np.array(ph_values, dtype=np.float64),
        np.array(do_values, dtype=np.float64)
    ]
    
    print("  原始数组信息:")
    total_memory_before = 0
    for i, arr in enumerate(test_arrays):
        memory_mb = arr.nbytes / (1024 * 1024)
        total_memory_before += memory_mb
        print(f"    数组 {i+1}: {arr.dtype}, {memory_mb:.2f} MB")
    
    optimized_arrays = optimizer.optimize_array_operations(test_arrays)
    
    print("  优化后数组信息:")
    total_memory_after = 0
    for i, arr in enumerate(optimized_arrays):
        memory_mb = arr.nbytes / (1024 * 1024)
        total_memory_after += memory_mb
        print(f"    数组 {i+1}: {arr.dtype}, {memory_mb:.2f} MB")
    
    memory_savings = (total_memory_before - total_memory_after) / total_memory_before * 100
    print(f"  内存节省: {memory_savings:.1f}%")


def demo_algorithm_optimization():
    """演示算法优化功能。"""
    print("\n" + "="*60)
    print("6. 算法优化演示")
    print("="*60)
    
    optimizer = AlgorithmOptimizer()
    
    # PID控制器优化演示
    print("PID控制器优化演示:")
    
    # 模拟控制系统
    setpoint = 25.0  # 目标温度
    current_temp = 20.0  # 当前温度
    errors = []
    
    # PID参数
    kp, ki, kd = 1.2, 0.5, 0.1
    dt = 0.1
    
    print(f"  目标温度: {setpoint}°C")
    print(f"  PID参数: Kp={kp}, Ki={ki}, Kd={kd}")
    
    # 模拟控制过程
    for step in range(10):
        error = setpoint - current_temp
        errors.append(error)
        
        # 保持最近10个误差值
        if len(errors) > 10:
            errors = errors[-10:]
        
        # 使用优化的PID计算
        p_term, i_term, d_term = optimizer.optimize_pid_calculation(
            np.array(errors), kp, ki, kd, dt
        )
        
        control_output = p_term + i_term + d_term
        
        # 模拟系统响应
        current_temp += control_output * dt * 0.8  # 简化的系统模型
        
        print(f"  步骤 {step+1}: 温度={current_temp:.2f}°C, "
              f"误差={error:.2f}, 控制输出={control_output:.3f}")
        
        if abs(error) < 0.1:  # 达到目标
            print(f"  在第 {step+1} 步达到目标温度!")
            break
    
    # 仿真步骤优化演示
    print("\n仿真步骤优化演示:")
    
    # 定义简单的水处理系统模型
    state_vector = np.array([100.0, 7.0], dtype=np.float32)  # [流量, pH]
    system_matrix = np.array([[0.95, 0.02], [0.01, 0.98]], dtype=np.float32)
    input_matrix = np.array([0.1, 0.05], dtype=np.float32)
    
    print(f"  初始状态: 流量={state_vector[0]:.1f} L/min, pH={state_vector[1]:.2f}")
    
    # 模拟控制输入序列
    control_inputs = [0.5, 0.3, -0.2, 0.1, 0.0]
    
    for i, control_input in enumerate(control_inputs):
        # 使用优化的仿真步骤
        state_vector = optimizer.optimize_simulation_step(
            state_vector, control_input, system_matrix, input_matrix, dt
        )
        
        print(f"  步骤 {i+1}: 控制输入={control_input:+.1f}, "
              f"流量={state_vector[0]:.1f} L/min, pH={state_vector[1]:.2f}")
    
    # 显示优化统计信息
    print("\n优化统计信息:")
    stats = optimizer.get_optimization_stats()
    
    memory_stats = stats['memory_usage']
    print(f"  内存使用: {memory_stats['rss']/(1024**2):.1f} MB "
          f"({memory_stats['percent']:.1f}%)")
    
    batch_config = stats['batch_processor_config']
    print(f"  批处理配置: 批大小={batch_config['batch_size']}, "
          f"工作线程={batch_config['max_workers']}")


def demo_performance_report(profiler):
    """演示性能报告生成。"""
    print("\n" + "="*60)
    print("7. 性能报告生成")
    print("="*60)
    
    # 生成性能报告
    report_file = "performance_report.json"
    report = profiler.generate_report(report_file)
    
    print(f"性能报告已生成: {report_file}")
    print("\n报告摘要:")
    
    summary = report['summary']
    print(f"  监控的函数数量: {summary['total_functions']}")
    print(f"  系统记录数量: {summary['total_system_records']}")
    
    if 'top_performers' in report and report['top_performers']:
        top_performers = report['top_performers']
        if 'fastest_functions' in top_performers and top_performers['fastest_functions']:
            print("\n性能最佳函数:")
            for func in top_performers['fastest_functions'][:3]:
                print(f"  {func['name']}: {func['avg_time']:.4f}秒/调用 (调用{func['call_count']}次)")
    
    if 'recommendations' in report and report['recommendations']:
        print("\n优化建议:")
        for rec in report['recommendations'][:3]:
            print(f"  - {rec}")
    
    print(f"\n详细报告已保存到: {os.path.abspath(report_file)}")


def main():
    """主函数。"""
    print("智能水厂系统 - 性能优化和监控演示")
    print("="*60)
    print("本演示将展示以下功能:")
    print("1. 基本性能监控")
    print("2. 系统资源监控")
    print("3. 缓存和记忆化")
    print("4. 批处理和并行计算")
    print("5. NumPy向量化优化")
    print("6. 算法优化")
    print("7. 性能报告生成")
    
    try:
        # 执行各个演示
        profiler = demo_basic_performance_monitoring()
        demo_system_monitoring(profiler)
        demo_caching_and_memoization()
        demo_batch_processing()
        demo_numpy_optimization()
        demo_algorithm_optimization()
        demo_performance_report(profiler)
        
        print("\n" + "="*60)
        print("演示完成!")
        print("="*60)
        print("\n主要收获:")
        print("- 性能监控可以帮助识别系统瓶颈")
        print("- 缓存和记忆化可以显著提升重复计算的性能")
        print("- 批处理和并行计算可以提高大数据处理效率")
        print("- NumPy向量化操作比标量操作快数倍")
        print("- 算法优化可以减少计算复杂度和内存使用")
        print("- 定期生成性能报告有助于持续优化")
        
    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)