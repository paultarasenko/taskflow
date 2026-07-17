"""JWT encode/decode через python-jose.

Токен несёт claim `type` (access|refresh) — без него refresh-токен можно
было бы подсунуть туда, где ожидается access, и наоборот. Контракт полей
(create_access_token/create_refresh_token/decode_token) зафиксирован ещё на
Этапе 2, здесь только реализация.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

TokenType = Literal["access", "refresh"]


def _create_token(subject: str, expires_delta: timedelta, token_type: TokenType) -> str:
    settings = get_settings()
    now = utc_now()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return str(jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def create_access_token(subject: str, expires_delta: timedelta) -> str:
    """Создаёт access JWT для пользователя `subject` (обычно — str(user.id))."""
    return _create_token(subject, expires_delta, "access")


def create_refresh_token(subject: str, expires_delta: timedelta) -> str:
    """Создаёт refresh JWT.

    Выпуск refresh-токена из `/auth/login` и сам эндпоинт `/auth/refresh`
    (с ревокацией) — Roadmap этого шага: ревокация требует хранилища
    (Redis/БД blocklist), которого пока нет в рамках Этапа 5. Функция готова
    как extension point — контракт не меняется, когда до этого дойдёт очередь.
    """
    return _create_token(subject, expires_delta, "refresh")


def decode_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
    """Валидирует и декодирует JWT.

    Бросает `UnauthorizedError` (не голый JWTError) при истёкшем/невалидном
    токене или несовпадении `type` — вызывающий код (dependencies.py) не
    должен знать про python-jose, только про доменные исключения.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise UnauthorizedError("Невалидный или истёкший токен") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError(f"Ожидался токен типа {expected_type!r}")

    return payload


def utc_now() -> datetime:
    return datetime.now(UTC)
