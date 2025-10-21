from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from .utils import std_time_choices

def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for row in (("Изменить измеряемые", "Ввести данные"), ("Получить выписку", "Отключить уведомления")):
        kb.row(*(KeyboardButton(text=txt) for txt in row))
    kb.row(KeyboardButton(text="Выбрать часовой пояс"))
    return kb.as_markup(resize_keyboard=True)

def measurement_choice_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Сахар в крови", callback_data="set_metric:sugar")
    b.button(text="Давление", callback_data="set_metric:bp")
    b.button(text="Все вместе", callback_data="set_metric:both")
    b.adjust(1)
    return b.as_markup()

def yes_no_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Подтвердить", callback_data=yes_cb)
    b.button(text="Изменить ввод", callback_data=no_cb)
    b.adjust(2)
    return b.as_markup()

def choose_what_to_enter_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Сахар", callback_data="enter:sugar")
    b.button(text="Давление", callback_data="enter:bp")
    b.button(text="Оба (по очереди)", callback_data="enter:both")
    b.adjust(2, 1)
    return b.as_markup()

def make_times_kb(selected: set[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in std_time_choices:
        mark = "✅ " if t in selected else ""
        b.button(text=f"{mark}{t}", callback_data=f"toggle_time:{t}")
    b.button(text="Готово", callback_data="times_done")
    b.adjust(3, 3, 1)
    return b.as_markup()

def timezone_kb() -> InlineKeyboardMarkup:
    cities = [
        ("−1 Калининград", "Europe/Kaliningrad"),
        ("±0 Москва / Санкт‑Петербург", "Europe/Moscow"),
        ("+1 Самара", "Europe/Samara"),
        ("+2 Екатеринбург", "Asia/Yekaterinburg"),
        ("+3 Омск", "Asia/Omsk"),
        ("+4 Новосибирск", "Asia/Novosibirsk"),
        ("+4 Красноярск", "Asia/Krasnoyarsk"),
        ("+5 Иркутск", "Asia/Irkutsk"),
        ("+6 Якутск", "Asia/Yakutsk"),
        ("+7 Владивосток", "Asia/Vladivostok"),
        ("+8 Магадан", "Asia/Magadan"),
        ("+9 Камчатка", "Asia/Kamchatka"),
    ]
    b = InlineKeyboardBuilder()
    for label, tz in cities:
        b.button(text=label, callback_data=f"set_tz:{tz}")
    b.adjust(2)
    return b.as_markup()
