---
name: vehicle-operations
description: 查询当前运营车辆与运单汇总。当用户说“现在运营的车辆”“当前在途车辆”“实时车辆位置”或“统计运单数据”“运单汇总”“昨日运单汇总”时使用。运营查询返回车辆位置、中文地址与当日里程，运单汇总输出有运单无里程和有里程无运单清单。不用于历史轨迹或单票运单查询。
---

# 车辆运营

一个技能覆盖两类实时查询，按用户意图选择子命令：

| 用户意图 | 子命令 |
| --- | --- |
| 现在运营的车辆、当前在途、实时车辆位置 | `online` |
| 统计运单数据、运单汇总、昨日运单汇总 | `summary` |

## 运行前准备

- Python 3.9 及以上。
- 安装依赖：`pip install -r requirements.txt`（含 `httpx`、`pymongo`、`dnspython`）。
- 配置 TOPGPS 凭证与 MongoDB 连接：写入技能根目录 `.env`（参考 `.env.example`），或设置同名环境变量。技能包不包含任何凭证。
- 无需修改代码，脚本会自动从“当前目录向上”和“技能根目录向上”查找 `.env`。

## 执行

在技能根目录执行（以下命令均为相对路径，可整体移动目录）：

```bash
# 当前运营车辆
python scripts/vehicle_ops.py online --minutes 5 --format json

# 当日运单汇总
python scripts/vehicle_ops.py summary --format text

# 指定日期（如昨日）
python scripts/vehicle_ops.py summary --date 2026-11-24 --format text
```

若使用虚拟环境，把 `python` 换成 `.venv/bin/python`（Windows 为 `.venv\Scripts\python.exe`）。

## 配置项

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `GPS_API_URL` | 否 | TOPGPS 服务地址 | 实时接口地址 |
| `GPS_USER_ID` | 是 | 空 | TOPGPS 账号 |
| `GPS_PASSWORD` | 是 | 空 | TOPGPS 密码 |
| `GPS_TIMEOUT` | 否 | `30` | 接口超时秒数 |
| `MONGO_URI` | summary 必填 | 空 | MongoDB 连接串 |
| `MONGO_DB` | 否 | `TOPGPS` | 数据库名 |
| `WAYBILL_COLLECTION` | 否 | `waybill_sync` | 运单集合名 |

也可用 `--env-file /path/to/.env` 或环境变量 `VEHICLE_OPS_ENV_FILE` 指定配置文件。

## 子命令 online

**口径**：`GpsTime` 在最近 `--minutes`（默认 5）内且 `Speed > 0`；同一车辆（`PlateNum` + `ColorCode`）保留最新一条。数据来自 `GetVehicleGpsInfo`（`NeedAddress=1`，返回中文地址）与 `GetVehicleMileage`（当天，取当日里程）。

**参数**：

- `--minutes`：GpsTime 新鲜度窗口，默认 5。未指定时长用 5；“最近 10 分钟/半小时”用 10/30。
- `--format`：`json`（默认）或 `table`。

**输出**：顶层 `generated_at`、`source`、`window_minutes`、`mileage_date`、`count`、`vehicles[]`。每车字段：`plate_num`、`color_code`、`gps_time`、`speed`、`today_mileage`、`address`、`altitude`、`valid`、`alarm`、`driver`、`license`、`org`、`region`、`fuel`、`signal`。

不输出经纬度、车辆状态与行驶方向。回复时先给总数与窗口，再用表格列出车牌、最新时间、速度、今日里程、驾驶员、地址。

## 子命令 summary

**口径**：

1. MongoDB 运单集合中 `unloading_date`（计划卸货日期）等于统计日期的运单，车牌取 `veh_code`；
2. `GetVehicleMileage` 统计日期当天里程 `>= 1` 的车辆，车牌取 `PlateNum`；
3. 求双向差集：`waybill_without_mileage` = 运单车辆 − 里程车辆；`mileage_without_waybill` = 里程车辆 − 运单车辆。

**参数**：

- `--date`：卸货日期，支持 `2026-11-24` 或 `20261124`；默认今天。用户说“昨日”时传昨天日期。
- `--format`：`text`（默认）或 `json`。

**输出**：`text` 含摘要与两个清单；`json` 字段 `generated_at`、`date`、`min_mileage`、`waybill_vehicle_count`、`mileage_vehicle_count`、`matched_count`、`waybill_without_mileage[]`、`mileage_without_waybill[]`。

回复时先说明统计日期与两侧车辆数，再分别列出「有运单但无里程记录的车辆」和「无运单但有里程记录的车辆」；某类为空时写“无”。

## 异常处理

- 缺少凭证、接口调用失败或业务码非 0 时，脚本以非零码退出并输出中文原因与排查提示。
- `online` 的里程接口失败时仅告警并留空里程，不影响实时位置结果。
- 指定日期无运单或无里程车辆时不报错，对应清单为空、计数为 0。
- 详细安装、平台导入与常见问题见 `README.md`。

## 适用范围

本技能用于实时车辆位置与按卸货日期的运单/里程比对；历史轨迹回放、单票运单详情、告警深度分析不在本技能范围。
