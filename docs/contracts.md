# Контракты (черновик v0.1)

Источник истины — Pydantic-модели в `backend/app/contracts/` (решение B2). Из них генерируются:

- `docs/openapi.json` — HTTP API для фронта (префикс `/v1`, E8);
- `docs/schemas/*.json` — JSON Schema основных сущностей;
- `frontend/src/api/schema.d.ts` — типы TypeScript.

После любого изменения моделей: `make contracts`. Проверка расхождения: `make contracts-check`.

## Кто чем владеет

| Файл | Сущности | Владелец |
|---|---|---|
| `contracts/common.py` | `Claim`, `Citation`, `Provenance`, `ApiError` | все |
| `contracts/taxonomy.py` | `SensitivityTag` — закрытый словарь тегов (D2) | роли 2 и 3 |
| `contracts/events.py` | `Event`, `EventListItem`, `NewsIngestRequest` | роль 2 |
| `contracts/clients.py` | `ClientProfile`, `FeedItem`, `RelevanceReason` | роль 3 |
| `contracts/insights.py` | `Insight`, `BankPosition`, `TraceStep`, `AgentTrace`, `Job`, чат | роль 4 |
| `contracts/platform.py` | авторизация, фидбек, метрики | роль 5 |

## Как подключить свой модуль

Внутри бэкенда модули вызываются как Python-функции (A1). Интерфейсы описаны в `backend/app/services/ports.py`:

- `NewsPort` (роль 2): `list_events`, `get_event`, `ingest_text`, `bank_positions`;
- `ProfilePort` (роль 3): `list_clients`, `get_profile`, `rank`;
- `AgentPort` (роль 4): `run` — асинхронный генератор, который отдаёт `TraceStep` по мере выполнения и `Insight` последним; `chat`.

Сейчас работают заглушки из `backend/app/stubs/` на синтетических фикстурах. Реальную реализацию подключайте в `backend/app/services/registry.py`. Если реализация проходит тесты из `backend/tests/`, фронт продолжит работать.

## Принятые по умолчанию решения, которые стоит подтвердить

- **A2.** Единица выдачи — событие. Инсайт ссылается на `event_id` и `event_version`; если `event.version` выросла, инсайт помечается `stale`.
- **D6.** У каждого утверждения есть `provenance`: `source_fact`, `bank_position` или `ai_inference`. Резюме события всегда `ai_inference`.
- **D8.** `null` значит «не определено», а не «нет». Пример: `foreign_trade.has_fea = null`.
- **E4.** Приём новости синхронный, только классификация. Инсайт считается фоновой задачей (`Job`), шаги приходят по SSE `/v1/jobs/{id}/stream`.
- **E5.** Все ошибки возвращаются в одном формате `ApiError {code, message, trace_id, details}`.
- **E7.** HTTP требует авторизации по демо-учётке. Запуск агента, чат и приём новостей ограничены по частоте для каждого пользователя.
- **J1.** У каждого запроса есть `X-Trace-Id`, он же в ответе. У каждой задачи агента свой `trace_id`.
- **H4.** Журнал вызовов пишет метод, путь, статус, длительность и `trace_id`, без тел запросов.

## Открытые вопросы роли 5

1. Роль 4: нужен ли агенту колбэк вместо генератора (если шаги идут из LangGraph)?
2. Роль 3: устроит ли `rank(profile, events) -> list[FeedItem]`, или ранжирование будет читать события само?
3. Роль 2: возвращает ли `ingest_text` событие с классификацией синхронно в пределах ~30 с?
4. Все: где хранить кэш инсайтов, фидбек и трассы — в общей Postgres (предлагаю отдельную схему `bff`)?
