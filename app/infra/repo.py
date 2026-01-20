from __future__ import annotations

import aiosqlite
from typing import Iterable, Optional, Sequence
from datetime import datetime, timezone
from decimal import Decimal

from app.domain.models import BP

async def upsert_user(conn: aiosqlite.Connection, user_id: int, timezone_str: str) -> None:
    await conn.execute(
        "INSERT INTO users(user_id, timezone) VALUES(?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET timezone=excluded.timezone",
        (user_id, timezone_str),
    )
    await conn.commit()

async def get_user_timezone(conn: aiosqlite.Connection, user_id: int) -> Optional[str]:
    cur = await conn.execute("SELECT timezone FROM users WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    return row[0] if row else None

async def set_reminder_slots(conn: aiosqlite.Connection, user_id: int, times_hm: Sequence[str]) -> None:
    # upsert user assumed
    await conn.execute("DELETE FROM reminder_slots WHERE user_id=?", (user_id,))
    await conn.executemany(
        "INSERT INTO reminder_slots(user_id, time_hm, enabled) VALUES(?, ?, 1)",
        [(user_id, t) for t in times_hm],
    )
    await conn.commit()

async def list_reminder_slots(conn: aiosqlite.Connection, user_id: int) -> list[str]:
    cur = await conn.execute("SELECT time_hm FROM reminder_slots WHERE user_id=? AND enabled=1 ORDER BY time_hm", (user_id,))
    rows = await cur.fetchall()
    return [r[0] for r in rows]

async def list_all_enabled_slots(conn: aiosqlite.Connection) -> list[tuple[int, str, str]]:
    """Returns (user_id, timezone, time_hm) for enabled slots."""
    cur = await conn.execute(
        "SELECT u.user_id, u.timezone, s.time_hm "
        "FROM users u JOIN reminder_slots s ON u.user_id = s.user_id "
        "WHERE s.enabled=1"
    )
    rows = await cur.fetchall()
    return [(int(r[0]), str(r[1]), str(r[2])) for r in rows]

async def disable_all_slots(conn: aiosqlite.Connection, user_id: int) -> None:
    await conn.execute("UPDATE reminder_slots SET enabled=0 WHERE user_id=?", (user_id,))
    await conn.commit()

async def insert_sugar(conn: aiosqlite.Connection, user_id: int, value: Decimal, measured_at_utc: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO measurements(user_id, kind, sugar_value, measured_at_utc, created_at_utc) VALUES(?, 'sugar', ?, ?, ?)",
        (user_id, str(value), measured_at_utc, now),
    )
    await conn.commit()

async def insert_bp(conn: aiosqlite.Connection, user_id: int, bp: BP, measured_at_utc: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO measurements(user_id, kind, sys, dia, pulse, measured_at_utc, created_at_utc) "
        "VALUES(?, 'bp', ?, ?, ?, ?, ?)",
        (user_id, bp.sys, bp.dia, bp.pulse, measured_at_utc, now),
    )
    await conn.commit()

async def get_measurements(conn: aiosqlite.Connection, user_id: int, since_utc_iso: str | None = None) -> list[dict]:
    if since_utc_iso:
        cur = await conn.execute(
            "SELECT kind, sugar_value, sys, dia, pulse, measured_at_utc FROM measurements "
            "WHERE user_id=? AND measured_at_utc >= ? "
            "ORDER BY measured_at_utc",
            (user_id, since_utc_iso),
        )
    else:
        cur = await conn.execute(
            "SELECT kind, sugar_value, sys, dia, pulse, measured_at_utc FROM measurements "
            "WHERE user_id=? ORDER BY measured_at_utc",
            (user_id,),
        )
    rows = await cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "kind": r[0],
            "sugar_value": r[1],
            "sys": r[2],
            "dia": r[3],
            "pulse": r[4],
            "measured_at_utc": r[5],
        })
    return out

async def reminder_already_sent(conn: aiosqlite.Connection, user_id: int, slot_date: str, time_hm: str) -> bool:
    cur = await conn.execute(
        "SELECT 1 FROM reminder_log WHERE user_id=? AND slot_date=? AND time_hm=?",
        (user_id, slot_date, time_hm),
    )
    row = await cur.fetchone()
    return row is not None

async def mark_reminder_sent(conn: aiosqlite.Connection, user_id: int, slot_date: str, time_hm: str, sent_at_utc: str) -> None:
    await conn.execute(
        "INSERT OR REPLACE INTO reminder_log(user_id, slot_date, time_hm, sent_at_utc) VALUES(?, ?, ?, ?)",
        (user_id, slot_date, time_hm, sent_at_utc),
    )
    await conn.commit()
