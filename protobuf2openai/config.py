#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理 - 使用统一的common.config模块
"""
import sys
from pathlib import Path

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import config

# 导出配置项，保持向后兼容
BRIDGE_BASE_URL = config.BRIDGE_BASE_URL
FALLBACK_BRIDGE_URLS = config.FALLBACK_BRIDGE_URLS

WARMUP_INIT_RETRIES = config.WARMUP_INIT_RETRIES
WARMUP_INIT_DELAY_S = config.WARMUP_INIT_DELAY_S
WARMUP_REQUEST_RETRIES = config.WARMUP_REQUEST_RETRIES
WARMUP_REQUEST_DELAY_S = config.WARMUP_REQUEST_DELAY_S