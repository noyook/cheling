# -*- coding: utf-8 -*-
"""
统一 Mongo 访问层：同步/异步客户端惰性单例 + 集合常量 + 索引初始化。

索引参数与旧代码一致：
- vehicle_mileage 唯一 (query_date, plate_num, color_code)（幂等 upsert 前提）
- vehicle_gps_buckets 唯一 (plate_num, color_code, hour)（防同窗口重复文档）
  另保留历史查询索引 (plate_num, hour) 与 (hour)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

from shared.config import get

logger = logging.getLogger("shared.mongo")

MONGO_SELECT_TIMEOUT_MS = 10000

# 集合常量
VEHICLE_MILEAGE = "vehicle_mileage"
VEHICLE_GPS_BUCKETS = "vehicle_gps_buckets"

_sync_client: Optional[pymongo.MongoClient] = None
_async_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> pymongo.MongoClient:
    """同步 MongoClient（惰性单例，连接串来自 MONGO_URI）。"""
    global _sync_client
    if _sync_client is None:
        uri = get("MONGO_URI", "")
        if not uri:
            raise ValueError("MONGO_URI is required (check .env)")
        _sync_client = pymongo.MongoClient(
            uri,
            serverSelectionTimeoutMS=MONGO_SELECT_TIMEOUT_MS,
        )
    return _sync_client


def get_async_mongo_client() -> AsyncIOMotorClient:
    """异步 AsyncIOMotorClient（惰性单例）。"""
    global _async_client
    if _async_client is None:
        uri = get("MONGO_URI", "")
        if not uri:
            raise ValueError("MONGO_URI is required (check .env)")
        _async_client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=MONGO_SELECT_TIMEOUT_MS,
            connectTimeoutMS=MONGO_SELECT_TIMEOUT_MS,
        )
    return _async_client


def ensure_indexes(db: Any) -> None:
    """初始化两集合索引（幂等）。db 可为同步库或异步库（create_index await 与否由调用方决定）。"""
    # vehicle_mileage：唯一 (query_date, plate_num, color_code)
    db[VEHICLE_MILEAGE].create_index(
        [("query_date", 1), ("plate_num", 1), ("color_code", 1)],
        unique=True,
        background=True,
    )
    # vehicle_gps_buckets：唯一 (plate_num, color_code, hour) 防同窗口重复
    db[VEHICLE_GPS_BUCKETS].create_index(
        [("plate_num", 1), ("color_code", 1), ("hour", 1)],
        unique=True,
        background=True,
    )
    # 历史查询索引
    db[VEHICLE_GPS_BUCKETS].create_index(
        [("plate_num", 1), ("hour", -1)], background=True
    )
    db[VEHICLE_GPS_BUCKETS].create_index([("hour", -1)], background=True)
    logger.info("[MongoDB] 索引创建/确认完成")


async def ensure_indexes_async(db: Any) -> None:
    """异步库索引初始化（await create_index）。"""
    await db[VEHICLE_MILEAGE].create_index(
        [("query_date", 1), ("plate_num", 1), ("color_code", 1)],
        unique=True,
        background=True,
    )
    await db[VEHICLE_GPS_BUCKETS].create_index(
        [("plate_num", 1), ("color_code", 1), ("hour", 1)],
        unique=True,
        background=True,
    )
    await db[VEHICLE_GPS_BUCKETS].create_index(
        [("plate_num", 1), ("hour", -1)], background=True
    )
    await db[VEHICLE_GPS_BUCKETS].create_index([("hour", -1)], background=True)
    logger.info("[MongoDB] 索引创建/确认完成（异步）")


__all__ = [
    "MONGO_SELECT_TIMEOUT_MS", "VEHICLE_MILEAGE", "VEHICLE_GPS_BUCKETS",
    "get_mongo_client", "get_async_mongo_client", "ensure_indexes",
    "ensure_indexes_async",
]