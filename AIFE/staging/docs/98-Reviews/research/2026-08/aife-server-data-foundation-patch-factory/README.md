---
title: "AIFE Server/Data Foundation — стратегия многоволновой разработки патчами"
status: draft
owner: Architecture Lead
created: 2026-08-25
updated: 2026-08-25
category: architecture
doc_type: readme
language: ru
tags: [server, data, patch-factory, research, development, handoff]
related:
  - PATCH_FACTORY_PLAN_aife-server-data-foundation_2026-08-25.md
---

# AIFE Server/Data Foundation — стратегия многоволновой разработки патчами

Этот каталог хранит предисполнительную доказательную и планировочную основу для
многоволновой разработки `AIFE_SERVER_DATA_FOUNDATION`. Он не открывает новый
канонический контур `docs/98-Reviews/execution/**`, не активирует `D-380` и не
является разрешением на реализацию серверного исполнения.

## Физическое применение

```text
physical-use class=agent-operator-workflow-improvement
PLANNING_ONLY=true
PATCH_FACTORY_STRATEGY=true
NO_CANONICAL_EXECUTION_AUTHORIZATION=true
NO_SERVER_RUNTIME_DELIVERY=true
```

Практическое назначение каталога — дать будущим агентам генерации патчей долговременный
маршрут, который не зависит от контекста чата: как выбирать неизменяемую базу, как создавать одну ограниченную волну,
как считать полный бюджет путей, как замораживать инкрементальный патч и накопительное
восстановление, как связывать дерево предшественника и результата (`predecessor/result tree`)
и когда обязательно проводить сверку перед канонической авторизацией и AEB.

## Канонический носитель плана

- [PATCH_FACTORY_PLAN_aife-server-data-foundation_2026-08-25.md](PATCH_FACTORY_PLAN_aife-server-data-foundation_2026-08-25.md)

## Граница полномочий

```text
RESEARCH_LAYER=evidence_history_only
D380_STATE=PROVISIONAL_NOT_ACTIVE
F1_SOURCE_IMPLEMENTATION=NO
AIFE_MAIN_MUTATION=NO
AEB_CREATED=NO
```

После успешной установки I-1071/I-1072 этот план требует нового чтения полномочий AIFE и
сверки предварительной линии Server/Data. До этого текущий снимок (`snapshot`) нельзя считать финальной
канонической базой для будущих волн установки.
