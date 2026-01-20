from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from app.ui.keyboards import kb_measure_choice, kb_skip_back
from app.domain.parsing import parse_sugar, parse_bp
from app.services.measurements import add_sugar, add_bp
from app.infra import repo

router = Router()

class MeasureFSM(StatesGroup):
    choosing = State()
    sugar = State()
    bp = State()
    both_sugar = State()
    both_bp = State()

@router.callback_query(F.data == "menu:measure")
async def cb_measure_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Что будем вводить?", reply_markup=kb_measure_choice())
    await callback.answer()

@router.callback_query(F.data.in_(["m:sugar","m:bp","m:both","m:skip"]))
async def cb_measure_choice(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    await callback.answer()
    if data == "m:skip":
        await callback.message.edit_text("Ок, пропускаем.", reply_markup=kb_measure_choice())
        return

    user_id = callback.from_user.id
    conn = callback.bot.get("db")
    user_tz = await repo.get_user_timezone(conn, user_id) or callback.bot.get("default_tz")

    await state.update_data(user_tz=user_tz)

    if data == "m:sugar":
        await state.set_state(MeasureFSM.sugar)
        await callback.message.edit_text(
            "Введите сахар. Примеры: 5.6 или 5,6",
            reply_markup=kb_skip_back("msugar"),
        )
    elif data == "m:bp":
        await state.set_state(MeasureFSM.bp)
        await callback.message.edit_text(
            "Введите давление: САД ДАД [пульс]. Примеры: 120 80 60, 120/80, 120:80:60",
            reply_markup=kb_skip_back("mbp"),
        )
    else:
        await state.set_state(MeasureFSM.both_sugar)
        await callback.message.edit_text(
            "Сначала сахар. Примеры: 5.6 или 5,6 (можно 'пропустить')",
            reply_markup=kb_skip_back("mboth_sugar"),
        )

@router.callback_query(F.data == "msugar:skip")
async def cb_skip_sugar(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Пропущено. Что дальше?", reply_markup=kb_measure_choice())
    await callback.answer()

@router.callback_query(F.data == "mbp:skip")
async def cb_skip_bp(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Пропущено. Что дальше?", reply_markup=kb_measure_choice())
    await callback.answer()

@router.callback_query(F.data == "mboth_sugar:skip")
async def cb_skip_both_sugar(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MeasureFSM.both_bp)
    await callback.message.edit_text(
        "Ок, сахар пропущен. Теперь давление: 120 80 60 или 120/80",
        reply_markup=kb_skip_back("mboth_bp"),
    )
    await callback.answer()

@router.callback_query(F.data == "mboth_bp:skip")
async def cb_skip_both_bp(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Ок, всё пропущено. Что дальше?", reply_markup=kb_measure_choice())
    await callback.answer()

@router.message(MeasureFSM.sugar)
async def msg_sugar(message: Message, state: FSMContext):
    data = await state.get_data()
    user_tz = data["user_tz"]
    conn = message.bot.get("db")

    try:
        val = parse_sugar(message.text or "")
    except Exception as e:
        await message.answer(f"❌ {e}")
        return

    await add_sugar(conn, message.from_user.id, user_tz, val)
    await state.clear()
    await message.answer("✅ Сахар сохранён.", reply_markup=kb_measure_choice())

@router.message(MeasureFSM.bp)
async def msg_bp(message: Message, state: FSMContext):
    data = await state.get_data()
    user_tz = data["user_tz"]
    conn = message.bot.get("db")

    try:
        bp = parse_bp(message.text or "")
    except Exception as e:
        await message.answer(f"❌ {e}")
        return

    await add_bp(conn, message.from_user.id, user_tz, bp)
    await state.clear()
    await message.answer("✅ Давление сохранено.", reply_markup=kb_measure_choice())

@router.message(MeasureFSM.both_sugar)
async def msg_both_sugar(message: Message, state: FSMContext):
    data = await state.get_data()
    user_tz = data["user_tz"]
    conn = message.bot.get("db")

    try:
        val = parse_sugar(message.text or "")
    except Exception as e:
        await message.answer(f"❌ {e}")
        return

    await add_sugar(conn, message.from_user.id, user_tz, val)
    await state.set_state(MeasureFSM.both_bp)
    await message.answer(
        "✅ Сахар сохранён. Теперь давление: 120 80 60 или 120/80 (пульс опционально)",
        reply_markup=kb_skip_back("mboth_bp"),
    )

@router.message(MeasureFSM.both_bp)
async def msg_both_bp(message: Message, state: FSMContext):
    data = await state.get_data()
    user_tz = data["user_tz"]
    conn = message.bot.get("db")

    try:
        bp = parse_bp(message.text or "")
    except Exception as e:
        await message.answer(f"❌ {e}")
        return

    await add_bp(conn, message.from_user.id, user_tz, bp)
    await state.clear()
    await message.answer("✅ Давление сохранено. Готово.", reply_markup=kb_measure_choice())
