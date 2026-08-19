# -*- coding: utf-8 -*-
"""
TOPGPS 公共模块（迁移自 TOPGPS/topgps_common.py）。

- load_config：保留 default_collection / read_env_collection 双参数语义
  （内部复用 shared.config 的统一 .env 加载，cwd 优先、逐级向上）
- build_request_data / call_api：POST 表单调用 TOPGPS 接口并校验业务返回
- setup_logging：委托 shared.logging（stderr 统一格式）

注意：Config.mongo_collection 不读取环境变量 MONGO_COLLECTION 作为通用默认
（该变量是 gps_bucket_poller 专用）；各脚本通过 load_config 的
default_collection / read_env_collection 参数控制自己的目标集合。
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Dict, Optional

import httpx

from packages.topgps.config import (
    DEFAULT_API_URL,
    DEFAULT_GPS_COLLECTION,
    DEFAULT_MILEAGE_COLLECTION,
    Config,
    config_from_env,
)
from shared.logging import setup_logging as shared_setup_logging
from shared.utils import (
    iter_date_range,
    normalize_query_date,
    parse_args_date,
)

MONGO_SELECT_TIMEOUT_MS = 10000
DATE_COMPACT = "%Y%m%d"
DATE_ISO = "%Y-%m-%d"

logger = logging.getLogger("packages.topgps.core.common")


def load_config(
    args: argparse.Namespace,
    default_collection: str = DEFAULT_MILEAGE_COLLECTION,
    read_env_collection: bool = False,
) -> Config:
    """加载配置：.env（cwd 优先逐级向上）+ 环境变量 + CLI 覆盖。

    参数:
        default_collection: 目标集合默认值（里程脚本=vehicle_mileage，GPS=vehicle_gps_buckets）
        read_env_collection: 是否读取 MONGO_COLLECTION 环境变量（仅 gps_bucket_poller 使用；
                             里程脚本刻意不读，避免被 .env 的 vehicle_gps_buckets 污染）
    """
    cfg = config_from_env(default_collection, read_env_collection)

    if getattr(args, "interval", None) is not None:
        cfg.interval = args.interval
    if getattr(args, "timeout", None) is not None:
        cfg.timeout = args.timeout
    if getattr(args, "db", None) is not None:
        cfg.mongo_db = args.db
    if getattr(args, "collection", None) is not None:
        cfg.mongo_collection = args.collection
    if getattr(args, "metrics_port", None) is not None:
        cfg.metrics_port = args.metrics_port
    return cfg


def build_request_data(cfg: Config, action: str, **extra: Any) -> Dict[str, str]:
    """构造 TOPGPS 表单请求：request 字段内嵌 JSON，Action 区分接口。"""
    payload: Dict[str, Any] = {
        "Action": action,
        "UserId": cfg.user_id,
        "Pwd": cfg.password,
    }
    payload.update(extra)
    return {"request": json.dumps(payload, ensure_ascii=False)}


def call_api(
    cfg: Config,
    action: str,
    max_response_size: Optional[int] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """POST 调用 TOPGPS 接口并校验业务返回。

    响应约定 {"Ret":0,"Msg":"","Data":[...]}，Ret != 0 视为业务失败抛 ValueError。
    返回完整响应 dict。
    """
    if not cfg.user_id or not cfg.password:
        raise ValueError("GPS_USER_ID and GPS_PASSWORD are required (check .env)")
    logger.info("请求 %s %s", action, json.dumps(extra, ensure_ascii=False))
    with httpx.Client(timeout=cfg.timeout) as client:
        resp = client.post(cfg.api_url, data=build_request_data(cfg, action, **extra))
        resp.raise_for_status()
        if max_response_size is not None and len(resp.content) > max_response_size:
            raise ValueError(
                f"Response exceeded {max_response_size // (1024 * 1024)}MB limit"
            )
        data = resp.json()
    ret = data.get("Ret", -1)
    if ret != 0:
        raise ValueError(f"API Ret={ret} Msg={data.get('Msg', '')}")
    return data


def setup_logging(level: str = "INFO") -> None:
    """初始化 stderr 日志（委托 shared.logging，全项目统一格式）。"""
    shared_setup_logging(level)


__all__ = [
    "MONGO_SELECT_TIMEOUT_MS", "DATE_COMPACT", "DATE_ISO",
    "load_config", "build_request_data", "call_api", "setup_logging",
    "normalize_query_date", "parse_args_date", "iter_date_range",
]