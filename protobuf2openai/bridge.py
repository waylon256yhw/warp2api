#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridge模块 - 使用统一的common.http_utils
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# 添加common模块到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.http_utils import get_http_client
from common.config import config

from .logging import logger
from .packets import packet_template
from .state import STATE, ensure_tool_ids


def bridge_send_stream(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    发送数据包到bridge并返回响应
    
    Args:
        packet: 要发送的数据包
        
    Returns:
        Dict: bridge响应
        
    Raises:
        Exception: 当所有备用URL都失败时
    """
    # 创建HTTP客户端
    client = get_http_client(
        base_urls=config.FALLBACK_BRIDGE_URLS,
        max_retries=1,  # 这里不重试，让post_with_fallback处理多个URL
        timeout=(5.0, 180.0)
    )
    
    # 准备请求数据
    wrapped_packet = {
        "json_data": packet,
        "message_type": "warp.multi_agent.v1.Request"
    }
    
    logger.debug("[OpenAI Compat] Bridge request payload prepared")
    
    # 使用新的HTTP客户端发送请求
    response = client.post_with_fallback(
        endpoint="/api/warp/send_stream",
        json_data=wrapped_packet
    )
    
    logger.debug("[OpenAI Compat] Bridge response received")
    
    return response.json()


def initialize_once() -> None:
    """
    初始化bridge连接和状态
    """
    if STATE.conversation_id:
        return
    
    ensure_tool_ids()
    
    first_task_id = STATE.baseline_task_id or str(uuid.uuid4())
    STATE.baseline_task_id = first_task_id
    
    # 创建HTTP客户端用于健康检查
    client = get_http_client(
        base_urls=config.FALLBACK_BRIDGE_URLS,
        max_retries=config.WARMUP_INIT_RETRIES,
        retry_delay=config.WARMUP_INIT_DELAY_S,
        timeout=(5.0, 5.0)
    )
    
    # 检查bridge服务器健康状态
    health_ok = False
    last_err = None
    
    for base_url in config.FALLBACK_BRIDGE_URLS:
        try:
            import requests
            resp = requests.get(f"{base_url}/healthz", timeout=5.0)
            if resp.status_code == 200:
                health_ok = True
                logger.debug("[OpenAI Compat] Bridge server is ready at %s", base_url)
                break
            else:
                last_err = f"HTTP {resp.status_code} at {base_url}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e} at {base_url}"
    
    if not health_ok:
        raise RuntimeError(f"Bridge server not ready: {last_err}")
    
    # 发送warmup请求
    pkt = packet_template()
    pkt["task_context"]["active_task_id"] = first_task_id
    pkt["input"]["user_inputs"]["inputs"].append({
        "user_query": {"query": "warmup"}
    })
    
    # 使用重试机制发送warmup请求
    last_exc = None
    for attempt in range(1, config.WARMUP_REQUEST_RETRIES + 1):
        try:
            resp = bridge_send_stream(pkt)
            break
        except Exception as e:
            last_exc = e
            logger.warning(f"[OpenAI Compat] Warmup attempt {attempt}/{config.WARMUP_REQUEST_RETRIES} failed: {e}")
            if attempt < config.WARMUP_REQUEST_RETRIES:
                time.sleep(config.WARMUP_REQUEST_DELAY_S)
            else:
                raise
    
    # 更新状态
    STATE.conversation_id = resp.get("conversation_id") or STATE.conversation_id
    ret_task_id = resp.get("task_id")
    if isinstance(ret_task_id, str) and ret_task_id:
        STATE.baseline_task_id = ret_task_id