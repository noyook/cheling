"""Waybill data service"""
import asyncio
import logging
from typing import Dict, Any, List

from packages.waybill_sync.core.config import API_BASE
from packages.waybill_sync.core.constants import BILL_STATE_MAP
from packages.waybill_sync.core.exceptions import APIError
from packages.waybill_sync.core.http_client import request
from packages.waybill_sync.core.response import ApiResponse
from packages.waybill_sync.utils.logger import setup_logger

logger = setup_logger("waybill_service")

# Base headers for waybill API requests (without Blade-Auth)
WAYBILL_HEADERS = {
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
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/147.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "macOS",
}


class WaybillService:
    """Waybill data service."""

    def __init__(self, token: str):
        self.token = token
        self.headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with auth token."""
        headers = dict(WAYBILL_HEADERS)
        headers["Blade-Auth"] = f"bearer {self.token}"
        return headers

    async def fetch_page(
        self,
        start_date: str,
        end_date: str,
        page: int = 1,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Fetch a single page of waybill data.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            page: Page number
            size: Page size

        Returns:
            Dict with records and total

        Raises:
            APIError: On request failure
        """
        url = f"{API_BASE}/inter/qy-server/busibill/page"
        params = {
            "current": page,
            "size": size,
            "consignName": "",
            "vehCode": "",
            "rangeDate": f"{start_date},{end_date}",
            "billState": "10,11,20,30,40,50,60,0",
            "billNo": "",
            "driverEscortId": "",
            "pdfState": "",
            "startDate": start_date,
            "endDate": end_date,
            "flag": "",
            "approvalState": "",
        }

        try:
            resp = await request("GET", url, headers=self.headers, params=params, verify=False)
            data = resp.json()
        except Exception as e:
            raise APIError(f"获取运单失败: {e}")

        if not isinstance(data, dict):
            raise APIError(f"运单响应类型错误: {type(data)}")

        if data.get("code") != 200:
            msg = data.get("msg", data.get("error", "未知错误"))
            raise APIError(f"获取运单错误: {msg}")

        return data.get("data", {})

    async def fetch_all(
        self,
        start_date: str,
        end_date: str,
        size: int = 100,
        max_pages: int = 100,
    ) -> ApiResponse:
        """Fetch all waybill data with pagination.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            size: Page size
            max_pages: Maximum pages to fetch

        Returns:
            ApiResponse with records and total
        """
        logger.info(f"开始获取运单: {start_date} ~ {end_date}")
        all_records: List[Dict[str, Any]] = []
        page = 1

        try:
            while page <= max_pages:
                data = await self.fetch_page(start_date, end_date, page, size)
                records = data.get("records", [])
                total = data.get("total", 0)

                if not records:
                    break

                all_records.extend(records)
                logger.info(
                    f"第 {page} 页: 获取 {len(records)} 条 "
                    f"(累计 {len(all_records)}/{total})"
                )

                if len(all_records) >= total:
                    break

                page += 1
                await asyncio.sleep(0.2)

            logger.info(f"获取完成: 共 {len(all_records)} 条")
            return ApiResponse.ok(data={"records": all_records, "total": len(all_records)})

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"获取运单异常: {e}")

    @staticmethod
    def parse_records(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Parse waybill records into readable format.

        Args:
            records: Raw waybill data

        Returns:
            List of parsed records with Chinese keys
        """
        result = []
        for item in records:
            bill_state = str(item.get("billState", ""))
            result.append({
                "运单号": item.get("billNo", ""),
                "车牌号": item.get("vehCode", ""),
                "承运人": item.get("consignName", ""),
                "驾驶员": item.get("driverName", ""),
                "联系人": item.get("driverTel", ""),
                "货物": item.get("goodsInfo", ""),
                "运费(元)": item.get("freight", ""),
                "运单状态": BILL_STATE_MAP.get(bill_state, f"未知({bill_state})"),
                "发车时间": item.get("departTime", ""),
                "到达时间": item.get("arriveTime", ""),
                "实际里程(km)": item.get("actualMileage", ""),
                "创建时间": item.get("createTime", ""),
            })
        return result
