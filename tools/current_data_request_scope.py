from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.current_data_transport import (
    CurrentDataTransportError,
    VALIDATION_SCHEMA,
    REQUEST_SATISFACTION_SCHEMA,
    _load_json,
    _load_request_wrapper,
    _write_json,
)
from canonical_json import sha256_canonical_json
from tools.capability_index import describe_requestable_capability
from liquidity_s1_runtime import (
    evaluate_resource_satisfaction,
    normalize_liquidity_request,
    normalize_order_book_observation,
    plan_liquidity_acquisition,
    qualify_liquidity_resource,
    qualify_quantity_semantics,
    validate_qualified_liquidity_resource,
)
from liquidity_s2_binance_adapter import build_binance_provider_plan
from liquidity_s2_kraken_spot_adapter import build_kraken_spot_provider_plan
from liquidity_s2_kraken_futures_adapter import build_kraken_futures_provider_plan
from liquidity_s3_executor import execute_s3

FLOW_METRICS = ("trade-count", "trade-volume", "aggressor-differential", "cvd")
RELEVANCE_GLOBAL = "GLOBAL_STRUCTURAL"
RELEVANCE_RESOURCE = "REQUESTED_RESOURCE"
RELEVANCE_DOMAIN = "REQUESTED_DOMAIN"
RELEVANCE_UNREQUESTED = "UNREQUESTED_RESOURCE"
FRESHNESS_LIVE_MAX_SECONDS = 600
FRESHNESS_RECENT_MAX_SECONDS = 1800


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise CurrentDataTransportError(code, message)


def _age(metric: Mapping[str, Any]) -> int | None:
    value = metric.get("data_age_seconds")
    if value is None:
        return None
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
             "KRAKEN_METRIC_AGE_INVALID", "Kraken metric data_age_seconds must be a non-negative integer")
    return int(value)


def _validate_freshness_envelope(metric: Mapping[str, Any], *, allow_unavailable: bool) -> None:
    freshness = metric.get("freshness_status")
    age = _age(metric)
    latest = metric.get("latest")
    if freshness == "LIVE_USABLE":
        _require(age is not None and age <= FRESHNESS_LIVE_MAX_SECONDS,
                 "KRAKEN_LIVE_FRESHNESS_CONTRADICTION",
                 "LIVE_USABLE Kraken metric exceeds the current freshness bound")
    elif freshness == "RECENT_CONTEXT":
        _require(age is not None and FRESHNESS_LIVE_MAX_SECONDS < age <= FRESHNESS_RECENT_MAX_SECONDS,
                 "KRAKEN_RECENT_FRESHNESS_CONTRADICTION",
                 "RECENT_CONTEXT Kraken metric has an impossible age")
    elif freshness == "STALE_FOR_CURRENT":
        _require(age is not None and age > FRESHNESS_RECENT_MAX_SECONDS,
                 "KRAKEN_STALE_FRESHNESS_CONTRADICTION",
                 "STALE_FOR_CURRENT Kraken metric has an impossible age")
    elif freshness == "UNAVAILABLE" and allow_unavailable:
        _require(latest is None, "KRAKEN_UNAVAILABLE_VALUE_PRESENT",
                 "UNAVAILABLE Kraken metric cannot expose ordinary latest value")
    else:
        raise CurrentDataTransportError(
            "KRAKEN_FRESHNESS_STATUS_INVALID",
            f"unsupported Kraken freshness_status={freshness!r}",
        )


def validate_flow_metric_envelope(
    metric_name: str,
    metric: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate PR #283 current metric envelope without requiring every metric to be qualified."""
    _require(metric_name in FLOW_METRICS, "FLOW_METRIC_UNKNOWN", f"unsupported flow metric: {metric_name}")
    _require(metric.get("more") is False, "KRAKEN_MORE_INCOMPLETE", f"{metric_name} pagination is incomplete")

    availability = str(metric.get("availability_status") or "UNKNOWN")
    reason = metric.get("availability_reason")
    reconciliation = str(metric.get("value_reconciliation_status") or "UNKNOWN")
    alignment = str(metric.get("temporal_alignment_status") or "UNKNOWN")
    semantics = str(metric.get("metric_semantics_status") or "UNKNOWN")
    consumer_qualified = projection.get("consumer_qualified")
    projected_value = projection.get("value")

    _require(isinstance(reason, str) and bool(reason),
             "FLOW_AVAILABILITY_REASON_MISSING", f"{metric_name} availability_reason is required")
    _require(projection.get("availability_status") == availability,
             "FLOW_PROJECTION_AVAILABILITY_MISMATCH", f"{metric_name} projection loses availability status")
    _require(projection.get("value_reconciliation_status") == reconciliation,
             "FLOW_PROJECTION_RECONCILIATION_MISMATCH", f"{metric_name} projection loses reconciliation status")
    _require(projection.get("temporal_alignment_status") == alignment,
             "FLOW_PROJECTION_ALIGNMENT_MISMATCH", f"{metric_name} projection loses alignment status")
    _require(projection.get("metric_semantics_status") == semantics,
             "FLOW_PROJECTION_SEMANTICS_MISMATCH", f"{metric_name} projection loses semantic status")
    _require(projection.get("availability_reason") == reason,
             "FLOW_PROJECTION_REASON_MISMATCH", f"{metric_name} projection loses availability reason")

    if availability == "AVAILABLE":
        _require(metric_name == "trade-count",
                 "FLOW_AVAILABLE_UNQUALIFIED_METRIC", f"{metric_name} cannot be consumer-qualified by current contract")
        _require(reconciliation == "MATCH" and alignment == "ALIGNED",
                 "FLOW_AVAILABLE_WITHOUT_MATCH", "available trade-count requires MATCH + ALIGNED")
        _require(semantics == "QUALIFIED_DIRECT_EXECUTION_COUNT",
                 "FLOW_AVAILABLE_SEMANTICS_INVALID", "available trade-count requires qualified execution-count semantics")
        _require(metric.get("feed_observed") is True and metric.get("coverage_complete") is True,
                 "FLOW_AVAILABLE_WITHOUT_COVERAGE", "available trade-count requires observed complete raw coverage")
        _validate_freshness_envelope(metric, allow_unavailable=False)
        _require(consumer_qualified is True,
                 "FLOW_AVAILABLE_PROJECTION_NOT_QUALIFIED", "available trade-count must remain consumer-qualified")
        _require(projected_value == metric.get("latest") and projected_value is not None,
                 "FLOW_AVAILABLE_VALUE_MISMATCH", "qualified flow projection must expose exact qualified value")
        if reason == "VALID_ZERO_NO_TRADES_IN_BUCKET":
            latest = metric.get("latest")
            _require(
                isinstance(latest, (list, tuple)) and len(latest) >= 2 and latest[1] == 0
                and metric.get("raw_observed_value") == 0
                and metric.get("native_observed_value") == 0,
                "VALID_ZERO_PROJECTION_INVALID",
                "valid-zero trade-count must preserve numeric zero across qualified observations",
            )
        return {"metric_qualification_status": "PASS", "consumer_qualified": True}

    _require(availability in {"UNAVAILABLE", "NOT_QUALIFIED", "UNKNOWN"},
             "FLOW_AVAILABILITY_STATUS_INVALID", f"unsupported fail-closed availability={availability}")
    _require(consumer_qualified is False,
             "FLOW_FAIL_CLOSED_CONSUMER_QUALIFIED", f"{metric_name} fail-closed state cannot be consumer-qualified")
    _require(projected_value is None,
             "FLOW_FAIL_CLOSED_PUBLIC_VALUE_PRESENT", f"{metric_name} fail-closed state cannot expose consumer value")

    if reconciliation == "SOURCE_CONFLICT":
        _require(availability == "UNAVAILABLE",
                 "SOURCE_CONFLICT_AVAILABILITY_INVALID", "SOURCE_CONFLICT must fail closed as UNAVAILABLE")
        _require(metric.get("latest") is None and metric.get("freshness_status") == "UNAVAILABLE",
                 "SOURCE_CONFLICT_VALUE_EXPOSED", "SOURCE_CONFLICT must clear ordinary latest/current value")
        _require(isinstance(metric.get("native_latest"), (list, tuple)),
                 "SOURCE_CONFLICT_NATIVE_EVIDENCE_MISSING", "SOURCE_CONFLICT must preserve provider-native evidence")
    elif reconciliation == "NOT_QUALIFIED":
        _require(availability in {"NOT_QUALIFIED", "UNAVAILABLE"},
                 "NOT_QUALIFIED_AVAILABILITY_INVALID", "NOT_QUALIFIED must not claim AVAILABLE")
        if availability == "NOT_QUALIFIED":
            _require(metric.get("native_latest") is not None,
                     "NOT_QUALIFIED_NATIVE_EVIDENCE_MISSING",
                     "NOT_QUALIFIED current metric must preserve explicit provider-native evidence")
            _validate_freshness_envelope(metric, allow_unavailable=False)
        else:
            _validate_freshness_envelope(metric, allow_unavailable=True)
    elif reconciliation == "UNAVAILABLE":
        _require(availability == "UNAVAILABLE",
                 "UNAVAILABLE_RECONCILIATION_INVALID", "UNAVAILABLE reconciliation must fail closed")
        _validate_freshness_envelope(metric, allow_unavailable=True)
    elif reconciliation == "UNKNOWN":
        _require(availability == "UNKNOWN",
                 "UNKNOWN_RECONCILIATION_INVALID", "UNKNOWN reconciliation must remain explicitly UNKNOWN")
        _require(metric.get("latest") is None,
                 "UNKNOWN_VALUE_EXPOSED", "UNKNOWN qualification cannot expose ordinary latest value")
    else:
        raise CurrentDataTransportError(
            "FLOW_RECONCILIATION_STATUS_INVALID",
            f"unsupported {metric_name} reconciliation={reconciliation!r}",
        )
    return {"metric_qualification_status": "DEGRADED", "consumer_qualified": False}


def validate_kraken_generation_integrity(
    provider: Mapping[str, Any],
    analytics_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Global generation-integrity check: honest fail-closed states are valid generations."""
    _require(provider.get("status") == "PASS",
             "KRAKEN_COLLECTION_STATUS_INVALID", "Kraken Futures collection status must be PASS")
    instruments = provider.get("instruments")
    _require(isinstance(instruments, Mapping) and bool(instruments),
             "KRAKEN_INSTRUMENTS_INVALID", "Kraken Futures instruments missing")

    latest = analytics_manifest.get("latest")
    _require(isinstance(latest, Mapping), "ANALYTICS_LATEST_INVALID", "analytics latest section missing")
    analytics_kraken = latest.get("kraken-futures")
    _require(isinstance(analytics_kraken, Mapping), "ANALYTICS_KRAKEN_INVALID", "Kraken analytics projection missing")
    analytics_instruments = analytics_kraken.get("instruments")
    _require(isinstance(analytics_instruments, Mapping),
             "ANALYTICS_KRAKEN_INSTRUMENTS_INVALID", "Kraken analytics instruments missing")

    degraded: list[dict[str, str]] = []
    qualified_count = 0
    metric_count = 0

    for instrument_id, instrument in instruments.items():
        _require(isinstance(instrument, Mapping), "KRAKEN_INSTRUMENT_INVALID", f"invalid instrument {instrument_id}")
        metrics = instrument.get("metrics")
        _require(isinstance(metrics, Mapping) and bool(metrics),
                 "KRAKEN_METRICS_INVALID", f"metrics missing for {instrument_id}")
        analytics_instrument = analytics_instruments.get(instrument_id)
        _require(isinstance(analytics_instrument, Mapping),
                 "ANALYTICS_INSTRUMENT_INVALID", f"analytics projection missing for {instrument_id}")
        validity = analytics_instrument.get("flow_metric_validity")
        _require(isinstance(validity, Mapping),
                 "FLOW_VALIDITY_PROJECTION_MISSING", f"flow validity missing for {instrument_id}")

        for metric_name, metric in metrics.items():
            metric_count += 1
            _require(isinstance(metric, Mapping),
                     "KRAKEN_METRIC_INVALID", f"invalid metric {instrument_id}/{metric_name}")
            _require(metric.get("more") is False,
                     "KRAKEN_MORE_INCOMPLETE", f"Kraken pagination incomplete for {instrument_id}/{metric_name}")

            if metric_name in FLOW_METRICS:
                projection = validity.get(metric_name)
                _require(isinstance(projection, Mapping),
                         "FLOW_VALIDITY_PROJECTION_MISSING",
                         f"flow validity missing for {instrument_id}/{metric_name}")
                result = validate_flow_metric_envelope(metric_name, metric, projection)
                if result["consumer_qualified"]:
                    qualified_count += 1
                else:
                    degraded.append({
                        "resource_id": f"derivatives.kraken-futures.{instrument_id}.{metric_name}",
                        "availability_status": str(metric.get("availability_status") or "UNKNOWN"),
                        "value_reconciliation_status": str(metric.get("value_reconciliation_status") or "UNKNOWN"),
                    })
                continue

            _validate_freshness_envelope(metric, allow_unavailable=False)
            if metric.get("freshness_status") == "LIVE_USABLE":
                qualified_count += 1
            else:
                degraded.append({
                    "resource_id": f"derivatives.kraken-futures.{instrument_id}.{metric_name}",
                    "availability_status": str(metric.get("freshness_status")),
                    "value_reconciliation_status": "NOT_APPLICABLE",
                })

    return {
        "generation_integrity_status": "PASS",
        "collection_status": "PASS",
        "metric_qualification_status": "PASS" if not degraded else "DEGRADED",
        "metric_count": metric_count,
        "consumer_qualified_metric_count": qualified_count,
        "degraded_resources": degraded,
    }


def _parse_kraken_series(series_id: str) -> tuple[str, str] | None:
    prefix = "derivatives.kraken-futures."
    if not series_id.startswith(prefix):
        return None
    rest = series_id[len(prefix):]
    if "." not in rest:
        return None
    instrument, metric = rest.split(".", 1)
    return instrument, metric


def _current_kraken_requirement(
    series_id: str,
    derivatives_manifest: Mapping[str, Any],
    analytics_manifest: Mapping[str, Any],
) -> dict[str, Any] | None:
    parsed = _parse_kraken_series(series_id)
    if parsed is None:
        return None
    instrument_id, metric_name = parsed
    provider = ((derivatives_manifest.get("providers") or {}).get("kraken-futures") or {})
    instrument = ((provider.get("instruments") or {}).get(instrument_id) or {})
    metric = ((instrument.get("metrics") or {}).get(metric_name) or {})
    _require(isinstance(metric, Mapping) and bool(metric),
             "REQUESTED_CURRENT_METRIC_MISSING", f"current Kraken metric missing: {series_id}")

    if metric_name in FLOW_METRICS:
        analytics_instrument = (
            (((analytics_manifest.get("latest") or {}).get("kraken-futures") or {}).get("instruments") or {})
            .get(instrument_id) or {}
        )
        projection = ((analytics_instrument.get("flow_metric_validity") or {}).get(metric_name) or {})
        _require(isinstance(projection, Mapping) and bool(projection),
                 "REQUESTED_FLOW_VALIDITY_MISSING", f"flow validity missing: {series_id}")
        validate_flow_metric_envelope(metric_name, metric, projection)
        return {
            "resource_id": series_id,
            "satisfied": projection.get("consumer_qualified") is True,
            "availability_status": str(projection.get("availability_status") or "UNKNOWN"),
            "value_reconciliation_status": str(projection.get("value_reconciliation_status") or "UNKNOWN"),
            "consumer_qualified": projection.get("consumer_qualified") is True,
        }

    freshness = str(metric.get("freshness_status") or "UNKNOWN")
    _validate_freshness_envelope(metric, allow_unavailable=False)
    return {
        "resource_id": series_id,
        "satisfied": freshness == "LIVE_USABLE",
        "availability_status": "AVAILABLE" if freshness == "LIVE_USABLE" else "UNAVAILABLE",
        "value_reconciliation_status": "NOT_APPLICABLE",
        "consumer_qualified": freshness == "LIVE_USABLE",
    }


def evaluate_request_satisfaction(
    request: Mapping[str, Any],
    resource_index: Mapping[str, Any],
    *,
    derivatives_manifest: Mapping[str, Any],
    analytics_manifest: Mapping[str, Any],
    global_integrity: Mapping[str, Any],
) -> dict[str, Any]:
    _require(global_integrity.get("generation_integrity_status") == "PASS",
             "GLOBAL_GENERATION_INTEGRITY_REQUIRED",
             "request satisfaction cannot run before global generation integrity PASS")

    domain_rows = resource_index.get("domains")
    series_rows = resource_index.get("series")
    _require(isinstance(domain_rows, list) and isinstance(series_rows, list),
             "RESOURCE_INDEX_INVALID", "resource index rows missing")

    domains = {row.get("domain_id"): row for row in domain_rows if isinstance(row, Mapping)}
    series = {row.get("series_id"): row for row in series_rows if isinstance(row, Mapping)}
    failures: list[dict[str, Any]] = []

    for domain in request.get("required_domains", []):
        row = domains.get(domain)
        satisfied = bool(
            isinstance(row, Mapping)
            and row.get("status") == "PASS"
            and row.get("freshness") == "FRESH"
        )
        if not satisfied:
            failures.append({
                "relevance": RELEVANCE_DOMAIN,
                "resource_id": f"current-domain:{str(domain).lower()}",
                "reason": "REQUIRED_DOMAIN_UNSATISFIED",
            })

    required_current: dict[str, dict[str, Any]] = {}
    for item in request.get("required_series", []):
        series_id = str(item["series_id"])
        bars = int(item["latest_bars"])
        row = series.get(series_id)
        base_ok = bool(
            isinstance(row, Mapping)
            and row.get("status") == "PASS"
            and row.get("availability") == "AVAILABLE"
            and row.get("finality") == "FINALIZED"
            and row.get("rows") == bars
            and row.get("expected_rows") == bars
            and row.get("gap_count") == 0
            and row.get("duplicates") == 0
        )
        current = _current_kraken_requirement(series_id, derivatives_manifest, analytics_manifest)
        if current is not None:
            required_current[series_id] = current
            base_ok = base_ok and bool(current["satisfied"])
        if not base_ok:
            failures.append({
                "relevance": RELEVANCE_RESOURCE,
                "resource_id": series_id,
                "reason": "REQUIRED_RESOURCE_UNSATISFIED",
                "current_qualification": current,
            })

    required_ids = {str(item["series_id"]) for item in request.get("required_series", [])}
    unrequested = [
        {**row, "relevance": RELEVANCE_UNREQUESTED}
        for row in global_integrity.get("degraded_resources", [])
        if isinstance(row, Mapping) and row.get("resource_id") not in required_ids
    ]

    unsatisfied_resources = sum(1 for row in failures if row["relevance"] == RELEVANCE_RESOURCE)
    unsatisfied_domains = sum(1 for row in failures if row["relevance"] == RELEVANCE_DOMAIN)
    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "generation_integrity_status": "PASS",
        "request_satisfaction_status": status,
        "collection_status": str(global_integrity.get("collection_status") or "UNKNOWN"),
        "metric_qualification_status": str(global_integrity.get("metric_qualification_status") or "UNKNOWN"),
        "failure_relevance_model": [
            RELEVANCE_GLOBAL, RELEVANCE_RESOURCE, RELEVANCE_DOMAIN, RELEVANCE_UNREQUESTED
        ],
        "failures": failures,
        "requested_current_qualification": required_current,
        "unrequested_degraded_resources": unrequested,
        "unsatisfied_required_resource_count": unsatisfied_resources,
        "unsatisfied_required_domain_count": unsatisfied_domains,
        "unrequested_degraded_resource_count": len(unrequested),
        "request_aware_network_acquisition_implemented": False,
        "broad_physical_acquisition_implies_broad_qualification": False,
    }


def resource_family_sha256(semantic_request: Mapping[str,Any]) -> str:
    request=normalize_liquidity_request(semantic_request)
    return sha256_canonical_json({
        "book_kind":request["book_kind"],
        "instrument_id":request["instrument_id"],
        "provider_id":request["provider_id"],
        "semantic_resource_id":request["series_id"],
    })

def _s1_provider_capability(capability: Mapping[str,Any]) -> dict[str,Any]:
    provider=str(capability["provider_id"])
    return {
        "provider_id":provider,
        "book_kind":capability["book_kind"],
        "raw_book_capability":"AVAILABLE_EXTERNALLY" if provider=="kraken-spot" else "CONFIRMED",
        "selectable_depth_limit":"NOT_NORMATIVELY_DOCUMENTED" if provider=="kraken-futures" else "NOT_QUALIFIED",
        "qualified_provider_depth_parameter":None,
    }

def _build_s2_plan(provider_id: str, s1_plan: Mapping[str,Any]) -> dict[str,Any]:
    if provider_id in {"binance-spot","binance-usdm"}:
        return build_binance_provider_plan(
            s1_plan,
            request_weight_budget=250 if provider_id=="binance-spot" else 20,
            max_raw_resource_bytes=8*1024*1024,
        )
    if provider_id=="kraken-spot":
        return build_kraken_spot_provider_plan(s1_plan,max_raw_resource_bytes=8*1024*1024)
    if provider_id=="kraken-futures":
        return build_kraken_futures_provider_plan(s1_plan,max_raw_resource_bytes=8*1024*1024)
    raise CurrentDataTransportError("REQUESTABLE_PROVIDER_UNSUPPORTED",provider_id)

def _legacy_snapshot_candidate(
    semantic_request: Mapping[str,Any],
    *,
    legacy_snapshots: Sequence[Mapping[str,Any]]|None=None,
) -> dict[str,Any]|None:
    request=normalize_liquidity_request(semantic_request)
    if request["provider_id"]!="binance-spot":
        return None
    snapshots=legacy_snapshots
    if snapshots is None:
        manifest=_load_json(ROOT/"liquidity"/"manifest.json")
        collection=manifest.get("collection") if isinstance(manifest,Mapping) else None
        snapshots=collection.get("snapshots") if isinstance(collection,Mapping) else None
    if not isinstance(snapshots,Sequence) or isinstance(snapshots,(str,bytes)):
        return None
    matches=[
        row for row in snapshots
        if isinstance(row,Mapping)
        and row.get("provider")==request["provider_id"]
        and row.get("instrument")==request["instrument_id"]
        and isinstance(row.get("timestamp_ms"),int)
        and isinstance(row.get("raw"),Mapping)
    ]
    if not matches:
        return None
    snapshot=max(matches,key=lambda row:int(row["timestamp_ms"]))
    raw=snapshot["raw"]
    bids=raw.get("bids"); asks=raw.get("asks")
    if not isinstance(bids,list) or not isinstance(asks,list) or not bids or not asks:
        return None
    identity_material={
        "source_family":"liquidity.orderbook-snapshots",
        "provider_id":request["provider_id"],
        "instrument_id":request["instrument_id"],
        "timestamp_ms":int(snapshot["timestamp_ms"]),
        "bids":bids,"asks":asks,
    }
    observation={
        "observation_id":"legacy:"+sha256_canonical_json(identity_material),
        "provider_id":request["provider_id"],
        "instrument_id":request["instrument_id"],
        "book_kind":request["book_kind"],
        "source_representation":"RAW",
        "timestamp_ms":int(snapshot["timestamp_ms"]),
        "bids":bids,"asks":asks,
    }
    try:
        book=normalize_order_book_observation(observation)
        total=sum((Decimal(str(level[1])) for side in (book["bids"],book["asks"]) for level in side),Decimal("0"))
        quantity=qualify_quantity_semantics(
            provider_id=request["provider_id"],instrument_id=request["instrument_id"],
            book_kind=request["book_kind"],native_quantity=format(total,"f"),
            native_quantity_unit=str(snapshot.get("native_amount_unit") or "BASE_ASSET"),
        )
        return validate_qualified_liquidity_resource(
            qualify_liquidity_resource(book,request,quantity_semantics=quantity)
        )
    except Exception:
        return None

def _write_self_hashed(path: Path, value: dict[str,Any], hash_field: str) -> str:
    material=dict(value)
    digest=sha256_canonical_json(material)
    material[hash_field]=digest
    _write_json(path,material)
    return digest

def _resource_artifacts(
    output_root: Path,
    resource: Mapping[str,Any],
    *,
    s1_planner_result: Mapping[str,Any]|None,
    s2_provider_plan: Mapping[str,Any]|None,
) -> tuple[str,str,str,str]:
    canonical=validate_qualified_liquidity_resource(resource)
    resource_sha=canonical["resource_sha256"]
    root=output_root/"liquidity"/"resources"/resource_sha
    resource_member=(root/"qualified-resource.json").relative_to(output_root).as_posix()
    _write_json(root/"qualified-resource.json",canonical)
    qualification={
        "schema_version":"liquidity-current-qualification-receipt/1.0.0",
        "resource_sha256":resource_sha,
        "qualification_request_sha256":sha256_canonical_json(canonical["qualification_request"]),
        "observation_id":canonical["observation_id"],
        "observation_sha256":canonical["observation_sha256"],
        "s1_planner_result":dict(s1_planner_result) if isinstance(s1_planner_result,Mapping) else None,
        "s2_provider_plan":dict(s2_provider_plan) if isinstance(s2_provider_plan,Mapping) else None,
    }
    qmember=(root/"qualification-receipt.json").relative_to(output_root).as_posix()
    qsha=_write_self_hashed(root/"qualification-receipt.json",qualification,"qualification_receipt_sha256")
    return resource_member,qmember,qsha,qualification["qualification_request_sha256"]

def _request_binding(
    output_root: Path,
    request: Mapping[str,Any],
    *,
    resource_sha256: str|None,
    satisfaction: Mapping[str,Any],
    acquisition_mode: str,
) -> tuple[str,str]:
    current_sha=sha256_canonical_json(request)
    status=str(satisfaction["status"])
    reasons=sorted(str(value) for value in satisfaction.get("reasons",[]))
    sat_sha=sha256_canonical_json({
        "current_semantic_request_sha256":current_sha,
        "resource_sha256":resource_sha256,
        "status":status,
        "reasons":reasons,
    })
    value={
        "schema_version":"liquidity-current-request-binding/1.0.0",
        "semantic_request":dict(request),
        "current_semantic_request_sha256":current_sha,
        "resource_sha256":resource_sha256,
        "request_satisfaction_status":status,
        "request_satisfaction_reasons":reasons,
        "request_satisfaction_sha256":sat_sha,
        "acquisition_mode":acquisition_mode,
    }
    path=output_root/"liquidity"/"bindings"/current_sha/"request-binding.json"
    _write_self_hashed(path,value,"request_binding_sha256")
    return path.relative_to(output_root).as_posix(),sat_sha

def _execution_receipt_artifact(output_root: Path, receipt: Mapping[str,Any]) -> tuple[str,str]:
    digest=str(receipt["execution_receipt_sha256"])
    path=output_root/"liquidity"/"executions"/digest/"execution-receipt.json"
    _write_json(path,dict(receipt))
    return digest,path.relative_to(output_root).as_posix()

def _candidate_sort(resource: Mapping[str,Any]) -> tuple[int,str]:
    canonical=validate_qualified_liquidity_resource(resource)
    return (-int(canonical["normalized_book"]["timestamp_ms"]),str(canonical["resource_sha256"]))

def _process_exact_liquidity(
    request: Mapping[str,Any],
    *,
    output_root: Path,
    s3_transport: Any|None=None,
    legacy_snapshots: Sequence[Mapping[str,Any]]|None=None,
) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    required=[normalize_liquidity_request(item) for item in request.get("required_liquidity",[])]
    # Dominance-first execution order; wire normalization order remains deterministic separately.
    ordered=sorted(required,key=lambda item:(
        str(item["series_id"]),
        -max(Decimal(str(item["requested_bid_coverage_bps"])),Decimal(str(item["requested_ask_coverage_bps"]))),
        0 if item["representation"]=="RAW" else 1,
        sha256_canonical_json(item),
    ))
    registry: dict[str,list[dict[str,Any]]]={}
    origin: dict[str,dict[str,Any]]={}
    rows=[]; failures=[]
    for current in ordered:
        current_sha=sha256_canonical_json(current)
        try:
            capability=describe_requestable_capability(str(current["series_id"]))
        except Exception as exc:
            raise CurrentDataTransportError("UNKNOWN_REQUESTABLE_CAPABILITY",str(current["series_id"])) from exc
        if (
            capability["provider_id"]!=current["provider_id"]
            or capability["instrument_id"]!=current["instrument_id"]
            or capability["book_kind"]!=current["book_kind"]
            or current["representation"] not in capability["supported_representations"]
        ):
            raise CurrentDataTransportError("REQUEST_CAPABILITY_IDENTITY_MISMATCH",str(current["series_id"]))
        family=resource_family_sha256(current)
        candidates=list(registry.get(family,[]))
        legacy=_legacy_snapshot_candidate(current,legacy_snapshots=legacy_snapshots)
        if legacy is not None:
            candidates.append(legacy)
        satisfying=[]
        for candidate in candidates:
            try:
                candidate=validate_qualified_liquidity_resource(candidate)
            except Exception:
                continue
            sat=evaluate_resource_satisfaction(candidate,current)
            if sat["status"]=="SATISFIED" and sat["reusable"] is True:
                satisfying.append(candidate)
        selected=sorted(satisfying,key=_candidate_sort)[0] if satisfying else None
        receipt_sha=None; receipt_member=None; s1_plan=None; s2_plan=None
        if selected is not None:
            selected_sha=selected["resource_sha256"]
            if selected_sha in origin:
                mode="SAME_EXECUTION_REUSE"
                meta=origin[selected_sha]
                resource_member=meta["resource_member"]; qmember=meta["qualification_member"]
                qsha=meta["qualification_sha"]; qualification_request_sha=meta["qualification_request_sha"]
            else:
                mode="LEGACY_PERSISTED_REQUALIFICATION"
                resource_member,qmember,qsha,qualification_request_sha=_resource_artifacts(
                    output_root,selected,s1_planner_result=None,s2_provider_plan=None
                )
                registry.setdefault(family,[]).append(selected)
                origin[selected_sha]={
                    "resource_member":resource_member,"qualification_member":qmember,
                    "qualification_sha":qsha,"qualification_request_sha":qualification_request_sha,
                }
            satisfaction=evaluate_resource_satisfaction(selected,current)
            resource=selected
        else:
            provider_cap=_s1_provider_capability(capability)
            s1_plan=plan_liquidity_acquisition(current,provider_cap)
            if s1_plan["decision"]!="ACQUISITION_REQUIRED" or s1_plan["network_required"] is not True:
                raise CurrentDataTransportError("S1_ACQUISITION_PLAN_INVALID","S1 did not produce exact acquisition requirement")
            s2_plan=_build_s2_plan(str(current["provider_id"]),s1_plan)
            execution=execute_s3(
                current,s1_plan,s2_plan,transport=s3_transport,execution_plane="GITHUB_ACTIONS"
            )
            receipt_sha,receipt_member=_execution_receipt_artifact(output_root,execution["receipt"])
            mode="S3_NETWORK_ACQUIRED"
            resource=execution.get("qualified_resource")
            if isinstance(resource,Mapping):
                resource=validate_qualified_liquidity_resource(resource)
                resource_member,qmember,qsha,qualification_request_sha=_resource_artifacts(
                    output_root,resource,s1_planner_result=s1_plan,s2_provider_plan=s2_plan
                )
                registry.setdefault(family,[]).append(resource)
                origin[resource["resource_sha256"]]={
                    "resource_member":resource_member,"qualification_member":qmember,
                    "qualification_sha":qsha,"qualification_request_sha":qualification_request_sha,
                }
                satisfaction=evaluate_resource_satisfaction(resource,current)
            else:
                resource_member=qmember=qsha=qualification_request_sha=None
                satisfaction={"status":"UNSATISFIED","reusable":False,"reasons":[execution["receipt"]["terminal_status"]]}
        resource_sha=resource.get("resource_sha256") if isinstance(resource,Mapping) else None
        binding_member,sat_sha=_request_binding(
            output_root,current,resource_sha256=resource_sha,satisfaction=satisfaction,acquisition_mode=mode
        )
        row={
            "semantic_resource_id":current["series_id"],"provider_id":current["provider_id"],
            "instrument_id":current["instrument_id"],"book_kind":current["book_kind"],
            "representation":current["representation"],"resource_family_sha256":family,
            "resource_sha256":resource_sha,"resource_qualification_request_sha256":qualification_request_sha,
            "current_semantic_request_sha256":current_sha,"qualification_receipt_sha256":qsha,
            "request_satisfaction_status":satisfaction["status"],"request_satisfaction_sha256":sat_sha,
            "request_satisfied":satisfaction["status"]=="SATISFIED",
            "observation_id":resource.get("observation_id") if isinstance(resource,Mapping) else None,
            "observation_sha256":resource.get("observation_sha256") if isinstance(resource,Mapping) else None,
            "acquisition_mode":mode,"durability_class":"EPHEMERAL_ONLY","cross_run_cache_eligible":False,
            "automatic_promotion":False,"automatic_history_append":False,"automatic_research_publication":False,
            "resource_artifact_member":resource_member,"qualification_receipt_member":qmember,
            "request_binding_member":binding_member,"s3_execution_receipt_sha256":receipt_sha,
            "s3_execution_receipt_member":receipt_member,
        }
        rows.append(row)
        if row["request_satisfied"] is not True:
            failures.append({
                "relevance":RELEVANCE_RESOURCE,"resource_id":current["series_id"],
                "reason":"REQUIRED_EXACT_LIQUIDITY_UNSATISFIED",
                "current_semantic_request_sha256":current_sha,
                "satisfaction_reasons":sorted(str(x) for x in satisfaction.get("reasons",[])),
            })
    rows.sort(key=lambda row:(str(row["semantic_resource_id"]),str(row["current_semantic_request_sha256"])))
    return rows,failures


def qualify_request(
    request: Mapping[str, Any],
    request_sha256: str,
    resource_index: Mapping[str, Any],
    *,
    output_root: Path,
    derivatives_manifest: Mapping[str, Any] | None = None,
    analytics_manifest: Mapping[str, Any] | None = None,
    s3_transport: Any | None = None,
    legacy_snapshots: Sequence[Mapping[str,Any]] | None = None,
) -> dict[str, Any]:
    ordinary_required=bool(request.get("required_series") or request.get("required_domains"))
    if ordinary_required:
        derivatives_manifest = derivatives_manifest or _load_json(ROOT / "derivatives" / "manifest.json")
        analytics_manifest = analytics_manifest or _load_json(ROOT / "analytics" / "manifest.json")
        _require(isinstance(derivatives_manifest, Mapping) and isinstance(analytics_manifest, Mapping),
                 "CURRENT_MANIFEST_INVALID", "current derivatives/analytics manifests must be objects")
        provider = ((derivatives_manifest.get("providers") or {}).get("kraken-futures") or {})
        _require(isinstance(provider, Mapping), "KRAKEN_PROVIDER_INVALID", "Kraken provider payload missing")
        global_integrity = validate_kraken_generation_integrity(provider, analytics_manifest)
        result = evaluate_request_satisfaction(
            request, resource_index, derivatives_manifest=derivatives_manifest,
            analytics_manifest=analytics_manifest, global_integrity=global_integrity,
        )
    else:
        global_integrity={
            "generation_integrity_status":"PASS","collection_status":"NOT_APPLICABLE_EXACT_ONLY",
            "metric_qualification_status":"NOT_APPLICABLE","degraded_resources":[],
        }
        result={
            "status":"PASS","generation_integrity_status":"PASS","request_satisfaction_status":"PASS",
            "collection_status":"NOT_APPLICABLE_EXACT_ONLY","metric_qualification_status":"NOT_APPLICABLE",
            "failure_relevance_model":[RELEVANCE_GLOBAL,RELEVANCE_RESOURCE,RELEVANCE_DOMAIN,RELEVANCE_UNREQUESTED],
            "failures":[],"requested_current_qualification":{},"unrequested_degraded_resources":[],
            "unsatisfied_required_resource_count":0,"unsatisfied_required_domain_count":0,
            "unrequested_degraded_resource_count":0,"request_aware_network_acquisition_implemented":True,
            "broad_physical_acquisition_implies_broad_qualification":False,
        }
    liquidity_rows,liquidity_failures=_process_exact_liquidity(
        request,output_root=output_root,s3_transport=s3_transport,legacy_snapshots=legacy_snapshots
    )
    if liquidity_failures:
        result["failures"].extend(liquidity_failures)
        result["unsatisfied_required_resource_count"] += len(liquidity_failures)
        result["status"]="FAIL"; result["request_satisfaction_status"]="FAIL"
    result["request_aware_network_acquisition_implemented"]=True
    result["exact_liquidity_results"]=[{
        "semantic_resource_id":row["semantic_resource_id"],
        "current_semantic_request_sha256":row["current_semantic_request_sha256"],
        "request_satisfaction_status":row["request_satisfaction_status"],
        "resource_sha256":row["resource_sha256"],
        "acquisition_mode":row["acquisition_mode"],
        "s3_execution_receipt_sha256":row["s3_execution_receipt_sha256"],
    } for row in liquidity_rows]
    result["request_sha256"]=request_sha256
    result["schema_version"]=REQUEST_SATISFACTION_SCHEMA
    _write_json(output_root/"request-satisfaction.json",result)
    enriched=dict(resource_index)
    enriched["liquidity_resources"]=liquidity_rows
    enriched["request_qualification"]={
        "request_satisfaction_status":result["request_satisfaction_status"],
        "failure_relevance_model":result["failure_relevance_model"],
        "requested_current_qualification":result["requested_current_qualification"],
        "exact_liquidity_results":result["exact_liquidity_results"],
        "unrequested_degraded_resources":result["unrequested_degraded_resources"],
        "unsatisfied_required_resource_count":result["unsatisfied_required_resource_count"],
        "unsatisfied_required_domain_count":result["unsatisfied_required_domain_count"],
        "unrequested_degraded_resource_count":result["unrequested_degraded_resource_count"],
    }
    _write_json(output_root/"resource-index.json",enriched)
    summary={
        "schema_version":VALIDATION_SCHEMA,"contract_id":"ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
        "contract_version":"1.1.0","status":result["status"],"generation_integrity_status":"PASS",
        "request_satisfaction_status":result["request_satisfaction_status"],"collection_status":result["collection_status"],
        "metric_qualification_status":result["metric_qualification_status"],"failure_relevance_model":result["failure_relevance_model"],
        "unsatisfied_required_resource_count":result["unsatisfied_required_resource_count"],
        "unsatisfied_required_domain_count":result["unsatisfied_required_domain_count"],
        "unrequested_degraded_resource_count":result["unrequested_degraded_resource_count"],
        "request_aware_network_acquisition_implemented":True,"existing_collector_reused":True,
        "direct_provider_call_by_agent":False,"generation_integrity_vs_request_satisfaction_separated":True,
        "exact_liquidity_outer_generation_freshness_is_authority":False,
        "s1_exact_liquidity_freshness_is_authority":True,
        "cross_run_s3_exact_resource_reuse":False,"normal_test_network_required":False,
    }
    _write_json(output_root/"validation-summary.json",summary)
    return result

def _append_output(path: Path | None, name: str, value: object) -> None:
    if path is None:
        return
    text = str(value)
    if "\n" in text or "\r" in text:
        raise CurrentDataTransportError("UNSAFE_GITHUB_OUTPUT", f"unsafe multiline output: {name}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={text}\n")


def _command_qualify(args: argparse.Namespace) -> int:
    request, request_sha = _load_request_wrapper(Path(args.request))
    output_root = Path(args.output_root)
    index = _load_json(output_root / "resource-index.json")
    if not isinstance(index, Mapping):
        raise CurrentDataTransportError("RESOURCE_INDEX_INVALID", "resource index must be an object")
    result = qualify_request(request, request_sha, index, output_root=output_root)
    github_output = Path(args.github_output) if args.github_output else None
    _append_output(github_output, "request_satisfaction_status", result["request_satisfaction_status"])
    _append_output(github_output, "unsatisfied_required_resource_count", result["unsatisfied_required_resource_count"])
    _append_output(github_output, "unsatisfied_required_domain_count", result["unsatisfied_required_domain_count"])
    _append_output(github_output, "unrequested_degraded_resource_count", result["unrequested_degraded_resource_count"])
    _append_output(github_output, "required_liquidity_count", len(request.get("required_liquidity", [])))
    print(f"CURRENT_DATA_REQUEST_SATISFACTION={result['request_satisfaction_status']}")
    print(f"UNSATISFIED_REQUIRED_RESOURCE_COUNT={result['unsatisfied_required_resource_count']}")
    print(f"UNSATISFIED_REQUIRED_DOMAIN_COUNT={result['unsatisfied_required_domain_count']}")
    print(f"UNREQUESTED_DEGRADED_RESOURCE_COUNT={result['unrequested_degraded_resource_count']}")
    if result["status"] != "PASS":
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Request-scoped Fresh Current qualification")
    sub = parser.add_subparsers(dest="command", required=True)
    qualify = sub.add_parser("qualify-request")
    qualify.add_argument("--request", required=True)
    qualify.add_argument("--output-root", required=True)
    qualify.add_argument("--github-output")
    qualify.set_defaults(func=_command_qualify)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CurrentDataTransportError as exc:
        print(f"CURRENT_DATA_REQUEST_SCOPE={exc.code} error={exc}", file=sys.stderr)
        raise SystemExit(2)
