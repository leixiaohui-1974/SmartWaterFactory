#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理演示程序。

本程序演示如何使用水厂控制器的配置管理系统，包括：
1. 多环境配置加载
2. 配置热重载
3. 环境变量覆盖
4. 配置验证和错误处理
"""

import os
import sys
import time
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.environments import (
    ConfigManager, Environment, get_config, reload_config
)
from config.hot_reload import ConfigWatcher, start_config_watching, stop_config_watching


def demo_basic_config_loading():
    """演示基本配置加载功能。"""
    print("=== 基本配置加载演示 ===")
    
    # 获取当前配置
    config = get_config()
    
    print(f"当前环境: {config.environment.value}")
    print(f"调试模式: {config.debug}")
    print(f"数据库配置:")
    print(f"  主机: {config.database.host}")
    print(f"  端口: {config.database.port}")
    print(f"  数据库: {config.database.database}")
    print(f"日志配置:")
    print(f"  级别: {config.logging.level}")
    print(f"  文件: {config.logging.file_path}")
    print(f"仿真配置:")
    print(f"  默认步数: {config.simulation.default_steps}")
    print(f"  最大步数: {config.simulation.max_steps}")
    print()


def demo_environment_switching():
    """演示环境切换功能。"""
    print("=== 环境切换演示 ===")
    
    manager = ConfigManager()
    
    # 测试不同环境
    environments = [Environment.DEVELOPMENT, Environment.TESTING, Environment.PRODUCTION]
    
    for env in environments:
        print(f"\n切换到 {env.value} 环境:")
        
        # 设置环境变量
        os.environ['WATER_PLANT_ENV'] = env.value
        
        # 重新加载配置
        config = manager.reload_config()
        
        print(f"  环境: {config.environment.value}")
        print(f"  调试模式: {config.debug}")
        print(f"  数据库主机: {config.database.host}")
        print(f"  日志级别: {config.logging.level}")
        print(f"  仿真步数: {config.simulation.default_steps}")
    
    print()


def demo_environment_variable_override():
    """演示环境变量覆盖功能。"""
    print("=== 环境变量覆盖演示 ===")
    
    # 保存原始环境变量
    original_env = {}
    env_vars = ['DB_HOST', 'DB_PORT', 'LOG_LEVEL', 'DEBUG']
    for var in env_vars:
        original_env[var] = os.environ.get(var)
    
    try:
        # 设置环境变量覆盖
        os.environ.update({
            'WATER_PLANT_ENV': 'development',
            'DB_HOST': 'override-database.example.com',
            'DB_PORT': '3306',
            'LOG_LEVEL': 'WARNING',
            'DEBUG': 'false'
        })
        
        print("设置环境变量覆盖:")
        print(f"  DB_HOST = {os.environ['DB_HOST']}")
        print(f"  DB_PORT = {os.environ['DB_PORT']}")
        print(f"  LOG_LEVEL = {os.environ['LOG_LEVEL']}")
        print(f"  DEBUG = {os.environ['DEBUG']}")
        
        # 重新加载配置
        config = reload_config()
        
        print("\n覆盖后的配置:")
        print(f"  数据库主机: {config.database.host}")
        print(f"  数据库端口: {config.database.port}")
        print(f"  日志级别: {config.logging.level}")
        print(f"  调试模式: {config.debug}")
        
    finally:
        # 恢复原始环境变量
        for var, value in original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
    
    print()


def demo_config_validation():
    """演示配置验证功能。"""
    print("=== 配置验证演示 ===")
    
    manager = ConfigManager()
    
    # 测试有效配置
    print("加载有效配置:")
    try:
        config = manager.get_config()
        print(f"  ✓ 配置加载成功: {config.environment.value}")
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
    
    # 测试无效环境
    print("\n测试无效环境:")
    original_env = os.environ.get('WATER_PLANT_ENV')
    try:
        os.environ['WATER_PLANT_ENV'] = 'invalid_environment'
        env = manager.get_current_environment()
        print(f"  无效环境回退到: {env.value}")
    finally:
        if original_env:
            os.environ['WATER_PLANT_ENV'] = original_env
        else:
            os.environ.pop('WATER_PLANT_ENV', None)
    
    print()


def demo_hot_reload():
    """演示配置热重载功能。"""
    print("=== 配置热重载演示 ===")
    print("注意: 这个演示需要手动修改配置文件来触发热重载")
    
    # 配置变更回调
    def on_config_changed(new_config):
        print(f"\n🔄 配置已重新加载!")
        print(f"  环境: {new_config.environment.value}")
        print(f"  数据库主机: {new_config.database.host}")
        print(f"  日志级别: {new_config.logging.level}")
        print(f"  时间: {time.strftime('%H:%M:%S')}")
    
    # 启动配置监控
    print("启动配置热重载监控...")
    
    try:
        with ConfigWatcher() as watcher:
            watcher.add_reload_callback(on_config_changed)
            
            print("配置监控已启动，请修改配置文件来测试热重载功能")
            print("提示: 可以修改 config/development.json 文件")
            print("按 Ctrl+C 停止监控\n")
            
            # 显示当前配置
            current_config = watcher.get_config()
            print(f"当前配置:")
            print(f"  环境: {current_config.environment.value}")
            print(f"  数据库主机: {current_config.database.host}")
            print(f"  日志级别: {current_config.logging.level}")
            
            # 等待用户中断
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n停止配置监控...")
                
    except Exception as e:
        print(f"配置热重载演示失败: {e}")
    
    print()


def demo_config_file_operations():
    """演示配置文件操作。"""
    print("=== 配置文件操作演示 ===")
    
    manager = ConfigManager()
    
    # 获取当前配置
    config = manager.get_config()
    
    # 显示配置文件路径
    config_file = manager.config_dir / f"{config.environment.value}.json"
    print(f"当前配置文件: {config_file}")
    print(f"文件存在: {config_file.exists()}")
    
    if config_file.exists():
        print(f"文件大小: {config_file.stat().st_size} 字节")
        
        # 显示配置文件内容（部分）
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            print("\n配置文件内容（部分）:")
            if 'database' in content:
                print(f"  数据库配置: {json.dumps(content['database'], indent=2, ensure_ascii=False)}")
            if 'logging' in content:
                print(f"  日志配置: {json.dumps(content['logging'], indent=2, ensure_ascii=False)}")
                
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 尝试保存配置
    print("\n测试配置保存功能:")
    try:
        # 创建一个测试配置文件
        test_config = config
        test_file = manager.config_dir / "test_save.json"
        
        # 保存配置（注意：敏感信息会被隐藏）
        manager.save_config(test_config, Environment.DEVELOPMENT)
        print(f"  ✓ 配置保存成功")
        
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()
            
    except Exception as e:
        print(f"  ✗ 配置保存失败: {e}")
    
    print()


def main():
    """主函数。"""
    print("水厂控制器配置管理演示程序")
    print("=" * 50)
    
    try:
        # 基本功能演示
        demo_basic_config_loading()
        demo_environment_switching()
        demo_environment_variable_override()
        demo_config_validation()
        demo_config_file_operations()
        
        # 交互式演示
        print("是否要演示配置热重载功能？(y/n): ", end="")
        if input().lower().startswith('y'):
            demo_hot_reload()
        
        print("演示完成！")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()