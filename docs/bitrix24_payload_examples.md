# Bitrix24 payload examples

Ниже приведены примеры payload для интеграции с Bitrix24 REST webhook API.

> Важно: точные поля и коды пользовательских полей (`UF_CRM_*`) зависят от настройки вашего портала Bitrix24.

---

## 1) Create lead

### Request

```json
{
  "fields": {
    "TITLE": "Лид с WhatsApp: +79990000001",
    "NAME": "Клиент WhatsApp",
    "PHONE": [
      {
        "VALUE": "+79990000001",
        "VALUE_TYPE": "WORK"
      }
    ],
    "COMMENTS": "Первичное обращение из WhatsApp бота",
    "UF_CRM_SOURCE_CHANNEL": "whatsapp_bot",
    "UF_CRM_BUDGET": 45000000,
    "UF_CRM_ROOMS": 2,
    "UF_CRM_DISTRICT": "Ботанический сад",
    "UF_CRM_RESIDENTIAL_COMPLEX": "Green Park",
    "UF_CRM_PURPOSE": "living"
  },
  "params": {
    "REGISTER_SONET_EVENT": "Y"
  }
}
```

### Typical response

```json
{
  "result": 12345,
  "time": {
    "start": 1710000000,
    "finish": 1710000001,
    "duration": 0.12
  }
}
```

---

## 2) Update lead

### Request

```json
{
  "id": 12345,
  "fields": {
    "UF_CRM_BUDGET": 50000000,
    "UF_CRM_ROOMS": 3,
    "UF_CRM_DISTRICT": "Есиль",
    "UF_CRM_PURPOSE": "investment",
    "COMMENTS": "Пользователь уточнил параметры: бюджет до 50 млн, 3 комнаты"
  },
  "params": {
    "REGISTER_SONET_EVENT": "Y"
  }
}
```

### Typical response

```json
{
  "result": true,
  "time": {
    "start": 1710000010,
    "finish": 1710000011,
    "duration": 0.10
  }
}
```

---

## 3) Add timeline comment

### Request

```json
{
  "fields": {
    "ENTITY_ID": 12345,
    "ENTITY_TYPE": "lead",
    "COMMENT": "[WhatsApp] Клиент: Свяжите меня с менеджером"
  }
}
```

### Typical response

```json
{
  "result": 777,
  "time": {
    "duration": 0.05
  }
}
```

---

## 4) Manager handover notification (вариант)

Некоторые команды реализуют уведомление менеджера через:
- timeline comment с префиксом `[HANDOVER]`, или
- постановку задачи (`tasks.task.add`), или
- изменение стадии/статуса лида.

### Timeline-based handover example

```json
{
  "fields": {
    "ENTITY_ID": 12345,
    "ENTITY_TYPE": "lead",
    "COMMENT": "[HANDOVER] Клиент запросил менеджера. Телефон: +79990000001"
  }
}
```

---

## 5) Ошибки и обработка

### Пример ошибки от Bitrix24

```json
{
  "error": "INVALID_CREDENTIALS",
  "error_description": "Invalid request credentials"
}
```

### Рекомендуемая стратегия

1. Логировать запрос/ответ (без утечки PII/секретов).
2. На transient ошибки использовать retry с exponential backoff.
3. На постоянные ошибки переводить событие в dead-letter очередь/таблицу.
4. Не терять локальное состояние диалога из-за сбоя внешней CRM.

---

## 6) Mapping из внутренней модели в Bitrix24

Рекомендуемая таблица соответствия:

- `lead.phone` -> `PHONE[0].VALUE`
- `lead.budget` -> `UF_CRM_BUDGET`
- `lead.rooms` -> `UF_CRM_ROOMS`
- `lead.district` -> `UF_CRM_DISTRICT`
- `lead.residential_complex` -> `UF_CRM_RESIDENTIAL_COMPLEX`
- `lead.purchase_purpose` -> `UF_CRM_PURPOSE`
- `conversation.status=handover` -> timeline comment / task / stage update

---

## 7) Идемпотентность и дубли

Чтобы избежать дублей лидов и комментариев:
- хранить `bitrix_lead_id` локально;
- использовать upsert стратегию create/update;
- добавлять correlation_id в комментарии/логи;
- применять дедупликацию на стороне consumer/job.