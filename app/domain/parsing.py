from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from .models import BP

def parse_sugar(text: str) -> Decimal:
    """Accepts 5.6, 5,6, 'sugar 5.6', etc."""
    m = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if not m:
        raise ValueError("Не вижу число. Пример: 5.6 или 5,6")
    s = m.group(1).replace(",", ".")
    try:
        val = Decimal(s)
    except InvalidOperation:
        raise ValueError("Некорректное число. Пример: 5.6")
    if val <= 0:
        raise ValueError("Значение должно быть больше 0")
    # Optional sanity bounds (can be relaxed)
    if val > 60:
        raise ValueError("Слишком большое значение. Проверь ввод.")
    return val

def parse_bp(text: str) -> BP:
    """Accepts '120 80 60', '120/80', '120:80:60', '120-80-60', etc."""
    nums = re.findall(r"\d+", text)
    if len(nums) < 2:
        raise ValueError("Нужно минимум 2 числа: САД ДАД [пульс]. Пример: 120 80 60 или 120/80")
    sys = int(nums[0])
    dia = int(nums[1])
    pulse = int(nums[2]) if len(nums) >= 3 else None

    if not (50 <= sys <= 260 and 30 <= dia <= 160):
        raise ValueError("Похоже на ошибку. Пример: 120 80 60")
    if sys <= dia:
        raise ValueError("САД должен быть больше ДАД. Пример: 120 80")
    if pulse is not None and not (30 <= pulse <= 220):
        raise ValueError("Пульс выглядит странно. Пример: 60")
    return BP(sys=sys, dia=dia, pulse=pulse)
