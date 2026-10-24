# Сторонние компоненты

Разделы про библиотеки и образы генерируются скриптом `scripts/third_party_notices.py` из lock-файлов. В список входит только то, что попадает в продукт; инструменты разработки (pytest, ruff, vite, typescript) не входят.

<!-- manual:start -->
## Модели, датасеты и сервисы

Этот раздел заполняется вручную и сохраняется при перегенерации файла.

| Что | Где используется | Лицензия или условия |
|---|---|---|
| LLM из разрешённого списка организаторов | агент (роль 4) | условия организаторов хакатона |
| Аналитика ЦМИ Альфа-Банка (9 PDF) | база знаний (роль 2) | условия организаторов хакатона |
| Обезличенные данные клиентов (CSV) | профили (роль 3) | условия организаторов хакатона |
| Let's Encrypt | HTTPS на стенде | Let's Encrypt Subscriber Agreement |
<!-- manual:end -->

## Python (backend, `backend/uv.lock`)

| Пакет | Версия | Лицензия |
|---|---|---|
| alembic | 1.20.0 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| asyncpg | 0.32.0 | Apache-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| fastapi | 0.142.2 | MIT |
| greenlet | 3.5.6 | MIT AND PSF-2.0 |
| h11 | 0.16.0 | MIT |
| httptools | 0.8.0 | MIT |
| idna | 3.20 | BSD-3-Clause |
| mako | 1.4.3 | MIT |
| markupsafe | 3.0.4 | BSD-3-Clause |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| pydantic | 2.13.5 | MIT |
| pydantic-core | 2.46.5 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| pyjwt | 2.15.1 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| pyyaml | 6.0.3 | MIT |
| sqlalchemy | 2.1.3 | MIT |
| starlette | 1.7.0 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| uvloop | 0.23.0 | Apache OR MIT |
| watchfiles | 1.3.0 | MIT |
| websockets | 17.2 | BSD-3-Clause |

## JavaScript (frontend, `frontend/package-lock.json`)

| Пакет | Версия | Лицензия |
|---|---|---|
| @tanstack/query-core | 5.104.1 | MIT |
| @tanstack/react-query | 5.104.1 | MIT |
| cookie | 1.1.1 | MIT |
| openapi-fetch | 0.17.0 | MIT |
| openapi-typescript-helpers | 0.1.0 | MIT |
| react | 19.3.0 | MIT |
| react-dom | 19.3.0 | MIT |
| react-router | 7.18.4 | MIT |
| react-router-dom | 7.18.4 | MIT |
| scheduler | 0.28.0 | MIT |
| set-cookie-parser | 2.7.2 | MIT |

## Docker-образы

| Образ | Зачем | Лицензия |
|---|---|---|
| `python:3.12-slim` | образ API | PSF-2.0 (Python), Debian |
| `ghcr.io/astral-sh/uv:0.13.4` | сборка образа API | MIT OR Apache-2.0 |
| `node:24.21.0-alpine` | сборка фронта | MIT (Node.js), Alpine |
| `nginx:1.28-alpine` | раздача фронта | BSD-2-Clause |
| `pgvector/pgvector:0.8.0-pg17` | база данных | PostgreSQL License |
| `caddy:2.10.0-alpine` | HTTPS на стенде | Apache-2.0 |
