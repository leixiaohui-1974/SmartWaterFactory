#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志系统演示脚本。

演示智能水厂系统的完整日志管理功能：
1. 基本日志记录
2. 结构化日志
3. 上下文日志记录
4. 日志轮转
5. 性能日志集成
6. 异常处理日志
7. 多线程日志记录
"""

import sys
import os
import time
import threading
import random
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logging_system import (
    get_logger, setup_logging, cleanup_logging,
    log_performance, log_simulation_step, log_control_action,
    log_error_with_context, LogFormat, StructuredFormatter
)
from utils.performance import PerformanceProfiler


def setup_demo_logging():
    """设置演示用的日志配置。"""
    # 确保日志目录存在
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    config = {
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
            'file_demo': {
                'class': 'utils.logging_system.LogRotationHandler',
                'level': 'DEBUG',
                'formatter': 'json',
                'filename': 'logs/demo.log',
                'max_bytes': 1024*1024,  # 1MB
                'backup_count': 3
            },
            'file_error': {
                'class': 'utils.logging_system.LogRotationHandler',
                'level': 'ERROR',
                'formatter': 'json',
                'filename': 'logs/demo_error.log',
                'max_bytes': 1024*1024,  # 1MB
                'backup_count': 5
            },
            'file_performance': {
                'class': 'utils.logging_system.TimedRotationHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': 'logs/demo_performance.log',
                'when': 'midnight',
                'interval': 1,
                'backup_count': 7
            }
        },
        'loggers': {
            'demo': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_demo'],
                'propagate': False
            },
            'demo.simulation': {
                'level': 'DEBUG',
                'handlers': ['file_demo'],
                'propagate': True
            },
            'demo.control': {
                'level': 'INFO',
                'handlers': ['console', 'file_demo'],
                'propagate': True
            },
            'demo.performance': {
                'level': 'INFO',
                'handlers': ['file_performance'],
                'propagate': True
            },
            'demo.error': {
                'level': 'ERROR',
                'handlers': ['console', 'file_error'],
                'propagate': True
            }
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console']
        }
    }
    
    setup_logging(config)
    print("日志系统配置完成")


def demo_basic_logging():
    """演示基本日志记录功能。"""
    print("\n=== 基本日志记录演示 ===")
    
    logger = get_logger('demo.basic')
    
    # 记录不同级别的日志
    logger.debug('这是调试信息：系统初始化开始')
    logger.info('这是信息日志：系统启动完成')
    logger.warning('这是警告日志：传感器读数异常')
    logger.error('这是错误日志：控制器连接失败')
    
    # 带参数的日志
    temperature = 25.5
    pressure = 1.2
    logger.info('系统状态更新：温度=%.1f°C, 压力=%.1f bar', temperature, pressure)
    
    print("基本日志记录完成")


def demo_structured_logging():
    """演示结构化日志记录。"""
    print("\n=== 结构化日志记录演示 ===")
    
    logger = get_logger('demo.structured')
    
    # 记录结构化数据
    system_state = {
        'temperature': 25.5,
        'pressure': 1.2,
        'flow_rate': 100.0,
        'ph_level': 7.2,
        'turbidity': 0.5
    }
    
    logger.info('系统状态监控', extra_data={
        'event_type': 'system_monitoring',
        'timestamp': datetime.now().isoformat(),
        'state': system_state,
        'status': 'normal',
        'alert_level': 0
    })
    
    # 记录设备状态
    device_status = {
        'pump_01': {'status': 'running', 'speed': 85, 'power': 2.5},
        'valve_02': {'status': 'open', 'position': 75},
        'sensor_03': {'status': 'active', 'last_reading': time.time()}
    }
    
    logger.info('设备状态检查', extra_data={
        'event_type': 'device_monitoring',
        'devices': device_status,
        'check_time': datetime.now().isoformat()
    })
    
    print("结构化日志记录完成")


def demo_contextual_logging():
    """演示上下文日志记录。"""
    print("\n=== 上下文日志记录演示 ===")
    
    # 创建带基础上下文的日志记录器
    base_logger = get_logger('demo.contextual').with_context(
        plant_id='PLANT_001',
        operator='张三',
        shift='早班'
    )
    
    base_logger.info('操作员登录系统')
    
    # 创建带更多上下文的子记录器
    control_logger = base_logger.with_context(
        subsystem='water_treatment',
        controller_type='PID'
    )
    
    control_logger.info('启动水处理控制器', extra_data={
        'setpoint': 50.0,
        'current_value': 45.0,
        'mode': 'automatic'
    })
    
    # 模拟控制过程
    for step in range(5):
        current_value = 45.0 + step * 1.0
        error = 50.0 - current_value
        
        control_logger.debug('控制步骤执行', extra_data={
            'step': step,
            'current_value': current_value,
            'error': error,
            'control_output': 50 + error * 0.5
        })
        
        time.sleep(0.1)
    
    control_logger.info('控制过程完成')
    
    print("上下文日志记录完成")


def demo_performance_logging():
    """演示性能日志记录。"""
    print("\n=== 性能日志记录演示 ===")
    
    profiler = PerformanceProfiler()
    
    @profiler.profile()
    def simulate_heavy_computation():
        """模拟重计算任务。"""
        time.sleep(0.1)
        result = sum(i**2 for i in range(1000))
        return result
    
    @profiler.profile()
    def simulate_data_processing(data_size):
        """模拟数据处理任务。"""
        time.sleep(0.05)
        data = [random.random() for _ in range(data_size)]
        return sum(data) / len(data)
    
    # 执行性能测试
    for i in range(3):
        result1 = simulate_heavy_computation()
        result2 = simulate_data_processing(500)
        
        # 记录性能日志
        log_performance(
            'simulate_heavy_computation',
            profiler.get_function_metrics('simulate_heavy_computation')['last_execution_time'],
            result=result1,
            iteration=i
        )
        
        log_performance(
            'simulate_data_processing',
            profiler.get_function_metrics('simulate_data_processing')['last_execution_time'],
            result=result2,
            data_size=500,
            iteration=i
        )
    
    # 生成性能报告
    report = profiler.generate_report()
    
    logger = get_logger('demo.performance')
    logger.info('性能分析报告', extra_data={
        'report_type': 'performance_summary',
        'total_functions': len(report['function_metrics']),
        'total_system_records': report['summary']['total_system_records'],
        'report_generated_at': datetime.now().isoformat()
    })
    
    print("性能日志记录完成")


def demo_simulation_logging():
    """演示仿真日志记录。"""
    print("\n=== 仿真日志记录演示 ===")
    
    # 模拟仿真过程
    for step in range(10):
        # 模拟系统状态
        state = {
            'temperature': 25.0 + random.uniform(-2, 2),
            'pressure': 1.0 + random.uniform(-0.1, 0.1),
            'flow_rate': 100.0 + random.uniform(-5, 5),
            'ph_level': 7.0 + random.uniform(-0.5, 0.5)
        }
        
        # 记录仿真步骤
        log_simulation_step(
            step=step,
            state=state,
            simulation_time=step * 0.1,
            convergence=random.choice([True, False]),
            iteration_count=random.randint(5, 15)
        )
        
        time.sleep(0.05)
    
    print("仿真日志记录完成")


def demo_control_logging():
    """演示控制日志记录。"""
    print("\n=== 控制日志记录演示 ===")
    
    # 模拟PID控制器
    setpoint = 50.0
    current_value = 45.0
    integral = 0.0
    previous_error = 0.0
    
    kp, ki, kd = 1.0, 0.1, 0.05
    
    for step in range(10):
        error = setpoint - current_value
        integral += error
        derivative = error - previous_error
        
        output = kp * error + ki * integral + kd * derivative
        
        # 记录控制动作
        log_control_action(
            controller_type='PID',
            setpoint=setpoint,
            output=output,
            error=error,
            integral=integral,
            derivative=derivative,
            kp=kp, ki=ki, kd=kd,
            step=step
        )
        
        # 更新系统状态
        current_value += output * 0.1
        previous_error = error
        
        time.sleep(0.05)
    
    print("控制日志记录完成")


def demo_error_logging():
    """演示错误日志记录。"""
    print("\n=== 错误日志记录演示 ===")
    
    logger = get_logger('demo.error')
    
    # 模拟各种错误情况
    error_scenarios = [
        {
            'error_type': 'ValidationError',
            'message': '传感器数据超出有效范围',
            'context': {
                'sensor_id': 'TEMP_001',
                'value': 150.0,
                'valid_range': [0, 100],
                'timestamp': datetime.now().isoformat()
            }
        },
        {
            'error_type': 'ConnectionError',
            'message': '无法连接到数据库',
            'context': {
                'database_host': 'localhost',
                'database_port': 5432,
                'retry_count': 3,
                'last_attempt': datetime.now().isoformat()
            }
        },
        {
            'error_type': 'ControllerError',
            'message': 'PID控制器输出饱和',
            'context': {
                'controller_id': 'PID_001',
                'output_value': 105.0,
                'output_limit': 100.0,
                'setpoint': 50.0,
                'current_value': 30.0
            }
        }
    ]
    
    for scenario in error_scenarios:
        try:
            # 模拟错误
            if scenario['error_type'] == 'ValidationError':
                raise ValueError(scenario['message'])
            elif scenario['error_type'] == 'ConnectionError':
                raise ConnectionError(scenario['message'])
            else:
                raise RuntimeError(scenario['message'])
        
        except Exception as e:
            log_error_with_context(e, scenario['context'])
            
            # 也可以直接使用logger记录
            logger.exception('捕获异常', extra_data={
                'error_scenario': scenario['error_type'],
                'context': scenario['context']
            })
        
        time.sleep(0.1)
    
    print("错误日志记录完成")


def demo_multithreaded_logging():
    """演示多线程日志记录。"""
    print("\n=== 多线程日志记录演示 ===")
    
    def worker_thread(thread_id, task_count):
        """工作线程函数。"""
        logger = get_logger(f'demo.thread_{thread_id}').with_context(
            thread_id=thread_id,
            worker_type='simulation_worker'
        )
        
        logger.info('工作线程启动', extra_data={'task_count': task_count})
        
        for task in range(task_count):
            # 模拟工作
            work_time = random.uniform(0.01, 0.05)
            time.sleep(work_time)
            
            logger.debug('任务完成', extra_data={
                'task_id': task,
                'execution_time': work_time,
                'result': random.randint(1, 100)
            })
        
        logger.info('工作线程完成')
    
    # 创建多个工作线程
    threads = []
    for i in range(5):
        thread = threading.Thread(
            target=worker_thread,
            args=(i, random.randint(5, 10))
        )
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    print("多线程日志记录完成")


def demo_log_analysis():
    """演示日志分析功能。"""
    print("\n=== 日志分析演示 ===")
    
    log_file = Path('logs/demo.log')
    
    if log_file.exists():
        print(f"分析日志文件: {log_file}")
        
        # 读取并分析日志
        log_entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    log_entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        if log_entries:
            # 统计日志级别
            level_counts = {}
            for entry in log_entries:
                level = entry.get('level', 'UNKNOWN')
                level_counts[level] = level_counts.get(level, 0) + 1
            
            print("日志级别统计:")
            for level, count in sorted(level_counts.items()):
                print(f"  {level}: {count}")
            
            # 统计日志记录器
            logger_counts = {}
            for entry in log_entries:
                logger_name = entry.get('logger_name', 'UNKNOWN')
                logger_counts[logger_name] = logger_counts.get(logger_name, 0) + 1
            
            print("\n日志记录器统计:")
            for logger, count in sorted(logger_counts.items()):
                print(f"  {logger}: {count}")
            
            # 查找错误日志
            error_entries = [e for e in log_entries if e.get('level') in ['ERROR', 'CRITICAL']]
            if error_entries:
                print(f"\n发现 {len(error_entries)} 条错误日志")
                for entry in error_entries[:3]:  # 显示前3条
                    print(f"  - {entry.get('message', 'No message')}")
        
        print(f"\n总共分析了 {len(log_entries)} 条日志记录")
    else:
        print("日志文件不存在，跳过分析")


def main():
    """主函数。"""
    print("智能水厂日志系统演示")
    print("=" * 50)
    
    try:
        # 设置日志系统
        setup_demo_logging()
        
        # 运行各种演示
        demo_basic_logging()
        demo_structured_logging()
        demo_contextual_logging()
        demo_performance_logging()
        demo_simulation_logging()
        demo_control_logging()
        demo_error_logging()
        demo_multithreaded_logging()
        
        # 等待一下确保所有日志都写入
        time.sleep(0.5)
        
        # 分析生成的日志
        demo_log_analysis()
        
        print("\n=== 演示完成 ===")
        print("请查看 logs/ 目录下的日志文件：")
        print("- demo.log: 主日志文件（JSON格式）")
        print("- demo_error.log: 错误日志文件")
        print("- demo_performance.log: 性能日志文件")
        
        # 显示日志文件信息
        log_dir = Path('logs')
        if log_dir.exists():
            print("\n生成的日志文件:")
            for log_file in log_dir.glob('demo*.log*'):
                size = log_file.stat().st_size
                print(f"  {log_file.name}: {size} bytes")
    
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理日志系统
        cleanup_logging()
        print("\n日志系统已清理")


if __name__ == '__main__':
    main()