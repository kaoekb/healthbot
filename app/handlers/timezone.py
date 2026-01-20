from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from zoneinfo import ZoneInfo

from app.infra import repo
from app.ui.keyboards import kb_back_main

router = Router()

class TZFSM(StatesGroup):
    waiting = State()

@router.callback_query(F.data == "menu:tz")
async def cb_tz(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TZFSM.waiting)
    await callback.message.edit_text(
        "Введите часовой пояс (IANA), например: Europe/Prague, Europe/Tallinn, Europe/Moscow",
        reply_markup=kb_back_main(),
    )
    await callback.answer()

@router.message(TZFSM.waiting)
async def msg_tz(message: Message, state: FSMContext):
    tz = (message.text or "").strip()
    try:
        ZoneInfo(tz)
    except Exception:
        await message.answer("❌ Не похоже на валидный TZ. Пример: Europe/Prague")
        return

    conn = message.bot.get("db")
    await repo.upsert_user(conn, message.from_user.id, tz)
    await state.clear()
    await message.answer(f"✅ Часовой пояс сохранён: {tz}", reply_markup=kb_back_main())
