# -*- coding: utf-8 -*-
"""shared.config 单元测试：.env 解析、取值、Config 构建语义。"""

import pytest

import shared.config as sc


def _write_env(tmp_path, content: str) -> None:
    (tmp_path / ".env").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# load_env_file
# ---------------------------------------------------------------------------

def test_load_env_file_basic(tmp_path):
    _write_env(tmp_path, "FOO=bar\nBAZ=qux\n")
    env = sc.load_env_file([tmp_path])
    assert env == {"FOO": "bar", "BAZ": "qux"}


def test_load_env_file_export_prefix_and_quotes(tmp_path):
    _write_env(tmp_path, 'export FOO="bar baz"\nBAZ=\'qux\'\n')
    env = sc.load_env_file([tmp_path])
    assert env == {"FOO": "bar baz", "BAZ": "qux"}


def test_load_env_file_skips_comments_and_blank(tmp_path):
    _write_env(tmp_path, "# 注释\n\nFOO=bar\n  \n")
    env = sc.load_env_file([tmp_path])
    assert env == {"FOO": "bar"}


def test_load_env_file_first_hit_wins(tmp_path, tmp_path_factory):
    first = tmp_path_factory.mktemp("a")
    second = tmp_path_factory.mktemp("b")
    _write_env(first, "FOO=first\n")
    _write_env(second, "FOO=second\n")
    env = sc.load_env_file([first, second])
    assert env == {"FOO": "first"}


def test_load_env_file_missing_returns_empty(tmp_path):
    assert sc.load_env_file([tmp_path]) == {}


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_env_cache(monkeypatch):
    monkeypatch.setattr(sc, "_env_cache", None)
    monkeypatch.delenv("GET_TEST_KEY", raising=False)


def test_get_missing_returns_default(monkeypatch):
    monkeypatch.setattr(sc, "_env_cache", {})
    assert sc.get("GET_TEST_KEY", "fallback") == "fallback"


def test_get_type_conversion(monkeypatch):
    monkeypatch.setattr(sc, "_env_cache", {"GET_TEST_INT": "42"})
    assert sc.get("GET_TEST_INT", 0, int) == 42


def test_get_type_conversion_failure_returns_default(monkeypatch):
    monkeypatch.setattr(sc, "_env_cache", {"GET_TEST_INT": "abc"})
    assert sc.get("GET_TEST_INT", 0, int) == 0


def test_get_os_environ_priority(monkeypatch):
    monkeypatch.setattr(sc, "_env_cache", {"GET_TEST_KEY": "from_env_file"})
    monkeypatch.setenv("GET_TEST_KEY", "from_os")
    assert sc.get("GET_TEST_KEY") == "from_os"


# ---------------------------------------------------------------------------
# config_from_env
# ---------------------------------------------------------------------------

def test_config_from_env_read_env_collection(monkeypatch):
    monkeypatch.setattr(
        sc, "_env_cache",
        {"MONGO_COLLECTION": "vehicle_gps_buckets"},
    )
    cfg = sc.config_from_env(
        default_collection="vehicle_mileage", read_env_collection=True
    )
    assert cfg.mongo_collection == "vehicle_gps_buckets"


def test_config_from_env_ignores_env_collection(monkeypatch):
    """里程脚本语义：read_env_collection=False 时固定 default_collection。"""
    monkeypatch.setattr(
        sc, "_env_cache",
        {"MONGO_COLLECTION": "vehicle_gps_buckets"},
    )
    cfg = sc.config_from_env(default_collection="vehicle_mileage")
    assert cfg.mongo_collection == "vehicle_mileage"


def test_config_from_env_defaults(monkeypatch):
    monkeypatch.setattr(sc, "_env_cache", {})
    cfg = sc.config_from_env()
    assert cfg.interval == 10
    assert cfg.metrics_port == 9090
    assert cfg.bucket_batch_size == 500