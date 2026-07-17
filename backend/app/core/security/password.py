"""Хэширование паролей — Argon2id через passlib (см. security-чек-лист,
docs/01-architecture-and-design.md, 7.4).

Реализовано на Этапе 4 раньше, чем формально запланировано (Этап 5) —
не потому что архитектура меняется, а потому что seed-скрипту (`scripts/seed.py`)
нужен настоящий хэш для demo-пользователя, а не заглушка. JWT, register/login
эндпоинты и RBAC-wiring остаются Этапом 5 без изменений — здесь только сама
функция хэширования, чей контракт (сигнатура) был зафиксирован ещё на Этапе 2.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return str(_pwd_context.hash(plain_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(_pwd_context.verify(plain_password, hashed_password))
