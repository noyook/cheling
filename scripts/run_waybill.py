#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""waybill 同步 CLI 入口：等价原 `python -m src.main`。

支持 --days 回看天数参数。
"""

import asyncio
import sys

from packages.waybill_sync.main import build_parser, main


if __name__ == "__main__":
    args = build_parser().parse_args()
    asyncio.run(main(days=args.days))