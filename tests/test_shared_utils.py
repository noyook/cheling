# -*- coding: utf-8 -*-
"""shared.utils 单元测试：日期工具边界与格式化。"""

from datetime import date, datetime

import pytest

from shared.utils import (
    cn_date,
    format_ts,
    iter_date_range,
    normalize_query_date,
    parse_args_date,
)


# ---------------------------------------------------------------------------
# normalize_query_date
# ---------------------------------------------------------------------------

def test_normalize_compact_kept():
    assert normalize_query_date("20260818") == "20260818"


def test_normalize_iso_to_compact():
    assert normalize_query_date("2026-08-18") == "20260818"


def test_normalize_empty_uses_today():
    today = datetime.now().strftime("%Y%m%d")
    assert normalize_query_date("") == today
    assert normalize_query_date(None) == today


def test_normalize_invalid_raises():
    with pytest.raises(ValueError):
        normalize_query_date("2026/08/18")


def test_normalize_strips_whitespace():
    assert normalize_query_date(" 2026-08-18 ") == "20260818"


# ---------------------------------------------------------------------------
# parse_args_date
# ---------------------------------------------------------------------------

def test_parse_iso():
    assert parse_args_date("2026-08-18") == date(2026, 8, 18)


def test_parse_compact():
    assert parse_args_date("20260818") == date(2026, 8, 18)


def test_parse_invalid_raises():
    with pytest.raises(ValueError):
        parse_args_date("not-a-date")


# ---------------------------------------------------------------------------
# iter_date_range
# ---------------------------------------------------------------------------

def test_iter_range_inclusive_both_ends():
    start = date(2026, 8, 1)
    end = date(2026, 8, 3)
    assert list(iter_date_range(start, end)) == [
        date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3),
    ]


def test_iter_range_single_day():
    d = date(2026, 8, 1)
    assert list(iter_date_range(d, d)) == [d]


def test_iter_range_start_after_end_empty():
    start = date(2026, 8, 3)
    end = date(2026, 8, 1)
    assert list(iter_date_range(start, end)) == []


# ---------------------------------------------------------------------------
# format_ts / cn_date
# ---------------------------------------------------------------------------

def test_format_ts_default():
    dt = datetime(2026, 8, 19, 10, 30, 0)
    assert format_ts(dt) == "2026-08-19 10:30:00"


def test_format_ts_custom():
    dt = datetime(2026, 8, 19, 10, 30, 0)
    assert format_ts(dt, "%Y%m%d") == "20260819"


def test_cn_date_weekday():
    # 2026-08-19 是周三
    assert cn_date(date(2026, 8, 19)) == "2026年8月19日（周三）"