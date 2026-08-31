---
title: "Core-слой AIFE"
id: DOC-10-ARCHITECTURE-TREE-RUNTIME-CORE
version: "0.3"
status: active
owner: Architecture Lead
created: 2026-06-04
updated: 2026-06-17
review_cycle_days: 90
next_review_due: 2026-09-15
tags: [architecture, tree]
category: architecture
doc_type: design
language: ru
authority_reference:
  - ../../architecture.md
---

# Core-слой AIFE

## Назначение

Дерево покрывает каталог `core/` по фактическому составу пакета. Оно помогает
понять назначение файлов, но не заменяет код, стандарты или ADR.

## Дерево

```text
core/  # Минимальный контур жизненного цикла, событий, данных и SysControl.
├── api/  # Пустое семантическое пространство имён для будущего слоя API; обработчики исполнения сейчас не реализованы.
│   └── __init__.py  # Инициализация Python-пакета `api`.
├── bots/  # Пустое семантическое пространство имён для будущих ботов; торговое исполнение сейчас не реализовано.
│   ├── strategies/  # Пустое семантическое пространство имён для будущих стратегий; реестр и исполнение сейчас не реализованы.
│   │   └── __init__.py  # Инициализация Python-пакета `strategies`.
│   └── __init__.py  # Инициализация Python-пакета `bots`.
├── communication/  # Слой адаптера между Core и communication layer.
│   ├── __init__.py  # Инициализация Python-пакета `communication`.
│   └── core_communication_adapter.py  # Передаёт core-события в `SignalCommunication`.
├── data/  # Подложка контрактов данных: адаптеры, репозитории, модели идентичности и unit-of-work.
│   ├── adapters/  # Контракты адаптеров между исполнением, хранением и сессиями.
│   │   ├── __init__.py  # Инициализация Python-пакета `adapters`.
│   │   ├── session_adapter.py  # Протокол доступа к слою данных через сессию.
│   │   ├── sqlite_control.py  # SQLite/WAL-адаптер durable F5 control state с транзакционными work/attempt/publication/recovery операциями.
│   │   └── sqlite_schema.py  # Bounded SQLite schema/version/compatibility contract для F5 control state.
│   ├── models/  # Базовые модели идентичности и контракты значений.
│   │   ├── __init__.py  # Инициализация Python-пакета `models`.
│   │   └── identity.py  # Identity-типы для `core.data`.
│   ├── repositories/  # Repository-контракты для доступа к данным.
│   │   ├── __init__.py  # Инициализация Python-пакета `repositories`.
│   │   ├── base_repository.py  # Базовый async repository contract.
│   │   └── server_control.py  # Узкий repository contract persisted F5 control state и backup/restore evidence.
│   ├── uow/  # Unit-of-work contracts для согласованного жизненного цикла data-операций.
│   │   ├── __init__.py  # Инициализация Python-пакета `uow`.
│   │   └── base_unit_of_work.py  # Базовый unit-of-work contract.
│   └── __init__.py  # Инициализация Python-пакета `data`.
├── graphs/  # Пустое семантическое пространство имён для будущего контура графов; рендеринг и экспорт сейчас не реализованы.
│   └── __init__.py  # Инициализация Python-пакета `graphs`.
├── management/  # Опциональная интеграция SysControl.
│   ├── __init__.py  # Инициализация Python-пакета `management`.
│   ├── README.md  # Обзор интеграции SysControl.
│   ├── syscontrol_client.py  # HTTP-клиент внешнего агента SysControl.
│   └── system_control_manager.py  # Опциональный менеджер с мягкой деградацией.
├── utils/  # Вспомогательные утилиты асинхронных операций и завершения.
│   ├── __init__.py  # Инициализация Python-пакета `utils`.
│   ├── asyncio_tools.py  # Помощники ожидания coroutine/task и обработки таймаутов.
│   └── shutdown_config.py  # Значения таймаутов завершения.
├── __init__.py  # Инициализация Python-пакета `core`.
├── core_manager.py  # Менеджер жизненного цикла и событий Core через `AppContext` и `CoreCommunicationAdapter`.
└── README.md  # Обзор и маршрут чтения: Core Package.
```

## Правило чтения

Комментарии рядом с файлами дают короткую тематическую роль. Подробное
поведение проверяется по коду, тестам и профильным документам:

- [docs/35-Core](../../../../35-Core/README.md)
- [ADR-INITIALIZER-CORE-001](../../../../../genome/adr/initializer/ADR-INITIALIZER-CORE-001.md)
- [ADR-INITIALIZER-CORE-002](../../../../../genome/adr/initializer/ADR-INITIALIZER-CORE-002.md)
