"""待审批运单安全检查及审批流程

功能：
1. 获取待审批运单列表
2. 按车牌号 + taskId 查询行车日志（logType=10 出车前检查）
3. 检查是否存在对应运单的出车前检查记录
4. 检查 list 中 8 项 checkPro 的 checkResult 是否全部为 0（合格）
5. 如未做检查，发送企业微信应用通知（文本卡片，1小时去重）
6. 如检查合格，调用审批 API 通过运单
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, TypedDict

from packages.waybill_sync.api.auth_client import TokenManager
from packages.waybill_sync.core.config import (
    API_BASE,
    DATA_DIR,
    WECOM_CORP_ID,
    WECOM_CORP_SECRET,
    WECOM_AGENT_ID,
)
from packages.waybill_sync.core.http_client import HttpClient
from packages.waybill_sync.utils.logger import setup_logger

logger = setup_logger("safety_sync")

# ============== 常量 ==============
# 日志类型: 10=出车前检查
LOG_TYPE_PRE_TRIP = "10"
# 检查状态: 0=合格
CHECK_RESULT_PASS = 0
# 运单状态: 3=待审批
TASK_STATE_PENDING = "3"
# 审批状态: 1=通过
CHECK_STATE_APPROVE = "1"
# 检查类型: 50=车辆与人员资质检查
CHECK_TYPE_VEHICLE_PERSONNEL = "50"

# 审批数据模板（固定部分）
APPROVE_PE_CHECK_DICT = {
    "id": "1893826703426473985",
    "dictId": "6f0c552846583c5aa1e13772aad87213",
    "ownerId": "00000000731a1d550173315462400244",
    "checkType": CHECK_TYPE_VEHICLE_PERSONNEL,
    "checkPro": "车辆与人员资质检查、运输任务合法性检查、车辆技术状况检查；",
    "checkContent": "1. 确认车辆的危险货物运输许可证...",
    "sortNum": 1,
    "note": "",
    "createUser": 1889122310109945900,
    "createTime": "2025-02-24 08:54:06",
    "updateUser": 0,
    "updateTime": None,
    "isDeleted": 0,
}

APPROVE_SELF_CHECK_DATA = {
    "mcert": True,
    "vehicleCcert": True,
    "vehicleGoods": True,
    "vehicleNextCheckDate": True,
    "vehicleInsuredValidDate": True,
    "vehicleRankDate": True,
    "tonnage": True,
    "driverEcertTime": True,
    "escortEcertTime": True,
    "driverEcertMatch": True,
    "escortEcertMatch": True,
    "gps": True,
    "ownerCert": "1",
    "vehCert": "1",
    "vehGoods": "1",
    "annualReview": "1",
    "insuredValid": "1",
    "vehTecRank": "1",
    "overload": "1",
    "driverLic": "1",
    "escortLic": "1",
    "driverQualifica": "1",
    "escorQualifica": "1",
    "gpsterminal": "1",
}


# ============== 类型定义 ==============
class CheckItem(TypedDict):
    checkPro: str
    checkDesc: str
    checkResult: int


class SafetyCheckResult(TypedDict):
    found: bool
    check_items: List[dict]
    all_passed: bool
    failed_items: List[CheckItem]
    pic_urls: List[str]


class ProcessResult(TypedDict):
    task_id: str
    veh_code: str
    driver_name: str
    found_log: bool
    check_items_count: int
    passed_count: int
    failed_count: int
    decision: str
    reason: str
    processed: str


# ============== 配置 ==============
class Config:
    """脚本配置"""

    API_BASE = API_BASE
    WECOM_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
    AGENT_ID = WECOM_AGENT_ID
    CONCURRENCY = 5
    # 通知去重时间间隔（秒）：1小时
    NOTIFY_DEDUP_INTERVAL = 3600
    # 分页大小
    PAGE_SIZE = 10
    # 查询日期范围（天）
    QUERY_DAYS = 7
    # 分页请求间隔（秒）
    REQUEST_DELAY = 0.2
    # 单条处理间隔（秒）
    PROCESS_DELAY = 0.5


# ============== 企业微信通知 ==============
class WeComNotifier:
    """企业微信应用通知"""

    def __init__(self):
        self._token_file = os.path.join(DATA_DIR, "wecom-token.json")
        self._dedup_file = os.path.join(DATA_DIR, "notify-dedup.json")

    async def get_access_token(self) -> str:
        """获取有效的 access_token"""
        if os.path.exists(self._token_file):
            try:
                with open(self._token_file, "r", encoding="utf-8") as f:
                    token_info = json.load(f)
                expires_timestamp = token_info.get("expires_timestamp", 0)
                now = int(datetime.now().timestamp())
                if now < expires_timestamp - 300:
                    return token_info.get("access_token", "")
            except Exception:
                pass

        url = f"{Config.WECOM_BASE}/gettoken"
        params = {"corpid": WECOM_CORP_ID, "corpsecret": WECOM_CORP_SECRET}
        client = HttpClient.get_client()
        try:
            resp = await client.get(url, params=params)
            result = resp.json()
        except Exception as e:
            logger.error(f"获取 WeCom Token 请求失败: {e}")
            return ""

        if result.get("errcode") != 0:
            logger.error(f"获取 WeCom Token 失败: {result.get('errmsg')}")
            return ""

        access_token = result.get("access_token", "")
        expires_in = result.get("expires_in", 7200)
        expires_time = datetime.now() + timedelta(seconds=expires_in)

        token_info = {
            "access_token": access_token,
            "expires_time": expires_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_timestamp": int(expires_time.timestamp()),
        }

        os.makedirs(os.path.dirname(self._token_file), exist_ok=True)
        with open(self._token_file, "w", encoding="utf-8") as f:
            json.dump(token_info, f, ensure_ascii=False, indent=2)

        return access_token

    def _load_dedup_records(self) -> Dict[str, int]:
        """加载去重记录 {veh_code: last_notify_timestamp}"""
        if not os.path.exists(self._dedup_file):
            return {}
        try:
            with open(self._dedup_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 兼容旧格式（全局单条记录）
                if isinstance(data, dict) and "content_hash" in data:
                    return {}
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_dedup_records(self, records: Dict[str, int]):
        """保存去重记录"""
        os.makedirs(os.path.dirname(self._dedup_file), exist_ok=True)
        with open(self._dedup_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def _clean_expired_records(self, records: Dict[str, int]) -> Dict[str, int]:
        """清理过期的去重记录"""
        now = int(datetime.now().timestamp())
        cutoff = now - Config.NOTIFY_DEDUP_INTERVAL
        return {k: v for k, v in records.items() if v > cutoff}

    def get_vehicles_to_notify(self, veh_codes: List[str]) -> List[str]:
        """
        检查哪些车辆应该发送通知（按车辆独立去重）

        Returns:
            需要去通知的车辆列表（不包含已在窗口期内通知过的）
        """
        if not veh_codes:
            return []

        records = self._load_dedup_records()
        records = self._clean_expired_records(records)

        to_notify = []
        now = int(datetime.now().timestamp())

        for veh in veh_codes:
            last_time = records.get(veh, 0)
            if now - last_time >= Config.NOTIFY_DEDUP_INTERVAL:
                to_notify.append(veh)

        skipped = set(veh_codes) - set(to_notify)
        if skipped:
            logger.info(
                f"跳过通知: {len(skipped)} 台车已在 "
                f"{Config.NOTIFY_DEDUP_INTERVAL // 3600} 小时内通知过"
            )

        return to_notify

    def mark_as_sent(self, veh_codes: List[str]):
        """标记车辆通知已发送（用于去重）"""
        records = self._load_dedup_records()
        records = self._clean_expired_records(records)
        now = int(datetime.now().timestamp())

        for veh in veh_codes:
            records[veh] = now

        self._save_dedup_records(records)

    async def send_textcard_notification(
        self, title: str, description: str, url: str = ""
    ) -> bool:
        """发送企业微信文本卡片消息"""
        access_token = await self.get_access_token()
        if not access_token:
            logger.error("无法获取 access_token，跳过通知")
            return False

        api_url = f"{Config.WECOM_BASE}/message/send"
        params = {"access_token": access_token}
        body = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": Config.AGENT_ID,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": "查看更多",
            },
        }

        client = HttpClient.get_client()
        try:
            resp = await client.post(api_url, params=params, json=body)
            result = resp.json()

            if result.get("errcode") == 0:
                logger.info("文本卡片通知发送成功 -> @all")
                return True
            else:
                logger.warning(f"发送通知失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            logger.error(f"发送通知异常: {e}")
            return False


# ============== 运单系统客户端 ==============
class WaybillClient:
    """运单系统 API 客户端"""

    BASE_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
        "Authorization": "Basic ZGdzLXdlYjpkZ3Nfd2ViX3NlY3JldA==",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": f"{API_BASE}/dgsqy/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "macOS",
    }

    def __init__(self, token: str):
        self.token = token

    def _build_headers(self) -> Dict[str, str]:
        headers = dict(self.BASE_HEADERS)
        headers["Blade-Auth"] = f"bearer {self.token}"
        return headers

    async def get_pending_list(
        self, start_date: str, end_date: str, page: int = 1, size: int = 10
    ) -> dict:
        url = f"{API_BASE}/inter/qy-server/busidispcheck/page"
        params = {
            "vehCode": "",
            "updateUser": "",
            "taskState": TASK_STATE_PENDING,
            "taskId": "",
            "current": page,
            "size": size,
            "createTimeStart": start_date,
            "createTimeEnd": end_date,
        }
        client = HttpClient.get_client()
        try:
            resp = await client.get(url, headers=self._build_headers(), params=params)
            return resp.json()
        except Exception as e:
            logger.error(f"获取待审批列表失败 (page={page}): {e}")
            return {"data": {"records": [], "total": 0}}

    async def get_vehicle_log(
        self, veh_code: str, start_date: str, end_date: str, task_id: str
    ) -> Dict[str, Any]:
        url = f"{API_BASE}/inter/qy-server/mgntvehrunlog/page"
        params = {
            "vehCode": veh_code.replace("鄂", ""),
            "vehtype": "1",
            "timeType": "1",
            "startDate": f"{start_date} 00:00:00",
            "endDate": f"{end_date} 23:59:59",
            "current": 1,
            "size": 20,
        }
        client = HttpClient.get_client()
        try:
            resp = await client.get(url, headers=self._build_headers(), params=params)
            data = resp.json()
        except Exception as e:
            logger.error(f"获取车辆日志失败 [{veh_code}]: {e}")
            return {"data": {}, "found": False}

        records = data.get("data", {}).get("records", [])
        for rec in records:
            if rec.get("taskId") == task_id and rec.get("logType") == LOG_TYPE_PRE_TRIP:
                return {"data": rec, "found": True}
        return {"data": {}, "found": False}

    async def approve_waybill(self, check_data: dict) -> dict:
        url = f"{API_BASE}/inter/qy-server/busidispcheck/check"
        headers = self._build_headers()
        headers["Content-Type"] = "application/json;charset=UTF-8"
        headers["Origin"] = API_BASE

        client = HttpClient.get_client()
        try:
            resp = await client.post(url, headers=headers, json=check_data)
            return resp.json()
        except Exception as e:
            logger.error(f"审批请求失败: {e}")
            return {"code": 500, "msg": f"请求异常: {e}"}


# ============== 安全检查处理器 ==============
class SafetyChecker:
    """安全检查处理器"""

    @staticmethod
    def check_pre_trip(log_data: dict) -> SafetyCheckResult:
        result: SafetyCheckResult = {
            "found": False,
            "check_items": [],
            "all_passed": False,
            "failed_items": [],
            "pic_urls": [],
        }

        if not log_data:
            return result

        result["found"] = True
        check_list = log_data.get("list", [])
        result["check_items"] = check_list

        if check_list:
            failed: List[CheckItem] = []
            for item in check_list:
                if item.get("checkResult") != CHECK_RESULT_PASS:
                    failed.append(
                        {
                            "checkPro": item.get("checkPro", ""),
                            "checkDesc": item.get("checkDesc", ""),
                            "checkResult": item.get("checkResult", -1),
                        }
                    )
            result["failed_items"] = failed
            result["all_passed"] = len(failed) == 0

        pic_url = log_data.get("picUrl", "")
        if pic_url:
            result["pic_urls"] = [
                url.strip() for url in pic_url.split(",") if url.strip()
            ]

        return result


# ============== 分页获取 ==============
async def fetch_all_records(
    client: WaybillClient,
    start_date: str,
    end_date: str,
    page_size: int = Config.PAGE_SIZE,
) -> List[dict]:
    """异步分页获取所有待审批运单"""
    all_records: List[dict] = []
    page = 1

    while True:
        data = await client.get_pending_list(start_date, end_date, page, page_size)
        records = data.get("data", {}).get("records", [])
        total = data.get("data", {}).get("total", 0)

        if not records:
            break

        all_records.extend(records)
        logger.info(f"第 {page} 页: {len(records)} 条 (累计 {len(all_records)}/{total})")

        if len(all_records) >= total:
            break

        page += 1
        await asyncio.sleep(Config.REQUEST_DELAY)

    return all_records


# ============== 主流程 ==============
async def process_waybill(
    client: WaybillClient,
    pending: dict,
    start_date: str,
    end_date: str,
) -> ProcessResult:
    """处理单个运单的安全检查和审批"""
    task_id = pending.get("taskId", "")
    disp_check_id = pending.get("dispCheckId", "")
    veh_code = pending.get("vehCode", "")
    driver_name = pending.get("driverName", "")

    result: ProcessResult = {
        "task_id": task_id,
        "veh_code": veh_code,
        "driver_name": driver_name,
        "found_log": False,
        "check_items_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "decision": "unknown",
        "reason": "",
        "processed": "待处理",
    }

    try:
        # 1. 获取车辆运行日志（按车牌号 + taskId）
        log_resp = await client.get_vehicle_log(
            veh_code, start_date, end_date, task_id
        )
        log_data = log_resp.get("data", {})
        found = log_resp.get("found", False)

        result["found_log"] = found

        if not found:
            result["decision"] = "notify"
            result[
                "reason"
            ] = f"未找到运单 {task_id} 的出车前检查记录(logType={LOG_TYPE_PRE_TRIP})"
            result["processed"] = "已记录: 缺少出车前检查"
            logger.warning(f"[{veh_code}] {result['reason']}")
            return result

        # 2. 安全检查
        safety = SafetyChecker.check_pre_trip(log_data)
        check_items = safety["check_items"]
        failed_items = safety["failed_items"]

        result["check_items_count"] = len(check_items)
        result["passed_count"] = len(check_items) - len(failed_items)
        result["failed_count"] = len(failed_items)

        if not safety["all_passed"]:
            failed_names = [
                f"{item['checkPro']}(异常码:{item['checkResult']})"
                for item in failed_items
            ]
            result["decision"] = "reject"
            result["reason"] = f"出车前检查未通过: {', '.join(failed_names)}"
            result["processed"] = "已驳回: 检查项不合格"
            logger.warning(f"[{veh_code}] {result['reason']}")
            return result

        # 3. 检查全部通过，调用审批 API
        result["decision"] = "approve"
        result["reason"] = "出车前检查全部合格"
        logger.info(f"[{veh_code}] 检查通过，准备审批...")

        approve_data = {
            "checkNote": "",
            "checkState": CHECK_STATE_APPROVE,
            "dispCheckId": disp_check_id,
            "taskId": task_id,
            "peoCheckdicts": [dict(APPROVE_PE_CHECK_DICT)],
            "selfCheckData": dict(APPROVE_SELF_CHECK_DATA),
        }

        approve_resp = await client.approve_waybill(approve_data)

        if approve_resp.get("code") == 200:
            result["processed"] = "已自动审批"
            logger.info(f"[{veh_code}] 审批成功")
        else:
            result["processed"] = f"审批失败: {approve_resp.get('msg', '未知错误')}"
            logger.warning(f"[{veh_code}] 审批失败: {approve_resp}")

        return result

    except Exception as e:
        logger.error(f"处理运单失败 {task_id}: {e}")
        result["decision"] = "error"
        result["reason"] = str(e)
        result["processed"] = "处理失败"
        return result


async def process_waybills_concurrently(
    client: WaybillClient,
    records: List[dict],
    start_date: str,
    end_date: str,
    concurrency: int = Config.CONCURRENCY,
) -> List[ProcessResult]:
    """并发处理运单，使用信号量控制并发数"""
    semaphore = asyncio.Semaphore(concurrency)

    async def _process_with_limit(pending: dict) -> ProcessResult:
        async with semaphore:
            result = await process_waybill(client, pending, start_date, end_date)
            await asyncio.sleep(Config.PROCESS_DELAY)
            return result

    tasks = [_process_with_limit(rec) for rec in records]
    return await asyncio.gather(*tasks)


def print_summary(results: List[ProcessResult]):
    """打印处理结果汇总"""
    logger.info("=" * 60)
    logger.info("处理结果汇总")
    logger.info("=" * 60)

    counts = {
        "approve": sum(1 for r in results if r["decision"] == "approve"),
        "reject": sum(1 for r in results if r["decision"] == "reject"),
        "notify": sum(1 for r in results if r["decision"] == "notify"),
        "error": sum(1 for r in results if r["decision"] == "error"),
    }

    logger.info(f"  通过:   {counts['approve']} 条")
    logger.info(f"  驳回:   {counts['reject']} 条")
    logger.info(f"  通知:   {counts['notify']} 条")
    logger.info(f"  错误:   {counts['error']} 条")
    logger.info("=" * 60)

    logger.info("详细结果:")
    for i, r in enumerate(results, 1):
        status_icon = (
            "[PASS]"
            if r["decision"] == "approve"
            else "[REJECT]"
            if r["decision"] == "reject"
            else "[NOTIFY]"
            if r["decision"] == "notify"
            else "[ERROR]"
        )
        logger.info(f"{status_icon} [{r['veh_code']}] {r['driver_name']}")
        logger.info(f"   任务ID: {r['task_id']}")
        logger.info(f"   决定: {r['decision']}")
        logger.info(f"   原因: {r['reason']}")
        logger.info(f"   状态: {r['processed']}")
        if r["check_items_count"] > 0:
            logger.info(
                f"   检查项: {r['passed_count']}/{r['check_items_count']} 合格"
            )
        logger.info("")


async def main() -> bool:
    """主入口
    
    Returns:
        bool: 是否执行了自动审批（有审批通过）
    """
    logger.info("=" * 60)
    logger.info("待审批运单安全检查及审批流程")
    logger.info("=" * 60)

    shanghai_tz = timezone(timedelta(hours=8))
    now = datetime.now(shanghai_tz)
    start_date = (now - timedelta(days=Config.QUERY_DAYS)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    logger.info(f"[时间] {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"[日期范围] {start_date} ~ {end_date}")

    approved_any = False

    try:
        # Step 1: 获取 Token
        logger.info("[Step 1] 获取 Token...")
        token_manager = TokenManager()
        token = await token_manager.get_token()
        logger.info("Token 获取成功")

        # Step 2: 初始化客户端
        logger.info("[Step 2] 初始化客户端...")
        client = WaybillClient(token)
        notifier = WeComNotifier()
        logger.info("客户端初始化完成")

        # Step 3: 获取待审批列表
        logger.info("[Step 3] 获取待审批运单列表...")
        all_records = await fetch_all_records(client, start_date, end_date)
        logger.info(f"获取到 {len(all_records)} 条待审批运单")

        if not all_records:
            logger.warning("无待审批运单，任务结束")
            return False

        # Step 4: 并发处理每个运单
        logger.info("[Step 4] 安全检查及审批...")
        results = await process_waybills_concurrently(
            client, all_records, start_date, end_date
        )

        # 统计审批结果
        approve_count = sum(1 for r in results if r["decision"] == "approve")
        approved_any = approve_count > 0

        # 收集未做检查的车辆
        notify_vehicles = [
            r["veh_code"] for r in results if r["decision"] == "notify"
        ]

        # Step 5: 发送合并通知
        if notify_vehicles:
            logger.info(
                f"[Step 5] 发送企业微信通知({len(notify_vehicles)}台车)..."
            )

            vehicles_to_notify = notifier.get_vehicles_to_notify(notify_vehicles)

            if vehicles_to_notify:
                current_time = datetime.now(shanghai_tz).strftime("%Y-%m-%d %H:%M:%S")
                veh_codes_str = "; ".join(vehicles_to_notify)

                title = "以下车辆未做出车检查："
                description = f"{veh_codes_str}\n{current_time}"

                success = await notifier.send_textcard_notification(
                    title=title,
                    description=description,
                    url=f"{Config.API_BASE}/dgsqy/",
                )

                if success:
                    notifier.mark_as_sent(vehicles_to_notify)
                    logger.info(f"通知发送成功: {veh_codes_str}")
                else:
                    logger.error("通知发送失败")
            else:
                logger.info(
                    f"跳过通知: 所有车辆已在 "
                    f"{Config.NOTIFY_DEDUP_INTERVAL // 3600} 小时内通知过"
                )
        else:
            logger.info("[Step 5] 无需发送通知（所有车辆检查合格）")

        # 打印结果汇总
        print_summary(results)

        return approved_any

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        raise
    finally:
        await HttpClient.close()


async def safety_sync_main() -> bool:
    """安全检查主入口（等价 main），供 Prefect flow 调用。"""
    return await main()


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
