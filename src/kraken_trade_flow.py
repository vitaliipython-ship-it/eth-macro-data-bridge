from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import quote

KRAKEN_FUTURES_HISTORY_BASE = "https://futures.kraken.com/derivatives/api/v3/history"
BUCKET_MS = 300_000
MAX_HISTORY_PAGES = 8
FLOW_METRICS = ("trade-count", "trade-volume", "aggressor-differential", "cvd")


def _iso_to_ms(value: str) -> int:
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("Kraken trade timestamp must contain timezone")
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"invalid Kraken trade {field}: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"non-finite Kraken trade {field}: {value!r}")
    return parsed


def normalize_trade(raw: Any, requested_product_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Kraken trade row must be an object")
    timestamp_ms = _iso_to_ms(raw["time"])
    price = _decimal(raw["price"], "price")
    size = _decimal(raw["size"], "size")
    if price <= 0 or size < 0:
        raise ValueError("Kraken trade price must be >0 and size must be >=0")
    side = str(raw.get("side") or "").lower()
    aggressor_side = side if side in ("buy", "sell") else "unknown"
    observed_product = raw.get("symbol")
    if observed_product is not None and str(observed_product).upper() != requested_product_id.upper():
        product_match = False
    else:
        # The public history endpoint is request-scoped by symbol; current response schema
        # does not require symbol on each trade row.
        product_match = True
    return {
        "timestamp_ms": timestamp_ms,
        "price": str(price),
        "native_size": str(size),
        "aggressor_side": aggressor_side,
        "trade_id": raw.get("trade_id"),
        "type": raw.get("type"),
        "observed_product_id": None if observed_product is None else str(observed_product),
        "product_match": product_match,
    }


def collect_trade_flow_evidence(
    get: Callable[[str], dict[str, Any]],
    now_ms: int,
    requested_product_id: str,
    *,
    bucket_ms: int = BUCKET_MS,
    max_pages: int = MAX_HISTORY_PAGES,
) -> dict[str, Any]:
    bucket_end = (now_ms // bucket_ms) * bucket_ms
    bucket_start = bucket_end - bucket_ms
    diagnostics: dict[str, Any] = {
        "subscription_requested": False,
        "subscription_acknowledged": False,
        "acquisition_mode": "REST_PUBLIC_HISTORY",
        "reconnect_count": 0,
        "sequence_gap_status": "NOT_APPLICABLE_REST_HISTORY",
        "received_at_ms": now_ms,
        "product_identity_authority": "REQUEST_SCOPED_ENDPOINT",
        "requested_product_id": requested_product_id,
        "observed_product_ids": [],
        "raw_trade_message_count": 0,
        "parsed_trade_count": 0,
        "product_matched_trade_count": 0,
        "timestamp_matched_trade_count": 0,
        "bucketed_trade_count": 0,
        "first_trade_timestamp": None,
        "last_trade_timestamp": None,
        "bucket_start": bucket_start,
        "bucket_end": bucket_end,
        "native_quantity_sum": None,
        "normalized_quantity_sum": None,
        "normalization_status": "UNAVAILABLE",
        "buy_aggressor_count": 0,
        "sell_aggressor_count": 0,
        "unknown_aggressor_count": 0,
        "buy_volume": None,
        "sell_volume": None,
        "signed_volume": None,
        "feed_observed": False,
        "coverage_complete": False,
        "last_trade_event_at": None,
        "transport_error": None,
        "parser_error": None,
        "drop_reason_counts": {},
        "pages": 0,
        "endpoint": KRAKEN_FUTURES_HISTORY_BASE,
        "aggressor_semantics": "KRAKEN_PUBLIC_HISTORY_SIDE_IS_TAKER_SIDE",
    }
    parsed: list[dict[str, Any]] = []
    observed_ids: set[str] = set()
    drops: Counter[str] = Counter()
    cursor: str | None = None
    oldest_seen: int | None = None
    server_time_ms: int | None = None
    seen_trade_keys: set[tuple[Any, ...]] = set()

    for _ in range(max_pages):
        url = f"{KRAKEN_FUTURES_HISTORY_BASE}?symbol={quote(requested_product_id)}"
        if cursor is not None:
            url += f"&lastTime={quote(cursor)}"
        try:
            response = get(url)
        except Exception as exc:
            diagnostics["transport_error"] = f"{type(exc).__name__}: {exc}"
            break
        diagnostics["pages"] += 1
        if response.get("result") != "success":
            diagnostics["transport_error"] = f"Kraken trade history failed: {response.get('error') or response.get('errors')}"
            break
        diagnostics["feed_observed"] = True
        if response.get("serverTime"):
            try:
                server_time_ms = _iso_to_ms(response["serverTime"])
            except Exception as exc:
                diagnostics["parser_error"] = f"serverTime: {type(exc).__name__}: {exc}"
                break
        history = response.get("history")
        if not isinstance(history, list):
            diagnostics["parser_error"] = "Kraken trade history missing history list"
            break
        diagnostics["raw_trade_message_count"] += len(history)
        for raw in history:
            try:
                trade = normalize_trade(raw, requested_product_id)
            except Exception as exc:
                drops["PARSER_ERROR"] += 1
                diagnostics["parser_error"] = f"{type(exc).__name__}: {exc}"
                break
            key = (
                trade.get("trade_id"),
                trade["timestamp_ms"],
                trade["price"],
                trade["native_size"],
                trade["aggressor_side"],
            )
            if key in seen_trade_keys:
                drops["DUPLICATE_PAGINATION"] += 1
                continue
            seen_trade_keys.add(key)
            parsed.append(trade)
            diagnostics["parsed_trade_count"] += 1
            if trade["observed_product_id"]:
                observed_ids.add(trade["observed_product_id"])
            if not trade["product_match"]:
                drops["PRODUCT_MISMATCH"] += 1
                continue
            diagnostics["product_matched_trade_count"] += 1
            ts = trade["timestamp_ms"]
            oldest_seen = ts if oldest_seen is None else min(oldest_seen, ts)
        if diagnostics["parser_error"]:
            break
        if not history:
            break
        oldest_raw = min(history, key=lambda x: _iso_to_ms(x["time"]))
        oldest_ts = _iso_to_ms(oldest_raw["time"])
        oldest_seen = oldest_ts if oldest_seen is None else min(oldest_seen, oldest_ts)
        if oldest_ts <= bucket_start:
            break
        if len(history) < 100:
            # Kraken documents retention as "7 days or recent engine restart". A short
            # page alone therefore does NOT prove the bucket start was continuously
            # observable; remain fail-closed unless an execution at/before start exists.
            break
        next_cursor = str(oldest_raw["time"])
        if next_cursor == cursor:
            diagnostics["transport_error"] = "Kraken trade history pagination stalled"
            break
        cursor = next_cursor

    diagnostics["observed_product_ids"] = sorted(observed_ids)
    diagnostics["product_identity_match"] = not bool(drops.get("PRODUCT_MISMATCH"))
    server_covers_end = server_time_ms is not None and server_time_ms >= bucket_end
    history_covers_start = oldest_seen is not None and oldest_seen <= bucket_start
    diagnostics["coverage_complete"] = bool(
        diagnostics["feed_observed"] and server_covers_end and history_covers_start
    )

    matched = [trade for trade in parsed if trade["product_match"]]
    for trade in matched:
        if trade["timestamp_ms"] >= bucket_end:
            drops["AT_OR_AFTER_BUCKET_END"] += 1
        elif trade["timestamp_ms"] < bucket_start:
            drops["BEFORE_BUCKET_START"] += 1
    timestamp_matched = [trade for trade in matched if trade["timestamp_ms"] < bucket_end]
    bucketed = [trade for trade in timestamp_matched if trade["timestamp_ms"] >= bucket_start]
    diagnostics["drop_reason_counts"] = dict(sorted(drops.items()))
    diagnostics["timestamp_matched_trade_count"] = len(timestamp_matched)
    diagnostics["bucketed_trade_count"] = len(bucketed)
    if parsed:
        timestamps = [trade["timestamp_ms"] for trade in parsed]
        diagnostics["first_trade_timestamp"] = min(timestamps)
        diagnostics["last_trade_timestamp"] = max(timestamps)
        diagnostics["last_trade_event_at"] = max(timestamps)

    native_sum = sum((Decimal(trade["native_size"]) for trade in bucketed), Decimal(0))
    buys = [trade for trade in bucketed if trade["aggressor_side"] == "buy"]
    sells = [trade for trade in bucketed if trade["aggressor_side"] == "sell"]
    unknown = [trade for trade in bucketed if trade["aggressor_side"] == "unknown"]
    buy_volume = sum((Decimal(trade["native_size"]) for trade in buys), Decimal(0))
    sell_volume = sum((Decimal(trade["native_size"]) for trade in sells), Decimal(0))
    diagnostics.update(
        {
            "native_quantity_sum": str(native_sum) if diagnostics["coverage_complete"] else None,
            "buy_aggressor_count": len(buys),
            "sell_aggressor_count": len(sells),
            "unknown_aggressor_count": len(unknown),
            "buy_volume": str(buy_volume) if diagnostics["coverage_complete"] else None,
            "sell_volume": str(sell_volume) if diagnostics["coverage_complete"] else None,
            "signed_volume": str(buy_volume - sell_volume)
            if diagnostics["coverage_complete"] and not unknown
            else None,
        }
    )
    return diagnostics


KRAKEN_ANALYTICS_INTERVAL_SECONDS = 300
KRAKEN_ANALYTICS_TIMESTAMP_SEMANTICS = "BUCKET_END"


def _native_observation(metric: dict[str, Any]) -> tuple[int | None, Any]:
    latest = metric.get("latest")
    if not isinstance(latest, (list, tuple)) or len(latest) < 2:
        return None, None
    try:
        timestamp = int(latest[0])
    except (TypeError, ValueError):
        return None, latest[1]
    return timestamp, latest[1]


def _temporal_alignment(
    metric: dict[str, Any], evidence: dict[str, Any], native_timestamp: int | None
) -> tuple[str, int | None, str]:
    raw_start = evidence.get("bucket_start")
    raw_end = evidence.get("bucket_end")
    semantics = str(
        metric.get("native_timestamp_semantics") or KRAKEN_ANALYTICS_TIMESTAMP_SEMANTICS
    ).upper()
    interval_value = metric.get("native_metric_interval_seconds", KRAKEN_ANALYTICS_INTERVAL_SECONDS)
    try:
        interval_seconds = int(interval_value)
    except (TypeError, ValueError):
        return "UNKNOWN", None, semantics
    if semantics not in {"BUCKET_START", "BUCKET_END"}:
        return "UNKNOWN", interval_seconds, semantics
    if native_timestamp is None or raw_start is None or raw_end is None:
        return "UNKNOWN", interval_seconds, semantics
    if int(raw_end) - int(raw_start) != interval_seconds * 1000:
        return "MISALIGNED", interval_seconds, semantics
    expected = int(raw_end) if semantics == "BUCKET_END" else int(raw_start)
    return ("ALIGNED" if native_timestamp == expected else "MISALIGNED"), interval_seconds, semantics


def _fail_closed(metric: dict[str, Any], reason: str) -> None:
    metric["availability_status"] = "UNAVAILABLE"
    metric["availability_reason"] = reason
    metric["latest"] = None
    metric["freshness_status"] = "UNAVAILABLE"


def gate_native_trade_metrics(metrics: dict[str, dict[str, Any]], evidence: dict[str, Any]) -> None:
    """Separate raw observation coverage from provider-native numerical validity."""
    feed_observed = bool(evidence.get("feed_observed"))
    coverage_complete = bool(evidence.get("coverage_complete"))
    raw_count = int(evidence.get("bucketed_trade_count") or 0)
    raw_start = evidence.get("bucket_start")
    raw_end = evidence.get("bucket_end")

    for metric_name in FLOW_METRICS:
        metric = metrics.get(metric_name)
        if not metric:
            continue
        native_latest = metric.get("latest")
        native_timestamp, native_value = _native_observation(metric)
        alignment, interval_seconds, timestamp_semantics = _temporal_alignment(
            metric, evidence, native_timestamp
        )
        metric["native_latest"] = native_latest
        metric["native_metric_timestamp"] = native_timestamp
        metric["native_metric_interval_seconds"] = interval_seconds
        metric["native_timestamp_semantics"] = timestamp_semantics
        metric["raw_bucket_start"] = raw_start
        metric["raw_bucket_end"] = raw_end
        metric["raw_bucketed_trade_count"] = raw_count
        metric["feed_observed"] = feed_observed
        metric["coverage_complete"] = coverage_complete
        metric["temporal_alignment_status"] = alignment
        metric["raw_coverage_status"] = (
            "UNOBSERVED" if not feed_observed else ("COMPLETE" if coverage_complete else "INCOMPLETE")
        )
        metric["raw_observed_value"] = None
        metric["native_observed_value"] = native_value
        metric["trade_flow_evidence"] = {
            "feed_observed": feed_observed,
            "coverage_complete": coverage_complete,
            "bucket_start": raw_start,
            "bucket_end": raw_end,
            "raw_trade_message_count": evidence.get("raw_trade_message_count"),
            "bucketed_trade_count": raw_count,
        }

        if metric_name == "trade-count":
            metric["metric_semantics_status"] = "QUALIFIED_DIRECT_EXECUTION_COUNT"
        elif metric_name == "trade-volume":
            metric["metric_semantics_status"] = "INSUFFICIENT_FOR_RAW_COMPARISON"
        elif metric_name == "aggressor-differential":
            metric["metric_semantics_status"] = "TAKER_SIDE_QUALIFIED_QUANTITY_UNIT_NOT_QUALIFIED"
        else:
            metric["metric_semantics_status"] = "PROVIDER_NATIVE_STATEFUL_DELTA_CONTRACT_NOT_QUALIFIED"

        if not feed_observed:
            metric["value_reconciliation_status"] = "UNAVAILABLE"
            _fail_closed(metric, "RAW_EXECUTION_FEED_NOT_OBSERVED")
            continue
        if not coverage_complete:
            metric["value_reconciliation_status"] = "UNAVAILABLE"
            _fail_closed(metric, "RAW_EXECUTION_COVERAGE_INCOMPLETE")
            continue
        if alignment != "ALIGNED":
            metric["value_reconciliation_status"] = "NOT_QUALIFIED"
            _fail_closed(metric, f"RAW_NATIVE_TEMPORAL_ALIGNMENT_{alignment}")
            continue

        if metric_name == "trade-count":
            metric["raw_observed_value"] = raw_count
            try:
                native_count_decimal = _decimal(native_value, "provider-native trade-count")
            except ValueError:
                metric["value_reconciliation_status"] = "NOT_QUALIFIED"
                _fail_closed(metric, "PROVIDER_NATIVE_TRADE_COUNT_NOT_INTEGER")
                continue
            if native_count_decimal < 0 or native_count_decimal != native_count_decimal.to_integral_value():
                metric["value_reconciliation_status"] = "NOT_QUALIFIED"
                _fail_closed(metric, "PROVIDER_NATIVE_TRADE_COUNT_NOT_INTEGER")
                continue
            native_count = int(native_count_decimal)
            metric["native_observed_value"] = native_count
            if raw_count != native_count:
                metric["value_reconciliation_status"] = "SOURCE_CONFLICT"
                _fail_closed(metric, "RAW_NATIVE_TRADE_COUNT_SOURCE_CONFLICT")
                continue
            metric["value_reconciliation_status"] = "MATCH"
            metric["availability_status"] = "AVAILABLE"
            metric["availability_reason"] = (
                "VALID_ZERO_NO_TRADES_IN_BUCKET"
                if raw_count == 0
                else "RAW_NATIVE_TRADE_COUNT_MATCH_SAME_BUCKET"
            )
            continue

        metric["value_reconciliation_status"] = "NOT_QUALIFIED"
        metric["availability_status"] = "NOT_QUALIFIED"
        if metric_name == "trade-volume":
            metric["availability_reason"] = "RAW_SIZE_TO_ANALYTICS_BASE_VOLUME_UNIT_NOT_QUALIFIED"
        elif metric_name == "aggressor-differential":
            metric["availability_reason"] = "AGGRESSOR_SIGN_QUALIFIED_RAW_SIZE_UNIT_NOT_QUALIFIED"
        else:
            metric["availability_reason"] = "PROVIDER_NATIVE_CVD_NOT_RAW_VALUE_VERIFIED"

def classify_root_cause(evidence: dict[str, Any], published_trade_count: Any = None) -> str:
    if not evidence.get("feed_observed") or (
        evidence.get("raw_trade_message_count") == 0 and not evidence.get("coverage_complete")
    ):
        return "A_ACQUISITION_OR_COVERAGE"
    if evidence.get("raw_trade_message_count", 0) > 0 and evidence.get("parsed_trade_count", 0) == 0:
        return "B_PARSER"
    if evidence.get("parsed_trade_count", 0) > 0 and evidence.get("product_matched_trade_count", 0) == 0:
        return "C_PRODUCT_FILTER"
    if evidence.get("coverage_complete") and evidence.get("bucketed_trade_count", 0) == 0:
        return "VALID_ZERO_NO_TRADES_IN_BUCKET"
    if evidence.get("product_matched_trade_count", 0) > 0 and evidence.get("timestamp_matched_trade_count", 0) == 0:
        return "D_TIME_WINDOW"
    if evidence.get("timestamp_matched_trade_count", 0) > 0 and evidence.get("bucketed_trade_count", 0) == 0:
        return "E_BUCKETIZATION_OR_INCOMPLETE_WINDOW"
    if evidence.get("bucketed_trade_count", 0) > 0 and published_trade_count in (0, "0", None):
        return "F_AGGREGATION_OR_MATERIALIZATION"
    if (
        evidence.get("bucketed_trade_count", 0) > 0
        and evidence.get("unknown_aggressor_count") == evidence.get("bucketed_trade_count")
    ):
        return "G_AGGRESSOR_CLASSIFICATION"
    return "NO_UPSTREAM_DEFECT_DETECTED"


def apply_trade_flow_evidence(
    intelligence: dict[str, Any], get: Callable[[str], dict[str, Any]], now_ms: int
) -> dict[str, Any]:
    """Attach bounded raw-execution evidence and rewrite current manifests fail-closed."""
    from pathlib import Path

    from archive import atomic_json

    derivatives = intelligence.get("derivatives") or {}
    provider = (derivatives.get("providers") or {}).get("kraken-futures") or {}
    instruments = provider.get("instruments") or {}
    analytics = intelligence.get("analytics") or {}
    analytics_kraken = (
        ((analytics.get("latest") or {}).get("kraken-futures") or {}).get("instruments") or {}
    )
    flow_pass = True
    for symbol, instrument in instruments.items():
        evidence = collect_trade_flow_evidence(get, now_ms, symbol)
        instrument["trade_flow"] = evidence
        metrics = instrument.get("metrics") or {}
        gate_native_trade_metrics(metrics, evidence)
        trade_count_metric = metrics.get("trade-count") or {}
        flow_pass = flow_pass and bool(
            evidence.get("feed_observed")
            and evidence.get("coverage_complete")
            and evidence.get("parser_error") is None
            and evidence.get("transport_error") is None
            and trade_count_metric.get("value_reconciliation_status") == "MATCH"
        )
        if symbol in analytics_kraken:
            for metric_name in FLOW_METRICS:
                if metric_name in metrics:
                    analytics_kraken[symbol][metric_name] = metrics[metric_name].get("latest")
            analytics_kraken[symbol]["trade_flow_evidence"] = evidence
        print(f"KRAKEN_TRADE_FLOW_{symbol}_RAW={evidence.get('raw_trade_message_count')}")
        print(f"KRAKEN_TRADE_FLOW_{symbol}_BUCKETED={evidence.get('bucketed_trade_count')}")
        print(
            f"KRAKEN_TRADE_FLOW_{symbol}_FEED_OBSERVED="
            f"{str(bool(evidence.get('feed_observed'))).lower()}"
        )
        print(
            f"KRAKEN_TRADE_FLOW_{symbol}_COVERAGE_COMPLETE="
            f"{str(bool(evidence.get('coverage_complete'))).lower()}"
        )
        print(f"KRAKEN_TRADE_FLOW_{symbol}_NATIVE_TRADE_COUNT_TIMESTAMP={trade_count_metric.get('native_metric_timestamp')}")
        print(f"KRAKEN_TRADE_FLOW_{symbol}_TEMPORAL_ALIGNMENT={trade_count_metric.get('temporal_alignment_status')}")
        print(f"KRAKEN_TRADE_FLOW_{symbol}_VALUE_RECONCILIATION={trade_count_metric.get('value_reconciliation_status')}")
    provider["trade_flow_status"] = "PASS" if flow_pass and instruments else "DEGRADED"
    atomic_json(Path("derivatives/manifest.json"), derivatives)
    atomic_json(Path("analytics/manifest.json"), analytics)
    return intelligence
