from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from kraken_trade_flow import collect_trade_flow_evidence, gate_native_trade_metrics, normalize_trade, classify_root_cause


def iso(ms):
    return datetime.fromtimestamp(ms/1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

NOW = 1_800_000_000_000
END = (NOW // 300_000) * 300_000
START = END - 300_000


def trade(offset_ms, size="2", side="buy", symbol=None, trade_id=1):
    row = {"time": iso(START + offset_ms), "price": "2500", "size": size, "side": side, "trade_id": trade_id, "type": "fill"}
    if symbol is not None:
        row["symbol"] = symbol
    return row


def getter(history, server_time=None):
    def get(url):
        return {"result": "success", "serverTime": server_time or iso(END + 1_000), "history": list(history)}
    return get


class KrakenTradeFlowTests(unittest.TestCase):
    def test_1_valid_trades_count_and_volume(self):
        evidence = collect_trade_flow_evidence(getter([trade(1_000,"2","buy",trade_id=1), trade(2_000,"3","sell",trade_id=2), trade(-1_000,"1","buy",trade_id=3)]), NOW, "PI_ETHUSD")
        self.assertTrue(evidence["coverage_complete"])
        self.assertEqual(evidence["bucketed_trade_count"], 2)
        self.assertEqual(Decimal(evidence["native_quantity_sum"]), Decimal("5"))

    def test_2_balanced_aggressor_flow_zero_is_not_no_data(self):
        evidence = collect_trade_flow_evidence(getter([trade(1_000,"4","buy",trade_id=1), trade(2_000,"4","sell",trade_id=2), trade(-1_000,"1","buy",trade_id=3)]), NOW, "PI_ETHUSD")
        self.assertEqual(evidence["bucketed_trade_count"], 2)
        self.assertEqual(evidence["buy_volume"], "4")
        self.assertEqual(evidence["sell_volume"], "4")
        self.assertEqual(evidence["signed_volume"], "0")

    def test_3_no_trades_complete_observation_is_valid_zero(self):
        evidence = collect_trade_flow_evidence(getter([]), NOW, "PI_ETHUSD")
        self.assertTrue(evidence["feed_observed"])
        self.assertTrue(evidence["coverage_complete"])
        self.assertEqual(evidence["bucketed_trade_count"], 0)
        self.assertEqual(evidence["native_quantity_sum"], "0")

    def test_4_feed_unavailable_fails_closed(self):
        def fail(_url): raise OSError("network down")
        evidence = collect_trade_flow_evidence(fail, NOW, "PI_ETHUSD")
        self.assertFalse(evidence["feed_observed"])
        self.assertFalse(evidence["coverage_complete"])
        metrics = {name:{"latest":[END,0],"freshness_status":"LIVE_USABLE"} for name in ("trade-count","trade-volume","aggressor-differential","cvd")}
        gate_native_trade_metrics(metrics,evidence)
        self.assertTrue(all(x["latest"] is None and x["availability_status"]=="UNAVAILABLE" for x in metrics.values()))
        self.assertTrue(all(x["native_latest"] == [END,0] for x in metrics.values()))

    def test_5_wrong_product_is_observable_not_zero_market(self):
        evidence = collect_trade_flow_evidence(getter([trade(1_000,"2","buy","PF_ETHUSD",1),trade(-1_000,"1","buy","PI_ETHUSD",2)]), NOW, "PI_ETHUSD")
        self.assertEqual(evidence["parsed_trade_count"], 2)
        self.assertEqual(evidence["product_matched_trade_count"], 1)
        self.assertEqual(evidence["drop_reason_counts"].get("PRODUCT_MISMATCH"),1)

    def test_6_bucket_boundaries_are_start_inclusive_end_exclusive(self):
        rows=[trade(-1,"1","buy",trade_id=1),trade(0,"1","buy",trade_id=2),trade(150_000,"1","sell",trade_id=3),trade(300_000,"1","buy",trade_id=4)]
        evidence=collect_trade_flow_evidence(getter(rows),NOW,"PI_ETHUSD")
        self.assertEqual(evidence["bucketed_trade_count"],2)

    def test_7_representative_payload_normalizes_timestamp_price_size_side_id(self):
        raw={"time":iso(START+1000),"price":2500.5,"size":"7","side":"sell","trade_id":42,"type":"fill"}
        parsed=normalize_trade(raw,"PI_ETHUSD")
        self.assertEqual(parsed["aggressor_side"],"sell")
        self.assertEqual(parsed["trade_id"],42)
        self.assertEqual(parsed["native_size"],"7")

    def test_8_unknown_side_is_never_silently_buy_or_sell(self):
        evidence=collect_trade_flow_evidence(getter([trade(1_000,"2","mystery",trade_id=1),trade(-1_000,"1","buy",trade_id=2)]),NOW,"PI_ETHUSD")
        self.assertEqual(evidence["unknown_aggressor_count"],1)
        self.assertIsNone(evidence["signed_volume"])

    def test_9_unavailable_materialization_never_recoerces_to_zero(self):
        evidence={"feed_observed":True,"coverage_complete":False,"bucket_start":START,"bucket_end":END,"raw_trade_message_count":0,"bucketed_trade_count":0}
        metrics={"trade-count":{"latest":[END,0],"freshness_status":"LIVE_USABLE"}}
        gate_native_trade_metrics(metrics,evidence)
        self.assertIsNone(metrics["trade-count"]["latest"])
        self.assertEqual(metrics["trade-count"]["native_latest"],[END,0])

    def test_10_cvd_is_not_recomputed_or_reset_by_gate(self):
        evidence={"feed_observed":True,"coverage_complete":True,"bucket_start":START,"bucket_end":END,"raw_trade_message_count":2,"bucketed_trade_count":2}
        native=[END,{"buy_volume":"4","sell_volume":"4","cvd":"123"}]
        metrics={"cvd":{"latest":native,"freshness_status":"LIVE_USABLE"}}
        gate_native_trade_metrics(metrics,evidence)
        self.assertEqual(metrics["cvd"]["latest"],native)
        self.assertEqual(metrics["cvd"]["native_latest"],native)

    def test_decision_tree_a_when_no_observation(self):
        self.assertEqual(classify_root_cause({"feed_observed":False,"raw_trade_message_count":0,"coverage_complete":False}),"A_ACQUISITION_OR_COVERAGE")

    def test_parser_failure_is_observable(self):
        bad={"time":"not-a-time","price":"2500","size":"1","side":"buy"}
        evidence=collect_trade_flow_evidence(getter([bad]),NOW,"PI_ETHUSD")
        self.assertTrue(evidence["feed_observed"])
        self.assertIsNotNone(evidence["parser_error"])
        self.assertEqual(evidence["drop_reason_counts"].get("PARSER_ERROR"),1)


if __name__ == "__main__": unittest.main()
