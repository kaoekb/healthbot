from __future__ import annotations

import os
import aiosqlite
from typing import Optional

SCHEMA_VERSION = 1

DDL = [
    """CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        timezone TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS reminder_slots (
        user_id INTEGER NOT NULL,
        time_hm TEXT NOT NULL,          -- 'HH:MM'
        enabled INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (user_id, time_hm),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );""",
    """CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,             -- 'sugar' | 'bp'
        sugar_value TEXT,               -- Decimal as string
        sys INTEGER,
        dia INTEGER,
        pulse INTEGER,
        measured_at_utc TEXT NOT NULL,  -- ISO 8601 with Z or +00:00
        created_at_utc TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );""",
    """CREATE TABLE IF NOT EXISTS reminder_log (
        user_id INTEGER NOT NULL,
        slot_date TEXT NOT NULL,        -- YYYY-MM-DD in user's local date
        time_hm TEXT NOT NULL,          -- HH:MM
        sent_at_utc TEXT NOT NULL,
        PRIMARY KEY (user_id, slot_date, time_hm)
    );""",
]

async def connect(db_path: str) -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    await conn.commit()
    return conn

async def init_db(conn: aiosqlite.Connection) -> None:
    for stmt in DDL:
        await conn.execute(stmt)
    # schema version
    await conn.execute("INSERT OR IGNORE INTO schema_meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
    await conn.commit()
