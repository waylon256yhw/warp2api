#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local logging for protobuf2openai package - 使用统一的common.logging
"""
import sys
from pathlib import Path

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logging import LoggerFactory
from common.config import config

# 使用统一的日志工厂创建logger
logger = LoggerFactory.create_logger(
    name='protobuf2openai',
    log_file='openai_compat.log',
    log_dir=config.LOGS_DIR,
    max_bytes=5*1024*1024,
    backup_count=3
)