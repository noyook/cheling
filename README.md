# cheling

TOPGPS 与 waybill-sync 合并后的 Monorepo：统一基础设施（共享配置/日志/异常/Mongo 访问）与 Prefect Cloud 任务编排。

## 结构

- `packages/topgps/`：GPS 轮询与车辆里程采集
- `packages/waybill_sync/`：运单同步与企业微信智能表格
- `shared/`：统一配置/日志/异常/Mongo/工具层
- `tasks/`：Prefect flow 定义
- `scripts/`：运行入口
- `deploy/`：Prefect 部署清单

## 快速开始

（文档终稿见任务 36）