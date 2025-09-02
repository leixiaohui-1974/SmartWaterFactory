#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能水厂控制系统备份和恢复工具
支持数据库备份、配置备份、日志归档等功能
"""

import argparse
import gzip
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import schedule
import time


class BackupManager:
    """备份管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.logger = self._setup_logging()
        self.backup_dir = Path(self.config['backup']['directory'])
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "backup": {
                "directory": "./backups",
                "retention_days": 30,
                "compression": True,
                "encryption": False
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "waterplant",
                "user": "postgres",
                "password": "password"
            },
            "paths": {
                "config": "./config",
                "logs": "./logs",
                "data": "./data"
            },
            "schedule": {
                "database_backup": "02:00",
                "config_backup": "03:00",
                "log_archive": "04:00",
                "cleanup": "05:00"
            },
            "notifications": {
                "webhook_url": None,
                "email_smtp": None
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"警告: 无法加载配置文件 {config_file}: {e}")
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('backup_manager')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _compress_file(self, source_path: Path, target_path: Path) -> None:
        """压缩文件"""
        if self.config['backup']['compression']:
            if source_path.is_file():
                with open(source_path, 'rb') as f_in:
                    with gzip.open(f"{target_path}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                target_path = Path(f"{target_path}.gz")
            else:
                with tarfile.open(f"{target_path}.tar.gz", 'w:gz') as tar:
                    tar.add(source_path, arcname=source_path.name)
                target_path = Path(f"{target_path}.tar.gz")
        else:
            if source_path.is_file():
                shutil.copy2(source_path, target_path)
            else:
                shutil.copytree(source_path, target_path)
        
        return target_path
    
    def backup_database(self) -> Optional[Path]:
        """备份数据库"""
        self.logger.info("开始数据库备份...")
        
        try:
            db_config = self.config['database']
            timestamp = self._get_timestamp()
            backup_file = self.backup_dir / f"database_backup_{timestamp}.sql"
            
            # 构建 pg_dump 命令
            cmd = [
                'pg_dump',
                '-h', db_config['host'],
                '-p', str(db_config['port']),
                '-U', db_config['user'],
                '-d', db_config['name'],
                '-f', str(backup_file),
                '--verbose',
                '--no-password'
            ]
            
            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
            
            # 执行备份
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                # 压缩备份文件
                compressed_file = self._compress_file(backup_file, backup_file)
                if compressed_file != backup_file:
                    backup_file.unlink()  # 删除原始文件
                    backup_file = compressed_file
                
                self.logger.info(f"数据库备份完成: {backup_file}")
                self._send_notification("数据库备份成功", f"备份文件: {backup_file}")
                return backup_file
            else:
                self.logger.error(f"数据库备份失败: {result.stderr}")
                self._send_notification("数据库备份失败", result.stderr)
                return None
        
        except Exception as e:
            self.logger.error(f"数据库备份异常: {e}")
            self._send_notification("数据库备份异常", str(e))
            return None
    
    def backup_config(self) -> Optional[Path]:
        """备份配置文件"""
        self.logger.info("开始配置文件备份...")
        
        try:
            config_path = Path(self.config['paths']['config'])
            if not config_path.exists():
                self.logger.warning(f"配置目录不存在: {config_path}")
                return None
            
            timestamp = self._get_timestamp()
            backup_file = self.backup_dir / f"config_backup_{timestamp}"
            
            # 压缩配置目录
            compressed_file = self._compress_file(config_path, backup_file)
            
            self.logger.info(f"配置文件备份完成: {compressed_file}")
            self._send_notification("配置文件备份成功", f"备份文件: {compressed_file}")
            return compressed_file
        
        except Exception as e:
            self.logger.error(f"配置文件备份异常: {e}")
            self._send_notification("配置文件备份异常", str(e))
            return None
    
    def archive_logs(self) -> Optional[Path]:
        """归档日志文件"""
        self.logger.info("开始日志归档...")
        
        try:
            logs_path = Path(self.config['paths']['logs'])
            if not logs_path.exists():
                self.logger.warning(f"日志目录不存在: {logs_path}")
                return None
            
            timestamp = self._get_timestamp()
            archive_file = self.backup_dir / f"logs_archive_{timestamp}"
            
            # 只归档7天前的日志
            cutoff_date = datetime.now() - timedelta(days=7)
            temp_dir = self.backup_dir / f"temp_logs_{timestamp}"
            temp_dir.mkdir(exist_ok=True)
            
            archived_files = []
            for log_file in logs_path.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    shutil.copy2(log_file, temp_dir)
                    archived_files.append(log_file)
            
            if archived_files:
                # 压缩归档
                compressed_file = self._compress_file(temp_dir, archive_file)
                
                # 删除临时目录
                shutil.rmtree(temp_dir)
                
                # 删除已归档的原始日志文件
                for log_file in archived_files:
                    log_file.unlink()
                
                self.logger.info(f"日志归档完成: {compressed_file} (归档了 {len(archived_files)} 个文件)")
                self._send_notification("日志归档成功", f"归档文件: {compressed_file}")
                return compressed_file
            else:
                shutil.rmtree(temp_dir)
                self.logger.info("没有需要归档的日志文件")
                return None
        
        except Exception as e:
            self.logger.error(f"日志归档异常: {e}")
            self._send_notification("日志归档异常", str(e))
            return None
    
    def backup_data(self) -> Optional[Path]:
        """备份数据文件"""
        self.logger.info("开始数据文件备份...")
        
        try:
            data_path = Path(self.config['paths']['data'])
            if not data_path.exists():
                self.logger.warning(f"数据目录不存在: {data_path}")
                return None
            
            timestamp = self._get_timestamp()
            backup_file = self.backup_dir / f"data_backup_{timestamp}"
            
            # 压缩数据目录
            compressed_file = self._compress_file(data_path, backup_file)
            
            self.logger.info(f"数据文件备份完成: {compressed_file}")
            self._send_notification("数据文件备份成功", f"备份文件: {compressed_file}")
            return compressed_file
        
        except Exception as e:
            self.logger.error(f"数据文件备份异常: {e}")
            self._send_notification("数据文件备份异常", str(e))
            return None
    
    def cleanup_old_backups(self) -> None:
        """清理过期备份"""
        self.logger.info("开始清理过期备份...")
        
        try:
            retention_days = self.config['backup']['retention_days']
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            deleted_files = []
            for backup_file in self.backup_dir.glob('*'):
                if backup_file.is_file() and backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    deleted_files.append(backup_file.name)
            
            if deleted_files:
                self.logger.info(f"清理了 {len(deleted_files)} 个过期备份文件")
                self._send_notification("备份清理完成", f"删除了 {len(deleted_files)} 个过期文件")
            else:
                self.logger.info("没有需要清理的过期备份")
        
        except Exception as e:
            self.logger.error(f"备份清理异常: {e}")
            self._send_notification("备份清理异常", str(e))
    
    def restore_database(self, backup_file: Path) -> bool:
        """恢复数据库"""
        self.logger.info(f"开始恢复数据库: {backup_file}")
        
        try:
            if not backup_file.exists():
                self.logger.error(f"备份文件不存在: {backup_file}")
                return False
            
            db_config = self.config['database']
            
            # 如果是压缩文件，先解压
            if backup_file.suffix == '.gz':
                temp_file = backup_file.with_suffix('')
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(temp_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                sql_file = temp_file
            else:
                sql_file = backup_file
            
            # 构建 psql 命令
            cmd = [
                'psql',
                '-h', db_config['host'],
                '-p', str(db_config['port']),
                '-U', db_config['user'],
                '-d', db_config['name'],
                '-f', str(sql_file)
            ]
            
            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
            
            # 执行恢复
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            # 清理临时文件
            if sql_file != backup_file:
                sql_file.unlink()
            
            if result.returncode == 0:
                self.logger.info("数据库恢复完成")
                self._send_notification("数据库恢复成功", f"从备份文件: {backup_file}")
                return True
            else:
                self.logger.error(f"数据库恢复失败: {result.stderr}")
                self._send_notification("数据库恢复失败", result.stderr)
                return False
        
        except Exception as e:
            self.logger.error(f"数据库恢复异常: {e}")
            self._send_notification("数据库恢复异常", str(e))
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True):
            if backup_file.is_file():
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'type': self._get_backup_type(backup_file.name)
                })
        
        return backups
    
    def _get_backup_type(self, filename: str) -> str:
        """获取备份类型"""
        if 'database' in filename:
            return 'database'
        elif 'config' in filename:
            return 'config'
        elif 'logs' in filename:
            return 'logs'
        elif 'data' in filename:
            return 'data'
        else:
            return 'unknown'
    
    def _send_notification(self, title: str, message: str) -> None:
        """发送通知"""
        notifications = self.config['notifications']
        
        # Webhook 通知
        if notifications.get('webhook_url'):
            try:
                import requests
                requests.post(
                    notifications['webhook_url'],
                    json={
                        'title': title,
                        'message': message,
                        'timestamp': datetime.now().isoformat()
                    },
                    timeout=10
                )
            except Exception as e:
                self.logger.error(f"发送 Webhook 通知失败: {e}")
    
    def run_full_backup(self) -> Dict[str, Optional[Path]]:
        """运行完整备份"""
        self.logger.info("开始完整备份...")
        
        results = {
            'database': self.backup_database(),
            'config': self.backup_config(),
            'data': self.backup_data(),
            'logs': self.archive_logs()
        }
        
        # 清理过期备份
        self.cleanup_old_backups()
        
        success_count = sum(1 for result in results.values() if result is not None)
        self.logger.info(f"完整备份完成，成功 {success_count}/{len(results)} 项")
        
        return results
    
    def setup_scheduled_backups(self) -> None:
        """设置定时备份"""
        schedule_config = self.config['schedule']
        
        # 数据库备份
        schedule.every().day.at(schedule_config['database_backup']).do(self.backup_database)
        
        # 配置备份
        schedule.every().day.at(schedule_config['config_backup']).do(self.backup_config)
        
        # 日志归档
        schedule.every().day.at(schedule_config['log_archive']).do(self.archive_logs)
        
        # 清理过期备份
        schedule.every().day.at(schedule_config['cleanup']).do(self.cleanup_old_backups)
        
        self.logger.info("定时备份任务已设置")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            self.logger.info("定时备份已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能水厂控制系统备份工具")
    parser.add_argument(
        "--config", "-c",
        help="配置文件路径",
        default="config/backup.json"
    )
    parser.add_argument(
        "--action", "-a",
        choices=["backup-db", "backup-config", "backup-data", "archive-logs", 
                "full-backup", "restore-db", "list", "cleanup", "schedule"],
        required=True,
        help="执行的操作"
    )
    parser.add_argument(
        "--file", "-f",
        help="恢复时指定的备份文件路径"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["console", "json"],
        default="console",
        help="输出格式"
    )
    
    args = parser.parse_args()
    
    # 创建备份管理器
    backup_manager = BackupManager(args.config)
    
    try:
        if args.action == "backup-db":
            result = backup_manager.backup_database()
            if args.output == "json":
                print(json.dumps({"backup_file": str(result) if result else None}))
        
        elif args.action == "backup-config":
            result = backup_manager.backup_config()
            if args.output == "json":
                print(json.dumps({"backup_file": str(result) if result else None}))
        
        elif args.action == "backup-data":
            result = backup_manager.backup_data()
            if args.output == "json":
                print(json.dumps({"backup_file": str(result) if result else None}))
        
        elif args.action == "archive-logs":
            result = backup_manager.archive_logs()
            if args.output == "json":
                print(json.dumps({"archive_file": str(result) if result else None}))
        
        elif args.action == "full-backup":
            results = backup_manager.run_full_backup()
            if args.output == "json":
                print(json.dumps({
                    key: str(value) if value else None 
                    for key, value in results.items()
                }))
        
        elif args.action == "restore-db":
            if not args.file:
                print("错误: 恢复数据库需要指定备份文件 (--file)", file=sys.stderr)
                sys.exit(1)
            
            backup_file = Path(args.file)
            success = backup_manager.restore_database(backup_file)
            if args.output == "json":
                print(json.dumps({"success": success}))
        
        elif args.action == "list":
            backups = backup_manager.list_backups()
            if args.output == "json":
                print(json.dumps(backups, indent=2))
            else:
                print(f"找到 {len(backups)} 个备份文件:")
                for backup in backups:
                    size_mb = backup['size'] / (1024 * 1024)
                    print(f"  {backup['name']} ({backup['type']}, {size_mb:.1f}MB, {backup['created']})")
        
        elif args.action == "cleanup":
            backup_manager.cleanup_old_backups()
        
        elif args.action == "schedule":
            backup_manager.setup_scheduled_backups()
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()