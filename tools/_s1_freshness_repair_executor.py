from __future__ import annotations

import re
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"REPLACE_COUNT_INVALID:{path}:{count}:{old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


runtime = "src/liquidity_s1_runtime.py"
tests = "tests/test_liquidity_s1_runtime.py"
validator = "tools/validation/validate_liquidity_s1_runtime.py"

replace_once(
    runtime,
    '''RESOURCE_SCHEMA = "liquidity-s1-qualified-resource/1.0.0"

BOOK_KINDS = {
''',
    '''RESOURCE_SCHEMA = "liquidity-s1-qualified-resource/1.0.0"
TEMPORAL_AUTHORITY_OWNER = "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1::tools/current_data_transport.py"
TEMPORAL_PROVENANCE_FIELDS = {
    "authority_owner",
    "evaluated_at_utc",
    "evaluation_time_ms",
    "observation_timestamp_ms",
    "derived_age_seconds",
}

BOOK_KINDS = {
''',
)
replace_once(
    runtime,
    '''    "observation_id",
    "observation_sha256",
    "age_seconds",
    "qualification_state",
''',
    '''    "observation_id",
    "observation_sha256",
    "temporal_provenance",
    "age_seconds",
    "freshness_verdict",
    "qualification_state",
''',
)
replace_once(
    runtime,
    '''def _nonnegative_int(value: Any, field: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{field}_INVALID")
    return int(value)


def _single_line_identity(value: Any, field: str) -> str:
''',
    '''def _nonnegative_int(value: Any, field: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{field}_INVALID")
    return int(value)


def _current_data_temporal_owner():
    try:
        import current_data_transport as temporal_owner
    except ImportError:
        try:
            from tools import current_data_transport as temporal_owner
        except ImportError as exc:
            raise LiquidityS1Error("TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    for name in ("_utc_now", "_format_utc", "_parse_utc"):
        _require(callable(getattr(temporal_owner, name, None)), "TEMPORAL_AUTHORITY_UNAVAILABLE")
    return temporal_owner


def _derive_temporal_provenance(
    normalized_book: Mapping[str, Any],
    *,
    evaluated_at_utc: str,
) -> dict[str, Any]:
    temporal_owner = _current_data_temporal_owner()
    try:
        parsed = temporal_owner._parse_utc(evaluated_at_utc, "liquidity_s1.evaluated_at_utc")
        canonical_utc = temporal_owner._format_utc(parsed)
    except Exception as exc:
        raise LiquidityS1Error("TEMPORAL_EVALUATION_TIME_INVALID") from exc
    _require(canonical_utc == evaluated_at_utc, "TEMPORAL_EVALUATION_TIME_NOT_CANONICAL")
    evaluation_time_ms = int(parsed.timestamp() * 1000)
    observation_timestamp_ms = _positive_int(
        normalized_book.get("timestamp_ms"),
        "OBSERVATION_TIMESTAMP_MS",
    )
    _require(evaluation_time_ms >= observation_timestamp_ms, "OBSERVATION_TIMESTAMP_IN_FUTURE")
    derived_age_seconds = (evaluation_time_ms - observation_timestamp_ms) // 1000
    return {
        "authority_owner": TEMPORAL_AUTHORITY_OWNER,
        "evaluated_at_utc": canonical_utc,
        "evaluation_time_ms": evaluation_time_ms,
        "observation_timestamp_ms": observation_timestamp_ms,
        "derived_age_seconds": derived_age_seconds,
    }


def _capture_temporal_provenance(normalized_book: Mapping[str, Any]) -> dict[str, Any]:
    temporal_owner = _current_data_temporal_owner()
    try:
        evaluated_at_utc = temporal_owner._format_utc(temporal_owner._utc_now())
    except Exception as exc:
        raise LiquidityS1Error("TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    return _derive_temporal_provenance(normalized_book, evaluated_at_utc=evaluated_at_utc)


def _validate_temporal_provenance(
    temporal_provenance: Mapping[str, Any],
    normalized_book: Mapping[str, Any],
) -> dict[str, Any]:
    _require(isinstance(temporal_provenance, Mapping), "TEMPORAL_PROVENANCE_REQUIRED")
    _require(set(temporal_provenance) == TEMPORAL_PROVENANCE_FIELDS, "TEMPORAL_PROVENANCE_FIELDS_INVALID")
    _require(
        temporal_provenance.get("authority_owner") == TEMPORAL_AUTHORITY_OWNER,
        "TEMPORAL_AUTHORITY_OWNER_INVALID",
    )
    evaluated_at_utc = temporal_provenance.get("evaluated_at_utc")
    _require(isinstance(evaluated_at_utc, str), "TEMPORAL_EVALUATION_TIME_INVALID")
    canonical = _derive_temporal_provenance(normalized_book, evaluated_at_utc=evaluated_at_utc)
    _require(dict(temporal_provenance) == canonical, "TEMPORAL_PROVENANCE_NOT_CANONICAL")
    return canonical


def _single_line_identity(value: Any, field: str) -> str:
''',
)
replace_once(
    runtime,
    '''def _evaluate_validated_resource(
    resource: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
''',
    '''def _evaluate_validated_resource(
    resource: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    evaluation_age_seconds: int,
) -> dict[str, Any]:
''',
)
replace_once(
    runtime,
    '''    age = int(resource["age_seconds"])
    if age > request["freshness"]["max_age_seconds"]:
''',
    '''    age = _nonnegative_int(evaluation_age_seconds, "EVALUATION_AGE_SECONDS")
    if age > request["freshness"]["max_age_seconds"]:
''',
)
replace_once(
    runtime,
    '''def _resource_material(
    *,
    request: Mapping[str, Any],
    book: Mapping[str, Any],
    age_seconds: int,
    quantity: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = compute_side_coverage(book, request)
    return {
''',
    '''def _resource_material(
    *,
    request: Mapping[str, Any],
    book: Mapping[str, Any],
    temporal_provenance: Mapping[str, Any],
    quantity: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = compute_side_coverage(book, request)
    temporal = _validate_temporal_provenance(temporal_provenance, book)
    age_seconds = temporal["derived_age_seconds"]
    freshness_verdict = "FRESH" if age_seconds <= request["freshness"]["max_age_seconds"] else "STALE"
    return {
''',
)
replace_once(
    runtime,
    '''        "observation_id": book["observation_id"],
        "observation_sha256": book["observation_sha256"],
        "age_seconds": age_seconds,
        "qualification_state": "QUALIFIED",
''',
    '''        "observation_id": book["observation_id"],
        "observation_sha256": book["observation_sha256"],
        "temporal_provenance": temporal,
        "age_seconds": age_seconds,
        "freshness_verdict": freshness_verdict,
        "qualification_state": "QUALIFIED",
''',
)
replace_once(
    runtime,
    '''    age_seconds: int,
    quantity_semantics: Mapping[str, Any],
) -> dict[str, Any]:
''',
    '''    age_seconds: int | None = None,
    quantity_semantics: Mapping[str, Any],
) -> dict[str, Any]:
''',
)
replace_once(
    runtime,
    '''    age = _nonnegative_int(age_seconds, "AGE_SECONDS")
    quantity = validate_quantity_semantics(quantity_semantics)
''',
    '''    temporal = _capture_temporal_provenance(book)
    if age_seconds is not None:
        caller_age = _nonnegative_int(age_seconds, "CALLER_AGE_SECONDS")
        _require(caller_age == temporal["derived_age_seconds"], "CALLER_AGE_SECONDS_MISMATCH")
    quantity = validate_quantity_semantics(quantity_semantics)
''',
)
replace_once(
    runtime,
    '''    resource = _resource_material(request=request, book=book, age_seconds=age, quantity=quantity)
    result = _evaluate_validated_resource(resource, request)
''',
    '''    resource = _resource_material(
        request=request,
        book=book,
        temporal_provenance=temporal,
        quantity=quantity,
    )
    result = _evaluate_validated_resource(
        resource,
        request,
        evaluation_age_seconds=resource["age_seconds"],
    )
''',
)
replace_once(
    runtime,
    '''    quantity = validate_quantity_semantics(quantity_raw)
    age = _nonnegative_int(resource.get("age_seconds"), "AGE_SECONDS")

    _require(resource.get("series_id") == request["series_id"], "RESOURCE_SERIES_ID_MISMATCH")
''',
    '''    quantity = validate_quantity_semantics(quantity_raw)
    temporal_raw = resource.get("temporal_provenance")
    _require(isinstance(temporal_raw, Mapping), "RESOURCE_TEMPORAL_PROVENANCE_MISSING")
    temporal = _validate_temporal_provenance(temporal_raw, book)
    age = temporal["derived_age_seconds"]
    _require(resource.get("age_seconds") == age, "RESOURCE_AGE_SECONDS_MISMATCH")

    _require(resource.get("series_id") == request["series_id"], "RESOURCE_SERIES_ID_MISMATCH")
''',
)
replace_once(
    runtime,
    '''    canonical = _resource_material(request=request, book=book, age_seconds=age, quantity=quantity)
    for field in (
''',
    '''    canonical = _resource_material(
        request=request,
        book=book,
        temporal_provenance=temporal,
        quantity=quantity,
    )
    _require(
        resource.get("freshness_verdict") == canonical["freshness_verdict"],
        "RESOURCE_FRESHNESS_VERDICT_MISMATCH",
    )
    for field in (
''',
)
replace_once(
    runtime,
    '''    own = _evaluate_validated_resource(canonical, request)
''',
    '''    own = _evaluate_validated_resource(
        canonical,
        request,
        evaluation_age_seconds=age,
    )
''',
)
replace_once(
    runtime,
    '''    except LiquidityS1Error as exc:
        return {
            "status": "NOT_QUALIFIED",
            "reusable": False,
            "reasons": [f"RESOURCE_REVALIDATION_FAILED:{exc}"],
        }
    return _evaluate_validated_resource(resource, request)


def validate_provider_capability_for_s1(
''',
    '''    except LiquidityS1Error as exc:
        return {
            "status": "NOT_QUALIFIED",
            "reusable": False,
            "reasons": [f"RESOURCE_REVALIDATION_FAILED:{exc}"],
        }
    try:
        current_temporal = _capture_temporal_provenance(resource["normalized_book"])
    except LiquidityS1Error as exc:
        return {
            "status": "NOT_QUALIFIED",
            "reusable": False,
            "reasons": [f"RESOURCE_CURRENT_FRESHNESS_FAILED:{exc}"],
        }
    return _evaluate_validated_resource(
        resource,
        request,
        evaluation_age_seconds=current_temporal["derived_age_seconds"],
    )


def validate_provider_capability_for_s1(
''',
)

replace_once(
    tests,
    '''import ast
import json
import math
import unittest
from pathlib import Path
''',
    '''import ast
import json
import math
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import current_data_transport
''',
)
replace_once(
    tests,
    '''ROOT = Path(__file__).resolve().parents[1]


def request(
''',
    '''ROOT = Path(__file__).resolve().parents[1]
TEST_EVALUATION_TIME_MS = 1_800_000_600_000
TEST_EVALUATION_TIME_UTC = "2027-01-15T08:10:00Z"


def _evaluation_datetime(timestamp_ms: int = TEST_EVALUATION_TIME_MS) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)


def request(
''',
)
replace_once(
    tests,
    '''    source_representation="RAW",
    oid="obs-1",
):
''',
    '''    source_representation="RAW",
    oid="obs-1",
    timestamp_ms=TEST_EVALUATION_TIME_MS,
):
''',
)
replace_once(
    tests,
    '''        "source_representation": source_representation,
        "timestamp_ms": 1_800_000_000_000,
''',
    '''        "source_representation": source_representation,
        "timestamp_ms": timestamp_ms,
''',
)
replace_once(
    tests,
    '''            book_kind=book_kind,
            source_representation="RAW",
        )
''',
    '''            book_kind=book_kind,
            source_representation="RAW",
            timestamp_ms=TEST_EVALUATION_TIME_MS - age * 1000,
        )
''',
)
replace_once(
    tests,
    '''class S1RuntimeTests(unittest.TestCase):
    def test_001_request_250_normalizes(self):
''',
    '''class S1RuntimeTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime())
        clock.start()
        self.addCleanup(clock.stop)

    def test_001_request_250_normalizes(self):
''',
)
replace_once(
    tests,
    '''    def test_099_resource_hash_is_not_decorative(self):
        r = legit_resource()
        stale = r["resource_sha256"]
        r["age_seconds"] = 1
        self.assertEqual(r["resource_sha256"], stale)
        with self.assertRaisesRegex(LiquidityS1Error, "RESOURCE_SHA256_MISMATCH"):
            validate_qualified_liquidity_resource(r)
''',
    '''    def test_099_resource_hash_is_not_decorative(self):
        r = legit_resource()
        stale = r["resource_sha256"]
        r["temporal_provenance"]["evaluated_at_utc"] = "2027-01-15T08:10:01Z"
        r["temporal_provenance"]["evaluation_time_ms"] = TEST_EVALUATION_TIME_MS + 1000
        r["temporal_provenance"]["derived_age_seconds"] = 1
        r["age_seconds"] = 1
        self.assertEqual(r["resource_sha256"], stale)
        with self.assertRaisesRegex(LiquidityS1Error, "RESOURCE_SHA256_MISMATCH"):
            validate_qualified_liquidity_resource(r)
''',
)
replace_once(
    tests,
    '''    def test_112_s1_s2_s3_runtime_boundary_unchanged(self):
        contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        self.assertTrue(contract["stage_boundaries"]["s1_source_implementation_performed"])
        self.assertFalse(contract["runtime_active"])
        self.assertFalse(contract["stage_boundaries"]["S2"]["active_in_this_contract_installation"])
        self.assertFalse(contract["stage_boundaries"]["S3"]["active_in_this_contract_installation"])


if __name__ == "__main__":
''',
    '''    def test_112_s1_s2_s3_runtime_boundary_unchanged(self):
        contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        self.assertTrue(contract["stage_boundaries"]["s1_source_implementation_performed"])
        self.assertFalse(contract["runtime_active"])
        self.assertFalse(contract["stage_boundaries"]["S2"]["active_in_this_contract_installation"])
        self.assertFalse(contract["stage_boundaries"]["S3"]["active_in_this_contract_installation"])

    def test_113_old_observation_forged_zero_age_is_rejected(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="old-zero-age"))
        with self.assertRaisesRegex(LiquidityS1Error, "CALLER_AGE_SECONDS_MISMATCH"):
            qualify_liquidity_resource(book, req, age_seconds=0, quantity_semantics=quantity())

    def test_114_old_observation_forged_small_age_is_rejected(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="old-small-age"))
        with self.assertRaisesRegex(LiquidityS1Error, "CALLER_AGE_SECONDS_MISMATCH"):
            qualify_liquidity_resource(book, req, age_seconds=1, quantity_semantics=quantity())

    def test_115_future_observation_timestamp_fails_closed(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=TEST_EVALUATION_TIME_MS + 1, oid="future"))
        with self.assertRaisesRegex(LiquidityS1Error, "OBSERVATION_TIMESTAMP_IN_FUTURE"):
            qualify_liquidity_resource(book, req, quantity_semantics=quantity())

    def test_116_missing_temporal_authority_fails_closed(self):
        book = normalize_order_book_observation(observation())
        with patch.object(current_data_transport, "_utc_now", side_effect=RuntimeError("clock unavailable")):
            with self.assertRaisesRegex(LiquidityS1Error, "TEMPORAL_AUTHORITY_UNAVAILABLE"):
                qualify_liquidity_resource(book, request(500), quantity_semantics=quantity())
        r = legit_resource()
        with patch.object(current_data_transport, "_utc_now", side_effect=RuntimeError("clock unavailable")):
            sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_117_malformed_temporal_authority_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["authority_owner"] = "caller"
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_118_negative_derived_age_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["derived_age_seconds"] = -1
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_119_stale_resource_remains_non_reusable(self):
        r = legit_resource(age=601)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=600))
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertIn("STALE", sat["reasons"])
        self.assertFalse(sat["reusable"])

    def test_120_exact_freshness_boundary_is_reusable(self):
        r = legit_resource(age=60)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "SATISFIED")
        self.assertTrue(sat["reusable"])

    def test_121_one_second_beyond_freshness_boundary_is_stale(self):
        r = legit_resource(age=61)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertIn("STALE", sat["reasons"])

    def test_122_tampered_observation_timestamp_with_stale_hash_fails(self):
        r = legit_resource()
        r["normalized_book"]["timestamp_ms"] -= 1000
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_123_tampered_derived_age_with_stale_hash_fails(self):
        r = legit_resource()
        r["age_seconds"] = 1
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_124_tampered_temporal_provenance_with_stale_hash_fails(self):
        r = legit_resource()
        r["temporal_provenance"]["evaluated_at_utc"] = "2027-01-15T08:10:01Z"
        r["temporal_provenance"]["evaluation_time_ms"] = TEST_EVALUATION_TIME_MS + 1000
        r["temporal_provenance"]["derived_age_seconds"] = 1
        r["age_seconds"] = 1
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertIn("RESOURCE_SHA256_MISMATCH", sat["reasons"][0])

    def test_125_canonical_resource_temporal_revalidation_idempotent(self):
        r = legit_resource(age=1)
        self.assertEqual(validate_qualified_liquidity_resource(r), r)
        self.assertEqual(validate_qualified_liquidity_resource(validate_qualified_liquidity_resource(r)), r)

    def test_126_legitimate_fresh_resource_remains_reusable(self):
        r = legit_resource(age=0)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "SATISFIED")
        self.assertTrue(sat["reusable"])

    def test_127_legitimate_stale_resource_remains_non_reusable(self):
        r = legit_resource(age=61)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertFalse(sat["reusable"])

    def test_128_planner_cannot_bypass_current_freshness_revalidation(self):
        req = request(500, max_age=60)
        old_timestamp = TEST_EVALUATION_TIME_MS - 3600 * 1000
        old_book = normalize_order_book_observation(observation(timestamp_ms=old_timestamp, oid="historically-fresh"))
        with patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime(old_timestamp)):
            historical = qualify_liquidity_resource(old_book, req, age_seconds=0, quantity_semantics=quantity())
        self.assertEqual(historical["request_satisfaction"], "SATISFIED")
        sat = evaluate_resource_satisfaction(historical, req)
        plan = plan_liquidity_acquisition(req, capability(), historical)
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertFalse(sat["reusable"])
        self.assertIn("STALE", sat["reasons"])
        self.assertEqual(plan["decision"], "ACQUISITION_REQUIRED")
        self.assertTrue(plan["network_required"])


if __name__ == "__main__":
''',
)

replace_once(
    validator,
    '''import ast
import json
import sys
from pathlib import Path
''',
    '''import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import current_data_transport
''',
)
replace_once(
    validator,
    '''    RESOURCE_SCHEMA,
    LiquidityS1Error,
''',
    '''    RESOURCE_SCHEMA,
    TEMPORAL_AUTHORITY_OWNER,
    LiquidityS1Error,
''',
)
replace_once(
    validator,
    '''    instrument: str = "ETHUSDT",
    book_kind: str = "L2_LEVEL_BOOK",
) -> dict:
''',
    '''    instrument: str = "ETHUSDT",
    book_kind: str = "L2_LEVEL_BOOK",
    timestamp_ms: int | None = None,
) -> dict:
''',
)
replace_once(
    validator,
    '''        "source_representation": "RAW",
        "timestamp_ms": 1_800_000_000_000,
''',
    '''        "source_representation": "RAW",
        "timestamp_ms": (
            int(current_data_transport._utc_now().replace(microsecond=0).timestamp() * 1000)
            if timestamp_ms is None
            else timestamp_ms
        ),
''',
)
vp = Path(validator)
vtext = vp.read_text(encoding="utf-8")
vtext = re.sub(r"^\s*age_seconds=0,\n", "", vtext, flags=re.MULTILINE)
vp.write_text(vtext, encoding="utf-8")
replace_once(
    validator,
    '''    require({"urllib", "requests", "http", "socket", "aiohttp"}.isdisjoint(imports), "NETWORK_IMPORT_FOUND")

    public = {
''',
    '''    require({"urllib", "requests", "http", "socket", "aiohttp"}.isdisjoint(imports), "NETWORK_IMPORT_FOUND")
    current_data_source = (ROOT / "tools/current_data_transport.py").read_text(encoding="utf-8")
    require("def _utc_now()" in current_data_source, "CURRENT_DATA_UTC_AUTHORITY_MISSING")
    require("def _format_utc(" in current_data_source, "CURRENT_DATA_TIME_FORMATTER_MISSING")
    require("def _parse_utc(" in current_data_source, "CURRENT_DATA_TIME_PARSER_MISSING")
    require("def evaluate_persisted_freshness" in current_data_source, "CURRENT_DATA_FRESHNESS_MODEL_MISSING")
    require(
        TEMPORAL_AUTHORITY_OWNER == "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1::tools/current_data_transport.py",
        "TEMPORAL_AUTHORITY_OWNER_DRIFT",
    )

    public = {
''',
)
replace_once(
    validator,
    '''    for mutate in ("coverage", "quantity", "observation", "hash"):
        tampered = json.loads(json.dumps(valid))
        if mutate == "coverage":
            tampered["achieved_bid_coverage_bps"] = "999"
        elif mutate == "quantity":
            tampered["quantity_semantics"]["native_quantity"] = "999"
        elif mutate == "observation":
            tampered["observation_id"] = "forged"
        else:
            tampered["resource_sha256"] = "0" * 64
        result = evaluate_resource_satisfaction(tampered, request(250))
        require(
            result["status"] == "NOT_QUALIFIED" and not result["reusable"],
            f"RESOURCE_{mutate.upper()}_TAMPER",
        )

    truncated = resource("97", "103.1")
''',
    '''    for mutate in ("coverage", "quantity", "observation", "hash"):
        tampered = json.loads(json.dumps(valid))
        if mutate == "coverage":
            tampered["achieved_bid_coverage_bps"] = "999"
        elif mutate == "quantity":
            tampered["quantity_semantics"]["native_quantity"] = "999"
        elif mutate == "observation":
            tampered["observation_id"] = "forged"
        else:
            tampered["resource_sha256"] = "0" * 64
        result = evaluate_resource_satisfaction(tampered, request(250))
        require(
            result["status"] == "NOT_QUALIFIED" and not result["reusable"],
            f"RESOURCE_{mutate.upper()}_TAMPER",
        )

    freshness_req = request()
    freshness_req["freshness"] = {"max_age_seconds": 60}
    old_book = normalize_order_book_observation(observation(timestamp_ms=1))
    expect_error(
        lambda: qualify_liquidity_resource(old_book, freshness_req, age_seconds=0, quantity_semantics=quantity()),
        "CALLER_AGE_SECONDS_MISMATCH",
        "FORGED_ZERO_AGE",
    )
    old_resource = qualify_liquidity_resource(old_book, freshness_req, quantity_semantics=quantity())
    require(old_resource["age_seconds"] > 60, "OLD_BOOK_DERIVED_AGE_INVALID")
    require(old_resource["freshness_verdict"] == "STALE", "OLD_BOOK_FRESHNESS_VERDICT")
    require(old_resource["request_satisfaction"] == "UNSATISFIED", "OLD_BOOK_RESOURCE_SATISFIED")
    old_sat = evaluate_resource_satisfaction(old_resource, freshness_req)
    old_plan = plan_liquidity_acquisition(freshness_req, capability(), old_resource)
    require(old_sat["status"] == "UNSATISFIED" and not old_sat["reusable"], "FORGED_FRESHNESS_SATISFIED")
    require(old_plan["decision"] == "ACQUISITION_REQUIRED" and old_plan["network_required"], "FORGED_FRESHNESS_REUSED")

    now_ms = int(current_data_transport._utc_now().replace(microsecond=0).timestamp() * 1000)
    future_book = normalize_order_book_observation(observation(timestamp_ms=now_ms + 1000))
    expect_error(
        lambda: qualify_liquidity_resource(future_book, freshness_req, quantity_semantics=quantity()),
        "OBSERVATION_TIMESTAMP_IN_FUTURE",
        "FUTURE_TIMESTAMP",
    )

    real_clock = current_data_transport._utc_now
    try:
        current_data_transport._utc_now = lambda: (_ for _ in ()).throw(RuntimeError("clock unavailable"))
        expect_error(
            lambda: qualify_liquidity_resource(complete, freshness_req, quantity_semantics=quantity()),
            "TEMPORAL_AUTHORITY_UNAVAILABLE",
            "MISSING_TEMPORAL_AUTHORITY",
        )
    finally:
        current_data_transport._utc_now = real_clock

    malformed_temporal = json.loads(json.dumps(valid))
    malformed_temporal["temporal_provenance"]["authority_owner"] = "caller"
    malformed_result = evaluate_resource_satisfaction(malformed_temporal, request(250))
    require(malformed_result["status"] == "NOT_QUALIFIED" and not malformed_result["reusable"], "MALFORMED_TEMPORAL_AUTHORITY")

    negative_age = json.loads(json.dumps(valid))
    negative_age["temporal_provenance"]["derived_age_seconds"] = -1
    negative_result = evaluate_resource_satisfaction(negative_age, request(250))
    require(negative_result["status"] == "NOT_QUALIFIED" and not negative_result["reusable"], "NEGATIVE_DERIVED_AGE")

    stale_hash_temporal = json.loads(json.dumps(valid))
    base_ms = stale_hash_temporal["temporal_provenance"]["evaluation_time_ms"]
    stale_hash_temporal["temporal_provenance"]["evaluated_at_utc"] = datetime.fromtimestamp(
        (base_ms + 1000) / 1000, timezone.utc
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    stale_hash_temporal["temporal_provenance"]["evaluation_time_ms"] = base_ms + 1000
    stale_hash_temporal["temporal_provenance"]["derived_age_seconds"] += 1
    stale_hash_temporal["age_seconds"] += 1
    stale_hash_result = evaluate_resource_satisfaction(stale_hash_temporal, request(250))
    require(stale_hash_result["status"] == "NOT_QUALIFIED" and not stale_hash_result["reusable"], "TEMPORAL_HASH_TAMPER")
    require("RESOURCE_SHA256_MISMATCH" in stale_hash_result["reasons"][0], "TEMPORAL_HASH_TAMPER_NOT_HASH_BOUND")

    historical_timestamp = now_ms - 3600 * 1000
    historical_book = normalize_order_book_observation(observation(timestamp_ms=historical_timestamp))
    real_clock = current_data_transport._utc_now
    try:
        current_data_transport._utc_now = lambda: datetime.fromtimestamp(historical_timestamp / 1000, timezone.utc)
        historical_fresh = qualify_liquidity_resource(historical_book, freshness_req, age_seconds=0, quantity_semantics=quantity())
    finally:
        current_data_transport._utc_now = real_clock
    reevaluated = evaluate_resource_satisfaction(historical_fresh, freshness_req)
    reevaluated_plan = plan_liquidity_acquisition(freshness_req, capability(), historical_fresh)
    require(reevaluated["status"] == "UNSATISFIED" and "STALE" in reevaluated["reasons"], "CURRENT_DERIVED_AGE_NOT_REVALIDATED")
    require(reevaluated_plan["decision"] == "ACQUISITION_REQUIRED" and reevaluated_plan["network_required"], "PLANNER_FRESHNESS_REVALIDATION_BYPASS")

    truncated = resource("97", "103.1")
''',
)
replace_once(
    validator,
    '''        ["normalize_liquidity_request", "semantic_request", "full revalidation"],
        ["evaluate_resource_satisfaction", "existing_resource", "qualified-resource full revalidation"],
        ["plan_liquidity_acquisition", "provider_capability", "S1 rejects caller-qualified depth; S2 owns qualification"],
''',
    '''        ["normalize_liquidity_request", "semantic_request", "full revalidation"],
        ["evaluate_resource_satisfaction", "existing_resource", "qualified-resource full revalidation + current-data temporal re-evaluation"],
        ["freshness_temporal_provenance", "physical observation timestamp + current-data UTC authority", "derived age only; caller age is consistency assertion"],
        ["plan_liquidity_acquisition", "provider_capability", "S1 rejects caller-qualified depth; S2 owns qualification"],
''',
)
replace_once(validator, '''    require(len(audit) == 13, "AUDIT_TABLE_INCOMPLETE")
''', '''    require(len(audit) == 14, "AUDIT_TABLE_INCOMPLETE")
''')
replace_once(
    validator,
    '''        "PLAN_SERIALIZER_REVALIDATION=PASS",
        "RESOURCE_SATISFACTION_ENGINE=PASS",
''',
    '''        "PLAN_SERIALIZER_REVALIDATION=PASS",
        "PRE_REPAIR_FORGED_FRESHNESS_CAN_REUSE=YES",
        "PRE_REPAIR_REPRODUCTION_AUTHORITY=RUN_558",
        "POST_REPAIR_FORGED_FRESHNESS_CAN_REUSE=NO",
        "FRESHNESS_PROVENANCE_AUTHORITY=PASS",
        "FORGED_FRESHNESS_CANNOT_CREATE_REUSE=PASS",
        "FUTURE_TIMESTAMP_FAIL_CLOSED=PASS",
        "MISSING_TEMPORAL_AUTHORITY_FAIL_CLOSED=PASS",
        "DERIVED_AGE_REVALIDATION=PASS",
        "FRESHNESS_HASH_TAMPER_REJECTED=PASS",
        "CALLER_SUPPLIED_FRESHNESS_CLAIM_IS_NOT_AUTHORITY=PASS",
        "TEMPORAL_AUTHORITY_OWNER=ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1::tools/current_data_transport.py",
        "CURRENT_DATA_TEMPORAL_MODEL_REUSED=PASS",
        "OBSERVATION_TIMESTAMP_NE_EVALUATION_TIME=PASS",
        "DERIVED_AGE_NE_FRESHNESS_THRESHOLD=PASS",
        "FRESHNESS_THRESHOLD_NE_FRESHNESS_VERDICT=PASS",
        "RESOURCE_SATISFACTION_ENGINE=PASS",
''',
)

print("PATCH_EXECUTOR=PASS")
