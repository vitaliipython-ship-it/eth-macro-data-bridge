# Семантика Kraken Futures CVD

## Контракт `kraken-futures-cvd/2.0.0`

Контролируемый probe для `PI_ETHUSD` доказал, что provider-native `cvd` зависит от параметра `since`: на общих пятиминутных buckets значения `buy_volume` и `sell_volume` совпадают, а абсолютный `cvd` отличается постоянным offset для пары окон. Поэтому абсолютный provider-native CVD нельзя считать глобально каноничным между разными request windows.

Release row сохраняет совместимые provider-native поля `buy_volume`, `sell_volume`, `cvd`, где `cvd` остаётся исходным значением Kraken. Поле `provider_native_cvd` используется как явный alias.

Канонические derived поля:

- `net_flow = Decimal(buy_volume) - Decimal(sell_volume)`;
- `canonical_rebased_cvd` — последовательная сумма `net_flow` от зафиксированного `canonical_anchor` в metadata asset;
- `metric_semantics.schema_version = kraken-futures-cvd/2.0.0`.

Старые consumers могут продолжать читать `cvd`, но обязаны трактовать его как window-anchored provider evidence. Новые consumers для сравнения разных окон должны использовать `net_flow` либо `canonical_rebased_cvd` при совместимом `canonical_anchor.identity`.

## Overlap policy

Verifier остаётся fail-closed:

- для обычных metrics требуется полное совпадение row;
- для versioned Kraken Futures CVD всегда требуется совпадение `timestamp`, `buy_volume` и `sell_volume`;
- canonical rebased CVD дополнительно сравнивается, когда anchor identity совместим;
- неизвестная cumulative semantics не получает исключений.

Этот контракт относится только к CVD и не разрешает blanket tolerance для других Kraken Futures metrics. Provider-revisable snapshot families классифицируются отдельно в machine-readable metric semantics contract и требуют собственного evidence.
