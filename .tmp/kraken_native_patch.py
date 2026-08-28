from pathlib import Path

path=Path('src/kraken_trade_flow.py')
text=path.read_text()
start=text.index('def gate_native_trade_metrics(')
end=text.index('\ndef classify_root_cause(', start)
replacement='''KRAKEN_ANALYTICS_INTERVAL_SECONDS = 300
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
'''
text=text[:start]+replacement+text[end:]
old='''        flow_pass = flow_pass and bool(\n            evidence.get("feed_observed")\n            and evidence.get("coverage_complete")\n            and evidence.get("parser_error") is None\n            and evidence.get("transport_error") is None\n        )\n        metrics = instrument.get("metrics") or {}\n        gate_native_trade_metrics(metrics, evidence)\n'''
new='''        metrics = instrument.get("metrics") or {}\n        gate_native_trade_metrics(metrics, evidence)\n        trade_count_metric = metrics.get("trade-count") or {}\n        flow_pass = flow_pass and bool(\n            evidence.get("feed_observed")\n            and evidence.get("coverage_complete")\n            and evidence.get("parser_error") is None\n            and evidence.get("transport_error") is None\n            and trade_count_metric.get("value_reconciliation_status") == "MATCH"\n        )\n'''
if old not in text:
    raise SystemExit('apply flow_pass anchor not found')
text=text.replace(old,new,1)
anchor='''        print(\n            f"KRAKEN_TRADE_FLOW_{symbol}_COVERAGE_COMPLETE="\n            f"{str(bool(evidence.get('coverage_complete'))).lower()}"\n        )\n'''
extra=anchor+'''        print(f"KRAKEN_TRADE_FLOW_{symbol}_NATIVE_TRADE_COUNT_TIMESTAMP={trade_count_metric.get('native_metric_timestamp')}")\n        print(f"KRAKEN_TRADE_FLOW_{symbol}_TEMPORAL_ALIGNMENT={trade_count_metric.get('temporal_alignment_status')}")\n        print(f"KRAKEN_TRADE_FLOW_{symbol}_VALUE_RECONCILIATION={trade_count_metric.get('value_reconciliation_status')}")\n'''
if anchor not in text:
    raise SystemExit('diagnostic anchor not found')
text=text.replace(anchor,extra,1)
path.write_text(text)

tests=Path('tests/test_kraken_trade_flow.py')
t=tests.read_text()
marker='\n\nif __name__ == "__main__":\n'
if marker not in t:
    raise SystemExit('test marker not found')
additions='''
    def test_14_nonzero_raw_vs_zero_native_is_source_conflict(self):
        evidence = collect_trade_flow_evidence(
            getter([trade(1_000, trade_id=1), trade(-1_000, trade_id=2)]), NOW, "PI_ETHUSD"
        )
        metrics = {"trade-count": {"latest": [END, 0], "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["trade-count"]
        self.assertEqual(metric["temporal_alignment_status"], "ALIGNED")
        self.assertEqual(metric["value_reconciliation_status"], "SOURCE_CONFLICT")
        self.assertNotEqual(metric["availability_status"], "AVAILABLE")
        self.assertIsNone(metric["latest"])
        self.assertEqual(metric["native_latest"], [END, 0])
        self.assertEqual(metric["raw_observed_value"], 1)

    def test_15_same_bucket_empty_raw_and_native_zero_is_match(self):
        evidence = collect_trade_flow_evidence(getter([trade(-1_000, trade_id=9)]), NOW, "PI_ETHUSD")
        metrics = {"trade-count": {"latest": [END, 0], "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["trade-count"]
        self.assertEqual(metric["value_reconciliation_status"], "MATCH")
        self.assertEqual(metric["availability_status"], "AVAILABLE")
        self.assertEqual(metric["availability_reason"], "VALID_ZERO_NO_TRADES_IN_BUCKET")
        self.assertEqual(metric["latest"], [END, 0])

    def test_16_previous_bucket_native_timestamp_is_misaligned(self):
        evidence = collect_trade_flow_evidence(getter([trade(-1_000, trade_id=9)]), NOW, "PI_ETHUSD")
        metrics = {"trade-count": {"latest": [START, 0], "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["trade-count"]
        self.assertEqual(metric["native_timestamp_semantics"], "BUCKET_END")
        self.assertEqual(metric["temporal_alignment_status"], "MISALIGNED")
        self.assertEqual(metric["value_reconciliation_status"], "NOT_QUALIFIED")
        self.assertIsNone(metric["latest"])

    def test_17_unknown_native_timestamp_semantics_fails_closed(self):
        evidence = collect_trade_flow_evidence(getter([trade(-1_000, trade_id=9)]), NOW, "PI_ETHUSD")
        metrics = {"trade-count": {"latest": [END, 0], "native_timestamp_semantics": "UNKNOWN"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["trade-count"]
        self.assertEqual(metric["temporal_alignment_status"], "UNKNOWN")
        self.assertEqual(metric["value_reconciliation_status"], "NOT_QUALIFIED")
        self.assertNotEqual(metric["availability_status"], "AVAILABLE")
        self.assertIsNone(metric["latest"])

    def test_18_nonzero_same_bucket_trade_count_match_is_available(self):
        evidence = collect_trade_flow_evidence(
            getter([trade(1_000, trade_id=1), trade(2_000, trade_id=2), trade(-1_000, trade_id=3)]),
            NOW,
            "PI_ETHUSD",
        )
        metrics = {"trade-count": {"latest": [END, 2], "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["trade-count"]
        self.assertEqual(metric["raw_observed_value"], 2)
        self.assertEqual(metric["native_observed_value"], 2)
        self.assertEqual(metric["value_reconciliation_status"], "MATCH")
        self.assertEqual(metric["availability_status"], "AVAILABLE")

    def test_19_trade_volume_without_unit_equivalence_is_not_qualified(self):
        evidence = collect_trade_flow_evidence(
            getter([trade(1_000, "2", trade_id=1), trade(-1_000, trade_id=2)]), NOW, "PI_ETHUSD"
        )
        native = [END, "2"]
        metrics = {"trade-volume": {"latest": native, "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["trade-volume"]
        self.assertEqual(metric["temporal_alignment_status"], "ALIGNED")
        self.assertEqual(metric["metric_semantics_status"], "INSUFFICIENT_FOR_RAW_COMPARISON")
        self.assertEqual(metric["value_reconciliation_status"], "NOT_QUALIFIED")
        self.assertEqual(metric["availability_status"], "NOT_QUALIFIED")
        self.assertEqual(metric["latest"], native)
        self.assertIsNone(metric["raw_observed_value"])

    def test_20_aggressor_differential_quantity_equivalence_not_assumed(self):
        evidence = collect_trade_flow_evidence(
            getter([trade(1_000, "2", "buy", trade_id=1), trade(-1_000, trade_id=2)]), NOW, "PI_ETHUSD"
        )
        native = [END, "2"]
        metrics = {"aggressor-differential": {"latest": native, "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["aggressor-differential"]
        self.assertEqual(metric["metric_semantics_status"], "TAKER_SIDE_QUALIFIED_QUANTITY_UNIT_NOT_QUALIFIED")
        self.assertEqual(metric["value_reconciliation_status"], "NOT_QUALIFIED")
        self.assertEqual(metric["availability_status"], "NOT_QUALIFIED")
        self.assertEqual(metric["latest"], native)

    def test_21_absolute_cvd_is_not_compared_to_one_bucket_signed_flow(self):
        evidence = collect_trade_flow_evidence(
            getter([trade(1_000, "4", "buy", trade_id=1), trade(-1_000, trade_id=2)]), NOW, "PI_ETHUSD"
        )
        native = [END, {"buy_volume": "4", "sell_volume": "0", "cvd": "12345"}]
        metrics = {"cvd": {"latest": native, "freshness_status": "LIVE_USABLE"}}
        gate_native_trade_metrics(metrics, evidence)
        metric = metrics["cvd"]
        self.assertEqual(metric["metric_semantics_status"], "PROVIDER_NATIVE_STATEFUL_DELTA_CONTRACT_NOT_QUALIFIED")
        self.assertEqual(metric["value_reconciliation_status"], "NOT_QUALIFIED")
        self.assertEqual(metric["availability_reason"], "PROVIDER_NATIVE_CVD_NOT_RAW_VALUE_VERIFIED")
        self.assertEqual(metric["latest"], native)
        self.assertIsNone(metric["raw_observed_value"])
'''
t=t.replace(marker,'\n'+additions+marker,1)
tests.write_text(t)
