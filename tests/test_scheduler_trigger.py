# -*- coding: utf-8 -*-
"""scheduler 触发链单元测试：safety_sync 返回 True 时联动触发 waybill_sync。

run_loop 启动时会按 interval_fn 重置全部 next_run，因此测试用
interval_fn 控制到期时间：safety 立即到期（0 秒），waybill 1 小时后（3600 秒）。
"""

import asyncio

import pytest

from tasks.scheduler import Job, now_shanghai, run_loop


def _make_jobs(safety_result, calls):
    safety_job = Job(
        name="safety_sync",
        description="",
        interval_fn=lambda now: 0,  # 立即到期
        coro=lambda: asyncio.sleep(0, result=safety_result),
    )
    waybill_job = Job(
        name="waybill_sync",
        description="",
        interval_fn=lambda now: 3600,  # 1 小时后
        coro=lambda: calls.append("waybill"),
    )
    return [safety_job, waybill_job]


def _run_loop_short(jobs, seconds=0.3):
    stop = asyncio.Event()

    async def _run():
        task = asyncio.create_task(run_loop(jobs, stop))
        await asyncio.sleep(seconds)
        stop.set()
        await task

    asyncio.run(_run())


def test_trigger_chain_on_approval():
    """safety_sync 返回 True → waybill_sync 的 next_run 被联动置为现在。"""
    calls = []
    safety_job, waybill_job = _make_jobs(True, calls)

    _run_loop_short([safety_job, waybill_job])

    assert calls == [], "联动只重置 next_run，waybill 应在下一 tick 才执行"
    assert waybill_job.next_run <= now_shanghai(), (
        "safety_sync 审批通过后 waybill_sync 的 next_run 应被联动置为现在"
    )


def test_no_trigger_without_approval():
    """safety_sync 返回 False → waybill_sync 的 next_run 不被联动修改。"""
    calls = []
    safety_job, waybill_job = _make_jobs(False, calls)

    _run_loop_short([safety_job, waybill_job])

    assert calls == [], "未审批通过时 waybill_sync 不应执行"
    assert waybill_job.next_run > now_shanghai(), (
        "未审批通过时 waybill_sync 的 next_run 应保持 1 小时后"
    )