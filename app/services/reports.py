from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from dateutil import parser as dtparser

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from app.services.plotting import SugarPoint, BPPoint, sugar_figure, bp_figure, fig_to_png_bytes

def _since_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

def since_iso(days: Optional[int]) -> Optional[str]:
    return None if days is None else _since_iso(days)

def _aggregate_daily(points: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    """Median per day in UTC."""
    by_day: dict[str, list[float]] = {}
    for dt, v in points:
        key = dt.date().isoformat()
        by_day.setdefault(key, []).append(v)
    out = []
    for day, vals in sorted(by_day.items()):
        vals_sorted = sorted(vals)
        mid = len(vals_sorted) // 2
        if len(vals_sorted) % 2 == 1:
            med = vals_sorted[mid]
        else:
            med = (vals_sorted[mid - 1] + vals_sorted[mid]) / 2
        out.append((datetime.fromisoformat(day).replace(tzinfo=timezone.utc), med))
    return out

def _build_pdf(path: str, pages: list[tuple[str, bytes]], title: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    for caption, png_bytes in pages:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, h - 50, title)
        c.setFont("Helvetica", 11)
        c.drawString(40, h - 70, caption)

        img = ImageReader(png_bytes)
        img_w = w - 80
        img_h = h - 140
        c.drawImage(img, 40, 60, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')
        c.showPage()

    c.save()

def build_report_pdf_from_rows(*, rows: list[dict], user_id: int, data_dir: str, days: Optional[int]) -> str:
    """Pure sync function: rows already fetched. Heavy plotting/PDF happens here."""
    period_label = "all" if days is None else f"{days}d"

    sugar_points_raw: list[tuple[datetime, float]] = []
    bp_points_raw: list[tuple[datetime, int, int, Optional[int]]] = []

    for r in rows:
        dt = dtparser.isoparse(r["measured_at_utc"]).astimezone(timezone.utc)
        if r["kind"] == "sugar" and r["sugar_value"] is not None:
            sugar_points_raw.append((dt, float(Decimal(r["sugar_value"]))))
        elif r["kind"] == "bp" and r["sys"] is not None and r["dia"] is not None:
            bp_points_raw.append((dt, int(r["sys"]), int(r["dia"]), int(r["pulse"]) if r["pulse"] is not None else None))

    if days is None:
        sugar_agg = _aggregate_daily([(dt, v) for dt, v in sugar_points_raw])
        sugar_points = [SugarPoint(dt=dt, value=Decimal(str(v))) for dt, v in sugar_agg]

        sys_agg = _aggregate_daily([(dt, float(sys)) for dt, sys, _, _ in bp_points_raw])
        dia_agg = _aggregate_daily([(dt, float(dia)) for dt, _, dia, _ in bp_points_raw])
        pulse_agg = _aggregate_daily([(dt, float(p)) for dt, _, _, p in bp_points_raw if p is not None])

        sys_map = {dt.date().isoformat(): int(round(v)) for dt, v in sys_agg}
        dia_map = {dt.date().isoformat(): int(round(v)) for dt, v in dia_agg}
        pulse_map = {dt.date().isoformat(): int(round(v)) for dt, v in pulse_agg}

        days_sorted = sorted(set(sys_map.keys()) | set(dia_map.keys()))
        bp_points = []
        for day in days_sorted:
            if day in sys_map and day in dia_map:
                dt = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
                bp_points.append(BPPoint(dt=dt, sys=sys_map[day], dia=dia_map[day], pulse=pulse_map.get(day)))
    else:
        sugar_points = [SugarPoint(dt=dt, value=Decimal(str(v))) for dt, v in sugar_points_raw]
        bp_points = [BPPoint(dt=dt, sys=sys, dia=dia, pulse=pulse) for dt, sys, dia, pulse in bp_points_raw]

    pages: list[tuple[str, bytes]] = []

    if sugar_points:
        fig = sugar_figure(sugar_points, title="Глюкоза (mmol/L)")
        pages.append(("Глюкоза", fig_to_png_bytes(fig)))

    if bp_points:
        fig = bp_figure(bp_points, title="Давление (mmHg) и пульс (bpm)")
        pages.append(("Давление", fig_to_png_bytes(fig)))

    out_path = os.path.join(data_dir, "reports", f"report_{user_id}_{period_label}.pdf")

    if not pages:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        c = canvas.Canvas(out_path, pagesize=A4)
        w, h = A4
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, h - 60, "Отчёт")
        c.setFont("Helvetica", 12)
        c.drawString(40, h - 90, "Нет данных за выбранный период.")
        c.save()
        return out_path

    title = f"HealthBot report ({period_label})"
    _build_pdf(out_path, pages, title=title)
    return out_path
