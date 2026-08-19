#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Waybill sync system entry point"""
import argparse
import asyncio
import sys

from packages.waybill_sync.core.exceptions import WaybillError
from packages.waybill_sync.core.http_client import HttpClient
from packages.waybill_sync.orchestrator import sync_waybill_data
from packages.waybill_sync.utils.notify import Notifier


async def main(days: int = 7):
    """Main entry point."""
    print("=" * 60)
    print("主控编排器 - 运单数据处理流程")
    print("=" * 60)

    try:
        result = await sync_waybill_data(days=days)
        if result.success:
            total = result.data["waybills"]
            print(f"\n✅ 获取成功: {total} 条运单")
            print("=" * 60)
            print("✅ 主控流程完成")
            print("=" * 60)
        else:
            print(f"\n❌ 流程失败: {result.error}")
            sys.exit(1)

    except WaybillError as e:
        error_msg = f"流程异常: {e.message}"
        await Notifier().alarm(error_msg)
        print(f"❌ {error_msg}\n")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(130)

    finally:
        await HttpClient.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="waybill_sync",
        description="Waybill sync system entry point",
    )
    parser.add_argument("--days", type=int, default=7, help="查询回看天数（默认 7）")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    asyncio.run(main(days=args.days))
