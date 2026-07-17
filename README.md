# TaskFlow

Современная система управления задачами (Kanban, realtime, AI-ассистент) —
портфолио-проект, демонстрирующий production-подход к архитектуре на Python/FastAPI + React.

> **Статус: Этап 7 из 13 — Comments + Notifications REST API.**
> Это техническая заглушка README. Полная версия — с описанием продукта,
> скриншотами, GIF-демо и roadmap — появится на Этапе 13 (см.
> [`docs/01-architecture-and-design.md`](docs/01-architecture-and-design.md), раздел 6).

## Документация

- [Архитектура и дизайн-документ](docs/01-architecture-and-design.md) — PRD, архитектура, схема БД, API-дизайн, план разработки
- [ADR](docs/adr/) — ключевые архитектурные решения и их обоснование
- [PROJECT_STATE](docs/PROJECT_STATE.md) — что сделано по этапам, что дальше

## Быстрый старт (Docker)

```bash
git clone <repo>
cd taskflow
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000/docs (Swagger UI)
- Frontend: http://localhost:3000
- Health check: http://localhost:8000/health

> На момент Этапа 3 backend/frontend поднимаются и отвечают на health-check,
> но бизнес-логика (БД, аутентификация, задачи) ещё не подключена — это
> Этапы 4–10. `docker compose up` уже сейчас поднимает весь стек одной
> командой, это и было целью этого этапа.

## Быстрый старт (без Docker)

Локальный запуск backend/frontend по отдельности, без контейнеров, описан в
`backend/README.md` и `frontend/README.md` — полезно для разработки с hot-reload
без пересборки образа на каждое изменение.

## Структура репозитория

```
taskflow/
├── backend/                  # FastAPI, SQLAlchemy 2.0, модульный монолит
│   ├── Dockerfile
│   └── app/
├── frontend/                 # React + TypeScript + TailwindCSS
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                     # архитектура, ADR, PROJECT_STATE
├── .github/workflows/ci.yml  # lint + typecheck + test + docker build
├── docker-compose.yml
├── .pre-commit-config.yaml
└── Makefile
```

## Команды разработки

| Команда | Действие |
|---|---|
| `make dev` | Поднять весь стек через `docker compose up --build` |
| `make down` | Остановить и убрать контейнеры |
| `make logs` | Логи всех сервисов (`docker compose logs -f`) |
| `make build` | Пересобрать образы без запуска |
| `make install` | Локальный venv + node_modules (для IDE, pre-commit) |
| `make migrate` | Применить Alembic-миграции (`alembic upgrade head`) |
| `make seed` | Наполнить БД demo-данными — идемпотентно, безопасно перезапускать |
| `make test` | Backend test suite (pytest, включая repository/alembic/DB-тесты) |
| `make lint` | ruff + mypy + oxlint |
| `make format` | black + ruff --fix |

## Pre-commit

```bash
pip install pre-commit  # или: pipx install pre-commit
pre-commit install
```
Хуки: ruff, black, mypy (backend), trailing-whitespace, end-of-file-fixer, check-yaml — прогоняются перед каждым коммитом.

## База данных

15 таблиц по схеме из `docs/01-architecture-and-design.md` (раздел 4), Alembic-миграции
в `backend/alembic/`. Локально (без Docker) нужен собственный Postgres:

```bash
createdb taskflow
make migrate   # alembic upgrade head
make seed      # demo workspace/user/project/tasks — идемпотентно
```

**Тесты, требующие БД**: repository-тесты, тест подключения и тест самой
Alembic-миграции используют отдельные `taskflow_test` и
`taskflow_migrations_test` (создаются автоматически схемой, но сами БД
должны существовать — см. `backend/tests/conftest.py` и
`backend/tests/test_alembic_migrations.py` за обоснованием, почему их две).
В CI (`.github/workflows/ci.yml`) поднимается сервис-контейнер Postgres и
создаёт обе БД перед прогоном тестов — локально это нужно сделать один раз
вручную, аналогично `taskflow`.

## CI/CD

`.github/workflows/ci.yml`: backend (создание тестовых БД → ruff → black →
mypy → pytest → alembic upgrade head → seed idempotency check), frontend
(lint → build), затем сборка обоих Docker-образов для верификации. Деплоя
пока нет — это Этап 12.

## Стек

**Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis, Celery, JWT
**Frontend**: React, TypeScript, TailwindCSS, TanStack Query, Zustand
**Infra**: Docker, Docker Compose, Nginx, GitHub Actions CI/CD

## Лицензия

[MIT](LICENSE)
