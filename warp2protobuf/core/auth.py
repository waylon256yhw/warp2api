#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT Authentication for Warp API

Handles JWT token management, refresh, and validation.
Integrates functionality from refresh_jwt.py.
"""
import base64
import json
import os
import time
from pathlib import Path
import httpx
import asyncio
from dotenv import load_dotenv, set_key

from ..config.settings import REFRESH_TOKEN_B64, REFRESH_URL, CLIENT_VERSION, OS_CATEGORY, OS_NAME, OS_VERSION
from .logging import logger, log

# 从环境变量获取URL
_ANON_GQL_URL = os.getenv("WARP_GQL_URL", "https://app.warp.dev/graphql/v2?op=CreateAnonymousUser")
_IDENTITY_TOOLKIT_BASE = os.getenv("IDENTITY_TOOLKIT_URL", "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken")


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload to check expiration"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        return payload
    except Exception as e:
        logger.debug(f"Error decoding JWT: {e}")
        return {}


def is_token_expired(token: str, buffer_minutes: int = 5) -> bool:
    payload = decode_jwt_payload(token)
    if not payload or 'exp' not in payload:
        return True
    expiry_time = payload['exp']
    current_time = time.time()
    buffer_time = buffer_minutes * 60
    return (expiry_time - current_time) <= buffer_time


async def refresh_jwt_token() -> dict:
    """Refresh the JWT token using the refresh token.

    Prefers environment variable WARP_REFRESH_TOKEN when present; otherwise
    falls back to the baked-in REFRESH_TOKEN_B64 payload.
    """
    logger.info("🔄 刷新JWT令牌...")
    # Prefer dynamic refresh token from environment if present
    env_refresh = os.getenv("WARP_REFRESH_TOKEN")
    if env_refresh:
        payload = f"grant_type=refresh_token&refresh_token={env_refresh}".encode("utf-8")
    else:
        payload = base64.b64decode(REFRESH_TOKEN_B64)
    headers = {
        "x-warp-client-version": CLIENT_VERSION,
        "x-warp-os-category": OS_CATEGORY,
        "x-warp-os-name": OS_NAME,
        "x-warp-os-version": OS_VERSION,
        "content-type": "application/x-www-form-urlencoded",
        "accept": "*/*",
        "accept-encoding": "gzip, br",
        "content-length": str(len(payload))
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                REFRESH_URL,
                headers=headers,
                content=payload
            )
            if response.status_code == 200:
                token_data = response.json()
                logger.info("✅ JWT令牌刷新成功")
                return token_data
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return {}
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return {}


def update_env_file(new_jwt: str) -> bool:
    env_path = Path(".env")
    try:
        set_key(str(env_path), "WARP_JWT", new_jwt)
        logger.debug("Updated .env file with new JWT token")
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        return False


def update_env_refresh_token(refresh_token: str) -> bool:
    env_path = Path(".env")
    try:
        set_key(str(env_path), "WARP_REFRESH_TOKEN", refresh_token)
        logger.debug("Updated .env with WARP_REFRESH_TOKEN")
        return True
    except Exception as e:
        logger.error(f"Error updating .env WARP_REFRESH_TOKEN: {e}")
        return False


async def check_and_refresh_token() -> bool:
    current_jwt = os.getenv("WARP_JWT")
    if not current_jwt:
        logger.warning("No JWT token found in environment")
        token_data = await refresh_jwt_token()
        if token_data and "access_token" in token_data:
            return update_env_file(token_data["access_token"])
        return False
    logger.debug("Checking current JWT token expiration...")
    if is_token_expired(current_jwt, buffer_minutes=15):
        logger.info("⚠️ JWT令牌即将过期，正在刷新...")
        token_data = await refresh_jwt_token()
        if token_data and "access_token" in token_data:
            new_jwt = token_data["access_token"]
            if not is_token_expired(new_jwt, buffer_minutes=0):
                logger.debug("New token is valid")
                return update_env_file(new_jwt)
            else:
                logger.warning("New token appears to be invalid or expired")
                return False
        else:
            logger.error("Failed to get new token from refresh")
            return False
    else:
        payload = decode_jwt_payload(current_jwt)
        if payload and 'exp' in payload:
            expiry_time = payload['exp']
            time_left = expiry_time - time.time()
            hours_left = time_left / 3600
            logger.debug(f"Current token is still valid ({hours_left:.1f} hours remaining)")
        else:
            logger.debug("Current token appears valid")
        return True


async def get_valid_jwt() -> str:
    from dotenv import load_dotenv as _load
    _load(override=True)
    jwt = os.getenv("WARP_JWT")
    if not jwt:
        logger.info("⚠️ 未找到JWT令牌，正在获取...")
        if await check_and_refresh_token():
            _load(override=True)
            jwt = os.getenv("WARP_JWT")
        if not jwt:
            raise RuntimeError("WARP_JWT is not set and refresh failed")
    if is_token_expired(jwt, buffer_minutes=2):
        logger.info("⚠️ JWT令牌即将过期，正在刷新...")
        if await check_and_refresh_token():
            _load(override=True)
            jwt = os.getenv("WARP_JWT")
            if not jwt or is_token_expired(jwt, buffer_minutes=0):
                logger.warning("Warning: New token has short expiry but proceeding anyway")
        else:
            logger.warning("Warning: JWT token refresh failed, trying to use existing token")
    return jwt


def get_jwt_token() -> str:
    from dotenv import load_dotenv as _load
    _load()
    return os.getenv("WARP_JWT", "")


async def refresh_jwt_if_needed() -> bool:
    try:
        return await check_and_refresh_token()
    except Exception as e:
        logger.error(f"JWT refresh failed: {e}")
        return False


# ============ Anonymous token acquisition (quota refresh) ============


def _extract_google_api_key_from_refresh_url() -> str:
    try:
        # 优先使用环境变量中的API密钥
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key
            
        # 否则从REFRESH_URL解析
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(REFRESH_URL)
        qs = parse_qs(parsed.query)
        key = qs.get("key", [""])[0]
        return key
    except Exception:
        return os.getenv("GOOGLE_API_KEY", "AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs")


async def _create_anonymous_user() -> dict:
    headers = {
        "accept-encoding": "gzip, br",
        "content-type": "application/json",
        "x-warp-client-version": CLIENT_VERSION,
        "x-warp-os-category": OS_CATEGORY,
        "x-warp-os-name": OS_NAME,
        "x-warp-os-version": OS_VERSION,
    }
    # GraphQL payload per anonymous.MD
    query = (
        "mutation CreateAnonymousUser($input: CreateAnonymousUserInput!, $requestContext: RequestContext!) {\n"
        "  createAnonymousUser(input: $input, requestContext: $requestContext) {\n"
        "    __typename\n"
        "    ... on CreateAnonymousUserOutput {\n"
        "      expiresAt\n"
        "      anonymousUserType\n"
        "      firebaseUid\n"
        "      idToken\n"
        "      isInviteValid\n"
        "      responseContext { serverVersion }\n"
        "    }\n"
        "    ... on UserFacingError {\n"
        "      error { __typename message }\n"
        "      responseContext { serverVersion }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    variables = {
        "input": {
            "anonymousUserType": "NATIVE_CLIENT_ANONYMOUS_USER_FEATURE_GATED",
            "expirationType": "NO_EXPIRATION",
            "referralCode": None
        },
        "requestContext": {
            "clientContext": {"version": CLIENT_VERSION},
            "osContext": {
                "category": OS_CATEGORY,
                "linuxKernelVersion": None,
                "name": OS_NAME,
                "version": OS_VERSION,
            }
        }
    }
    body = {"query": query, "variables": variables, "operationName": "CreateAnonymousUser"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(_ANON_GQL_URL, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError(f"CreateAnonymousUser failed: HTTP {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        return data


async def _exchange_id_token_for_refresh_token(id_token: str) -> dict:
    key = _extract_google_api_key_from_refresh_url()
    url = f"{_IDENTITY_TOOLKIT_BASE}?key={key}" if key else f"{_IDENTITY_TOOLKIT_BASE}?key={os.getenv('GOOGLE_API_KEY', 'AIzaSyBdy3O3S9hrdayLJxJ7mriBR4qgUaUygAs')}"
    headers = {
        "accept-encoding": "gzip, br",
        "content-type": "application/x-www-form-urlencoded",
        "x-warp-client-version": CLIENT_VERSION,
        "x-warp-os-category": OS_CATEGORY,
        "x-warp-os-name": OS_NAME,
        "x-warp-os-version": OS_VERSION,
    }
    form = {
        "returnSecureToken": "true",
        "token": id_token,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(url, headers=headers, data=form)
        if resp.status_code != 200:
            raise RuntimeError(f"signInWithCustomToken failed: HTTP {resp.status_code} {resp.text[:200]}")
        return resp.json()


async def acquire_anonymous_access_token() -> str:
    """Acquire a new anonymous access token (quota refresh) and persist to .env.

    Returns the new access token string. Raises on failure.
    """
    logger.info("🔑 申请匿名访问令牌...")
    data = await _create_anonymous_user()
    id_token = None
    try:
        id_token = data["data"]["createAnonymousUser"].get("idToken")
    except Exception:
        pass
    if not id_token:
        raise RuntimeError(f"CreateAnonymousUser did not return idToken: {data}")

    signin = await _exchange_id_token_for_refresh_token(id_token)
    refresh_token = signin.get("refreshToken")
    if not refresh_token:
        raise RuntimeError(f"signInWithCustomToken did not return refreshToken: {signin}")

    # Persist refresh token for future time-based refreshes
    update_env_refresh_token(refresh_token)

    # Now call Warp proxy token endpoint to get access_token using this refresh token
    payload = f"grant_type=refresh_token&refresh_token={refresh_token}".encode("utf-8")
    headers = {
        "x-warp-client-version": CLIENT_VERSION,
        "x-warp-os-category": OS_CATEGORY,
        "x-warp-os-name": OS_NAME,
        "x-warp-os-version": OS_VERSION,
        "content-type": "application/x-www-form-urlencoded",
        "accept": "*/*",
        "accept-encoding": "gzip, br",
        "content-length": str(len(payload))
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(REFRESH_URL, headers=headers, content=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Acquire access_token failed: HTTP {resp.status_code} {resp.text[:200]}")
        token_data = resp.json()
        access = token_data.get("access_token")
        if not access:
            raise RuntimeError(f"No access_token in response: {token_data}")
        update_env_file(access)
        return access


def print_token_info():
    current_jwt = os.getenv("WARP_JWT")
    if not current_jwt:
        logger.debug("No JWT token found")
        return
    payload = decode_jwt_payload(current_jwt)
    if not payload:
        logger.debug("Cannot decode JWT token")
        return
    logger.debug("=== JWT Token Information ===")
    if 'email' in payload:
        logger.debug(f"Email: {payload['email']}")
    if 'user_id' in payload:
        logger.debug(f"User ID: {payload['user_id']}")
