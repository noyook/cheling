#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""车辆运营技能：当前运营车辆查询 + 运单汇总。

子命令：
  online   查询当前运营车辆（Speed > 0 且 GpsTime 新鲜），含中文地址与当日里程
  summary  统计指定卸货日期的运单车辆与当日里程车辆，输出双向差异清单

数据来源：
  * TOPGPS GetVehicleGpsInfo（NeedAddress=1）：实时 GPS 快照与中文地址
  * TOPGPS GetVehicleMileage（QueryDate=统计日期）：当日里程
  * MongoDB（默认库 TOPGPS、集合 waybill_sync）：电子运单

配置：环境变量优先，其次自动查找 .env（当前目录向上、技能根目录向上）。
     也可用 --env-file 或 VEHICLE_OPS_ENV_FILE 指定配置文件。

用法：
  python scripts/vehicle_ops.py online --minutes 5 --format json
  python scripts/vehicle_ops.py summary --date 2026-11-24 --format text
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

SKILL_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_API_URL = "http://61.183.9.49:8088/topgps/services/TopDataService.ashx"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MONGO_DB = "TOPGPS"
DEFAULT_WAYBILL_COLLECTION = "waybill_sync"

GPS_ACTION = "GetVehicleGpsInfo"
MILEAGE_ACTION = "GetVehicleMileage"
GPS_TIME_FORMATS = ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")
DATE_FORMATS = ("%Y-%m-%d", "%Y%m%d")
OUTPUT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MIN_MILEAGE = 1.0

ENV_HELP = (
    "请检查环境变量或 .env 中的 GPS_API_URL / GPS_USER_ID / GPS_PASSWORD / "
    "MONGO_URI / MONGO_DB，并确认网络可访问 TOPGPS 接口与 MongoDB。"
)


# ---------------------------------------------------------------------------
# 配置加载（零依赖 .env 解析）
# ---------------------------------------------------------------------------

def _parse_env_file(path: Path) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return parsed
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            parsed[key] = value
    return parsed


def _search_dirs() -> Iterator[Path]:
    """当前目录与技能根目录分别向上遍历，去重后依次产出。"""
    seen: Set[Path] = set()
    for base in (Path.cwd(), SKILL_ROOT):
        path = base.resolve()
        while True:
            if path not in seen:
                seen.add(path)
                yield path
            if path == path.parent:
                break
            path = path.parent


def _load_env(explicit: Optional[str]) -> None:
    """加载 .env；真实环境变量始终优先，.env 只补缺。"""
    env_path: Optional[Path] = None
    if explicit:
        env_path = Path(explicit).expanduser().resolve()
        if not env_path.is_file():
            raise RuntimeError(f"--env-file 指定的文件不存在：{env_path}")
    elif os.environ.get("VEHICLE_OPS_ENV_FILE"):
        env_path = Path(os.environ["VEHICLE_OPS_ENV_FILE"]).expanduser().resolve()
        if not env_path.is_file():
            raise RuntimeError(f"VEHICLE_OPS_ENV_FILE 指定的文件不存在：{env_path}")
    else:
        for directory in _search_dirs():
            candidate = directory / ".env"
            if candidate.is_file():
                env_path = candidate
                break

    if env_path is None:
        return
    for key, value in _parse_env_file(env_path).items():
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    api_url: str
    user_id: str
    password: str
    timeout: float
    mongo_uri: str
    mongo_db: str
    waybill_collection: str


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_settings() -> Settings:
    try:
        timeout = float(_env("GPS_TIMEOUT", str(DEFAULT_TIMEOUT)) or DEFAULT_TIMEOUT)
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    return Settings(
        api_url=_env("GPS_API_URL", DEFAULT_API_URL).strip(),
        user_id=_env("GPS_USER_ID", "").strip(),
        password=_env("GPS_PASSWORD", ""),
        timeout=timeout if timeout > 0 else DEFAULT_TIMEOUT,
        mongo_uri=_env("MONGO_URI", "").strip(),
        mongo_db=_env("MONGO_DB", DEFAULT_MONGO_DB).strip() or DEFAULT_MONGO_DB,
        waybill_collection=(
            _env("WAYBILL_COLLECTION", DEFAULT_WAYBILL_COLLECTION).strip()
            or DEFAULT_WAYBILL_COLLECTION
        ),
    )


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def _import_httpx() -> Any:
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "缺少依赖 httpx，请先执行 pip install -r requirements.txt"
        ) from exc
    return httpx


def _import_mongo_client() -> Any:
    try:
        from pymongo import MongoClient  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "缺少依赖 pymongo，请先执行 pip install -r requirements.txt"
        ) from exc
    return MongoClient


def _parse_gps_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for fmt in GPS_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_date(value: Optional[str]) -> datetime:
    """解析 YYYY-MM-DD 或 YYYYMMDD；为空时返回今天。"""
    if value is None or not value.strip():
        return datetime.now()
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"日期格式无效：{value}（支持 YYYY-MM-DD 或 YYYYMMDD）")


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_plate(value: Any) -> str:
    return str(value or "").strip()


def _vehicle_key(plate: Any, color_code: Any) -> Tuple[str, str]:
    return (_normalize_plate(plate), str(color_code or "").strip())


def _call_api(settings: Settings, action: str, **extra: Any) -> List[Dict[str, Any]]:
    """POST 调用 TOPGPS 接口，校验业务码并返回 Data 列表。"""
    if not settings.api_url:
        raise RuntimeError("缺少 GPS_API_URL")
    if not settings.user_id or not settings.password:
        raise RuntimeError("缺少 GPS_USER_ID / GPS_PASSWORD")

    httpx = _import_httpx()
    payload: Dict[str, Any] = {
        "Action": action,
        "UserId": settings.user_id,
        "Pwd": settings.password,
    }
    payload.update(extra)

    try:
        with httpx.Client(timeout=settings.timeout) as client:
            resp = client.post(
                settings.api_url,
                data={"request": json.dumps(payload, ensure_ascii=False)},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"调用 TOPGPS 接口失败：{exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"接口返回内容不是合法 JSON：{exc}") from exc

    if not isinstance(body, dict):
        raise RuntimeError("接口返回结构异常：顶层不是 JSON 对象")
    ret = body.get("Ret", -1)
    if ret != 0:
        raise RuntimeError(f"接口业务失败 Ret={ret} Msg={body.get('Msg', '')}")
    data = body.get("Data") or []
    if not isinstance(data, list):
        raise RuntimeError("接口 Data 字段不是列表")
    return data


def _fetch_mileage_map(
    settings: Settings, query_date: str
) -> Dict[Tuple[str, str], float]:
    """指定日期里程，返回 {(车牌, 颜色码): 里程}；query_date 为 YYYYMMDD。"""
    records = _call_api(settings, MILEAGE_ACTION, QueryDate=query_date, Vehicles=[])
    result: Dict[Tuple[str, str], float] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        mileage = _to_float(rec.get("Mileage"))
        if mileage is None:
            continue
        result[_vehicle_key(rec.get("PlateNum"), rec.get("ColorCode"))] = mileage
    return result


# ---------------------------------------------------------------------------
# 子命令：online —— 当前运营车辆
# ---------------------------------------------------------------------------

def _normalize_vehicle(
    raw: Dict[str, Any], gps_time: datetime, today_mileage: Optional[float]
) -> Dict[str, Any]:
    return {
        "plate_num": _normalize_plate(raw.get("PlateNum")),
        "color_code": raw.get("ColorCode"),
        "gps_time": gps_time.strftime(OUTPUT_TIME_FORMAT),
        "speed": _to_float(raw.get("Speed")),
        "today_mileage": today_mileage,
        "address": raw.get("Address") or "",
        "altitude": raw.get("Altitude"),
        "valid": raw.get("IsGpsValid"),
        "alarm": raw.get("AlarmInfo"),
        "driver": raw.get("DriverName"),
        "license": raw.get("DriverLicense"),
        "org": raw.get("OrgName"),
        "region": raw.get("RegionName"),
        "fuel": raw.get("ResidualFuel"),
        "signal": raw.get("WirelessSignal"),
    }


def query_online_vehicles(settings: Settings, minutes: int = 5) -> Dict[str, Any]:
    """返回最近 minutes 分钟内仍在行驶（Speed > 0）的车辆及当日里程。"""
    now = datetime.now()
    cutoff = now - timedelta(minutes=minutes)
    mileage_date = now.strftime("%Y%m%d")

    raw_list = _call_api(settings, GPS_ACTION, Vehicles=[], NeedAddress="1")
    try:
        mileage_map = _fetch_mileage_map(settings, mileage_date)
    except RuntimeError as exc:
        print(f"警告：当日里程获取失败，里程字段留空（{exc}）", file=sys.stderr)
        mileage_map = {}

    latest: Dict[Tuple[str, str], Tuple[datetime, Dict[str, Any]]] = {}
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        key = _vehicle_key(raw.get("PlateNum"), raw.get("ColorCode"))
        if not key[0]:
            continue
        gps_time = _parse_gps_time(raw.get("GpsTime"))
        if gps_time is None:
            continue
        if key not in latest or gps_time > latest[key][0]:
            latest[key] = (gps_time, raw)

    vehicles: List[Dict[str, Any]] = []
    for key, (gps_time, raw) in latest.items():
        if gps_time < cutoff:
            continue
        speed = _to_float(raw.get("Speed"))
        if speed is None or speed <= 0:
            continue
        vehicles.append(_normalize_vehicle(raw, gps_time, mileage_map.get(key)))
    vehicles.sort(key=lambda item: item["gps_time"], reverse=True)

    return {
        "generated_at": now.strftime(OUTPUT_TIME_FORMAT),
        "source": "TOPGPS GetVehicleGpsInfo + GetVehicleMileage API",
        "window_minutes": minutes,
        "mileage_date": now.strftime("%Y-%m-%d"),
        "count": len(vehicles),
        "vehicles": vehicles,
    }


def _format_online_table(result: Dict[str, Any]) -> str:
    vehicles = result["vehicles"]
    if not vehicles:
        return (
            f"最近 {result['window_minutes']} 分钟内没有在运营的车辆"
            f"（查询时间 {result['generated_at']}）。"
        )
    header = (
        f"当前运营车辆：{result['count']} 辆"
        f"（最近 {result['window_minutes']} 分钟内 Speed > 0，"
        f"查询时间 {result['generated_at']}，"
        f"里程为 {result['mileage_date']} 当日里程）\n"
    )
    columns = [
        ("车牌", "plate_num", 12),
        ("颜色码", "color_code", 6),
        ("最新时间", "gps_time", 20),
        ("速度", "speed", 7),
        ("今日里程", "today_mileage", 10),
        ("驾驶员", "driver", 10),
        ("地址", "address", 40),
    ]
    lines = [header]
    lines.append(" | ".join(title.ljust(width) for title, _, width in columns))
    lines.append("-+-".join("-" * width for _, _, width in columns))
    for item in vehicles:
        cells = []
        for _, key, width in columns:
            value = item.get(key)
            cells.append(str(value if value not in (None, "") else "-").ljust(width))
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _run_online(args: argparse.Namespace) -> int:
    settings = load_settings()
    result = query_online_vehicles(settings, args.minutes)
    if args.format == "table":
        print(_format_online_table(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# 子命令：summary —— 运单与里程比对
# ---------------------------------------------------------------------------

def fetch_waybill_plates(settings: Settings, date_str: str) -> Set[str]:
    """指定卸货日期的运单车牌号集合。"""
    if not settings.mongo_uri:
        raise RuntimeError("缺少 MONGO_URI（summary 子命令需要访问 MongoDB）")
    MongoClient = _import_mongo_client()
    try:
        client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=10000)
        try:
            collection = client[settings.mongo_db][settings.waybill_collection]
            plates = collection.distinct("veh_code", {"unloading_date": date_str})
        finally:
            client.close()
    except Exception as exc:
        raise RuntimeError(f"查询运单数据失败：{exc}") from exc
    return {_normalize_plate(p) for p in plates if _normalize_plate(p)}


def summarize_waybills(
    settings: Settings,
    date_value: Optional[str] = None,
    min_mileage: float = MIN_MILEAGE,
) -> Dict[str, Any]:
    """指定卸货日期的运单车辆与当日里程车辆做双向差集（默认今天）。"""
    day = _parse_date(date_value)
    date_iso = day.strftime("%Y-%m-%d")

    waybill_plates = fetch_waybill_plates(settings, date_iso)
    mileage_map = _fetch_mileage_map(settings, day.strftime("%Y%m%d"))
    mileage_plates = {
        plate
        for (plate, _color), mileage in mileage_map.items()
        if mileage >= min_mileage
    }

    return {
        "generated_at": datetime.now().strftime(OUTPUT_TIME_FORMAT),
        "date": date_iso,
        "min_mileage": min_mileage,
        "waybill_vehicle_count": len(waybill_plates),
        "mileage_vehicle_count": len(mileage_plates),
        "matched_count": len(waybill_plates & mileage_plates),
        "waybill_without_mileage": sorted(waybill_plates - mileage_plates),
        "mileage_without_waybill": sorted(mileage_plates - waybill_plates),
    }


def _format_summary_text(result: Dict[str, Any]) -> str:
    lines = [
        f"运单汇总（卸货日期 {result['date']}，查询时间 {result['generated_at']}）",
        (
            f"卸货运单车辆 {result['waybill_vehicle_count']} 辆；"
            f"该日里程 ≥ {result['min_mileage']:g} 的车辆 {result['mileage_vehicle_count']} 辆；"
            f"两者匹配 {result['matched_count']} 辆"
        ),
        "",
    ]
    for title, key in (
        ("有运单但无里程记录的车辆", "waybill_without_mileage"),
        ("无运单但有里程记录的车辆", "mileage_without_waybill"),
    ):
        items = result[key]
        lines.append(f"{title}（{len(items)} 辆）：")
        if items:
            lines.extend(f"  {plate}" for plate in items)
        else:
            lines.append("  （无）")
        lines.append("")
    return "\n".join(lines).rstrip()


def _run_summary(args: argparse.Namespace) -> int:
    settings = load_settings()
    result = summarize_waybills(settings, args.date)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_summary_text(result))
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="车辆运营技能：当前运营车辆查询与运单汇总"
    )
    parser.add_argument("--version", action="version", version="vehicle-operations 1.0.0")
    sub = parser.add_subparsers(dest="command", required=True)

    p_online = sub.add_parser("online", help="查询当前运营车辆（实时位置、中文地址、当日里程）")
    p_online.add_argument("--minutes", type=int, default=5, help="GpsTime 新鲜度窗口（分钟），默认 5")
    p_online.add_argument("--format", choices=["json", "table"], default="json", help="输出格式，默认 json")
    p_online.add_argument("--env-file", default=None, help="指定 .env 文件路径（可选）")

    p_summary = sub.add_parser("summary", help="统计指定卸货日期的运单车辆与里程车辆差异清单")
    p_summary.add_argument("--date", default=None, help="卸货日期，支持 2026-11-25 或 20261125；默认今天")
    p_summary.add_argument("--format", choices=["text", "json"], default="text", help="输出格式，默认 text")
    p_summary.add_argument("--env-file", default=None, help="指定 .env 文件路径（可选）")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "online" and args.minutes <= 0:
        print("--minutes 必须为正整数", file=sys.stderr)
        return 2

    try:
        _load_env(args.env_file)
        if args.command == "online":
            return _run_online(args)
        return _run_summary(args)
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        print(ENV_HELP, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
