from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import history_sealer as sealer


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


class D9SealingCrashMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "history/binance/ETHUSDT/1h/2026").mkdir(parents=True)
        (self.root / "derivatives").mkdir(exist_ok=True)
        (self.root / "options").mkdir(exist_ok=True)
        (self.root / "contracts").mkdir(exist_ok=True)
        jan_start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        jan_last = int(datetime(2026, 1, 31, 23, tzinfo=timezone.utc).timestamp() * 1000)
        (self.root / "history/release-manifest.json").write_text(
            compact({
                "series_inventory":[{
                    "provider":"binance",
                    "instrument":"ETHUSDT",
                    "interval_or_metric":"1h",
                    "last_timestamp":jan_last,
                }]
            }),
            encoding="utf-8",
        )
        (self.root / "history/manifest.json").write_text(
            compact({
                "schema_version":"1.0.0",
                "series":[{
                    "provider":"binance",
                    "symbol":"ETHUSDT",
                    "interval":"1h",
                    "first_timestamp":jan_start,
                    "last_timestamp":jan_last,
                    "historical_backfill":"PASS",
                    "provider_history_limit":False,
                }],
            }),
            encoding="utf-8",
        )
        (self.root / "derivatives/history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":[]}), encoding="utf-8")
        (self.root / "derivatives/deribit-history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":[],"d9_candidate_series":[]}), encoding="utf-8")
        (self.root / "options/history-manifest.json").write_text(
            compact({"schema_version":"1.0.0","deribit_dvol":{"historical_backfill":"UNAVAILABLE_BY_PROVIDER"}}),
            encoding="utf-8",
        )
        (self.root / "contracts/d9-sealing-candidate.json").write_text(
            compact({
                "generation_membership":{
                    "policy_version":"d9-generation-membership/1.0.0",
                    "authority":"CANONICAL_WARM_MANIFESTS",
                },
                "finalization_policy":{
                    "policy_version":"d9-cold-finalization/1.0.0",
                    "regular_grid_default_finalization_lag_seconds":3600,
                    "provider_overrides":{"kraken-futures":{"ingestion_stabilization_source":"derivatives/metric-semantics.json"}},
                    "metric_overrides":{},
                    "revision_class_lag_seconds":{
                        "STRICT_OVERLAP_REQUIRED":0,
                        "WINDOW_ANCHORED_CUMULATIVE":0,
                        "PROVIDER_REVISABLE_SNAPSHOT":10800,
                    },
                    "missing_required_revision_policy":"FAIL_CLOSED",
                },
                "high_cardinality_warm":{"status":"BLOCKED_TEST","cold_sealing_enabled":False},
            }),
            encoding="utf-8",
        )
        start, end = sealer.month_bounds(2026, 2)
        rows = [[ts,"1","2","0.5","1.5","10",ts + 3599999] for ts in range(start, end, 3600000)]
        self.warm = self.root / "history/binance/ETHUSDT/1h/2026/02.json"
        self.warm.write_text(
            compact({
                "schema_version":"1.0.0",
                "provider":"binance",
                "symbol":"ETHUSDT",
                "interval":"1h",
                "columns":["open_time_ms","open","high","low","close","base_volume","close_time_ms"],
                "closed_only":True,
                "records":rows,
            }),
            encoding="utf-8",
        )
        self.as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp() * 1000)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def remote_fixture(manifest):
        asset = manifest["assets"][0]
        raw = Path(manifest["_asset_paths"][asset["asset_name"]]).read_bytes()
        release = {
            "id":4242,
            "tag_name":manifest["generation_id"],
            "draft":False,
            "immutable":True,
        }
        remote_asset = {
            "id":9901,
            "name":asset["asset_name"],
            "size":len(raw),
            "browser_download_url":"https://example.invalid/d9-cold-asset",
        }
        return release, remote_asset, raw

    @staticmethod
    def read_only_release_gh(remote_release):
        calls = []

        def gh(path, method="GET", payload=None, **_kwargs):
            calls.append((path, method, payload))
            if path != f"/releases/{remote_release['id']}" or method != "GET" or payload is not None:
                raise AssertionError(f"unexpected release mutation during immutable retry: {path} {method}")
            return dict(remote_release)

        return calls, gh

    def test_remote_success_local_install_loss_same_candidate_converges(self):
        first = sealer.build(self.as_of, self.root / "first", self.root)
        self.assertEqual(len(first), 1)
        remote_release, remote_asset, remote_raw = self.remote_fixture(first[0])
        self.assertFalse((self.root / "history/generation-index.json").exists())

        retry = sealer.build(self.as_of, self.root / "retry", self.root)
        self.assertEqual(retry[0]["generation_id"], first[0]["generation_id"])
        self.assertEqual(retry[0]["candidate_fingerprint"], first[0]["candidate_fingerprint"])
        gh_calls, gh = self.read_only_release_gh(remote_release)
        with (
            patch.object(sealer.release, "release_by_tag", return_value=remote_release),
            patch.object(sealer.release, "list_assets", return_value=[remote_asset]),
            patch.object(sealer.release, "download_release_asset", return_value=remote_raw),
            patch.object(sealer.release, "gh", side_effect=gh),
            patch.object(sealer.release, "upload_verified") as upload,
        ):
            sealer.publish_generation(retry[0])
            index = sealer.install_candidate_control_plane(retry, self.root)
        self.assertEqual(gh_calls, [("/releases/4242", "GET", None)])
        upload.assert_not_called()
        self.assertEqual(retry[0]["publication"]["readback_status"], "PASS")
        self.assertEqual(index["generations"][0]["generation_id"], first[0]["generation_id"])
        self.assertTrue((self.root / "history/generations" / f"{first[0]['generation_id']}.json").is_file())

    def test_remote_success_local_install_loss_changed_candidate_fails_closed(self):
        first = sealer.build(self.as_of, self.root / "first", self.root)
        self.assertEqual(len(first), 1)
        remote_release, remote_asset, remote_raw = self.remote_fixture(first[0])
        original_id = first[0]["generation_id"]
        original_fingerprint = first[0]["candidate_fingerprint"]

        payload = json.loads(self.warm.read_text(encoding="utf-8"))
        payload["records"][0][4] = "1.6"
        self.warm.write_text(compact(payload), encoding="utf-8")
        changed = sealer.build(self.as_of, self.root / "changed", self.root)
        self.assertEqual(changed[0]["generation_id"], original_id)
        self.assertNotEqual(changed[0]["candidate_fingerprint"], original_fingerprint)
        self.assertFalse((self.root / "history/generation-index.json").exists())

        gh_calls, gh = self.read_only_release_gh(remote_release)
        with (
            patch.object(sealer.release, "release_by_tag", return_value=remote_release),
            patch.object(sealer.release, "list_assets", return_value=[remote_asset]),
            patch.object(sealer.release, "download_release_asset", return_value=remote_raw),
            patch.object(sealer.release, "gh", side_effect=gh),
            patch.object(sealer.release, "upload_verified") as upload,
        ):
            with self.assertRaisesRegex(RuntimeError, "remote COLD sha mismatch"):
                sealer.publish_generation(changed[0])
        self.assertEqual(gh_calls, [("/releases/4242", "GET", None)])
        upload.assert_not_called()
        self.assertFalse((self.root / "history/generation-index.json").exists())
        self.assertFalse((self.root / "history/generations").exists())


if __name__ == "__main__":
    unittest.main()
