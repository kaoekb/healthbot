# =============================
# app/utils.py
# =============================
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

std_time_choices = ["08:00", "10:00", "12:00", "14:00", "17:00", "19:00", "21:00"]

def now_in_tz(tzname: str) -> datetime:
    return datetime.now(ZoneInfo(tzname))

def parse_hhmm(text: str) -> Optional[Tuple[int, int]]:
    text = text.strip()
    if len(text) != 5 or text[2] != ":":
        return None
    try:
        h = int(text[:2]); m = int(text[3:])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except Exception:
        return None
    return None

def parse_bp_triplet(text: str) -> Optional[tuple[int, int, int]]:
    parts = text.replace(",", ".").split()
    if len(parts) != 3:
        return None
    try:
        s, d, p = map(int, parts)
        return s, d, p
    except Exception:
        return None
# =============================
