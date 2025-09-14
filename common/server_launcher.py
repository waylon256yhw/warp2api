#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的服务器启动器模块
提供标准化的命令行参数解析和服务器启动功能
"""
import argparse
import asyncio
from typing import Optional, Callable
from pathlib import Path
import uvicorn
from fastapi import FastAPI

from .config import config
from .logging import get_logger

logger = get_logger("server_launcher")


class ServerLauncher:
    """统一的服务器启动器"""
    
    def __init__(
        self,
        app_name: str,
        description: str,
        default_port: int,
        default_host: str = "0.0.0.0"
    ):
        """
        初始化服务器启动器
        
        Args:
            app_name: 应用名称
            description: 应用描述
            default_port: 默认端口
            default_host: 默认主机地址
        """
        self.app_name = app_name
        self.description = description
        self.default_port = default_port
        self.default_host = default_host
        self.parser = None
        
    def parse_args(self) -> argparse.Namespace:
        """
        解析命令行参数
        
        Returns:
            argparse.Namespace: 解析后的参数
        """
        self.parser = argparse.ArgumentParser(description=self.description)
        self.parser.add_argument(
            "--port",
            type=int,
            default=self.default_port,
            help=f"服务器监听端口 (默认: {self.default_port})"
        )
        self.parser.add_argument(
            "--host",
            type=str,
            default=self.default_host,
            help=f"服务器监听地址 (默认: {self.default_host})"
        )
        self.parser.add_argument(
            "--reload",
            action="store_true",
            help="启用自动重载（开发模式）"
        )
        self.parser.add_argument(
            "--log-level",
            type=str,
            default="info",
            choices=["debug", "info", "warning", "error", "critical"],
            help="日志级别 (默认: info)"
        )
        
        return self.parser.parse_args()
    
    def run(
        self,
        app: FastAPI,
        startup_callback: Optional[Callable] = None,
        **uvicorn_kwargs
    ):
        """
        启动服务器
        
        Args:
            app: FastAPI应用实例
            startup_callback: 启动时的回调函数
            **uvicorn_kwargs: 额外的uvicorn配置参数
        """
        args = self.parse_args()
        
        # 如果提供了启动回调，添加到应用事件中
        if startup_callback:
            @app.on_event("startup")
            async def startup_event():
                if asyncio.iscoroutinefunction(startup_callback):
                    await startup_callback()
                else:
                    startup_callback()
        
        # 准备uvicorn配置
        uvicorn_config = {
            "app": app,
            "host": args.host,
            "port": args.port,
            "log_level": args.log_level,
            "reload": args.reload,
            "access_log": True,
            **uvicorn_kwargs  # 允许覆盖或添加额外配置
        }
        
        # 启动服务器
        try:
            logger.info(f"{'='*60}")
            logger.info(f"{self.app_name} 启动")
            logger.info(f"监听地址: {args.host}:{args.port}")
            logger.info(f"日志级别: {args.log_level}")
            if args.reload:
                logger.info("自动重载: 已启用")
            logger.info(f"{'='*60}")
            
            uvicorn.run(**uvicorn_config)
            
        except KeyboardInterrupt:
            logger.info(f"{self.app_name} 被用户停止")
        except Exception as e:
            logger.error(f"{self.app_name} 启动失败: {e}")
            raise
    
    def run_with_jwt_refresh(
        self,
        app: FastAPI,
        startup_callback: Optional[Callable] = None,
        **uvicorn_kwargs
    ):
        """
        启动服务器前先尝试刷新JWT
        
        Args:
            app: FastAPI应用实例
            startup_callback: 启动时的回调函数
            **uvicorn_kwargs: 额外的uvicorn配置参数
        """
        # 尝试刷新JWT
        try:
            from warp2protobuf.core.auth import refresh_jwt_if_needed
            logger.info("检查并刷新JWT token...")
            asyncio.run(refresh_jwt_if_needed())
        except Exception as e:
            logger.warning(f"JWT刷新失败或跳过: {e}")
        
        # 正常启动服务器
        self.run(app, startup_callback, **uvicorn_kwargs)


def create_launcher(
    app_name: str,
    description: str,
    default_port: int,
    default_host: str = "0.0.0.0"
) -> ServerLauncher:
    """
    创建服务器启动器的便捷函数
    
    Args:
        app_name: 应用名称
        description: 应用描述
        default_port: 默认端口
        default_host: 默认主机地址
        
    Returns:
        ServerLauncher: 服务器启动器实例
    """
    return ServerLauncher(app_name, description, default_port, default_host)