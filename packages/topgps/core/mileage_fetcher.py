#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPGPS 车辆里程数据采集脚本。

调用 TopDataService.ashx 的 GetVehicleMileage 接口，按日期获取全部车辆里程，
写入 MongoDB TOPGPS 库的 vehicle_mileage 集合。

配置/日期/API 基础能力来自 topgps_common（本脚本固定写 vehicle_mileage 集合，
不读取 .env 的 MONGO_COLLECTION）。

用法：
    python vehicle_mileage_fetcher.py                          # 默认今天
    python vehicle_mileage_fetcher.py --query-date 2026-08-15  # 格式化日期
    python vehicle_mileage_fetcher.py --query-date 20260815    # 紧凑日期
    python vehicle_mileage_fetcher.py --query-date 2026-08-14 --collection vehicle_mileage

批量调用：可循环调用 GetVehicleMileage(query_date) 逐日获取并入库（幂等，可重复执行）。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pymongo
from pymongo import UpdateOne

from packages.topgps.core.common import (
    Config,
    call_api,
    load_config,
    normalize_query_date,
    setup_logging,
)

MAX_RESPONSE_SIZE = 20 * 1024 * 1024  # 20MB
MONGO_SELECT_TIMEOUT_MS = 10000

EXIT_SUCCESS = 0
EXIT_CONFIG = 2
EXIT_DATA = 3

logger = logging.getLogger("vehicle_mileage_fetcher")


# ---------------------------------------------------------------------------
# 核心函数：获取车辆里程数据
# ---------------------------------------------------------------------------

def GetVehicleMileage(query_date: str, cfg: Optional[Config] = None) -> List[Dict[str, Any]]:
    """获取指定日期的全部车辆里程数据。

    参数:
        query_date: 查询日期，支持 '20260815' 或 '2026-08-15' 格式
        cfg: 配置对象；为 None 时自动从 .env / 环境变量加载

    返回:
        API Data 列表，每项含 PlateNum / ColorCode / Date / Mileage 字段

    异常:
        ValueError: 日期格式错误、API 返回 Ret != 0 或响应结构异常
        httpx.HTTPError: 网络/超时异常
    """
    if cfg is None:
        cfg = load_config(argparse.Namespace())
    query_date = normalize_query_date(query_date)

    data = call_api(
        cfg, "GetVehicleMileage",
        max_response_size=MAX_RESPONSE_SIZE,
        QueryDate=query_date, Vehicles=[],
    )
    vehicles = data.get("Data", [])
    if not isinstance(vehicles, list):
        raise ValueError("Data field is not a list")

    logger.info("获取 %d 台车辆里程记录", len(vehicles))
    return vehicles


# ---------------------------------------------------------------------------
# MongoDB 写入
# ---------------------------------------------------------------------------

def _to_mileage_float(value: Any) -> Optional[float]:
    """Mileage 字段转 float，无法解析返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def save_mileage_to_mongo(
    records: List[Dict[str, Any]],
    query_date: str,
    cfg: Config,
) -> Tuple[int, int]:
    """将里程记录写入 MongoDB（幂等 upsert，可重复执行）。

    以 (query_date, plate_num, color_code) 为唯一键：重复执行同一日期的
    获取仅更新已有记录，不产生重复文档。返回 (写入条数, 失败条数)。
    """
    if not records:
        return 0, 0
    if not cfg.mongo_uri:
        raise ValueError("MONGO_URI is required (check .env)")

    client = pymongo.MongoClient(
        cfg.mongo_uri,
        serverSelectionTimeoutMS=MONGO_SELECT_TIMEOUT_MS,
    )
    try:
        collection = client[cfg.mongo_db][cfg.mongo_collection]

        # 幂等唯一索引
        collection.create_index(
            [("query_date", 1), ("plate_num", 1), ("color_code", 1)],
            unique=True,
            background=True,
        )

        now = datetime.now(timezone.utc)
        operations = []
        for rec in records:
            plate = str(rec.get("PlateNum", "")).strip()
            if not plate:
                continue
            mileage = _to_mileage_float(rec.get("Mileage"))
            operations.append(
                UpdateOne(
                    {
                        "query_date": query_date,
                        "plate_num": plate,
                        "color_code": str(rec.get("ColorCode", "")).strip(),
                    },
                    {
                        "$set": {
                            "mileage": mileage,
                            "mileage_raw": rec.get("Mileage"),
                            "date": rec.get("Date"),
                            "updated_at": now,
                        },
                        "$setOnInsert": {"created_at": now},
                    },
                    upsert=True,
                )
            )

        inserted, modified = 0, 0
        for i in range(0, len(operations), 500):
            result = collection.bulk_write(operations[i:i + 500], ordered=False)
            inserted += result.upserted_count
            modified += result.modified_count

        logger.info(
            "MongoDB %s.%s 写入完成：新增 %d，更新 %d",
            cfg.mongo_db, cfg.mongo_collection, inserted, modified,
        )
        return inserted + modified, 0
    finally:
        client.close()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vehicle_mileage_fetcher",
        description="TOPGPS 车辆里程采集：调用 GetVehicleMileage 接口并写入 MongoDB vehicle_mileage 集合。",
    )
    parser.add_argument(
        "--query-date", default=None,
        help="查询日期，支持 20260815 或 2026-08-15 格式；默认今天",
    )
    parser.add_argument(
        "--db", default=None,
        help="数据库名，覆盖 MONGO_DB",
    )
    parser.add_argument(
        "--collection", default=None,
        help="集合名，覆盖 MONGO_COLLECTION",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅获取并打印数据，不写入 MongoDB",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="stderr 日志级别（默认 INFO）",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)

    try:
        cfg = load_config(args, default_collection="vehicle_mileage")
        query_date = normalize_query_date(args.query_date)

        records = GetVehicleMileage(query_date, cfg)

        if args.dry_run:
            print(json.dumps(records, ensure_ascii=False, indent=2))
            return EXIT_SUCCESS

        written, failed = save_mileage_to_mongo(records, query_date, cfg)
        if failed:
            return EXIT_DATA
        return EXIT_SUCCESS
    except (ValueError, pymongo.errors.PyMongoError) as exc:
        logger.error("执行失败: %s", exc)
        return EXIT_CONFIG if "required" in str(exc) else EXIT_DATA


if __name__ == "__main__":
    sys.exit(main())
