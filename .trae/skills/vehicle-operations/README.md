# 车辆运营技能包（vehicle-operations）

版本：1.0.0
许可：内部使用

通过 TOPGPS 实时接口查询当前运营车辆，并按卸货日期统计运单与里程的车辆差异。技能包为纯 Python 实现，不依赖特定项目仓库，可整体复制或导入其他支持 Skill 的 AI 平台。

---

## 一、功能说明

| 子命令 | 用途 | 触发示例 |
| --- | --- | --- |
| `online` | 查询当前运营车辆、中文地址、当日里程 | “现在运营的车辆”“当前在途车辆”“实时车辆位置” |
| `summary` | 按卸货日期统计有运单无里程、有里程无运单的车辆 | “统计运单数据”“运单汇总”“昨日运单汇总” |

### online

- 数据源：`GetVehicleGpsInfo`（实时 GPS，`NeedAddress=1` 返回中文地址）+ `GetVehicleMileage`（当日里程）。
- 判定：`GpsTime` 在最近 N 分钟内且 `Speed > 0`；同车同颜色码取最新一条。
- 输出：总数、查询窗口、每车车牌、颜色码、最新时间、速度、当日里程、中文地址、驾驶员等。

### summary

- 数据源：MongoDB 运单集合（默认 `TOPGPS.waybill_sync`）+ `GetVehicleMileage`。
- 逻辑：运单车辆集合与当日里程 ≥ 1 的车辆集合求双向差集。
- 输出：两侧车辆数、匹配数、「有运单但无里程记录」「无运单但有里程记录」两份清单。

---

## 二、目录结构

```text
vehicle-operations/
├── SKILL.md              # 技能入口说明（AI 平台读取）
├── README.md             # 安装、导入、使用与排障
├── requirements.txt      # Python 依赖声明
├── .env.example          # 配置模板（不含真实凭证）
└── scripts/
    └── vehicle_ops.py    # 全部功能实现，无硬编码绝对路径
```

---

## 三、安装步骤

### 1. 解压

把分发包解压到目标位置，得到 `vehicle-operations/` 目录。

### 2. 安装依赖

```bash
cd vehicle-operations
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Windows：

```bat
cd vehicle-operations
py -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```

要求 Python 3.9+；已在 Python 3.12 / 3.13 独立环境验证。

### 3. 配置凭证

```bash
cp .env.example .env
# 编辑 .env，填写 GPS_USER_ID / GPS_PASSWORD / MONGO_URI
```

或直接使用环境变量（优先级高于 `.env`）：

```bash
export GPS_USER_ID="你的账号"
export GPS_PASSWORD="你的密码"
export MONGO_URI="mongodb://..."       # summary 需要
export MONGO_DB="TOPGPS"               # 可选
export WAYBILL_COLLECTION="waybill_sync"  # 可选
```

配置文件查找顺序：

1. `--env-file` 指定的文件；
2. `VEHICLE_OPS_ENV_FILE` 指定的文件；
3. 当前工作目录逐级向上查找 `.env`；
4. 技能根目录逐级向上查找 `.env`。

真实环境变量始终优先于 `.env`。技能包不包含任何凭证。

### 4. 自检

```bash
.venv/bin/python scripts/vehicle_ops.py --version
.venv/bin/python scripts/vehicle_ops.py online --minutes 5 --format table
```

---

## 四、使用方式

```bash
# 当前运营车辆（JSON，适合程序处理）
.venv/bin/python scripts/vehicle_ops.py online --minutes 5 --format json

# 当前运营车辆（表格，适合直接阅读）
.venv/bin/python scripts/vehicle_ops.py online --minutes 5 --format table

# 当日运单汇总
.venv/bin/python scripts/vehicle_ops.py summary --format text

# 指定日期（昨日 / 历史日期）
.venv/bin/python scripts/vehicle_ops.py summary --date 2026-11-24 --format text

# 指定配置文件
.venv/bin/python scripts/vehicle_ops.py summary --env-file /path/to/.env
```

`online --minutes` 默认 5；用户说“最近半小时”时传 `30`。
`summary --date` 默认今天，支持 `YYYY-MM-DD` 与 `YYYYMMDD`。

---

## 五、导入到 AI 平台

### Trae

把整个 `vehicle-operations/` 目录放到以下任一位置，平台会自动发现 `SKILL.md`：

- 项目级：`<项目根>/.trae/skills/vehicle-operations/`
- 全局级：平台的全局 skills 目录（以当前 Trae 版本文档为准）

### Claude Code / Anthropic Agent Skills

解压到用户级技能目录：

```bash
mkdir -p ~/.claude/skills
unzip vehicle-operations-1.0.0.zip -d ~/.claude/skills/
```

确保最终路径为 `~/.claude/skills/vehicle-operations/SKILL.md`。`SKILL.md` 使用标准 `name` / `description` 前置元数据。

### 其他平台

- 支持 `SKILL.md` 约定的平台：按平台技能目录导入整个文件夹。
- 不支持 Skill 约定的平台：让 Agent 阅读 `SKILL.md` 作为操作说明，并按“使用方式”执行脚本即可；也可把本 README 作为工具说明接入。

> 导入后请确认平台执行命令时的当前目录为技能根目录，或使用脚本的绝对路径；脚本会自动定位技能根目录下的 `.env`。

---

## 六、常见问题排查

### 1. 提示缺少依赖 httpx / pymongo

```text
执行失败：缺少依赖 httpx，请先执行 pip install -r requirements.txt
```

确认已激活正确的虚拟环境，并重新执行 `pip install -r requirements.txt`。

### 2. 提示缺少 GPS_USER_ID / GPS_PASSWORD

`.env` 不在查找路径内，或变量名为空。可在技能根目录创建 `.env`，或显式传入 `--env-file`。注意环境变量优先级最高，若系统里存在空值变量会覆盖 `.env`。

### 3. 接口返回 `Ret=1`

TOPGPS 账号或密码错误。检查 `GPS_USER_ID` / `GPS_PASSWORD`，确认账号未被停用。

### 4. 调用接口超时 / 连接失败

检查网络是否能访问 `GPS_API_URL`，必要时调大 `GPS_TIMEOUT`。若服务地址变更，更新 `GPS_API_URL`。

### 5. summary 提示缺少 MONGO_URI

`summary` 需要访问 MongoDB；`online` 不需要。填写 `MONGO_URI`（支持 `mongodb://` 与 `mongodb+srv://`）后重试。使用 SRV 连接串时依赖 `dnspython`，已包含在 `requirements.txt`。

### 6. MongoDB 连接超时（ServerSelectionTimeoutError）

确认 `MONGO_URI` 可达、数据库允许当前机器 IP、账号有目标库读权限。云数据库需在控制台放行出口 IP。

### 7. online 有车辆但“今日里程”为空

实时位置接口正常、里程接口失败时，脚本会告警并留空里程，不影响位置结果。优先检查凭证与 `GPS_TIMEOUT`。

### 8. 查询结果为空

- `online`：确认 `--minutes` 窗口内确有车辆行驶；夜间或全部停驶时为空属正常。
- `summary`：确认 `--date` 日期存在运单，且当日里程数据已生成；若里程表未更新，会表现为“有运单但无里程”。

### 9. 输出中文乱码（Windows）

在终端执行 `chcp 65001` 切换到 UTF-8，或使用 Windows Terminal。

### 10. 如何切换数据库或集合

设置 `MONGO_DB`、`WAYBILL_COLLECTION` 即可，无需改代码。若运单字段名不同（非 `veh_code` / `unloading_date`），需要调整 `scripts/vehicle_ops.py` 中的字段名。

### 11. 凭证会随包分发吗

不会。分发包只包含 `.env.example` 模板，不包含 `.env`。请勿把真实 `.env` 打入压缩包或提交到代码仓库。

---

## 七、验证清单（分发前）

- [x] 在干净虚拟环境中 `pip install -r requirements.txt` 成功。
- [x] `online` 与 `summary` 均可正常返回。
- [x] 从任意工作目录调用可自动定位 `.env`。
- [x] 包内无 `/home/...` 等绝对路径、无项目内部模块引用。
- [x] 包内不含真实凭证。
- [x] 缺少凭证、接口失败、缺少 MongoDB 配置时均有中文提示。

---

## 八、变更记录

- 1.0.0：首个可移植版本。移除对项目 `shared` / `packages` 的依赖与硬编码路径，改为环境变量 + `.env` 自动查找；新增依赖声明、配置模板、安装/导入/排障文档与分发包。
