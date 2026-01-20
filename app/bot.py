from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers import start, menu, measure, timezone, reminders, reports

def create_bot(token: str) -> Bot:
    return Bot(token=token)

def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(measure.router)
    dp.include_router(timezone.router)
    dp.include_router(reminders.router)
    dp.include_router(reports.router)
    return dp
