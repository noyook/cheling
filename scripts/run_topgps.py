#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOPGPS GPS daemon 入口：等价 `uv run python -m packages.topgps.core.gps_poller`。

支持透传 gps_poller 的全部参数（--once、--interval 等）。
"""

import sys

from packages.topgps.core.gps_poller import main


if __name__ == "__main__":
    sys.exit(main())