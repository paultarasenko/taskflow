# TaskFlow — Frontend

React + TypeScript + TailwindCSS + TanStack Query + Zustand. Полное описание
архитектуры — в [`docs/01-architecture-and-design.md`](../docs/01-architecture-and-design.md).

> Техническая заглушка для Этапа 2. UI наполняется на Этапе 9.

## Быстрый старт (локально, без Docker)

```bash
cd frontend
npm install
npm run dev
```

Приложение: http://localhost:3000

## Скрипты

| Команда | Действие |
|---|---|
| `npm run dev` | Dev-сервер с hot-reload |
| `npm run build` | Typecheck (`tsc -b`) + production-сборка |
| `npm run lint` | oxlint |
| `npm run preview` | Просмотр production-сборки локально |

## Структура

```
src/
├── components/   # переиспользуемые UI-компоненты
├── features/     # по одной папке на backend-модуль (auth, tasks, projects, ...)
├── lib/          # api-client (axios), query-client (TanStack Query)
└── types/        # общие TS-типы, в т.ч. сгенерированные из OpenAPI (Roadmap)
```
