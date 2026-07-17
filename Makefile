.PHONY: install dev down logs build test lint format migrate seed

# ---------------------------------------------------------------------------
# `make dev` теперь поднимает полный стек через docker compose (Этап 3).
# `make test` / `lint` / `format` по-прежнему работают против локального
# venv/node_modules — быстрее для цикла разработки (не нужно пересобирать
# образ на каждый прогон pytest), и то же самое использует CI (.github/workflows/ci.yml).
# `make install` нужен, чтобы локальный инструментарий (mypy в pre-commit,
# IDE autocomplete) продолжал работать вне контейнера.
# ---------------------------------------------------------------------------

install:
	cd backend && python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

test:
	cd backend && ./.venv/bin/pytest

lint:
	cd backend && ./.venv/bin/ruff check app tests scripts alembic && ./.venv/bin/mypy app scripts
	cd frontend && npm run lint

format:
	cd backend && ./.venv/bin/black app tests scripts && ./.venv/bin/ruff check app tests scripts alembic --fix

migrate:
	cd backend && ./.venv/bin/alembic upgrade head

seed:
	cd backend && ./.venv/bin/python -m scripts.seed
