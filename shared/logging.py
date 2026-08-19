# -*- coding: utf-8 -*-
"""
统一日志层：stderr 默认输出 + 可选 RotatingFileHandler 按模块名落盘。

- setup_logging(level, log_dir)：幂等；默认 stderr；log_dir 给定时根日志额外写
  logs/cheling.log（RotatingFileHandler maxBytes=5MB backupCount=5）
- get_logger(name)：返回命名 logger；若 log_dir 已配置，按模块名建独立日志文件
  （如 get_logger("waybill_sync.api") -> logs/waybill_sync/api.log）
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5

_log_dir: Optional[Path] = None


def _make_file_handler(path: Path) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
    return handler


def setup_logging(level: str = "INFO", log_dir: Optional[str] = None) -> None:
    """初始化根 logger（stderr）；log_dir 给定时追加根文件日志。幂等。"""
    global _log_dir
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
        root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if log_dir is not None:
        _log_dir = Path(log_dir)
        _log_dir.mkdir(parents=True, exist_ok=True)
        if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
            root.addHandler(_make_file_handler(_log_dir / "cheling.log"))


def get_logger(name: str) -> logging.Logger:
    """返回命名 logger；log_dir 已配置时按模块名落盘（避免重复挂 handler）。"""
    logger = logging.getLogger(name)
    if _log_dir is not None and not any(
        isinstance(h, RotatingFileHandler) for h in logger.handlers
    ):
        rel = name.replace(".", "/")
        logger.addHandler(_make_file_handler(_log_dir / f"{rel}.log"))
        logger.propagate = False
    return logger


__all__ = ["setup_logging", "get_logger"]