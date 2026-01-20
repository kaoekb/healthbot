from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

SLOTS = ["08:00","10:00","12:00","14:00","17:00","19:00","21:00"]

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Ввести данные", callback_data="menu:measure")],
        [InlineKeyboardButton(text="📄 Отчёт (7 дней)", callback_data="menu:report:7")],
        [InlineKeyboardButton(text="📄 Отчёт (30 дней)", callback_data="menu:report:30")],
        [InlineKeyboardButton(text="📄 Отчёт (всё время)", callback_data="menu:report:all")],
        [InlineKeyboardButton(text="⏰ Напоминания", callback_data="menu:reminders")],
        [InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="menu:tz")],
        [InlineKeyboardButton(text="🛑 Отключить напоминания", callback_data="menu:stop")],
    ])

def kb_back_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")]
    ])

def kb_measure_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🩸 Сахар", callback_data="m:sugar")],
        [InlineKeyboardButton(text="💓 Давление", callback_data="m:bp")],
        [InlineKeyboardButton(text="🧾 Оба", callback_data="m:both")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="m:skip")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")],
    ])

def kb_skip_back(state: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"{state}:skip")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")],
    ])

def kb_slots(selected: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for hm in SLOTS:
        mark = "✅" if hm in selected else "☑️"
        rows.append([InlineKeyboardButton(text=f"{mark} {hm}", callback_data=f"slot:{hm}")])
    rows.append([InlineKeyboardButton(text="💾 Сохранить", callback_data="slot:save")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
