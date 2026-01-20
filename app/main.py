from __future__ import annotations

import asyncio
import os
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.settings import load_settings
from app.logging_setup import setup_logging
from app.bot import create_bot, create_dispatcher
from app.infra.db import connect, init_db
from app.infra import repo
from app.services.reminders import schedule_all_from_db

log = logging.getLogger(__name__)

async def main():
    settings = load_settings()
    setup_logging(settings.log_level)

    data_dir = settings.data_dir
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    db_path = os.path.join(data_dir, "healthbot.sqlite3")

    conn = await connect(db_path)
    await init_db(conn)

    bot = create_bot(settings.bot_token)
    dp = create_dispatcher()

    # attach shared objects
    bot["db"] = conn
    bot["data_dir"] = data_dir
    bot["default_tz"] = settings.default_timezone

    scheduler = AsyncIOScheduler()
    scheduler.start()
    bot["scheduler"] = scheduler

    # warm-up: ensure any known users are scheduled
    await schedule_all_from_db(scheduler, bot, conn)

    log.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
