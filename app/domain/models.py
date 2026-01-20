from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class BP:
    sys: int
    dia: int
    pulse: Optional[int]

@dataclass(frozen=True)
class UserPrefs:
    user_id: int
    timezone: str
