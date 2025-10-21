# =============================
# app/scheduler.py
# =============================
from __future__ import annotations
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from . import storage as db

async def reminder_loop(bot: Bot):
    while True:
        try:
            users = await db.list_users_enabled()
            for u in users:
                tzname = u.get("user_timezone") or "Europe/Moscow"
                now_local = datetime.now(ZoneInfo(tzname))
                hhmm = now_local.strftime("%H:%M")
                times = await db.list_schedule_times(u["user_id"])
                if hhmm not in times:
                    continue
                date_local = now_local.strftime("%Y-%m-%d")
                if not await db.should_remind(u["user_id"], hhmm, date_local):
                    continue
                metric = u.get("metric", "both")
                simult = bool(u.get("simultaneous", 1))
                if metric == "sugar":
                    text = "Напоминание измерений: пора измерить <b>сахар в крови</b>."
                elif metric == "bp":
                    text = "Напоминание измерений: пора измерить <b>давление</b>."
                else:
                    text = ("Напоминание: пора измерить <b>сахар и давление</b>." if simult else "Напоминание: пора измерить <b>сахар</b> и <b>давление</b>.")
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ввести данные", callback_data="enter_from_reminder")]])
                await bot.send_message(u["user_id"], text, reply_markup=kb)
                await db.mark_reminded(u["user_id"], hhmm, date_local)
        except Exception:
            pass
        await asyncio.sleep(30)
# =============================
