# -*- coding: utf-8 -*-
"""
统一配置层：.env 加载（零依赖解析）+ 环境变量合并 + 合并版 Config。

合并自 TOPGPS/topgps_common.py 的 load_env_file / load_config 语义
与 waybill-sync/src/core/config.py 的 get() 语义：
- .env 查找：cwd 优先，随后逐级向上（含模块所在目录链）
- 取值优先级：已存在的环境变量 > .env > 默认值
- get() 带类型转换，转换失败回退默认值（与 waybill 原实现一致）
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "http://61.183.9.49:8088/topgps/services/TopDataService.ashx"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MONGO_DB = "TOPGPS"
DEFAULT_MILEAGE_COLLECTION = "vehicle_mileage"
DEFAULT_GPS_COLLECTION = "vehicle_gps_buckets"
DATE_COMPACT = "%Y%m%d"
DATE_ISO = "%Y-%m-%d"


# ---------------------------------------------------------------------------
# .env 加载（零依赖）
# ---------------------------------------------------------------------------

def load_env_file(candidates: List[Path]) -> Dict[str, str]:
    """从候选目录依次查找 .env 并解析为 dict（零依赖，不引入 python-dotenv）。

    语义与 topgps_common.load_env_file 完全一致：跳过空行与 # 注释、
    支持 ``export KEY=VALUE`` 前缀、剥离引号；第一个找到的 .env 生效。
    """
    for base in candidates:
        env_path = base / ".env"
        if not env_path.is_file():
            continue
        parsed: Dict[str, str] = {}
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    parsed[key] = value
            return parsed
        except OSError:
            continue
    return {}


def _env_search_paths() -> List[Path]:
    """cwd 优先 + 逐级向上到文件系统根 + 本模块所在目录链（去重）。"""
    paths: List[Path] = []
    cwd = Path.cwd()
    p = cwd
    while True:
        if p not in paths:
            paths.append(p)
        if p == p.parent:
            break
        p = p.parent
    mod_dir = Path(__file__).resolve().parent
    p = mod_dir
    while True:
        if p not in paths:
            paths.append(p)
        if p == p.parent:
            break
        p = p.parent
    return paths


# ---------------------------------------------------------------------------
# 取值
# ---------------------------------------------------------------------------

_env_cache: Optional[Dict[str, str]] = None


def _merged_env() -> Dict[str, str]:
    """.env 值 + os.environ 合并（os.environ 优先，.env 兜底），惰性加载。"""
    global _env_cache
    if _env_cache is None:
        _env_cache = load_env_file(_env_search_paths())
    merged = dict(os.environ)
    for key, value in _env_cache.items():
        if key not in os.environ:
            merged[key] = value
    return merged


def get(key: str, default=None, type_fn: Callable = str):
    """按 key 读配置，可选类型转换；转换失败或缺失时返回 default。"""
    value = _merged_env().get(key, default)
    if value is None:
        return default
    try:
        return type_fn(value)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 合并版 Config（GPS/Mongo/分桶/指标/waybill/wecom/智能表格 全部字段）
# ---------------------------------------------------------------------------

@dataclass
class Config:
    # GPS 接口
    api_url: str = DEFAULT_API_URL
    user_id: str = ""
    password: str = ""
    timeout: float = DEFAULT_TIMEOUT
    interval: int = 10                # GPS 轮询间隔（秒）
    need_address: str = "0"           # GPS 是否返回地址
    # Mongo
    mongo_uri: str = ""
    mongo_db: str = DEFAULT_MONGO_DB
    mongo_collection: str = DEFAULT_MILEAGE_COLLECTION
    # 分桶
    bucket_flush_interval: float = 30.0
    bucket_batch_size: int = 500
    queue_max_size: int = 10_000
    # 指标
    metrics_port: int = 9090
    # waybill
    waybill_api_base: str = "https://183.95.190.189:8681"
    waybill_username: str = ""
    waybill_password: str = ""
    token_buffer_seconds: int = 300
    # 企业微信
    wecom_corp_id: str = ""
    wecom_corp_secret: str = ""
    wecom_agent_id: str = "1000033"
    # 智能表格
    smartsheet_sheet_id: str = ""
    dtjk_docid: str = ""


def config_from_env(
    default_collection: str = DEFAULT_MILEAGE_COLLECTION,
    read_env_collection: bool = False,
) -> Config:
    """从合并环境构建 Config。

    read_env_collection=True 时读取 MONGO_COLLECTION（仅 GPS poller 使用）；
    里程脚本刻意不读，避免被 .env 的 vehicle_gps_buckets 污染（原语义保留）。
    """
    cfg = Config()
    cfg.api_url = get("GPS_API_URL", DEFAULT_API_URL)
    cfg.user_id = get("GPS_USER_ID", "")
    cfg.password = get("GPS_PASSWORD", "")
    cfg.timeout = get("GPS_TIMEOUT", DEFAULT_TIMEOUT, float)
    cfg.interval = get("GPS_INTERVAL", 10, int)
    cfg.need_address = get("GPS_NEED_ADDRESS", "0")
    cfg.mongo_uri = get("MONGO_URI", "")
    cfg.mongo_db = get("MONGO_DB", DEFAULT_MONGO_DB)
    if read_env_collection:
        cfg.mongo_collection = get("MONGO_COLLECTION", default_collection)
    else:
        cfg.mongo_collection = default_collection
    cfg.bucket_flush_interval = get("BUCKET_FLUSH_INTERVAL", 30.0, float)
    cfg.bucket_batch_size = get("BUCKET_BATCH_SIZE", 500, int)
    cfg.queue_max_size = get("QUEUE_MAX_SIZE", 10_000, int)
    cfg.metrics_port = get("METRICS_PORT", 9090, int)
    cfg.waybill_api_base = get("WAYBILL_API_BASE", cfg.waybill_api_base)
    cfg.waybill_username = get("WAYBILL_USERNAME", "")
    cfg.waybill_password = get("WAYBILL_PASSWORD", "")
    cfg.token_buffer_seconds = get("TOKEN_BUFFER_SECONDS", 300, int)
    cfg.wecom_corp_id = get("WECOM_CORP_ID", "")
    cfg.wecom_corp_secret = get("WECOM_CORP_SECRET", "")
    cfg.wecom_agent_id = get("WECOM_AGENT_ID", "1000033")
    cfg.smartsheet_sheet_id = get("SMARTSHEET_SHEET_ID", "")
    cfg.dtjk_docid = get("DTJK_DOCID", "")
    return cfg


__all__ = [
    "load_env_file", "get", "Config", "config_from_env",
    "DEFAULT_API_URL", "DEFAULT_TIMEOUT", "DEFAULT_MONGO_DB",
    "DEFAULT_MILEAGE_COLLECTION", "DEFAULT_GPS_COLLECTION",
    "DATE_COMPACT", "DATE_ISO",
]