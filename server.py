#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Warp Protobuf编解码服务器启动文件

纯protobuf编解码服务器，提供JSON<->Protobuf转换、WebSocket监控和静态文件服务。
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import Query, HTTPException
from fastapi.responses import Response

# 使用统一的共享模块
from common.config import config
from common.schema_utils import sanitize_json_schema
from common.message_codec import decode_server_message_data, encode_server_message_data

from warp2protobuf.api.protobuf_routes import app as protobuf_app
from warp2protobuf.core.logging import logger, set_log_file
from warp2protobuf.api.protobuf_routes import EncodeRequest, _encode_smd_inplace
from warp2protobuf.core.protobuf_utils import dict_to_protobuf_bytes
from warp2protobuf.core.schema_sanitizer import sanitize_mcp_input_schema_in_packet
from warp2protobuf.core.auth import acquire_anonymous_access_token
from warp2protobuf.config.models import get_all_unique_models


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    # 将服务器日志重定向到专用文件
    try:
        set_log_file('warp_server.log')
    except Exception:
        pass
    
    # 使用protobuf路由的应用作为主应用
    app = protobuf_app

    # ============= 新增接口：返回protobuf编码后的AI请求字节 =============
    @app.post("/api/warp/encode_raw")
    async def encode_ai_request_raw(
        request: EncodeRequest,
        output: str = Query("raw", description="输出格式：raw(默认，返回application/x-protobuf字节) 或 base64", pattern=r"^(raw|base64)$"),
    ):
        try:
            # 获取实际数据并验证
            actual_data = request.get_data()
            if not actual_data:
                raise HTTPException(400, "数据包不能为空")

            # 在 encode 之前，对 mcp_context.tools[*].input_schema 做一次安全清理
            if isinstance(actual_data, dict):
                wrapped = {"json_data": actual_data}
                wrapped = sanitize_mcp_input_schema_in_packet(wrapped)
                actual_data = wrapped.get("json_data", actual_data)

            # 将 server_message_data 对象（如有）编码为 Base64URL 字符串
            actual_data = _encode_smd_inplace(actual_data)

            # 编码为protobuf字节
            protobuf_bytes = dict_to_protobuf_bytes(actual_data, request.message_type)
            logger.debug(f"✅ AI请求编码为protobuf成功: {len(protobuf_bytes)} 字节")

            if output == "raw":
                # 直接返回二进制 protobuf 内容
                return Response(
                    content=protobuf_bytes,
                    media_type="application/x-protobuf",
                    headers={"Content-Length": str(len(protobuf_bytes))},
                )
            else:
                # 返回base64文本，便于在JSON中传输/调试
                import base64
                return {
                    "protobuf_base64": base64.b64encode(protobuf_bytes).decode("utf-8"),
                    "size": len(protobuf_bytes),
                    "message_type": request.message_type,
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ AI请求编码失败: {e}")
            raise HTTPException(500, f"编码失败: {str(e)}")
    
    # ============= OpenAI 兼容：模型列表接口 =============
    @app.get("/v1/models")
    async def list_models():
        """OpenAI-compatible endpoint that lists available models."""
        try:
            models = get_all_unique_models()
            return {"object": "list", "data": models}
        except Exception as e:
            logger.error(f"❌ 获取模型列表失败: {e}")
            raise HTTPException(500, f"获取模型列表失败: {str(e)}")
    
    return app


async def startup_tasks():
    """启动时执行的任务"""
    logger.info("="*60)
    logger.info("Warp Protobuf编解码服务器启动")
    logger.info("="*60)
    
    # 检查端口冲突
    if config.WARP_SERVER_PORT == config.OPENAI_COMPAT_PORT:
        logger.warning("⚠️ 警告：Warp服务器端口和OpenAI兼容层端口相同，可能导致冲突！")
        logger.warning(f"当前配置：WARP_SERVER_PORT={config.WARP_SERVER_PORT}, OPENAI_COMPAT_PORT={config.OPENAI_COMPAT_PORT}")
        logger.warning("请在.env文件中设置不同的端口，或使用--port参数指定不同的端口")
    
    # 检查protobuf运行时
    try:
        from warp2protobuf.core.protobuf import ensure_proto_runtime
        ensure_proto_runtime()
        logger.info("✅ Protobuf运行时初始化成功")
    except Exception as e:
        logger.error(f"❌ Protobuf运行时初始化失败: {e}")
        raise
    
    # 检查JWT token
    try:
        from warp2protobuf.core.auth import get_jwt_token, is_token_expired
        token = get_jwt_token()
        if token and not is_token_expired(token):
            logger.info("✅ JWT token有效")
        elif not token:
            logger.warning("⚠️ 未找到JWT token，尝试申请匿名访问token用于额度初始化…")
            try:
                new_token = await acquire_anonymous_access_token()
                if new_token:
                    logger.info("✅ 匿名访问token申请成功")
                else:
                    logger.warning("⚠️ 匿名访问token申请失败")
            except Exception as e2:
                logger.warning(f"⚠️ 匿名访问token申请异常: {e2}")
        else:
            logger.warning("⚠️ JWT token无效或已过期，建议运行: uv run refresh_jwt.py")
    except Exception as e:
        logger.warning(f"⚠️ JWT检查失败: {e}")
    
    # 显示可用端点（简化版）
    logger.info("📍 API端点: http://localhost:%s", config.WARP_SERVER_PORT)


def main():
    """主函数"""
    import argparse
    from contextlib import asynccontextmanager
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Warp Protobuf编解码服务器")
    parser.add_argument("--port", type=int, default=config.WARP_SERVER_PORT,
                        help=f"服务器监听端口 (默认: {config.WARP_SERVER_PORT})")
    args = parser.parse_args()
    
    # 使用lifespan上下文管理器替代on_event
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 启动时执行
        await startup_tasks()
        yield
        # 关闭时执行（如果需要的话）
    
    # 创建应用
    app = create_app()
    app.router.lifespan_context = lifespan
    
    # 启动服务器
    try:
        logger.info(f"🌐 服务器监听端口: {args.port}")
        uvicorn.run(
            app,
            host=config.HOST,
            port=args.port,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("服务器被用户停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    main()
