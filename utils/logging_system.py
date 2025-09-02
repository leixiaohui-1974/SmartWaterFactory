#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能水厂系统日志管理模块。

本模块提供完整的日志管理功能，包括：
1. 结构化日志记录
2. 多级别日志支持
3. 日志轮转和归档
4. 性能监控集成
5. 异常追踪和报告
"""

import logging
import logging.handlers
import json
import time
import traceback
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sys
import os


class LogLevel(Enum):
    """日志级别枚举。"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """日志格式枚举。"""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class LogEntry:
    """结构化日志条目。"""
    timestamp: float
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    extra_data: Dict[str, Any]
    exception_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON格式。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
    
    @property
    def formatted_timestamp(self) -> str:
        """格式化的时间戳。"""
        return datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器。"""
    
    def __init__(self, format_type: LogFormat = LogFormat.JSON):
        super().__init__()
        self.format_type = format_type
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录。"""
        # 创建结构化日志条目
        log_entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
            thread_id=record.thread,
            process_id=record.process,
            extra_data=getattr(record, 'extra_data', {})
        )
        
        # 处理异常信息
        if record.exc_info:
            log_entry.exception_info = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # 根据格式类型返回相应格式
        if self.format_type == LogFormat.JSON:
            return log_entry.to_json()
        elif self.format_type == LogFormat.STRUCTURED:
            return self._format_structured(log_entry)
        else:  # TEXT
            return self._format_text(log_entry)
    
    def _format_structured(self, entry: LogEntry) -> str:
        """格式化为结构化文本。"""
        parts = [
            f"[{entry.formatted_timestamp}]",
            f"[{entry.level}]",
            f"[{entry.logger_name}]",
            f"[{entry.module}:{entry.function}:{entry.line_number}]",
            f"[PID:{entry.process_id}]",
            f"[TID:{entry.thread_id}]",
            entry.message
        ]
        
        result = " ".join(parts)
        
        # 添加额外数据
        if entry.extra_data:
            extra_str = json.dumps(entry.extra_data, ensure_ascii=False)
            result += f" | Extra: {extra_str}"
        
        # 添加异常信息
        if entry.exception_info:
            result += f" | Exception: {entry.exception_info['type']}: {entry.exception_info['message']}"
        
        return result
    
    def _format_text(self, entry: LogEntry) -> str:
        """格式化为简单文本。"""
        return f"{entry.formatted_timestamp} - {entry.level} - {entry.logger_name} - {entry.message}"


class LogRotationHandler(logging.handlers.RotatingFileHandler):
    """增强的日志轮转处理器。"""
    
    def __init__(self, filename: str, max_bytes: int = 10*1024*1024, 
                 backup_count: int = 5, encoding: str = 'utf-8',
                 compress_old_logs: bool = True):
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding)
        self.compress_old_logs = compress_old_logs
    
    def doRollover(self):
        """执行日志轮转。"""
        super().doRollover()
        
        # 压缩旧日志文件
        if self.compress_old_logs:
            self._compress_old_logs()
    
    def _compress_old_logs(self):
        """压缩旧的日志文件。"""
        try:
            import gzip
            import shutil
            
            base_filename = self.baseFilename
            for i in range(1, self.backupCount + 1):
                old_log = f"{base_filename}.{i}"
                compressed_log = f"{old_log}.gz"
                
                if os.path.exists(old_log) and not os.path.exists(compressed_log):
                    with open(old_log, 'rb') as f_in:
                        with gzip.open(compressed_log, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(old_log)
        except Exception as e:
            # 压缩失败不应该影响日志记录
            pass


class TimedRotationHandler(logging.handlers.TimedRotatingFileHandler):
    """基于时间的日志轮转处理器。"""
    
    def __init__(self, filename: str, when: str = 'midnight', interval: int = 1,
                 backup_count: int = 30, encoding: str = 'utf-8',
                 compress_old_logs: bool = True):
        super().__init__(filename, when=when, interval=interval, 
                        backupCount=backup_count, encoding=encoding)
        self.compress_old_logs = compress_old_logs
    
    def doRollover(self):
        """执行基于时间的日志轮转。"""
        super().doRollover()
        
        # 压缩旧日志文件
        if self.compress_old_logs:
            self._compress_old_logs()
    
    def _compress_old_logs(self):
        """压缩旧的日志文件。"""
        try:
            import gzip
            import shutil
            import glob
            
            # 查找所有旧日志文件
            pattern = f"{self.baseFilename}.*"
            old_logs = glob.glob(pattern)
            
            for old_log in old_logs:
                if not old_log.endswith('.gz') and old_log != self.baseFilename:
                    compressed_log = f"{old_log}.gz"
                    
                    if not os.path.exists(compressed_log):
                        with open(old_log, 'rb') as f_in:
                            with gzip.open(compressed_log, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        os.remove(old_log)
        except Exception as e:
            # 压缩失败不应该影响日志记录
            pass


class LoggerManager:
    """日志管理器。"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: Dict[str, logging.Handler] = {}
        self._lock = threading.Lock()
        
        # 初始化根日志配置
        self._setup_root_logger()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置。"""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    'class': 'utils.logging_system.StructuredFormatter',
                    'format_type': 'json'
                },
                'structured': {
                    'class': 'utils.logging_system.StructuredFormatter',
                    'format_type': 'structured'
                },
                'simple': {
                    'class': 'utils.logging_system.StructuredFormatter',
                    'format_type': 'text'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'structured',
                    'stream': 'ext://sys.stdout'
                },
                'file_info': {
                    'class': 'utils.logging_system.LogRotationHandler',
                    'level': 'INFO',
                    'formatter': 'json',
                    'filename': 'logs/water_plant.log',
                    'max_bytes': 10485760,  # 10MB
                    'backup_count': 5
                },
                'file_error': {
                    'class': 'utils.logging_system.LogRotationHandler',
                    'level': 'ERROR',
                    'formatter': 'json',
                    'filename': 'logs/water_plant_error.log',
                    'max_bytes': 10485760,  # 10MB
                    'backup_count': 10
                },
                'file_debug': {
                    'class': 'utils.logging_system.TimedRotationHandler',
                    'level': 'DEBUG',
                    'formatter': 'json',
                    'filename': 'logs/water_plant_debug.log',
                    'when': 'midnight',
                    'interval': 1,
                    'backup_count': 7
                }
            },
            'loggers': {
                'water_plant': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file_info', 'file_error'],
                    'propagate': False
                },
                'water_plant.simulation': {
                    'level': 'DEBUG',
                    'handlers': ['file_debug'],
                    'propagate': True
                },
                'water_plant.control': {
                    'level': 'INFO',
                    'handlers': ['console', 'file_info'],
                    'propagate': True
                },
                'water_plant.performance': {
                    'level': 'INFO',
                    'handlers': ['file_info'],
                    'propagate': True
                }
            },
            'root': {
                'level': 'WARNING',
                'handlers': ['console']
            }
        }
    
    def _setup_root_logger(self):
        """设置根日志记录器。"""
        # 确保日志目录存在
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config['root']['level']))
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(StructuredFormatter(LogFormat.STRUCTURED))
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str, **kwargs) -> logging.Logger:
        """获取或创建日志记录器。
        
        Args:
            name: 日志记录器名称
            **kwargs: 额外配置参数
        
        Returns:
            配置好的日志记录器
        """
        with self._lock:
            if name in self.loggers:
                return self.loggers[name]
            
            # 创建新的日志记录器
            logger = logging.getLogger(name)
            
            # 应用配置
            if name in self.config['loggers']:
                logger_config = self.config['loggers'][name]
                logger.setLevel(getattr(logging, logger_config['level']))
                logger.propagate = logger_config.get('propagate', True)
                
                # 添加处理器
                for handler_name in logger_config['handlers']:
                    handler = self._get_handler(handler_name)
                    if handler:
                        logger.addHandler(handler)
            else:
                # 使用默认配置
                logger.setLevel(logging.INFO)
                console_handler = self._get_handler('console')
                if console_handler:
                    logger.addHandler(console_handler)
            
            # 应用额外配置
            for key, value in kwargs.items():
                if key == 'level':
                    logger.setLevel(getattr(logging, value.upper()))
                elif key == 'propagate':
                    logger.propagate = value
            
            self.loggers[name] = logger
            return logger
    
    def _get_handler(self, handler_name: str) -> Optional[logging.Handler]:
        """获取或创建处理器。"""
        if handler_name in self.handlers:
            return self.handlers[handler_name]
        
        if handler_name not in self.config['handlers']:
            return None
        
        handler_config = self.config['handlers'][handler_name]
        handler_class = handler_config['class']
        
        try:
            # 创建处理器
            if handler_class == 'logging.StreamHandler':
                handler = logging.StreamHandler(sys.stdout)
            elif handler_class == 'utils.logging_system.LogRotationHandler':
                # 确保日志目录存在
                log_file = Path(handler_config['filename'])
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                handler = LogRotationHandler(
                    filename=handler_config['filename'],
                    max_bytes=handler_config.get('max_bytes', 10*1024*1024),
                    backup_count=handler_config.get('backup_count', 5)
                )
            elif handler_class == 'utils.logging_system.TimedRotationHandler':
                # 确保日志目录存在
                log_file = Path(handler_config['filename'])
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                handler = TimedRotationHandler(
                    filename=handler_config['filename'],
                    when=handler_config.get('when', 'midnight'),
                    interval=handler_config.get('interval', 1),
                    backup_count=handler_config.get('backup_count', 30)
                )
            else:
                return None
            
            # 设置级别
            handler.setLevel(getattr(logging, handler_config['level']))
            
            # 设置格式化器
            formatter_name = handler_config.get('formatter', 'simple')
            formatter_config = self.config['formatters'].get(formatter_name, {})
            
            if formatter_name == 'json':
                formatter = StructuredFormatter(LogFormat.JSON)
            elif formatter_name == 'structured':
                formatter = StructuredFormatter(LogFormat.STRUCTURED)
            else:
                formatter = StructuredFormatter(LogFormat.TEXT)
            
            handler.setFormatter(formatter)
            
            self.handlers[handler_name] = handler
            return handler
            
        except Exception as e:
            print(f"创建处理器 {handler_name} 失败: {e}")
            return None
    
    def add_handler(self, logger_name: str, handler: logging.Handler):
        """为指定日志记录器添加处理器。"""
        logger = self.get_logger(logger_name)
        logger.addHandler(handler)
    
    def remove_handler(self, logger_name: str, handler: logging.Handler):
        """从指定日志记录器移除处理器。"""
        if logger_name in self.loggers:
            self.loggers[logger_name].removeHandler(handler)
    
    def set_level(self, logger_name: str, level: Union[str, int]):
        """设置日志记录器级别。"""
        logger = self.get_logger(logger_name)
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        logger.setLevel(level)
    
    def cleanup(self):
        """清理资源。"""
        for handler in self.handlers.values():
            handler.close()
        self.handlers.clear()
        self.loggers.clear()


class ContextualLogger:
    """上下文日志记录器。"""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any] = None):
        self.logger = logger
        self.context = context or {}
    
    def _log_with_context(self, level: int, message: str, *args, **kwargs):
        """带上下文的日志记录。"""
        # 合并上下文数据
        extra_data = self.context.copy()
        extra_data.update(kwargs.pop('extra_data', {}))
        
        # 获取异常信息
        exc_info = kwargs.pop('exc_info', None)
        if exc_info is True:
            exc_info = sys.exc_info()
        
        # 创建日志记录
        record = self.logger.makeRecord(
            self.logger.name, level, 
            kwargs.pop('pathname', ''), kwargs.pop('lineno', 0),
            message % args if args else message,
            args, exc_info
        )
        
        # 添加额外数据
        record.extra_data = extra_data
        
        # 记录日志
        self.logger.handle(record)
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试日志。"""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录信息日志。"""
        self._log_with_context(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告日志。"""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录错误日志。"""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录严重错误日志。"""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """记录异常日志。"""
        kwargs['exc_info'] = True
        self.error(message, *args, **kwargs)
    
    def with_context(self, **context) -> 'ContextualLogger':
        """创建带有额外上下文的日志记录器。"""
        new_context = self.context.copy()
        new_context.update(context)
        return ContextualLogger(self.logger, new_context)


# 全局日志管理器实例
_logger_manager = None
_manager_lock = threading.Lock()


def get_logger_manager() -> LoggerManager:
    """获取全局日志管理器实例。"""
    global _logger_manager
    
    if _logger_manager is None:
        with _manager_lock:
            if _logger_manager is None:
                _logger_manager = LoggerManager()
    
    return _logger_manager


def get_logger(name: str, **kwargs) -> ContextualLogger:
    """获取上下文日志记录器。
    
    Args:
        name: 日志记录器名称
        **kwargs: 额外配置参数
    
    Returns:
        上下文日志记录器
    """
    manager = get_logger_manager()
    logger = manager.get_logger(name, **kwargs)
    return ContextualLogger(logger)


def setup_logging(config: Optional[Dict[str, Any]] = None):
    """设置日志系统。
    
    Args:
        config: 日志配置字典
    """
    global _logger_manager
    
    with _manager_lock:
        if _logger_manager is not None:
            _logger_manager.cleanup()
        
        _logger_manager = LoggerManager(config)


def cleanup_logging():
    """清理日志系统。"""
    global _logger_manager
    
    with _manager_lock:
        if _logger_manager is not None:
            _logger_manager.cleanup()
            _logger_manager = None


# 便捷函数
def log_performance(func_name: str, execution_time: float, **extra_data):
    """记录性能日志。"""
    logger = get_logger('water_plant.performance')
    logger.info(
        f"函数 {func_name} 执行完成",
        extra_data={
            'function_name': func_name,
            'execution_time': execution_time,
            'performance_metric': True,
            **extra_data
        }
    )


def log_simulation_step(step: int, state: Dict[str, Any], **extra_data):
    """记录仿真步骤日志。"""
    logger = get_logger('water_plant.simulation')
    logger.debug(
        f"仿真步骤 {step}",
        extra_data={
            'simulation_step': step,
            'system_state': state,
            **extra_data
        }
    )


def log_control_action(controller_type: str, setpoint: float, output: float, **extra_data):
    """记录控制动作日志。"""
    logger = get_logger('water_plant.control')
    logger.info(
        f"{controller_type} 控制器动作",
        extra_data={
            'controller_type': controller_type,
            'setpoint': setpoint,
            'control_output': output,
            **extra_data
        }
    )


def log_error_with_context(error: Exception, context: Dict[str, Any] = None):
    """记录带上下文的错误日志。"""
    logger = get_logger('water_plant')
    logger.exception(
        f"发生错误: {str(error)}",
        extra_data={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'error_occurred': True
        }
    )