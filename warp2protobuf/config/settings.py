#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置设置 - 使用统一的common.config模块
"""
import sys
from pathlib import Path

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.config import config

# 导出所有配置项，保持向后兼容
SCRIPT_DIR = config.SCRIPT_DIR
PROTO_DIR = config.PROTO_DIR
LOGS_DIR = config.LOGS_DIR

# API配置
WARP_URL = config.WARP_URL

# 环境变量
HOST = config.HOST
PORT = config.WARP_SERVER_PORT  # 使用正确的端口名称
WARP_JWT = config.WARP_JWT
TIMEOUT = config.TIMEOUT

# 客户端headers配置
CLIENT_VERSION = config.CLIENT_VERSION
OS_CATEGORY = config.OS_CATEGORY
OS_NAME = config.OS_NAME
OS_VERSION = config.OS_VERSION

# Protobuf字段名
TEXT_FIELD_NAMES = config.TEXT_FIELD_NAMES
PATH_HINT_BONUS = config.PATH_HINT_BONUS

# 响应解析配置
SYSTEM_STR = config.SYSTEM_STR

# JWT刷新配置
REFRESH_TOKEN_B64 = config.REFRESH_TOKEN_B64
REFRESH_URL = config.REFRESH_URL
