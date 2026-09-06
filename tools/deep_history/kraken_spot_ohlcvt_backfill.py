from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tools.deep_history import kraken_spot_posttrade as posttrade
from tools.deep_history import release_publisher as release

SCHEMA = "1.0.0"
SOURCE_SCHEMA = posttrade.SOURCE_SCHEMA
SOURCE_MODE = posttrade.SOURCE_MODE
GAP_POLICY = posttrade.GAP_POLICY
SUPPORT_URL = posttrade.DOCUMENTATION
RELEASE_TAG = "history-kraken-spot-v2"
TARGETS = {"5m": {"minutes": 5, "aliases": ("ETHUSD_5.csv", "XETHZUSD_5.csv")}, "1d": {"minutes": 1440, "aliases": ("ETHUSD_1440.csv", "XETHZUSD_1440.csv")}}
COLUMNS = ["open_time_ms", "open", "high", "low", "close", "volume", "trade_count", "close_time_ms"]
ROOT = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / "kraken-spot-ohlcvt-v2"
FROZEN_SOURCE_ROOT = ROOT / "source" / "posttrade-segments"
ARCHIVE = ROOT / "source" / "kraken-posttrade-derived-ohlcvt.zip"
SOURCE_META = ROOT / "source" / "source.json"
BUILD_A = ROOT / "build-a"
BUILD_B = ROOT / "build-b"
GENERATED = ROOT / "release-manifest.generated.json"
WARM_OVERLAP_MS = 4 * 86_400_000
QUALIFICATION_START_UTC = "2017-06-29T00:00:00Z"
QUALIFICATION_END_UTC = "2017-07-03T00:00:00Z"


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _warm_first_timestamp(repository_root: Path = Path(".")) -> int:
    timestamps = []
    for path in sorted((Path(repository_root) / "history" / "kraken" / "ETHUSD" / "5m").rglob("*.json")):
        payload = json.loads(path.read_text())
        timestamps.extend(int(row[0]) for row in payload.get("records", []) if row)
    if not timestamps:
        raise RuntimeError("canonical Kraken ETHUSD M5 WARM boundary is unavailable")
    return min(timestamps)


def _iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _utc_day_start_ms(value: int) -> int:
    dt = datetime.fromtimestamp(value / 1000, timezone.utc)
    return int(datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp() * 1000)


def _source_lineage(results: list[dict]) -> dict:
    evidence = [item["evidence"] for item in results]
    frozen = [item["frozen_source_digest"] for item in evidence]
    outputs = [item["segment_output_digest"] for item in evidence]
    material = {"source_mode": SOURCE_MODE, "source_schema": SOURCE_SCHEMA, "endpoint": posttrade.ENDPOINT, "segment_ids": [item["segment_id"] for item in evidence], "frozen_source_digests": frozen, "segment_output_digests": outputs}
    return {
        "frozen_source_digest": hashlib.sha256(compact(frozen)).hexdigest(),
        "source_lineage_digest": hashlib.sha256(compact(material)).hexdigest(),
        "segment_count": len(evidence),
        "first_provider_trade_ts": next((x["first_provider_trade_ts"] for x in evidence if x["first_provider_trade_ts"]), None),
        "first_provider_trade_id": next((x["first_provider_trade_id"] for x in evidence if x["first_provider_trade_id"]), None),
        "last_provider_trade_ts": next((x["last_provider_trade_ts"] for x in reversed(evidence) if x["last_provider_trade_ts"]), None),
        "last_provider_trade_id": next((x["last_provider_trade_id"] for x in reversed(evidence) if x["last_provider_trade_id"]), None),
        "page_count": sum(int(x["page_count"]) for x in evidence),
        "raw_row_count": sum(int(x["raw_row_count"]) for x in evidence),
        "unique_trade_count": sum(int(x["unique_trade_count"]) for x in evidence),
        "duplicate_trade_id_count": sum(int(x["duplicate_trade_id_count"]) for x in evidence),
    }


def acquire_archive(destination: Path = ARCHIVE, *, cutoff_ms: int, warm_first_ms: int, opener=None) -> dict:
    end_ms = min(int(cutoff_ms), int(warm_first_ms) + WARM_OVERLAP_MS)
    execution = posttrade.execute_inventory(FROZEN_SOURCE_ROOT, posttrade.MARKET_INCEPTION_UTC, _iso_ms(end_ms), opener=opener)
    derived = posttrade.write_derived_archive(execution["assembled"], destination)
    lineage = _source_lineage(execution["results"])
    source = {
        "schema_version": SOURCE_SCHEMA, "source_mode": SOURCE_MODE, "authority": "KRAKEN_OFFICIAL_POSTTRADE", "endpoint": posttrade.ENDPOINT,
        "documentation": posttrade.DOCUMENTATION, "symbol": posttrade.SYMBOL, "segmentation": "UTC_CALENDAR_QUARTER", "resume_granularity": "COMPLETED_SEGMENT",
        "page_level_checkpointing": False, "max_parallel": posttrade.MAX_PARALLEL, "backfill_cutoff_ms": cutoff_ms, "canonical_warm_first_ms": warm_first_ms,
        "coverage_declared_start_utc": posttrade.MARKET_INCEPTION_UTC, "coverage_declared_end_utc": _iso_ms(end_ms), "archive_sha256": lineage["frozen_source_digest"],
        "archive_size_bytes": sum(sum(p.stat().st_size for p in Path(item["directory"]).iterdir() if p.is_file()) for item in execution["results"]),
        "source_lineage_digest": lineage["source_lineage_digest"], "segment_count": lineage["segment_count"], "first_provider_trade_ts": lineage["first_provider_trade_ts"],
        "first_provider_trade_id": lineage["first_provider_trade_id"], "last_provider_trade_ts": lineage["last_provider_trade_ts"], "last_provider_trade_id": lineage["last_provider_trade_id"],
        "page_count": lineage["page_count"], "raw_row_count": lineage["raw_row_count"], "unique_trade_count": lineage["unique_trade_count"],
        "duplicate_trade_id_count": lineage["duplicate_trade_id_count"], "derived_archive_sha256": derived["derived_archive_sha256"],
        "derived_archive_size_bytes": derived["derived_archive_size_bytes"], "derived_row_counts": derived["row_counts"], "gap_policy": GAP_POLICY, "synthetic_fill": False,
        "acquired_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    SOURCE_META.parent.mkdir(parents=True, exist_ok=True); SOURCE_META.write_bytes(compact(source))
    print(f"KRAKEN_OHLCVT_SOURCE_MODE={SOURCE_MODE}")
    print(f"KRAKEN_POSTTRADE_SEGMENT_COUNT={source['segment_count']}")
    return source


def _member_for_interval(names, interval: str) -> str:
    matches = [name for name in names if any(name.upper().endswith(alias.upper()) for alias in TARGETS[interval]["aliases"])]
    if len(matches) != 1:
        raise RuntimeError(f"expected one Kraken ETHUSD {interval} member, found {matches}")
    return matches[0]


def _decimal(value: str, context: str) -> str:
    text = value.strip()
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise RuntimeError(f"invalid Kraken decimal {context}: {value!r}") from exc
    if not number.is_finite():
        raise RuntimeError(f"non-finite Kraken decimal {context}: {value!r}")
    return text


def parse_ohlcvt(stream, interval: str, cutoff_ms: int) -> list[list]:
    step = TARGETS[interval]["minutes"] * 60 * 1000
    reader = csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
    rows = {}
    for line_number, raw in enumerate(reader, 1):
        if not raw or all(not value.strip() for value in raw):
            continue
        if len(raw) < 7:
            raise RuntimeError(f"Kraken OHLCVT row has fewer than 7 columns at line {line_number}")
        try:
            source_timestamp = Decimal(raw[0].strip())
        except InvalidOperation:
            if line_number == 1:
                continue
            raise
        if source_timestamp != source_timestamp.to_integral_value():
            raise RuntimeError(f"fractional Kraken OHLCVT timestamp at line {line_number}")
        timestamp = int(source_timestamp); timestamp_ms = timestamp * 1000 if timestamp < 10**12 else timestamp; close_time_ms = timestamp_ms + step - 1
        if close_time_ms >= cutoff_ms:
            continue
        if timestamp_ms % min(step, 86_400_000):
            raise RuntimeError(f"unaligned Kraken OHLCVT timestamp at line {line_number}: {timestamp_ms}")
        values = [_decimal(raw[index], f"line={line_number} column={index}") for index in range(1, 6)]
        trades = Decimal(raw[6].strip())
        if trades != trades.to_integral_value() or trades < 0:
            raise RuntimeError(f"invalid Kraken trade_count at line {line_number}")
        o, h, low, close, volume = map(Decimal, values)
        if h < max(o, low, close) or low > min(o, h, close) or volume < 0:
            raise RuntimeError(f"invalid Kraken OHLCVT candle at {timestamp_ms}")
        row = [timestamp_ms, *values, int(trades), close_time_ms]
        if timestamp_ms in rows and rows[timestamp_ms] != row:
            raise RuntimeError(f"conflicting Kraken OHLCVT timestamp {timestamp_ms}")
        rows[timestamp_ms] = row
    if not rows:
        raise RuntimeError(f"Kraken OHLCVT {interval} produced no closed rows")
    return [rows[key] for key in sorted(rows)]


def gap_summary(rows: list[list], step: int) -> dict:
    gaps = [b[0] - a[0] for a, b in zip(rows, rows[1:]) if b[0] - a[0] > step]
    return {"policy": GAP_POLICY, "synthetic_fill": False, "gap_events": len(gaps), "missing_intervals": sum(delta // step - 1 for delta in gaps)}


def _asset_descriptor(path, interval, period, records, summary, source) -> dict:
    return {
        "local_path": str(path), "asset_name": path.name, "provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": interval,
        "first_timestamp": records[0][0], "last_timestamp": records[-1][0], "row_count": len(records), "partitioning": "yearly", "closed_only": True,
        "size_bytes": path.stat().st_size, "sha256": sha256_file(path), "canonical_source_sha256": hashlib.sha256(compact(records)).hexdigest(),
        "retrieved_at_utc": source["acquired_at_utc"], "source_route": posttrade.ENDPOINT, "historical_availability": "MAX_AVAILABLE", "provider_history_limit": False,
        "known_gaps": [], "gap_semantics": summary,
        "boundary_proof": {"requested_start": posttrade.MARKET_INCEPTION_UTC, "earliest_accepted_timestamp": records[0][0], "last_timestamp": records[-1][0],
            "provider_more_exhausted": True, "boundary_status": "MAX_AVAILABLE", "source_route": posttrade.ENDPOINT, "source_mode": SOURCE_MODE,
            "source_schema_version": SOURCE_SCHEMA, "source_frozen_digest": source["archive_sha256"], "source_lineage_digest": source["source_lineage_digest"],
            "source_segment_count": source["segment_count"], "derived_archive_sha256": source["derived_archive_sha256"], "source_member_period": period,
            "gap_policy": GAP_POLICY, "synthetic_fill": False}, "metric_semantics": None,
    }


def build_assets(archive_path: Path, output_root: Path, cutoff_ms: int, source: dict) -> list[dict]:
    assets = []
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        for interval in ("5m", "1d"):
            with archive.open(archive.getinfo(_member_for_interval(names, interval))) as stream:
                rows = parse_ohlcvt(stream, interval, cutoff_ms)
            grouped = defaultdict(list)
            for row in rows:
                grouped[datetime.fromtimestamp(row[0] / 1000, timezone.utc).strftime("%Y")].append(row)
            for period, records in sorted(grouped.items()):
                summary = gap_summary(records, TARGETS[interval]["minutes"] * 60 * 1000)
                path = Path(output_root) / f"kraken--ETHUSD--{interval}--{period}.json"; path.parent.mkdir(parents=True, exist_ok=True)
                payload = {"schema_version": SCHEMA, "provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": interval, "columns": COLUMNS,
                    "partitioning": "yearly", "period": period, "closed_only": True, "source_semantics": "KRAKEN_POSTTRADE_DERIVED_OHLCVT", "gap_semantics": summary, "records": records}
                path.write_bytes(compact(payload))
                if path.stat().st_size > 64 * 1024 * 1024:
                    raise RuntimeError(f"Kraken OHLCVT asset exceeds 64 MiB: {path.name}")
                assets.append(_asset_descriptor(path, interval, period, records, summary, source))
    return sorted(assets, key=lambda item: item["asset_name"])


def compare_builds(left: list[dict], right: list[dict]) -> None:
    if {x["asset_name"]: x["sha256"] for x in left} != {x["asset_name"]: x["sha256"] for x in right}:
        raise RuntimeError("Kraken OHLCVT deterministic build mismatch")
    print(f"KRAKEN_OHLCVT_DETERMINISM=PASS assets={len(left)}")


def _numeric_equal(left, right) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def _warm_overlap_eligibility(candidate: list, interval: str, coverage_end_ms: int) -> tuple[bool, str]:
    step = TARGETS[interval]["minutes"] * 60 * 1000
    close_exclusive = int(candidate[7]) + 1
    expected_close_exclusive = int(candidate[0]) + step
    if close_exclusive != expected_close_exclusive:
        raise RuntimeError(f"candidate close boundary mismatch interval={interval} open={candidate[0]}")
    if close_exclusive > int(coverage_end_ms):
        return False, "PARTIAL_SOURCE_COVERAGE"
    return True, "FULL_SOURCE_COVERAGE"


def verify_warm_overlap_records(output: dict, repository_root: Path = Path("."), *, coverage_end_ms: int) -> dict:
    full = {interval: {row[0]: row for row in output[interval]} for interval in ("5m", "1d")}
    overlaps = {"5m": 0, "1d": 0}; partial_skipped = {"5m": 0, "1d": 0}; native_matches = {"5m": 0, "1d": 0}; conflicts = 0
    for interval in ("5m", "1d"):
        for path in sorted((Path(repository_root) / "history" / "kraken" / "ETHUSD" / interval).rglob("*.json")):
            payload = json.loads(path.read_text()); native = {row[0]: row for row in payload.get("provider_native_records", [])}
            for warm in payload.get("records", []):
                candidate = full[interval].get(warm[0])
                if candidate is None: continue
                eligible, reason = _warm_overlap_eligibility(candidate, interval, coverage_end_ms)
                if not eligible:
                    if reason != "PARTIAL_SOURCE_COVERAGE": raise RuntimeError(f"unexpected overlap eligibility reason: {reason}")
                    partial_skipped[interval] += 1
                    continue
                overlaps[interval] += 1; core = [candidate[0], *candidate[1:6], candidate[7]]
                if len(warm) < 7 or warm[0] != core[0] or warm[6] != core[6] or any(not _numeric_equal(warm[i], core[i]) for i in range(1, 6)):
                    conflicts += 1; continue
                native_row = native.get(warm[0])
                if native_row is not None and len(native_row) > 7:
                    if int(Decimal(str(native_row[7]))) != candidate[6]: conflicts += 1
                    else: native_matches[interval] += 1
    if conflicts:
        raise RuntimeError(f"POSTTRADE_PRODUCTION_WARM_OVERLAP_CONFLICT count={conflicts}")
    for interval in ("5m", "1d"):
        if overlaps[interval] < 3: raise RuntimeError(f"insufficient Kraken PostTrade/WARM overlap for {interval}: {overlaps[interval]}")
        if native_matches[interval] < 1: raise RuntimeError(f"missing provider-native trade_count overlap for {interval}")
    return {"status": "PASS", "overlaps": overlaps, "partial_buckets_skipped": partial_skipped, "native_trade_count_matches": native_matches, "conflicts": 0}


def verify_warm_overlap(assets: list[dict], repository_root: Path = Path("."), *, coverage_end_ms: int) -> dict:
    output = {"5m": [], "1d": []}
    for asset in assets:
        output[asset["interval_or_metric"]].extend(json.loads(Path(asset["local_path"]).read_text())["records"])
    result = verify_warm_overlap_records(output, repository_root, coverage_end_ms=coverage_end_ms)
    print("KRAKEN_OHLCVT_WARM_OVERLAP=PASS"); print(f"KRAKEN_OHLCVT_WARM_OVERLAPS={json.dumps(result['overlaps'], sort_keys=True)}"); print(f"KRAKEN_OHLCVT_WARM_PARTIAL_SKIPPED={json.dumps(result['partial_buckets_skipped'], sort_keys=True)}"); print("KRAKEN_OHLCVT_WARM_CONFLICTS=0")
    return result

def _publish_assets(assets: list[dict], source: dict) -> tuple[list[dict], dict]:
    body = f"Immutable Kraken official PostTrade-derived OHLCVT successor; source_mode={SOURCE_MODE}; source_sha256={source['archive_sha256']}; authority={posttrade.ENDPOINT}"
    current = release.release_by_tag(RELEASE_TAG)
    if current is None:
        current = release.gh("/releases", method="POST", payload={"tag_name": RELEASE_TAG, "target_commitish": os.environ.get("GITHUB_SHA", "main"), "name": RELEASE_TAG, "body": body, "draft": True, "prerelease": False})
    if source["archive_sha256"] not in (current.get("body") or ""): raise RuntimeError("Kraken OHLCVT v2 release lineage mismatch")
    if current.get("draft"):
        for asset in assets: release.upload_verified(current, asset)
        current = release.gh(f"/releases/{current['id']}", method="PATCH", payload={"draft": False})
    current = release.gh(f"/releases/{current['id']}")
    if not current.get("immutable"): raise RuntimeError("Kraken OHLCVT v2 release is not immutable")
    remote_by_name = {x["name"]: x for x in release.list_assets(current["id"])}
    if set(remote_by_name) != {x["asset_name"] for x in assets}: raise RuntimeError("Kraken OHLCVT v2 remote inventory mismatch")
    for asset in assets:
        remote = remote_by_name[asset["asset_name"]]
        if remote["size"] != asset["size_bytes"]: raise RuntimeError(f"Kraken OHLCVT v2 remote size mismatch: {asset['asset_name']}")
        if hashlib.sha256(release.download_release_asset(remote["id"])).hexdigest() != asset["sha256"]: raise RuntimeError(f"Kraken OHLCVT v2 remote SHA mismatch: {asset['asset_name']}")
        asset.update({"storage_backend": "GITHUB_RELEASE_ASSET", "release_tag": RELEASE_TAG, "release_id": current["id"], "release_url": current["html_url"], "asset_id": remote["id"], "browser_download_url": remote["browser_download_url"], "content_type": remote["content_type"], "format": "compact-json", "schema_version": SCHEMA, "immutable": True, "integrity_status": "PASS"})
    return assets, current


def merge_release_manifest(current: dict, assets: list[dict], source: dict, published_release: dict) -> dict:
    replaced = {("kraken", "ETHUSD", "5m"), ("kraken", "ETHUSD", "1d")}
    inventory = [x for x in current["asset_inventory"] if (x.get("provider"), x.get("instrument"), x.get("interval_or_metric")) not in replaced]
    inventory.extend({k: v for k, v in x.items() if k != "local_path"} for x in assets)
    inventory.sort(key=lambda x: (x.get("provider", ""), x.get("instrument", ""), x.get("interval_or_metric", ""), x.get("first_timestamp", 0), x.get("asset_name", "")))
    series = [x for x in current["series_inventory"] if (x.get("provider"), x.get("instrument"), x.get("interval_or_metric")) not in replaced]
    for interval in ("5m", "1d"):
        chosen = [x for x in assets if x["interval_or_metric"] == interval]
        series.append({"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": interval, "first_timestamp": min(x["first_timestamp"] for x in chosen), "last_timestamp": max(x["last_timestamp"] for x in chosen), "row_count": sum(x["row_count"] for x in chosen), "asset_count": len(chosen), "release_tag": RELEASE_TAG, "boundary_status": "MAX_AVAILABLE"})
    releases = [x for x in current["release_inventory"] if x.get("release_tag") != RELEASE_TAG]
    releases.append({"release_tag": RELEASE_TAG, "release_id": published_release["id"], "release_url": published_release["html_url"], "immutable": True, "asset_count": len(assets)})
    supplemental = [x for x in current.get("supplemental_frozen_sources", []) if x.get("authority") != source["authority"]] + [source]
    result = dict(current); result.update({"generated_at_utc": source["acquired_at_utc"], "release_inventory": sorted(releases, key=lambda x: x["release_tag"]), "series_inventory": sorted(series, key=lambda x: (x["provider"], x["instrument"], x["interval_or_metric"])), "asset_inventory": inventory, "supplemental_frozen_sources": supplemental})
    integrity = dict(current.get("integrity_summary", {})); integrity.update({"kraken_spot_ohlcvt_full_history": "PASS", "kraken_spot_ohlcvt_gap_policy": "PASS", "kraken_spot_ohlcvt_warm_overlap": "PASS", "kraken_spot_deep_history_source_mode": SOURCE_MODE}); result["integrity_summary"] = integrity
    return result


def qualification_inventory() -> list[dict]:
    inventory = posttrade.build_segment_inventory(QUALIFICATION_START_UTC, QUALIFICATION_END_UTC)
    if len(inventory) != 2 or inventory[0]["requested_end_utc"] != "2017-07-01T00:00:00.000000Z":
        raise RuntimeError("bounded production quarter inventory mismatch")
    return inventory


def qualify_segment_a(output_root: Path) -> dict:
    output_root = Path(output_root); inventory = qualification_inventory(); left = inventory[0]
    retention = posttrade.retention_plan(posttrade.MARKET_INCEPTION_UTC, _iso_ms(_warm_first_timestamp()))
    interrupted_root = output_root / "interrupted"
    try: posttrade.execute_segment(interrupted_root, left, interrupt_after_pages=3)
    except posttrade.SegmentInterrupted: pass
    else: raise RuntimeError("production interruption proof did not interrupt")
    if (interrupted_root / "segments" / left["segment_id"]).exists(): raise RuntimeError("partial production segment became COMPLETE authority")
    restarted = posttrade.execute_segment(output_root / "checkpoint", left); uninterrupted = posttrade.execute_segment(output_root / "uninterrupted", left)
    rdir = Path(restarted["directory"]); udir = Path(uninterrupted["directory"])
    if restarted["evidence"]["frozen_source_digest"] != uninterrupted["evidence"]["frozen_source_digest"] or (rdir / "provider-trade-ids.txt").read_bytes() != (udir / "provider-trade-ids.txt").read_bytes() or (rdir / "segment-output.json").read_bytes() != (udir / "segment-output.json").read_bytes():
        raise RuntimeError("POSTTRADE_PRODUCTION_SEGMENT_RESTART_NONDETERMINISTIC")
    summary = {"inventory": inventory, "left": restarted["evidence"], "retention": retention, "checkpoint_directory": str(rdir)}; (output_root / "qualification-a-summary.json").write_bytes(compact(summary))
    for marker in ("PRODUCTION_POSTTRADE_SOURCE_MODE=PASS", "PRODUCTION_SEGMENT_INVENTORY=PASS", "PRODUCTION_SEGMENT_BOUNDARY=PASS", "PRODUCTION_ATOMIC_SEGMENT_RESTART=PASS", "PRODUCTION_BUILD_A_B=PASS", "PRODUCTION_COMPLETED_SEGMENT_PERSISTENCE=READY", "PRODUCTION_PERSISTENCE_LIFETIME=PASS"): print(marker)
    print(f"PRODUCTION_LEFT_SEGMENT_ID={left['segment_id']}"); print(f"PRODUCTION_LEFT_PAGE_COUNT={restarted['evidence']['page_count']}"); print(f"PRODUCTION_LEFT_RAW_ROWS={restarted['evidence']['raw_row_count']}"); print(f"PRODUCTION_LEFT_UNIQUE_ROWS={restarted['evidence']['unique_trade_count']}")
    print(f"RESTARTED_NORMALIZED_DIGEST={restarted['evidence']['frozen_source_digest']}"); print(f"UNINTERRUPTED_NORMALIZED_DIGEST={uninterrupted['evidence']['frozen_source_digest']}"); print(f"REQUIRED_RETENTION_SECONDS={retention['required_retention_seconds']}"); print(f"CONFIGURED_RETENTION_DAYS={retention['configured_retention_days']}"); print(f"RETENTION_SAFETY_MARGIN_SECONDS={retention['retention_safety_margin_seconds']}")
    return summary


def _copy_completed_segment(source_dir: Path, checkpoint_root: Path, descriptor: dict) -> Path:
    destination = Path(checkpoint_root) / "segments" / descriptor["segment_id"]; destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(source_dir, destination); return destination


def qualify_segment_b(output_root: Path, restored_left: Path, repository_root: Path = Path(".")) -> dict:
    output_root = Path(output_root); inventory = qualification_inventory(); checkpoint_root = output_root / "checkpoint"
    left_dir = _copy_completed_segment(restored_left, checkpoint_root, inventory[0]); chain = posttrade.execute_inventory(checkpoint_root, QUALIFICATION_START_UTC, QUALIFICATION_END_UTC)
    if not chain["results"][0]["reused"]: raise RuntimeError("completed production segment was reacquired instead of resumed")
    right_dir = Path(chain["results"][1]["directory"]); direct = posttrade.execute_segment(output_root / "direct", posttrade.segment_descriptor(QUALIFICATION_START_UTC, QUALIFICATION_END_UTC)); direct_dir = Path(direct["directory"])
    direct_output = json.loads((direct_dir / "segment-output.json").read_text()); segmented_digest = posttrade.output_digest(chain["assembled"]); direct_digest = posttrade.output_digest(direct_output)
    if segmented_digest != direct_digest: raise RuntimeError("POSTTRADE_PRODUCTION_ASSEMBLY_NONDETERMINISTIC")
    left_ids = set((left_dir / "provider-trade-ids.txt").read_text().splitlines()); right_ids = set((right_dir / "provider-trade-ids.txt").read_text().splitlines()); direct_ids = set((direct_dir / "provider-trade-ids.txt").read_text().splitlines())
    conflicts = left_ids & right_ids; missing = direct_ids - (left_ids | right_ids); extra = (left_ids | right_ids) - direct_ids
    if conflicts: raise RuntimeError(f"POSTTRADE_PRODUCTION_TRADE_ID_CONFLICT seam={len(conflicts)}")
    if missing or extra: raise RuntimeError(f"POSTTRADE_PRODUCTION_SEGMENT_SEAM_GAP missing={len(missing)} extra={len(extra)}")
    warm_first_ms = _warm_first_timestamp(repository_root); cutoff_ms = int(json.loads((repository_root / "history" / "release-manifest.json").read_text())["backfill_as_of_ms"]); warm_start_ms = _utc_day_start_ms(warm_first_ms); warm_end_ms = _utc_day_start_ms(min(cutoff_ms, warm_start_ms + WARM_OVERLAP_MS))
    if warm_end_ms <= warm_start_ms: raise RuntimeError("insufficient fully covered UTC-day WARM overlap window")
    warm = posttrade.execute_segment(output_root / "warm", posttrade.segment_descriptor(_iso_ms(warm_start_ms), _iso_ms(warm_end_ms))); warm_output = json.loads((Path(warm["directory"]) / "segment-output.json").read_text()); warm_overlap = verify_warm_overlap_records(warm_output, repository_root, coverage_end_ms=warm_end_ms)
    summary = {"left": chain["results"][0]["evidence"], "right": chain["results"][1]["evidence"], "direct": direct["evidence"], "segmented_output_digest": segmented_digest, "direct_output_digest": direct_digest, "seam_provider_id_conflicts": len(conflicts), "seam_missing_executions": len(missing), "seam_extra_executions": len(extra), "warm": warm["evidence"], "warm_overlap": warm_overlap}; (output_root / "qualification-b-summary.json").write_bytes(compact(summary))
    for marker in ("PRODUCTION_POSTTRADE_PROVIDER_SCHEMA=PASS", "PRODUCTION_PROVIDER_TRADE_ID_CONTINUITY=PASS", "PRODUCTION_CURSOR_MONOTONICITY=PASS", "PRODUCTION_ADJACENT_SEGMENT_SEAM=PASS", "PRODUCTION_SEGMENT_ASSEMBLY=PASS", "PRODUCTION_NO_TRADE_SEMANTICS=PASS", "PRODUCTION_COMPLETED_SEGMENT_PERSISTENCE=PASS"): print(marker)
    print(f"PRODUCTION_RIGHT_PAGE_COUNT={chain['results'][1]['evidence']['page_count']}"); print(f"PRODUCTION_RIGHT_RAW_ROWS={chain['results'][1]['evidence']['raw_row_count']}"); print(f"PRODUCTION_RIGHT_UNIQUE_ROWS={chain['results'][1]['evidence']['unique_trade_count']}"); print(f"SEAM_PROVIDER_ID_CONFLICTS={len(conflicts)}"); print(f"SEAM_MISSING_EXECUTIONS={len(missing)}"); print(f"SEAM_DUPLICATES_AFTER_DEDUP={len(extra)}"); print(f"SEGMENTED_ASSEMBLY_DIGEST={segmented_digest}"); print(f"DIRECT_COMBINED_REFERENCE_DIGEST={direct_digest}"); print("WARM_OVERLAP_CONFLICTS=0"); print(f"WARM_OVERLAPS={json.dumps(warm_overlap['overlaps'], sort_keys=True)}"); print("FULL_2015_TO_WARM_ACQUISITION=NOT_RUN"); print("RELEASE_PUBLICATION=NOT_RUN"); print("CONTROL_PLANE_INSTALL=NOT_RUN")
    return summary


def publish() -> None:
    current = json.loads(Path("history/release-manifest.json").read_text()); cutoff_ms = int(current["backfill_as_of_ms"]); warm_first_ms = _warm_first_timestamp()
    try: source = acquire_archive(cutoff_ms=cutoff_ms, warm_first_ms=warm_first_ms)
    except posttrade.PostTradeIncomplete as exc:
        print(f"KRAKEN_POSTTRADE_BLOCKER={exc}"); print("KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=false"); raise SystemExit(76) from exc
    assets_a = build_assets(ARCHIVE, BUILD_A, cutoff_ms, source); assets_b = build_assets(ARCHIVE, BUILD_B, cutoff_ms, source); compare_builds(assets_a, assets_b); coverage_end_ms = int(posttrade.parse_utc(source['coverage_declared_end_utc']).timestamp() * 1000); verify_warm_overlap(assets_a, coverage_end_ms=coverage_end_ms)
    published_assets, published_release = _publish_assets(assets_a, source); GENERATED.write_bytes(compact(merge_release_manifest(current, published_assets, source, published_release))); print("KRAKEN_OHLCVT_SUCCESSOR_MANIFEST=PASS"); print("KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=pending-control-plane-install")


def install_manifest() -> None:
    if not GENERATED.is_file(): raise RuntimeError("Kraken OHLCVT successor manifest missing")
    Path("history/release-manifest.json").write_bytes(GENERATED.read_bytes()); print("KRAKEN_OHLCVT_CONTROL_PLANE_INSTALL=PASS")


def plan() -> None:
    print(f"KRAKEN_OHLCVT_SOURCE_MODE={SOURCE_MODE}"); print(f"KRAKEN_OHLCVT_SOURCE_SCHEMA={SOURCE_SCHEMA}"); print(f"KRAKEN_OHLCVT_AUTHORITY={posttrade.ENDPOINT}"); print("KRAKEN_OHLCVT_SEGMENTATION=UTC_CALENDAR_QUARTER"); print("KRAKEN_OHLCVT_RESUME_GRANULARITY=COMPLETED_SEGMENT"); print("KRAKEN_OHLCVT_PAGE_LEVEL_CHECKPOINTING=false"); print(f"KRAKEN_OHLCVT_MAX_PARALLEL={posttrade.MAX_PARALLEL}"); print(f"KRAKEN_OHLCVT_RELEASE_TAG={RELEASE_TAG}"); print("KRAKEN_OHLCVT_INTERVALS=5m,1d"); print("KRAKEN_OHLCVT_SYNTHETIC_FILL=false"); print(f"KRAKEN_OHLCVT_GAP_POLICY={GAP_POLICY}")


def _main() -> None:
    if len(os.sys.argv) < 2: raise SystemExit("usage: kraken_spot_ohlcvt_backfill.py plan|publish|install-manifest|qualify-segment-a|qualify-segment-b")
    command = os.sys.argv[1]
    if command == "plan": plan()
    elif command == "publish": publish()
    elif command == "install-manifest": install_manifest()
    elif command == "qualify-segment-a" and len(os.sys.argv) == 3: qualify_segment_a(Path(os.sys.argv[2]))
    elif command == "qualify-segment-b" and len(os.sys.argv) == 4: qualify_segment_b(Path(os.sys.argv[2]), Path(os.sys.argv[3]))
    else: raise SystemExit("invalid command/arguments")


if __name__ == "__main__":
    _main()
