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
        # Public history is request-scoped by symbol; the response schema does not
        # require symbol on every execution row.
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
    page_lengths: list[int] = []

    try:
        for _ in range(max_pages):
            url = f"{KRAKEN_FUTURES_HISTORY_BASE}?symbol={quote(requested_product_id)}"
            if cursor is not None:
                url += f"&lastTime={quote(cursor)}"
            response = get(url)
            diagnostics["pages"] += 1
            if response.get("result") != "success":
                raise ValueError(f"Kraken trade history failed: {response.get('error') or response.get('errors')}")
            diagnostics["feed_observed"] = True
            if response.get("serverTime"):
                server_time_ms = _iso_to_ms(response["serverTime"])
            history = response.get("history")
            if not isinstance(history, list):
                raise ValueError("Kraken trade history missing history list")
            page_lengths.append(len(history))
            diagnostics["raw_trade_message_count"] += len(history)
            for raw in history:
                try:
                    trade = normalize_trade(raw, requested_product_id)
                except Exception:
                    drops["PARSER_ERROR"] += 1
                    raise
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
            if not history:
                break
            oldest_raw = min(history, key=lambda x: _iso_to_ms(x["time"]))
            oldest_ts = _iso_to_ms(oldest_raw["time"])
            oldest_seen = oldest_ts if oldest_seen is None else min(oldest_seen, oldest_ts)
            if oldest_ts <= bucket_start:
                break
            if len(history) < 100:
                break
            next_cursor = str(oldest_raw["time"])
            if next_cursor == cursor:
                raise ValueError("Kraken trade history pagination stalled")
            cursor = next_cursor
    except Exception as exc:
        diagnostics["transport_error"] = None if diagnostics["feed_observed"] else f"{type(exc).__name__}: {exc}"
        diagnostics["parser_error"] = f"{type(exc).__name__}: {exc}" if diagnostics["feed_observed"] else None
        diagnostics["drop_reason_counts"] = dict(sorted(drops.items()))
        diagnostics["observed_product_ids"] = sorted(observed_ids)
        return diagnostics

    diagnostics["observed_product_ids"] = sorted(observed_ids)
    diagnostics["drop_reason_counts"] = dict(sorted(drops.items()))
    server_covers_end = server_time_ms is not None and server_time_ms >= bucket_end
    history_covers_start = (
        diagnostics["raw_trade_message_count"] == 0
        or (oldest_seen is not None and oldest_seen <= bucket_start)
        or (page_lengths and page_lengths[-1] < 100)
    )
    diagnostics["coverage_complete"] = bool(diagnostics["feed_observed"] and server_covers_end and history_covers_start)

    matched = [trade for trade in parsed if trade["product_match"]]
    timestamp_matched = [trade for trade in matched if trade["timestamp_ms"] < bucket_end]
    bucketed = [trade for trade in timestamp_matched if trade["timestamp_ms"] >= bucket_start]
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
    diagnostics.update({
        "native_quantity_sum": str(native_sum) if diagnostics["coverage_complete"] else None,
        "buy_aggressor_count": len(buys),
        "sell_aggressor_count": len(sells),
        "unknown_aggressor_count": len(unknown),
        "buy_volume": str(buy_volume) if diagnostics["coverage_complete"] else None,
        "sell_volume": str(sell_volume) if diagnostics["coverage_complete"] else None,
        "signed_volume": str(buy_volume - sell_volume) if diagnostics["coverage_complete"] and not unknown else None,
    })
    return diagnostics


def gate_native_trade_metrics(metrics: dict[str, dict[str, Any]], evidence: dict[str, Any]) -> None:
    """Fail closed current native flow metrics unless raw execution coverage is proven."""
    available = bool(evidence.get("feed_observed") and evidence.get("coverage_complete"))
    for metric_name in FLOW_METRICS:
        metric = metrics.get(metric_name)
        if not metric:
            continue
        native_latest = metric.get("latest")
        metric["native_latest"] = native_latest
        metric["trade_flow_evidence"] = {
            "feed_observed": bool(evidence.get("feed_observed")),
            "coverage_complete": bool(evidence.get("coverage_complete")),
            "bucket_start": evidence.get("bucket_start"),
            "bucket_end": evidence.get("bucket_end"),
            "raw_trade_message_count": evidence.get("raw_trade_message_count"),
            "bucketed_trade_count": evidence.get("bucketed_trade_count"),
        }
        if available:
            metric["availability_status"] = "AVAILABLE"
            metric["availability_reason"] = "RAW_EXECUTION_COVERAGE_PROVEN"
        else:
            metric["availability_status"] = "UNAVAILABLE"
            metric["availability_reason"] = "RAW_EXECUTION_FEED_NOT_OBSERVED" if not evidence.get("feed_observed") else "RAW_EXECUTION_COVERAGE_INCOMPLETE"
            metric["latest"] = None
            metric["freshness_status"] = "UNAVAILABLE"


def classify_root_cause(evidence: dict[str, Any], published_trade_count: Any = None) -> str:
    if not evidence.get("feed_observed") or evidence.get("raw_trade_message_count") == 0 and not evidence.get("coverage_complete"):
        return "A_ACQUISITION_OR_COVERAGE"
    if evidence.get("raw_trade_message_count", 0) > 0 and evidence.get("parsed_trade_count", 0) == 0:
        return "B_PARSER"
    if evidence.get("parsed_trade_count", 0) > 0 and evidence.get("product_matched_trade_count", 0) == 0:
        return "C_PRODUCT_FILTER"
    if evidence.get("product_matched_trade_count", 0) > 0 and evidence.get("timestamp_matched_trade_count", 0) == 0:
        return "D_TIME_WINDOW"
    if evidence.get("timestamp_matched_trade_count", 0) > 0 and evidence.get("bucketed_trade_count", 0) == 0:
        return "E_BUCKETIZATION"
    if evidence.get("bucketed_trade_count", 0) > 0 and published_trade_count in (0, "0", None):
        return "F_AGGREGATION_OR_MATERIALIZATION"
    if evidence.get("bucketed_trade_count", 0) > 0 and evidence.get("unknown_aggressor_count") == evidence.get("bucketed_trade_count"):
        return "G_AGGRESSOR_CLASSIFICATION"
    return "NO_UPSTREAM_DEFECT_DETECTED"


def apply_trade_flow_evidence(intelligence: dict[str, Any], get: Callable[[str], dict[str, Any]], now_ms: int) -> dict[str, Any]:
    """Attach bounded raw-execution evidence and rewrite current manifests fail-closed."""
    from archive import atomic_json

    derivatives = intelligence.get("derivatives") or {}
    provider = (derivatives.get("providers") or {}).get("kraken-futures") or {}
    instruments = provider.get("instruments") or {}
    analytics = intelligence.get("analytics") or {}
    analytics_kraken = (((analytics.get("latest") or {}).get("kraken-futures") or {}).get("instruments") or {})
    for symbol, instrument in instruments.items():
        evidence = collect_trade_flow_evidence(get, now_ms, symbol)
        instrument["trade_flow"] = evidence
        metrics = instrument.get("metrics") or {}
        gate_native_trade_metrics(metrics, evidence)
        if symbol in analytics_kraken:
            for metric_name in FLOW_METRICS:
                if metric_name in metrics:
                    analytics_kraken[symbol][metric_name] = metrics[metric_name].get("latest")
            analytics_kraken[symbol]["trade_flow_evidence"] = evidence
    atomic_json(__import__("pathlib").Path("derivatives/manifest.json"), derivatives)
    atomic_json(__import__("pathlib").Path("analytics/manifest.json"), analytics)
    return intelligence
