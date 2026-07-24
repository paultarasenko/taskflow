# TaskFlow — Project State

Живой журнал прогресса по этапам. Обновляется в конце каждого этапа —
что сделано, что проверено, что дальше. Полная детализация плана — в
[`docs/01-architecture-and-design.md`](01-architecture-and-design.md), раздел 6.

---

## Этап 1 — Architecture & Design ✅

PRD, архитектура (плоская модульная структура после review), схема БД (ERD,
soft delete, `ACTIVITY_LOG`), API-дизайн (пагинация, версионирование),
5 ADR, стратегия тестирования, план деплоя, Developer Experience.

**Результат**: `docs/01-architecture-and-design.md` (v1.2), `docs/adr/0001-0005`.

---

## Этап 2 — Repository Skeleton ✅

Backend: FastAPI-скелет, 9 модулей по единому шаблону (`model/schema/repository/service/router`),
`core/`, `database/`, `shared/`, security-заготовки, `main.py` подключает все роутеры.
Frontend: Vite + React 19 + TS, Tailwind v4, TanStack Query, Zustand, `features/`
зеркалит backend-модули.

**Проверено**: pytest (3/3) ✅, ruff ✅, black ✅, mypy --strict (71 файл) ✅,
реальный запуск uvicorn + curl `/health` ✅, `npm run build` ✅, `npm run lint` ✅.

---

## Этап 3 — Docker, Environment, CI/CD skeleton ✅

### Что сделано
- `backend/Dockerfile` — multi-stage (builder + runtime), non-root user (uid 1000),
  зависимости из `pyproject.toml` (без dev-extras), healthcheck через `python -c`
  (без лишнего curl/wget в образе).
- `frontend/Dockerfile` — multi-stage (node:22-alpine build → nginx:1.27-alpine runtime),
  `VITE_API_URL` как build-arg (осознанный трейд-офф: Vite встраивает env в бандл на
  этапе build, не в рантайме — задокументировано в самом Dockerfile).
- `frontend/nginx.conf` — SPA fallback (`try_files ... /index.html`), кэширование
  `/assets/`, gzip.
- `docker-compose.yml` — 4 сервиса (`postgres`, `redis`, `api`, `frontend`), healthchecks
  у всех, `depends_on: condition: service_healthy` у `api`, именованный volume для
  Postgres, отдельная bridge-сеть. **Без Celery worker** — сознательно: единственный
  потребитель очереди (AI-слой) появляется на Этапе 10, до этого воркер простаивал бы
  без единой задачи.
- `.env.example` — уже полностью покрывал нужные переменные с Этапа 2
  (`POSTGRES_USER/PASSWORD/DB`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`,
  `VITE_API_URL` и т.д.); имена **не переименовывались**.
- `Makefile` — `make dev` теперь `docker compose up --build`; добавлены `down`,
  `logs`, `build`; `test`/`lint`/`format` намеренно остались на локальном
  venv/node_modules (быстрее для цикла разработки, то же самое использует CI).
- `.pre-commit-config.yaml` — ruff, black, mypy (**local hook**, не mirrors-mypy —
  чтобы видеть реальные зависимости проекта без ложных ошибок импорта),
  trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files.
- `.github/workflows/ci.yml` — backend (ruff → black → mypy → pytest), frontend
  (lint → build), затем `docker build` обоих образов (только после того как
  lint/test прошли). Без deployment-джобы.
- `backend/.dockerignore`, `frontend/.dockerignore`.
- Обновлены `README.md` (docker-first quick start) и этот файл.

### Что проверено и как
| Проверка | Статус | Как проверено |
|---|---|---|
| `backend/Dockerfile` — синтаксис и логика | Ревью вручную | Docker daemon недоступен в среде разработки (см. ниже) |
| `frontend/Dockerfile` — синтаксис и логика | Ревью вручную | Аналогично |
| `docker-compose.yml` — переменные покрыты `.env.example` | ✅ Пройдено | `grep` всех `${VAR}` в compose-файле против ключей `.env.example` — полное совпадение (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `VITE_API_URL`) |
| `docker-compose.yml` — валидность YAML | Не выполнено | См. ограничение среды ниже |
| `.pre-commit-config.yaml` — синтаксис YAML | Ревью вручную | — |
| `.github/workflows/ci.yml` — синтаксис YAML | Ревью вручную | — |

### ⚠️ Ограничение среды разработки
В песочнице, где выполняется эта сессия, **нет полноценного Docker daemon**, а
сетевой доступ ограничен allowlist'ом доменов, в который не входит
`registry-1.docker.io`. Попытка реального `docker build`/`podman build`
подтвердила это явной ошибкой сети при попытке стянуть `python:3.12-slim`
(`403, Host not in allowlist: registry-1.docker.io`).

Соответственно, **не выполнены и не могут считаться подтверждёнными** в этой
сессии:
- `docker build ./backend` / `docker build ./frontend` — реальная сборка образов
- `docker compose config` — валидация compose-файла инструментом (пробовал
  установить `docker-compose-plugin` — недоступен в apt-репозитории этой среды;
  `python3-compose` (legacy v1 loader) ставится, но не даёт CLI-бинарник для
  `config`-валидации без дополнительной обвязки)
- `docker compose up` — реальный подъём стека, healthcheck-и в рантайме

Файлы написаны и проверены вручную (построчный ревью на соответствие
Dockerfile best practices и Compose Specification), но **первая реальная
проверка должна пройти в CI** (`.github/workflows/ci.yml`, джоба `docker-build`)
или локально у разработчика с Docker Desktop/Engine — это первое, что стоит
сделать сразу после мержа этого этапа, до перехода на Этап 4.

### Следующий этап (на момент завершения Этапа 3)
**Этап 4 — Database layer + Alembic migrations**: реальные SQLAlchemy-модели
по схеме из `docs/01-architecture-and-design.md` (раздел 4), Alembic-миграции,
`database/session.py` (engine + session factory), первый прогон `make migrate`
против поднятого через `docker compose` Postgres — и заодно первая настоящая
проверка того, что `docker-compose.yml` из Этапа 3 действительно рабочий.

---

## Этап 4 — Database layer + Alembic ✅

### Расхождения с исходным ТЗ этапа (сверено с уже принятыми решениями Этапа 1)
Прежде чем писать код, три пункта из типового чек-листа Этапа 4 были сверены
с `docs/01-architecture-and-design.md` v1.2 и explicitly отклонены как
устаревшие относительно уже принятых решений:
1. **`Attachment`** — не реализован. Исключён из Portfolio MVP на Этапе 1
   (Roadmap).
2. **`TaskHistory`** — не реализован как отдельная сущность. Вместо этого —
   `ActivityLog` (полиморфная `entity_type`/`entity_id`), как было решено на
   Этапе 1 при обобщении.
3. **`tasks.search_vector` (tsvector)** — не добавлен. Полнотекстовый поиск
   вынесен в Roadmap на Этапе 1 вместе с отдельным поисковым модулем.

### Что сделано

**Database layer**
- `app/database/mixins.py` — `UUIDPrimaryKeyMixin`, `TimestampMixin`,
  `UpdatedAtMixin`, `SoftDeleteMixin`, переиспользуются 15 моделями.
- `app/database/session.py` — реальный async engine (`pool_pre_ping=True`),
  `session_factory`, `get_session()` с auto-commit/rollback на границе
  запроса (см. ADR-0006).
- `app/database/repository.py` — generic `BaseRepository[ModelType]`
  (get_by_id, list, add, soft-delete-aware delete), от него наследуются
  репозитории 7 модулей.
- `app/database/models_registry.py` — единая точка импорта всех 15 моделей;
  устраняет класс багов с нерезолвящимися строковыми relationship-таргетами
  в отдельных entry points (Alembic, seed, тесты) — см. docstring файла.
- `app/core/dependencies.py` — `get_db_session`/`DbSession` подключены к
  реальной сессии вместо `NotImplementedError`.
- `app/core/security/password.py` — Argon2id через passlib реализован
  раньше срока (формально Этап 5), поскольку seed-скрипту нужен настоящий
  хэш. JWT/эндпоинты остаются Этапом 5.
- `/health/ready` — реальная проверка `SELECT 1` против Postgres (Redis —
  остаётся TODO, используется только с Этапа 8).

**15 SQLAlchemy-моделей** по 7 модулям (users, workspace, projects, tasks,
comments, notifications, ai) + `auth/model.py` явно документирует отсутствие
собственной таблицы (переиспользует `users.User`). Все Enum-поля — реальные
Postgres ENUM-типы (8 штук), UUID PK везде (ADR-0003), soft delete на
workspaces/projects/tasks (ADR/раздел 4.2).

**Alembic** — async migration environment (`alembic/env.py`), URL берётся из
`Settings`, не из `alembic.ini`. Одна миграция `initial_schema`
(autogenerate), с ручной правкой `downgrade()` — см. "Пойманные баги" ниже.

**Repository layer** — 7 модулей, реальные Postgres-реализации поверх
`BaseRepository`, плюс доменные запросы: `UserRepository.get_by_email`,
`WorkspaceRepository.list_for_user`, `TaskRepository.list_by_project`
(фильтры status/priority — контракт `GET /projects/{id}/tasks`, раздел 5.5),
`ActivityLogRepository.list_for_entity` и др.

**Seed** (`scripts/seed.py`, `make seed`) — идемпотентный (проверка по email
demo-пользователя): 1 workspace, 1 user, 1 project, доска с 4 колонками
(Ideas/Development/Testing/Done), 7 задач, распределённых по статусам. Это
минимальный работающий механизм, а не финальный богатый seed на 45
задач/12 пользователей — та версия остаётся Этапом 13 (раздел 9.5).

**Testing** — `tests/conftest.py` (сессионная фикстура схемы через
`create_all`, транзакционная `db_session` на каждый тест), `test_database_connection.py`,
`test_alembic_migrations.py` (реальный subprocess `alembic upgrade/downgrade`
против отдельной `taskflow_migrations_test`), repository-интеграционные
тесты для users/workspace/tasks (7 новых тестов). Итого 13/13 passed.

**ADR-0006** — Generic BaseRepository + session-per-request auto-commit
(`docs/adr/0006-repository-and-session-lifecycle.md`), добавлен в реестр
раздела 10 архитектурного документа.

**CI** — `.github/workflows/ci.yml`: добавлен Postgres service-контейнер,
шаг создания `taskflow_test`/`taskflow_migrations_test`, ruff/black/mypy
расширены на `scripts/`+`alembic/`, добавлены шаги `alembic upgrade head` и
seed idempotency smoke-check.

### Три реальных бага, пойманных живым прогоном (не просто по документации)
1. **Alembic autogenerate не удаляет Postgres ENUM-типы при downgrade** —
   `op.drop_table(...)` не трогает независимые от таблиц ENUM-объекты;
   повторный `upgrade` после `downgrade` падал с `DuplicateObjectError`.
   Исправлено вручную в `downgrade()` (явный `postgresql.ENUM(...).drop(...)`
   на все 8 типов), закреплено регрессионным тестом
   `test_alembic_downgrade_then_upgrade_is_reversible`.
2. **SQLAlchemy не резолвит строковые relationship-таргеты
   (`Mapped[list["Comment"]]`) без импорта соответствующего класса в рантайме
   процесса** — `scripts/seed.py` падал на `InvalidRequestError: failed to
   locate a name ('Comment')`, потому что импортировал только используемые
   напрямую модели. Решено централизованно через `models_registry.py`
   (см. выше), а не точечными `noqa`-импортами в каждом файле.
3. **pytest-asyncio 1.x: два разных ключа scope для фикстур и для тестов**
   (`asyncio_default_fixture_loop_scope` и `asyncio_default_test_loop_scope`)
   — несовпадение между ними давало `RuntimeError: ... attached to a
   different loop` на всех repository-тестах, а `AsyncEngine`, созданный на
   уровне модуля (до старта event loop), давал ту же ошибку даже после
   выравнивания scope. Оба исправления — синхронизация обоих ключей на
   `session` и перенос создания engine внутрь async-фикстуры — задокументированы
   прямо в `tests/conftest.py` и `pyproject.toml`.

### Проверки — реально выполненные
| Проверка | Команда | Результат |
|---|---|---|
| Backend tests | `pytest` | ✅ 13/13 passed |
| Ruff | `ruff check app tests scripts alembic` | ✅ All checks passed |
| Black | `black --check app tests scripts` | ✅ 85 files unchanged |
| MyPy --strict | `mypy app scripts` | ✅ 76 файлов, 0 ошибок |
| Alembic upgrade (чистая БД) | `alembic upgrade head` | ✅ 16 таблиц, 8 enum-типов |
| Alembic downgrade | `alembic downgrade base` | ✅ таблицы и enum-типы удалены полностью |
| Alembic upgrade (повторно, регрессия) | `alembic upgrade head` | ✅ прошёл после фикса enum-drop |
| Seed | `python -m scripts.seed` (дважды подряд) | ✅ создаёт один раз, второй прогон — no-op |
| `/health/ready` | реальный `SELECT 1` | ✅ 200 при живом Postgres, 503 при недоступном |

Верификация проводилась против реального PostgreSQL 16, поднятого напрямую
через `apt`/`pg_ctlcluster` в этой среде (Docker недоступен — то же
ограничение, что и на Этапе 3), с теми же `POSTGRES_USER/PASSWORD/DB`, что
заданы в `.env.example`, — то есть эквивалентно тому, что даст
`docker compose up postgres`.

### Не проверено в этой сессии (то же ограничение среды, что и Этап 3)
`docker build`/`docker compose up` по-прежнему не выполнить — нет Docker
daemon, сетевой allowlist блокирует `registry-1.docker.io`. Совместимость
`docker-compose.yml` с новым DB-слоем проверена статически (переменные
`DATABASE_URL`/`POSTGRES_*`, которые ожидает `api`-сервис, совпадают с тем,
что реально сработало в локальном прогоне) и через реальный Postgres вне
Docker — функционально эквивалентно, но не то же самое, что "поднять сам
контейнер и увидеть его healthy". Первая реальная проверка —
`.github/workflows/ci.yml`, джоба `docker-build`.

### Следующий этап (на момент завершения Этапа 4)
**Этап 5 — Authentication**: JWT access+refresh, register/login/logout,
RBAC-wiring (`core/security/permissions.py` уже готов с Этапа 2, реально
используется впервые), эндпоинты `auth/router.py`. `UserRepository` и
`hash_password`/`verify_password` уже реализованы (Этап 4) — Этап 5
подключает их к HTTP-слою и JWT.

---

## Этап 5 — Authentication, Authorization, CRUD API ✅

### Конфликт с ранее принятым API-дизайном (зафиксировано перед началом)
Раздел 5.4–5.5 архитектурного документа (Этап 1) проектировал вложенные
роуты: `POST /workspaces/{ws_id}/projects`, `GET /projects/{id}/tasks`. ТЗ
Этапа 5 явно требует плоские: `POST /projects`, `POST /tasks`, `GET /tasks`.

Рассмотренные варианты: (1) оставить вложенные — нарушает буквальное ТЗ
Этапа 5; (2) полностью перейти на плоские — расходится с задокументированным
дизайном; (3) плоские роуты снаружи, `workspace_id`/`project_id` как
обязательный параметр (body для POST, query для GET), вся repository-логика
без изменений. **Выбран вариант 3** — минимальное расхождение, ни один
репозиторий не переписывался, только форма URL.

### Что реализовано

**JWT** (`core/security/jwt.py`) — access/refresh через python-jose, claim
`type` различает токены (без него refresh можно было бы подсунуть вместо
access). `create_refresh_token` реализована, но `/auth/refresh` и
`/auth/logout` — осознанный extension point: нужно хранилище ревокации
(Redis/БД blocklist), которого нет в рамках этого шага.

**Auth flow**: `POST /auth/register` (409 на дубль email, пароль никогда не
возвращается — просто не объявлен в `UserRead`, не вычищается постфактум),
`POST /auth/login` (401 с одинаковым сообщением на "нет email" и "неверный
пароль" — не даёт атакующему подтверждения через разницу ответов),
`GET /users/me`.

**RBAC-основа** (`core/dependencies.py`): `get_current_user` (HTTPBearer —
не OAuth2PasswordBearer, API принимает JSON, не form-encoded; в Swagger UI
даёт простую кнопку "Authorize" с полем для токена), `require_workspace_member`
как FastAPI-зависимость для path-based роутов (`/workspaces/{id}`), и
эквивалентная проверка внутри `ProjectService`/`TaskService` для эндпоинтов,
где `workspace_id`/`project_id` приходит из тела/query, а не из пути.
`WorkspaceRole`/`require_workspace_role` (Этап 2) впервые реально
используются.

**CRUD API**:
- Workspaces: create/list/get, автосоздание `WorkspaceMember(role=OWNER)`
  для создателя.
- Projects: create/list/get, **при создании проекта автоматически
  создаётся Board + 4 колонки** (Ideas/Development/Testing/Done, тот же
  паттерн, что в `scripts/seed.py`) — своих board/column-эндпоинтов в этом
  шаге ещё нет (Kanban UI — Этап 9), но без доски задачу некуда положить.
  Кросс-модульная зависимость сделана через `TaskService.create_default_board`,
  не через прямой доступ `ProjectService` к репозиторию модуля `tasks`
  (раздел 3.1).
- Tasks: полный CRUD + PATCH с валидацией переходов статуса через
  `ALLOWED_TRANSITIONS` из `entity.py` (Этап 2/ADR-0004) — использована
  напрямую как проверка, без полного маппинга ORM↔TaskEntity (тот остаётся
  extension point, если бизнес-правил вокруг Task наберётся больше).
  DELETE — soft delete (уже существующий `BaseRepository.delete`, Этап 4).

**Пагинация** — `WorkspaceRepository.list_for_user` и
`ProjectRepository.list_for_workspace` (Этап 4) расширены `limit`/`offset`
(были без пагинации) для консистентности со всеми list-эндпоинтами (раздел
5.0); `TaskRepository.list_by_project` уже поддерживал это с Этапа 4.
`BaseRepository` получил `save()` — сервисы больше не лезут в
`repository.session` напрямую для flush изменённого объекта.

### Проверки — реально выполненные
| Проверка | Результат |
|---|---|
| Backend tests | ✅ 28/28 passed (20 из Этапов 1–4 не сломаны + 8 новых на auth/CRUD/RBAC) |
| Ruff | ✅ All checks passed |
| Black --check | ✅ 87 files unchanged |
| MyPy --strict | ✅ 76 файлов, 0 ошибок |
| Реальный запуск (uvicorn + curl) | ✅ register → login → `/users/me` (200 с токеном, 401 без) |
| OpenAPI / `/docs` | ✅ все 10 эндпоинтов видны в `/openapi.json` |

Тесты используют изолированную транзакционную БД даже для полного
HTTP-стека — `client`-фикстура (`tests/conftest.py`) теперь переопределяет
`get_db_session` на ту же rollback-per-test сессию, что и repository-тесты,
вместо реального dev-engine приложения. Иначе auth/CRUD-тесты либо
засоряли бы dev-базу, либо падали бы на повторный прогон из-за уникальности
email.

### Известные ограничения / extension points, оставленные сознательно
1. `/auth/refresh`, `/auth/logout` — нужна ревокация (Redis/БД blocklist).
2. RBAC — только членство в workspace проверяется (`require_workspace_member`
   / эквивалент в сервисах), различие ролей (Owner/Admin/Member) внутри
   проверки не используется нигде, кроме `require_workspace_role`, который
   пока не вызывается ни одним эндпоинтом. Не enterprise-RBAC (не просили),
   но основа, которую легко ужесточить (например: только Owner/Admin может
   удалить проект) без смены контракта зависимостей.
3. Board/Column — нет отдельных эндпоинтов, только автосоздание при
   создании проекта. Полноценный Kanban CRUD (переименование колонок,
   reorder, WIP-лимиты) — Этап 9.
4. `docker build`/`docker compose up` — то же сетевое ограничение среды, что
   на Этапах 3–4, не проверено в этой сессии.

### Следующий этап (на момент завершения Этапа 5)
**Этап 6 — Users и Workspace (расширенное управление)**: приглашение
участников по email, изменение/удаление ролей (`require_workspace_role`
впервые реально используется для проверки минимальной роли), настройки
аккаунта пользователя. Либо, альтернативно (на усмотрение владельца
проекта) — реализация WebSocket realtime (Этап 8) поверх уже готового CRUD.

---

## Этап 6 — Users и Workspace (управление участниками, приглашения, аккаунт) ✅

### Новая сущность вне исходного ERD (см. ADR-0007)
Исходный API-дизайн (Этап 1, раздел 5.3) предполагал разовое
`POST /workspaces/{id}/invite` без отдельной сущности приглашения. ТЗ
Этапа 6 явно потребовало полноценный жизненный цикл (create → публичный
статус → accept), что не покрывается немедленным добавлением участника —
понадобилась новая таблица `invitations`, новая Alembic-миграция
(`28fe033d807a_add_invitations`), обновлён `models_registry.py`. Решение и
все проектные детали (вычисляемый, не хранимый статус; разделение
"добавить существующего" vs "пригласить кого угодно") — в ADR-0007.

### Что реализовано

**Workspace members** (`workspace/service.py`, расширен, не переписан):
`add_member` (только существующие пользователи — для остальных явное
сообщение "используйте приглашение"), `list_members` (eager-load `.user`
через `selectinload`, без N+1), `change_member_role`, `remove_member`.
RBAC — `require_workspace_role(actor_role, WorkspaceRole.ADMIN)` (Этап 2)
использован по-настоящему впервые. Инварианты: роль Owner нельзя сменить
или назначить через этот эндпоинт (передача владения — Roadmap), Owner
нельзя удалить, участник может удалить сам себя ("leave"), удаление
чужого требует ADMIN+.

**Invitations**: `POST /workspaces/{id}/invitations` (ADMIN+, проверка на
дубль pending-приглашения и на "уже участник"), `GET /invitations/{token}`
(без авторизации), `POST /invitations/{token}/accept` (сверяет
`current_user.email == invitation.email`). Email-доставка — extension
point, токен возвращается прямо в ответе `POST .../invitations` (ADR-0007).

**Account settings** (`users/service.py`, `users/router.py`, из stub):
`PATCH /users/me` (частичное обновление — full_name/avatar_url; email
осознанно не редактируется здесь — смена требует подтверждения, Roadmap),
`POST /users/me/password` (проверка текущего пароля через уже
существующий `verify_password`, Этап 4).

### Проверки — реально выполненные
| Проверка | Результат |
|---|---|
| Backend tests | ✅ 49/49 passed (28 из Этапов 1–5 не сломаны + 21 новый: 10 workspace members, 6 invitations, 5 account settings) |
| Ruff | ✅ All checks passed |
| Black --check | ✅ 90 files unchanged |
| MyPy --strict | ✅ 76 файлов, 0 ошибок |
| Alembic upgrade → downgrade → upgrade (чистая БД) | ✅ 17 таблиц (16 из Этапа 4 + invitations), полностью обратимо дважды подряд |
| Seed на чистую схему | ✅ применяется без ошибок |
| Живой E2E (uvicorn + curl) | ✅ register → login → create workspace → create invitation, реальные SQL INSERT в логах |

### Реальный баг, пойманный тестами (не по документации)
**Ленивая подгрузка SQLAlchemy-relationship в синхронном контексте
Pydantic-валидации.** `WorkspaceMemberRead.model_validate(new_member)` для
только что созданного (не через SELECT) `WorkspaceMember` падал с
`MissingGreenlet` при обращении к `.user` — async lazy-load требует
awaited-контекста, которого у Pydantic `model_validate` (обычный синхронный
getattr) нет. Исправлено двумя способами: (1) `get_membership` теперь всегда
делает `selectinload(.user)`, (2) `add_member`/`accept_invitation` вручную
присваивают `.user` только что созданному объекту вместо перезапроса.
Поймано первым же прогоном `test_owner_can_add_existing_user_as_member`,
не предугадано заранее.

### Известные ограничения / extension points, оставленные сознательно
1. `/auth/refresh`, `/auth/logout` — не реализованы с Этапа 5, требуют
   ревокации (без изменений в этом этапе).
2. Email-доставка приглашений — не реализована (см. ADR-0007), токен
   возвращается в API-ответе напрямую.
3. Передача владения (смена Owner) — не поддерживается ни одним эндпоинтом,
   явный 403 при попытке через `PATCH /members/{user_id}`.
4. `docker build`/`docker compose up` — то же сетевое ограничение среды,
   что на Этапах 3–5, не проверено в этой сессии.

### Следующий этап (на момент завершения Этапа 6)
**Этап 7 — Realtime (WebSocket)**: `websocket/connection_manager.py` (стаб
с Этапа 2) получает реальную реализацию поверх Redis Pub/Sub, события
`task.created/updated/moved`, `comment.created`, `notification.created`
(контракт зафиксирован в разделе 5.10 архитектурного документа). Либо, на
усмотрение владельца проекта — Comments/Notifications REST API (модули
существуют как стабы с Этапа 2, ещё не реализованы) как более простое
продолжение уже готового паттерна CRUD.

---

## Этап 7 — Comments + Notifications REST API ✅

Выбрано после аудита (см. переписку) — направление с меньшим риском:
продолжение уже 5 раз подтверждённого паттерна Repository/Service/Router,
без новой инфраструктуры (WebSocket/Redis остаются на следующий этап).

### Обнаруженный по ходу пробел: назначение задачи
`POST /tasks/{id}/assignees` был в исходном API-дизайне (раздел 5.5) с
Этапа 1, но не реализовывался — только модель `TaskAssignee` (Этап 4), без
репозитория и эндпоинта. Требование "уведомление при назначении" не могло
быть выполнено без механизма назначения, поэтому реализован в рамках этого
этапа: `PostgresTaskAssigneeRepository` (новый), `TaskService.assign_user`
(проверяет, что назначаемый — участник того же workspace; 409 на повторное
назначение), эндпоинт, `TaskAssigneeRead`-схема.

### Что реализовано

**Notifications**: `GET /notifications` (пагинация), `PATCH /notifications/{id}/read`
(проверка владения — чужое уведомление пометить нельзя, 403). Плюс
внутренние `notify_task_assigned`/`notify_new_comment` в `NotificationService`
— вызываются другими сервисами кросс-модульно (раздел 3.1), сама запись в
БД остаётся ответственностью модуля `notifications`.

**Comments**: `POST /tasks/{id}/comments`, `GET /tasks/{id}/comments`
(пагинация — расширен `list_by_task`, тот же паттерн, что дважды применялся
в Этапах 5–6), `PATCH /comments/{id}`, `DELETE /comments/{id}`. RBAC:
редактировать/удалять может автор комментария или ADMIN+ workspace
(`require_workspace_role`, тот же примитив, что в `WorkspaceService` с
Этапа 6). Роутер — единственный в проекте без общего `prefix`: контракт
смешивает вложенный (`/tasks/{id}/comments`) и плоский (`/comments/{id}`)
пути в одном модуле, явный полный путь на каждый route.

**Уведомления при создании комментария**: автор задачи уведомляется о
новом комментарии, если комментирует не он сам (self-comment не создаёт
уведомление).

### Известное, сознательно не устранённое дублирование
`_require_project_access` (резолвинг project → workspace → membership)
теперь продублирован **трижды**: `TaskService`, и с этого этапа —
`CommentService`. Ранее (Этап 5) было явно написано условие для выноса в
общую утилиту — "если проверка понадобится третьему модулю". Момент
настал, но рефакторинг уже протестированного `TaskService`/`ProjectService`
не запрашивался явно в задаче этого этапа — решено не трогать работающий
код без прямого запроса (см. Правила работы). **Кандидат на отдельный
этап технического долга.**

### Проверки — реально выполненные
| Проверка | Результат |
|---|---|
| Backend tests | ✅ 63/63 passed (49 из Этапов 1–6 не сломаны + 14 новых: 5 assignment/notifications, 9 comments) |
| Ruff | ✅ All checks passed |
| Black --check | ✅ 92 files unchanged |
| MyPy --strict | ✅ 76 файлов, 0 ошибок |
| Alembic autogenerate против текущих моделей | ✅ пустой diff (`pass`/`pass`) — подтверждает, что схема БД не менялась в этом этапе, файл удалён после проверки |
| Живой запуск (uvicorn + `/openapi.json`) | ✅ все 6 новых эндпоинтов зарегистрированы |

### Известные ограничения / extension points, оставленные сознательно
1. `_require_project_access` продублирован трижды — см. выше, кандидат на рефакторинг.
2. `/auth/refresh`, `/auth/logout` — по-прежнему не реализованы (Этап 5).
3. Email-доставка приглашений — по-прежнему не реализована (ADR-0007).
4. WebSocket/Redis — не начаты, следующий этап.
5. `docker build`/`docker compose up` — то же сетевое ограничение среды,
   что на Этапах 3–6, не проверено в этой сессии.

### Следующий этап (на момент завершения Этапа 7)
**Этап 8 — Realtime (WebSocket)**: единственный оставшийся нереализованный
модуль-стаб. Redis-клиент, `ConnectionManager` поверх Pub/Sub, JWT через
query-param при handshake (текущий `HTTPBearer` для этого не подходит),
event-схемы для `task.*`/`comment.created`/`notification.created`, точки
публикации внутри `TaskService`/`CommentService`/`NotificationService`
(события пока создаются в БД, но никуда не публикуются live). Подробный
разбор пробелов — см. предыдущий аудит в этом файле выше.

---

## Этап 8 — Realtime (WebSocket + Redis Pub/Sub) ✅

### Что реализовано

**Redis-клиент и lifecycle** (`app/core/redis.py`) — единственная точка
создания Redis-подключения, по аналогии с `database/session.py`. Lifespan-
обработчик в `main.py` закрывает пул при остановке приложения.
`/health/ready` расширен реальной `PING`-проверкой Redis (было: только
Postgres, с явным TODO на Redis с Этапа 4) — живой прогон подтвердил и
`200 {"status":"ok"}` при доступном Redis, и честный `503` при его
отключении.

**WebSocket-аутентификация** (`get_current_user_ws`, `core/dependencies.py`) —
токен из query-параметра, не заголовка. Обработчик ошибок — вручную
(`websocket.close(code=1008)`), не через `Depends()`+`AppError`: HTTP
exception handler на WS не распространяется (см. ADR-0008).

**`ConnectionManager`** (`websocket/connection_manager.py`) — единственный
экземпляр на процесс, комната = `project_id`, одна Redis pub/sub подписка
на комнату с хотя бы одним локальным клиентом, `publish()` всегда через
Redis (единый код-путь для горизонтального масштабирования). Полный
дизайн — ADR-0008.

**Событийная интеграция**: `TaskService` (`create`/`update`/`delete`/`assign_user`)
и `CommentService` (`create`) публикуют `task.created/updated/moved/deleted`,
`comment.created`, `notification.created` через общий `_publish()`-хелпер
(намеренно продублирован в обоих сервисах — тот же принцип, что
`_require_project_access` с Этапа 7). Ошибка публикации логируется, но не
роняет API-ответ — задача/комментарий уже в БД к этому моменту.

**Роутер** (`websocket/router.py`) — `WSS /ws/projects/{project_id}?token=<jwt>`,
проверка членства в workspace проекта перед `connection_manager.connect()`,
`WebSocketDisconnect` корректно отписывает от комнаты.

### Найденная и исправленная проблема: cross-event-loop соединения БД

WebSocket тестируется только через Starlette `TestClient` — `httpx.AsyncClient`
не поддерживает WS. `TestClient` запускает ASGI-приложение в **отдельном
потоке со своим event loop**, что здесь трижды подряд ломало тесты одним и
тем же классом ошибки (`RuntimeError: ... attached to a different loop`) —
тот же баг, что уже ловили на Этапе 4, но в новой форме:

1. **Попытка 1** — переиспользовать транзакционную `db_session` (как во всех
   остальных тестах через `client`-фикстуру): падает сразу, сессия открыта
   в loop основного теста, недоступна из loop `TestClient`.
2. **Попытка 2** — обычный, не переопределённый клиент на реальный
   `app.database.session.engine`, с explicit `await engine.dispose()` после
   каждого WS-блока: падает **на самом `dispose()`** — пул всё равно
   пытается закрыть asyncpg-соединение, физически созданное в чужом loop.
   `dispose()` не убирает причину, только двигает момент её проявления.
3. **Корневая причина**: `AsyncAdaptedQueuePool` (обычный пул SQLAlchemy)
   кэширует живые соединения между чекаутами, и каждое такое соединение
   жёстко привязано к тому event loop, в котором было создано. Как только
   на него претендуют два разных loop'а — попытка закрыть/переиспользовать
   его из "чужого" валится.
4. **Рабочее решение** — отдельный engine с `NullPool` для WS-тестов
   (`tests/modules/test_websocket.py`): NullPool не кэширует соединения
   вообще — каждый checkout создаёт новое asyncpg-соединение с нуля в
   _текущем_ loop и закрывает его сразу по возврату. Соединение никогда не
   переживает границу вызова, поэтому вопрос "из какого loop его закрывать"
   не возникает структурно, а не обходится точечно. Через
   `app.dependency_overrides[get_db_session]` эта версия подставляется на
   время файла — и HTTP-вызовы (основной loop), и WS (loop потока)
   используют её одинаково безопасно.

Цена решения: WS-тесты не используют транзакционную изоляцию (как остальные
тесты), пишут в реальную dev-БД с уникальными email/названиями на каждый
тест — тот же компромисс, что был у тестов до появления transactional
`client` на Этапе 5.

### Проверки — реально выполненные
| Проверка | Результат |
|---|---|
| Backend tests | ✅ 68/68 passed (63 из Этапов 1–7 не сломаны + 5 новых WS-тестов) |
| Ruff | ✅ All checks passed |
| Black --check | ✅ 94 files unchanged |
| MyPy --strict | ✅ 77 файлов, 0 ошибок |
| Alembic autogenerate против текущих моделей | ✅ пустой diff — моделей в этом этапе не менялось |
| `/health/ready` с реальным Redis | ✅ `200 ok` при живом Redis, `503` при отключённом |
| WS: подключение с валидным токеном + membership | ✅ реальный `TestClient.websocket_connect` |
| WS: отклонение при невалидном токене | ✅ соединение закрывается |
| WS: отклонение не-участника workspace | ✅ соединение закрывается |
| WS: доставка `task.created` через живой Redis Pub/Sub | ✅ `receive_json()` получает реальное опубликованное событие |
| WS: изоляция комнат по `project_id` | ✅ событие из проекта A не долетает до клиента в проекте B |
| OpenAPI / `/docs` | ✅ все HTTP-эндпоинты на месте (WS-роут в OpenAPI не отображается — так и задумано FastAPI) |

Все проверки WebSocket+Redis — реальные: живой `redis-server` (не мок),
реальный `TestClient.websocket_connect`, реальная публикация через
`redis.asyncio.Redis.publish()` и получение через `pubsub.listen()`.

### Известные ограничения / extension points, оставленные сознательно
1. `member.online`/`member.offline` — не реализованы (нет потребителя на
   фронтенде, Этап 9).
2. `notification.created` публикуется в комнату проекта, не персонально
   пользователю — известное ограничение WS-контракта, см. ADR-0008.
3. `_require_project_access`/`_publish` — паттерн дублирования продолжает
   расти (теперь и в `TaskService`, и в `CommentService`) — тот же
   зафиксированный кандидат на рефакторинг с Этапа 7.
4. `docker build`/`docker compose up` — то же сетевое ограничение среды,
   что на Этапах 3–7, не проверено в этой сессии. Песочница в этом
   этапе дополнительно продемонстрировала нестабильность инфраструктуры
   (Postgres/Redis падали между вызовами несколько раз, требовался
   перезапуск) — сама разработка от этого не пострадала (каждый раз
   перепроверялось перед продолжением), но стоит иметь в виду при
   повторном запуске сессии.
5. **Полная потеря рабочей директории в середине этапа**: песочница была
   один раз полностью пересоздана (все установленные пакеты, БД и
   несохранённый код исчезли). Восстановлено из `taskflow-stage7.zip`
   (последний сохранённый архив), Redis/WS-код Этапа 8 воссоздан заново по
   тому же дизайну. Практический вывод: архивы в `/mnt/user-data/outputs/`
   переживают пересоздание песочницы, рабочая директория — нет.

### Следующий этап
**Этап 9 — Frontend**: единственный полностью нереализованный уровень
проекта (React-скелет с Этапа 2 не наполнен). Либо, на усмотрение
владельца проекта — Этап 10 (AI-функциональность) как продолжение backend-
паттернов без переключения на фронтенд.
