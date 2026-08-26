---
title: "AIFE Server/Data Foundation — F1: диспозиция стандартов DATA"
status: draft
owner: Architecture Lead
created: 2026-08-25
updated: 2026-08-25
category: architecture
doc_type: analysis
language: ru
tags: [server, data, f1, standards, disposition, storage]
authority_reference:
  - ../../../../../../genome/standards/data/STD-DATA-MGMT-001.md
  - ../../../../../../genome/standards/data/STD-DATA-SCHEMA-001.md
  - ../../../../../../genome/standards/data/STD-DATA-MIGRATION-001.md
  - ../../../../../../genome/standards/data/STD-DATA-VALIDATION-001.md
  - ../../../../../../genome/standards/data/STD-DATA-RETENTION-001.md
  - ../../../../../../genome/standards/data/STD-DATA-BACKUP-001.md
related:
  - README.md
  - ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
---

# AIFE Server/Data Foundation — F1: диспозиция стандартов DATA

## 1. Назначение

```text
physical-use class=agent-operator-workflow-improvement
CHECKPOINT=CHECKPOINT_F1_ARCHITECTURE
DATA_STANDARDS_DISPOSITION_ONLY=true
DATA_STANDARDS_MUTATION_NOW=false
F2_ENTRY_REQUIRES_DATA_STANDARDS_ALIGNMENT=true
```

F1 обязан классифицировать все шесть текущих стандартов `DATA`, но не должен
переписывать их в той же контрольной точке. Все шесть имеют `version=0.1.0` и
`status=draft` на текущем снимке. В них есть полезная основа, но нормативный
текст смешан с примерами конкретных БД, инструментов и мест хранения. Поэтому
F1 не повышает их статус и не использует SQLite, MongoDB, S3 или `cron` как
выбор технологии для будущего Server/Data.

## 2. Итоговая диспозиция

| Стандарт | Решение F1 | Причина | Следующее ограниченное изменение |
| --- | --- | --- | --- |
| `STD-DATA-MGMT-001` | `AMEND_REQUIRED` | операции создания, чтения, изменения, удаления, архивации и очистки (`CRUD/Delete/Archive/Purge`) и примерные владельцы хранения не выражают классы устойчивости и различие между приёмом и канонической публикацией | добавить классы устойчивости, владения и границу физической и семантической власти |
| `STD-DATA-SCHEMA-001` | `AMEND_REQUIRED` | нормативный текст фактически предполагает связку SQLite+MongoDB и правила конкретных движков | сделать идентичность, версию, совместимость и требования к индексированию независимыми от поставщика; профили БД оставить справочными |
| `STD-DATA-MIGRATION-001` | `AMEND_REQUIRED` | маршрут ориентирован на Alembic/SQLite/MongoDB и не покрывает перенос физического корпуса, дозагрузку истории (`backfill`) и переключение полномочий | добавить виды миграции, перечень, идентичность, целостность, полноту, независимое чтение, паритет, откат и шлюз переключения |
| `STD-DATA-VALIDATION-001` | `AMEND_REQUIRED` | правила слишком тесно связаны с Pydantic и примерами хранилищ и не отделяют общую проверку от доменной | разделить проверку оболочки, схемы, целостности, публикации, происхождения и полноты от доменной проверки и финальности |
| `STD-DATA-RETENTION-001` | `AMEND_REQUIRED` | возрастные сроки и удаление могут быть ошибочно прочитаны как автоматическое физическое удаление (`purge`) | закрепить логические роли `HOT/WARM/COLD/ARCHIVAL/RETIREMENT/PURGE`, восстановимость, состояние миграции и отдельный шлюз удаления |
| `STD-DATA-BACKUP-001` | `AMEND_REQUIRED` | текст опирается на SQLite/MongoDB/S3/cron/пути и недостаточно отделяет наличие копии от доказанного восстановления | сделать требования независимыми от поставщика: область, идентичность, целостность, RPO/RTO, удалённая/неизменяемая копия при необходимости и независимая репетиция восстановления |

```text
STD_DATA_MGMT_001=AMEND_REQUIRED
STD_DATA_SCHEMA_001=AMEND_REQUIRED
STD_DATA_MIGRATION_001=AMEND_REQUIRED
STD_DATA_VALIDATION_001=AMEND_REQUIRED
STD_DATA_RETENTION_001=AMEND_REQUIRED
STD_DATA_BACKUP_001=AMEND_REQUIRED
DATA_STANDARDS_DISPOSITION=PASS
```

## 3. Общие требования к следующему изменению стандартов

Следующий `CHECKPOINT_DATA_STANDARDS` должен сохранить существующие идентификаторы (`IDs`) и
выполнить смысловое изменение каждого стандарта, если свежее полномочие не
потребует разделения документа.

### 3.1. Классы полномочий и устойчивости

```text
VOLATILE_PROCESS_STATE
NODE_LOCAL_RECOVERABLE_STATE
INGEST_DURABLE_STATE
CANONICAL_PUBLISHED_STATE
ARCHIVAL_STATE
```

Ни один класс физического хранения не получает доменную семантическую власть.

### 3.2. Независимость от поставщика

SQLite, MongoDB, PostgreSQL, Redis, S3, Parquet и другие технологии могут
оставаться справочными примерами или профилями, но не универсальным выбором
AIFE. Конкретная реализация выбирается позже в `F3_BACKEND_SELECTION_GATE`
после контрактов F2.

### 3.3. Виды миграции

```text
SCHEMA_MIGRATION
DATA_MIGRATION
PHYSICAL_BACKEND_MIGRATION
HISTORICAL_BACKFILL
AUTHORITY_OR_CUTOVER_MIGRATION
```

Каждый применимый маршрут должен явно задавать перечень, идентичности,
целостность, полноту, происхождение, независимое чтение, паритет, условия
отката/переключения и сохранение читаемости прежнего маршрута.

### 3.4. Разделение общей и доменной проверки

```text
AIFE_GENERIC_VALIDATION=
  envelope_identity
  + schema_version_compatibility
  + content_integrity
  + publication_state
  + readback_proof
  + provenance_presence
  + migration_completeness_proof

DOMAIN_VALIDATION=
  domain_identity
  + provider_semantics
  + normalization
  + finality
  + revision/gap rules
```

Проверка, специфичная для ETH, остаётся полномочием Data Bridge.

### 3.5. Удержание и удаление

```text
RETENTION_IS_NOT_AUTOMATIC_DELETE_BY_AGE=YES
PURGE_REQUIRES_AUTHORITY_AND_RECOVERABILITY_GATE=YES
MIGRATION_OR_CUTOVER_STATE_CAN_BLOCK_RETIREMENT=YES
```

### 3.6. Резервная копия и восстановление

```text
BACKUP_EXISTS != RESTORE_IS_PROVEN
RESTORE_REHEARSAL_REQUIRED=YES
RESTORE_PROOF_MUST_BIND_BACKUP_IDENTITY=YES
```

Целевые показатели точки и времени восстановления (`RPO/RTO`) задаются для класса данных и варианта использования, а не одним
универсальным числом для всего AIFE.

## 4. Что F1 намеренно не делает

```text
STANDARD_FILES_MODIFIED=NO
STANDARD_STATUS_PROMOTED=NO
NEW_STD_SERVER_CREATED=NO
DATABASE_VENDOR_SELECTED=NO
BACKUP_PROVIDER_SELECTED=NO
MIGRATION_EXECUTED=NO
RETENTION_PURGE_EXECUTED=NO
```

Если изменение одного стандарта приближается к безопасному лимиту путей или
требует отдельного решения владельца, его можно смыслово разделить. F2 остаётся
закрыт до `PASS` либо до явно одобренного владельцем отложенного пункта с
причиной.

## 5. Следующая контрольная точка

```text
NEXT_CHECKPOINT=CHECKPOINT_DATA_STANDARDS
EXPECTED_SCOPE=AMEND_EXISTING_SIX_DATA_STANDARDS_WITHOUT_RUNTIME_IMPLEMENTATION
F2_ENTRY_AFTER_DATA_STANDARDS=CONDITIONAL_ON_VALIDATED_DISPOSITION_IMPLEMENTATION
```
