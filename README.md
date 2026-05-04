# SVOYDOM MVP: AI WhatsApp Bot Backend for Real Estate

Production-oriented MVP backend that automates первичную коммуникацию с клиентом в WhatsApp, извлекает сущности из диалога, выполняет поиск объектов через SVOYDOM API-адаптер и синхронизирует лид в Bitrix24.

## 1) Цель проекта

Сервис покрывает сценарий от первого входящего сообщения до:
- квалификации лида;
- формирования релевантного ответа;
- передачи менеджеру (handover) при явном запросе клиента;
- синхронизации собранных данных в CRM Bitrix24.

Ключевой принцип MVP: **контролируемая, тестируемая интеграция** через адаптеры и mock-режимы на внешних границах.

---

## 2) Технологический стек
 **Python 3.11+**
- **FastAPI** (HTTP API / webhooks)
- **SQLAlchemy + SQLite** (состояние диалогов, сообщений, лидов)
- **LangChain + OpenAI** (LLM orchestration и tool-calling)
- **Bitrix24 REST API** (mock / real)
- **WhatsApp Provider abstraction** (mock / Twilio adapter)

---

## 3) Архитектура проекта (полная)

### 3.1 Контекстная схема (уровень C4-Container)

1. **Client (WhatsApp user)** отправляет сообщение.
2. **WhatsApp provider** (Twilio или mock) доставляет webhook.
3. **FastAPI webhook** принимает payload и валидирует контракт.
4. **Message Processor** оркестрирует бизнес-пайплайн.
5. **Entity Extractor** извлекает параметры (budget/rooms/district/...) из текста.
6. **Lead Service** обновляет агрегированный профиль лида.
7. **Handover Service** определяет, нужен ли оператор.
8. **LLM Agent + Tools** формирует ответ и вызывает `search_properties` при необходимости.
9. **CRM Service** upsert-ит лид в Bitrix24 и пишет timeline/notification события.
10. **DB Layer** хранит conversation state + message history + lead snapshot.

### 3.2 Слои и ответственность

#### API Layer (`app/api/*`)
- Роуты `health`, `whatsapp`, `debug`.
- Pydantic-схемы входящего webhook payload.
- Минимум бизнес-логики: только валидация и вызов orchestration.

#### Bot/Application Layer (`app/bot/*`)
- `message_processor.py` — единая orchestration-точка.
- `agent.py` — LLM runtime + tool binding.
- `entity_extractor.py` — извлечение сущностей (LLM + fallback).
- `handover.py` — правила передачи оператору.
- `memory.py`, `prompts.py`, `tools.py` — контекст, промпт, инструменты.

#### Service Layer (`app/services/*`)
- `conversation_service.py` — управление диалогами.
- `lead_service.py` — обновление/квалификация лида.
- `crm_service.py` — интеграционный orchestration для Bitrix24.
- `property_service.py` — унифицированный доступ к объектам недвижимости.
- `whatsapp_service.py` — транспорт отправки сообщений через provider abstraction.

#### Integration Layer (`app/integrations/*`)
- `svoydom/*` — контракты + mock-клиент внешнего каталога объектов.
- `bitrix24/*` — контракты + mock/real клиенты CRM.
- `whatsapp/*` — base + mock + Twilio client.

#### Persistence Layer (`app/database/*`)
- SQLAlchemy модели: `Conversation`, `Message`, `Lead`.
- Репозитории с CRUD и query-операциями.
- Session/engine lifecycle.

#### Core Layer (`app/core/*`)
- Константы, ошибки, логирование, доменные enum/справочники.

### 3.3 Жизненный цикл сообщения (runtime flow)

1. `POST /webhooks/whatsapp` принимает `{phone, message}`.
2. Находится/создается `Conversation` по телефону.
3. Входящее сообщение сохраняется как `MessageSender.USER`.
4. Находится/создается `Lead` для текущего диалога.
5. Если `Conversation.status == handover`:
   - пользовательское сообщение отправляется в CRM timeline;
   - бот возвращает служебный ответ о передаче менеджеру.
6. Иначе запускается `extract_entities`.
7. Извлеченные поля merge-ятся в лид (non-null strategy).
8. Проверяются правила handover.
9. Если handover=true:
   - conversation переводится в `handover`;
   - CRM получает notify + comment;
   - пользователю отправляется подтверждение передачи.
10. Если handover=false:
    - собирается history context;
    - запускается LLM agent;
    - при необходимости вызывается `search_properties`;
    - генерируется финальный ответ.
11. Ответ сохраняется как `MessageSender.BOT`.
12. Выполняется CRM upsert лида (`create`/`update`).
13. API возвращает `reply` + `conversation_status`.

### 3.4 Memory management

MVP memory-подход:
- **Conversation** = state machine (`active`, `handover`, `closed`);
- **Message** = immutable журнал диалога;
- **Lead** = агрегированная бизнес-карточка клиента.

Особенности:
- История хранится в БД и переживает рестарт приложения.
- Entity merge не затирает поля `None`.
- Handover-режим sticky: бот не «возвращается» в автоответы без явного изменения статуса.

### 3.5 Интеграция с Bitrix24

Поддерживаемые режимы:
- `BITRIX_MODE=mock` — локальная эмуляция;
- `BITRIX_MODE=real` — реальные REST webhook вызовы.

Логика sync:
- нет `bitrix_lead_id` → `create_lead`;
- есть `bitrix_lead_id` → `update_lead`;
- на handover/особые события → timeline comment + manager notification.

### 3.6 Tool-calling (RAG & Tools)

Инструмент `search_properties(...)` принимает:
- `district`
- `residential_complex`
- `rooms`
- `max_budget`

Возвращает нормализованный список карточек недвижимости для генерации ответа без «галлюцинаций» по объектам.
## 4) Структура репозитория
```text
app/
  api/
    routes/
      debug.py
      health.py
      whatsapp.py
    schemas/
      whatsapp.py
  bot/
    agent.py
    entity_extractor.py
    handover.py
    memory.py
    message_processor.py
    prompts.py
    tools.py
  core/
    astana_districts.py
    constants.py
    exceptions.py
    logger.py
  data/
    mock_properties.json
  database/
    models.py
    repositories.py
    session.py
  integrations/
    bitrix24/
      base.py
      mock_client.py
      real_client.py
      schemas.py
    svoydom/
      base.py
      mock_client.py
      schemas.py
    whatsapp/
      base.py
      mock_client.py
      twilio_client.py
  services/
    conversation_service.py
    crm_service.py
    lead_service.py
    llm_factory.py
    property_service.py
    whatsapp_service.py
  config.py
  dependencies.py
  main.py
docs/
  architecture.md
  bitrix24_payload_examples.md
  lifecycle.md
tests/
  ...
```
## 5) Быстрый старт

### 5.1 Требования
- Python 3.11+
- pip

### 5.2 Установка

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5.3 Конфигурация

```bash
cp .env.example .env
```

Минимальные переменные:
- `OPENAI_API_KEY`
- `LLM_MODEL` (по умолчанию задается в конфиге)
- `BITRIX_MODE` (`mock`/`real`)
- `BITRIX_WEBHOOK_URL` (обязательно для `real`)

### 5.4 Запуск

```bash
uvicorn app.main:app --reload
```

### 5.5 Запуск через

Если не хотите поднимать окружение вручную, можно запустить сервис в контейнере:

```bash
docker compose up --build
```

После старта приложение доступно на `http://127.0.0.1:8000`.

Остановить сервис:

```bash
docker compose down
```

Health-check:
```bash
curl -X GET http://127.0.0.1:8000/health
```

---

## 6) Локальный прием webhook через ngrok + Twilio

Ниже — стандартный путь для теста реального входящего WhatsApp webhook в локальную машину.

### 6.1 Поднять приложение

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6.2 Поднять ngrok-туннель

```bash
ngrok http 8000
```

Скопируйте публичный HTTPS URL вида:
`https://<random>.ngrok-free.app`

### 6.3 Настроить Twilio Sandbox for WhatsApp

1. Откройте **Twilio Console → Messaging → Try it out → Send a WhatsApp message**.
2. В поле **WHEN A MESSAGE COMES IN** укажите webhook:
   - `https://<random>.ngrok-free.app/webhooks/whatsapp`
3. Метод запроса: `POST`.
4. Сохраните конфиг.

### 6.4 Проверить входящее сообщение

- Подключите ваш номер к Twilio Sandbox (код join из консоли Twilio).
- Отправьте сообщение в sandbox-номер.
- Убедитесь, что лог API показывает успешную обработку webhook.

### 6.5 Важные замечания по Twilio payload

Twilio отправляет поля в своем формате (например `From`, `Body`).
Для production стоит добавить явный adapter/mapper Twilio payload → внутренний контракт `{phone, message}`.

---

## 7) Примеры API

### 7.1 Поисковый запрос

```bash
curl -X POST http://127.0.0.1:8000/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79990000001",
    "message": "Ищу 2-комнатную квартиру в районе Ботанического сада, бюджет до 45 млн, для жизни"
  }'
```

### 7.2 Запрос handover

```bash
curl -X POST http://127.0.0.1:8000/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79990000001",
    "message": "Свяжите меня с менеджером"
  }'
```

---

## 8) Тестирование

Запуск полного набора:

```bash
pytest -q
```

Сьют покрывает:
- webhook processing;
- entity extraction;
- property search;
- lead/crm logic;
- handover behavior.

---

## 9) Ограничения MVP

- SVOYDOM и часть WhatsApp/CRM контуров могут работать в mock-режиме.
- Нет очередей/ретраев/circuit breaker на внешние API.
- SQLite подходит для MVP, но не для высокой конкурентной нагрузки.

---

## 10) Roadmap до production

1. Перейти с SQLite на PostgreSQL + Alembic migrations.

2. Вынести тяжелую обработку в task queue:
   - Celery;
   - RQ;
   - Kafka consumers.

3. Добавить retry/backoff + idempotency keys для CRM/webhook операций:
   - повторная отправка при временных ошибках;
   - защита от дублей сообщений;
   - корректная обработка повторных webhook-событий.

4. Усилить безопасность webhook:
   - проверка подписи входящих запросов;
   - replay protection;
   - rate limiting;
   - логирование подозрительных запросов.

5. Ввести observability:
   - structured logs;
   - метрики;
   - tracing;
   - alerting;
   - мониторинг ошибок webhook и отправки сообщений.

6. Добавить E2E тесты с Twilio Sandbox contract fixtures:
   - тесты входящих WhatsApp-сообщений;
   - тесты исходящих ответов;
   - тесты ошибок провайдера;
   - тесты retry-логики.

7. Для production перейти с Twilio Sandbox на официальный Meta WhatsApp Cloud API:
   - подключить Meta Developer App;
   - настроить WhatsApp Business Account;
   - подключить реальный business phone number;
   - получить permanent access token через System User;
   - реализовать webhook verification для Meta;
   - реализовать проверку подписи `X-Hub-Signature-256`;
   - нормализовать payload Meta Cloud API во внутренний формат `{phone, message}`;
   - реализовать отправку исходящих WhatsApp-сообщений через Meta Graph API.