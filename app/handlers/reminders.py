from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.ui.keyboards import kb_slots, SLOTS, kb_back_main
from app.infra import repo
from app.services import reminders as reminder_service

router = Router()

class SlotsFSM(StatesGroup):
    picking = State()

@router.callback_query(F.data == "menu:reminders")
async def cb_reminders(callback: CallbackQuery, state: FSMContext):
    conn = callback.bot.get("db")
    user_id = callback.from_user.id
    selected = set(await repo.list_reminder_slots(conn, user_id))
    await state.set_state(SlotsFSM.picking)
    await state.update_data(selected=list(selected))
    await callback.message.edit_text("Выбери слоты времени для напоминаний:", reply_markup=kb_slots(selected))
    await callback.answer()

@router.callback_query(SlotsFSM.picking, F.data.startswith("slot:"))
async def cb_slot_pick(callback: CallbackQuery, state: FSMContext):
    payload = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("selected", []))

    if payload == "save":
        conn = callback.bot.get("db")
        scheduler: AsyncIOScheduler = callback.bot.get("scheduler")
        user_id = callback.from_user.id

        # ensure user exists with tz
        user_tz = await repo.get_user_timezone(conn, user_id) or callback.bot.get("default_tz")
        await repo.upsert_user(conn, user_id, user_tz)

        await repo.set_reminder_slots(conn, user_id, sorted(selected))
        # reschedule jobs
        await reminder_service.cancel_user_jobs(scheduler, user_id)
        for hm in sorted(selected):
            await reminder_service.schedule_one(scheduler, callback.bot, conn, user_id, user_tz, hm)

        await state.clear()
        await callback.message.edit_text("✅ Напоминания сохранены.", reply_markup=kb_back_main())
        await callback.answer()
        return

    # toggle slot
    if payload in SLOTS:
        if payload in selected:
            selected.remove(payload)
        else:
            selected.add(payload)

    await state.update_data(selected=list(selected))
    await callback.message.edit_reply_markup(reply_markup=kb_slots(selected))
    await callback.answer()

@router.callback_query(F.data == "menu:stop")
async def cb_stop(callback: CallbackQuery):
    conn = callback.bot.get("db")
    scheduler: AsyncIOScheduler = callback.bot.get("scheduler")
    user_id = callback.from_user.id
    await repo.disable_all_slots(conn, user_id)
    await reminder_service.cancel_user_jobs(scheduler, user_id)
    await callback.message.edit_text("🛑 Напоминания отключены.", reply_markup=kb_back_main())
    await callback.answer()
