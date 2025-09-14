#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Chat Completions compatible server (system-prompt flavored)

Startup entrypoint that exposes the modular app implemented in protobuf2openai.
"""

from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from common.config import config
from protobuf2openai.app import app  # FastAPI app


if __name__ == "__main__":
    import argparse
    import uvicorn

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="OpenAI兼容API服务器")
    parser.add_argument(
        "--port", type=int, default=config.OPENAI_COMPAT_PORT, 
        help=f"服务器监听端口 (默认: {config.OPENAI_COMPAT_PORT})"
    )
    args = parser.parse_args()

    # Refresh JWT on startup before running the server
    try:
        from warp2protobuf.core.auth import refresh_jwt_if_needed as _refresh_jwt

        asyncio.run(_refresh_jwt())
    except Exception:
        pass
    uvicorn.run(
        app,
        host=config.HOST,
        port=args.port,
        log_level="info",
    )
