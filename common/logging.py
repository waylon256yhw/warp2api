#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的日志系统配置
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

class LoggerFactory:
    """日志工厂类，用于创建统一配置的logger"""
    
    DEFAULT_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    @classmethod
    def create_logger(
        cls,
        name: str,
        log_file: str,
        log_dir: Path = Path("logs"),
        max_bytes: int = 10*1024*1024,
        backup_count: int = 5,
        console_level: int = logging.WARNING,  # 提高控制台输出级别，减少日志
        file_level: int = logging.INFO  # 文件仍然记录INFO级别
    ) -> logging.Logger:
        """
        创建一个配置好的logger实例
        
        Args:
            name: Logger名称
            log_file: 日志文件名
            log_dir: 日志目录
            max_bytes: 单个日志文件最大大小
            backup_count: 日志文件备份数量
            console_level: 控制台输出级别
            file_level: 文件输出级别
        """
        # 确保日志目录存在
        log_dir.mkdir(exist_ok=True)
        
        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(min(console_level, file_level))
        
        # 清除已有的handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 文件处理器
        file_handler = RotatingFileHandler(
            log_dir / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        
        # 设置格式
        formatter = logging.Formatter(cls.DEFAULT_FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

# 创建默认的logger实例
def get_logger(name: str = "default") -> logging.Logger:
    """获取logger实例，使用统一的配置"""
    return LoggerFactory.create_logger(
        name=name,
        log_file=f"{name}.log"
    )