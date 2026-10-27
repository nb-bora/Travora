# syntax=docker/dockerfile:1

FROM python:3.14-slim AS builder

ENV POETRY_VERSION=2.4.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root


FROM python:3.14-slim AS runtime

# WeasyPrint exige Pango (version 1.44 ou plus) et des polices installées.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 travora

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=travora:travora manage.py ./
COPY --chown=travora:travora config ./config
COPY --chown=travora:travora apps ./apps
COPY --chown=travora:travora templates ./templates
COPY --chown=travora:travora tools ./tools

RUN DJANGO_SECRET_KEY=build-only DJANGO_ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput \
    && chown -R travora:travora /app/staticfiles

USER travora
EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
