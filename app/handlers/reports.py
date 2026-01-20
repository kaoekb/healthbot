from __future__ import annotations

import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile

from app.infra import repo
from app.services.reports import since_iso, build_report_pdf_from_rows
from app.ui.keyboards import kb_back_main

router = Router()

@router.callback_query(F.data.startswith("menu:report:"))
async def cb_report(callback: CallbackQuery):
    kind = callback.data.split(":", 2)[2]
    days = None
    if kind in ("7", "30"):
        days = int(kind)

    conn = callback.bot.get("db")
    user_id = callback.from_user.id
    data_dir = callback.bot.get("data_dir")

    await callback.answer()
    await callback.message.edit_text("📄 Готовлю отчёт…", reply_markup=kb_back_main())

    rows = await repo.get_measurements(conn, user_id, since_utc_iso=since_iso(days))

    path = await asyncio.to_thread(
        build_report_pdf_from_rows,
        rows=rows,
        user_id=user_id,
        data_dir=data_dir,
        days=days,
    )

    await callback.message.answer_document(FSInputFile(path), caption="Ваш отчёт")
    await callback.message.answer("⬅️ В меню", reply_markup=kb_back_main())
