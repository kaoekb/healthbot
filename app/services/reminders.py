from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from aiogram import Bot

from app.infra import repo
from app.services.timeutils import next_fire_local, now_utc_iso
from app.ui.keyboards import kb_measure_choice

log = logging.getLogger(__name__)

def _job_id(user_id: int, time_hm: str) -> str:
    return f"reminder:{user_id}:{time_hm}"

async def schedule_one(scheduler: AsyncIOScheduler, bot: Bot, conn, user_id: int, user_tz: str, time_hm: str) -> None:
    tz = ZoneInfo(user_tz)
    dt_local = next_fire_local(user_tz, time_hm)
    run_date_utc = dt_local.astimezone(timezone.utc)

    job_id = _job_id(user_id, time_hm)

    # Replace existing job idempotently
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    scheduler.add_job(
        func=send_and_reschedule,
        trigger=DateTrigger(run_date=run_date_utc),
        id=job_id,
        kwargs={
            "scheduler": scheduler,
            "bot": bot,
            "conn": conn,
            "user_id": user_id,
            "user_tz": user_tz,
            "time_hm": time_hm,
        },
        replace_existing=True,
        misfire_grace_time=60 * 10,  # 10 minutes
    )
    log.info("Scheduled reminder user=%s time=%s at_utc=%s", user_id, time_hm, run_date_utc.isoformat())

async def send_and_reschedule(*, scheduler: AsyncIOScheduler, bot: Bot, conn, user_id: int, user_tz: str, time_hm: str) -> None:
    tz = ZoneInfo(user_tz)
    local_now = datetime.now(tz)
    slot_date = local_now.date().isoformat()

    # Idempotency: ensure one send per day+slot
    if await repo.reminder_already_sent(conn, user_id, slot_date, time_hm):
        log.info("Reminder already sent user=%s slot=%s %s", user_id, slot_date, time_hm)
    else:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"⏰ Напоминание: замер в {time_hm}. Что внесём?",
                reply_markup=kb_measure_choice(),
            )
            await repo.mark_reminder_sent(conn, user_id, slot_date, time_hm, now_utc_iso())
        except Exception:
            log.exception("Failed to send reminder to user=%s", user_id)

    # Reschedule next occurrence
    await schedule_one(scheduler, bot, conn, user_id, user_tz, time_hm)

async def schedule_all_from_db(scheduler: AsyncIOScheduler, bot: Bot, conn) -> None:
    rows = await repo.list_all_enabled_slots(conn)
    for user_id, user_tz, time_hm in rows:
        await schedule_one(scheduler, bot, conn, user_id, user_tz, time_hm)

async def cancel_user_jobs(scheduler: AsyncIOScheduler, user_id: int) -> None:
    # APScheduler doesn't support prefix remove directly; iterate
    for job in scheduler.get_jobs():
        if job.id.startswith(f"reminder:{user_id}:"):
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass
