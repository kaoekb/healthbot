from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.ui.texts import START_TEXT
from app.ui.keyboards import kb_main

router = Router()

@router.callback_query(F.data == "menu:main")
async def cb_main(callback: CallbackQuery):
    await callback.message.edit_text(START_TEXT, reply_markup=kb_main())
    await callback.answer()
