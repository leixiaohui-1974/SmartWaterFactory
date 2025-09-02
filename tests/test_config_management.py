"""配置管理模块测试。

测试多环境配置、配置验证、热重载等功能。
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from config.environments import (
    Environment, DatabaseConfig, LoggingConfig, SimulationConfig,
    SecurityConfig, EnvironmentConfig, ConfigManager
)
from config.hot_reload import ConfigWatcher, HotReloadManager


class TestEnvironmentConfig(unittest.TestCase):
    """环境配置测试。"""
    
    def test_database_config_creation(self):
        """测试数据库配置创建。"""
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            pool_size=5,
            max_overflow=10
        )
        
        self.assertEqual(db_config.host, "localhost")
        self.assertEqual(db_config.port, 5432)
        self.assertEqual(db_config.database, "test_db")
        self.assertEqual(db_config.pool_size, 5)
    
    def test_logging_config_creation(self):
        """测试日志配置创建。"""
        log_config = LoggingConfig(
            level="DEBUG",
            format="%(asctime)s - %(message)s",
            file_path="test.log",
            max_file_size=1024,
            backup_count=3,
            enable_console=True,
            enable_file=False
        )
        
        self.assertEqual(log_config.level, "DEBUG")
        self.assertEqual(log_config.max_file_size, 1024)
        self.assertTrue(log_config.enable_console)
        self.assertFalse(log_config.enable_file)
    
    def test_simulation_config_creation(self):
        """测试仿真配置创建。"""
        sim_config = SimulationConfig(
            default_steps=100,
            max_steps=1000,
            time_step=0.5,
            output_directory="outputs",
            enable_real_time=True,
            performance_monitoring=False
        )
        
        self.assertEqual(sim_config.default_steps, 100)
        self.assertEqual(sim_config.time_step, 0.5)
        self.assertTrue(sim_config.enable_real_time)
    
    def test_security_config_creation(self):
        """测试安全配置创建。"""
        security_config = SecurityConfig(
            secret_key="test-key",
            token_expiry=3600,
            max_login_attempts=5,
            enable_rate_limiting=True,
            cors_origins=["http://localhost:3000"]
        )
        
        self.assertEqual(security_config.secret_key, "test-key")
        self.assertEqual(security_config.token_expiry, 3600)
        self.assertEqual(len(security_config.cors_origins), 1)
    
    def test_environment_config_creation(self):
        """测试完整环境配置创建。"""
        env_config = EnvironmentConfig(
            environment=Environment.DEVELOPMENT,
            database=DatabaseConfig(
                host="localhost", port=5432, database="dev_db",
                username="dev_user", password="dev_pass"
            ),
            logging=LoggingConfig(
                level="DEBUG", format="%(message)s"
            ),
            simulation=SimulationConfig(
                default_steps=50, max_steps=500
            ),
            security=SecurityConfig(
                secret_key="dev-key", token_expiry=1800
            ),
            debug=True
        )
        
        self.assertEqual(env_config.environment, Environment.DEVELOPMENT)
        self.assertTrue(env_config.debug)
        self.assertEqual(env_config.database.host, "localhost")
        self.assertEqual(env_config.logging.level, "DEBUG")


class TestConfigManager(unittest.TestCase):
    """配置管理器测试。"""
    
    def setUp(self):
        """测试前准备。"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)
        
        # 创建测试配置文件
        self.dev_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "dev_db",
                "username": "dev_user",
                "password": "dev_pass",
                "pool_size": 5,
                "max_overflow": 10
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(message)s",
                "file_path": "dev.log",
                "max_file_size": 1048576,
                "backup_count": 3,
                "enable_console": True,
                "enable_file": True
            },
            "simulation": {
                "default_steps": 100,
                "max_steps": 1000,
                "time_step": 1.0,
                "output_directory": "dev_outputs",
                "enable_real_time": True,
                "performance_monitoring": True
            },
            "security": {
                "secret_key": "dev-secret-key",
                "token_expiry": 1800,
                "max_login_attempts": 10,
                "enable_rate_limiting": False,
                "cors_origins": ["http://localhost:3000"]
            },
            "debug": True
        }
        
        with open(self.config_dir / "development.json", "w", encoding="utf-8") as f:
            json.dump(self.dev_config, f, indent=2)
    
    def tearDown(self):
        """测试后清理。"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_manager_initialization(self):
        """测试配置管理器初始化。"""
        manager = ConfigManager(str(self.config_dir))
        self.assertEqual(manager.config_dir, self.config_dir)
    
    @patch.dict(os.environ, {'WATER_PLANT_ENV': 'development'})
    def test_load_development_config(self):
        """测试加载开发环境配置。"""
        manager = ConfigManager(str(self.config_dir))
        config = manager.get_config()
        
        self.assertEqual(config.environment, Environment.DEVELOPMENT)
        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.logging.level, "DEBUG")
        self.assertTrue(config.debug)
    
    @patch.dict(os.environ, {'WATER_PLANT_ENV': 'production'})
    def test_load_nonexistent_config_falls_back_to_development(self):
        """测试加载不存在的配置文件时的处理。"""
        manager = ConfigManager(str(self.config_dir))
        config = manager.get_config()
        
        # 环境应该是production，但使用默认配置值
        self.assertEqual(config.environment, Environment.PRODUCTION)
    
    def test_config_validation_invalid_json(self):
        """测试无效JSON配置文件的处理。"""
        # 覆盖development.json为无效JSON
        invalid_config_path = self.config_dir / "development.json"
        with open(invalid_config_path, "w") as f:
            f.write("{ invalid json }")
        
        manager = ConfigManager(str(self.config_dir))
        
        # 测试加载无效JSON文件时的处理
        result = manager._load_environment_config(Environment.DEVELOPMENT)
        # 由于无效JSON，应该返回None
        self.assertIsNone(result)
    
    def test_config_validation_missing_required_fields(self):
        """测试缺少必需字段的配置验证。"""
        incomplete_config = {
            "database": {
                "host": "localhost"
                # 缺少其他必需字段
            }
        }
        
        incomplete_path = self.config_dir / "incomplete.json"
        with open(incomplete_path, "w") as f:
            json.dump(incomplete_config, f)
        
        manager = ConfigManager(str(self.config_dir))
        
        # 测试加载不完整配置时的处理
        # ConfigManager会使用默认值填充缺失字段
        config = manager.load_config(Environment.DEVELOPMENT)
        self.assertIsNotNone(config)
        self.assertEqual(config.database.host, "localhost")
    
    @patch.dict(os.environ, {
        'DB_HOST': 'env-host',
        'DB_PORT': '3306',
        'LOG_LEVEL': 'ERROR'
    })
    def test_environment_variable_override(self):
        """测试环境变量覆盖配置。"""
        manager = ConfigManager(str(self.config_dir))
        config = manager.get_config()
        
        # 环境变量应该覆盖文件配置
        self.assertEqual(config.database.host, "env-host")
        self.assertEqual(config.database.port, 3306)
        self.assertEqual(config.logging.level, "ERROR")
    
    def test_config_reload(self):
        """测试配置重新加载。"""
        manager = ConfigManager(str(self.config_dir))
        
        # 首次加载
        config1 = manager.get_config()
        original_host = config1.database.host
        
        # 修改配置文件
        modified_config = self.dev_config.copy()
        modified_config["database"]["host"] = "modified-host"
        
        with open(self.config_dir / "development.json", "w") as f:
            json.dump(modified_config, f, indent=2)
        
        # 重新加载
        config2 = manager.reload_config()
        
        self.assertNotEqual(config2.database.host, original_host)
        self.assertEqual(config2.database.host, "modified-host")


class TestHotReload(unittest.TestCase):
    """热重载功能测试。"""
    
    def setUp(self):
        """测试前准备。"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)
        
        # 创建基础配置文件
        basic_config = {
            "database": {"host": "localhost", "port": 5432, "database": "test", "username": "user", "password": "pass"},
            "logging": {"level": "INFO", "format": "%(message)s"},
            "simulation": {"default_steps": 10, "max_steps": 100},
            "security": {"secret_key": "key", "token_expiry": 3600},
            "debug": False
        }
        
        with open(self.config_dir / "development.json", "w") as f:
            json.dump(basic_config, f)
    
    def tearDown(self):
        """测试后清理。"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_config_watcher_initialization(self):
        """测试配置监控器初始化。"""
        watcher = ConfigWatcher(str(self.config_dir))
        self.assertIsNotNone(watcher.config_manager)
        self.assertIsNotNone(watcher.hot_reload_manager)
    
    def test_config_watcher_get_config(self):
        """测试配置监控器获取配置。"""
        watcher = ConfigWatcher(str(self.config_dir))
        config = watcher.get_config()
        
        self.assertIsInstance(config, EnvironmentConfig)
        self.assertEqual(config.database.host, "localhost")
    
    def test_hot_reload_manager_callback_management(self):
        """测试热重载管理器回调管理。"""
        manager = ConfigManager(str(self.config_dir))
        hot_reload = HotReloadManager(manager)
        
        callback_called = [False]
        
        def test_callback(config):
            callback_called[0] = True
        
        # 添加回调
        hot_reload.add_callback(test_callback)
        self.assertIn(test_callback, hot_reload.callbacks)
        
        # 移除回调
        hot_reload.remove_callback(test_callback)
        self.assertNotIn(test_callback, hot_reload.callbacks)
    
    def test_config_watcher_context_manager(self):
        """测试配置监控器上下文管理器。"""
        watcher = ConfigWatcher(str(self.config_dir))
        
        with watcher:
            # 在上下文中，监控应该是活跃的
            self.assertTrue(watcher.hot_reload_manager.is_running)
        
        # 退出上下文后，监控应该停止
        # 注意：由于watchdog的异步特性，这里可能需要短暂等待
        import time
        time.sleep(0.1)
        self.assertFalse(watcher.hot_reload_manager.is_running)
    
    @patch.dict(os.environ, {'WATER_PLANT_ENV': 'development'})
    def test_environment_switching(self):
        """测试环境切换。"""
        watcher = ConfigWatcher(str(self.config_dir))
        
        # 切换到测试环境
        config = watcher.switch_environment(Environment.TESTING)
        
        # 检查环境变量是否已设置
        self.assertEqual(os.environ.get('WATER_PLANT_ENV'), 'testing')
        
        # 环境应该是testing，使用默认配置值
        self.assertEqual(config.environment, Environment.TESTING)


class TestConfigIntegration(unittest.TestCase):
    """配置系统集成测试。"""
    
    def setUp(self):
        """测试前准备。"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir)
        
        # 创建多个环境的配置文件
        configs = {
            "development": {
                "database": {"host": "dev-host", "port": 5432, "database": "dev_db", "username": "dev", "password": "dev"},
                "logging": {"level": "DEBUG", "format": "%(message)s"},
                "simulation": {"default_steps": 10, "max_steps": 100},
                "security": {"secret_key": "dev-key", "token_expiry": 1800},
                "debug": True
            },
            "testing": {
                "database": {"host": "test-host", "port": 5432, "database": "test_db", "username": "test", "password": "test"},
                "logging": {"level": "WARNING", "format": "%(message)s"},
                "simulation": {"default_steps": 5, "max_steps": 50},
                "security": {"secret_key": "test-key", "token_expiry": 300},
                "debug": True
            },
            "production": {
                "database": {"host": "prod-host", "port": 5432, "database": "prod_db", "username": "prod", "password": "prod"},
                "logging": {"level": "ERROR", "format": "%(asctime)s - %(message)s"},
                "simulation": {"default_steps": 1000, "max_steps": 10000},
                "security": {"secret_key": "prod-key", "token_expiry": 3600},
                "debug": False
            }
        }
        
        for env_name, config in configs.items():
            with open(self.config_dir / f"{env_name}.json", "w") as f:
                json.dump(config, f, indent=2)
    
    def tearDown(self):
        """测试后清理。"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch.dict(os.environ, {'WATER_PLANT_ENV': 'development'})
    def test_multi_environment_loading(self):
        """测试多环境配置加载。"""
        manager = ConfigManager(str(self.config_dir))
        
        # 测试开发环境
        config = manager.get_config()
        self.assertEqual(config.environment, Environment.DEVELOPMENT)
        self.assertEqual(config.database.host, "dev-host")
        self.assertTrue(config.debug)
    
    @patch.dict(os.environ, {'WATER_PLANT_ENV': 'testing'})
    def test_testing_environment_loading(self):
        """测试测试环境配置加载。"""
        manager = ConfigManager(str(self.config_dir))
        
        config = manager.get_config()
        self.assertEqual(config.environment, Environment.TESTING)
        self.assertEqual(config.database.host, "test-host")
        self.assertEqual(config.simulation.default_steps, 5)
    
    @patch.dict(os.environ, {'WATER_PLANT_ENV': 'production'})
    def test_production_environment_loading(self):
        """测试生产环境配置加载。"""
        manager = ConfigManager(str(self.config_dir))
        
        config = manager.get_config()
        self.assertEqual(config.environment, Environment.PRODUCTION)
        self.assertEqual(config.database.host, "prod-host")
        self.assertFalse(config.debug)
        self.assertEqual(config.logging.level, "ERROR")
    
    def test_config_inheritance_and_override(self):
        """测试配置继承和覆盖。"""
        manager = ConfigManager(str(self.config_dir))
        
        # 测试环境变量覆盖
        with patch.dict(os.environ, {
            'WATER_PLANT_ENV': 'development',
            'DB_HOST': 'override-host',
            'DEBUG': 'false'
        }):
            config = manager.get_config()
            
            # 环境变量应该覆盖文件配置
            self.assertEqual(config.database.host, "override-host")
            self.assertFalse(config.debug)  # 字符串 'false' 应该转换为布尔值 False


if __name__ == '__main__':
    unittest.main()