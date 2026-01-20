from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from dateutil import parser as dtparser

@dataclass(frozen=True)
class SugarPoint:
    dt: datetime
    value: Decimal

@dataclass(frozen=True)
class BPPoint:
    dt: datetime
    sys: int
    dia: int
    pulse: Optional[int]

def _prep_ax_time(ax, n: int):
    ax.grid(True, alpha=0.2)
    interval = max(1, n // 10) if n else 1
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_ha("right")

def sugar_figure(points: Sequence[SugarPoint], title: str):
    fig, ax = plt.subplots(figsize=(8.27, 4.8))  # ~A4 width
    if points:
        xs = [p.dt for p in points]
        ys = [float(p.value) for p in points]
        ax.plot(xs, ys, marker="o", linewidth=1)
        ax.set_ylabel("mmol/L")
        _prep_ax_time(ax, len(points))
    ax.set_title(title)
    fig.tight_layout()
    return fig

def bp_figure(points: Sequence[BPPoint], title: str):
    fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(8.27, 6.0), sharex=True, height_ratios=[2, 1])
    if points:
        xs = [p.dt for p in points]
        sys = [p.sys for p in points]
        dia = [p.dia for p in points]
        pulse = [p.pulse for p in points]

        ax1.plot(xs, sys, marker="o", linewidth=1, label="SYS")
        ax1.plot(xs, dia, marker="o", linewidth=1, label="DIA")
        ax1.set_ylabel("mmHg")
        ax1.legend(loc="upper right")
        ax1.grid(True, alpha=0.2)

        # plot pulse only where present
        xs_p = [x for x, p in zip(xs, pulse) if p is not None]
        p_p = [p for p in pulse if p is not None]
        if xs_p:
            ax2.plot(xs_p, p_p, marker="o", linewidth=1)
        ax2.set_ylabel("bpm")
        _prep_ax_time(ax2, len(points))

    ax1.set_title(title)
    fig.tight_layout()
    return fig

def fig_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()

def parse_utc_iso(iso: str) -> datetime:
    return dtparser.isoparse(iso)
