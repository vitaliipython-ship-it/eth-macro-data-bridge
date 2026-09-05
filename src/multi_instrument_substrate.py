from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Protocol
from zoneinfo import ZoneInfo

from canonical_json import canonical_json_bytes

CONFIG_SCHEMA = "free-multi-instrument-substrate-config/1.0.0"
RECEIPT_SCHEMA = "free-multi-instrument-acquisition-receipt/1.0.0"
NORMALIZED_SCHEMA = "free-multi-instrument-normalized-sample/1.0.0"
PLAN_SCHEMA = "market-data-resolution-plan/2.0.0"
SAMPLE_CLASS = "NON_PRODUCTION_INTEGRATION_SAMPLE"
ALLOWED_MARKET_TYPES = {"SPOT", "CFD", "REFERENCE_SERIES", "FUTURES_SINGLE", "FUTURES_CONTINUOUS", "INDEX", "OTHER"}
ALLOWED_SESSION_KINDS = {"24X7", "DECLARED_SESSION", "DAILY_BREAK", "WEEKEND_CLOSE", "HOLIDAY_OR_SPECIAL_CLOSE", "UNKNOWN_SESSION"}
ALLOWED_GAP_CLASSES = {"REAL_PRICE_MOVE", "SESSION_REOPEN_GAP", "MARKET_CLOSED_INTERVAL", "MISSING_DATA", "PROVIDER_OUTAGE", "ROLL_GAP", "ADJUSTMENT_ARTIFACT", "UNKNOWN_GAP"}
ALLOWED_SERIES_KINDS = {"OHLCV", "SCALAR_TIME_SERIES"}
ALLOWED_COVERAGE = {"FIXED_GRID", "SAMPLED_SCHEDULE", "EVENT_DRIVEN"}


def canonical_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value: Any) -> str:
    return sha256(canonical_bytes(value))


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"timestamp must be UTC: {value}")
    return parsed.astimezone(timezone.utc)


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def to_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def decimal_text(value: Any, field: str) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric field {field}") from exc
    if not number.is_finite():
        raise ValueError(f"non-finite numeric field {field}")
    return format(number, "f")


def safe_component(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    result = "".join(ch if ch in allowed else "_" for ch in value)
    if not value or result in {"", ".", ".."}:
        raise ValueError("invalid identity component")
    return result


@dataclass(frozen=True)
class AcquisitionWindow:
    start_utc: str
    end_utc: str

    def validate(self) -> "AcquisitionWindow":
        if parse_utc(self.start_utc) >= parse_utc(self.end_utc):
            raise ValueError("acquisition window must be non-empty")
        return self

    @property
    def start_ms(self) -> int:
        return to_ms(parse_utc(self.start_utc))

    @property
    def end_ms(self) -> int:
        return to_ms(parse_utc(self.end_utc))


@dataclass(frozen=True)
class InstrumentConfig:
    provider_id: str
    provider_instrument_id: str
    economic_subject_id: str
    market_type: str
    price_semantics: str
    granularity: str
    interval_ms: int | None
    series_kind: str
    coverage_semantics: str
    source_timezone: str
    source_time_kind: str
    session_calendar_ref: str
    session_kind: str
    acquisition_method: str
    source_provenance: str
    adapter: str
    series_id: str
    enabled_for_live_probe: bool
    endpoint: str | None = None
    value_column: str | None = None
    date_column: str | None = None
    optional_semantics: Mapping[str, Any] | None = None

    def validate(self) -> "InstrumentConfig":
        strings = (
            self.provider_id,
            self.provider_instrument_id,
            self.economic_subject_id,
            self.price_semantics,
            self.granularity,
            self.source_timezone,
            self.source_time_kind,
            self.session_calendar_ref,
            self.acquisition_method,
            self.source_provenance,
            self.adapter,
            self.series_id,
        )
        if any(not isinstance(value, str) or not value for value in strings):
            raise ValueError("instrument configuration string field missing")
        if self.market_type not in ALLOWED_MARKET_TYPES:
            raise ValueError(f"unsupported market_type: {self.market_type}")
        if self.series_kind not in ALLOWED_SERIES_KINDS:
            raise ValueError(f"unsupported series_kind: {self.series_kind}")
        if self.coverage_semantics not in ALLOWED_COVERAGE:
            raise ValueError(f"unsupported coverage_semantics: {self.coverage_semantics}")
        if self.session_kind not in ALLOWED_SESSION_KINDS:
            raise ValueError(f"unsupported session_kind: {self.session_kind}")
        if self.interval_ms is not None and (not isinstance(self.interval_ms, int) or self.interval_ms <= 0):
            raise ValueError("interval_ms must be positive when present")
        if self.coverage_semantics == "FIXED_GRID" and self.interval_ms is None:
            raise ValueError("FIXED_GRID requires interval_ms")
        ZoneInfo(self.source_timezone)
        forbidden = {"synthetic_roll", "canonical_i7_wti", "production_capability"}
        if self.optional_semantics and forbidden & set(self.optional_semantics):
            raise ValueError("I7/production-specific semantics are forbidden")
        return self


@dataclass(frozen=True)
class ProviderBatch:
    raw_bytes: bytes
    retrieved_at_utc: str
    retrieval_method: str
    source_provenance: str
    content_type: str


class ProviderAdapter(Protocol):
    adapter_id: str

    def acquire(self, config: InstrumentConfig, window: AcquisitionWindow) -> ProviderBatch: ...

    def parse(self, config: InstrumentConfig, batch: ProviderBatch) -> list[dict[str, Any]]: ...


class StaticRowsAdapter:
    adapter_id = "STATIC_ROWS"

    def __init__(self, rows: list[dict[str, Any]], retrieved_at_utc: str = "2026-09-05T00:00:00Z"):
        self._rows = json.loads(json.dumps(rows))
        self._retrieved_at_utc = retrieved_at_utc

    def acquire(self, config: InstrumentConfig, window: AcquisitionWindow) -> ProviderBatch:
        config.validate()
        window.validate()
        return ProviderBatch(
            raw_bytes=canonical_bytes({"rows": self._rows}),
            retrieved_at_utc=self._retrieved_at_utc,
            retrieval_method="SYNTHETIC_OR_PREACQUIRED_ROWS_TEST_ADAPTER",
            source_provenance="NON_VENDOR_TEST_FIXTURE",
            content_type="application/json",
        )

    def parse(self, config: InstrumentConfig, batch: ProviderBatch) -> list[dict[str, Any]]:
        rows = json.loads(batch.raw_bytes).get("rows")
        if not isinstance(rows, list):
            raise ValueError("STATIC_ROWS payload malformed")
        return rows


def source_time_to_ms(config: InstrumentConfig, value: Any) -> int:
    text = str(value).strip()
    if config.source_time_kind == "EPOCH_MS":
        return int(text)
    zone = ZoneInfo(config.source_timezone)
    if config.source_time_kind == "DATE_PERIOD":
        parsed = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=zone)
    elif config.source_time_kind == "ISO8601":
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=zone)
    else:
        raise ValueError(f"unsupported source_time_kind: {config.source_time_kind}")
    return to_ms(parsed.astimezone(timezone.utc))


def validate_ohlcv(row: Mapping[str, Any]) -> dict[str, str]:
    values = {field: decimal_text(row[field], field) for field in ("open", "high", "low", "close", "volume")}
    o, h, l, c, volume = (Decimal(values[field]) for field in ("open", "high", "low", "close", "volume"))
    if h < max(o, l, c) or l > min(o, h, c) or volume < 0:
        raise ValueError("invalid OHLCV bounds")
    return values


def normalize_records(
    config: InstrumentConfig,
    provider_rows: list[dict[str, Any]],
    window: AcquisitionWindow,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    input_order: list[int] = []
    for raw in provider_rows:
        if not isinstance(raw, dict) or "source_time" not in raw:
            raise ValueError("provider row must contain source_time")
        ts = source_time_to_ms(config, raw["source_time"])
        if not (window.start_ms <= ts < window.end_ms):
            continue
        input_order.append(ts)
        if config.series_kind == "OHLCV":
            normalized.append({"timestamp_ms": ts, **validate_ohlcv(raw)})
        else:
            normalized.append({"timestamp_ms": ts, "value": decimal_text(raw["value"], "value")})
    if not normalized:
        raise ValueError("no normalized records fall inside requested window")
    duplicate_count = len(normalized) - len({row["timestamp_ms"] for row in normalized})
    if duplicate_count:
        raise ValueError("duplicate timestamps are forbidden")
    out_of_order = sum(1 for a, b in zip(input_order, input_order[1:]) if b < a)
    normalized.sort(key=lambda row: row["timestamp_ms"])
    timestamps = [row["timestamp_ms"] for row in normalized]
    gaps = []
    if config.interval_ms is not None:
        gaps = [b - a for a, b in zip(timestamps, timestamps[1:]) if b - a > config.interval_ms]
    return normalized, {
        "record_count": len(normalized),
        "duplicate_timestamps": duplicate_count,
        "out_of_order_timestamps": out_of_order,
        "invalid_ohlc": 0,
        "non_finite_values": 0,
        "raw_gaps": len(gaps),
        "normalized_gaps": len(gaps),
        "max_gap_ms": max(gaps) if gaps else None,
        "gap_classes": ["UNKNOWN_GAP"] if gaps else [],
    }


def normalized_payload(config: InstrumentConfig, records: list[dict[str, Any]]) -> dict[str, Any]:
    if config.series_kind == "OHLCV":
        columns = ["timestamp_ms", "open", "high", "low", "close", "volume"]
        rows = [[r["timestamp_ms"], r["open"], r["high"], r["low"], r["close"], r["volume"]] for r in records]
    else:
        columns = ["timestamp_ms", "value"]
        rows = [[r["timestamp_ms"], r["value"]] for r in records]
    return {
        "schema_version": NORMALIZED_SCHEMA,
        "sample_class": SAMPLE_CLASS,
        "provider": config.provider_id,
        "symbol": config.provider_instrument_id,
        "interval": config.granularity,
        "economic_subject_id": config.economic_subject_id,
        "market_type": config.market_type,
        "price_semantics": config.price_semantics,
        "session": {
            "session_calendar_ref": config.session_calendar_ref,
            "session_kind": config.session_kind,
            "source_timezone": config.source_timezone,
            "source_time_kind": config.source_time_kind,
        },
        "columns": columns,
        "records": rows,
    }


def config_identity(config: InstrumentConfig) -> dict[str, Any]:
    return {
        "provider_id": config.provider_id,
        "provider_instrument_id": config.provider_instrument_id,
        "economic_subject_id": config.economic_subject_id,
        "market_type": config.market_type,
        "price_semantics": config.price_semantics,
        "granularity": config.granularity,
        "interval_ms": config.interval_ms,
        "series_kind": config.series_kind,
        "coverage_semantics": config.coverage_semantics,
        "source_timezone": config.source_timezone,
        "source_time_kind": config.source_time_kind,
        "session_calendar_ref": config.session_calendar_ref,
        "session_kind": config.session_kind,
        "acquisition_method": config.acquisition_method,
        "source_provenance": config.source_provenance,
        "adapter": config.adapter,
        "series_id": config.series_id,
        "optional_semantics": dict(config.optional_semantics or {}),
    }


def run_acquisition(
    config: InstrumentConfig,
    window: AcquisitionWindow,
    adapter: ProviderAdapter,
    *,
    staging_root: Path,
) -> dict[str, Any]:
    config.validate()
    window.validate()
    if getattr(adapter, "adapter_id", None) != config.adapter:
        raise ValueError("provider adapter does not match instrument configuration")
    batch = adapter.acquire(config, window)
    records, quality = normalize_records(config, adapter.parse(config, batch), window)
    payload = normalized_payload(config, records)
    raw_sha = sha256(batch.raw_bytes)
    normalized_bytes = canonical_bytes(payload)
    normalized_sha = sha256(normalized_bytes)
    config_sha = fingerprint(config_identity(config))
    acquisition_identity = fingerprint(
        {
            "provider_id": config.provider_id,
            "provider_instrument_id": config.provider_instrument_id,
            "economic_subject_id": config.economic_subject_id,
            "requested_window": {"start_utc": window.start_utc, "end_utc": window.end_utc},
            "granularity": config.granularity,
            "configuration_fingerprint": config_sha,
        }
    )
    generation_id = fingerprint({"acquisition_identity": acquisition_identity, "raw_fingerprint": raw_sha})
    generation_root = (
        Path(staging_root)
        / "multi-instrument"
        / safe_component(config.provider_id)
        / safe_component(config.provider_instrument_id)
        / acquisition_identity
        / generation_id
    )
    generation_root.mkdir(parents=True, exist_ok=True)
    raw_path = generation_root / "raw.bin"
    normalized_path = generation_root / "normalized.json"
    if raw_path.exists() and raw_path.read_bytes() != batch.raw_bytes:
        raise ValueError("conflicting raw bytes at same generation")
    raw_path.write_bytes(batch.raw_bytes)
    if normalized_path.exists() and normalized_path.read_bytes() != normalized_bytes:
        raise ValueError("conflicting normalized bytes at same generation")
    normalized_path.write_bytes(normalized_bytes)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "sample_class": SAMPLE_CLASS,
        "provider_id": config.provider_id,
        "provider_instrument": config.provider_instrument_id,
        "economic_subject": config.economic_subject_id,
        "market_type": config.market_type,
        "retrieval_method": batch.retrieval_method,
        "source_provenance": batch.source_provenance,
        "retrieved_at_utc": batch.retrieved_at_utc,
        "requested_window": {"start_utc": window.start_utc, "end_utc": window.end_utc},
        "actual_window": {
            "start_utc": utc_iso(datetime.fromtimestamp(records[0]["timestamp_ms"] / 1000, timezone.utc)),
            "end_utc": utc_iso(datetime.fromtimestamp(records[-1]["timestamp_ms"] / 1000, timezone.utc)),
        },
        "granularity": config.granularity,
        "price_semantics": config.price_semantics,
        "source_timezone": config.source_timezone,
        "source_time_kind": config.source_time_kind,
        "record_count": len(records),
        "raw_fingerprint": raw_sha,
        "normalized_fingerprint": normalized_sha,
        "configuration_fingerprint": config_sha,
        "acquisition_identity": acquisition_identity,
        "generation_id": generation_id,
        "quality": quality,
        "raw_or_staging_is_canonical_history": False,
        "production_capability_advertised": False,
    }
    receipt_bytes = canonical_bytes(receipt)
    receipt_path = generation_root / f"receipt-{sha256(receipt_bytes)}.json"
    if receipt_path.exists() and receipt_path.read_bytes() != receipt_bytes:
        raise ValueError("conflicting receipt bytes for same receipt fingerprint")
    receipt_path.write_bytes(receipt_bytes)
    return {
        "receipt": receipt,
        "normalized_payload": payload,
        "raw_path": raw_path,
        "normalized_path": normalized_path,
        "receipt_path": receipt_path,
        "normalized_relative_path": normalized_path.relative_to(staging_root).as_posix(),
        "idempotent_reingestion": "PASS",
    }


def aggregate_ohlcv(
    records: list[dict[str, Any]],
    *,
    source_interval_ms: int,
    target_interval_ms: int,
    bucket_anchor_ms: int,
) -> list[dict[str, Any]]:
    if source_interval_ms <= 0 or target_interval_ms <= source_interval_ms or target_interval_ms % source_interval_ms:
        raise ValueError("target interval must be an integer multiple of source interval")
    expected_per_bucket = target_interval_ms // source_interval_ms
    ordered = sorted(records, key=lambda row: row["timestamp_ms"])
    if len({row["timestamp_ms"] for row in ordered}) != len(ordered):
        raise ValueError("duplicate timestamps are forbidden")
    buckets: dict[int, list[dict[str, Any]]] = {}
    for row in ordered:
        ts = int(row["timestamp_ms"])
        key = bucket_anchor_ms + ((ts - bucket_anchor_ms) // target_interval_ms) * target_interval_ms
        buckets.setdefault(key, []).append(row)
    result = []
    for start in sorted(buckets):
        bucket = buckets[start]
        expected = [start + i * source_interval_ms for i in range(expected_per_bucket)]
        if [int(row["timestamp_ms"]) for row in bucket] != expected:
            raise ValueError("incomplete aggregation bucket; synthetic fill is forbidden")
        highs = [Decimal(str(row["high"])) for row in bucket]
        lows = [Decimal(str(row["low"])) for row in bucket]
        volumes = [Decimal(str(row["volume"])) for row in bucket]
        result.append(
            {
                "timestamp_ms": start,
                "open": str(bucket[0]["open"]),
                "high": format(max(highs), "f"),
                "low": format(min(lows), "f"),
                "close": str(bucket[-1]["close"]),
                "volume": format(sum(volumes), "f"),
            }
        )
    return result


def build_nonproduction_resolution_plan(config: InstrumentConfig, acquisition_result: Mapping[str, Any]) -> dict[str, Any]:
    config.validate()
    if config.coverage_semantics != "FIXED_GRID" or config.interval_ms is None:
        raise ValueError("non-production reader proof requires FIXED_GRID")
    receipt = acquisition_result["receipt"]
    if receipt.get("sample_class") != SAMPLE_CLASS or receipt.get("production_capability_advertised") is not False:
        raise ValueError("only non-production samples may use the test-plan builder")
    records = acquisition_result["normalized_payload"].get("records", [])
    if not records:
        raise ValueError("normalized payload has no records")
    start = int(records[0][0])
    end = int(records[-1][0]) + config.interval_ms
    relative_path = str(acquisition_result["normalized_relative_path"])
    raw = Path(acquisition_result["normalized_path"]).read_bytes()
    body = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": {
            "market_data_semantic_authority": "ETH_MACRO_DATA_BRIDGE",
            "test_route": "NON_PRODUCTION_INTEGRATION_TEST_ONLY",
            "capability_advertisement": False,
            "second_resolver": False,
        },
        "request": {"series_id": config.series_id, "start_ms": start, "end_ms": end, "current_policy": "FINALIZED_ONLY"},
        "series": {
            "series_id": config.series_id,
            "series_kind": config.series_kind,
            "coverage_semantics": config.coverage_semantics,
            "finality_policy": "FINALIZED_ONLY",
            "revision_policy": "IMMUTABLE",
            "interval_ms": config.interval_ms,
            "economic_subject_id": config.economic_subject_id,
            "market_type": config.market_type,
            "session_calendar_ref": config.session_calendar_ref,
        },
        "segments": [
            {
                "segment_id": f"nonprod-{receipt['generation_id'][:16]}",
                "residence_role": "WARM",
                "adapter_profile": "NON_PRODUCTION_STAGING_V1",
                "resource_ref": f"nonprod:{receipt['generation_id']}",
                "integrity_evidence": {"sample_class": SAMPLE_CLASS, "receipt_fingerprint": fingerprint(receipt)},
                "storage": "GIT_WARM_RESOURCE",
                "generation_id": receipt["generation_id"],
                "sha256": sha256(raw),
                "size_bytes": len(raw),
                "read_start_ms": start,
                "read_end_ms": end,
                "physical_descriptor": {"resource_path": relative_path},
                "resource_path": relative_path,
                "source_provider": config.provider_id,
                "instrument": config.provider_instrument_id,
                "source_interval_or_metric": config.granularity,
                "known_gaps": [],
            }
        ],
    }
    return {**body, "plan_sha256": sha256(canonical_bytes(body))}


def load_repository_config(path: Path) -> dict[str, InstrumentConfig]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("multi-instrument config schema mismatch")
    activation = payload.get("activation", {})
    if activation.get("new_production_provider_active") is not False:
        raise ValueError("production provider activation is forbidden")
    if activation.get("production_capability_advertisement") is not False:
        raise ValueError("production capability advertisement is forbidden")
    configs: dict[str, InstrumentConfig] = {}
    for row in payload.get("instruments", []):
        config = InstrumentConfig(
            provider_id=row["provider_id"],
            provider_instrument_id=row["provider_instrument_id"],
            economic_subject_id=row["economic_subject_id"],
            market_type=row["market_type"],
            price_semantics=row["price_semantics"],
            granularity=row["granularity"],
            interval_ms=row.get("interval_ms"),
            series_kind=row["series_kind"],
            coverage_semantics=row["coverage_semantics"],
            source_timezone=row["source_timezone"],
            source_time_kind=row["source_time_kind"],
            session_calendar_ref=row["session_calendar_ref"],
            session_kind=row["session_kind"],
            acquisition_method=row["acquisition_method"],
            source_provenance=row["source_provenance"],
            adapter=row["adapter"],
            series_id=row["series_id"],
            enabled_for_live_probe=bool(row.get("enabled_for_live_probe", False)),
            endpoint=row.get("endpoint"),
            value_column=row.get("value_column"),
            date_column=row.get("date_column"),
            optional_semantics=row.get("optional_semantics"),
        ).validate()
        if config.series_id in configs:
            raise ValueError(f"duplicate series_id: {config.series_id}")
        configs[config.series_id] = config
    if not configs:
        raise ValueError("multi-instrument config has no instruments")
    return configs


def server_config_from_environment() -> tuple[Path, Path]:
    config_path = os.environ.get("AIFE_MULTI_INSTRUMENT_CONFIG")
    staging_root = os.environ.get("AIFE_MULTI_INSTRUMENT_STAGING_ROOT")
    if not config_path or not staging_root:
        raise ValueError("AIFE_MULTI_INSTRUMENT_CONFIG and AIFE_MULTI_INSTRUMENT_STAGING_ROOT are required")
    return Path(config_path), Path(staging_root)
