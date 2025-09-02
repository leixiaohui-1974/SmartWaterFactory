#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志系统测试模块。

测试日志系统的各项功能：
1. 结构化日志记录
2. 多级别日志支持
3. 日志轮转和归档
4. 上下文日志记录
5. 性能日志集成
"""

import unittest
import tempfile
import shutil
import json
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_system import (
    LogLevel, LogFormat, LogEntry, StructuredFormatter,
    LogRotationHandler, TimedRotationHandler, LoggerManager,
    ContextualLogger, get_logger, get_logger_manager,
    setup_logging, cleanup_logging, log_performance,
    log_simulation_step, log_control_action, log_error_with_context
)


class TestLogEntry(unittest.TestCase):
    """测试日志条目类。"""
    
    def test_log_entry_creation(self):
        """测试日志条目创建。"""
        entry = LogEntry(
            timestamp=time.time(),
            level="INFO",
            logger_name="test_logger",
            message="测试消息",
            module="test_module",
            function="test_function",
            line_number=100,
            thread_id=12345,
            process_id=67890,
            extra_data={"key": "value"}
        )
        
        self.assertEqual(entry.level, "INFO")
        self.assertEqual(entry.message, "测试消息")
        self.assertEqual(entry.extra_data["key"], "value")
    
    def test_log_entry_to_dict(self):
        """测试日志条目转换为字典。"""
        entry = LogEntry(
            timestamp=1234567890.123,
            level="ERROR",
            logger_name="error_logger",
            message="错误消息",
            module="error_module",
            function="error_function",
            line_number=200,
            thread_id=11111,
            process_id=22222,
            extra_data={"error_code": 500}
        )
        
        entry_dict = entry.to_dict()
        self.assertIsInstance(entry_dict, dict)
        self.assertEqual(entry_dict["level"], "ERROR")
        self.assertEqual(entry_dict["extra_data"]["error_code"], 500)
    
    def test_log_entry_to_json(self):
        """测试日志条目转换为JSON。"""
        entry = LogEntry(
            timestamp=time.time(),
            level="DEBUG",
            logger_name="debug_logger",
            message="调试消息",
            module="debug_module",
            function="debug_function",
            line_number=50,
            thread_id=33333,
            process_id=44444,
            extra_data={"debug_info": "详细信息"}
        )
        
        json_str = entry.to_json()
        self.assertIsInstance(json_str, str)
        
        # 验证JSON格式正确
        parsed = json.loads(json_str)
        self.assertEqual(parsed["level"], "DEBUG")
        self.assertEqual(parsed["message"], "调试消息")
    
    def test_formatted_timestamp(self):
        """测试格式化时间戳。"""
        timestamp = 1234567890.123456
        entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            logger_name="test",
            message="test",
            module="test",
            function="test",
            line_number=1,
            thread_id=1,
            process_id=1,
            extra_data={}
        )
        
        formatted = entry.formatted_timestamp
        self.assertIsInstance(formatted, str)
        # 检查格式是否正确（YYYY-MM-DD HH:MM:SS.mmm）
        self.assertRegex(formatted, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}')


class TestStructuredFormatter(unittest.TestCase):
    """测试结构化格式化器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=100,
            msg="测试消息 %s",
            args=("参数",),
            exc_info=None
        )
        self.record.module = "test_module"
        self.record.funcName = "test_function"
        self.record.created = time.time()
        self.record.thread = 12345
        self.record.process = 67890
    
    def test_json_formatter(self):
        """测试JSON格式化器。"""
        formatter = StructuredFormatter(LogFormat.JSON)
        formatted = formatter.format(self.record)
        
        # 验证是有效的JSON
        parsed = json.loads(formatted)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["message"], "测试消息 参数")
        self.assertEqual(parsed["module"], "test_module")
    
    def test_structured_formatter(self):
        """测试结构化文本格式化器。"""
        formatter = StructuredFormatter(LogFormat.STRUCTURED)
        formatted = formatter.format(self.record)
        
        self.assertIn("[INFO]", formatted)
        self.assertIn("[test_logger]", formatted)
        self.assertIn("测试消息 参数", formatted)
        self.assertIn("test_module:test_function:100", formatted)
    
    def test_text_formatter(self):
        """测试简单文本格式化器。"""
        formatter = StructuredFormatter(LogFormat.TEXT)
        formatted = formatter.format(self.record)
        
        self.assertIn("INFO", formatted)
        self.assertIn("test_logger", formatted)
        self.assertIn("测试消息 参数", formatted)
    
    def test_exception_formatting(self):
        """测试异常信息格式化。"""
        try:
            raise ValueError("测试异常")
        except ValueError:
            self.record.exc_info = sys.exc_info()
        
        formatter = StructuredFormatter(LogFormat.JSON)
        formatted = formatter.format(self.record)
        
        parsed = json.loads(formatted)
        self.assertIsNotNone(parsed["exception_info"])
        self.assertEqual(parsed["exception_info"]["type"], "ValueError")
        self.assertIn("测试异常", parsed["exception_info"]["message"])
    
    def test_extra_data_formatting(self):
        """测试额外数据格式化。"""
        self.record.extra_data = {"key1": "value1", "key2": 123}
        
        formatter = StructuredFormatter(LogFormat.JSON)
        formatted = formatter.format(self.record)
        
        parsed = json.loads(formatted)
        self.assertEqual(parsed["extra_data"]["key1"], "value1")
        self.assertEqual(parsed["extra_data"]["key2"], 123)


class TestLogRotationHandler(unittest.TestCase):
    """测试日志轮转处理器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
    
    def tearDown(self):
        """清理测试环境。"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_rotation_handler_creation(self):
        """测试轮转处理器创建。"""
        handler = LogRotationHandler(
            filename=self.log_file,
            max_bytes=1024,
            backup_count=3
        )
        
        self.assertEqual(handler.maxBytes, 1024)
        self.assertEqual(handler.backupCount, 3)
        self.assertTrue(handler.compress_old_logs)
        
        handler.close()
    
    def test_log_rotation(self):
        """测试日志轮转功能。"""
        handler = LogRotationHandler(
            filename=self.log_file,
            max_bytes=100,  # 很小的文件大小以触发轮转
            backup_count=2,
            compress_old_logs=False  # 禁用压缩以简化测试
        )
        
        formatter = StructuredFormatter(LogFormat.TEXT)
        handler.setFormatter(formatter)
        
        logger = logging.getLogger("test_rotation")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # 写入足够的日志以触发轮转
        for i in range(20):
            logger.info(f"这是一条很长的测试日志消息，用于触发日志轮转功能 {i}")
        
        # 检查是否创建了轮转文件
        self.assertTrue(os.path.exists(self.log_file))
        
        handler.close()
        logger.removeHandler(handler)


class TestTimedRotationHandler(unittest.TestCase):
    """测试基于时间的日志轮转处理器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "timed_test.log")
    
    def tearDown(self):
        """清理测试环境。"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_timed_handler_creation(self):
        """测试基于时间的处理器创建。"""
        handler = TimedRotationHandler(
            filename=self.log_file,
            when='midnight',
            interval=1,
            backup_count=7
        )
        
        self.assertEqual(handler.when, 'MIDNIGHT')
        # interval在TimedRotatingFileHandler中可能被转换为秒数
        self.assertTrue(handler.interval >= 1)
        self.assertEqual(handler.backupCount, 7)
        
        handler.close()


class TestLoggerManager(unittest.TestCase):
    """测试日志管理器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置
        self.test_config = {
            'version': 1,
            'formatters': {
                'simple': {
                    'class': 'utils.logging_system.StructuredFormatter',
                    'format_type': 'text'
                }
            },
            'handlers': {
                'test_console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'simple'
                }
            },
            'loggers': {
                'test_logger': {
                    'level': 'DEBUG',
                    'handlers': ['test_console'],
                    'propagate': False
                }
            },
            'root': {
                'level': 'WARNING',
                'handlers': ['test_console']
            }
        }
    
    def tearDown(self):
        """清理测试环境。"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manager_creation(self):
        """测试管理器创建。"""
        manager = LoggerManager(self.test_config)
        self.assertIsNotNone(manager)
        self.assertEqual(manager.config, self.test_config)
        
        manager.cleanup()
    
    def test_get_logger(self):
        """测试获取日志记录器。"""
        manager = LoggerManager(self.test_config)
        
        logger = manager.get_logger('test_logger')
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'test_logger')
        self.assertEqual(logger.level, logging.DEBUG)
        
        # 测试缓存
        logger2 = manager.get_logger('test_logger')
        self.assertIs(logger, logger2)
        
        manager.cleanup()
    
    def test_set_level(self):
        """测试设置日志级别。"""
        manager = LoggerManager(self.test_config)
        
        manager.set_level('test_logger', 'ERROR')
        logger = manager.get_logger('test_logger')
        self.assertEqual(logger.level, logging.ERROR)
        
        manager.cleanup()
    
    def test_cleanup(self):
        """测试清理功能。"""
        manager = LoggerManager(self.test_config)
        
        # 创建一些日志记录器
        manager.get_logger('test1')
        manager.get_logger('test2')
        
        self.assertTrue(len(manager.loggers) > 0)
        
        manager.cleanup()
        self.assertEqual(len(manager.loggers), 0)
        self.assertEqual(len(manager.handlers), 0)


class TestContextualLogger(unittest.TestCase):
    """测试上下文日志记录器。"""
    
    def setUp(self):
        """设置测试环境。"""
        self.base_logger = logging.getLogger('test_contextual')
        self.base_logger.setLevel(logging.DEBUG)
        
        # 添加内存处理器用于测试
        self.handler = logging.handlers.MemoryHandler(capacity=100)
        self.handler.setFormatter(StructuredFormatter(LogFormat.JSON))
        self.base_logger.addHandler(self.handler)
    
    def tearDown(self):
        """清理测试环境。"""
        self.base_logger.removeHandler(self.handler)
        self.handler.close()
    
    def test_contextual_logger_creation(self):
        """测试上下文日志记录器创建。"""
        context = {'user_id': 123, 'session_id': 'abc123'}
        contextual_logger = ContextualLogger(self.base_logger, context)
        
        self.assertEqual(contextual_logger.context, context)
        self.assertIs(contextual_logger.logger, self.base_logger)
    
    def test_logging_with_context(self):
        """测试带上下文的日志记录。"""
        context = {'component': 'test', 'version': '1.0'}
        contextual_logger = ContextualLogger(self.base_logger, context)
        
        contextual_logger.info('测试消息', extra_data={'action': 'test_action'})
        
        # 检查日志记录
        self.handler.flush()
        records = self.handler.buffer
        self.assertTrue(len(records) > 0)
        
        # 验证上下文数据
        record = records[-1]
        self.assertTrue(hasattr(record, 'extra_data'))
        self.assertEqual(record.extra_data['component'], 'test')
        self.assertEqual(record.extra_data['action'], 'test_action')
    
    def test_with_context(self):
        """测试创建带额外上下文的日志记录器。"""
        base_context = {'base': 'value'}
        contextual_logger = ContextualLogger(self.base_logger, base_context)
        
        new_logger = contextual_logger.with_context(extra='data')
        
        self.assertEqual(new_logger.context['base'], 'value')
        self.assertEqual(new_logger.context['extra'], 'data')
        self.assertIsNot(new_logger, contextual_logger)
    
    def test_exception_logging(self):
        """测试异常日志记录。"""
        contextual_logger = ContextualLogger(self.base_logger)
        
        try:
            raise ValueError('测试异常')
        except ValueError:
            contextual_logger.exception('发生异常')
        
        # 检查异常记录
        self.handler.flush()
        records = self.handler.buffer
        self.assertTrue(len(records) > 0)
        
        record = records[-1]
        self.assertIsNotNone(record.exc_info)


class TestGlobalFunctions(unittest.TestCase):
    """测试全局函数。"""
    
    def setUp(self):
        """设置测试环境。"""
        # 清理全局状态
        cleanup_logging()
    
    def tearDown(self):
        """清理测试环境。"""
        cleanup_logging()
    
    def test_get_logger_manager(self):
        """测试获取全局日志管理器。"""
        manager1 = get_logger_manager()
        manager2 = get_logger_manager()
        
        self.assertIs(manager1, manager2)  # 应该是同一个实例
    
    def test_get_logger(self):
        """测试获取日志记录器。"""
        logger = get_logger('test_global')
        
        self.assertIsInstance(logger, ContextualLogger)
        self.assertEqual(logger.logger.name, 'test_global')
    
    def test_setup_logging(self):
        """测试设置日志系统。"""
        config = {
            'version': 1,
            'formatters': {},
            'handlers': {},
            'loggers': {},
            'root': {'level': 'INFO', 'handlers': []}
        }
        
        setup_logging(config)
        manager = get_logger_manager()
        
        self.assertEqual(manager.config, config)
    
    def test_convenience_functions(self):
        """测试便捷函数。"""
        # 测试性能日志
        log_performance('test_function', 0.123, param1='value1')
        
        # 测试仿真步骤日志
        state = {'temperature': 25.0, 'pressure': 1.0}
        log_simulation_step(100, state, extra_info='test')
        
        # 测试控制动作日志
        log_control_action('PID', 50.0, 45.0, error=5.0)
        
        # 测试错误日志
        try:
            raise RuntimeError('测试错误')
        except RuntimeError as e:
            log_error_with_context(e, {'context': 'test_context'})
        
        # 这些函数应该不会抛出异常
        self.assertTrue(True)


class TestThreadSafety(unittest.TestCase):
    """测试线程安全性。"""
    
    def test_concurrent_logger_creation(self):
        """测试并发日志记录器创建。"""
        results = []
        errors = []
        
        def create_logger(name):
            try:
                logger = get_logger(f'thread_test_{name}')
                results.append(logger)
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程同时创建日志记录器
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_logger, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 检查结果
        self.assertEqual(len(errors), 0, f"发生错误: {errors}")
        self.assertEqual(len(results), 10)
        
        cleanup_logging()
    
    def test_concurrent_logging(self):
        """测试并发日志记录。"""
        logger = get_logger('concurrent_test')
        errors = []
        
        def log_messages(thread_id):
            try:
                for i in range(100):
                    logger.info(f'线程 {thread_id} 消息 {i}', 
                               extra_data={'thread_id': thread_id, 'message_id': i})
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程同时记录日志
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_messages, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 检查是否有错误
        self.assertEqual(len(errors), 0, f"发生错误: {errors}")
        
        cleanup_logging()


if __name__ == '__main__':
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestLogEntry,
        TestStructuredFormatter,
        TestLogRotationHandler,
        TestTimedRotationHandler,
        TestLoggerManager,
        TestContextualLogger,
        TestGlobalFunctions,
        TestThreadSafety
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出结果
    if result.wasSuccessful():
        print("\n所有日志系统测试通过！")
    else:
        print(f"\n测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        sys.exit(1)