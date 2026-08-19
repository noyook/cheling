# cheling

TOPGPS（GPS 采集与车辆里程）与 waybill-sync（运单同步与安全检查）合并后的 Monorepo。核心诉求：**数据互通**（共享配置/日志/异常/Mongo 访问）与**统一任务编排**（自研调度器）。

## 目录结构

```
cheling/
├── pyproject.toml            # 统一依赖管理（uv）
├── .env                      # 统一环境变量（不入库）
├── packages/                 # 核心代码包
│   ├── topgps/               # GPS 轮询与车辆里程采集
│   │   └── core/
│   │       ├── gps_poller.py        # GPS 常驻守护（10s 轮询 + 分桶 + metrics）
│   │       ├── mileage_fetcher.py   # 单日里程采集
│   │       ├── batch_mileage.py     # 批量里程采集（并发 + 失败重试）
│   │       └── common.py            # 公共 Config/load_config/日期工具
│   └── waybill_sync/         # 运单同步与企业微信智能表格
│       ├── core/             # 配置/HTTP 客户端/异常/响应
│       ├── api/              # 运单认证、企业微信 API
│       ├── modules/          # 运单服务、智能表格
│       ├── scripts/safety_sync.py   # 安全检查与审批
│       ├── orchestrator.py   # 运单同步编排
│       └── main.py           # CLI 入口
├── shared/                   # 共享模块
│   ├── config.py             # 统一配置加载（.env 合并）
│   ├── mongo.py              # 统一 Mongo 客户端 + 索引初始化
│   ├── logging.py            # 统一日志
│   ├── exceptions.py         # 统一异常体系
│   └── utils.py              # 日期工具
├── tasks/scheduler.py        # 统一调度器（JOBS 注册表 + 时段感知 + 触发链）
├── scripts/                  # 运行入口（run_topgps / run_waybill / run_all）
├── systemd/                  # 服务单元（cheling-scheduler / gps-poller）
├── tests/                    # pytest 测试（shared + scheduler）
├── docs/                     # 迁移归档文档
├── data/                     # 运行时数据（token/去重状态，不入库）
├── logs/                     # 运行时日志（不入库）
└── mileage_failed_dates.txt  # 里程失败清单（运行时产物，不入库）
```

## 快速开始

```bash
uv sync                          # 安装依赖（Python 3.13+）
uv run pytest                    # 运行测试
uv run python -m tasks.scheduler --dry-run   # 查看调度计划
```

## 运行方式

### 统一调度器（推荐）

```bash
uv run python -m tasks.scheduler            # 常驻运行全部任务
uv run python -m tasks.scheduler --now      # 立即执行一次全部任务后退出
uv run python -m tasks.scheduler --jobs safety_sync --now   # 只跑单个任务
```

作为 systemd 服务（生产推荐）：

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cheling-scheduler gps-poller
journalctl -u cheling-scheduler -f   # 查看调度器日志
journalctl -u gps-poller -f          # 查看 GPS 守护日志
```

### 单任务手动执行

```bash
uv run python -m packages.topgps.core.gps_poller          # GPS 常驻守护
uv run python -m packages.topgps.core.gps_poller --once   # 单次轮询
uv run python -m packages.topgps.core.mileage_fetcher --dry-run --date 2026-08-18
uv run python -m packages.topgps.core.batch_mileage --days 1
uv run python -m packages.waybill_sync.main --days 7      # 运单同步
uv run python -m packages.waybill_sync.scripts.safety_sync
```

scripts/ 目录提供等价短入口（统一 `-m` 运行模式）：

```bash
uv run python -m scripts.run_topgps --once
uv run python -m scripts.run_waybill --days 7
uv run python -m scripts.run_all     # 服务状态与运维指引
```

> 注意：包内脚本需以 `python -m packages.xxx` 方式运行（包结构下直接执行脚本文件会因 import 路径失败）。

## 调度规则

| 任务 | 规则 | 说明 |
|------|------|------|
| **daily_mileage** | 每日 02:00（Asia/Shanghai） | 抓昨日里程入库 vehicle_mileage（幂等 upsert） |
| **safety_sync** | 06:00-10:00 每 5 分钟，其余每 15 分钟 | 待审批运单安全检查与审批 |
| **waybill_sync** | 保底每 15 分钟 | 同步近 7 天运单到智能表格；safety_sync 审批通过时联动立即执行 |

## 配置项（.env）

| 变量 | 说明 |
|------|------|
| `GPS_API_URL` / `GPS_USER_ID` / `GPS_PASSWORD` / `GPS_TIMEOUT` / `GPS_INTERVAL` / `GPS_NEED_ADDRESS` | TOPGPS 接口凭证与轮询参数 |
| `MONGO_URI` / `MONGO_DB` | MongoDB 连接与库名 |
| `MONGO_COLLECTION` | **仅 GPS poller 使用**（vehicle_gps_buckets）；里程脚本固定写 vehicle_mileage，不读此变量 |
| `BUCKET_FLUSH_INTERVAL` / `BUCKET_BATCH_SIZE` / `QUEUE_MAX_SIZE` / `METRICS_PORT` | 分桶与指标参数 |
| `WAYBILL_API_BASE` / `WAYBILL_USERNAME` / `WAYBILL_PASSWORD` / `TOKEN_BUFFER_SECONDS` | 运单系统凭证 |
| `WECOM_CORP_ID` / `WECOM_CORP_SECRET` / `WECOM_AGENT_ID` | 企业微信凭证 |
| `SMARTSHEET_SHEET_ID` / `SMARTSHEET_DOC_URL` / `DTJK_DOCID` | 智能表格定位 |

## MongoDB 数据模型（库 TOPGPS）

- `vehicle_mileage`：唯一索引 `(query_date, plate_num, color_code)`，upsert 幂等写入。
- `vehicle_gps_buckets`：每文档 = 每车每 15 分钟窗口（points 数组 + latest_point）；唯一索引 `(plate_num, color_code, hour)`，另保留 `(plate_num, hour)` 与 `(hour)`。

## 测试

```bash
uv run pytest          # shared 层 + scheduler 触发链，35 项
```

## 运维要点

- `.env` 变更后需重启 cheling-scheduler 与 gps-poller：`sudo systemctl restart cheling-scheduler gps-poller`。
- 调度器信号：`systemctl stop`（SIGTERM 优雅关闭）。
- 里程失败补跑：`uv run python -m packages.topgps.core.batch_mileage --retry-file`。