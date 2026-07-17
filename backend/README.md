# TaskFlow — Backend

FastAPI-бэкенд TaskFlow. Полное описание архитектуры, модели данных и API — в
[`docs/01-architecture-and-design.md`](../docs/01-architecture-and-design.md) и
[`docs/adr/`](../docs/adr/).

> Техническая заглушка. Полноценный README проекта (с скриншотами, roadmap
> и инструкцией для рекрутера) появится на Этапе 13.

## Быстрый старт (локально, без Docker)

Нужен свой PostgreSQL (Docker поднимает его сам — см. корневой README) —
приложение реально подключается к БД с Этапа 4, `/health/ready` вернёт 503
без неё.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

createdb taskflow          # если ещё не создана
cp ../.env.example ../.env # DATABASE_URL по умолчанию рассчитан на localhost:5432

alembic upgrade head       # применить миграции
python -m scripts.seed     # demo workspace/user/project/tasks (не обязательно)

uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Readiness (проверяет реальное соединение с Postgres): http://localhost:8000/health/ready

## Тесты

Часть тестов стучится в настоящую БД (repository-тесты, тест подключения,
тест самой Alembic-миграции) — нужны ещё две БД, `taskflow_test` и
`taskflow_migrations_test` (почему две, а не одна — см. docstring
`tests/conftest.py` и `tests/test_alembic_migrations.py`):

```bash
createdb taskflow_test
createdb taskflow_migrations_test
pytest
```

## Database layer

- `app/database/session.py` — async engine + session factory, `get_session()`
  коммитит в конце запроса автоматически, откатывает при исключении.
- `app/database/mixins.py` — UUID PK, timestamps, soft delete (переиспользуются
  всеми 15 моделями, см. ADR-0003 и раздел 4.2 архитектурного документа).
- `app/database/repository.py` — generic `BaseRepository`, от которого
  наследуются репозитории 7 модулей (users, workspace, projects, tasks,
  comments, notifications, ai).
- `app/database/models_registry.py` — единая точка импорта всех моделей;
  Alembic, seed-скрипт и `main.py` импортируют этот модуль, а не
  перечисляют модели по отдельности (см. docstring файла — там же история
  бага, из-за которого это появилось).
- `alembic/` — async migration environment, URL читается из `Settings`, не
  из `alembic.ini`.
- `scripts/seed.py` — идемпотентное наполнение demo-данными (`make seed`).

## Статус

Этап 4 из 13 — Database layer + Alembic. Аутентификация и бизнес-логика
модулей — следующие этапы (см. корневой `docs/01-architecture-and-design.md`, раздел 6).
