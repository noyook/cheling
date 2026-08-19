# -*- coding: utf-8 -*-
"""
通用工具层：日期工具（从 topgps_common 迁移，语义逐字保留）+ 通用格式化。

- normalize_query_date：规范化日期为 %Y%m%d（API 要求），支持紧凑/ISO 两种输入，空值取今天
- parse_args_date：CLI 日期参数 -> date 对象
- iter_date_range：[start, end] 闭区间日期迭代
- format_ts / cn_date：通用时间戳格式化与中文日期输出
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterator, Optional

DATE_COMPACT = "%Y%m%d"
DATE_ISO = "%Y-%m-%d"

# 中文星期
_WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def normalize_query_date(query_date: Optional[str]) -> str:
    """将日期参数规范化为 %Y%m%d 紧凑格式（API 要求）。空值取今天（本地时区）。"""
    if not query_date:
        return datetime.now().strftime(DATE_COMPACT)
    text = query_date.strip()
    for fmt in (DATE_COMPACT, DATE_ISO):
        try:
            return datetime.strptime(text, fmt).strftime(DATE_COMPACT)
        except ValueError:
            continue
    raise ValueError(
        f"无法解析日期 '{query_date}'，支持格式：{DATE_COMPACT} 或 {DATE_ISO}"
    )


def parse_args_date(text: str) -> date:
    """解析 CLI 日期参数（%Y-%m-%d 或 %Y%m%d）为 date 对象。"""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return datetime.strptime(text, "%Y%m%d").date()


def iter_date_range(start: date, end: date) -> Iterator[date]:
    """生成 [start, end] 闭区间内的全部日期（含两端）。"""
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def format_ts(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """通用时间戳格式化。"""
    return dt.strftime(fmt)


def cn_date(dt: date) -> str:
    """中文日期输出，如 2026年8月19日（周三）。"""
    return f"{dt.year}年{dt.month}月{dt.day}日（{_WEEKDAYS_CN[dt.weekday()]}）"


__all__ = [
    "DATE_COMPACT", "DATE_ISO",
    "normalize_query_date", "parse_args_date", "iter_date_range",
    "format_ts", "cn_date",
]