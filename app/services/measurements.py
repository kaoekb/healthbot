from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal

from app.domain.models import BP
from app.infra import repo

def measured_at_utc_now(user_tz: str) -> str:
    tz = ZoneInfo(user_tz)
    local_now = datetime.now(tz)
    return local_now.astimezone(timezone.utc).isoformat()

async def add_sugar(conn, user_id: int, user_tz: str, value: Decimal) -> None:
    await repo.insert_sugar(conn, user_id, value=value, measured_at_utc=measured_at_utc_now(user_tz))

async def add_bp(conn, user_id: int, user_tz: str, bp: BP) -> None:
    await repo.insert_bp(conn, user_id, bp=bp, measured_at_utc=measured_at_utc_now(user_tz))
