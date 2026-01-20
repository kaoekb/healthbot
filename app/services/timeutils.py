from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def utc_iso_from_local_now(user_tz: str) -> tuple[str, str]:
    """Return (utc_iso, local_date_ymd)."""
    tz = ZoneInfo(user_tz)
    local = datetime.now(tz)
    utc = local.astimezone(timezone.utc)
    return utc.isoformat(), local.date().isoformat()

def utc_iso_from_local_datetime(user_tz: str, dt_local: datetime) -> str:
    tz = ZoneInfo(user_tz)
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=tz)
    return dt_local.astimezone(timezone.utc).isoformat()

def next_fire_local(user_tz: str, time_hm: str, now_local: datetime | None = None) -> datetime:
    tz = ZoneInfo(user_tz)
    if now_local is None:
        now_local = datetime.now(tz)
    hh, mm = map(int, time_hm.split(":"))
    candidate = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if candidate <= now_local:
        # tomorrow
        candidate = candidate.replace(day=candidate.day)  # no-op for clarity
        candidate = candidate + __import__("datetime").timedelta(days=1)
    return candidate
