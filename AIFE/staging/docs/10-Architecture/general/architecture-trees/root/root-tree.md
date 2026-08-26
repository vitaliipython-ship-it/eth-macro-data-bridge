---
title: "Корневая топология AIFE"
id: DOC-10-ARCHITECTURE-TREE-ROOT
version: '0.3'
status: active
owner: Architecture Lead
created: 2026-06-04
updated: 2026-08-26
review_cycle_days: 90
next_review_due: 2026-09-02
tags: [architecture, tree]
category: architecture
doc_type: design
language: ru
authority_reference:
  - ../../architecture.md
  - ../../../../../AGENTS.md
---

# Корневая топология AIFE

## Назначение

Короткий вид корня с route-переходами к подробным деревьям. Для пофайлового
описания используйте `root-files.md` и профильные модульные деревья.

```text
AIFE/
├── .aife/  # Машинный управляющий слой проекта: правила, схемы, измерение и упаковка проверки. См. ../project-control/aife-control-plane-tree.md.
├── .benchmarks/  # Выходной измерительный слой: результаты, сравнения и базовые снимки. См. ../measurement/benchmark-output-tree.md.
├── .claude/  # Локальный слой навыков Claude для рабочих сценариев. См. ../project-control/prompt-skill-layer-tree.md.
├── .github/  # Промты, инструкции и служебная конфигурация агентного workflow. См. ../project-control/agent-instruction-tree.md.
├── .iis/  # Локальная поддержка IIS; не основной runtime проекта. См. ../tooling/workspace-support-tree.md.
├── .vscode/  # Настройки рабочей области редактора. См. ../tooling/workspace-support-tree.md.
├── ai/  # Runtime-обвязка AI-слоя; models/preprocessing/training сейчас skeleton, future ML horizon см. docs/20-AI. См. ../runtime/ai-tree.md.
├── blockchain/  # Runtime-слой блокчейн-интеграции. См. ../runtime/blockchain-tree.md.
├── communication/  # Runtime-слой обмена событиями и сообщениями. См. ../runtime/communication-tree.md.
├── core/  # Базовые сервисы, управление, данные, API и доменная логика. См. ../runtime/core-tree.md.
├── deploy/  # Скрипты и конфигурация доставки/развёртывания. См. ../tooling/deploy-tree.md.
├── docs/  # Документация, обзоры, архитектура, отчёты и review-носители. См. ../project-control/docs-governance-tree.md.
├── examples/  # Примеры и вспомогательные материалы разработки. См. ../tooling/workspace-support-tree.md.
├── external/  # Граница внешних справочных материалов; не источник полномочий AIFE. См. ../reference-disposition/external-disposition.md.
├── genome/  # Владелец-слой стандартов, ADR, контрактов и реестров. См. ../project-control/genome-owner-layer-tree.md.
├── initializer/  # Инициализация приложения, AppContext и жизненный цикл запуска. См. ../runtime/initializer-tree.md.
├── monitoring/  # Runtime-поддержка мониторинга и наблюдаемости. См. ../runtime/monitoring-tree.md.
├── patterns/  # Оболочка жизненного цикла и пересылки событий; аналитический движок распознавания паттернов не реализован. См. ../runtime/patterns-tree.md.
├── resources/  # Ресурсы интерфейса, иконки и сопутствующие файлы. См. ../runtime/resources-tree.md.
├── scripts/  # Инструменты проверки, сборки, обслуживания и измерения. См. ../tooling/scripts-tooling-tree.md.
├── security/  # Слой безопасности, валидации, сканирования и защитных правил. См. ../runtime/security-tree.md.
├── server/  # Backend-neutral Server/Data foundation: work, scheduling, execution, publication, storage и access. См. ../runtime/server-tree.md.
├── tests/  # Тестовый и проверочный слой проекта. См. ../tooling/tests-verification-tree.md.
├── ui/  # Интерфейс, рабочая область, панели, графики и визуальные компоненты. См. ../runtime/ui-tree.md.
└── root files  # См. root-files.md.
```

## Граница

Этот файл не заменяет подробные деревья. Он показывает только маршрут чтения.
