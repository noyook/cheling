#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPGPS 车辆里程批量采集脚本。

调用 vehicle_mileage_fetcher 的 GetVehicleMileage 函数，批量获取近一年
（默认 365 天）每日车辆里程数据，写入 MongoDB TOPGPS.vehicle_mileage。

特性：
  * 并发抓取（默认 5 线程），失败日期自动重试
  * 幂等 upsert：重复执行同一日期仅更新，不产生重复文档
  * 失败日期持久化到文件（mileage_failed_dates.txt），支持 --retry-file 补跑
  * 断点续跑：--resume 跳过已完整入库的日期

用法：
    python batch_mileage_fetcher.py                          # 近一年（今天往前 365 天）
    python batch_mileage_fetcher.py --days 30                # 近 30 天
    python batch_mileage_fetcher.py --start-date 2025-08-15 --end-date 2026-08-15
    python batch_mileage_fetcher.py --workers 8              # 提高并发
    python batch_mileage_fetcher.py --retry-file mileage_failed_dates.txt  # 补跑失败日期
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pymongo

from packages.topgps.core.mileage_fetcher import (
    GetVehicleMileage,
    save_mileage_to_mongo,
)

from packages.topgps.core.common import (
    Config,
    iter_date_range,
    load_config,
    normalize_query_date,
    parse_args_date,
    setup_logging,
)

FAILED_DATES_FILE = "mileage_failed_dates.txt"
DEFAULT_DAYS = 365
DEFAULT_WORKERS = 5
DEFAULT_RETRY = 2
SLEEP_BETWEEN_RETRIES = 2.0

EXIT_SUCCESS = 0
EXIT_PARTIAL = 3  # 部分日期失败

logger = logging.getLogger("batch_mileage_fetcher")


# ---------------------------------------------------------------------------
# 单日任务
# ---------------------------------------------------------------------------

def fetch_one_day(
    query_date: str,
    cfg: Config,
    dry_run: bool = False,
) -> Tuple[str, int]:
    """抓取单日里程并入库，返回 (query_date, 记录数)；失败抛异常。"""
    records = GetVehicleMileage(query_date, cfg)
    if dry_run:
        return query_date, len(records)
    written, failed = save_mileage_to_mongo(records, query_date, cfg)
    if failed:
        raise RuntimeError(f"写入失败 {failed} 条")
    return query_date, len(records)


def fetch_one_day_with_retry(
    query_date: str,
    cfg: Config,
    retry: int,
    dry_run: bool = False,
) -> Tuple[str, int]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, retry + 2):
        try:
            return fetch_one_day(query_date, cfg, dry_run)
        except Exception as exc:
            last_exc = exc
            logger.warning("[%s] 第 %d 次尝试失败: %s", query_date, attempt, exc)
            time.sleep(SLEEP_BETWEEN_RETRIES * attempt)
    raise RuntimeError(f"{query_date} 重试 {retry} 次后仍失败: {last_exc}")


# ---------------------------------------------------------------------------
# 失败日期文件管理
# ---------------------------------------------------------------------------

def read_failed_dates(path: Path) -> List[str]:
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_failed_dates(path: Path, dates: List[str]) -> None:
    path.write_text("\n".join(sorted(dates)) + ("\n" if dates else ""), encoding="utf-8")


# ---------------------------------------------------------------------------
# 已入库日期探测（断点续跑）
# ---------------------------------------------------------------------------

def load_done_dates(cfg: Config, dry_run: bool) -> set:
    """查询 MongoDB 中已存在完整数据的 query_date 集合。"""
    if dry_run or not cfg.mongo_uri:
        return set()
    client = pymongo.MongoClient(cfg.mongo_uri, serverSelectionTimeoutMS=10000)
    try:
        collection = client[cfg.mongo_db][cfg.mongo_collection]
        return {doc["_id"] for doc in collection.aggregate(
            [{"$group": {"_id": "$query_date"}}]
        )}
    finally:
        client.close()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch_mileage_fetcher",
        description="TOPGPS 车辆里程批量采集：按日调用 GetVehicleMileage 并写入 MongoDB vehicle_mileage。",
    )
    parser.add_argument(
        "--days", type=int, default=DEFAULT_DAYS,
        help=f"抓取最近 N 天（默认 {DEFAULT_DAYS}）",
    )
    parser.add_argument(
        "--start-date", default=None,
        help="起始日期（含），格式 2025-08-15 或 20250815；与 --days 互斥，优先于 --days",
    )
    parser.add_argument(
        "--end-date", default=None,
        help="结束日期（含），默认今天；与 --days 互斥",
    )
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"并发线程数（默认 {DEFAULT_WORKERS}）",
    )
    parser.add_argument(
        "--retry", type=int, default=DEFAULT_RETRY,
        help=f"单日失败重试次数（默认 {DEFAULT_RETRY}）",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="跳过 MongoDB 中已存在 query_date 的日期（断点续跑）",
    )
    parser.add_argument(
        "--retry-file", default=FAILED_DATES_FILE,
        help=f"失败日期文件路径（默认 {FAILED_DATES_FILE}）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅调用 API 不写库",
    )
    parser.add_argument(
        "--db", default=None,
        help="数据库名，覆盖 MONGO_DB",
    )
    parser.add_argument(
        "--collection", default=None,
        help="集合名，覆盖默认 vehicle_mileage",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="stderr 日志级别（默认 INFO）",
    )
    return parser


def resolve_dates(args: argparse.Namespace) -> List[str]:
    """确定待抓取日期列表；--retry-file 存在且非空时优先补跑模式。"""
    retry_path = Path(args.retry_file)
    if args.retry_file and args.retry_file != FAILED_DATES_FILE and retry_path.is_file():
        failed = read_failed_dates(retry_path)
        if failed:
            logger.info("补跑模式：读取 %d 个失败日期", len(failed))
            return sorted(normalize_query_date(d) for d in failed)

    end = parse_args_date(args.end_date) if args.end_date else date.today()
    if args.start_date:
        start = parse_args_date(args.start_date)
    else:
        start = end - timedelta(days=args.days - 1)
    if start > end:
        raise ValueError(f"start_date({start}) 晚于 end_date({end})")
    logger.info("抓取区间：%s ~ %s，共 %d 天", start, end, (end - start).days + 1)
    return [d.strftime("%Y%m%d") for d in iter_date_range(start, end)]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)

    try:
        cfg = load_config(args, default_collection="vehicle_mileage")
        dates = resolve_dates(args)

        if args.resume and not args.dry_run:
            done = load_done_dates(cfg, args.dry_run)
            skipped = [d for d in dates if d in done]
            dates = [d for d in dates if d not in done]
            if skipped:
                logger.info("断点续跑：跳过 %d 个已入库日期（剩余 %d 天）", len(skipped), len(dates))

        if not dates:
            logger.info("没有需要抓取的日期")
            return EXIT_SUCCESS

        total_records = 0
        failed_dates: List[str] = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(fetch_one_day_with_retry, d, cfg, args.retry, args.dry_run): d
                for d in dates
            }
            for future in as_completed(futures):
                d = futures[future]
                try:
                    _, count = future.result()
                    total_records += count
                    logger.info("[%s] 成功，%d 条", d, count)
                except Exception as exc:
                    failed_dates.append(d)
                    logger.error("[%s] 最终失败: %s", d, exc)

        elapsed = time.time() - start_time
        write_failed_dates(Path(args.retry_file), failed_dates)
        logger.info(
            "批量完成：共 %d 天，成功 %d，失败 %d，累计 %d 条记录，耗时 %.1f 分钟",
            len(dates), len(dates) - len(failed_dates), len(failed_dates),
            total_records, elapsed / 60,
        )
        if failed_dates:
            logger.warning("失败日期已写入 %s，可用 --retry-file 补跑", args.retry_file)
            return EXIT_PARTIAL
        return EXIT_SUCCESS
    except (ValueError, httpx.HTTPError, pymongo.errors.PyMongoError) as exc:
        logger.error("执行失败: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
