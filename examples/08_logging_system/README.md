# 日志系统演示

本示例展示智能水厂系统的完整日志管理功能，包括结构化日志、多级别日志、日志轮转和性能监控集成。

## 功能特性

### 1. 结构化日志记录
- **JSON格式日志**：便于日志分析和处理
- **结构化文本日志**：人类可读的格式化输出
- **上下文信息**：自动记录模块、函数、行号等信息
- **异常追踪**：完整的异常堆栈信息记录

### 2. 多级别日志支持
- **DEBUG**：详细的调试信息
- **INFO**：一般信息记录
- **WARNING**：警告信息
- **ERROR**：错误信息
- **CRITICAL**：严重错误信息

### 3. 日志轮转和归档
- **基于大小的轮转**：当日志文件达到指定大小时自动轮转
- **基于时间的轮转**：按时间间隔（如每日、每周）轮转
- **自动压缩**：旧日志文件自动压缩以节省空间
- **备份管理**：自动管理备份文件数量

### 4. 上下文日志记录
- **上下文传递**：在日志中自动包含上下文信息
- **链式上下文**：支持创建带有额外上下文的子记录器
- **性能集成**：与性能监控系统集成

### 5. 专用日志记录器
- **仿真日志**：记录仿真步骤和状态
- **控制日志**：记录控制器动作和参数
- **性能日志**：记录性能指标和监控数据
- **错误日志**：专门的错误和异常记录

## 使用示例

### 基本日志记录

```python
from utils.logging_system import get_logger

# 获取日志记录器
logger = get_logger('water_plant.main')

# 记录不同级别的日志
logger.debug('调试信息：系统初始化开始')
logger.info('系统启动完成')
logger.warning('传感器读数异常')
logger.error('控制器连接失败')
logger.critical('系统紧急停机')
```

### 带上下文的日志记录

```python
# 创建带上下文的日志记录器
logger = get_logger('water_plant.control').with_context(
    controller_id='PID_001',
    plant_section='treatment'
)

# 记录带上下文的日志
logger.info('PID控制器启动', extra_data={
    'setpoint': 50.0,
    'current_value': 45.0
})
```

### 异常日志记录

```python
try:
    # 可能出错的代码
    result = risky_operation()
except Exception as e:
    logger.exception('操作失败', extra_data={
        'operation': 'risky_operation',
        'parameters': {'param1': 'value1'}
    })
```

### 性能日志记录

```python
from utils.logging_system import log_performance

# 记录函数执行性能
start_time = time.time()
result = expensive_function()
execution_time = time.time() - start_time

log_performance('expensive_function', execution_time, 
               result_size=len(result),
               memory_usage=get_memory_usage())
```

### 仿真日志记录

```python
from utils.logging_system import log_simulation_step

# 记录仿真步骤
state = {
    'temperature': 25.0,
    'pressure': 1.2,
    'flow_rate': 100.0
}

log_simulation_step(step=100, state=state, 
                   simulation_time=10.0,
                   convergence=True)
```

### 控制动作日志记录

```python
from utils.logging_system import log_control_action

# 记录控制器动作
log_control_action(
    controller_type='PID',
    setpoint=50.0,
    output=45.0,
    error=5.0,
    integral=2.5,
    derivative=0.1
)
```

## 配置说明

### 日志配置文件

日志系统支持通过配置文件进行详细配置：

```python
config = {
    'version': 1,
    'formatters': {
        'json': {
            'class': 'utils.logging_system.StructuredFormatter',
            'format_type': 'json'
        },
        'structured': {
            'class': 'utils.logging_system.StructuredFormatter',
            'format_type': 'structured'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'structured'
        },
        'file_rotating': {
            'class': 'utils.logging_system.LogRotationHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filename': 'logs/water_plant.log',
            'max_bytes': 10485760,  # 10MB
            'backup_count': 5
        }
    },
    'loggers': {
        'water_plant': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_rotating'],
            'propagate': False
        }
    }
}

from utils.logging_system import setup_logging
setup_logging(config)
```

### 环境变量配置

支持通过环境变量调整日志级别：

```bash
# 设置全局日志级别
export LOG_LEVEL=DEBUG

# 设置特定模块日志级别
export WATER_PLANT_LOG_LEVEL=INFO
export SIMULATION_LOG_LEVEL=DEBUG
```

## 日志文件结构

```
logs/
├── water_plant.log          # 主日志文件
├── water_plant.log.1        # 轮转备份文件
├── water_plant.log.2.gz     # 压缩的备份文件
├── water_plant_error.log    # 错误专用日志
├── water_plant_debug.log    # 调试日志（按日轮转）
└── performance/
    ├── 2024-01-15.log      # 按日期分组的性能日志
    └── 2024-01-16.log
```

## 日志分析

### JSON日志查询

使用 `jq` 工具分析JSON格式日志：

```bash
# 查询错误日志
cat logs/water_plant.log | jq 'select(.level == "ERROR")'

# 查询特定时间范围的日志
cat logs/water_plant.log | jq 'select(.timestamp > 1640995200)'

# 统计各级别日志数量
cat logs/water_plant.log | jq -r '.level' | sort | uniq -c
```

### 性能分析

```bash
# 查询性能日志
cat logs/water_plant.log | jq 'select(.extra_data.performance_metric == true)'

# 分析函数执行时间
cat logs/water_plant.log | jq -r 'select(.extra_data.function_name) | "\(.extra_data.function_name): \(.extra_data.execution_time)"'
```

## 最佳实践

### 1. 日志级别使用
- **DEBUG**：仅在开发和调试时使用
- **INFO**：记录重要的业务流程
- **WARNING**：记录可能的问题但不影响运行
- **ERROR**：记录错误但系统可以继续运行
- **CRITICAL**：记录严重错误，系统可能无法继续

### 2. 上下文信息
- 在日志中包含足够的上下文信息
- 使用结构化数据而不是字符串拼接
- 避免记录敏感信息（如密码、密钥）

### 3. 性能考虑
- 在生产环境中适当调整日志级别
- 使用异步日志记录器处理高频日志
- 定期清理旧日志文件

### 4. 监控和告警
- 监控错误日志的频率
- 设置关键错误的告警机制
- 定期分析日志模式和趋势

## 集成示例

### 与性能监控集成

```python
from utils.performance import PerformanceProfiler
from utils.logging_system import get_logger

logger = get_logger('water_plant.performance')
profiler = PerformanceProfiler()

@profiler.profile_function
def critical_function():
    # 关键函数实现
    pass

# 自动记录性能日志
metrics = profiler.get_function_metrics('critical_function')
logger.info('函数性能报告', extra_data=metrics)
```

### 与异常处理集成

```python
from utils.logging_system import log_error_with_context

def safe_operation(data):
    try:
        return process_data(data)
    except ValidationError as e:
        log_error_with_context(e, {
            'data_size': len(data),
            'operation': 'process_data',
            'validation_rules': get_validation_rules()
        })
        raise
    except Exception as e:
        log_error_with_context(e, {
            'data': data,
            'operation': 'process_data'
        })
        raise
```

这个日志系统为智能水厂提供了完整的日志管理解决方案，支持开发、测试和生产环境的不同需求。