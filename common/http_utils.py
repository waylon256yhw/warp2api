#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP请求工具模块
提供统一的HTTP请求处理，包括重试逻辑和错误处理
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Union
import httpx
import requests
from .logging import get_logger

logger = get_logger("http_utils")

class HTTPClient:
    """统一的HTTP客户端，支持重试和错误处理"""
    
    def __init__(
        self,
        base_urls: Optional[List[str]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: tuple = (5.0, 180.0)
    ):
        """
        初始化HTTP客户端
        
        Args:
            base_urls: 基础URL列表，支持多个备用地址
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            timeout: 请求超时设置 (连接超时, 读取超时)
        """
        self.base_urls = base_urls or []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
    
    def post_with_fallback(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """
        发送POST请求，支持多个备用URL
        
        Args:
            endpoint: API端点路径
            json_data: JSON数据
            **kwargs: 其他请求参数
        
        Returns:
            requests.Response: 响应对象
        
        Raises:
            Exception: 所有URL都失败时抛出异常
        """
        last_exc: Optional[Exception] = None
        
        for base_url in self.base_urls:
            url = f"{base_url}{endpoint}"
            try:
                logger.debug(f"发送POST请求到: {url}")
                response = requests.post(
                    url,
                    json=json_data,
                    timeout=self.timeout,
                    **kwargs
                )
                if response.status_code == 200:
                    return response
                else:
                    last_exc = Exception(f"HTTP {response.status_code}: {response.text}")
                    logger.warning(f"请求失败 {url}: {last_exc}")
            except Exception as e:
                last_exc = e
                logger.warning(f"请求异常 {url}: {e}")
                continue
        
        if last_exc:
            raise last_exc
        raise Exception("所有备用URL都不可用")
    
    def post_with_retry(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        handle_429: bool = True,
        refresh_url: Optional[str] = None,
        **kwargs
    ) -> requests.Response:
        """
        发送POST请求，支持重试和429处理
        
        Args:
            url: 请求URL
            json_data: JSON数据
            handle_429: 是否处理429错误（限流）
            refresh_url: JWT刷新URL（用于处理429）
            **kwargs: 其他请求参数
        
        Returns:
            requests.Response: 响应对象
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"尝试 {attempt}/{self.max_retries}: POST {url}")
                response = requests.post(
                    url,
                    json=json_data,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # 处理429限流错误
                if response.status_code == 429 and handle_429 and refresh_url:
                    logger.warning("收到429限流错误，尝试刷新JWT...")
                    try:
                        refresh_resp = requests.post(refresh_url, timeout=10.0)
                        logger.debug(f"JWT刷新响应: HTTP {refresh_resp.status_code}")
                    except Exception as e:
                        logger.warning(f"JWT刷新失败: {e}")
                    
                    # 重试原请求
                    response = requests.post(
                        url,
                        json=json_data,
                        timeout=self.timeout,
                        **kwargs
                    )
                
                if response.status_code == 200:
                    return response
                
                logger.warning(f"请求失败: HTTP {response.status_code}")
                
            except Exception as e:
                logger.warning(f"请求异常 (尝试 {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise
        
        raise Exception(f"请求失败，已重试 {self.max_retries} 次")
    
    async def async_post_with_retry(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        异步发送POST请求，支持重试
        
        Args:
            url: 请求URL
            json_data: JSON数据
            **kwargs: 其他请求参数
        
        Returns:
            httpx.Response: 响应对象
        """
        async with httpx.AsyncClient(timeout=self.timeout[1], trust_env=True) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug(f"异步尝试 {attempt}/{self.max_retries}: POST {url}")
                    response = await client.post(url, json=json_data, **kwargs)
                    
                    if response.status_code == 200:
                        return response
                    
                    logger.warning(f"异步请求失败: HTTP {response.status_code}")
                    
                except Exception as e:
                    logger.warning(f"异步请求异常 (尝试 {attempt}/{self.max_retries}): {e}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        raise
        
        raise Exception(f"异步请求失败，已重试 {self.max_retries} 次")


# 创建默认的HTTP客户端实例
def get_http_client(
    base_urls: Optional[List[str]] = None,
    **kwargs
) -> HTTPClient:
    """
    获取HTTP客户端实例
    
    Args:
        base_urls: 基础URL列表
        **kwargs: 其他HTTPClient参数
    
    Returns:
        HTTPClient: HTTP客户端实例
    """
    return HTTPClient(base_urls=base_urls, **kwargs)