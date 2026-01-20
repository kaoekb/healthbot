from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    bot_token: str
    data_dir: str
    default_timezone: str
    log_level: str

def load_settings() -> Settings:
    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    data_dir = os.environ.get("DATA_DIR", "/data").strip() or "/data"
    default_timezone = os.environ.get("DEFAULT_TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"
    log_level = os.environ.get("LOG_LEVEL", "INFO").strip() or "INFO"
    return Settings(
        bot_token=bot_token,
        data_dir=data_dir,
        default_timezone=default_timezone,
        log_level=log_level,
    )
