# -*- coding: utf-8 -*-
"""
topgps 配置兼容层：re-export 统一 shared 配置。

迁移自 TOPGPS/topgps_common.py 的 Config 相关符号，保持字段名与
旧代码完全一致，避免各采集脚本改动。
"""

from shared.config import (
    Config,
    DEFAULT_API_URL,
    DEFAULT_GPS_COLLECTION,
    DEFAULT_MILEAGE_COLLECTION,
    DEFAULT_MONGO_DB,
    DEFAULT_TIMEOUT,
    DATE_COMPACT,
    DATE_ISO,
    config_from_env,
    get,
    load_env_file,
)

__all__ = [
    "Config",
    "DEFAULT_API_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MONGO_DB",
    "DEFAULT_MILEAGE_COLLECTION",
    "DEFAULT_GPS_COLLECTION",
    "DATE_COMPACT",
    "DATE_ISO",
    "config_from_env",
    "get",
    "load_env_file",
]