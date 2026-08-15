# Семантика Kraken Futures CVD

## Контракт `kraken-futures-cvd/2.0.0`

Контрольований probe для `PI_ETHUSD` довів, що provider-native `cvd` залежить від
параметра `since`: на 577 спільних п'ятихвилинних buckets значення
`buy_volume` і `sell_volume` були однаковими, а різниця `cvd` була сталим
зсувом для кожної пари вікон. Тому абсолютний provider-native CVD не є
глобально канонічним.

Release row зберігає сумісні поля `buy_volume`, `sell_volume`, `cvd`, де `cvd`
залишається provider-native значенням. Поле `provider_native_cvd` є його явним
аліасом. Канонічні поля:

- `net_flow = Decimal(buy_volume) - Decimal(sell_volume)`;
- `canonical_rebased_cvd` — послідовна сума `net_flow` від зафіксованого
  `canonical_anchor` у metadata asset;
- `metric_semantics.schema_version = kraken-futures-cvd/2.0.0`.

Старі consumers можуть продовжувати читати `cvd`, але мають трактувати його як
window-anchored provider evidence. Нові consumers для порівняння різних вікон
мають використовувати `net_flow` або `canonical_rebased_cvd` з однаковим
`canonical_anchor.identity`.

Overlap verifier лишається fail-closed: для звичайних metrics потрібна повна
рівність row; для versioned Kraken Futures CVD завжди потрібна рівність
`timestamp`, `buy_volume` і `sell_volume`, а canonical CVD порівнюється також,
коли anchor identity однаковий. Невідома cumulative semantics не отримує
винятків.
