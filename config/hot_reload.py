"""配置热重载模块。

该模块提供配置文件的热重载功能，当配置文件发生变化时
自动重新加载配置，无需重启应用程序。
"""

import os
import time
import threading
from typing import Dict, Callable, Optional, Set
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .environments import ConfigManager, EnvironmentConfig, Environment


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变化处理器。"""
    
    def __init__(self, config_manager: ConfigManager, callback: Optional[Callable[[EnvironmentConfig], None]] = None):
        """初始化处理器。
        
        Args:
            config_manager: 配置管理器实例
            callback: 配置重载后的回调函数
        """
        super().__init__()
        self.config_manager = config_manager
        self.callback = callback
        self.last_reload_time = 0
        self.reload_cooldown = 1.0  # 1秒冷却时间，避免频繁重载
        
    def on_modified(self, event):
        """文件修改事件处理。"""
        if event.is_directory:
            return
            
        # 只处理JSON配置文件
        if not event.src_path.endswith('.json'):
            return
            
        # 检查冷却时间
        current_time = time.time()
        if current_time - self.last_reload_time < self.reload_cooldown:
            return
            
        try:
            print(f"检测到配置文件变化: {event.src_path}")
            
            # 重新加载配置
            new_config = self.config_manager.reload_config()
            self.last_reload_time = current_time
            
            print(f"配置已重新加载，当前环境: {new_config.environment.value}")
            
            # 执行回调
            if self.callback:
                self.callback(new_config)
                
        except Exception as e:
            print(f"配置重载失败: {e}")


class HotReloadManager:
    """配置热重载管理器。
    
    负责监控配置文件变化并自动重新加载配置。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """初始化热重载管理器。
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.observer: Optional[Observer] = None
        self.callbacks: Set[Callable[[EnvironmentConfig], None]] = set()
        self.is_running = False
        self._lock = threading.Lock()
        
    def add_callback(self, callback: Callable[[EnvironmentConfig], None]) -> None:
        """添加配置重载回调函数。
        
        Args:
            callback: 当配置重载时调用的函数，接收新配置作为参数
        """
        with self._lock:
            self.callbacks.add(callback)
    
    def remove_callback(self, callback: Callable[[EnvironmentConfig], None]) -> None:
        """移除配置重载回调函数。
        
        Args:
            callback: 要移除的回调函数
        """
        with self._lock:
            self.callbacks.discard(callback)
    
    def _notify_callbacks(self, config: EnvironmentConfig) -> None:
        """通知所有回调函数。
        
        Args:
            config: 新的配置对象
        """
        with self._lock:
            for callback in self.callbacks.copy():
                try:
                    callback(config)
                except Exception as e:
                    print(f"配置回调执行失败: {e}")
    
    def start(self) -> None:
        """启动热重载监控。"""
        if self.is_running:
            print("热重载已经在运行中")
            return
            
        try:
            self.observer = Observer()
            
            # 创建事件处理器
            handler = ConfigFileHandler(
                self.config_manager,
                self._notify_callbacks
            )
            
            # 监控配置目录
            config_dir = self.config_manager.config_dir
            if config_dir.exists():
                self.observer.schedule(handler, str(config_dir), recursive=False)
                self.observer.start()
                self.is_running = True
                print(f"配置热重载已启动，监控目录: {config_dir}")
            else:
                print(f"配置目录不存在: {config_dir}")
                
        except Exception as e:
            print(f"启动配置热重载失败: {e}")
            self.is_running = False
    
    def stop(self) -> None:
        """停止热重载监控。"""
        if not self.is_running:
            return
            
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5.0)
                self.observer = None
            
            self.is_running = False
            print("配置热重载已停止")
            
        except Exception as e:
            print(f"停止配置热重载失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口。"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""
        self.stop()


class ConfigWatcher:
    """配置监控器。
    
    提供简化的配置监控接口，自动管理配置管理器和热重载。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """初始化配置监控器。
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_manager = ConfigManager(config_dir)
        self.hot_reload_manager = HotReloadManager(self.config_manager)
        self._current_config: Optional[EnvironmentConfig] = None
        
    def get_config(self) -> EnvironmentConfig:
        """获取当前配置。"""
        if self._current_config is None:
            self._current_config = self.config_manager.get_config()
        return self._current_config
    
    def start_watching(self) -> None:
        """开始监控配置变化。"""
        # 添加内部回调来更新当前配置
        self.hot_reload_manager.add_callback(self._update_current_config)
        self.hot_reload_manager.start()
    
    def stop_watching(self) -> None:
        """停止监控配置变化。"""
        self.hot_reload_manager.stop()
    
    def add_reload_callback(self, callback: Callable[[EnvironmentConfig], None]) -> None:
        """添加配置重载回调。
        
        Args:
            callback: 配置重载时调用的函数
        """
        self.hot_reload_manager.add_callback(callback)
    
    def remove_reload_callback(self, callback: Callable[[EnvironmentConfig], None]) -> None:
        """移除配置重载回调。
        
        Args:
            callback: 要移除的回调函数
        """
        self.hot_reload_manager.remove_callback(callback)
    
    def _update_current_config(self, config: EnvironmentConfig) -> None:
        """更新当前配置的内部回调。
        
        Args:
            config: 新的配置对象
        """
        self._current_config = config
    
    def reload_config(self) -> EnvironmentConfig:
        """手动重新加载配置。
        
        Returns:
            EnvironmentConfig: 重新加载的配置
        """
        self._current_config = self.config_manager.reload_config()
        return self._current_config
    
    def switch_environment(self, environment: Environment) -> EnvironmentConfig:
        """切换到指定环境。
        
        Args:
            environment: 目标环境
            
        Returns:
            EnvironmentConfig: 新环境的配置
        """
        # 设置环境变量
        os.environ['WATER_PLANT_ENV'] = environment.value
        
        # 重新加载配置
        return self.reload_config()
    
    def __enter__(self):
        """上下文管理器入口。"""
        self.start_watching()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""
        self.stop_watching()


# 全局配置监控器实例
config_watcher = ConfigWatcher()


def start_config_watching() -> None:
    """启动全局配置监控。"""
    config_watcher.start_watching()


def stop_config_watching() -> None:
    """停止全局配置监控。"""
    config_watcher.stop_watching()


def get_watched_config() -> EnvironmentConfig:
    """获取被监控的配置。"""
    return config_watcher.get_config()


def add_config_reload_callback(callback: Callable[[EnvironmentConfig], None]) -> None:
    """添加全局配置重载回调。"""
    config_watcher.add_reload_callback(callback)


def remove_config_reload_callback(callback: Callable[[EnvironmentConfig], None]) -> None:
    """移除全局配置重载回调。"""
    config_watcher.remove_reload_callback(callback)