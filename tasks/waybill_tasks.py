# -*- coding: utf-8 -*-
"""waybill Prefect flows：安全检查审批 + 运单同步。"""

from __future__ import annotations

from prefect import flow
from prefect.events import emit_event

from packages.waybill_sync.orchestrator import sync_waybill_data
from packages.waybill_sync.scripts.safety_sync import safety_sync_main


@flow(log_prints=True)
async def safety_sync_flow() -> dict:
    """待审批运单安全检查：本次有审批通过时发射事件触发运单同步。"""
    approved = await safety_sync_main()
    if approved:
        emit_event(
            event="waybill.approval.approved",
            resource={
                "prefect.resource.id": "waybill.task",
                "prefect.resource.name": "waybill",
            },
        )
    return {"approved": approved}


@flow(log_prints=True)
async def waybill_sync_flow(days: int = 7) -> dict:
    """运单同步：同步近 days 天运单到智能表格。"""
    result = await sync_waybill_data(days=days)
    return {"success": result.success, "data": result.data}