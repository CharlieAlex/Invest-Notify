from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

LOGGER = logging.getLogger(__name__)


def run_interval_job(job, interval_minutes: int) -> None:
    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(job, "interval", minutes=interval_minutes, id="fetch-and-plot")

    LOGGER.info("Scheduler started. interval_minutes=%s", interval_minutes)
    job()
    scheduler.start()
