from __future__ import annotations

import json
import unittest

from tools.history_issue_request import HistoryIssueRequestError, parse_issue_event, parse_request_body


class HistoryIssueRequestTests(unittest.TestCase):
    def test_semantic_request_is_normalized_without_physical_inputs(self):
        request = parse_request_body(json.dumps({
            "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "from_utc": "2025-04-09T00:00:00Z",
            "to_utc": "2025-08-25T00:00:00Z",
        }))
        self.assertEqual(request["mode"], "strict")
        self.assertEqual(request["output_format"], "csv")
        self.assertEqual(request["cutoff_utc"], "")
        self.assertNotIn("asset_name", request)
        self.assertNotIn("release_tag", request)

    def test_physical_route_input_is_rejected(self):
        with self.assertRaises(HistoryIssueRequestError):
            parse_request_body(json.dumps({
                "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
                "from_utc": "2025-04-09T00:00:00Z",
                "to_utc": "2025-08-25T00:00:00Z",
                "asset_name": "binance--ETHUSDT--1h--2025.json",
            }))

    def test_owner_only_issue_event_is_accepted(self):
        event = {
            "repository": {"owner": {"login": "owner"}},
            "issue": {
                "number": 42,
                "title": "[history-read] ETHUSDT H1 wave audit",
                "user": {"login": "owner"},
                "body": json.dumps({
                    "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
                    "from_utc": "2025-04-09T00:00:00Z",
                    "to_utc": "2025-08-25T00:00:00Z",
                    "mode": "strict",
                    "output_format": "csv",
                }),
            },
        }
        number, request, digest = parse_issue_event(event)
        self.assertEqual(number, 42)
        self.assertEqual(request["series_id"], "spot.binance-spot.ETHUSDT.ohlcv.1h")
        self.assertEqual(len(digest), 64)

    def test_non_owner_request_is_rejected(self):
        event = {
            "repository": {"owner": {"login": "owner"}},
            "issue": {
                "number": 42,
                "title": "[history-read] request",
                "user": {"login": "someone-else"},
                "body": "{}",
            },
        }
        with self.assertRaises(HistoryIssueRequestError):
            parse_issue_event(event)

    def test_invalid_range_is_rejected(self):
        with self.assertRaises(HistoryIssueRequestError):
            parse_request_body(json.dumps({
                "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
                "from_utc": "2025-08-25T00:00:00Z",
                "to_utc": "2025-04-09T00:00:00Z",
            }))


if __name__ == "__main__":
    unittest.main()
