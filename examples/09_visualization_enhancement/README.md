# 可视化功能增强示例

本示例展示智能水厂系统的增强可视化功能，包括实时监控仪表板、交互式图表和高级数据分析工具。

## 功能特性

### 1. 实时监控仪表板
- **多标签页界面**：水质监控、性能监控、系统状态分离显示
- **实时数据更新**：支持可配置的更新间隔
- **交互式控制**：启动/停止监控、保存图表等操作
- **系统状态显示**：CPU、内存、磁盘使用率实时监控

### 2. 增强的图表系统
- **实时图表**：支持多数据序列的实时更新
- **主题支持**：默认、深色、浅色主题切换
- **自动缩放**：智能坐标轴调整
- **数据点管理**：自动限制数据点数量，防止内存溢出
- **图表保存**：支持高质量图片导出

### 3. 数据序列管理
- **灵活配置**：颜色、线型、标记样式自定义
- **时间窗口**：支持获取指定时间范围内的数据
- **统计信息**：自动计算最值、均值等统计量
- **数据持久化**：支持数据的保存和加载

### 4. 高级数据分析
- **趋势分析**：自动检测数据趋势（上升、下降、稳定）
- **异常检测**：基于统计方法的异常值识别
- **线性回归**：计算趋势斜率和拟合度
- **汇总报告**：生成详细的数据分析报告

### 5. 性能监控集成
- **系统资源监控**：CPU、内存、磁盘使用率
- **进程信息显示**：进程ID、线程数、内存占用
- **性能指标可视化**：进度条和数值显示
- **颜色编码**：根据使用率自动调整显示颜色

## 使用示例

### 基本实时图表

```python
from utils.visualization import create_real_time_chart, VisualizationConfig

# 创建配置
config = VisualizationConfig(
    update_interval=1.0,
    theme='dark',
    figure_size=(10, 6)
)

# 创建图表
chart = create_real_time_chart("水质监控", "浓度 (mg/L)", config)

# 添加数据序列
turbidity_series = chart.add_series("浊度", color='blue', unit='NTU')
do_series = chart.add_series("溶解氧", color='red', unit='mg/L')

# 更新数据
chart.update_data("浊度", 2.5)
chart.update_data("溶解氧", 8.2)

# 启动动画
chart.start_animation()
```

### 实时监控仪表板

```python
from utils.visualization import create_monitoring_dashboard

# 创建仪表板
dashboard = create_monitoring_dashboard()

# 运行仪表板
dashboard.run()
```

### 数据分析

```python
from utils.visualization import DataSeries, DataAnalyzer
from datetime import datetime

# 创建数据序列
series = DataSeries(name="温度", unit="°C")

# 添加数据
for i in range(100):
    series.add_point(20 + i * 0.1 + random.gauss(0, 0.5))

# 分析趋势
analyzer = DataAnalyzer()
trends = analyzer.analyze_trends(series)
print(f"趋势: {trends['trend']}")
print(f"斜率: {trends['slope']:.4f}")
print(f"拟合度: {trends['r_squared']:.4f}")

# 检测异常
anomalies = analyzer.detect_anomalies(series)
print(f"检测到 {len(anomalies)} 个异常值")
```

### 配置自定义

```python
from utils.visualization import VisualizationConfig

# 自定义配置
config = VisualizationConfig(
    update_interval=0.5,      # 更新间隔500ms
    max_data_points=2000,     # 最大2000个数据点
    figure_size=(15, 10),     # 图表尺寸
    dpi=150,                  # 高分辨率
    theme='dark',             # 深色主题
    auto_scale=True,          # 自动缩放
    show_grid=True,           # 显示网格
    line_width=3.0,           # 线条宽度
    marker_size=6.0           # 标记大小
)
```

## 高级功能

### 1. 主题定制

系统支持三种内置主题：
- **default**: 默认主题，适合一般使用
- **dark**: 深色主题，适合低光环境
- **light**: 浅色主题，适合打印和演示

### 2. 数据窗口管理

```python
# 获取最近1小时的数据
recent_timestamps, recent_data = series.get_recent_data(60)

# 获取最近24小时的数据
daily_timestamps, daily_data = series.get_recent_data(1440)
```

### 3. 异常检测配置

```python
# 调整异常检测阈值
anomalies = analyzer.detect_anomalies(series, threshold=3.0)  # 3σ阈值

# 更严格的异常检测
anomalies = analyzer.detect_anomalies(series, threshold=2.0)  # 2σ阈值
```

### 4. 趋势分析窗口

```python
# 使用不同的窗口大小分析趋势
short_term = analyzer.analyze_trends(series, window_size=10)   # 短期趋势
long_term = analyzer.analyze_trends(series, window_size=50)    # 长期趋势
```

## 性能优化

### 1. 数据点限制
- 自动限制数据点数量，防止内存溢出
- 使用deque数据结构，高效的FIFO操作
- 可配置的最大数据点数量

### 2. 更新频率控制
- 可配置的更新间隔
- 异步数据更新，不阻塞UI
- 智能重绘，只在数据变化时更新

### 3. 内存管理
- 自动清理过期数据
- 延迟加载大数据集
- 压缩历史数据存储

## 集成示例

### 与性能监控集成

```python
from utils.performance import PerformanceProfiler
from utils.visualization import create_monitoring_dashboard

# 创建性能分析器
profiler = PerformanceProfiler()

# 创建监控仪表板
dashboard = create_monitoring_dashboard()

# 启动系统监控
profiler.start_system_monitoring()

# 运行仪表板
dashboard.run()
```

### 与日志系统集成

```python
from utils.logging_system import get_logger
from utils.visualization import DataAnalyzer

# 获取日志记录器
logger = get_logger("visualization")

# 创建数据分析器
analyzer = DataAnalyzer()

# 分析数据并记录日志
trends = analyzer.analyze_trends(series)
logger.info("数据趋势分析完成", extra={
    "trend": trends['trend'],
    "slope": trends['slope'],
    "r_squared": trends['r_squared']
})
```

## 最佳实践

### 1. 配置管理
- 根据使用场景选择合适的更新间隔
- 合理设置最大数据点数量
- 选择适合的主题和样式

### 2. 性能优化
- 避免过于频繁的数据更新
- 定期清理不需要的历史数据
- 使用合适的图表尺寸和分辨率

### 3. 用户体验
- 提供清晰的状态指示
- 支持用户交互操作
- 合理的颜色编码和图例

### 4. 错误处理
- 优雅处理数据异常
- 提供有意义的错误信息
- 支持系统恢复和重试

## 故障排除

### 常见问题

1. **图表不更新**
   - 检查动画是否已启动
   - 确认数据更新频率设置
   - 验证数据序列名称是否正确

2. **内存使用过高**
   - 减少最大数据点数量
   - 增加数据清理频率
   - 检查是否有内存泄漏

3. **界面响应缓慢**
   - 降低更新频率
   - 减少同时显示的数据序列
   - 优化图表渲染设置

4. **主题显示异常**
   - 确认matplotlib版本兼容性
   - 检查字体设置
   - 验证颜色配置

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查数据序列状态
print(f"数据点数量: {len(series.data)}")
print(f"最新值: {list(series.data)[-1] if series.data else 'None'}")
print(f"时间范围: {series.timestamps[0]} - {series.timestamps[-1]}")

# 验证图表配置
print(f"主题: {chart.config.theme}")
print(f"更新间隔: {chart.config.update_interval}")
print(f"动画状态: {chart.is_running}")
```

## 扩展开发

### 自定义图表类型

```python
class CustomChart(RealTimeChart):
    def __init__(self, title, ylabel, config):
        super().__init__(title, ylabel, config)
        # 添加自定义功能
    
    def custom_analysis(self):
        # 实现自定义分析逻辑
        pass
```

### 新增数据分析方法

```python
class ExtendedAnalyzer(DataAnalyzer):
    def fourier_analysis(self, series):
        # 实现傅里叶分析
        pass
    
    def correlation_analysis(self, series1, series2):
        # 实现相关性分析
        pass
```

这个可视化增强系统为智能水厂提供了强大的数据可视化和分析能力，支持实时监控、趋势分析和异常检测，是系统监控和决策支持的重要工具。