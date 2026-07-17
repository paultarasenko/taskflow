# syntax=docker/dockerfile:1

# ---------- Builder ----------
# Отдельный build-стейдж с build-essential, который не попадает в финальный
# образ — держим runtime-образ маленьким.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем только то, что нужно для install — кэш Docker-слоя не инвалидируется
# при изменении кода приложения, если зависимости не менялись.
COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# ---------- Runtime ----------
FROM python:3.12-slim AS runtime

# Непривилегированный пользователь — контейнер не должен работать от root.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# Health-эндпоинт уже существует с Этапа 2 (app/main.py). Используем python,
# а не curl/wget — незачем ставить лишний пакет ради healthcheck.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
