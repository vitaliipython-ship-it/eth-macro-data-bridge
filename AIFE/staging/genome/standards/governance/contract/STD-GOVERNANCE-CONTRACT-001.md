---
id: STD-GOVERNANCE-CONTRACT-001
domain: GOVERNANCE
title: Contract Authoring Standard
version: '1.1.0'
status: approved
owner: AIFE Standards Team
created: 2026-03-24
updated: 2026-08-26
category: standards
doc_type: standard
language: ru
tags: [contract, governance, authoring, template]
review_cycle_days: 180
next_review_due: 2027-02-22
related:
  - genome/adr/governance/ADR-GOVERNANCE-CONTRACT-001.md
  - genome/standards/governance/STD-GOVERNANCE-AUTHORING-001.md
  - genome/standards/doc/metadata/STD-DOC-METADATA-001.md
  - genome/standards/governance/STD-GOVERNANCE-NAMING-001.md
---

# Contract Authoring Standard

> Стандарт определяет форму, хранение, lifecycle и family-specific правила
> authoring для контрактов в Genome-системе AIFE. Общая grammar canonical ID и
> canonical filename stem читается через `STD-GOVERNANCE-NAMING-001`.

---

## 🧭 Карта смысловых блоков

> Этот owner-side блок фиксирует ограниченный набор `machine-safe carrier`
> для текущего стандарта. Таблица не создаёт второй источник истины: каждый
> смысловой блок читается только через указанный носитель внутри этого файла
> и YAML front matter.

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Каноническая идентичность, статус и владелец стандарта |
| `overview_definition` | `## 1. Обзор`; `## 2. Определение контракта` | `block-level` | Обзор и базовое определение contract family |
| `naming_storage` | `## 3. Именование`; `## 4. Хранение` | `block-level` | Канонические правила именования и размещения контрактов |
| `metadata_sections` | `## 5. Метаданные (frontmatter)`; `## 6. Обязательные секции контракта`; `## 7. Опциональные секции` | `block-level` | Структурный contract для front matter и секций артефакта |
| `lifecycle_compliance` | `## 8. Lifecycle`; `## 9. Enforcement & Compliance`; `## 10. Dependencies`; `## 11. Usage Checklist` | `block-level` | Жизненный цикл, compliance и usage guidance для contract family |

## 1. Обзор

- **Purpose:** Унифицировать структуру контрактов — binding agreements между артефактами, процессами или ролями
- **Scope:** Все файлы типа `CONTRACT-*` в `genome/contracts/`
- **Audience:** AI-агенты (Claude, Copilot, Codex), Architecture Lead

---

## 2. Определение контракта

**Contract** — нормативный документ, фиксирующий binding agreement между конкретными артефактами, процессами или ролями.

Отличия от смежных типов:

| Тип | Назначение | Lifecycle |
|-----|-----------|-----------|
| **Standard (STD-\*)** | Общие нормативные правила (как писать код/документы) | Версионируется, review cycle |
| **ADR** | Point-in-time архитектурное решение | Accepted → deprecated/superseded |
| **Contract** | Binding relation между конкретными артефактами | draft → approved → superseded, с revision history |

---

## 3. Именование

### 3.1 ID контракта

Общая owner-side grammar публикуется в `STD-GOVERNANCE-NAMING-001`.
Для family `CONTRACT` её проекция выглядит так:

```text
CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>
```

- `DOMAIN` — uppercase, из списка доменов Genome (DOC, ARCH, LOG, SEC, GOVERNANCE, API, DATA, MON, PERF, TEST, CHANGE, SERVER)
- `QUALIFIER` — обязательный single semantic qualifier, краткий и стабильный
  mnemonic relation family; это не free-form `NAME` и не prose title chain
- `NNN` — порядковый номер, 3 цифры с ведущими нулями (001-999), всегда
  terminal slot canonical stem

Дополнительные правила:

- canonical ID stem заканчивается на `NNN` и не содержит version/date/title
  chain;
- между `DOMAIN` и `NNN` обязателен ровно один `QUALIFIER`;
- `NNN` начинается с `001` внутри каждого canonical bucket
  `CONTRACT + DOMAIN + QUALIFIER`;
- если полное human-readable имя relation длиннее одного qualifier,
  подробное описание живёт в `title`, H1 и контенте контракта.

Примеры:

- `CONTRACT-DOC-PRR-001` — PRR Integration Contract
- `CONTRACT-ARCH-OWNERSHIP-001` — Ownership Contract *(иллюстративный ID формата; артефакт не развёрнут в текущем scope)*

### 3.2 Имя файла

```text
CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>.md
```

Файл именуется точно как ID. Пример: `CONTRACT-DOC-PRR-001.md`.

---

## 4. Хранение

### 4.1 Каноническое место

```text
genome/contracts/<domain-lowercase>/CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>.md
```

Домен в пути — lowercase. Пример:

```text
genome/contracts/doc/CONTRACT-DOC-PRR-001.md
genome/contracts/arch/CONTRACT-ARCH-OWNERSHIP-001.md  (иллюстративный пример формата; артефакт не развёрнут)
genome/contracts/server/CONTRACT-SERVER-WORK-001.md  (future governed example; artifact is not materialized by domain admission)
```

### 4.2 Реестр

```text
genome/registries/CONTRACTS_REGISTRY.md
```

Формат таблицы унифицирован с STANDARDS_REGISTRY и ADR_REGISTRY.

### 4.3 Иерархия

```text
genome/contracts/
  doc/
    CONTRACT-DOC-PRR-001.md
  arch/
    (будущие контракты)
  governance/
    (будущие контракты)
  server/
    (future generic Server/Data contracts; no artifact is materialized by admission alone)
```

### 4.4 Governance домена `SERVER`

`SERVER` является допустимым contract domain для generic Server/Data mechanism boundaries.
Сам допуск домена не создаёт контрактов, runtime-кода или физической реализации.

```text
SERVER_DOMAIN_ADMITTED=YES
SERVER_DOMAIN_IS_GENERIC_MECHANISM_AUTHORITY=YES
SERVER_DOMAIN_IS_DOMAIN_SEMANTIC_AUTHORITY=NO
F2_CONTRACT_IMPLEMENTATION_STARTED_BY_DOMAIN_ADMISSION=NO
```

Будущие `SERVER` contracts могут владеть generic boundaries для work identity/state,
scheduling/due-computation mechanism, execution/claim/lease/fencing, publication, storage,
access и runtime/configuration-facing contracts в пределах архитектуры AIFE. Они не получают
полномочия на provider/domain identities, normalization, finality, gap/revision,
domain-specific due/retention или resolution semantics. Для ETH эти semantics остаются у
ETH Data Bridge.

Регистрация в `CONTRACTS_REGISTRY.md` выполняется только при фактическом создании
конкретного contract artifact; фиктивная registry row ради admission запрещена.

---

## 5. Метаданные (frontmatter)

Контракт обязан содержать YAML front matter по STD-DOC-METADATA-001:

```yaml
---
id: CONTRACT-DOC-PRR-001
domain: DOC
title: "PRR Integration Contract"
version: "1.0.0"
status: approved
owner: Architecture Lead
created: 2026-03-24
updated: 2026-03-24
review_cycle_days: 180
next_review_due: 2026-09-20
category: standards
doc_type: contract
language: ru
tags: [contract, prr, dev-tz]
related:
  - genome/adr/governance/ADR-GOVERNANCE-CONTRACT-001.md
---
```

Обязательные поля: `id`, `domain`, `title`, `version`, `status`, `owner`, `created`, `updated`, `doc_type: contract`.

---

## 6. Обязательные секции контракта

Каждый контракт обязан содержать следующие секции (в указанном порядке):

### 6.1 Purpose (✅)

Зачем контракт существует. Одно предложение + целевая модель.

### 6.2 Scope (✅)

- К каким артефактам/процессам применяется
- К чему явно НЕ применяется (scope guards)

### 6.3 Core Rules (✅)

Каноническое отношение между артефактами:

- Cardinality (1:1, 1:N, etc.)
- Default prohibitions
- Canonical relation formula

### 6.4 Authority Model (✅)

- Какой артефакт за что отвечает (authority split)
- Conflict precedence order

### 6.5 Naming Contract (✅)

Именование артефактов, которыми управляет контракт (не самого контракта — это определяет данный стандарт).

### 6.6 Placement Contract (✅)

Где хранятся артефакты, которыми управляет контракт. Canonical path с примером.

### 6.7 Agent Rules (✅)

Конкретные инструкции для AI-агентов:

- Когда создавать артефакт (trigger/lazy-creation)
- Когда переиспользовать существующий
- Как обновлять
- Как поддерживать navigation sync

### 6.8 Acceptance Criteria (✅)

Когда контракт считается реализованным. Список проверяемых условий.

### 6.9 Enforcement & Compliance (✅)

Таблица контроля (унифицирована с STD-GOVERNANCE-AUTHORING-001):

```markdown
| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
|-------------|------------------|-------------------|-------|-----------------|
```

---

## 7. Опциональные секции

Добавляются если применимы:

- **Level Policy** — правила по L-классификации (L1-L5)
- **Retention Contract** — что остаётся inline, что выносится
- **Update Rules** — re-review, supersession, closure
- **Migration Policy** — backward compatibility, rollout
- **Exception Rule** — когда допускается отступление
- **Minimal Normative Form** — краткая выжимка (для quick-reference)

---

## 8. Lifecycle

```text
draft → proposed → approved → deprecated → superseded
```

- `draft` — контракт в разработке, не обязателен к исполнению
- `proposed` — на ревью, агенты должны учитывать
- `approved` — обязателен к исполнению всеми агентами
- `deprecated` — заменяется, агенты следуют новому контракту
- `superseded` — полностью заменён, `deprecated_by` указывает на замену

При `status: approved` обязательны `review_cycle_days` и `next_review_due`.

---

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
|-------------|------------------|-------------------|-------|-----------------|
| Контракт содержит все обязательные секции (§6) | Manual | Architecture Review Checklist | Architecture Lead | При создании/обновлении контракта |
| Frontmatter по STD-DOC-METADATA-001 | Automated | pre-commit → metadata_validator | Docs QA | on commit |
| Контракт зарегистрирован в CONTRACTS_REGISTRY | Manual | Governance Review | Architecture Lead | При создании контракта |
| ID соответствует формату `CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>` | Manual | Architecture Review | Architecture Lead | При создании контракта |
| Файл в canonical path genome/contracts/domain/ | Manual | File placement check | Architecture Lead | При создании контракта |

---

## 10. Dependencies

- **Depends on:**
  - `ADR-GOVERNANCE-CONTRACT-001` — решение о введении типа Contract
  - `STD-DOC-METADATA-001` — формат frontmatter
  - `STD-GOVERNANCE-NAMING-001` — общие правила именования
  - `STD-GOVERNANCE-AUTHORING-001` — шаблон авторинга (base)

- **Impacts:**
  - `AGENTS_ARTIFACTS.md` — добавлен тип Contract в карту размещения
  - `CONTRACTS_REGISTRY.md` — новый реестр

---

## 11. Usage Checklist

- [ ] Создать файл контракта с обязательными секциями (§6) и frontmatter (§5)
- [ ] Разместить в `genome/contracts/<domain>/`
- [ ] Зарегистрировать в `genome/registries/CONTRACTS_REGISTRY.md`
- [ ] Убедиться, что связанный ADR (если есть) ссылается на контракт
- [ ] Назначить Owner и `review_cycle_days`
