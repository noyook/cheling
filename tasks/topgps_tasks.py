# -*- coding: utf-8 -*-
"""TOPGPS Prefect flows：每日里程采集。"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from prefect import flow

from packages.topgps.core.batch_mileage import fetch_one_day_with_retry
from packages.topgps.core.common import Config, load_config

DEFAULT_RETRY = 2


@flow(log_prints=True, retries=2, retry_delay_seconds=60)
def daily_mileage_flow(query_date: str | None = None, dry_run: bool = False) -> dict:
    """每日里程采集：默认抓取昨日并入库；dry_run 只取数不写库。"""
    if query_date is None:
        query_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    cfg: Config = load_config(argparse.Namespace(), default_collection="vehicle_mileage")
    fetched_date, records = fetch_one_day_with_retry(
        query_date, cfg, retry=DEFAULT_RETRY, dry_run=dry_run
    )

    result = {"query_date": fetched_date, "records": records, "dry_run": dry_run}
    print(f"daily_mileage_flow 完成: {records} 条记录 (dry_run={dry_run})")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="topgps_tasks",
        description="TOPGPS 每日里程采集 flow CLI",
    )
    parser.add_argument(
        "--date", default=None,
        help="查询日期，支持 20260815 或 2026-08-15；默认昨日",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅获取并打印记录数，不写入 MongoDB",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    daily_mileage_flow(query_date=args.date, dry_run=args.dry_run)