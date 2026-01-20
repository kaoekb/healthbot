from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.ui.texts import START_TEXT, HELP_TEXT
from app.ui.keyboards import kb_main

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(START_TEXT, reply_markup=kb_main())

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=kb_main())

@router.callback_query(lambda c: c.data == "menu:main")
async def cb_main(callback: CallbackQuery):
    await callback.message.edit_text(START_TEXT, reply_markup=kb_main())
    await callback.answer()
