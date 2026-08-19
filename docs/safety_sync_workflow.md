# 运单安全检查及审批流程

## 工作流图

```mermaid
flowchart TD
    Start([开始]) --> Step1[获取Token]
    Step1 --> Step2[初始化客户端<br/>WaybillClient + WeComNotifier]
    Step2 --> Step3[获取待审批运单列表<br/>GET /busidispcheck/page<br/>taskState=3, 近7天]
    
    Step3 --> HasRecords{有待审批运单?}
    HasRecords -->|否| End([任务结束])
    HasRecords -->|是| Step4[遍历每个运单]
    
    Step4 --> GetLog[查询行车日志<br/>GET /mgntvehrunlog/page<br/>vehCode + taskId + logType=10]
    
    GetLog --> LogFound{找到日志?}
    LogFound -->|否| MarkNotify[标记: notify<br/>原因: 缺少出车前检查]
    LogFound -->|是| CheckItems[安全检查<br/>检查8项checkPro的checkResult]
    
    CheckItems --> AllPass{全部合格?<br/>checkResult=0}
    AllPass -->|否| MarkReject[标记: reject<br/>原因: 检查项不合格]
    AllPass -->|是| Approve[调用审批API<br/>POST /busidispcheck/check]
    
    Approve --> ApproveResult{审批成功?}
    ApproveResult -->|是| MarkApproved[标记: approve<br/>状态: 已自动审批]
    ApproveResult -->|否| MarkApproveFail[标记: approve<br/>状态: 审批失败]
    
    MarkNotify --> CollectVehicles[收集需通知车辆]
    MarkReject --> CollectVehicles
    MarkApproved --> CollectVehicles
    MarkApproveFail --> CollectVehicles
    
    CollectVehicles --> HasNotify{有需通知车辆?}
    HasNotify -->|否| PrintSummary[打印结果汇总]
    HasNotify -->|是| DedupCheck{1小时内已发送?<br/>MD5去重}
    
    DedupCheck -->|是| SkipNotify[跳过通知]
    DedupCheck -->|否| BuildMsg[构建文本卡片消息<br/>标题: 📢 以下车辆未做出车检查：<br/>内容: 车号; 车号<br/>时间]
    
    BuildMsg --> SendNotify[发送企业微信通知<br/>POST /message/send<br/>touser: @all]
    
    SendNotify --> SendResult{发送成功?}
    SendResult -->|是| MarkSent[标记已发送<br/>保存去重记录]
    SendResult -->|否| LogFail[记录发送失败]
    
    MarkSent --> PrintSummary
    LogFail --> PrintSummary
    SkipNotify --> PrintSummary
    
    PrintSummary --> End
```

## 流程说明

| 步骤 | 说明 | API |
|------|------|-----|
| 1 | 获取Token | TokenManager |
| 2 | 初始化客户端 | - |
| 3 | 获取待审批列表 | `GET /busidispcheck/page` |
| 4 | 查询行车日志 | `GET /mgntvehrunlog/page` |
| 5 | 安全检查 | 本地逻辑（checkResult=0为合格） |
| 6 | 审批通过 | `POST /busidispcheck/check` |
| 7 | 发送通知 | `POST /message/send` |

## 判定逻辑

### 出车前检查判定
```
if 无行车日志(logType=10):
    → notify (发送企业微信通知)
elif 8项检查中有checkResult≠0:
    → reject (驳回)
else:
    → approve (调用审批API)
```

### 通知去重逻辑
```
content_hash = MD5(sorted(veh_codes))
if 相同hash且间隔<3600秒:
    → 跳过
else:
    → 发送并记录
```

## 通知消息格式

**标题**: 📢 以下车辆未做出车检查：

**内容**:
```
鄂ACB379; 鄂A12345
2026-05-20 17:00:00
```

**接收人**: @all（全员）
