"""Общие чистые проверки для моделей Server/Data.

Модуль не хранит состояние исполнения и не зависит от backend.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256


def require_non_empty(value: str, field_name: str) -> str:
    """Проверить непустую строку. EN summary: validate a non-empty string."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} не должен быть пустым")
    return normalized


def require_aware(value: datetime, field_name: str) -> datetime:
    """Проверить timezone-aware время. EN summary: validate timezone-aware datetime."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} должен содержать timezone/offset")
    return value


def stable_identity(*parts: str) -> str:
    """Построить стабильный digest. EN summary: build a stable identity digest."""
    payload = "".join(parts).encode("utf-8")
    return sha256(payload).hexdigest()
