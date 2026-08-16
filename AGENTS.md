# AGENTS.md

## Назначение

Это первая и каноническая semantic точка входа для любого агента, который читает или изменяет `eth-macro-data-bridge`. Репозиторий является authority рыночных фактов; Elliott/NEoWave, гипотезы, сценарии и интерпретация принадлежат `eth-macro-research`.

Документация ведётся на русском. Machine identifiers, provider names, schema fields, paths и commands сохраняются на английском.

## Канонический market-data route

Не начинать с provider path, Release tag, asset filename или URL.

```text
AGENTS.md
→ bridge-contract.json
→ canonical_paths.capability_index
→ semantic capability discovery
→ tools/capability_index.py resolve(series_id, [from,to), optional cutoff)
→ validated ResolutionPlan
→ canonical physical manifest/resource
→ tools/history_access.py slice
→ verified WARM / immutable COLD bytes
```

`bridge-contract.json` — route/provider-policy authority. Capability index — derived discovery layer, не byte authority. `ResolutionPlan` — единственный input authority reader-а. Exact Release locator/size/SHA и Git resources принадлежат canonical physical manifests.

## Agent-callable historical read

Preferred local adapter:

```bash
python tools/history_consumer.py read \
  --series-id spot.binance-spot.ETHUSDT.ohlcv.1h \
  --from 2025-04-09T00:00:00Z \
  --to 2025-08-25T00:00:00Z \
  --mode strict \
  --format csv \
  --output candles.csv \
  --plan-output resolution-plan.json \
  --diagnostics-output diagnostics.json \
  --receipt-output receipt.json
```

`tools/history_consumer.py` не является вторым resolver: он композиционно вызывает canonical semantic resolver и передаёт полученный `ResolutionPlan` существующему plan-only reader.

### ChatGPT/connector runtime без direct Release body или workflow_dispatch

Если агент не может выполнить local reader и подключённый GitHub primitive не предоставляет `workflow_dispatch(inputs)`, использовать `bridge-contract.json.semantic_resolution.agent_transport`.

Текущий transport — owner-only GitHub Issue request:

```text
TITLE: [history-read] <short description>
BODY: pure JSON object
```

Допустимы только semantic fields:

```json
{
  "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
  "from_utc": "2025-04-09T00:00:00Z",
  "to_utc": "2025-08-25T00:00:00Z",
  "cutoff_utc": null,
  "mode": "strict",
  "output_format": "csv"
}
```

Запрещено передавать asset/release/path/URL/SHA. Workflow сам выполняет тот же canonical resolver → ResolutionPlan → reader и после materialization оставляет Issue receipt с `RUN_ID`, rows, plan/output SHA и artifact URL. Ephemeral Actions artifact содержит candles + plan + diagnostics + receipt и **не является authority**.

После Issue receipt агент получает run artifacts штатным GitHub connector и проверяет receipt/diagnostics до анализа.

Если оба canonical transports недоступны, вернуть `DATA_TRANSPORT_BLOCKED`; не заменять данные прямым provider API. Provider API допустим только как отдельная corroboration, не replacement authority.

## Hard guardrails

1. `ResolutionPlan` остаётся input authority reader-а.
2. Capability catalog/index — только derived projection, не второй SSOT.
3. Никаких guessed/hardcoded Release routes.
4. WARM/COLD merge и integrity deterministic и SHA-pinned.
5. Никаких synthetic gap fills.
6. Никакого silent provider substitution.
7. Binance USDⓈ-M остаётся `DISABLED_BY_POLICY`, пока contract явно не изменён.
8. Historical options/order-book surface не фабрикуется.
9. Git — HOT/WARM/control plane; max deep history — immutable Release assets.
10. Runtime transport не становится data authority и не копирует raw history в Research.

## D6 status

```text
D6.1=QUALIFIED/PASS
D6.2A=QUALIFIED/PASS
D6.2B=QUALIFIED/PASS
D6.3=QUALIFIED/PASS
D6.4=QUALIFIED/PASS/ACTIVE
D6.5=QUALIFIED/PASS/MERGED
AGENT_RUNTIME_HISTORY_TRANSPORT=ACTIVE
```

Research migration authority: `eth-macro-research` main after D6.5. Historical-access as-built details: `docs/semantics/history-access-v1.md`.

## Provider/history semantics

`history_mode` values:

```text
MAX_AVAILABLE
PROVIDER_LIMITED
FORWARD_ONLY
FROZEN_REFERENCE
UNAVAILABLE
```

Known Binance H1 `2023-03-24T13:00:00Z` provider-native no-trading gap remains fail-closed in strict mode; no synthetic candle is permitted.

## Выполнение и validation

```bash
python -m compileall -q src tools tests
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

Network-backed historical materialization qualification остаётся отдельным workflow. Route/runtime changes не являются причиной повторного D5 acquisition или repack immutable Releases.

## Ownership boundaries

Не изменять в рамках consumer-read transport:

- collector/cadence;
- provider acquisition;
- immutable Releases/COLD packaging;
- raw market rows;
- server/runtime acquisition plane;
- Macro Watch interpretation;
- Research wave/hypothesis objects.

Новый mechanism допускается только если закрывает доказанный operational risk, проще существующих вариантов и уменьшает число ручных действий следующего агента.
