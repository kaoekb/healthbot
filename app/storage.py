from __future__ import annotations
import aiosqlite
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import os

DB_PATH = os.getenv("DB_PATH", "/app/data/healthbot.sqlite3")

SCHEMA_SQL = """CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  full_name TEXT,
  username TEXT,
  notifications_enabled INTEGER DEFAULT 1,
  metric TEXT DEFAULT 'both',
  simultaneous INTEGER DEFAULT 1,
  user_timezone TEXT DEFAULT 'Europe/Moscow'
);

CREATE TABLE IF NOT EXISTS schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  time_str TEXT NOT NULL,
  UNIQUE(user_id, time_str)
);

CREATE TABLE IF NOT EXISTS sugar (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  value REAL NOT NULL,
  measured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bp (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  sys INTEGER NOT NULL,
  dia INTEGER NOT NULL,
  pulse INTEGER NOT NULL,
  measured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminder_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  date TEXT NOT NULL,
  time_str TEXT NOT NULL,
  UNIQUE(user_id, date, time_str)
);
"""

async def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_SQL)
        # Migration guard for older DBs
        try:
            await db.execute("ALTER TABLE users ADD COLUMN user_timezone TEXT DEFAULT 'Europe/Moscow'")
        except Exception:
            pass
        await db.commit()

async def upsert_user(u) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, full_name, username) VALUES (?,?,?)\n"
            "ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name, username=excluded.username",
            (u.id, u.full_name, getattr(u, "username", None)),
        )
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def set_metric(user_id: int, metric: str, simultaneous: int = 1) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET metric=?, simultaneous=? WHERE user_id=?",
            (metric, simultaneous, user_id),
        )
        await db.commit()

async def list_schedule_times(user_id: int) -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT time_str FROM schedules WHERE user_id=? ORDER BY time_str",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]

async def toggle_schedule_time(user_id: int, time_str: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO schedules (user_id, time_str) VALUES (?,?)",
                (user_id, time_str),
            )
        except Exception:
            await db.execute(
                "DELETE FROM schedules WHERE user_id=? AND time_str=?",
                (user_id, time_str),
            )
        await db.commit()

async def enable_notifications(user_id: int, enabled: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET notifications_enabled=? WHERE user_id=?",
            (enabled, user_id),
        )
        await db.commit()

async def should_remind(user_id: int, time_str: str, today_iso: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM reminder_log WHERE user_id=? AND date=? AND time_str=?",
            (user_id, today_iso, time_str),
        )
        return (await cur.fetchone()) is None

async def mark_reminded(user_id: int, time_str: str, today_iso: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO reminder_log (user_id, date, time_str) VALUES (?,?,?)",
            (user_id, today_iso, time_str),
        )
        await db.commit()

async def list_users_enabled() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE notifications_enabled=1"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def insert_sugar(user_id: int, value: float, when_utc: datetime) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sugar (user_id, value, measured_at) VALUES (?,?,?)",
            (user_id, value, when_utc.isoformat()),
        )
        await db.commit()

async def insert_bp(user_id: int, sys: int, dia: int, pulse: int, when_utc: datetime) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bp (user_id, sys, dia, pulse, measured_at) VALUES (?,?,?,?,?)",
            (user_id, sys, dia, pulse, when_utc.isoformat()),
        )
        await db.commit()

async def period_stats(user_id: int, days: int) -> dict:
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # sugar avg
        cur = await db.execute(
            "SELECT AVG(value) as avg_val, COUNT(*) as cnt FROM sugar WHERE user_id=? AND measured_at>=?",
            (user_id, since),
        )
        s = await cur.fetchone()
        # bp avg
        cur = await db.execute(
            "SELECT AVG(sys) as a_sys, AVG(dia) as a_dia, AVG(pulse) as a_p FROM bp WHERE user_id=? AND measured_at>=?",
            (user_id, since),
        )
        b = await cur.fetchone()
    return {
        "sugar_avg": (s["avg_val"] if s and s["cnt"] else None),
        "sugar_cnt": (s["cnt"] if s else 0),
        "bp_sys_avg": (b["a_sys"] if b else None),
        "bp_dia_avg": (b["a_dia"] if b else None),
        "bp_p_avg": (b["a_p"] if b else None),
    }

async def timeseries(user_id: int, days: int) -> dict:
    since_dt = datetime.utcnow() - timedelta(days=days)
    since = since_dt.isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT measured_at, value FROM sugar WHERE user_id=? AND measured_at>=? ORDER BY measured_at",
            (user_id, since),
        )
        sugar = [(r["measured_at"], r["value"]) for r in await cur.fetchall()]
        cur = await db.execute(
            "SELECT measured_at, sys, dia, pulse FROM bp WHERE user_id=? AND measured_at>=? ORDER BY measured_at",
            (user_id, since),
        )
        bp = [(r["measured_at"], r["sys"], r["dia"], r["pulse"]) for r in await cur.fetchall()]
    return {"sugar": sugar, "bp": bp}
