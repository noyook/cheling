"""Main flow orchestrator"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from packages.waybill_sync.api.auth_client import TokenManager
from packages.waybill_sync.core.config import SMARTSHEET_SHEET_ID
from packages.waybill_sync.core.exceptions import WaybillError
from packages.waybill_sync.core.http_client import HttpClient
from packages.waybill_sync.core.response import ApiResponse
from packages.waybill_sync.modules.mongo_service import save_waybills
from packages.waybill_sync.modules.sheet_service import SheetService
from packages.waybill_sync.modules.waybill_service import WaybillService
from packages.waybill_sync.utils.logger import setup_logger
from packages.waybill_sync.utils.notify import Notifier

logger = setup_logger("orchestrator")
notifier = Notifier()
token_manager = TokenManager()


async def sync_waybill_data(days: int = 7) -> ApiResponse:
    """Execute waybill sync to smart sheet (callable by scheduler).

    Args:
        days: Number of days to query back

    Returns:
        ApiResponse with execution result
    """
    shanghai_tz = timezone(timedelta(hours=8))
    now = datetime.now(shanghai_tz)
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    logger.info("=== 运单同步开始 ===")
    logger.info(f"[时间] {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"[日期范围] {start_date} ~ {end_date}")

    try:
        # Step 1: Get waybill data
        logger.info("[Step 1] 获取运单数据...")
        token = await token_manager.get_token()
        waybill_service = WaybillService(token)
        result = await waybill_service.fetch_all(start_date, end_date)
        if not result.success:
            raise WaybillError(f"获取运单失败: {result.error}")

        waybills = result.data["records"]
        total = result.data["total"]
        logger.info(f"Step 1 完成: 获取 {total} 条运单")

        # Step 2: Save to MongoDB
        logger.info("[Step 2] 写入 MongoDB...")
        if not waybills:
            logger.info("无运单数据需要写入")
        else:
            inserted, modified = await asyncio.to_thread(save_waybills, waybills)
            logger.info(f"Step 2 完成: 新增 {inserted} 条，更新 {modified} 条")

        # Step 3: Save to smart sheet
        logger.info("[Step 3] 保存到智能表格...")
        if not waybills:
            logger.info("无运单数据需要保存")
        else:
            sheet_service = SheetService()
            await sheet_service.ensure_columns(SMARTSHEET_SHEET_ID)
            sync_result = await sheet_service.sync_records(SMARTSHEET_SHEET_ID, waybills)
            if sync_result.success:
                added = sync_result.data["added"]
                logger.info(f"Step 3 完成: 新增 {added} 条记录")
            else:
                raise WaybillError(f"保存到智能表格失败: {sync_result.error}")

        logger.info("=== 运单同步结束 ===")
        return ApiResponse.ok(data={"waybills": total})

    except WaybillError:
        raise
    except Exception as e:
        raise WaybillError(f"运单同步异常: {e}")



