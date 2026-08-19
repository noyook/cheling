# -*- coding: utf-8 -*-
"""shared.mongo 单元测试：mock 索引初始化调用与客户端缺失 URI 行为。"""

from unittest.mock import MagicMock

import pytest

import shared.mongo as sm


class _FakeCollection:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def create_index(self, keys, **kwargs):
        self.calls.append((keys, kwargs))
        return "idx"


class _FakeDB(dict):
    def __getitem__(self, key):
        if key not in self:
            self[key] = _FakeCollection(key)
        return super().__getitem__(key)


def test_ensure_indexes_creates_all_four():
    db = _FakeDB()
    sm.ensure_indexes(db)
    mileage_idx = db["vehicle_mileage"].calls
    gps_idx = db["vehicle_gps_buckets"].calls

    assert len(mileage_idx) == 1
    keys, kwargs = mileage_idx[0]
    assert keys == [("query_date", 1), ("plate_num", 1), ("color_code", 1)]
    assert kwargs["unique"] is True

    assert len(gps_idx) == 3
    unique_keys, unique_kwargs = gps_idx[0]
    assert unique_keys == [("plate_num", 1), ("color_code", 1), ("hour", 1)]
    assert unique_kwargs["unique"] is True
    # 历史查询索引非唯一
    for _, kwargs in gps_idx[1:]:
        assert "unique" not in kwargs or kwargs["unique"] is False


def test_get_mongo_client_missing_uri_raises(monkeypatch):
    """MONGO_URI 缺失（含 .env 缓存置空）时应抛 ValueError。"""
    import shared.config as sc

    monkeypatch.setattr(sc, "_env_cache", {})
    monkeypatch.delenv("MONGO_URI", raising=False)
    sm._sync_client = None
    with pytest.raises(ValueError):
        sm.get_mongo_client()


def test_collection_constants():
    assert sm.VEHICLE_MILEAGE == "vehicle_mileage"
    assert sm.VEHICLE_GPS_BUCKETS == "vehicle_gps_buckets"
    assert sm.MONGO_SELECT_TIMEOUT_MS == 10000