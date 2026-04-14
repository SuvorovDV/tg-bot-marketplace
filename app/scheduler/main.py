from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import get_session, init_db
from app.services.billing import charge_daily_placement

log = logging.getLogger(__name__)


async def run_daily_job() -> None:
    async with get_session() as s:
        result = await charge_daily_placement(s)
    log.info("daily billing: %s", result)


async def run_scheduler() -> None:
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_job, CronTrigger(hour=3, minute=0))
    scheduler.start()
    log.info("scheduler started; daily billing at 03:00 UTC")
    while True:
        await asyncio.sleep(3600)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
