"""电子运单 MongoDB 入库服务"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from pymongo import UpdateOne

from packages.waybill_sync.core.constants import BILL_STATE_MAP
from packages.waybill_sync.utils.logger import setup_logger
from shared.config import get as get_config
from shared.mongo import WAYBILL_SYNC, get_mongo_client

logger = setup_logger("mongo_service")

BATCH_SIZE = 500


def build_document(item: Dict[str, Any]) -> Dict[str, Any]:
    """将单条电子运单映射为 MongoDB 文档（保留原始报文到 raw）。"""
    bill_state = str(item.get("billState", ""))
    return {
        "bill_no": str(item.get("billNo", "")).strip(),
        "veh_code": item.get("vehCode", ""),
        "consign_name": item.get("consignName", ""),
        "driver_name": item.get("driverName", ""),
        "driver_tel": item.get("driverTel", ""),
        "goods_info": item.get("goodsInfo", ""),
        "freight": item.get("freight"),
        "bill_state": bill_state,
        "bill_state_text": BILL_STATE_MAP.get(bill_state, f"未知({bill_state})"),
        "depart_time": item.get("departTime"),
        "arrive_time": item.get("arriveTime"),
        "actual_mileage": item.get("actualMileage"),
        "create_time": item.get("createTime"),
        "loading_date": item.get("loadingDate"),
        "unloading_date": item.get("unloadingDate"),
        "raw": item,
    }


def save_waybills(records: List[Dict[str, Any]]) -> Tuple[int, int]:
    """写入电子运单到 MongoDB TOPGPS.waybill_sync（按 bill_no 幂等 upsert）。

    Args:
        records: 运单原始记录列表

    Returns:
        (新增条数, 更新条数)
    """
    docs = [
        build_document(item)
        for item in records
        if str(item.get("billNo", "")).strip()
    ]
    if not docs:
        return 0, 0

    db_name = get_config("MONGO_DB", "TOPGPS")
    collection = get_mongo_client()[db_name][WAYBILL_SYNC]
    collection.create_index([("bill_no", 1)], unique=True, background=True)

    now = datetime.now(timezone.utc)
    operations = []
    for doc in docs:
        bill_no = doc.pop("bill_no")
        operations.append(
            UpdateOne(
                {"bill_no": bill_no},
                {"$set": {**doc, "updated_at": now}, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )

    inserted = modified = 0
    for i in range(0, len(operations), BATCH_SIZE):
        result = collection.bulk_write(operations[i:i + BATCH_SIZE], ordered=False)
        inserted += result.upserted_count
        modified += result.modified_count

    logger.info(
        "MongoDB %s.%s 写入完成：新增 %d，更新 %d",
        db_name, WAYBILL_SYNC, inserted, modified,
    )
    return inserted, modified
