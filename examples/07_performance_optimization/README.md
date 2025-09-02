# 性能优化和监控示例

本示例展示了智能水厂系统的性能优化和监控功能，包括性能分析、算法优化和系统监控等特性。

## 功能特性

### 1. 性能分析器 (Performance Profiler)
- **函数性能监控**: 自动记录函数执行时间、内存使用和CPU使用率
- **系统资源监控**: 实时监控系统CPU、内存和磁盘使用情况
- **性能报告生成**: 生成详细的性能分析报告
- **热点函数识别**: 自动识别性能瓶颈和优化建议

### 2. 算法优化器 (Algorithm Optimizer)
- **LRU缓存**: 高效的最近最少使用缓存实现
- **记忆化装饰器**: 自动缓存函数计算结果
- **批处理器**: 支持并行和串行的批量数据处理
- **NumPy优化**: 向量化操作和数组优化
- **内存优化**: 智能内存管理和垃圾回收
- **并行处理**: 多线程和多进程并行计算

### 3. 专用优化函数
- **PID控制器优化**: 向量化PID计算，提升控制系统性能
- **仿真步骤优化**: 优化仿真循环，减少计算开销
- **矩阵运算优化**: 批量矩阵操作和内存布局优化

## 使用示例

### 基本性能监控

```python
from utils.performance import PerformanceProfiler, profile_performance

# 创建性能分析器
profiler = PerformanceProfiler()

# 使用装饰器监控函数性能
@profiler.profile("water_treatment")
def simulate_water_treatment(volume, chemicals):
    # 模拟水处理过程
    time.sleep(0.1)  # 模拟计算时间
    return volume * 0.95

# 执行函数
result = simulate_water_treatment(1000, ['chlorine', 'fluoride'])

# 获取性能指标
metrics = profiler.get_function_metrics("water_treatment")
print(f"执行时间: {metrics['avg_execution_time']:.3f}秒")
print(f"调用次数: {metrics['call_count']}")

# 生成性能报告
report = profiler.generate_report("performance_report.json")
```

### 系统资源监控

```python
# 启动系统监控
profiler.start_system_monitoring(interval=1.0)

# 运行一些计算密集型任务
for i in range(10):
    simulate_water_treatment(1000, ['chlorine'])
    time.sleep(0.5)

# 停止监控
profiler.stop_system_monitoring()

# 获取系统指标
system_metrics = profiler.get_system_metrics()
for metric in system_metrics[-5:]:  # 显示最后5个指标
    print(f"CPU: {metric['cpu_percent']:.1f}%, "
          f"内存: {metric['memory_percent']:.1f}%, "
          f"时间: {time.strftime('%H:%M:%S', time.localtime(metric['timestamp']))}")
```

### 算法优化

```python
from utils.optimization import memoize, LRUCache, optimize_pid_calculation
import numpy as np

# 使用记忆化缓存
@memoize(maxsize=100)
def expensive_calculation(x, y):
    """模拟昂贵的计算。"""
    time.sleep(0.01)  # 模拟计算时间
    return x ** 2 + y ** 2

# 第一次调用会执行计算
result1 = expensive_calculation(10, 20)  # 耗时
# 第二次调用使用缓存
result2 = expensive_calculation(10, 20)  # 快速

# 使用LRU缓存
cache = LRUCache(maxsize=50)
cache.put("sensor_data_123", {"temperature": 25.5, "ph": 7.2})
data = cache.get("sensor_data_123")
print(f"缓存统计: {cache.stats()}")

# PID控制器优化
errors = np.array([0.1, 0.2, 0.3, 0.2, 0.1])  # 历史误差
kp, ki, kd = 1.0, 0.5, 0.1  # PID参数
dt = 0.1  # 时间步长

# 优化的PID计算
p_term, i_term, d_term = optimize_pid_calculation(errors, kp, ki, kd, dt)
control_output = p_term + i_term + d_term
print(f"PID输出: {control_output:.3f}")
```

### 批处理优化

```python
from utils.optimization import BatchProcessor

# 创建批处理器
processor = BatchProcessor(batch_size=10, max_workers=4)

# 大量传感器数据
sensor_readings = list(range(1000))

def process_sensor_batch(batch):
    """处理传感器数据批次。"""
    return [reading * 1.1 + 0.5 for reading in batch]  # 校准数据

# 并行批处理
processed_data = processor.process_batches(
    sensor_readings, 
    process_sensor_batch, 
    use_threads=True
)

print(f"处理了 {len(processed_data)} 个传感器读数")
```

### NumPy向量化优化

```python
from utils.optimization import NumpyOptimizer
import numpy as np

optimizer = NumpyOptimizer()

# 向量化操作
@optimizer.vectorize_operation
def water_quality_index(temperature, ph, dissolved_oxygen):
    """计算水质指数。"""
    return (temperature * 0.3 + ph * 0.4 + dissolved_oxygen * 0.3) / 3

# 批量计算水质指数
temperatures = np.array([20.5, 21.0, 19.8, 22.1, 20.9])
ph_values = np.array([7.2, 7.1, 7.3, 7.0, 7.2])
do_values = np.array([8.5, 8.3, 8.7, 8.1, 8.4])

quality_indices = water_quality_index(temperatures, ph_values, do_values)
print(f"水质指数: {quality_indices}")

# 数组操作优化
arrays = [temperatures, ph_values, do_values]
optimized_arrays = optimizer.optimize_array_operations(arrays)
print(f"优化后数据类型: {[arr.dtype for arr in optimized_arrays]}")
```

## 性能基准测试

运行 `run_performance_demo.py` 来查看完整的性能优化演示：

```bash
cd examples/07_performance_optimization
python run_performance_demo.py
```

## 最佳实践

### 1. 性能监控
- 在关键函数上使用 `@profile` 装饰器
- 定期生成性能报告，识别瓶颈
- 监控系统资源使用情况
- 设置性能阈值和告警

### 2. 缓存策略
- 对计算密集型函数使用记忆化
- 为频繁访问的数据使用LRU缓存
- 合理设置缓存大小，避免内存溢出
- 定期清理过期缓存

### 3. 算法优化
- 使用NumPy向量化操作替代Python循环
- 对大数据集使用批处理
- 利用并行处理提升计算效率
- 优化数据结构和内存布局

### 4. 系统优化
- 监控内存使用，及时释放资源
- 使用适当的数据类型，减少内存占用
- 避免不必要的数据复制
- 合理配置并行处理参数

## 注意事项

1. **内存管理**: 大数据处理时注意内存使用，避免内存泄漏
2. **并发安全**: 多线程环境下注意线程安全
3. **缓存一致性**: 确保缓存数据的一致性和有效性
4. **性能权衡**: 在性能和代码复杂度之间找到平衡
5. **监控开销**: 性能监控本身也有开销，在生产环境中适度使用

通过合理使用这些性能优化工具，可以显著提升智能水厂系统的运行效率和响应速度。