# =============================
# app/bot.py
# =============================
from __future__ import annotations
import asyncio
import os
import aiosqlite
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton)
from pathlib import Path
from aiogram.types import FSInputFile, BufferedInputFile


from . import storage as db
from . import scheduler
from . import reports
from .utils import (
    parse_hhmm, parse_bp_triplet,
)
from .keyboards import (
    main_menu_kb, yes_no_kb, measurement_choice_kb, choose_what_to_enter_kb,
    make_times_kb, timezone_kb,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TZ = os.getenv("TZ", "UTC")

router = Router()

class SugarFlow(StatesGroup):
    time = State()
    value = State()
    confirm = State()

class BpFlow(StatesGroup):
    time = State()
    values = State()
    confirm = State()

class SettingsFlow(StatesGroup):
    metric = State()
    times = State()
    simultaneous = State()

class ReportPeriod(StatesGroup):
    stub = State()

@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await db.upsert_user(m.from_user)
    await m.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb(),
    )

@router.message(F.text == "Изменить измеряемые")
async def change_measured(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SettingsFlow.metric)
    await m.answer(
        "Что будем измерять?", reply_markup=measurement_choice_kb()
    )

@router.callback_query(F.data.startswith("set_metric:"))
async def set_metric(cb: CallbackQuery, state: FSMContext):
    metric = cb.data.split(":", 1)[1]
    await state.update_data(metric=metric)
    await state.set_state(SettingsFlow.times)
    existing = await db.list_schedule_times(cb.from_user.id)
    await cb.message.edit_text(
        "Выберите время измерений (можно несколько). Нажимайте, чтобы переключать. Нажмите Готово когда закончите.",
        reply_markup=make_times_kb(selected=set(existing)),
    )
    await cb.answer()

@router.callback_query(F.data.startswith("toggle_time:"))
async def toggle_time(cb: CallbackQuery, state: FSMContext):
    time_str = cb.data.split(":", 1)[1]
    await db.toggle_schedule_time(cb.from_user.id, time_str)
    current = set(await db.list_schedule_times(cb.from_user.id))
    await cb.message.edit_reply_markup(reply_markup=make_times_kb(selected=current))
    await cb.answer()

@router.callback_query(F.data == "times_done")
async def times_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    metric = data.get("metric", "both")
    times = await db.list_schedule_times(cb.from_user.id)
    if not times:
        await cb.answer("Выберите хотя бы одно время", show_alert=True)
        return
    if metric == "both":
        await state.set_state(SettingsFlow.simultaneous)
        await cb.message.edit_text(
            "Измерять одновременно? (одно напоминание для двух показателей)",
            reply_markup=yes_no_kb("simul_yes", "simul_no"),
        )
    else:
        await db.set_metric(cb.from_user.id, metric=metric, simultaneous=1)
        await cb.message.edit_text(
            f"Сохранено. Измеряем: {('Сахар' if metric=='sugar' else 'Давление')}\nВремя: {', '.join(times)}",
        )
        await cb.message.answer("Готово ✨", reply_markup=main_menu_kb())
    await cb.answer()

@router.callback_query(F.data.in_({"simul_yes", "simul_no"}))
async def set_simul(cb: CallbackQuery, state: FSMContext):
    simul = 1 if cb.data == "simul_yes" else 0
    data = await state.get_data()
    metric = data.get("metric", "both")
    await db.set_metric(cb.from_user.id, metric=metric, simultaneous=simul)
    times = await db.list_schedule_times(cb.from_user.id)
    await cb.message.edit_text(
        f"Сохранено. Измеряем: оба показателя. Одновременно: {'да' if simul else 'нет'}.\nВремя: {', '.join(times)}"
    )
    await cb.message.answer("Готово ✨", reply_markup=main_menu_kb())
    await cb.answer()

@router.message(F.text == "Отключить уведомления")
async def disable_notifs(m: Message):
    u = await db.get_user(m.from_user.id)
    new_val = 0 if u and u.get("notifications_enabled", 1) else 1
    await db.enable_notifications(m.from_user.id, new_val)
    await m.answer(
        "Уведомления: " + ("выключены" if new_val == 0 else "включены"),
        reply_markup=main_menu_kb(),
    )

@router.message(F.text == "Выбрать часовой пояс")
async def choose_tz(m: Message, state: FSMContext):
    u = await db.get_user(m.from_user.id)
    cur_tz = (u or {}).get("user_timezone") or "Europe/Moscow"
    spb_now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%H:%M")
    your_now = datetime.now(ZoneInfo(cur_tz)).strftime("%H:%M")
    await m.answer(
        f"Стандартное время СПб (Москва): <b>{spb_now}</b>\nВаш текущий часовой пояс: <code>{cur_tz}</code> (сейчас <b>{your_now}</b>).\nВыберите из списка:",
        reply_markup=timezone_kb(),
    )

@router.message(F.text == "Ввести данные")
async def input_data(m: Message, state: FSMContext):
    u = await db.get_user(m.from_user.id)
    metric = u.get("metric", "both") if u else "both"
    if metric == "both":
        await m.answer("Что вводим?", reply_markup=choose_what_to_enter_kb())
    elif metric == "sugar":
        await ask_sugar_time(m, state)
    else:
        await ask_bp_time(m, state)

@router.callback_query(F.data == "enter:sugar")
async def enter_sugar(cb: CallbackQuery, state: FSMContext):
    await ask_sugar_time(cb.message, state)
    await cb.answer()

@router.callback_query(F.data == "enter:bp")
async def enter_bp(cb: CallbackQuery, state: FSMContext):
    await ask_bp_time(cb.message, state)
    await cb.answer()

@router.callback_query(F.data == "enter:both")
async def enter_both(cb: CallbackQuery, state: FSMContext):
    await state.update_data(enter_both=True)
    await ask_sugar_time(cb.message, state)
    await cb.answer()

async def ask_sugar_time(m: Message, state: FSMContext):
    await state.set_state(SugarFlow.time)
    await m.answer(
        "Сахар в крови — если измерение было ранее, введите время (HH:MM). Либо нажмите кнопку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Измерение сейчас", callback_data="sugar_time:now")]
        ]),
    )

@router.callback_query(F.data.startswith("sugar_time:"))
async def sugar_time_cb(cb: CallbackQuery, state: FSMContext):
    tag = cb.data.split(":", 1)[1]
    u = await db.get_user(cb.from_user.id)
    tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
    when = datetime.now(ZoneInfo(tzname)) if tag == "now" else None
    await state.update_data(sugar_time=when)
    await state.set_state(SugarFlow.value)
    await cb.message.answer("Введите значение сахара (например 5.6). Только число:")
    await cb.answer()

@router.message(SugarFlow.time)
async def sugar_time_text(m: Message, state: FSMContext):
    hhmm = parse_hhmm(m.text)
    if not hhmm:
        await m.answer("Ожидаю время в формате HH:MM. Попробуйте ещё раз.")
        return
    u = await db.get_user(m.from_user.id)
    tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
    now_local = datetime.now(ZoneInfo(tzname))
    when = now_local.replace(hour=hhmm[0], minute=hhmm[1], second=0, microsecond=0)
    if when > now_local:
        from datetime import timedelta
        when = when - timedelta(days=1)
    await state.update_data(sugar_time=when)
    await state.set_state(SugarFlow.value)
    await m.answer("Введите значение сахара (например 5.6). Только число:")

@router.message(SugarFlow.value)
async def sugar_value(m: Message, state: FSMContext):
    try:
        val = float(m.text.replace(",", "."))
    except Exception:
        await m.answer("Нужно число. Попробуйте ещё раз.")
        return
    data = await state.get_data()
    when_local = data.get("sugar_time")
    u = await db.get_user(m.from_user.id)
    tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
    if when_local is None:
        when_local = datetime.now(ZoneInfo(tzname))
    # store UTC for DB
    when_utc = when_local.astimezone(dt_timezone.utc)
    await state.update_data(sugar_value=val, sugar_time=when_local)
    await state.set_state(SugarFlow.confirm)
    await m.answer(
        f"Проверьте: сахар = {val} ммоль/л, время = {when_local.strftime('%Y-%m-%d %H:%M')} ({tzname})",
        reply_markup=yes_no_kb("sugar_confirm", "sugar_edit"),
    )

@router.callback_query(F.data.in_({"sugar_confirm", "sugar_edit"}))
async def sugar_confirm(cb: CallbackQuery, state: FSMContext):
    if cb.data == "sugar_edit":
        await state.set_state(SugarFlow.value)
        await cb.message.answer("Введите значение сахара заново:")
    else:
        data = await state.get_data()
        val = data.get("sugar_value")
        when_local = data.get("sugar_time")
        u = await db.get_user(cb.from_user.id)
        tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
        if when_local is None:
            when_local = datetime.now(ZoneInfo(tzname))
        when_utc = when_local.astimezone(dt_timezone.utc)
        await db.insert_sugar(cb.from_user.id, val, when_utc)
        await cb.message.answer("Сохранено ✔️")
        if data.get("enter_both"):
            await ask_bp_time(cb.message, state)
        else:
            await cb.message.answer("Что дальше?", reply_markup=main_menu_kb())
        await state.clear()
    await cb.answer()

async def ask_bp_time(m: Message, state: FSMContext):
    await state.set_state(BpFlow.time)
    await m.answer(
        "Давление — если измерение было ранее, введите время (HH:MM). Либо нажмите кнопку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Измерение сейчас", callback_data="bp_time:now")]
        ]),
    )

@router.callback_query(F.data.startswith("bp_time:"))
async def bp_time_cb(cb: CallbackQuery, state: FSMContext):
    tag = cb.data.split(":", 1)[1]
    u = await db.get_user(cb.from_user.id)
    tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
    when = datetime.now(ZoneInfo(tzname)) if tag == "now" else None
    await state.update_data(bp_time=when)
    await state.set_state(BpFlow.values)
    await cb.message.answer("Введите три числа через пробел: Систолическое Диастолическое Пульс (например: 120 70 90)")
    await cb.answer()

@router.message(BpFlow.time)
async def bp_time_text(m: Message, state: FSMContext):
    hhmm = parse_hhmm(m.text)
    if not hhmm:
        await m.answer("Ожидаю время в формате HH:MM. Попробуйте ещё раз.")
        return
    u = await db.get_user(m.from_user.id)
    tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
    now_local = datetime.now(ZoneInfo(tzname))
    when = now_local.replace(hour=hhmm[0], minute=hhmm[1], second=0, microsecond=0)
    if when > now_local:
        from datetime import timedelta
        when = when - timedelta(days=1)
    await state.update_data(bp_time=when)
    await state.set_state(BpFlow.values)
    await m.answer("Введите три числа через пробел: Систолическое Диастолическое Пульс (например: 120 70 90)")

@router.message(BpFlow.values)
async def bp_values(m: Message, state: FSMContext):
    triplet = parse_bp_triplet(m.text)
    if not triplet:
        await m.answer("Нужно три числа: 120 70 90. Попробуйте ещё раз.")
        return
    s, d, p = triplet
    data = await state.get_data()
    when_local = data.get("bp_time")
    u = await db.get_user(m.from_user.id)
    tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
    if when_local is None:
        when_local = datetime.now(ZoneInfo(tzname))
    await state.update_data(bp_values=(s, d, p), bp_time=when_local)
    await state.set_state(BpFlow.confirm)
    await m.answer(
        f"Проверьте: Давление = {s}/{d}, пульс = {p}, время = {when_local.strftime('%Y-%m-%d %H:%M')} ({tzname})",
        reply_markup=yes_no_kb("bp_confirm", "bp_edit"),
    )

@router.callback_query(F.data.in_({"bp_confirm", "bp_edit"}))
async def bp_confirm(cb: CallbackQuery, state: FSMContext):
    if cb.data == "bp_edit":
        await state.set_state(BpFlow.values)
        await cb.message.answer("Введите три числа снова: 120 70 90")
    else:
        data = await state.get_data()
        s, d, p = data.get("bp_values")
        when_local = data.get("bp_time")
        u = await db.get_user(cb.from_user.id)
        tzname = (u or {}).get("user_timezone") or "Europe/Moscow"
        if when_local is None:
            when_local = datetime.now(ZoneInfo(tzname))
        when_utc = when_local.astimezone(dt_timezone.utc)
        await db.insert_bp(cb.from_user.id, s, d, p, when_utc)
        await cb.message.answer("Сохранено ✔️")
        await cb.message.answer("Что дальше?", reply_markup=main_menu_kb())
        await state.clear()
    await cb.answer()

@router.message(F.text == "Получить выписку")
async def get_report(m: Message, state: FSMContext):
    text, pdf_path = await reports.build_report(m.from_user.id)
    await m.answer(text, parse_mode=ParseMode.HTML)
    if pdf_path:
        doc = FSInputFile(pdf_path, filename="report.pdf")
        await m.answer_document(document=doc, caption="Отчёт с графиками")

@router.callback_query(F.data == "enter_from_reminder")
async def enter_from_reminder(cb: CallbackQuery, state: FSMContext):
    await input_data(cb.message, state)
    await cb.answer()

@router.callback_query(F.data.startswith("set_tz:"))
async def set_tz(cb: CallbackQuery, state: FSMContext):
    tzname = cb.data.split(":", 1)[1]
    async with aiosqlite.connect(db.DB_PATH) as con:
        await con.execute("UPDATE users SET user_timezone=? WHERE user_id=?", (tzname, cb.from_user.id))
        await con.commit()
    spb_now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%H:%M")
    your_now = datetime.now(ZoneInfo(tzname)).strftime("%H:%M")
    await cb.message.edit_text(
        f"Часовой пояс установлен: <code>{tzname}</code>.\nСПб сейчас: <b>{spb_now}</b>, у вас: <b>{your_now}</b>.")
    await cb.message.answer("Готово ✨", reply_markup=main_menu_kb())
    await cb.answer()

async def on_startup(bot: Bot):
    await db.init_db()

async def send_pdf(m, pdf, filename="report.pdf", caption="Отчёт с графиками"):
    if isinstance(pdf, (bytes, bytearray)):
        doc = BufferedInputFile(bytes(pdf), filename=filename)
    else:
        doc = FSInputFile(str(Path(pdf)), filename=filename)  # pdf = путь
    await m.answer_document(document=doc, caption=caption)

async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set")
    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)

    await on_startup(bot)
    asyncio.create_task(scheduler.reminder_loop(bot))

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
