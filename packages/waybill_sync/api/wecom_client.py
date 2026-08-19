"""WeCom (企业微信) API client"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from packages.waybill_sync.core.config import WECOM_CORP_ID, WECOM_CORP_SECRET, WECOM_AGENT_ID, DATA_DIR
from packages.waybill_sync.core.exceptions import WeComError
from packages.waybill_sync.core.http_client import HttpClient, request
from packages.waybill_sync.utils.logger import setup_logger

logger = setup_logger("wecom_client")

TOKEN_FILE = os.path.join(DATA_DIR, "wecom-token.json")
BUFFER_SECONDS = 300


def _load_wecom_token() -> Optional[Dict[str, Any]]:
    """Load WeCom token from file."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取 WeCom Token 文件失败: {e}")
        return None


def _is_wecom_token_valid(token_info: Optional[Dict[str, Any]]) -> bool:
    """Check if WeCom token is valid."""
    if not token_info:
        return False
    expires_timestamp = token_info.get("expires_timestamp", 0)
    if not expires_timestamp:
        return False
    now = int(datetime.now().timestamp())
    return now < expires_timestamp - BUFFER_SECONDS


def _save_wecom_token(token_info: Dict[str, Any]):
    """Save WeCom token to file."""
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_info, f, ensure_ascii=False, indent=2)
    logger.info(f"WeCom Token 已保存，过期时间: {token_info.get('expires_time')}")


class WeComClient:
    """WeCom API client for messages and smartsheet operations."""

    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self):
        self._token_info: Optional[Dict[str, Any]] = None

    async def get_access_token(self) -> str:
        """Get a valid WeCom access token.

        Returns:
            str: Valid access token

        Raises:
            WeComError: On token acquisition failure
        """
        if self._token_info is None or not _is_wecom_token_valid(self._token_info):
            self._token_info = _load_wecom_token()
            if not _is_wecom_token_valid(self._token_info):
                await self._fetch_token()
        return self._token_info.get("access_token", "")

    async def _fetch_token(self):
        """Fetch new access token from WeCom API."""
        url = f"{self.BASE_URL}/gettoken"
        params = {
            "corpid": WECOM_CORP_ID,
            "corpsecret": WECOM_CORP_SECRET,
        }
        try:
            resp = await request("GET", url, params=params)
            result = resp.json()
        except Exception as e:
            raise WeComError(f"获取 WeCom Token 失败: {e}")

        if result.get("errcode") != 0:
            raise WeComError(f"获取 WeCom Token 失败: {result.get('errmsg')}")

        access_token = result.get("access_token", "")
        expires_in = result.get("expires_in", 7200)
        expires_time = datetime.now() + timedelta(seconds=expires_in)

        self._token_info = {
            "access_token": access_token,
            "expires_time": expires_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_timestamp": int(expires_time.timestamp()),
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_wecom_token(self._token_info)
        logger.info("WeCom Token 获取成功")

    async def send_message(
        self,
        content: str,
        title: str = "系统通知",
        touser: str = "@all",
        msgtype: str = "textcard",
    ) -> Dict[str, Any]:
        """Send a WeCom message.

        Args:
            content: Message content
            title: Message title (for textcard)
            touser: Recipients
            msgtype: Message type (text or textcard)

        Raises:
            WeComError: On send failure
        """
        access_token = await self.get_access_token()
        url = f"{self.BASE_URL}/message/send"
        params = {"access_token": access_token}

        if msgtype == "textcard":
            msg_data = {
                "touser": touser,
                "msgtype": "textcard",
                "agentid": WECOM_AGENT_ID,
                "textcard": {
                    "title": title,
                    "description": content,
                    "url": "https://work.weixin.qq.com/",
                    "btntxt": "查看详情",
                },
            }
        else:
            msg_data = {
                "touser": touser,
                "msgtype": "text",
                "agentid": WECOM_AGENT_ID,
                "text": {"content": content},
            }

        try:
            resp = await request("POST", url, params=params, json_body=msg_data)
            result = resp.json()
        except Exception as e:
            raise WeComError(f"发送消息失败: {e}")

        if result.get("errcode") != 0:
            raise WeComError(f"发送消息失败: {result.get('errmsg')}")

        logger.info(f"消息发送成功: msgid={result.get('msgid')}")
        return result

    async def smartsheet_get_fields(
        self, docid: str, sheet_id: str
    ) -> Dict[str, Any]:
        """Get smartsheet fields.

        Raises:
            WeComError: On API failure
        """
        access_token = await self.get_access_token()
        url = f"{self.BASE_URL}/wedoc/smartsheet/get_fields"
        params = {"access_token": access_token}
        body = {"docid": docid, "sheet_id": sheet_id}

        try:
            resp = await request("POST", url, params=params, json_body=body)
            return resp.json()
        except Exception as e:
            raise WeComError(f"获取智能表格字段失败: {e}")

    async def smartsheet_add_fields(
        self, docid: str, sheet_id: str, fields: list
    ) -> Dict[str, Any]:
        """Add smartsheet fields.

        Raises:
            WeComError: On API failure
        """
        access_token = await self.get_access_token()
        url = f"{self.BASE_URL}/wedoc/smartsheet/add_fields"
        params = {"access_token": access_token}
        body = {"docid": docid, "sheet_id": sheet_id, "fields": fields}

        try:
            resp = await request("POST", url, params=params, json_body=body)
            return resp.json()
        except Exception as e:
            raise WeComError(f"添加智能表格字段失败: {e}")

    async def smartsheet_get_records(
        self, docid: str, sheet_id: str
    ) -> Dict[str, Any]:
        """Get smartsheet records.

        Raises:
            WeComError: On API failure
        """
        access_token = await self.get_access_token()
        url = f"{self.BASE_URL}/wedoc/smartsheet/get_records"
        params = {"access_token": access_token}
        body = {"docid": docid, "sheet_id": sheet_id}

        try:
            resp = await request("POST", url, params=params, json_body=body)
            return resp.json()
        except Exception as e:
            raise WeComError(f"获取智能表格记录失败: {e}")

    async def smartsheet_add_records(
        self, docid: str, sheet_id: str, records: list
    ) -> Dict[str, Any]:
        """Add smartsheet records.

        Raises:
            WeComError: On API failure
        """
        access_token = await self.get_access_token()
        url = f"{self.BASE_URL}/wedoc/smartsheet/add_records"
        params = {"access_token": access_token}
        body = {"docid": docid, "sheet_id": sheet_id, "records": records}

        try:
            resp = await request("POST", url, params=params, json_body=body)
            return resp.json()
        except Exception as e:
            raise WeComError(f"添加智能表格记录失败: {e}")

    async def smartsheet_delete_records(
        self, docid: str, sheet_id: str, record_ids: list
    ) -> Dict[str, Any]:
        """Delete smartsheet records.

        Raises:
            WeComError: On API failure
        """
        access_token = await self.get_access_token()
        url = f"{self.BASE_URL}/wedoc/smartsheet/delete_records"
        params = {"access_token": access_token}
        body = {"docid": docid, "sheet_id": sheet_id, "record_ids": record_ids}

        try:
            resp = await request("POST", url, params=params, json_body=body)
            return resp.json()
        except Exception as e:
            raise WeComError(f"删除智能表格记录失败: {e}")
