"""Waybill system authentication client"""
import asyncio
import base64
import json
import logging
import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt

from packages.waybill_sync.core.config import API_BASE, USERNAME, PASSWORD, TOKEN_BUFFER_SECONDS, DATA_DIR
from packages.waybill_sync.core.exceptions import TokenError
from packages.waybill_sync.core.http_client import HttpClient, request
from packages.waybill_sync.utils.logger import setup_logger

logger = setup_logger("auth_client")

# Shared headers (without Blade-Auth, added per-request)
BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
    "Authorization": "Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Referer": f"{API_BASE}/dgsqy/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/147.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "macOS",
}

TOKEN_FILE = os.path.join(DATA_DIR, "waybill-token.json")
TOKEN_BACKUP = os.path.join(DATA_DIR, "waybill-token.json.bak")


def _load_token() -> Optional[Dict[str, Any]]:
    """Load token from file."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载 Token 文件失败: {e}")
        return None


def _save_token(token_info: Dict[str, Any]):
    """Save token to file."""
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_info, f, ensure_ascii=False, indent=2)
    logger.info(f"Token 已保存，过期时间: {token_info.get('expires_time')}")


def _backup_token():
    """Backup current token file."""
    if os.path.exists(TOKEN_FILE):
        shutil.copy2(TOKEN_FILE, TOKEN_BACKUP)
        logger.info("Token 已备份")


def _restore_token() -> bool:
    """Restore token from backup."""
    if os.path.exists(TOKEN_BACKUP):
        shutil.copy2(TOKEN_BACKUP, TOKEN_FILE)
        logger.info("Token 已从备份恢复")
        return True
    return False


def _is_token_valid(token_info: Optional[Dict[str, Any]]) -> bool:
    """Check if token is still valid."""
    if not token_info:
        return False
    expires_timestamp = token_info.get("expires_timestamp", 0)
    if not expires_timestamp:
        return False
    now = int(datetime.now().timestamp())
    return now < expires_timestamp - TOKEN_BUFFER_SECONDS


def _parse_token_exp(access_token: str) -> datetime:
    """Parse token expiration from JWT."""
    try:
        payload = jwt.decode(access_token, options={"verify_signature": False})
        exp = payload.get("exp", 0)
        if exp:
            return datetime.fromtimestamp(exp)
    except Exception as e:
        logger.warning(f"JWT 解析失败: {e}")
    return datetime.now() + timedelta(hours=20)


class AuthClient:
    """Waybill system authentication client."""

    async def get_captcha(self) -> tuple:
        """Get captcha image and key.

        Returns:
            tuple: (img_bytes, captcha_key)

        Raises:
            TokenError: On captcha failure
        """
        url = f"{API_BASE}/inter/blade-auth/oauth/captcha"
        try:
            resp = await request("GET", url, headers=BASE_HEADERS, verify=False)
            data = resp.json()
        except Exception as e:
            raise TokenError(f"获取验证码失败: {e}")

        if "code" in data and data.get("code") != 200:
            raise TokenError(f"获取验证码失败: {data}")

        result = data.get("data", data)
        img_base64 = result.get("image", "")
        captcha_key = result.get("key", "")

        if not img_base64:
            raise TokenError("获取验证码失败，无图片")

        # Strip data URI prefix if present
        if img_base64.startswith("data:image"):
            img_base64 = re.sub(r"^data:image/[^;]+;base64,", "", img_base64)

        try:
            img_bytes = base64.b64decode(img_base64)
        except Exception as e:
            raise TokenError(f"验证码图片解码失败: {e}")

        return img_bytes, captcha_key

    async def login(
        self,
        username: str,
        password: str,
        captcha_code: str,
        captcha_key: str,
    ) -> Dict[str, Any]:
        """Login to get access token.

        Raises:
            TokenError: On login failure
        """
        url = f"{API_BASE}/inter/blade-auth/oauth/token"
        params = {
            "tenantId": "000000",
            "username": username,
            "password": password,
            "grant_type": "captcha",
            "scope": "all",
            "type": "account",
        }
        headers = dict(BASE_HEADERS)
        headers.update({
            "Captcha-Code": captcha_code,
            "Captcha-Key": captcha_key,
            "Content-Length": "0",
            "Dept-Id": "",
            "Origin": API_BASE,
            "Role-Id": "",
            "Tenant-Id": "000000",
            "systemType": "qy-pc",
            "terminal": "pc",
        })

        try:
            resp = await request("POST", url, headers=headers, params=params, verify=False)
            data = resp.json()
        except Exception as e:
            raise TokenError(f"登录请求失败: {e}")

        token_info = data.get("data", data)
        if isinstance(token_info, dict):
            access_token = token_info.get("access_token", "")
        else:
            access_token = ""

        if not access_token:
            if data.get("error") == "unauthorized":
                raise TokenError(f"登录失败: {data.get('error_description', data)}")
            raise TokenError(f"登录失败: {data}")

        logger.info("登录成功，获取到 token")
        return token_info

    async def refresh_token(self) -> bool:
        """Refresh token with retry mechanism.

        Returns:
            bool: True if token was refreshed successfully
        """
        logger.info("开始刷新 Token...")
        max_retries = 3

        for attempt in range(max_retries):
            wait_time = 2 ** attempt
            try:
                img_bytes, captcha_key = await self.get_captcha()
                captcha_code = await self._recognize_captcha(img_bytes)

                if len(captcha_code) != 5 or not captcha_code.isdigit():
                    logger.warning(f"识别结果不是 5 位数字: {captcha_code}")
                    await asyncio.sleep(wait_time)
                    continue

                _backup_token()
                token_info = await self.login(USERNAME, PASSWORD, captcha_code, captcha_key)
                self._save_token_with_exp(token_info)
                logger.info("Token 刷新成功")
                return True

            except Exception as e:
                logger.error(f"Token 刷新尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)

        # Restore from backup if all retries failed
        if _restore_token():
            logger.info("已从备份恢复 Token")
            return True

        return False

    @staticmethod
    async def _recognize_captcha(img_bytes: bytes) -> str:
        """Recognize captcha using ddddocr."""
        try:
            import ddddocr
        except ImportError:
            raise TokenError("需要安装 ddddocr: pip install ddddocr")

        ocr = ddddocr.DdddOcr(show_ad=False)
        result = ocr.classification(img_bytes).strip()
        logger.info(f"验证码识别结果: {result}")
        return result

    @staticmethod
    def _save_token_with_exp(token_info: Dict[str, Any]):
        """Save token with parsed expiration."""
        access_token = token_info.get("access_token", "")
        expires_time = _parse_token_exp(access_token)
        data = {
            "access_token": access_token,
            "expires_time": expires_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_timestamp": int(expires_time.timestamp()),
            "username": USERNAME,
        }
        _save_token(data)


class TokenManager:
    """Token manager with automatic refresh."""

    def __init__(self):
        self._token_info: Optional[Dict[str, Any]] = None
        self._auth_client = AuthClient()

    async def get_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            str: Valid access token

        Raises:
            TokenError: If token cannot be obtained
        """
        if self._token_info is None or not _is_token_valid(self._token_info):
            logger.info("Token 无效或过期，尝试刷新...")
            self._token_info = _load_token()
            if not _is_token_valid(self._token_info):
                if not await self._auth_client.refresh_token():
                    raise TokenError("Token 获取失败")
                self._token_info = _load_token()

        return self._token_info.get("access_token", "")

    async def force_refresh(self) -> str:
        """Force refresh the token."""
        self._token_info = None
        return await self.get_token()
