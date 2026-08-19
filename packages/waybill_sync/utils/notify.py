"""WeCom notification helpers"""
import logging

from packages.waybill_sync.api.wecom_client import WeComClient
from packages.waybill_sync.utils.logger import setup_logger

logger = setup_logger("notify")


class Notifier:
    """WeCom notification sender."""

    def __init__(self):
        self._wecom = WeComClient()

    async def alarm(self, content: str):
        """Send alarm notification."""
        try:
            await self._wecom.send_message(content, title="⚠️ 流程告警")
            logger.info("告警通知发送成功")
        except Exception as e:
            logger.error(f"告警通知发送失败: {e}", exc_info=True)

    async def success(self, content: str):
        """Send success notification."""
        try:
            await self._wecom.send_message(content, title="✅ 流程完成")
            logger.info("成功通知发送成功")
        except Exception as e:
            logger.error(f"成功通知发送失败: {e}", exc_info=True)

    async def info(self, content: str):
        """Send info notification."""
        try:
            await self._wecom.send_message(content, title="ℹ️ 系统通知")
            logger.info("通知发送成功")
        except Exception as e:
            logger.error(f"通知发送失败: {e}", exc_info=True)
