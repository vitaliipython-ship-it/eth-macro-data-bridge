from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
for value in (ROOT,ROOT/"src",ROOT/"tools"):
    if str(value) not in sys.path:
        sys.path.insert(0,str(value))

import event_window
from tools import current_data_transport as transport


class EventsFreshCurrentTests(unittest.TestCase):
    def _request(self, domains=None, max_age=600):
        return transport.normalize_request({
            "request_type":"FRESH_CURRENT",
            "required_series":[],
            "required_domains":domains or ["EVENTS"],
            "max_generation_age_seconds":max_age,
            "current_policy":"FINALIZED_ONLY",
        })

    def _empty_manifest(self, path: Path):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({
            "schema_version":event_window.EVENT_VERSION,
            "event_count":0,
            "latest_event":None,
            "events":[],
        }),encoding="utf-8")

    def test_empty_events_manifest_is_valid_with_explicit_generation_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"events/manifest.json"
            self._empty_manifest(path)
            manifest=event_window.refresh_event_manifest("2026-08-27T12:00:00Z",manifest_path=path)
            persisted=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["event_count"],0)
        self.assertIsNone(manifest["latest_event"])
        self.assertEqual(manifest["events"],[])
        self.assertEqual(manifest["generated_at_utc"],"2026-08-27T12:00:00.000Z")
        self.assertEqual(persisted,manifest)

    def test_generation_identity_is_utc_and_untrusted_time_fails_closed(self):
        self.assertEqual(event_window.canonical_generation_time("2026-08-27T12:00:00+00:00"),"2026-08-27T12:00:00.000Z")
        for value in ("", "2026-08-27T12:00:00", "2026-08-27T15:00:00+03:00", "not-a-time"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                event_window.canonical_generation_time(value)

    def test_events_resource_index_materializes_empty_registry(self):
        request=self._request()
        wrapper=transport.request_wrapper(request)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"events/manifest.json"; self._empty_manifest(source)
            event_window.refresh_event_manifest("2026-08-27T12:00:00Z",manifest_path=source)
            output=root/"out"; output.mkdir()
            with mock.patch.object(transport,"_domain_manifest_path",return_value=source):
                index=transport.build_resource_index(
                    request,wrapper["request_sha256"],output_root=output,
                    now=datetime(2026,8,27,12,5,tzinfo=timezone.utc),
                )
        row=index["domains"][0]
        self.assertEqual(row["domain_id"],"EVENTS")
        self.assertEqual(row["resource_logical_id"],"current-domain:events")
        self.assertEqual(row["generated_at_utc"],"2026-08-27T12:00:00.000Z")
        self.assertEqual(row["freshness"],"FRESH")
        self.assertEqual(row["status"],"PASS")

    def test_events_fresh_and_stale_evaluation_uses_registry_generation_time(self):
        request=self._request(max_age=600)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"events/manifest.json"; self._empty_manifest(source)
            event_window.refresh_event_manifest("2026-08-27T12:00:00Z",manifest_path=source)
            with mock.patch.object(transport,"_domain_manifest_path",return_value=source):
                fresh=transport.evaluate_persisted_freshness(request,now=datetime(2026,8,27,12,10,tzinfo=timezone.utc))
                stale=transport.evaluate_persisted_freshness(request,now=datetime(2026,8,27,12,10,1,tzinfo=timezone.utc))
        self.assertTrue(fresh["persisted_fresh_enough"])
        self.assertEqual(fresh["generation_mode"],"PERSISTED_REUSE")
        self.assertFalse(stale["persisted_fresh_enough"])
        self.assertEqual(stale["generation_mode"],"FRESH_ACQUISITION")
        self.assertTrue(any(reason.startswith("STALE:domain:EVENTS:") for reason in stale["reasons"]))

    def test_missing_generation_time_still_fails_closed(self):
        request=self._request()
        wrapper=transport.request_wrapper(request)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"events/manifest.json"; self._empty_manifest(source)
            output=root/"out"; output.mkdir()
            with mock.patch.object(transport,"_domain_manifest_path",return_value=source):
                freshness=transport.evaluate_persisted_freshness(request,now=datetime(2026,8,27,12,5,tzinfo=timezone.utc))
                with self.assertRaises(transport.CurrentDataTransportError) as caught:
                    transport.build_resource_index(request,wrapper["request_sha256"],output_root=output)
        self.assertIn("NO_GENERATION_TIME:domain:EVENTS",freshness["reasons"])
        self.assertFalse(freshness["persisted_fresh_enough"])
        self.assertEqual(caught.exception.code,"DOMAIN_GENERATION_TIME_MISSING")

    def test_all_six_domains_keep_existing_resource_index_semantics(self):
        domains=["SPOT","DERIVATIVES","OPTIONS","LIQUIDITY","ANALYTICS","EVENTS"]
        request=self._request(domains=domains)
        wrapper=transport.request_wrapper(request)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); paths={}
            for domain in domains:
                path=root/f"{domain.lower()}.json"; paths[domain]=path
                if domain=="EVENTS":
                    self._empty_manifest(path)
                    event_window.refresh_event_manifest("2026-08-27T12:00:00Z",manifest_path=path)
                else:
                    path.write_text(json.dumps({"generated_at_utc":"2026-08-27T12:00:00Z","status":"PASS"}),encoding="utf-8")
            output=root/"out"; output.mkdir()
            with mock.patch.object(transport,"_domain_manifest_path",side_effect=lambda domain: paths[domain]):
                index=transport.build_resource_index(
                    request,wrapper["request_sha256"],output_root=output,
                    now=datetime(2026,8,27,12,5,tzinfo=timezone.utc),
                )
        self.assertEqual([row["domain_id"] for row in index["domains"]],sorted(domains))
        self.assertTrue(all(row["status"]=="PASS" and row["freshness"]=="FRESH" for row in index["domains"]))

    def test_collector_refreshes_events_with_same_generation_anchor(self):
        source=(ROOT/"src/collector.py").read_text(encoding="utf-8")
        self.assertIn("now = int(time.time()*1000); generated = iso(now)",source)
        self.assertIn("refresh_event_manifest(generated)",source)
        self.assertNotIn("refresh_event_manifest(iso(int(time.time()",source)


if __name__=="__main__":
    unittest.main()
