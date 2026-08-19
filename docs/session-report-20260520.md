# Waybill-Sync 项目审核评估与部署报告

> 生成时间: 2026-05-20 23:05 CST  
> 服务器: ali-ecs-dev (Ubuntu 22.04 LTS)  
> 项目路径: /root/waybill-sync

---

## 一、项目概览

**waybill-sync** 是一个异步 Python 自动化系统 (v2.1)，用于将物流管理系统的电子运单数据同步到企业微信智能表格，并执行车辆安全检查与自动审批工作流。

**核心价值**：减少人工操作，实现运单数据自动同步 + 安全检查自动审批 + 异常自动通知。

### 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.13+ |
| HTTP 客户端 | httpx.AsyncClient (全异步) |
| CAPTCHA 识别 | ddddocr |
| Token 管理 | PyJWT |
| 调度 | asyncio + 自定义 Scheduler |
| 进程管理 | systemd |
| 包管理 | uv |

---

## 二、系统交互流程图

### 2.1 整体架构

```
systemd 守护进程
    │
    ▼
┌─────────────────┐
│  scheduler.py   │  智能调度器 (单进程常驻)
│  (Tick 每60秒)  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│safety_ │ │ waybill  │
│ sync   │ │ _sync    │
└───┬────┘ └────┬─────┘
    │           │
    └─────┬─────┘
          ▼
┌─────────────────────┐
│  httpx.AsyncClient  │  连接池复用
└────────┬────────────┘
         │
    ┌────┴────────────┐
    ▼                 ▼
┌──────────┐  ┌──────────────┐
│物流运单API│  │企业微信 API  │
│(BladeX)  │  │(智能表格/消息)│
└──────────┘  └──────────────┘
```

### 2.2 调度规则

| 任务 | 高频时段 (06:00-10:00) | 其他时段 | 触发链 |
|------|------------------------|----------|--------|
| **safety_sync**<br>安全检查与审批 | 每 **5 分钟** | 每 **15 分钟** | 审批通过 → 立即触发 waybill_sync |
| **waybill_sync**<br>运单数据同步 | 保底每 **15 分钟** | 保底每 **15 分钟** | — |

### 2.3 安全检查流程

```
获取 Token (CAPTCHA→OCR→Login→JWT)
    │
    ▼
分页获取待审批运单 (taskState=3)
    │
    ▼
并发处理每个运单 (Semaphore=5)
    │
    ├── 查询行车日志 (logType=10 出车前检查)
    │       │
    │       ├── 未找到日志 → 记录需通知车辆
    │       │
    │       └── 找到日志 → 检查 8 项安全指标
    │               │
    │               ├── 全部合格 → 自动审批 (POST /busidispcheck/check)
    │               │
    │               └── 有不合格 → 记录需通知车辆
    │
    ▼
合并发送企业微信通知 (1小时去重)
    │
    ▼
返回是否审批通过 → 触发 waybill_sync
```

### 2.4 运单同步流程

```
获取有效 Token
    │
    ▼
分页获取运单数据 (近7天, 100条/页)
    │
    ▼
清空智能表格 (删除所有现有记录)
    │
    ▼
批量写入新记录 (500条/批, 间隔0.3s)
    │
    ▼
返回同步结果 (总条数)
```

---

## 三、目录结构

```
waybill-sync/
├── .env                          # 环境配置 (凭证)
├── requirements.txt              # Python 依赖
├── systemd/
│   └── waybill-scheduler.service # systemd 服务配置
├── src/
│   ├── main.py                   # CLI 入口 (手动单次执行)
│   ├── orchestrator.py           # 运单同步编排器
│   ├── scripts/
│   │   ├── scheduler.py          # 智能调度器 (主进程)
│   │   └── safety_sync.py        # 安全检查与自动审批
│   ├── core/
│   │   ├── config.py             # 统一配置加载
│   │   ├── constants.py          # 共享常量 (运单状态映射)
│   │   ├── http_client.py        # httpx.AsyncClient 单例
│   │   ├── exceptions.py         # 自定义异常体系
│   │   └── response.py           # ApiResponse 标准化响应
│   ├── api/
│   │   ├── auth_client.py        # 运单系统认证 + Token 管理
│   │   └── wecom_client.py       # 企业微信 API 客户端
│   ├── modules/
│   │   ├── waybill_service.py    # 运单数据获取 (分页)
│   │   └── sheet_service.py      # 智能表格同步 (清空后写入)
│   └── utils/
│       ├── logger.py             # 分模块日志
│       └── notify.py             # 企业微信通知
├── data/                         # 运行时数据
│   ├── waybill-token.json        # JWT Token (带过期时间)
│   ├── wecom-token.json          # 企业微信 Token
│   └── notify-dedup.json         # 通知去重状态
└── logs/                         # 日志文件 (8个模块)
```

---

## 四、外部系统集成

### 4.1 物流运单系统 (BladeX)

| 项目 | 值 |
|------|-----|
| Base URL | `https://183.95.190.189:8681` |
| 认证方式 | CAPTCHA → OCR → Login → JWT (Blade-Auth header) |
| Basic Auth | `Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==` |

**关键端点：**

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/inter/blade-auth/oauth/captcha` | 获取验证码 |
| POST | `/inter/blade-auth/oauth/token` | 登录获取 Token |
| GET | `/inter/qy-server/busibill/page` | 获取运单记录 (分页) |
| GET | `/inter/qy-server/busidispcheck/page` | 获取待审批任务 |
| GET | `/inter/qy-server/mgntvehrunlog/page` | 查询车辆行车日志 |
| POST | `/inter/qy-server/busidispcheck/check` | 提交审批 |

### 4.2 企业微信 API

| 项目 | 值 |
|------|-----|
| Base URL | `https://qyapi.weixin.qq.com/cgi-bin` |
| 认证 | CorpID + CorpSecret → access_token |
| 智能表格 DocID | 配置于 `.env` |
| Sheet ID | `tWSwK1` |

**关键端点：**

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/gettoken` | 获取 access_token |
| POST | `/message/send` | 发送消息 |
| POST | `/wedoc/smartsheet/get_fields` | 获取表格列 |
| POST | `/wedoc/smartsheet/add_fields` | 添加列 |
| POST | `/wedoc/smartsheet/get_records` | 获取记录 |
| POST | `/wedoc/smartsheet/add_records` | 添加记录 |
| POST | `/wedoc/smartsheet/delete_records` | 删除记录 |

---

## 五、架构评估

### 5.1 分层评分

| 层级 | 模块 | 评分 |
|------|------|------|
| 入口层 | scheduler.py, main.py, safety_sync.py | ⭐⭐⭐⭐ |
| 编排层 | orchestrator.py | ⭐⭐⭐⭐⭐ |
| 业务层 | waybill_service.py, sheet_service.py | ⭐⭐⭐⭐ |
| API 层 | auth_client.py, wecom_client.py | ⭐⭐⭐⭐ |
| 核心层 | config.py, http_client.py, exceptions.py, response.py | ⭐⭐⭐⭐⭐ |
| 工具层 | logger.py, notify.py | ⭐⭐⭐⭐ |

### 5.2 优点

1. **清晰的分层架构**：core → api → modules → scripts，职责分离明确
2. **全异步设计**：asyncio + httpx.AsyncClient，连接池复用
3. **统一响应模式**：ApiResponse 提供一致的成功/失败处理
4. **完善的异常体系**：WaybillError → AuthError/TokenError/APIError/WeComError
5. **智能 Token 管理**：文件持久化 + 过期追踪 + 提前续期 + 备份恢复
6. **CAPTCHA 自动识别**：ddddocr + 指数退避重试
7. **智能调度**：时段感知频率切换 + 触发链减少无效调用
8. **分模块日志**：8 个独立日志文件
9. **通知去重**：按车辆独立记录，1 小时窗口期
10. **优雅关闭**：SIGTERM 信号处理 + asyncio.Event
11. **并发控制**：Semaphore 限制并发度 (5)
12. **批量操作**：智能表格 500 条/批写入 + 限流

### 5.3 风险与改进建议

| 优先级 | 问题 | 影响 | 建议 |
|--------|------|------|------|
| **P0** | 智能表格"先清空后写入"策略 | 写入失败导致数据丢失 | 改为 upsert/diff 策略 |
| **P0** | `.env` 包含明文凭证 | 安全风险 | 使用密钥管理服务 |
| **P1** | SSL 验证全局禁用 | MITM 攻击风险 | 将自签名证书加入信任库 |
| **P1** | 审批模板硬编码 | 上游变更导致静默失败 | 改为配置化 |
| **P1** | 日志文件无轮转 | 磁盘空间耗尽 | 使用 RotatingFileHandler |
| **P2** | `src/data/` 与 `data/` 重复 | 状态文件混乱 | 统一使用根目录 data/ |
| **P2** | requirements.txt 含未使用依赖 | 安装时间增加 | 移除 requests 和 pandas |
| **P2** | 无健康检查端点 | 无法外部验证状态 | 添加 health check |

### 5.4 代码质量评分

| 维度 | 评分 |
|------|------|
| 架构设计 | ⭐⭐⭐⭐ |
| 代码规范 | ⭐⭐⭐⭐ |
| 错误处理 | ⭐⭐⭐⭐⭐ |
| 可维护性 | ⭐⭐⭐⭐ |
| 性能 | ⭐⭐⭐⭐⭐ |
| 安全性 | ⭐⭐⭐ |
| 可测试性 | ⭐⭐⭐ |
| 文档 | ⭐⭐⭐⭐ |

---

## 六、依赖分析

```
requirements.txt:
├── httpx>=0.24.0          ✅ 核心使用
├── ddddocr>=1.4.0         ✅ CAPTCHA 识别
├── PyJWT>=2.6.0           ✅ JWT 解析
├── python-dotenv>=0.21.0  ✅ 环境配置
├── requests>=2.28.0       ❌ 未使用 (v2.0 已迁移 httpx)
└── pandas>=1.5.0          ❌ 未使用 (从未导入)
```

---

## 七、远程服务器部署记录

### 7.1 部署前状态

| 检查项 | 结果 |
|--------|------|
| systemd 服务 | ❌ waybill-scheduler.service 不存在 |
| Python 进程 | ❌ 无 scheduler 或 orchestrator 进程 |
| cron 任务 | ⚠️ 有旧版 orchestrator 任务 (每 15 分钟) |
| 最近执行 | ✅ 22:29 手动执行过一次，成功同步 434 条运单 |

### 7.2 执行的操作

#### 步骤 1：删除旧版 cron 配置

```bash
# 删除旧的 orchestrator cron 任务
crontab -l | grep -v 'waybill-orchestrator.lock' | crontab -
```

#### 步骤 2：创建 systemd 服务

```bash
cat > /etc/systemd/system/waybill-scheduler.service << 'EOF'
[Unit]
Description=Waybill Sync Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/waybill-sync
ExecStart=/root/waybill-sync/.venv/bin/python -m src.scripts.scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### 步骤 3：启动并验证

```bash
systemctl daemon-reload
systemctl enable --now waybill-scheduler
```

### 7.3 部署后状态

| 检查项 | 结果 |
|--------|------|
| 服务状态 | ✅ `active (running)` |
| 进程 PID | 8312 |
| 内存占用 | 21.6M |
| 开机自启 | ✅ `enabled` |
| 旧 Cron 配置 | ✅ 已删除 (0 条匹配) |
| 首次执行 | ✅ 23:00 safety_sync → 23:01 waybill_sync (434 条运单) |

### 7.4 常用运维命令

```bash
# 查看服务状态
systemctl status waybill-scheduler

# 查看实时日志
journalctl -u waybill-scheduler -f

# 查看最近 50 条日志
journalctl -u waybill-scheduler -n 50 --no-pager

# 查看最近 1 小时错误日志
journalctl -u waybill-scheduler --since '1 hour ago' -p err --no-pager

# 重启服务
systemctl restart waybill-scheduler

# 停止服务
systemctl stop waybill-scheduler

# 查看项目日志
tail -f /root/waybill-sync/logs/scheduler.log
```

---

## 八、数据模型

### 8.1 Token 存储格式

```json
{
  "access_token": "<JWT string>",
  "expires_time": "2026-05-21 22:03:18",
  "expires_timestamp": 1779372198,
  "username": "13971673595"
}
```

### 8.2 通知去重格式

```json
{
  "鄂ACB379": 1779283356
}
```

### 8.3 运单状态映射

| 代码 | 状态 |
|------|------|
| 10 | 已派单 |
| 11 | 已发车 |
| 20 | 已装车 |
| 30 | 运输中 |
| 40 | 已卸货 |
| 50 | 已完成 |
| 60 | 已回场 |
| 0 | 已作废 |

### 8.4 智能表格列定义

| 列名 | 类型 |
|------|------|
| 车牌号码 | 文本 |
| 驾驶员姓名 | 文本 |
| 驾驶员电话 | 文本 |
| 电子运单编号 | 文本 |
| 运单状态 | 单选 |
| 运单创建日期 | 日期时间 |
| 收货单位名称 | 文本 |
| 计划装货日期 | 日期时间 |
| 计划卸货日期 | 日期时间 |
| 货物详细信息 | 文本 |

---

## 九、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.1 | 2026-05-20 | 智能调度器、触发链、systemd 服务、通知去重按车辆独立 |
| v2.0 | - | 完全异步架构、httpx.AsyncClient、ApiResponse、异常体系 |
| v1.x | - | 同步架构、requests 库 |

---

*报告生成时间: 2026-05-20 23:05 CST*
