"""多环境配置管理模块。

该模块提供了对不同环境（开发、测试、生产）配置的支持，
允许根据环境变量或配置文件动态加载相应的配置参数。
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class Environment(Enum):
    """环境类型枚举。"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """数据库配置。"""
    host: str = "localhost"
    port: int = 5432
    database: str = "water_plant"
    username: str = "admin"
    password: str = "password"
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class LoggingConfig:
    """日志配置。"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_console: bool = True
    enable_file: bool = False


@dataclass
class SimulationConfig:
    """仿真配置。"""
    default_steps: int = 100
    max_steps: int = 10000
    time_step: float = 1.0
    output_directory: str = "outputs"
    enable_real_time: bool = False
    performance_monitoring: bool = False
    enable_noise: bool = False
    noise_level: float = 0.01
    enable_disturbances: bool = False


@dataclass
class SecurityConfig:
    """安全配置。"""
    secret_key: str = "dev-secret-key"
    token_expiry: int = 3600  # 1小时
    max_login_attempts: int = 5
    enable_rate_limiting: bool = True
    cors_origins: list = None

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000"]


@dataclass
class EnvironmentConfig:
    """完整的环境配置。"""
    environment: Environment
    database: DatabaseConfig
    logging: LoggingConfig
    simulation: SimulationConfig
    security: SecurityConfig
    debug: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典。"""
        result = asdict(self)
        # 将Environment枚举转换为字符串
        result['environment'] = self.environment.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentConfig':
        """从字典创建配置对象。"""
        env = Environment(data.get('environment', 'development'))
        
        return cls(
            environment=env,
            database=DatabaseConfig(**data.get('database', {})),
            logging=LoggingConfig(**data.get('logging', {})),
            simulation=SimulationConfig(**data.get('simulation', {})),
            security=SecurityConfig(**data.get('security', {})),
            debug=data.get('debug', False)
        )


class ConfigManager:
    """配置管理器。
    
    负责加载、验证和管理不同环境的配置。
    支持从环境变量、配置文件和默认值加载配置。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """初始化配置管理器。
        
        Args:
            config_dir: 配置文件目录路径，默认为项目根目录下的config文件夹
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self._current_config: Optional[EnvironmentConfig] = None
        self._config_cache: Dict[Environment, EnvironmentConfig] = {}
    
    def get_current_environment(self) -> Environment:
        """获取当前环境。
        
        优先级：环境变量 > 配置文件 > 默认值(development)
        """
        env_name = os.getenv('WATER_PLANT_ENV', 'development').lower()
        try:
            return Environment(env_name)
        except ValueError:
            return Environment.DEVELOPMENT
    
    def load_config(self, environment: Optional[Environment] = None) -> EnvironmentConfig:
        """加载指定环境的配置。
        
        Args:
            environment: 目标环境，如果为None则使用当前环境
            
        Returns:
            EnvironmentConfig: 加载的配置对象
        """
        if environment is None:
            environment = self.get_current_environment()
        
        # 检查缓存
        if environment in self._config_cache:
            return self._config_cache[environment]
        
        # 加载基础配置
        config = self._load_base_config()
        
        # 加载环境特定配置
        env_config = self._load_environment_config(environment)
        if env_config:
            config = self._merge_configs(config, env_config)
        
        # 应用环境变量覆盖
        config = self._apply_env_overrides(config)
        
        # 设置环境类型
        config.environment = environment
        
        # 缓存配置
        self._config_cache[environment] = config
        self._current_config = config
        
        return config
    
    def _load_base_config(self) -> EnvironmentConfig:
        """加载基础配置。"""
        return EnvironmentConfig(
            environment=Environment.DEVELOPMENT,
            database=DatabaseConfig(),
            logging=LoggingConfig(),
            simulation=SimulationConfig(),
            security=SecurityConfig()
        )
    
    def _load_environment_config(self, environment: Environment) -> Optional[Dict[str, Any]]:
        """加载环境特定配置文件。"""
        config_file = self.config_dir / f"{environment.value}.json"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告：无法加载配置文件 {config_file}: {e}")
            return None
    
    def _merge_configs(self, base: EnvironmentConfig, override: Dict[str, Any]) -> EnvironmentConfig:
        """合并配置。"""
        base_dict = base.to_dict()
        
        # 深度合并字典
        for key, value in override.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                base_dict[key].update(value)
            else:
                base_dict[key] = value
        
        return EnvironmentConfig.from_dict(base_dict)
    
    def _apply_env_overrides(self, config: EnvironmentConfig) -> EnvironmentConfig:
        """应用环境变量覆盖。"""
        # 数据库配置覆盖
        if os.getenv('DB_HOST'):
            config.database.host = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            config.database.port = int(os.getenv('DB_PORT'))
        if os.getenv('DB_NAME'):
            config.database.database = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            config.database.username = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            config.database.password = os.getenv('DB_PASSWORD')
        
        # 日志配置覆盖
        if os.getenv('LOG_LEVEL'):
            config.logging.level = os.getenv('LOG_LEVEL')
        if os.getenv('LOG_FILE'):
            config.logging.file_path = os.getenv('LOG_FILE')
            config.logging.enable_file = True
        
        # 安全配置覆盖
        if os.getenv('SECRET_KEY'):
            config.security.secret_key = os.getenv('SECRET_KEY')
        
        # 调试模式
        if os.getenv('DEBUG'):
            config.debug = os.getenv('DEBUG').lower() in ('true', '1', 'yes')
        
        return config
    
    def get_config(self) -> EnvironmentConfig:
        """获取当前配置。"""
        if self._current_config is None:
            self._current_config = self.load_config()
        return self._current_config
    
    def reload_config(self) -> EnvironmentConfig:
        """重新加载配置。"""
        self._config_cache.clear()
        self._current_config = None
        return self.load_config()
    
    def save_config(self, config: EnvironmentConfig, environment: Optional[Environment] = None) -> None:
        """保存配置到文件。
        
        Args:
            config: 要保存的配置
            environment: 目标环境，如果为None则使用配置中的环境
        """
        if environment is None:
            environment = config.environment
        
        config_file = self.config_dir / f"{environment.value}.json"
        
        # 确保目录存在
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存配置（排除敏感信息）
        config_dict = config.to_dict()
        # 移除敏感信息
        if 'security' in config_dict and 'secret_key' in config_dict['security']:
            config_dict['security']['secret_key'] = "***HIDDEN***"
        if 'database' in config_dict and 'password' in config_dict['database']:
            config_dict['database']['password'] = "***HIDDEN***"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise RuntimeError(f"无法保存配置文件 {config_file}: {e}")


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> EnvironmentConfig:
    """获取当前配置的便捷函数。"""
    return config_manager.get_config()


def reload_config() -> EnvironmentConfig:
    """重新加载配置的便捷函数。"""
    return config_manager.reload_config()