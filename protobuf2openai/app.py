from __future__ import annotations

import asyncio
import json

import httpx
from fastapi import FastAPI

from .logging import logger

from .config import BRIDGE_BASE_URL, WARMUP_INIT_RETRIES, WARMUP_INIT_DELAY_S
from .bridge import initialize_once
from .router import router


app = FastAPI(title="OpenAI Chat Completions (Warp bridge) - Streaming")
app.include_router(router)


@app.on_event("startup")
async def _on_startup():
    try:
        logger.info("[OpenAI Compat] Server starting. BRIDGE_BASE_URL=%s", BRIDGE_BASE_URL)
        logger.info("[OpenAI Compat] Endpoints: GET /healthz, GET /v1/models, POST /v1/chat/completions")
    except Exception:
        pass

    url = f"{BRIDGE_BASE_URL}/healthz"
    retries = WARMUP_INIT_RETRIES
    delay_s = WARMUP_INIT_DELAY_S
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=5.0, trust_env=True) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                logger.info("[OpenAI Compat] Bridge server is ready at %s", url)
                break
            else:
                logger.warning("[OpenAI Compat] Bridge health at %s -> HTTP %s", url, resp.status_code)
        except Exception as e:
            logger.warning("[OpenAI Compat] Bridge health attempt %s/%s failed: %s", attempt, retries, e)
        await asyncio.sleep(delay_s)
    else:
        logger.error("[OpenAI Compat] Bridge server not ready at %s", url)

    try:
        await asyncio.to_thread(initialize_once)
    except Exception as e:
        logger.warning(f"[OpenAI Compat] Warmup initialize_once on startup failed: {e}") 