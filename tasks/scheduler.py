# -*- coding: utf-8 -*-
"""统一自研调度器：合并 TOPGPS 与 waybill-sync 的定时调度语义。

调度规则（单进程常驻，Tick 60s，时区 Asia/Shanghai）：
  * daily_mileage : 每日 02:00 抓昨日里程入库
  * safety_sync   : 时段感知——06:00-10:00 每 5 分钟，其余时段每 15 分钟；
                    执行返回 True（有审批通过）时立即触发 waybill_sync
  * waybill_sync  : 保底每 15 分钟；safety_sync 审批通过时联动立即执行

CLI：--jobs 选择任务子集、--now 立即执行一次选中任务后退出、--dry-run 打印调度计划。
信号：SIGTERM/SIGINT 优雅关闭。
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from packages.topgps.core.batch_mileage import fetch_one_day_with_retry
from packages.topgps.core.common import Config, load_config
from packages.waybill_sync.orchestrator import sync_waybill_data
from packages.waybill_sync.scripts.safety_sync import safety_sync_main
from shared.logging import get_logger, setup_logging

TICK_SECONDS = 60
SHANGHAI = timezone(timedelta(hours=8))
HIGH_FREQ_START_HOUR = 6
HIGH_FREQ_END_HOUR = 10
HIGH_FREQ_INTERVAL = 300
LOW_FREQ_INTERVAL = 900
DAILY_MILEAGE_HOUR = 2
DAILY_MILEAGE_RETRY = 2

EXIT_SUCCESS = 0
EXIT_CONFIG = 2

logger = get_logger("scheduler")


def now_shanghai() -> datetime:
    return datetime.now(SHANGHAI)


def waybill_interval(now: datetime) -> int:
    """waybill_sync 保底间隔：始终 15 分钟。"""
    return LOW_FREQ_INTERVAL


def safety_sync_interval(now: datetime) -> int:
    """safety_sync 时段感知间隔：06:00-10:00 高频 5 分钟，其余 15 分钟。"""
    hour = now.hour
    if HIGH_FREQ_START_HOUR <= hour < HIGH_FREQ_END_HOUR:
        return HIGH_FREQ_INTERVAL
    return LOW_FREQ_INTERVAL


def daily_mileage_interval(now: datetime) -> int:
    """daily_mileage 每日 02:00：距下一次 02:00 的秒数。"""
    target = now.replace(hour=DAILY_MILEAGE_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return int((target - now).total_seconds())


async def _daily_mileage_job() -> None:
    """抓取昨日里程入库（幂等 upsert，可重复执行）。"""
    cfg: Config = load_config(argparse.Namespace(), default_collection="vehicle_mileage")
    yesterday = (now_shanghai() - timedelta(days=1)).strftime("%Y-%m-%d")
    query_date, records = fetch_one_day_with_retry(
        yesterday, cfg, retry=DAILY_MILEAGE_RETRY, dry_run=False
    )
    logger.info("daily_mileage 完成: %s 共 %d 条", query_date, records)


async def _safety_sync_job() -> bool:
    """待审批运单安全检查；返回是否有审批通过。"""
    return await safety_sync_main()


async def _waybill_sync_job() -> None:
    """同步近 7 天运单到智能表格。"""
    result = await sync_waybill_data(days=7)
    if not result.success:
        raise RuntimeError(f"waybill_sync 失败: {result.error}")


@dataclass
class Job:
    name: str
    description: str
    interval_fn: Callable[[datetime], int]
    coro: Callable[[], Any]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


def build_jobs() -> List[Job]:
    return [
        Job(
            name="daily_mileage",
            description="每日 02:00 抓昨日里程入库",
            interval_fn=daily_mileage_interval,
            coro=_daily_mileage_job,
        ),
        Job(
            name="safety_sync",
            description="安全检查与审批（06-10 点每 5 分钟，其余每 15 分钟）",
            interval_fn=safety_sync_interval,
            coro=_safety_sync_job,
        ),
        Job(
            name="waybill_sync",
            description="运单同步（保底每 15 分钟，审批通过联动立即执行）",
            interval_fn=waybill_interval,
            coro=_waybill_sync_job,
        ),
    ]


def select_jobs(all_jobs: List[Job], names: List[str]) -> List[Job]:
    if not names:
        return all_jobs
    by_name = {j.name: j for j in all_jobs}
    missing = [n for n in names if n not in by_name]
    if missing:
        raise ValueError(f"未知任务: {', '.join(missing)}")
    return [by_name[n] for n in names]


def print_plan(jobs: List[Job]) -> None:
    logger.info("=" * 56)
    logger.info("调度计划（时区 Asia/Shanghai）")
    logger.info("=" * 56)
    for job in jobs:
        logger.info("  %-14s %s", job.name, job.description)
    logger.info("=" * 56)


async def run_once(jobs: List[Job]) -> int:
    """--now：立即执行一次选中任务后退出。"""
    for job in jobs:
        logger.info("执行 %s ...", job.name)
        try:
            result = await job.coro()
            logger.info("%s 完成: %r", job.name, result)
        except Exception as exc:
            logger.error("%s 失败: %s", job.name, exc)
    return EXIT_SUCCESS


async def run_loop(jobs: List[Job], stop_event: asyncio.Event) -> None:
    """常驻调度主循环。"""
    for job in jobs:
        job.next_run = now_shanghai() + timedelta(seconds=job.interval_fn(now_shanghai()))
        logger.info(
            "[%s] 已注册，下次执行 %s", job.name,
            job.next_run.strftime("%Y-%m-%d %H:%M:%S"),
        )

    while not stop_event.is_set():
        now = now_shanghai()
        for job in jobs:
            if job.next_run is None or job.next_run > now:
                continue
            logger.info("[%s] 开始执行", job.name)
            try:
                result = await job.coro()
                logger.info("[%s] 执行完成: %r", job.name, result)
                if job.name == "safety_sync" and result:
                    waybill = next(j for j in jobs if j.name == "waybill_sync")
                    waybill.next_run = now_shanghai()
                    logger.info("[safety_sync] 有审批通过，联动立即触发 waybill_sync")
            except Exception as exc:
                logger.error("[%s] 执行失败: %s", job.name, exc)
            finally:
                job.last_run = now_shanghai()
                job.next_run = job.last_run + timedelta(
                    seconds=job.interval_fn(job.last_run)
                )

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=TICK_SECONDS)
        except asyncio.TimeoutError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scheduler",
        description="cheling 统一调度器：daily_mileage / safety_sync / waybill_sync",
    )
    parser.add_argument(
        "--jobs", default="",
        help="逗号分隔的任务名子集（默认全部）：daily_mileage,safety_sync,waybill_sync",
    )
    parser.add_argument(
        "--now", action="store_true",
        help="立即执行一次选中任务后退出（不进入常驻循环）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅打印调度计划后退出",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging("INFO")

    try:
        jobs = select_jobs(build_jobs(), [s for s in args.jobs.split(",") if s])
    except ValueError as exc:
        logger.error("%s", exc)
        return EXIT_CONFIG

    if args.dry_run:
        print_plan(jobs)
        return EXIT_SUCCESS

    stop_event = asyncio.Event()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _request_stop() -> None:
        logger.info("收到停止信号，优雅关闭中...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        if args.now:
            return loop.run_until_complete(run_once(jobs))
        loop.run_until_complete(run_loop(jobs, stop_event))
        return EXIT_SUCCESS
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt，退出")
        return EXIT_SUCCESS
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())