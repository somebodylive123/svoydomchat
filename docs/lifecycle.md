# Lifecycle: обработка входящего сообщения

Документ описывает пошаговый flow обработки одного входящего сообщения клиента.

---

## 1. Цель lifecycle

- Обработать входящий текст пользователя.
- Сохранить историю и состояние.
- Обновить профиль лида.
- Либо передать менеджеру, либо вернуть автоматический ответ.
- Синхронизировать результат с CRM.

---

## 2. Основной сценарий (happy path)

1. **Webhook intake**
   - `POST /webhooks/whatsapp` получает payload.
   - Проводится валидация структуры и обязательных полей.

2. **Conversation bootstrap**
   - По номеру телефона находится или создается `Conversation`.

3. **Message persist (incoming)**
   - Сообщение сохраняется в БД как `sender=user`.

4. **Lead bootstrap**
   - Находится или создается `Lead`, связанный с `Conversation`.

5. **Handover short-circuit check**
   - Если диалог уже в статусе `handover`, бот не выполняет LLM flow.
   - Сообщение отправляется в CRM timeline и возвращается служебный ответ.

6. **Entity extraction**
   - Из текста извлекаются параметры:
     - `budget`
     - `rooms`
     - `district`
     - `residential_complex`
     - `purchase_purpose`
     - `wants_manager`

7. **Lead merge/update**
   - Поля обновляются по стратегии not-null merge.
   - Считается признак qualification.

8. **Handover decision**
   - Проверяются триггеры передачи менеджеру.

9. **Branch A: handover=true**
   - `Conversation.status = handover`.
   - В CRM отправляются:
     - уведомление менеджеру,
     - timeline comment.
   - Пользователю возвращается сообщение о передаче.

10. **Branch B: handover=false**
    - Строится memory context из истории сообщений.
    - LLM-агент формирует ответ.
    - При необходимости вызывает tool `search_properties`.

11. **Message persist (outgoing)**
    - Ответ бота сохраняется как `sender=bot`.

12. **CRM upsert**
    - Лид синхронизируется в Bitrix24 (`create`/`update`).

13. **API response**
    - Возвращается payload вида:
      - `reply`
      - `conversation_status`

---

## 3. Сценарии отклонения

### 3.1 Невалидный webhook payload
- Возвращается ошибка валидации (4xx).
- Сообщение не обрабатывается дальше.

### 3.2 Ошибка внешней CRM
- Локальные данные (conversation/message/lead) сохраняются.
- Ошибка CRM логируется.
- Для production рекомендуется retry механизм.

### 3.3 Ошибка LLM/tool вызова
- Возможен fallback-ответ пользователю.
- Инцидент логируется для последующей диагностики.

---

## 4. Состояния conversation

- `active` — обычная автоматическая обработка ботом.
- `handover` — диалог закреплен за менеджером.
- `closed` — опциональное завершение диалога.

Переходы:
- `active -> handover` при выполнении handover условий.
- `handover -> active` только по явному бизнес-сценарию (в MVP обычно не используется автоматически).

---

## 5. SLA/качество (рекомендации)

- p95 latency webhook обработки.
- доля успешных CRM upsert.
- доля handover от общего числа обращений.
- доля ответов с tool-calling.

---

## 6. Диагностика

Для расследования конкретного кейса использовать связку:
- `phone`
- `conversation_id`
- `lead_id`
- временные метки входящего/исходящего message
- CRM event log (create/update/comment/notify)
