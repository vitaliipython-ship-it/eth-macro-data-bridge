import json
import tempfile
import unittest
from pathlib import Path

from tools.deep_history import kraken_spot_posttrade as posttrade


class Response:
    def __init__(self, payload, *, status=200, headers=None):
        self._raw = json.dumps(payload, separators=(",", ":")).encode()
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._raw


class Opener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def open(self, request, timeout=30):
        self.requests.append(request.full_url)
        if not self.payloads:
            raise AssertionError("unexpected extra network request")
        return Response(self.payloads.pop(0))


def trade(ts, tid, price="100", quantity="1", **extra):
    return {
        "trade_ts": ts,
        "trade_id": tid,
        "price": price,
        "quantity": quantity,
        "symbol": "ETH/USD",
        "side": extra.pop("side", "buy"),
        "ord_type": extra.pop("ord_type", "limit"),
        **extra,
    }


def page(trades, last_ts):
    return {"error": [], "result": {"count": len(trades), "trades": trades, "last_ts": last_ts}}


class KrakenSpotPostTradeTests(unittest.TestCase):
    def test_source_identity_and_schema(self):
        self.assertEqual("KRAKEN_OFFICIAL_POSTTRADE_BULK", posttrade.SOURCE_MODE)
        self.assertEqual("https://api.kraken.com/0/public/PostTrade", posttrade.ENDPOINT)
        self.assertEqual("ETH/USD", posttrade.SYMBOL)
        self.assertEqual(1, posttrade.MAX_PARALLEL)
        self.assertEqual(7, posttrade.ARTIFACT_RETENTION_DAYS)

    def test_quarter_inventory_is_deterministic_and_partial_at_edges(self):
        left = posttrade.build_segment_inventory("2015-08-07T00:00:00Z", "2016-04-02T00:00:00Z")
        right = posttrade.build_segment_inventory("2015-08-07T00:00:00Z", "2016-04-02T00:00:00Z")
        self.assertEqual(left, right)
        self.assertEqual(
            [
                ("2015-08-07T00:00:00.000000Z", "2015-10-01T00:00:00.000000Z"),
                ("2015-10-01T00:00:00.000000Z", "2016-01-01T00:00:00.000000Z"),
                ("2016-01-01T00:00:00.000000Z", "2016-04-01T00:00:00.000000Z"),
                ("2016-04-01T00:00:00.000000Z", "2016-04-02T00:00:00.000000Z"),
            ],
            [(item["requested_start_utc"], item["requested_end_utc"]) for item in left],
        )
        self.assertEqual(len({item["segment_id"] for item in left}), len(left))

    def test_retention_plan_covers_full_execution_budget(self):
        plan = posttrade.retention_plan(posttrade.MARKET_INCEPTION_UTC, "2026-08-12T06:30:00Z")
        self.assertEqual(45, plan["segment_count"])
        self.assertEqual("160236.887220", plan["required_retention_seconds"])
        self.assertEqual("604800", plan["configured_retention_seconds"])
        self.assertEqual("444563.112780", plan["retention_safety_margin_seconds"])
        self.assertEqual("PASS", plan["status"])

    def test_cursor_non_advancement_fails_closed(self):
        opener = Opener([page([], "2020-01-01T00:00:00.000000Z")])
        with self.assertRaisesRegex(posttrade.PostTradeIncomplete, "CURSOR_NON_ADVANCING"):
            posttrade._request_page(
                "2020-01-01T00:00:00.000000Z",
                "2020-01-02T00:00:00.000000Z",
                opener=opener,
                sleep_fn=lambda _: None,
            )

    def test_provider_schema_rejects_missing_trade_id(self):
        broken = trade("2020-01-01T00:00:01Z", "x")
        del broken["trade_id"]
        with self.assertRaisesRegex(posttrade.PostTradeIncomplete, "SCHEMA_NOT_QUALIFIED"):
            posttrade._normalize_trade(broken)

    def test_same_trade_id_identical_row_dedups(self):
        item = trade("2020-01-01T00:00:01Z", "A", "100", "2")
        opener = Opener([page([item, dict(item)], "2020-01-01T00:10:00Z")])
        with tempfile.TemporaryDirectory() as temporary:
            descriptor = posttrade.segment_descriptor("2020-01-01T00:00:00Z", "2020-01-01T00:05:00Z")
            result = posttrade.execute_segment(Path(temporary), descriptor, opener=opener, sleep_fn=lambda _: None, delay_seconds=0)
            evidence = result["evidence"]
            self.assertEqual(2, evidence["raw_row_count"])
            self.assertEqual(1, evidence["unique_trade_count"])
            self.assertEqual(1, evidence["duplicate_trade_id_count"])
            self.assertEqual(0, evidence["trade_id_conflict_count"])

    def test_same_trade_id_different_row_fails_closed(self):
        left = trade("2020-01-01T00:00:01Z", "A", "100", "2")
        right = trade("2020-01-01T00:00:01Z", "A", "101", "2")
        opener = Opener([page([left, right], "2020-01-01T00:10:00Z")])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = posttrade.segment_descriptor("2020-01-01T00:00:00Z", "2020-01-01T00:05:00Z")
            with self.assertRaisesRegex(posttrade.PostTradeIncomplete, "TRADE_ID_CONFLICT"):
                posttrade.execute_segment(root, descriptor, opener=opener, sleep_fn=lambda _: None, delay_seconds=0)
            self.assertFalse((root / "segments" / descriptor["segment_id"]).exists())
            state = json.loads((root / "states" / f"{descriptor['segment_id']}.json").read_text())
            self.assertEqual("FAILED", state["status"])

    def test_economically_equal_distinct_ids_are_retained_in_order(self):
        rows = [
            trade("2020-01-01T00:00:01.000000001Z", "A", "100", "2"),
            trade("2020-01-01T00:00:01.000000001Z", "B", "100", "2"),
        ]
        opener = Opener([page(rows, "2020-01-01T00:10:00Z")])
        with tempfile.TemporaryDirectory() as temporary:
            descriptor = posttrade.segment_descriptor("2020-01-01T00:00:00Z", "2020-01-01T00:05:00Z")
            result = posttrade.execute_segment(Path(temporary), descriptor, opener=opener, sleep_fn=lambda _: None, delay_seconds=0)
            output = json.loads((Path(result["directory"]) / "segment-output.json").read_text())
            row = output["5m"][0]
            self.assertEqual("100", row[1])
            self.assertEqual("100", row[4])
            self.assertEqual("4", row[5])
            self.assertEqual(2, row[6])
            self.assertEqual(["A", "B"], (Path(result["directory"]) / "provider-trade-ids.txt").read_text().splitlines())

    def test_no_trade_segment_is_complete_without_synthetic_candles(self):
        opener = Opener([page([], "2020-01-01T01:00:00Z")])
        with tempfile.TemporaryDirectory() as temporary:
            descriptor = posttrade.segment_descriptor("2020-01-01T00:00:00Z", "2020-01-01T00:30:00Z")
            result = posttrade.execute_segment(Path(temporary), descriptor, opener=opener, sleep_fn=lambda _: None, delay_seconds=0)
            output = json.loads((Path(result["directory"]) / "segment-output.json").read_text())
            self.assertEqual([], output["5m"])
            self.assertEqual([], output["1d"])
            self.assertEqual(0, result["evidence"]["unique_trade_count"])
            self.assertEqual(posttrade.GAP_POLICY, result["evidence"]["gap_policy"])
            self.assertFalse(result["evidence"]["synthetic_fill"])

    def test_atomic_interruption_discards_partial_and_restart_matches(self):
        rows = [trade("2020-01-01T00:00:01Z", "A", "100", "1")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = posttrade.segment_descriptor("2020-01-01T00:00:00Z", "2020-01-01T00:05:00Z")
            with self.assertRaises(posttrade.SegmentInterrupted):
                posttrade.execute_segment(
                    root / "restart",
                    descriptor,
                    opener=Opener([page(rows, "2020-01-01T00:10:00Z")]),
                    sleep_fn=lambda _: None,
                    delay_seconds=0,
                    interrupt_after_pages=1,
                )
            self.assertFalse((root / "restart" / "segments" / descriptor["segment_id"]).exists())
            restarted = posttrade.execute_segment(
                root / "restart", descriptor, opener=Opener([page(rows, "2020-01-01T00:10:00Z")]), sleep_fn=lambda _: None, delay_seconds=0
            )
            uninterrupted = posttrade.execute_segment(
                root / "direct", descriptor, opener=Opener([page(rows, "2020-01-01T00:10:00Z")]), sleep_fn=lambda _: None, delay_seconds=0
            )
            self.assertEqual(restarted["evidence"]["frozen_source_digest"], uninterrupted["evidence"]["frozen_source_digest"])
            self.assertEqual((Path(restarted["directory"]) / "segment-output.json").read_bytes(), (Path(uninterrupted["directory"]) / "segment-output.json").read_bytes())
            self.assertFalse((Path(restarted["directory"]) / "normalized.jsonl").exists())
            self.assertFalse((Path(restarted["directory"]) / "raw-pages.bin").exists())

    def test_aggregation_preserves_gaps_and_build_ab_source_digest(self):
        rows = [
            trade("2020-01-01T00:00:01Z", "A", "100", "1"),
            trade("2020-01-01T00:10:01Z", "B", "105", "3"),
        ]
        opener = Opener([page(rows, "2020-01-01T01:00:00Z")])
        with tempfile.TemporaryDirectory() as temporary:
            descriptor = posttrade.segment_descriptor("2020-01-01T00:00:00Z", "2020-01-01T00:15:00Z")
            result = posttrade.execute_segment(Path(temporary), descriptor, opener=opener, sleep_fn=lambda _: None, delay_seconds=0)
            output = json.loads((Path(result["directory"]) / "segment-output.json").read_text())
            self.assertEqual(2, len(output["5m"]))
            self.assertEqual([1577836800000, 1577837400000], [row[0] for row in output["5m"]])
            evidence = result["evidence"]
            self.assertEqual(evidence["frozen_source_digest"], evidence["build_a_source_digest"])
            self.assertEqual(evidence["build_a_source_digest"], evidence["build_b_source_digest"])
            self.assertTrue(evidence["derived_5m_digest"])
            self.assertTrue(evidence["derived_1d_digest"])

    def test_assembly_merges_shared_daily_bucket(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a_dir = root / "a"; b_dir = root / "b"; a_dir.mkdir(); b_dir.mkdir()
            a_output = {
                "5m": [[1577836800000, "100", "101", "99", "100", "1", 1, 1577837099999]],
                "1d": [[1577836800000, "100", "101", "99", "100", "1", 1, 1577923199999]],
            }
            b_output = {
                "5m": [[1577837100000, "102", "103", "101", "102", "2", 1, 1577837399999]],
                "1d": [[1577836800000, "102", "103", "101", "102", "2", 1, 1577923199999]],
            }
            for directory, output, tid in ((a_dir, a_output, "A"), (b_dir, b_output, "B")):
                (directory / "segment-output.json").write_bytes(posttrade.compact(output))
                (directory / "provider-trade-ids.txt").write_text(tid + "\n")
                (directory / "evidence.json").write_bytes(posttrade.compact({"completion_status": "COMPLETE"}))
            assembled = posttrade.assemble_segment_outputs([a_dir, b_dir])
            self.assertEqual(2, len(assembled["5m"]))
            daily = assembled["1d"][0]
            self.assertEqual(["100", "103", "99", "102", "3", 2], [daily[1], daily[2], daily[3], daily[4], daily[5], daily[6]])

    def test_completed_inventory_reuses_prior_segment_without_network(self):
        rows = [trade("2020-01-01T00:00:01Z", "A")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            start = "2020-01-01T00:00:00Z"; end = "2020-01-02T00:00:00Z"
            descriptor = posttrade.build_segment_inventory(start, end)[0]
            posttrade.execute_segment(root, descriptor, opener=Opener([page(rows, "2020-01-02T00:00:00Z")]), sleep_fn=lambda _: None, delay_seconds=0)
            execution = posttrade.execute_inventory(root, start, end, opener=Opener([]), sleep_fn=lambda _: None, delay_seconds=0)
            self.assertTrue(execution["results"][0]["reused"])
            state = json.loads((root / "inventory.json").read_text())
            self.assertEqual("COMPLETE", state["segments"][0]["status"])


if __name__ == "__main__":
    unittest.main()
