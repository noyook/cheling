"""Smart sheet service for WeCom"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from packages.waybill_sync.api.wecom_client import WeComClient
from packages.waybill_sync.core.config import DTJK_DOCID
from packages.waybill_sync.core.constants import BILL_STATE_MAP
from packages.waybill_sync.core.exceptions import WeComError
from packages.waybill_sync.core.response import ApiResponse
from packages.waybill_sync.utils.logger import setup_logger

logger = setup_logger("sheet_service")

COLUMNS = [
    {"field_title": "车牌号码", "field_type": "FIELD_TYPE_TEXT"},
    {"field_title": "驾驶员姓名", "field_type": "FIELD_TYPE_TEXT"},
    {"field_title": "驾驶员电话", "field_type": "FIELD_TYPE_TEXT"},
    {"field_title": "电子运单编号", "field_type": "FIELD_TYPE_TEXT"},
    {"field_title": "运单状态", "field_type": "FIELD_TYPE_SINGLE_SELECT"},
    {"field_title": "运单创建日期", "field_type": "FIELD_TYPE_DATE_TIME"},
    {"field_title": "收货单位名称", "field_type": "FIELD_TYPE_TEXT"},
    {"field_title": "计划装货日期", "field_type": "FIELD_TYPE_DATE_TIME"},
    {"field_title": "计划卸货日期", "field_type": "FIELD_TYPE_DATE_TIME"},
    {"field_title": "货物详细信息", "field_type": "FIELD_TYPE_TEXT"},
]


class SheetService:
    """WeCom smart sheet service."""

    def __init__(self):
        self.wecom = WeComClient()
        self.docid = DTJK_DOCID

    async def ensure_columns(self, sheet_id: str) -> ApiResponse:
        """Ensure all required columns exist, add missing ones.

        Args:
            sheet_id: Target sheet ID

        Returns:
            ApiResponse with count of added columns
        """
        logger.info("检查智能表格列...")
        try:
            fields_result = await self.wecom.smartsheet_get_fields(self.docid, sheet_id)
            fields = fields_result.get("fields", [])
            existing_titles = {f["field_title"] for f in fields}
            logger.info(f"现有列: {list(existing_titles) if existing_titles else '无'}")
        except Exception as e:
            logger.warning(f"获取现有列失败: {e}")
            existing_titles = set()

        missing_cols = [col for col in COLUMNS if col["field_title"] not in existing_titles]
        if missing_cols:
            try:
                await self.wecom.smartsheet_add_fields(self.docid, sheet_id, missing_cols)
                logger.info(f"添加 {len(missing_cols)} 个缺失列")
            except Exception as e:
                raise WeComError(f"添加列失败: {e}")

        return ApiResponse.ok(data={"added": len(missing_cols)})

    async def sync_records(
        self, sheet_id: str, waybill_records: List[Dict[str, Any]]
    ) -> ApiResponse:
        """Sync records: clear existing and write new data.

        Args:
            sheet_id: Target sheet ID
            waybill_records: List of waybill data dicts

        Returns:
            ApiResponse with count of added records
        """
        logger.info("开始同步智能表格...")

        # Clear existing records
        try:
            existing = await self.wecom.smartsheet_get_records(self.docid, sheet_id)
            record_ids = [r["record_id"] for r in existing.get("records", [])]
            if record_ids:
                await self.wecom.smartsheet_delete_records(self.docid, sheet_id, record_ids)
                logger.info(f"清空 {len(record_ids)} 条现有记录")
        except Exception as e:
            logger.warning(f"清空记录失败，将追加写入: {e}")

        # Map and add new records
        to_add = [
            self._map_record(item)
            for item in waybill_records
            if item.get("billNo")
        ]

        if not to_add:
            logger.info("无新记录需要添加")
            return ApiResponse.ok(data={"added": 0})

        batch_size = 500
        total_added = 0
        for i in range(0, len(to_add), batch_size):
            batch = to_add[i:i + batch_size]
            try:
                await self.wecom.smartsheet_add_records(self.docid, sheet_id, batch)
                total_added += len(batch)
                logger.info(f"已写入 {total_added}/{len(to_add)} 条")
            except Exception as e:
                raise WeComError(f"添加记录失败: {e}")
            await asyncio.sleep(0.3)

        logger.info(f"同步完成: 新增 {total_added} 条")
        return ApiResponse.ok(data={"added": total_added})

    @staticmethod
    def _map_record(item: Dict[str, Any]) -> Dict[str, Any]:
        """Map a waybill record to smart sheet format.

        Args:
            item: Raw waybill data

        Returns:
            Dict formatted for WeCom smart sheet
        """
        bill_state = str(item.get("billState", ""))

        def fmt_date(val) -> str | None:
            """Format date value to timestamp string for WeCom."""
            if not val or val == "null" or str(val) == "None":
                return None
            try:
                if isinstance(val, (int, float)):
                    timestamp = int(val * 1000) if val < 10000000000 else int(val)
                else:
                    val_str = str(val)
                    timestamp = None
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
                        try:
                            dt = datetime.strptime(val_str, fmt)
                            timestamp = int(dt.timestamp() * 1000)
                            break
                        except ValueError:
                            continue
                    if timestamp is None:
                        return None
                return str(timestamp)
            except Exception:
                return None

        values = {
            "车牌号码": [{"type": "text", "text": str(item.get("vehCode", ""))}],
            "驾驶员姓名": [{"type": "text", "text": str(item.get("driverName", ""))}],
            "驾驶员电话": [{"type": "text", "text": str(item.get("driverTel", ""))}],
            "电子运单编号": [{"type": "text", "text": str(item.get("billNo", ""))}],
            "运单状态": [{"text": BILL_STATE_MAP.get(bill_state, f"未知({bill_state})")}],
            "收货单位名称": [{"type": "text", "text": str(item.get("consignName", ""))}],
            "货物详细信息": [{"type": "text", "text": str(item.get("goodsInfo", ""))}],
        }

        create_time = fmt_date(item.get("createTime"))
        if create_time:
            values["运单创建日期"] = create_time

        loading = fmt_date(item.get("loadingDate"))
        if loading:
            values["计划装货日期"] = loading

        unloading = fmt_date(item.get("unloadingDate"))
        if unloading:
            values["计划卸货日期"] = unloading

        return {"values": values}
