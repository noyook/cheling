# AGENTS.md

cheling = TOPGPS（车辆 GPS / 里程采集）+ waybill-sync（运单同步 / 安全检查）合并 Monorepo。统一基础设施（shared 层）与统一调度（tasks/scheduler.py）。

## 运行环境

- 一律用 `uv run python -m ...` 运行（Python 3.13，uv 管理依赖）。直接执行包内脚本文件会因 `No module named 'packages'` 失败——必须以 `-m` 方式运行。
- `.env` 解析是 shared/config.py 内手写零依赖逻辑（`load_env_file`），支持 `export KEY=VALUE` 前缀、引号剥离、注释/空行跳过；cwd 优先逐级向上查找第一个 `.env`。

## 架构

```
tasks/scheduler.py           统一调度器（推荐唯一常驻入口，systemd: cheling-scheduler）
  ├─ daily_mileage  每日 02:00 -> packages.topgps.core.batch_mileage（抓昨日）
  ├─ safety_sync    时段感知 5/15min -> packages.waybill_sync.scripts.safety_sync
  └─ waybill_sync   保底 15min -> packages.waybill_sync.orchestrator
                    （safety_sync 审批通过 -> 联动立即触发 waybill_sync）
packages/topgps/core/gps_poller.py   GPS 常驻守护（独立 systemd: gps-poller）
```

- 调度器 CLI：`--jobs` 选任务、`--now` 立即执行一次、`--dry-run` 看计划；SIGTERM/SIGINT 优雅关闭。新增定时工作流 = 在 scheduler.py 的 `build_jobs()` 加一条 `Job` 记录。
- 各脚本仍可独立运行（gps_poller / mileage_fetcher / batch_mileage / safety_sync / main）。

## 配置陷阱（.env）

- `GPS_USER_ID` / `GPS_PASSWORD` / `GPS_API_URL`：TOPGPS 接口凭证；`MONGO_URI` / `MONGO_DB=TOPGPS`。
- **`MONGO_COLLECTION=vehicle_gps_buckets` 是 gps_poller 专用**。里程脚本（mileage_fetcher / batch_mileage / daily_mileage）刻意不读取该变量、固定写 `vehicle_mileage` 集合——这不是 bug，不要"修复"（曾因此把数据写进错误集合并在错误集合上建索引失败）。该差异由 shared.config 的 `config_from_env(read_env_collection=...)` 控制（poller=True，里程=False）。

## 脚本

- `tasks/scheduler.py`：统一调度器。单进程常驻 asyncio，Tick 60s；时段感知 + 触发链；日志走 shared/logging。
- `gps_poller.py`：GPS 守护。轮询 `GetVehicleGpsInfo`（实时 GPS 点，过滤 speed==0 与超 90 秒旧点），按（车牌, 小时）分桶批量写入；内嵌 /metrics(9090)、`--once` 单次、信号优雅关闭。
- `mileage_fetcher.py`：单日里程。`GetVehicleMileage(query_date, cfg=None)`（日期支持 `20260815` 或 `2026-08-15`）；`--dry-run` 只查不写。
- `batch_mileage.py`：批量里程。并发（默认 5）循环；失败自动重试并写入 `mileage_failed_dates.txt`，`--retry-file` 补跑、`--resume` 断点续跑。
- `safety_sync.py`：安全检查。`safety_sync_main()` 返回 bool（True=本次有审批通过），触发链依据。

## API 约定

- POST 表单，`request` 字段内嵌 JSON：`{"Action":"GetVehicleMileage","UserId":...,"Pwd":...,"QueryDate":"20260815","Vehicles":[]}`；`Action` 区分接口。
- 响应 `{"Ret":0,"Msg":"","Data":[...]}`，`Ret != 0` 即业务失败（抛 ValueError）。
- 日期参数一律 `%Y%m%d`；CLI 同时接受 `%Y-%m-%d` 自动转换。

## MongoDB 数据模型（库 TOPGPS）

- `vehicle_mileage`：唯一索引 `(query_date, plate_num, color_code)`，upsert 幂等写入（同日重复执行 = 更新非重复）。
- `vehicle_gps_buckets`：分桶结构，每文档 = 每车每 15 分钟窗口，`points` 数组 + `latest_point`（窗口内最新点，查询最新位置直接读取，无需 $unwind）；`hour` 为 15 分钟窗口边界（与 GpsTime 同基准，注意并非 UTC，勿做时区转换）。写入为 bulk_write upsert（同窗口追加 `$push` points、`$inc` point_count、`$set` latest_point/updated_at），幂等。索引：唯一 `(plate_num, color_code, hour)`（防重复写入），另保留 `(plate_num, hour)` 与 `(hour)`。

## 约定

- 日志 / 注释 / 输出全部中文；代码标识符英文。
- 新采集脚本复用 shared.config 的 `load_env_file` / `config_from_env` / shared.utils 的 `normalize_query_date` 模式，不重复造轮子。
- 测试：`uv run pytest`（shared 层 + scheduler 触发链）。
- 运维：`.env` 变更后 `sudo systemctl restart cheling-scheduler gps-poller`。