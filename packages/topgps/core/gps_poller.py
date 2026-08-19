#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPGPS 车辆 GPS 数据采集 + MongoDB 写入（生产级优化版）。

合并 gps_poller + gps_mongo_poller，采用生产者-消费者架构：
  * Producer：轮询 API，原始车辆数据入 asyncio.Queue
  * Consumer：按 (plate_num, hour) 分桶聚合，批量 upsert 写入 MongoDB
  * Bucket Pattern：每车每 15 分钟一个文档，points 数组存储该窗口全部 GPS 点，
    latest_point 存储窗口内最新点（查询最新位置直接读取，无需 $unwind）
  * 重试：API 请求 tenacity 指数退避；写入失败回灌队列
  * 指标：内嵌 /metrics HTTP 端点 + 结构化日志

配置：全部通过环境变量读取（GPS_*、MONGO_*），支持 .env 文件。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
import weakref
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
import motor.motor_asyncio
from pymongo import UpdateOne
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from packages.topgps.core.common import (
    Config,
    build_request_data,
    load_config,
    setup_logging,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
MONGO_SELECT_TIMEOUT_MS = 8000

# 数据质量过滤
FILTER_STALE_MAX_AGE_SECONDS = 90.0  # GpsTime 早于当前时间超过该秒数则过滤
FILTER_ZERO_SPEED = True             # 过滤 speed == 0 的点

# 分桶窗口粒度（分钟）：每车每窗口一个文档，points 存该窗口全部点位
BUCKET_WINDOW_MINUTES = 15

# 退出码
EXIT_SUCCESS = 0
EXIT_NETWORK = 1
EXIT_CONFIG = 2
EXIT_DATA = 3

logger = logging.getLogger("gps_bucket_poller")

# ---------------------------------------------------------------------------
# 指标（线程安全由 asyncio 单线程保证）
# ---------------------------------------------------------------------------

@dataclass
class Metrics:
    ticks_total: int = 0
    ticks_success: int = 0
    ticks_failed: int = 0
    vehicles_received: int = 0
    vehicles_enqueued: int = 0
    vehicles_dropped: int = 0
    points_filtered: int = 0
    points_duplicates_skipped: int = 0
    buckets_flushed: int = 0
    points_written: int = 0
    points_failed: int = 0
    mongo_errors: int = 0
    api_errors: int = 0
    queue_depth: int = 0
    last_tick_ms: int = 0
    last_flush_ms: int = 0
    start_time: float = field(default_factory=time.time)

    def to_prometheus(self) -> str:
        now = time.time()
        uptime = now - self.start_time
        lines = [
            "# HELP gps_poller_ticks_total Total polling ticks",
            "# TYPE gps_poller_ticks_total counter",
            f'gps_poller_ticks_total{{status="success"}} {self.ticks_success}',
            f'gps_poller_ticks_total{{status="failed"}} {self.ticks_failed}',
            "# HELP gps_poller_vehicles_total Total vehicles processed",
            "# TYPE gps_poller_vehicles_total counter",
            f"gps_poller_vehicles_received_total {self.vehicles_received}",
            f"gps_poller_vehicles_enqueued_total {self.vehicles_enqueued}",
            f"gps_poller_vehicles_dropped_total {self.vehicles_dropped}",
            "# HELP gps_poller_points_filtered_total Total GPS points filtered by quality rules",
            "# TYPE gps_poller_points_filtered_total counter",
            f"gps_poller_points_filtered_total {self.points_filtered}",
            "# HELP gps_poller_points_duplicates_skipped_total Total duplicate GPS points skipped within bucket",
            "# TYPE gps_poller_points_duplicates_skipped_total counter",
            f"gps_poller_points_duplicates_skipped_total {self.points_duplicates_skipped}",
            "# HELP gps_poller_points_total Total GPS points written",
            "# TYPE gps_poller_points_total counter",
            f"gps_poller_points_written_total {self.points_written}",
            f"gps_poller_points_failed_total {self.points_failed}",
            "# HELP gps_poller_buckets_flushed_total Total buckets flushed",
            "# TYPE gps_poller_buckets_flushed_total counter",
            f"gps_poller_buckets_flushed_total {self.buckets_flushed}",
            "# HELP gps_poller_errors_total Total errors",
            "# TYPE gps_poller_errors_total counter",
            f'gps_poller_errors_total{{source="api"}} {self.api_errors}',
            f'gps_poller_errors_total{{source="mongo"}} {self.mongo_errors}',
            "# HELP gps_poller_queue_depth Current queue depth",
            "# TYPE gps_poller_queue_depth gauge",
            f"gps_poller_queue_depth {self.queue_depth}",
            "# HELP gps_poller_last_tick_ms Last tick latency",
            "# TYPE gps_poller_last_tick_ms gauge",
            f"gps_poller_last_tick_ms {self.last_tick_ms}",
            "# HELP gps_poller_last_flush_ms Last flush latency",
            "# TYPE gps_poller_last_flush_ms gauge",
            f"gps_poller_last_flush_ms {self.last_flush_ms}",
            "# HELP gps_poller_uptime_seconds Process uptime",
            "# TYPE gps_poller_uptime_seconds gauge",
            f"gps_poller_uptime_seconds {uptime:.3f}",
        ]
        return "\n".join(lines) + "\n"

    def to_json(self) -> Dict[str, Any]:
        return {
            "ticks_total": self.ticks_total,
            "ticks_success": self.ticks_success,
            "ticks_failed": self.ticks_failed,
            "vehicles_received": self.vehicles_received,
            "vehicles_enqueued": self.vehicles_enqueued,
            "vehicles_dropped": self.vehicles_dropped,
            "points_filtered": self.points_filtered,
            "points_duplicates_skipped": self.points_duplicates_skipped,
            "buckets_flushed": self.buckets_flushed,
            "points_written": self.points_written,
            "points_failed": self.points_failed,
            "mongo_errors": self.mongo_errors,
            "api_errors": self.api_errors,
            "queue_depth": self.queue_depth,
            "last_tick_ms": self.last_tick_ms,
            "last_flush_ms": self.last_flush_ms,
            "uptime_sec": round(time.time() - self.start_time, 3),
        }


METRICS = Metrics()

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    base = time.strftime("%Y-%m-%dT%H:%M:%S")
    tz = time.strftime("%z")
    if len(tz) == 5:
        tz = f"{tz[:3]}:{tz[3:]}"
    return base + tz


def _parse_gps_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _quarter_bucket(dt: datetime) -> datetime:
    """将 datetime 对齐到 15 分钟窗口边界（与 gps_time 同基准，查询时保持一致）。"""
    return dt.replace(minute=(dt.minute // BUCKET_WINDOW_MINUTES) * BUCKET_WINDOW_MINUTES,
                      second=0, microsecond=0)


def _should_filter(raw: Dict[str, Any], gps_time: datetime) -> Tuple[bool, str]:
    """按数据质量规则判定是否过滤该点。返回 (是否过滤, 原因)。"""
    gt = gps_time.replace(tzinfo=None) if gps_time.tzinfo is not None else gps_time
    if gt < datetime.now() - timedelta(seconds=FILTER_STALE_MAX_AGE_SECONDS):
        return True, "stale_gpstime"
    if FILTER_ZERO_SPEED:
        speed = raw.get("Speed")
        try:
            if float(speed) == 0.0:
                return True, "zero_speed"
        except (TypeError, ValueError):
            pass
    return False, ""


# ---------------------------------------------------------------------------
# 配置与请求构造来自 topgps_common（本脚本读取 MONGO_COLLECTION 环境变量，
# 默认 vehicle_gps_buckets）
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 生产者：API 轮询 + Queue 入队
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.TransportError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _fetch_raw_with_retry(
    client: httpx.AsyncClient,
    cfg: Config,
) -> Tuple[int, List[Dict[str, Any]]]:
    """带重试的原始数据获取，返回 (http_status, raw_vehicles_list)。"""
    async with client.stream(
        "POST", cfg.api_url,
        data=build_request_data(cfg, "GetVehicleGpsInfo", Vehicles=[], NeedAddress=cfg.need_address),
    ) as resp:
        if resp.status_code != 200:
            return resp.status_code, []
        total = 0
        chunks: List[bytes] = []
        async for chunk in resp.aiter_bytes():
            total += len(chunk)
            if total > MAX_RESPONSE_SIZE:
                raise ValueError("Response exceeded 5MB limit")
            chunks.append(chunk)
        raw = b"".join(chunks)
        data = json.loads(raw.decode("utf-8"))
        ret = data.get("Ret", 0)
        if ret != 0:
            raise ValueError(f"API Ret={ret} Msg={data.get('Msg', '')}")
        vehicles = data.get("Data", [])
        if not isinstance(vehicles, list):
            raise ValueError("Data field is not a list")
        return 200, vehicles


async def producer(
    cfg: Config,
    queue: asyncio.Queue,
    stop_event: asyncio.Event,
    http_client: httpx.AsyncClient,
) -> None:
    """守护循环：按 interval 对齐边界轮询 API，原始车辆数据入队。"""
    tick_id = 1
    next_fire = time.time() + (cfg.interval - time.time() % cfg.interval)

    logger.info(
        "[Producer] 启动，interval=%ss, timeout=%ss, queue_max=%d",
        cfg.interval, cfg.timeout, cfg.queue_max_size,
    )

    while not stop_event.is_set():
        now = time.time()
        if now < next_fire:
            sleep_for = max(0.0, next_fire - now)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
                break
            except asyncio.TimeoutError:
                pass
            continue

        start = time.perf_counter()
        METRICS.ticks_total += 1
        tick_id += 1
        next_fire += cfg.interval

        try:
            status, raw_vehicles = await _fetch_raw_with_retry(http_client, cfg)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            METRICS.last_tick_ms = elapsed_ms

            if status != 200:
                logger.error("[Producer] tick=%d HTTP %d", tick_id, status)
                METRICS.ticks_failed += 1
                METRICS.api_errors += 1
                continue

            count = len(raw_vehicles)
            METRICS.vehicles_received += count
            METRICS.ticks_success += 1
            logger.info("[Producer] tick=%d 获取 %d 台车，耗时 %dms", tick_id, count, elapsed_ms)

            dropped = 0
            for raw in raw_vehicles:
                if queue.qsize() >= cfg.queue_max_size:
                    dropped += 1
                    continue
                queue.put_nowait(raw)
                METRICS.vehicles_enqueued += 1
            if dropped:
                METRICS.vehicles_dropped += dropped
                logger.warning("[Producer] 队列满，丢弃 %d 台车", dropped)

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            METRICS.last_tick_ms = elapsed_ms
            METRICS.ticks_failed += 1
            METRICS.api_errors += 1
            logger.error("[Producer] tick=%d 异常: %s", tick_id, exc)

    logger.info("[Producer] 停止")


# ---------------------------------------------------------------------------
# 消费者：分桶聚合 + 批量写入 MongoDB
# ---------------------------------------------------------------------------

@dataclass
class BucketKey:
    plate_num: str
    color_code: int
    hour: datetime

    def __hash__(self) -> int:
        return hash((self.plate_num, self.color_code, self.hour.isoformat()))


@dataclass
class Bucket:
    key: BucketKey
    points: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    t_seen: Set[datetime] = field(default_factory=set)
    latest_point: Optional[Dict[str, Any]] = None


def _build_point(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """将 API 原始数据转为桶内单点文档。"""
    gps_time = _parse_gps_time(raw.get("GpsTime"))
    if gps_time is None:
        return None
    return {
        "t": gps_time,                     # 精确时间
        "lng": raw.get("Longitude"),       # 经度
        "lat": raw.get("Latitude"),        # 纬度
        "spd": raw.get("Speed"),           # 速度
        "mil": raw.get("Mileage"),         # 里程
        "valid": raw.get("IsGpsValid"),    # GPS有效
        "state": raw.get("StateInfo"),     # 状态
        "addr": raw.get("Address"),        # 地址
        "alarm": raw.get("AlarmInfo"),     # 报警
        "org": raw.get("OrgName"),         # 组织
        "dir": raw.get("Direction"),       # 方向
        "alt": raw.get("Altitude"),        # 海拔
        "driver": raw.get("DriverName"),   # 驾驶员
        "license": raw.get("DriverLicense"), # 驾照
        "region": raw.get("RegionName"),   # 区域
        "fuel": raw.get("ResidualFuel"),   # 油量
        "signal": raw.get("WirelessSignal"), # 信号
    }


def _build_bucket_doc(bucket: Bucket) -> Dict[str, Any]:
    """将内存中的 Bucket 转为 MongoDB 文档。"""
    return {
        "plate_num": bucket.key.plate_num,
        "color_code": bucket.key.color_code,
        "hour": bucket.key.hour,
        "point_count": len(bucket.points),
        "points": bucket.points,
        "latest_point": bucket.latest_point,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class BucketBuffer:
    """内存分桶缓冲区，定时/定量 flush 到 MongoDB。"""

    def __init__(self, collection, batch_size: int, flush_interval: float):
        self.collection = collection
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buckets: Dict[BucketKey, Bucket] = {}
        self._last_flush = time.time()
        self._lock = asyncio.Lock()

    def _get_or_create(self, key: BucketKey) -> Bucket:
        if key not in self.buckets:
            self.buckets[key] = Bucket(key=key)
        return self.buckets[key]

    async def add(self, raw: Dict[str, Any]) -> bool:
        plate = raw.get("PlateNum", "")
        if not plate or not plate.strip():
            return False
        gps_time = _parse_gps_time(raw.get("GpsTime"))
        if gps_time is None:
            return False

        filtered, reason = _should_filter(raw, gps_time)
        if filtered:
            METRICS.points_filtered += 1
            logger.debug("[Consumer] 过滤 %s: %s", reason, plate.strip())
            return False

        key = BucketKey(
            plate_num=plate.strip(),
            color_code=raw.get("ColorCode", 0) or 0,
            hour=_quarter_bucket(gps_time),
        )
        point = _build_point(raw)
        if point is None:
            return False

        async with self._lock:
            bucket = self._get_or_create(key)
            if point["t"] in bucket.t_seen:
                METRICS.points_duplicates_skipped += 1
                return False
            bucket.t_seen.add(point["t"])
            bucket.points.append(point)
            if bucket.latest_point is None or point["t"] > bucket.latest_point["t"]:
                bucket.latest_point = point

        return True

    async def maybe_flush(self, force: bool = False) -> Tuple[int, int]:
        now = time.time()
        should_flush = (
            force
            or len(self.buckets) >= self.batch_size
            or (self.buckets and now - self._last_flush >= self.flush_interval)
        )
        if not should_flush:
            return 0, 0

        async with self._lock:
            if not self.buckets:
                return 0, 0
            buckets_to_flush = list(self.buckets.values())
            self.buckets = {}
            self._last_flush = now

        docs = [_build_bucket_doc(b) for b in buckets_to_flush]
        return await self._flush_docs(docs)

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=False,
    )
    async def _flush_docs(self, docs: List[Dict[str, Any]]) -> Tuple[int, int]:
        """批量 upsert：同 (plate_num, color_code, hour) 窗口追加 points、刷新 latest_point。"""
        if not docs:
            return 0, 0
        start = time.perf_counter()
        try:
            operations = [
                UpdateOne(
                    {"plate_num": d["plate_num"], "color_code": d["color_code"], "hour": d["hour"]},
                    {
                        "$push": {"points": {"$each": d["points"]}},
                        "$inc": {"point_count": len(d["points"])},
                        "$set": {
                            "latest_point": d["latest_point"],
                            "updated_at": d["updated_at"],
                        },
                        "$setOnInsert": {"created_at": d["created_at"]},
                    },
                    upsert=True,
                )
                for d in docs
            ]
            result = await self.collection.bulk_write(operations, ordered=False)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            written = result.upserted_count + result.modified_count
            points = sum(d["point_count"] for d in docs)
            METRICS.buckets_flushed += written
            METRICS.points_written += points
            METRICS.last_flush_ms = elapsed_ms
            logger.info(
                "[Consumer] Flush %d buckets (%d points) in %dms",
                written, points, elapsed_ms,
            )
            return written, 0
        except Exception as exc:
            METRICS.mongo_errors += 1
            METRICS.points_failed += sum(d["point_count"] for d in docs)
            logger.error("[Consumer] Flush failed: %s", exc)
            raise


async def consumer(
    cfg: Config,
    queue: asyncio.Queue,
    stop_event: asyncio.Event,
    collection,
) -> None:
    """从队列消费原始数据，分桶聚合，定时 flush。"""
    buffer = BucketBuffer(
        collection=collection,
        batch_size=cfg.bucket_batch_size,
        flush_interval=cfg.bucket_flush_interval,
    )

    logger.info(
        "[Consumer] 启动，batch_size=%d, flush_interval=%.1fs",
        cfg.bucket_batch_size, cfg.bucket_flush_interval,
    )

    while not stop_event.is_set() or not queue.empty():
        try:
            raw = await asyncio.wait_for(queue.get(), timeout=1.0)
            await buffer.add(raw)
            queue.task_done()
        except asyncio.TimeoutError:
            pass

        # 定时尝试 flush
        await buffer.maybe_flush()
        METRICS.queue_depth = queue.qsize()

    # 最终强制 flush
    logger.info("[Consumer] 最终强制 flush...")
    await buffer.maybe_flush(force=True)
    logger.info("[Consumer] 停止")


# ---------------------------------------------------------------------------
# 指标 HTTP 服务
# ---------------------------------------------------------------------------

async def metrics_server(port: int, stop_event: asyncio.Event) -> None:
    """极简 /metrics HTTP 端点（Prometheus 格式）。"""
    import aiohttp.web

    async def handle_metrics(request: aiohttp.web.Request) -> aiohttp.web.Response:
        return aiohttp.web.Response(
            text=METRICS.to_prometheus(),
            content_type="text/plain; version=0.0.4",
        )

    async def handle_health(request: aiohttp.web.Request) -> aiohttp.web.Response:
        return aiohttp.web.Response(
            text=json.dumps({"status": "ok", "metrics": METRICS.to_json()}, ensure_ascii=False),
            content_type="application/json",
        )

    app = aiohttp.web.Application()
    app.router.add_get("/metrics", handle_metrics)
    app.router.add_get("/health", handle_health)

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("[Metrics] HTTP 服务启动于 http://0.0.0.0:%d/metrics", port)

    await stop_event.wait()
    await runner.cleanup()
    logger.info("[Metrics] HTTP 服务停止")


# ---------------------------------------------------------------------------
# 主控 + 信号处理
# ---------------------------------------------------------------------------

async def run_daemon(cfg: Config) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        logger.info("收到停止信号，优雅关闭中...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except (NotImplementedError, RuntimeError):
            pass

    queue: asyncio.Queue = asyncio.Queue(maxsize=cfg.queue_max_size)

    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
        cfg.mongo_uri,
        serverSelectionTimeoutMS=MONGO_SELECT_TIMEOUT_MS,
        connectTimeoutMS=MONGO_SELECT_TIMEOUT_MS,
    )
    collection = mongo_client[cfg.mongo_db][cfg.mongo_collection]

    # 创建索引（幂等）
    try:
        await collection.create_index([("plate_num", 1), ("hour", -1)], background=True)
        await collection.create_index([("hour", -1)], background=True)
        logger.info("[MongoDB] 索引创建/确认完成")
    except Exception as exc:
        logger.warning("[MongoDB] 索引创建失败（可能已存在）: %s", exc)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(cfg.timeout),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    ) as http_client:
        tasks = [
            asyncio.create_task(producer(cfg, queue, stop_event, http_client)),
            asyncio.create_task(consumer(cfg, queue, stop_event, collection)),
            asyncio.create_task(metrics_server(cfg.metrics_port, stop_event)),
        ]

        # 优雅关闭：先停生产者，等队列排空，再停消费者和指标服务
        await stop_event.wait()
        logger.info("[Main] 停止信号已触发，等待生产者结束...")
        await tasks[0]
        logger.info("[Main] 生产者已结束，等待队列排空...")
        await queue.join()
        logger.info("[Main] 队列已排空，停止消费者...")
        # consumer 会在 stop_event 且 queue 空时退出
        await tasks[1]
        logger.info("[Main] 消费者已结束，停止指标服务...")
        await tasks[2]

    mongo_client.close()
    logger.info("[Main] 全部关闭完成")


# ---------------------------------------------------------------------------
# 输出辅助
# ---------------------------------------------------------------------------

def emit(result: Dict[str, Any], output_file: Optional[str]) -> None:
    line = json.dumps(result, ensure_ascii=False)
    if output_file:
        with open(output_file, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    else:
        print(line, flush=True)


async def _run_once(cfg: Config) -> int:
    """单次轮询验证：拉取一次原始 GPS 数据并输出统计，不写库、不启动守护进程。"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(cfg.timeout)) as client:
        try:
            status, vehicles = await _fetch_raw_with_retry(client, cfg)
        except Exception as exc:
            emit({"status": "error", "error": str(exc)}, None)
            return EXIT_NETWORK
    if status != 200:
        emit({"status": "http_error", "http_status": status}, None)
        return EXIT_NETWORK
    emit({"status": "ok", "vehicles": len(vehicles)}, None)
    return EXIT_SUCCESS


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gps_bucket_poller",
        description="TOPGPS 车辆 GPS 采集 + MongoDB 分桶写入（生产级优化版）。",
    )
    parser.add_argument(
        "--interval", type=int, default=None,
        help="轮询间隔（秒）；默认取 GPS_INTERVAL 或 10",
    )
    parser.add_argument(
        "--timeout", type=float, default=None,
        help="单次请求超时（秒）；默认取 GPS_TIMEOUT 或 8",
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
        "--metrics-port", type=int, default=None,
        help="指标 HTTP 端口；默认取 METRICS_PORT 或 9090",
    )
    parser.add_argument(
        "--output-file", default=None,
        help="输出到文件（追加 JSON Lines）而非 stdout",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="单次轮询验证：拉取一次原始数据并输出统计后退出（不写库、不启动守护进程）",
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

    cfg = load_config(args, default_collection="vehicle_gps_buckets", read_env_collection=True)

    # 启动校验
    if not cfg.user_id or not cfg.password:
        emit({"status": "config_error", "error": "GPS_USER_ID and GPS_PASSWORD are required"}, args.output_file)
        return EXIT_CONFIG
    if cfg.timeout >= cfg.interval:
        emit({"status": "config_error", "error": "GPS_TIMEOUT must be less than GPS_INTERVAL"}, args.output_file)
        return EXIT_CONFIG
    if not cfg.mongo_uri or not cfg.mongo_db:
        emit({"status": "config_error", "error": "MONGO_URI and MONGO_DB are required"}, args.output_file)
        return EXIT_CONFIG

    try:
        if args.once:
            return asyncio.run(_run_once(cfg))
        asyncio.run(run_daemon(cfg))
        return EXIT_SUCCESS
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt，退出")
        return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
