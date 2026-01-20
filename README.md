# HealthBot (rewrite)

Telegram bot for tracking **blood glucose** and **blood pressure** with:
- explicit choice what to enter (no auto-picking)
- forgiving input parsing (spaces / `/` / `:` / `.` / `-` etc.)
- per-user timezone, reminders by local time
- SQLite (aiosqlite), aiogram v3
- readable PDF reports with clean charts (7 days / 30 days / all time)

## Quick start (Docker)

1) Create `.env`:
```bash
BOT_TOKEN=123456:ABCDEF...
DATA_DIR=/data
DEFAULT_TIMEZONE=Europe/Moscow
LOG_LEVEL=INFO
```

2) Run:
```bash
docker compose up -d --build
```

DB and generated reports live in the mounted volume (`./data` by default in compose).

## Commands
- `/start` – main menu
- `/help` – short help

## Input examples

### Glucose
- `5.6`
- `5,6`
- `sugar 5.6`

### Blood pressure
- `120 80 60`
- `120/80/60`
- `120:80`
- `120-80-60`
(Pulse is optional.)

## Notes
- All timestamps are stored in **UTC**.
- Heavy work (charts/PDF) is executed via `asyncio.to_thread()` so the bot stays responsive.
