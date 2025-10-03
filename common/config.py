#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的配置管理模块
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 加载环境变量（只加载一次）
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

class Config:
    """统一的配置类"""
    
    # 路径配置
    SCRIPT_DIR = PROJECT_ROOT
    PROTO_DIR = PROJECT_ROOT / "proto"
    LOGS_DIR = PROJECT_ROOT / "logs"
    STATIC_DIR = PROJECT_ROOT / "static"
    
    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    WARP_SERVER_PORT = int(os.getenv("WARP_SERVER_PORT", "28888"))
    OPENAI_COMPAT_PORT = int(os.getenv("OPENAI_COMPAT_PORT", "28889"))
    TIMEOUT = int(os.getenv("TIMEOUT", "60"))
    
    # Warp API配置
    WARP_URL = os.getenv("WARP_API_URL", "https://app.warp.dev/ai/multi-agent")
    WARP_JWT = os.getenv("WARP_JWT")
    
    # Bridge配置
    BRIDGE_BASE_URL = os.getenv("WARP_BRIDGE_URL", f"http://127.0.0.1:{WARP_SERVER_PORT}")
    FALLBACK_BRIDGE_URLS = [
        BRIDGE_BASE_URL,
        f"http://127.0.0.1:{WARP_SERVER_PORT}",
    ]
    
    # 客户端配置
    CLIENT_VERSION = os.getenv("CLIENT_VERSION", "v0.2025.08.06.08.12.stable_02")
    OS_CATEGORY = os.getenv("OS_CATEGORY", "Windows")
    OS_NAME = os.getenv("OS_NAME", "Windows")
    OS_VERSION = os.getenv("OS_VERSION", "11 (26100)")
    
    # Warmup配置
    WARMUP_INIT_RETRIES = int(os.getenv("WARP_COMPAT_INIT_RETRIES", "10"))
    WARMUP_INIT_DELAY_S = float(os.getenv("WARP_COMPAT_INIT_DELAY", "0.5"))
    WARMUP_REQUEST_RETRIES = int(os.getenv("WARP_COMPAT_WARMUP_RETRIES", "3"))
    WARMUP_REQUEST_DELAY_S = float(os.getenv("WARP_COMPAT_WARMUP_DELAY", "1.5"))
    
    # JWT刷新配置
    REFRESH_TOKEN_B64 = os.getenv("BACKUP_REFRESH_TOKEN_B64", "Z3JhbnRfdHlwZT1yZWZyZXNoX3Rva2VuJnJlZnJlc2hfdG9rZW49QU1mLXZCeFNSbWRodmVHR0JZTTY5cDA1a0RoSW4xaTd3c2NBTEVtQzlmWURScEh6akVSOWRMN2trLWtIUFl3dlk5Uk9rbXk1MHFHVGNJaUpaNEFtODZoUFhrcFZQTDkwSEptQWY1Zlo3UGVqeXBkYmNLNHdzbzhLZjNheGlTV3RJUk9oT2NuOU56R2FTdmw3V3FSTU5PcEhHZ0JyWW40SThrclc1N1I4X3dzOHU3WGNTdzh1MERpTDlIcnBNbTBMdHdzQ2g4MWtfNmJiMkNXT0ViMWxJeDNIV1NCVGVQRldzUQ==")
    REFRESH_URL = os.getenv("WARP_REFRESH_URL", "https://app.warp.dev/proxy/token?key=AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs")
    
    # Protobuf字段名配置
    TEXT_FIELD_NAMES = ("text", "prompt", "query", "content", "message", "input")
    PATH_HINT_BONUS = ("conversation", "query", "input", "user", "request", "delta")
    
    # 响应解析配置
    SYSTEM_STR = {"agent_output.text", "server_message_data", "USER_INITIATED", "agent_output", "text"}
    
    @classmethod
    def ensure_directories(cls):
        """确保所有必要的目录存在"""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        if cls.STATIC_DIR.exists():
            return True
        return False

# 创建全局配置实例
config = Config()
