#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging system for Warp API server - 使用统一的common.logging
"""
import shutil
from datetime import datetime
from pathlib import Path
import sys
import os

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.logging import LoggerFactory
from common.config import config

def backup_existing_log():
    """备份现有的日志文件"""
    log_file = config.LOGS_DIR / 'warp_api.log'
    
    if log_file.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'warp_api_{timestamp}.log'
        backup_path = config.LOGS_DIR / backup_name
        
        try:
            shutil.move(str(log_file), str(backup_path))
            print(f"Previous log backed up as: {backup_name}")
        except Exception as e:
            print(f"Warning: Could not backup log file: {e}")

# 创建logger实例
def setup_logging():
    """使用统一的日志工厂创建logger"""
    config.ensure_directories()
    backup_existing_log()
    
    return LoggerFactory.create_logger(
        name='warp_api',
        log_file='warp_api.log',
        log_dir=config.LOGS_DIR,
        max_bytes=10*1024*1024,
        backup_count=5
    )

# 初始化logger
logger = setup_logging()

def log(*a):
    """向后兼容的log函数"""
    logger.info(" ".join(str(x) for x in a))

def set_log_file(log_file_name: str) -> None:
    """重新配置logger写入特定的日志文件"""
    global logger
    
    config.ensure_directories()
    
    logger = LoggerFactory.create_logger(
        name='warp_api',
        log_file=log_file_name,
        log_dir=config.LOGS_DIR,
        max_bytes=10*1024*1024,
        backup_count=5
    )
    
    try:
        logger.info(f"Logging redirected to: {config.LOGS_DIR / log_file_name}")
    except Exception:
        pass

# 为了向后兼容，导出LOGS_DIR
LOGS_DIR = config.LOGS_DIR