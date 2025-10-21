# =============================
# app/reports.py
# =============================
from __future__ import annotations
import os
from datetime import datetime
from typing import Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from . import storage as db

DATA_DIR = "/app/data"

def _plot_sugar(ax, series):
    if not series:
        ax.text(0.5, 0.5, 'Нет данных по сахару', ha='center')
        return
    xs = [datetime.fromisoformat(t) for t, _ in series]
    ys = [v for _, v in series]
    ax.plot(xs, ys, marker='o')
    ax.set_title('Сахар (ммоль/л)')
    ax.set_xlabel('Дата')
    ax.set_ylabel('Значение')

def _plot_bp(ax, series):
    if not series:
        ax.text(0.5, 0.5, 'Нет данных по давлению', ha='center')
        return
    xs = [datetime.fromisoformat(t) for t, *_ in series]
    s = [v[1] for v in series]
    d = [v[2] for v in series]
    p = [v[3] for v in series]
    ax.plot(xs, s, marker='o', label='Систолическое')
    ax.plot(xs, d, marker='o', label='Диастолическое')
    ax.plot(xs, p, marker='o', label='Пульс')
    ax.legend()
    ax.set_title('Давление и пульс')
    ax.set_xlabel('Дата')

async def build_report(user_id: int) -> Tuple[str, str | None]:
    s = await db.period_stats(user_id, 7)
    parts = ["<b>Выписка</b> — средние за 7 дней:"]
    if s["sugar_avg"] is not None:
        parts.append(f"• Сахар: <b>{s['sugar_avg']:.2f}</b> ммоль/л")
    else:
        parts.append("• Сахар: нет данных")
    if s["bp_sys_avg"] is not None:
        parts.append(f"• Давление: <b>{s['bp_sys_avg']:.0f}/{s['bp_dia_avg']:.0f}</b>, Пульс: <b>{s['bp_p_avg']:.0f}</b>")
    else:
        parts.append("• Давление: нет данных")

    ts7 = await db.timeseries(user_id, 7)
    ts30 = await db.timeseries(user_id, 30)
    ts_all = await db.timeseries(user_id, 3650)

    has_any = any((ts7["sugar"], ts7["bp"], ts30["sugar"], ts30["bp"], ts_all["sugar"], ts_all["bp"]))
    pdf_path = None
    if has_any:
        os.makedirs(DATA_DIR, exist_ok=True)
        pdf_path = os.path.join(DATA_DIR, f"report_{user_id}.pdf")
        with PdfPages(pdf_path) as pdf:
            for title, ts in (("Неделя", ts7), ("Месяц", ts30), ("Всё время", ts_all)):
                fig = plt.figure()
                ax1 = fig.add_subplot(2, 1, 1)
                _plot_sugar(ax1, ts["sugar"])
                ax2 = fig.add_subplot(2, 1, 2)
                _plot_bp(ax2, ts["bp"])
                fig.suptitle(f"Графики — {title}")
                fig.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
    else:
        parts.append("\nДля графиков пока недостаточно данных.")

    return "\n".join(parts), pdf_path
