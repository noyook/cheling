#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一运行引导：打印 scheduler / gps-poller 服务状态与运维指引。

自研调度方案（原 Prefect Cloud 计划因免费层不支持 process work pool 而放弃）：
  * cheling-scheduler : 统一调度器（daily_mileage / safety_sync / waybill_sync + 联动）
  * gps-poller        : GPS 常驻采集
"""

import subprocess
import sys

SERVICES = [
    ("cheling-scheduler", "统一调度器（daily_mileage/safety_sync/waybill_sync）"),
    ("gps-poller", "GPS 常驻采集"),
]


def systemd_status(service: str) -> str:
    try:
        out = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True,
        )
        return out.stdout.strip() or out.stderr.strip()
    except FileNotFoundError:
        return "systemd 不可用"


def main() -> int:
    print("=" * 60)
    print("cheling 统一运行指引")
    print("=" * 60)
    for service, desc in SERVICES:
        status = systemd_status(service)
        print(f"  {service:18s} [{status}]  {desc}")
    print("-" * 60)
    print("手动启动：")
    print("  uv run python -m tasks.scheduler --dry-run   # 查看调度计划")
    print("  uv run python -m tasks.scheduler --now       # 立即执行一次全部任务")
    print("  uv run python -m tasks.scheduler --jobs safety_sync --now")
    print("  uv run python -m packages.topgps.core.gps_poller --once")
    print("-" * 60)
    print("systemd 运维：")
    print("  sudo systemctl enable --now cheling-scheduler gps-poller")
    print("  journalctl -u cheling-scheduler -f")
    print("  journalctl -u gps-poller -f")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())