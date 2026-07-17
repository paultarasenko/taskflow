"""Тест самой миграции — реальный `alembic` через subprocess (то же самое,
что делает `make migrate`), с DATABASE_URL, указывающим на тестовую БД.

Через subprocess, а не через `alembic.command` API напрямую: `get_settings()`
в основном процессе pytest закэширован через `@lru_cache` с DATABASE_URL из
.env, и переопределить его "на лету" для одного теста без гонок с другими
тестами — сложнее и хрупче, чем просто запустить тот же CLI, которым
пользуется разработчик.
"""

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _migrations_test_database_url() -> str:
    """Отдельная БД, не `taskflow_test` из conftest.py: там схема создаётся
    через `Base.metadata.create_all` (для repository-тестов, без накладных
    расходов Alembic на каждый прогон), а здесь та же самая alembic-миграция
    реально применяется/откатывается — если бы это была одна и та же БД,
    `create_all` и `alembic upgrade` конфликтовали бы за то, кто уже создал
    таблицы.
    """
    base_url = get_settings().database_url
    prefix, _, db_name = base_url.rpartition("/")
    return f"{prefix}/{db_name}_migrations_test"


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": _migrations_test_database_url()}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_alembic_upgrade_head_applies_cleanly() -> None:
    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr


def test_alembic_downgrade_then_upgrade_is_reversible() -> None:
    """Регрессионный тест на баг, пойманный при разработке этой миграции:
    autogenerate не включает удаление PostgreSQL ENUM-типов при downgrade
    (они не привязаны к жизненному циклу таблицы), из-за чего повторный
    upgrade падал с `DuplicateObjectError: type ... already exists`. Исправлено
    вручную в alembic/versions/95133f460418_initial_schema.py — этот тест
    не даёт регрессии вернуться незамеченной.
    """
    down = _run_alembic("downgrade", "base")
    assert down.returncode == 0, down.stderr

    up = _run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr
