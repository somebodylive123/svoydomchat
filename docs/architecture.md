# Архитектура проекта SVOYDOM AI WhatsApp Bot (MVP)

Документ описывает архитектуру backend-сервиса: компоненты, границы ответственности, жизненный цикл сообщений, модель данных, интеграции, надежность и путь к production.

---

## 1. Архитектурные цели

1. **Надежный intake сообщений** из WhatsApp webhook.
2. **Контролируемая LLM-оркестрация** с tool-calling, чтобы снизить риск галлюцинаций.
3. **Накопление контекста диалога** и инкрементальное обновление профиля лида.
4. **Прозрачная интеграция с CRM (Bitrix24)**: create/update lead, timeline, handover уведомления.
5. **Тестируемость и повторяемость** через mock-адаптеры.

---

## 2. Границы системы

### Входные границы
- WhatsApp provider webhook (`/webhooks/whatsapp`).
- Отладочные запросы через API.

### Выходные границы
- Bitrix24 REST webhook API.
- SVOYDOM API-адаптер (в MVP — mock dataset).
- WhatsApp provider send API (mock/Twilio abstraction).

### Хранилище
- SQL database (MVP: SQLite) как source of truth для:
  - conversation state,
  - message history,
  - lead snapshot.

---

## 3. Компонентная модель

## 3.1 API Layer
**Папка:** `app/api/*`

Ответственность:
- валидация входных payload;
- вызов orchestration-сценария;
- возврат стандартизированного ответа.

Ключевые роуты:
- `GET /health`
- `POST /webhooks/whatsapp`
- `GET /debug/*` (служебные маршруты)

## 3.2 Application/Bot Layer
**Папка:** `app/bot/*`

Ответственность:
- оркестрация бизнес-сценария (`message_processor`);
- LLM-агент и выбор инструментов (`agent`, `tools`);
- entity extraction и fallback-логика;
- handover-правила;
- сбор истории для memory context.

## 3.3 Service Layer
**Папка:** `app/services/*`

Ответственность:
- инкапсуляция прикладной логики, не привязанной к HTTP;
- управление conversation/lead;
- CRM sync и property access;
- слой абстракции транспорта отправки сообщений.

## 3.4 Integration Layer
**Папка:** `app/integrations/*`

Ответственность:
- adapters/contracts для внешних систем;
- переключение `mock` / `real` реализаций;
- нормализация внешних payload/response форматов.

Подсистемы:
- `bitrix24` (mock + real)
- `svoydom` (mock)
- `whatsapp` (mock + twilio)

## 3.5 Persistence Layer
**Папка:** `app/database/*`

Ответственность:
- SQLAlchemy models, session lifecycle, repositories.

Сущности:
- `Conversation` — состояние диалога.
- `Message` — журнал сообщений.
- `Lead` — агрегированные клиентские данные и CRM linkage.

---

## 4. Runtime-сценарий обработки

1. API получает входящее сообщение `{phone, message}`.
2. Создается/получается `Conversation` по телефону.
3. Сообщение сохраняется в `Message` (sender=user).
4. Создается/получается `Lead`.
5. Если conversation уже в `handover`:
   - новое сообщение пишется в CRM timeline;
   - бот возвращает служебный ответ без LLM-обработки.
6. Иначе запускается `entity_extractor`.
7. Выделенные поля merge-ятся в лид (обновление только not-null).
8. Выполняется handover-check.
9. Если handover=true:
   - conversation.status=`handover`;
   - CRM notify manager + timeline comment;
   - клиент получает ответ о передаче менеджеру.
10. Если handover=false:
   - формируется memory context;
   - LLM агент генерирует ответ;
   - при необходимости вызывает `search_properties`.
11. Ответ сохраняется в `Message` (sender=bot).
12. Выполняется upsert лида в Bitrix24.
13. API возвращает `{reply, conversation_status}`.

---

## 5. Memory и состояние

### 5.1 Почему DB-first memory
- Простая и надежная модель для MVP.
- Состояние не теряется при рестартах.
- История доступна для аналитики/аудита.

### 5.2 Принципы
- Контекст LLM строится из истории текущего разговора.
- Lead данные обновляются инкрементально.
- Handover-статус sticky до явного изменения.

### 5.3 Риски и ограничения
- Без лимитов истории может расти latency/token cost.
- Для production нужен стратегический trimming/summarization.

---

## 6. Интеграция Bitrix24

### 6.1 Режимы
- `BITRIX_MODE=mock`: локальный безопасный режим.
- `BITRIX_MODE=real`: HTTP webhook вызовы в Bitrix24.

### 6.2 Операции
- `create_lead`
- `update_lead`
- `add_timeline_comment`
- `notify_manager`

### 6.3 Стратегия upsert
- Нет `bitrix_lead_id` → create.
- Есть `bitrix_lead_id` → update.
- На handover всегда отправляется служебный event в CRM.

### 6.4 Надежность (рекомендации)
- retries/backoff на transient-ошибках;
- idempotency ключи для исключения дублей;
- dead-letter сценарии для неуспешных sync операций.

---

## 7. Tool-calling и поиск объектов

Инструмент: `search_properties(district, residential_complex, rooms, max_budget)`.

Поток:
1. LLM определяет необходимость tool вызова.
2. Tool обращается к `PropertyService`.
3. `PropertyService` использует SVOYDOM adapter.
4. Результаты передаются в LLM для ответа клиенту.

Плюс: внешние данные идут из инструмента, а не «из памяти модели».

---

## 8. Безопасность и комплаенс

MVP-минимум:
- базовая валидация payload;
- разделение внешних ключей через env;
- отсутствие hardcode секретов.

Для production:
- проверка подписи webhook provider;
- replay protection;
- rate limiting + abuse controls;
- PII redaction в логах;
- audit trail действий handover/CRM.

---

## 9. Наблюдаемость

Рекомендуемый baseline:
- structured logs (request_id, phone_hash, conversation_id, lead_id);
- latency метрики по этапам pipeline;
- отдельные счетчики: handover_rate, tool_call_rate, crm_error_rate;
- error budget алерты.

---

## 10. Масштабирование

Переход к production:
1. PostgreSQL + Alembic.
2. Async task queue для внешних интеграций.
3. Outbox pattern для надежной доставки CRM событий.
4. Горизонтальное масштабирование API-воркеров.
5. Контроль token-cost и latency per request.