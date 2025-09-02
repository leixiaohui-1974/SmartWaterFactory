# 配置管理示例

本示例演示如何使用水厂控制器的配置管理系统，包括多环境配置、配置热重载和环境变量覆盖等功能。

## 功能特性

### 1. 多环境配置支持
- **开发环境** (development): 用于本地开发，启用调试模式
- **测试环境** (testing): 用于自动化测试，简化配置
- **生产环境** (production): 用于生产部署，优化性能和安全性

### 2. 配置热重载
- 监控配置文件变化
- 自动重新加载配置
- 支持配置变更回调

### 3. 环境变量覆盖
- 支持通过环境变量覆盖配置文件设置
- 适用于容器化部署和CI/CD流水线

### 4. 配置验证
- 自动验证配置格式和类型
- 提供默认值和错误处理

## 配置文件结构

```
config/
├── development.json    # 开发环境配置
├── testing.json       # 测试环境配置
├── production.json    # 生产环境配置
├── environments.py    # 配置管理核心模块
└── hot_reload.py      # 热重载功能模块
```

## 使用方法

### 基本配置加载

```python
from config.environments import get_config

# 获取当前环境配置
config = get_config()
print(f"当前环境: {config.environment.value}")
print(f"数据库主机: {config.database.host}")
print(f"日志级别: {config.logging.level}")
```

### 环境切换

```python
import os
from config.environments import ConfigManager, Environment

# 设置环境变量
os.environ['WATER_PLANT_ENV'] = 'production'

# 重新加载配置
manager = ConfigManager()
config = manager.reload_config()
print(f"切换到: {config.environment.value}")
```

### 配置热重载

```python
from config.hot_reload import ConfigWatcher

def on_config_changed(new_config):
    print(f"配置已更新: {new_config.environment.value}")
    print(f"新的数据库主机: {new_config.database.host}")

# 启动配置监控
with ConfigWatcher() as watcher:
    watcher.add_reload_callback(on_config_changed)
    
    # 应用程序继续运行...
    # 当配置文件发生变化时，会自动调用回调函数
```

### 环境变量覆盖

```bash
# 设置环境变量
export WATER_PLANT_ENV=production
export DB_HOST=prod-database.company.com
export DB_PORT=5432
export LOG_LEVEL=ERROR
export DEBUG=false

# 运行应用程序
python run_simulation.py
```

## 配置项说明

### 数据库配置 (DatabaseConfig)
- `host`: 数据库主机地址
- `port`: 数据库端口
- `database`: 数据库名称
- `username`: 用户名
- `password`: 密码
- `pool_size`: 连接池大小
- `max_overflow`: 最大溢出连接数

### 日志配置 (LoggingConfig)
- `level`: 日志级别 (DEBUG, INFO, WARNING, ERROR)
- `format`: 日志格式
- `file_path`: 日志文件路径
- `max_file_size`: 最大文件大小
- `backup_count`: 备份文件数量
- `enable_console`: 是否启用控制台输出
- `enable_file`: 是否启用文件输出

### 仿真配置 (SimulationConfig)
- `default_steps`: 默认仿真步数
- `max_steps`: 最大仿真步数
- `time_step`: 时间步长
- `output_directory`: 输出目录
- `enable_real_time`: 是否启用实时模式
- `performance_monitoring`: 是否启用性能监控

### 安全配置 (SecurityConfig)
- `secret_key`: 密钥
- `token_expiry`: 令牌过期时间
- `max_login_attempts`: 最大登录尝试次数
- `enable_rate_limiting`: 是否启用速率限制
- `cors_origins`: 允许的跨域来源

## 环境变量映射

| 配置项 | 环境变量 | 示例值 |
|--------|----------|--------|
| 环境类型 | `WATER_PLANT_ENV` | `development` |
| 数据库主机 | `DB_HOST` | `localhost` |
| 数据库端口 | `DB_PORT` | `5432` |
| 数据库名称 | `DB_NAME` | `water_plant` |
| 数据库用户 | `DB_USER` | `admin` |
| 数据库密码 | `DB_PASSWORD` | `password` |
| 日志级别 | `LOG_LEVEL` | `INFO` |
| 日志文件 | `LOG_FILE` | `/var/log/app.log` |
| 密钥 | `SECRET_KEY` | `your-secret-key` |
| 调试模式 | `DEBUG` | `true` |

## 最佳实践

### 1. 环境隔离
- 为每个环境创建独立的配置文件
- 使用环境变量区分不同部署环境
- 避免在代码中硬编码配置值

### 2. 安全性
- 不要在配置文件中存储明文密码
- 使用环境变量传递敏感信息
- 在版本控制中排除包含敏感信息的配置文件

### 3. 配置验证
- 在应用启动时验证配置完整性
- 为关键配置项提供合理的默认值
- 记录配置加载和验证过程

### 4. 热重载使用
- 仅在开发环境启用配置热重载
- 在生产环境中谨慎使用热重载功能
- 确保配置变更不会影响正在运行的关键任务

## 故障排除

### 配置文件未找到
```
警告：无法加载配置文件 config/production.json: [Errno 2] No such file or directory
```
**解决方案**: 确保配置文件存在，或者系统会使用默认配置。

### JSON格式错误
```
警告：无法加载配置文件 config/development.json: Expecting ',' delimiter: line 5 column 10
```
**解决方案**: 检查JSON文件格式，确保语法正确。

### 环境变量类型错误
```
ValueError: invalid literal for int() with base 10: 'invalid_port'
```
**解决方案**: 确保环境变量值的类型正确，如端口号应为数字。

## 扩展功能

### 自定义配置加载器
```python
from config.environments import ConfigManager

class CustomConfigManager(ConfigManager):
    def _apply_custom_overrides(self, config):
        # 实现自定义配置覆盖逻辑
        pass
```

### 配置变更通知
```python
from config.hot_reload import add_config_reload_callback

def notify_services(config):
    # 通知其他服务配置已更新
    pass

add_config_reload_callback(notify_services)
```

这个配置管理系统为水厂控制器提供了灵活、安全和易于维护的配置解决方案。