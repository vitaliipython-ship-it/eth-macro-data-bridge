from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from tools.deep_history import kraken_spot_rest_trades as rest_trades
from tools.deep_history import kraken_spot_time_sales as time_sales
from tools.deep_history import release_publisher as release

SCHEMA = "1.0.0"
SOURCE_SCHEMA = "kraken-spot-hybrid-trade-source/1.0.0"
SOURCE_MODE = "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL"
GAP_POLICY = "PROVIDER_NO_TRADE_OMISSION"
SUPPORT_URL = time_sales.SUPPORT_URL
FILE_ID = time_sales.COMPLETE_FILE_ID
LANDING_URL = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
RELEASE_TAG = "history-kraken-spot-v2"
TARGETS = {
    "5m": {"minutes": 5, "aliases": ("ETHUSD_5.csv", "XETHZUSD_5.csv")},
    "1d": {"minutes": 1440, "aliases": ("ETHUSD_1440.csv", "XETHZUSD_1440.csv")},
}
COLUMNS = [
    "open_time_ms",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade_count",
    "close_time_ms",
]
ROOT = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / "kraken-spot-ohlcvt-v2"
FROZEN_SOURCE_ROOT = ROOT / "source" / "time-sales"
REST_SOURCE_ROOT = ROOT / "source" / "rest-trades"
ARCHIVE_ONLY = ROOT / "source" / "kraken-timesales-derived-ohlcvt.zip"
REST_OVERLAP_ARCHIVE = ROOT / "source" / "kraken-rest-overlap-derived-ohlcvt.zip"
REST_TAIL_ARCHIVE = ROOT / "source" / "kraken-rest-tail-derived-ohlcvt.zip"
ARCHIVE = ROOT / "source" / "kraken-hybrid-derived-ohlcvt.zip"
SOURCE_META = ROOT / "source" / "source.json"
BUILD_A = ROOT / "build-a"
BUILD_B = ROOT / "build-b"
GENERATED = ROOT / "release-manifest.generated.json"
REST_WARM_OVERLAP_MS = 4 * 86_400_000


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _warm_first_timestamp(repository_root: Path = Path(".")) -> int:
    root = Path(repository_root) / "history" / "kraken" / "ETHUSD" / "5m"
    timestamps: list[int] = []
    for path in sorted(root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("records", []):
            if row:
                timestamps.append(int(row[0]))
    if not timestamps:
        raise RuntimeError("canonical Kraken ETHUSD M5 WARM boundary is unavailable")
    return min(timestamps)


def _rest_tail_end_ms(cutoff_ms: int, warm_first_ms: int) -> int:
    return min(int(cutoff_ms), int(warm_first_ms) + REST_WARM_OVERLAP_MS)


def acquire_archive(
    destination: Path = ARCHIVE,
    *,
    cutoff_ms: int,
    warm_first_ms: int,
    opener=None,
) -> dict:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    inventory = time_sales.discover_quarterly_archives(opener)
    frozen = time_sales.acquire_frozen_sources(FROZEN_SOURCE_ROOT, opener)
    archive_derived = time_sales.derive_ohlcvt_archive(frozen, ARCHIVE_ONLY, cutoff_ms)
    archive_latest_ns = int(archive_derived["latest_trade_ns"])
    rest_start_ns = max(0, archive_latest_ns - rest_trades.OVERLAP_NS)
    rest_end_ms = _rest_tail_end_ms(cutoff_ms, warm_first_ms)
    rest_end_ns = rest_end_ms * 1_000_000
    if rest_end_ns <= archive_latest_ns:
        raise RuntimeError("Kraken REST tail target does not extend beyond archive authority")

    rest_frozen = rest_trades.acquire_frozen_tail(
        REST_SOURCE_ROOT,
        start_ns=rest_start_ns,
        end_ns=rest_end_ns,
        opener=opener,
    )
    rest_trades.derive_ohlcvt_archive(rest_frozen, REST_OVERLAP_ARCHIVE, cutoff_ms)
    seam_overlap = rest_trades.verify_archive_overlap(
        ARCHIVE_ONLY,
        REST_OVERLAP_ARCHIVE,
        archive_latest_ns,
    )
    if int(rest_frozen["metadata"]["coverage_end_ns"]) < int(warm_first_ms) * 1_000_000:
        raise rest_trades.RestTailIncomplete(
            "Kraken REST tail does not reach canonical M5 WARM boundary"
        )
    rest_trades.derive_ohlcvt_archive(
        rest_frozen,
        REST_TAIL_ARCHIVE,
        cutoff_ms,
        min_exclusive_ns=archive_latest_ns,
    )
    merged = rest_trades.merge_derived_archives(
        ARCHIVE_ONLY,
        REST_TAIL_ARCHIVE,
        destination,
    )

    archive_meta = frozen["metadata"]
    rest_meta = rest_frozen["metadata"]
    hybrid_material = {
        "archive_component_sha256": archive_meta["archive_sha256"],
        "rest_tail_source_sha256": rest_meta["frozen_source_sha256"],
        "seam_overlap": seam_overlap,
        "derived_archive_sha256": merged["derived_archive_sha256"],
    }
    hybrid_sha = hashlib.sha256(compact(hybrid_material)).hexdigest()
    source = dict(archive_meta)
    source.update(
        {
            "schema_version": SOURCE_SCHEMA,
            "source_mode": SOURCE_MODE,
            "authority": "KRAKEN_OFFICIAL_TIME_SALES_PLUS_REST_TRADES",
            "source_routes": [time_sales.SUPPORT_URL, rest_trades.ENDPOINT],
            "backfill_cutoff_ms": cutoff_ms,
            "canonical_warm_first_ms": warm_first_ms,
            "archive_component_sha256": archive_meta["archive_sha256"],
            "archive_sha256": hybrid_sha,
            "archive_size_bytes": (
                int(archive_meta["archive_size_bytes"])
                + Path(rest_frozen["frames_path"]).stat().st_size
                + Path(rest_frozen["rows_path"]).stat().st_size
            ),
            "derived_archive_sha256": merged["derived_archive_sha256"],
            "derived_archive_size_bytes": destination.stat().st_size,
            "earliest_canonical_trade_ms": archive_derived["first_trade_ms"],
            "latest_frozen_trade_ms": int(rest_meta["latest_trade_ns"]) // 1_000_000,
            "archive_latest_trade_ns": archive_latest_ns,
            "coverage_declared_end_ms": rest_end_ms,
            "rest_tail_coverage_end_ms": rest_end_ms,
            "quarter_partitions": archive_derived["quarter_partitions"],
            "derived_row_counts": merged["row_counts"],
            "quarter_inventory": [
                {
                    "year": int(item["year"]),
                    "quarter": int(item["quarter"]),
                    "filename": item["filename"],
                    "file_id": item["file_id"],
                }
                for item in inventory
            ],
            "rest_tail_source_sha256": rest_meta["frozen_source_sha256"],
            "rest_tail_raw_pages_sha256": rest_meta["raw_pages_frame_sha256"],
            "rest_tail_rows_sha256": rest_meta["normalized_rows_sha256"],
            "rest_tail_page_count": rest_meta["page_count"],
            "rest_tail_row_count": rest_meta["row_count"],
            "rest_tail_requested_start_ns": rest_meta["requested_start_ns"],
            "rest_tail_requested_end_ns": rest_meta["requested_end_ns"],
            "rest_tail_final_cursor": rest_meta["final_cursor"],
            "rest_tail_cursor_monotonic": rest_meta["cursor_monotonic"],
            "rest_tail_rows_monotonic": rest_meta["rows_monotonic"],
            "source_seam_overlap": seam_overlap,
            "source_seam_bucket_merge": merged["seam_buckets"],
            "acquired_at_utc": rest_meta["acquired_at_utc"],
        }
    )
    SOURCE_META.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_META.write_bytes(compact(source))
    print(f"KRAKEN_OHLCVT_SOURCE_MODE={SOURCE_MODE}")
    print(f"KRAKEN_OHLCVT_EARLIEST_TRADE_MS={source['earliest_canonical_trade_ms']}")
    print(f"KRAKEN_OHLCVT_HYBRID_SOURCE_SHA256={source['archive_sha256']}")
    print(f"KRAKEN_REST_TAIL_PAGES={source['rest_tail_page_count']}")
    return source


def _member_for_interval(names: Iterable[str], interval: str) -> str:
    aliases = TARGETS[interval]["aliases"]
    matches = [name for name in names if any(name.upper().endswith(alias.upper()) for alias in aliases)]
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
    rows: dict[int, list] = {}
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
            raise RuntimeError(f"invalid Kraken OHLCVT timestamp at line {line_number}")
        if source_timestamp != source_timestamp.to_integral_value():
            raise RuntimeError(f"fractional Kraken OHLCVT timestamp at line {line_number}")
        timestamp = int(source_timestamp)
        timestamp_ms = timestamp * 1000 if timestamp < 10**12 else timestamp
        close_time_ms = timestamp_ms + step - 1
        if close_time_ms >= cutoff_ms:
            continue
        alignment = min(step, 86_400_000)
        if timestamp_ms % alignment:
            raise RuntimeError(f"unaligned Kraken OHLCVT timestamp at line {line_number}: {timestamp_ms}")
        values = [_decimal(raw[index], f"line={line_number} column={index}") for index in range(1, 6)]
        try:
            trades_decimal = Decimal(raw[6].strip())
        except InvalidOperation as exc:
            raise RuntimeError(f"invalid Kraken trade_count at line {line_number}") from exc
        if trades_decimal != trades_decimal.to_integral_value() or trades_decimal < 0:
            raise RuntimeError(f"invalid Kraken trade_count at line {line_number}")
        o, h, low, close, volume = map(Decimal, values)
        if h < max(o, low, close) or low > min(o, h, close) or volume < 0:
            raise RuntimeError(f"invalid Kraken OHLCVT candle at {timestamp_ms}")
        row = [timestamp_ms, *values, int(trades_decimal), close_time_ms]
        existing = rows.get(timestamp_ms)
        if existing is not None and existing != row:
            raise RuntimeError(f"conflicting Kraken OHLCVT timestamp {timestamp_ms}")
        rows[timestamp_ms] = row
    if not rows:
        raise RuntimeError(f"Kraken OHLCVT {interval} produced no closed rows")
    return [rows[key] for key in sorted(rows)]


def gap_summary(rows: list[list], step: int) -> dict:
    gaps = [right[0] - left[0] for left, right in zip(rows, rows[1:]) if right[0] - left[0] > step]
    missing = sum(delta // step - 1 for delta in gaps)
    return {
        "policy": GAP_POLICY,
        "synthetic_fill": False,
        "gap_events": len(gaps),
        "missing_intervals": missing,
    }


def _asset_descriptor(
    path: Path,
    interval: str,
    period: str,
    records: list[list],
    summary: dict,
    source: dict,
) -> dict:
    return {
        "local_path": str(path),
        "asset_name": path.name,
        "provider": "kraken",
        "instrument": "ETHUSD",
        "interval_or_metric": interval,
        "first_timestamp": records[0][0],
        "last_timestamp": records[-1][0],
        "row_count": len(records),
        "partitioning": "yearly",
        "closed_only": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "canonical_source_sha256": hashlib.sha256(compact(records)).hexdigest(),
        "retrieved_at_utc": source["acquired_at_utc"],
        "source_route": SUPPORT_URL,
        "historical_availability": "MAX_AVAILABLE",
        "provider_history_limit": False,
        "known_gaps": [],
        "gap_semantics": summary,
        "boundary_proof": {
            "requested_start": 0,
            "earliest_accepted_timestamp": records[0][0],
            "last_timestamp": records[-1][0],
            "pagination_pages": 1,
            "provider_more_exhausted": True,
            "boundary_status": "MAX_AVAILABLE",
            "source_route": SUPPORT_URL,
            "source_mode": SOURCE_MODE,
            "source_archive_sha256": source["archive_sha256"],
            "source_archive_size_bytes": source["archive_size_bytes"],
            "source_archive_file_ids": source["file_ids"],
            "archive_component_sha256": source["archive_component_sha256"],
            "rest_tail_source_sha256": source["rest_tail_source_sha256"],
            "rest_tail_page_count": source["rest_tail_page_count"],
            "source_seam_overlap": source["source_seam_overlap"],
            "derived_archive_sha256": source["derived_archive_sha256"],
            "source_member_period": period,
            "gap_policy": GAP_POLICY,
            "synthetic_fill": False,
        },
        "metric_semantics": None,
    }


def build_assets(archive_path: Path, output_root: Path, cutoff_ms: int, source: dict) -> list[dict]:
    assets: list[dict] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        for interval in ("5m", "1d"):
            member = _member_for_interval(names, interval)
            info = archive.getinfo(member)
            with archive.open(info) as stream:
                rows = parse_ohlcvt(stream, interval, cutoff_ms)
            grouped: dict[str, list[list]] = defaultdict(list)
            for row in rows:
                grouped[datetime.fromtimestamp(row[0] / 1000, timezone.utc).strftime("%Y")].append(row)
            step = TARGETS[interval]["minutes"] * 60 * 1000
            for period, records in sorted(grouped.items()):
                summary = gap_summary(records, step)
                name = f"kraken--ETHUSD--{interval}--{period}.json"
                path = Path(output_root) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "schema_version": SCHEMA,
                    "provider": "kraken",
                    "instrument": "ETHUSD",
                    "interval_or_metric": interval,
                    "columns": COLUMNS,
                    "partitioning": "yearly",
                    "period": period,
                    "closed_only": True,
                    "source_semantics": "KRAKEN_TIME_SALES_PLUS_REST_TRADES_DERIVED_OHLCVT",
                    "gap_semantics": summary,
                    "records": records,
                }
                path.write_bytes(compact(payload))
                if path.stat().st_size > 64 * 1024 * 1024:
                    raise RuntimeError(f"Kraken OHLCVT asset exceeds 64 MiB: {name}")
                assets.append(_asset_descriptor(path, interval, period, records, summary, source))
    return sorted(assets, key=lambda item: item["asset_name"])


def compare_builds(left: list[dict], right: list[dict]) -> None:
    left_map = {item["asset_name"]: item["sha256"] for item in left}
    right_map = {item["asset_name"]: item["sha256"] for item in right}
    if left_map != right_map:
        raise RuntimeError("Kraken OHLCVT deterministic build mismatch")
    print(f"KRAKEN_OHLCVT_DETERMINISM=PASS assets={len(left_map)}")


def _numeric_equal(left, right) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def verify_warm_overlap(assets: list[dict], repository_root: Path = Path(".")) -> dict:
    full: dict[str, dict[int, list]] = {"5m": {}, "1d": {}}
    for asset in assets:
        payload = json.loads(Path(asset["local_path"]).read_text(encoding="utf-8"))
        full[asset["interval_or_metric"]].update({row[0]: row for row in payload["records"]})

    overlaps = {"5m": 0, "1d": 0}
    native_trade_count_matches = {"5m": 0, "1d": 0}
    conflicts = 0
    for interval in ("5m", "1d"):
        root = repository_root / "history" / "kraken" / "ETHUSD" / interval
        for path in sorted(root.rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            native = {row[0]: row for row in payload.get("provider_native_records", [])}
            for warm in payload.get("records", []):
                candidate = full[interval].get(warm[0])
                if candidate is None:
                    continue
                overlaps[interval] += 1
                core = [candidate[0], candidate[1], candidate[2], candidate[3], candidate[4], candidate[5], candidate[7]]
                if len(warm) < 7 or warm[0] != core[0] or warm[6] != core[6]:
                    conflicts += 1
                    continue
                if any(not _numeric_equal(warm[index], core[index]) for index in range(1, 6)):
                    conflicts += 1
                    continue
                native_row = native.get(warm[0])
                if native_row is not None and len(native_row) > 7:
                    if int(Decimal(str(native_row[7]))) != candidate[6]:
                        conflicts += 1
                    else:
                        native_trade_count_matches[interval] += 1
    if conflicts:
        raise RuntimeError(f"Kraken OHLCVT/WARM overlap conflict count={conflicts}")
    for interval in ("5m", "1d"):
        if overlaps[interval] < 3:
            raise RuntimeError(f"insufficient Kraken OHLCVT/WARM overlap for {interval}: {overlaps[interval]}")
        if native_trade_count_matches[interval] < 1:
            raise RuntimeError(f"missing provider-native trade_count overlap for {interval}")
    result = {
        "status": "PASS",
        "overlaps": overlaps,
        "native_trade_count_matches": native_trade_count_matches,
        "conflicts": conflicts,
    }
    print("KRAKEN_OHLCVT_WARM_OVERLAP=PASS")
    print(f"KRAKEN_OHLCVT_WARM_OVERLAPS={json.dumps(overlaps, sort_keys=True)}")
    print("KRAKEN_OHLCVT_WARM_CONFLICTS=0")
    return result


def _publish_assets(assets: list[dict], source: dict) -> tuple[list[dict], dict]:
    body = (
        "Immutable Kraken official Time & Sales + bounded REST Trades tail-derived OHLCVT successor; "
        f"source_mode={SOURCE_MODE}; source_sha256={source['archive_sha256']}; authority={SUPPORT_URL}"
    )
    current = release.release_by_tag(RELEASE_TAG)
    if current is None:
        current = release.gh(
            "/releases",
            method="POST",
            payload={
                "tag_name": RELEASE_TAG,
                "target_commitish": os.environ.get("GITHUB_SHA", "main"),
                "name": RELEASE_TAG,
                "body": body,
                "draft": True,
                "prerelease": False,
            },
        )
    if source["archive_sha256"] not in (current.get("body") or ""):
        raise RuntimeError("Kraken OHLCVT v2 release lineage mismatch")

    if current.get("draft"):
        for asset in assets:
            release.upload_verified(current, asset)
        current = release.gh(f"/releases/{current['id']}", method="PATCH", payload={"draft": False})
    current = release.gh(f"/releases/{current['id']}")
    if not current.get("immutable"):
        raise RuntimeError("Kraken OHLCVT v2 release is not immutable")

    remote_by_name = {item["name"]: item for item in release.list_assets(current["id"])}
    if set(remote_by_name) != {item["asset_name"] for item in assets}:
        raise RuntimeError("Kraken OHLCVT v2 remote inventory mismatch")
    for asset in assets:
        remote = remote_by_name[asset["asset_name"]]
        if remote["size"] != asset["size_bytes"]:
            raise RuntimeError(f"Kraken OHLCVT v2 remote size mismatch: {asset['asset_name']}")
        raw = release.download_release_asset(remote["id"])
        if hashlib.sha256(raw).hexdigest() != asset["sha256"]:
            raise RuntimeError(f"Kraken OHLCVT v2 remote SHA mismatch: {asset['asset_name']}")
        asset.update(
            {
                "storage_backend": "GITHUB_RELEASE_ASSET",
                "release_tag": RELEASE_TAG,
                "release_id": current["id"],
                "release_url": current["html_url"],
                "asset_id": remote["id"],
                "browser_download_url": remote["browser_download_url"],
                "content_type": remote["content_type"],
                "format": "compact-json",
                "schema_version": SCHEMA,
                "immutable": True,
                "integrity_status": "PASS",
            }
        )
    print("KRAKEN_OHLCVT_REMOTE_READBACK=PASS")
    return assets, current


def merge_release_manifest(current: dict, assets: list[dict], source: dict, published_release: dict) -> dict:
    replaced = {("kraken", "ETHUSD", "5m"), ("kraken", "ETHUSD", "1d")}
    inventory = [
        item
        for item in current["asset_inventory"]
        if (item.get("provider"), item.get("instrument"), item.get("interval_or_metric")) not in replaced
    ]
    inventory.extend({key: value for key, value in item.items() if key != "local_path"} for item in assets)
    inventory.sort(
        key=lambda item: (
            item.get("provider", ""),
            item.get("instrument", ""),
            item.get("interval_or_metric", ""),
            item.get("first_timestamp", 0),
            item.get("asset_name", ""),
        )
    )

    series = [
        item
        for item in current["series_inventory"]
        if (item.get("provider"), item.get("instrument"), item.get("interval_or_metric")) not in replaced
    ]
    for interval in ("5m", "1d"):
        chosen = [item for item in assets if item["interval_or_metric"] == interval]
        series.append(
            {
                "provider": "kraken",
                "instrument": "ETHUSD",
                "interval_or_metric": interval,
                "first_timestamp": min(item["first_timestamp"] for item in chosen),
                "last_timestamp": max(item["last_timestamp"] for item in chosen),
                "row_count": sum(item["row_count"] for item in chosen),
                "asset_count": len(chosen),
                "release_tag": RELEASE_TAG,
                "boundary_status": "MAX_AVAILABLE",
            }
        )
    series.sort(key=lambda item: (item["provider"], item["instrument"], item["interval_or_metric"]))

    releases = [item for item in current["release_inventory"] if item.get("release_tag") != RELEASE_TAG]
    releases.append(
        {
            "release_tag": RELEASE_TAG,
            "release_id": published_release["id"],
            "release_url": published_release["html_url"],
            "immutable": True,
            "asset_count": len(assets),
        }
    )
    releases.sort(key=lambda item: item["release_tag"])

    supplemental = list(current.get("supplemental_frozen_sources", []))
    supplemental = [item for item in supplemental if item.get("authority") != source["authority"]]
    supplemental.append(source)

    result = dict(current)
    result["generated_at_utc"] = source["acquired_at_utc"]
    result["release_inventory"] = releases
    result["series_inventory"] = series
    result["asset_inventory"] = inventory
    result["supplemental_frozen_sources"] = supplemental
    integrity = dict(current.get("integrity_summary", {}))
    integrity.update(
        {
            "kraken_spot_ohlcvt_full_history": "PASS",
            "kraken_spot_ohlcvt_gap_policy": "PASS",
            "kraken_spot_ohlcvt_warm_overlap": "PASS",
            "kraken_spot_deep_history_source_mode": SOURCE_MODE,
        }
    )
    result["integrity_summary"] = integrity
    return result


def publish() -> None:
    current_manifest = json.loads(Path("history/release-manifest.json").read_text(encoding="utf-8"))
    cutoff_ms = int(current_manifest["backfill_as_of_ms"])
    warm_first_ms = _warm_first_timestamp()
    try:
        source = acquire_archive(cutoff_ms=cutoff_ms, warm_first_ms=warm_first_ms)
    except rest_trades.RestTailIncomplete as exc:
        print("KRAKEN_REST_TRADES_TAIL=INCOMPLETE")
        print(f"KRAKEN_REST_TRADES_BLOCKER={exc}")
        print("KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=false")
        raise SystemExit(76) from exc

    assets_a = build_assets(ARCHIVE, BUILD_A, cutoff_ms, source)
    assets_b = build_assets(ARCHIVE, BUILD_B, cutoff_ms, source)
    compare_builds(assets_a, assets_b)
    verify_warm_overlap(assets_a)
    published_assets, published_release = _publish_assets(assets_a, source)
    successor = merge_release_manifest(current_manifest, published_assets, source, published_release)
    GENERATED.write_bytes(compact(successor))
    print("KRAKEN_OHLCVT_SUCCESSOR_MANIFEST=PASS")
    print("KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=pending-control-plane-install")


def install_manifest() -> None:
    if not GENERATED.is_file():
        raise RuntimeError("Kraken OHLCVT successor manifest missing")
    Path("history/release-manifest.json").write_bytes(GENERATED.read_bytes())
    print("KRAKEN_OHLCVT_CONTROL_PLANE_INSTALL=PASS")


def plan() -> None:
    print(f"KRAKEN_OHLCVT_SOURCE_MODE={SOURCE_MODE}")
    print(f"KRAKEN_OHLCVT_AUTHORITY={SUPPORT_URL}")
    print(f"KRAKEN_OHLCVT_COMPLETE_FILE_ID={FILE_ID}")
    print(f"KRAKEN_OHLCVT_QUARTER_FOLDER_ID={time_sales.QUARTER_FOLDER_ID}")
    print(f"KRAKEN_OHLCVT_REST_TAIL_ENDPOINT={rest_trades.ENDPOINT}")
    print(f"KRAKEN_OHLCVT_REST_TAIL_OVERLAP_NS={rest_trades.OVERLAP_NS}")
    print(f"KRAKEN_OHLCVT_REST_WARM_OVERLAP_MS={REST_WARM_OVERLAP_MS}")
    print(f"KRAKEN_OHLCVT_RELEASE_TAG={RELEASE_TAG}")
    print("KRAKEN_OHLCVT_INTERVALS=5m,1d")
    print("KRAKEN_OHLCVT_SYNTHETIC_FILL=false")
    print(f"KRAKEN_OHLCVT_GAP_POLICY={GAP_POLICY}")


if __name__ == "__main__":
    commands = {"plan": plan, "publish": publish, "install-manifest": install_manifest}
    if len(os.sys.argv) != 2 or os.sys.argv[1] not in commands:
        raise SystemExit("usage: kraken_spot_ohlcvt_backfill.py plan|publish|install-manifest")
    commands[os.sys.argv[1]]()
