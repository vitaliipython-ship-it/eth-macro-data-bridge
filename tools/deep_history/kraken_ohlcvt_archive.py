from __future__ import annotations

import argparse
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

try:
    from . import release_publisher as rp
except ImportError:
    import release_publisher as rp

TAG = "history-kraken-spot-v2"
DRIVE_FILE_ID = "1ptNqWYidLkhb2VAKuLCxmp2OXEfGO-AP"
SUPPORT_URL = "https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data"
TARGET = {"5m": 5, "1d": 1440}
COLUMNS = ["open_time_ms", "open", "high", "low", "close", "volume", "close_time_ms"]
ROOT = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / "kraken-full-ohlcvt"
BUILD = ROOT / "build"
GENERATED = ROOT / "release-manifest.generated.json"


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(8 * 1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def year_start_ms(year: int) -> int:
    return int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def decimal_text(value) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RuntimeError(f"invalid Kraken OHLCVT decimal: {value!r}") from exc
    if not number.is_finite():
        raise RuntimeError(f"non-finite Kraken OHLCVT decimal: {value!r}")
    text = format(number, "f")
    return "0" if Decimal(text) == 0 else text


def member_for(zf: zipfile.ZipFile, minutes: int) -> str:
    expected = f"ETHUSD_{minutes}.csv".upper()
    matches = [name for name in zf.namelist() if Path(name).name.upper() == expected]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {expected} in Kraken archive, found {matches}")
    return matches[0]


def parse_member(archive: Path, interval: str) -> tuple[list[list], str]:
    minutes = TARGET[interval]
    step = minutes * 60_000
    with zipfile.ZipFile(archive) as zf:
        member = member_for(zf, minutes)
        with zf.open(member) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            rows = []
            seen = set()
            for fields in reader:
                if not fields:
                    continue
                try:
                    ts_raw = int(fields[0])
                except ValueError:
                    if not rows:
                        continue
                    raise RuntimeError(f"non-numeric timestamp inside {member}: {fields[:2]!r}")
                if len(fields) < 7:
                    raise RuntimeError(f"invalid Kraken OHLCVT row width in {member}: {len(fields)}")
                ts = ts_raw * 1000 if ts_raw < 10**12 else ts_raw
                if ts in seen:
                    raise RuntimeError(f"duplicate Kraken OHLCVT timestamp in {member}: {ts}")
                seen.add(ts)
                o, h, l, c, v = [decimal_text(value) for value in fields[1:6]]
                od, hd, ld, cd, vd = map(Decimal, (o, h, l, c, v))
                if hd < max(od, ld, cd) or ld > min(od, hd, cd) or vd < 0:
                    raise RuntimeError(f"invalid Kraken OHLCVT candle in {member}: {ts}")
                rows.append([ts, o, h, l, c, v, ts + step - 1])
    timestamps = [row[0] for row in rows]
    if not rows or timestamps != sorted(timestamps):
        raise RuntimeError(f"Kraken archive member not strictly ordered/non-empty: {member}")
    return rows, member


def old_kraken_assets(manifest: dict) -> list[dict]:
    assets = [dict(item) for item in manifest.get("asset_inventory", []) if item.get("provider") == "kraken"]
    if not assets:
        raise RuntimeError("existing Kraken release inventory missing")
    return assets


def download_old_assets(assets: list[dict]) -> list[dict]:
    copied = []
    target = BUILD / "copied"
    target.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        raw = rp.download_release_asset(int(asset["asset_id"]))
        if len(raw) != int(asset["size_bytes"]) or sha_bytes(raw) != asset["sha256"]:
            raise RuntimeError(f"existing Kraken release asset integrity mismatch: {asset['asset_name']}")
        path = target / Path(asset["asset_name"]).name
        path.write_bytes(raw)
        item = dict(asset)
        item["local_path"] = str(path)
        copied.append(item)
    return copied


def old_rows(copied: list[dict], interval: str) -> tuple[dict[int, list], int | None]:
    rows = {}
    first = None
    for asset in copied:
        if asset.get("instrument") != "ETHUSD" or asset.get("interval_or_metric") != interval:
            continue
        payload = json.loads(Path(asset["local_path"]).read_text())
        columns = payload["columns"]
        aliases = {
            "open_time_ms": ("open_time_ms", "timestamp_ms"),
            "open": ("open",), "high": ("high",), "low": ("low",), "close": ("close",),
            "volume": ("volume", "base_volume"),
        }
        positions = {}
        for key, candidates in aliases.items():
            positions[key] = next((columns.index(name) for name in candidates if name in columns), None)
            if positions[key] is None:
                raise RuntimeError(f"existing Kraken target column missing: {interval} {key}")
        for record in payload["records"]:
            ts = int(record[positions["open_time_ms"]])
            normalized = [ts] + [decimal_text(record[positions[name]]) for name in ("open", "high", "low", "close", "volume")]
            previous = rows.get(ts)
            if previous is not None and previous != normalized:
                raise RuntimeError(f"conflicting existing Kraken tail row: {interval} {ts}")
            rows[ts] = normalized
            first = ts if first is None else min(first, ts)
    return rows, first


def verify_overlap(archive_rows: list[list], tail_rows: dict[int, list], interval: str) -> int:
    matched = 0
    for row in archive_rows:
        previous = tail_rows.get(row[0])
        if previous is None:
            continue
        if previous != row[:6]:
            raise RuntimeError(f"Kraken archive/REST overlap conflict: {interval} {row[0]}")
        matched += 1
    return matched


def build_archive_assets(archive: Path, copied: list[dict], archive_sha: str) -> tuple[list[dict], dict]:
    generated = []
    proof = {"archive_sha256": archive_sha, "members": {}, "overlap_rows": {}}
    target_dir = BUILD / "archive"
    target_dir.mkdir(parents=True, exist_ok=True)
    for interval, minutes in TARGET.items():
        rows, member = parse_member(archive, interval)
        tail_rows, tail_first = old_rows(copied, interval)
        matched = verify_overlap(rows, tail_rows, interval)
        step = minutes * 60_000
        archive_end = rows[-1][0] + step
        if tail_first is not None and tail_first < archive_end:
            coverage_end = tail_first
            rows = [row for row in rows if row[0] < tail_first]
        else:
            coverage_end = archive_end
        if not rows:
            raise RuntimeError(f"Kraken archive adds no predecessor history for ETHUSD {interval}")
        coverage_start = rows[0][0]
        proof["members"][interval] = member
        proof["overlap_rows"][interval] = matched
        grouped = defaultdict(list)
        for row in rows:
            grouped[datetime.fromtimestamp(row[0] / 1000, timezone.utc).year].append(row)
        for year, records in sorted(grouped.items()):
            logical_start = max(coverage_start, year_start_ms(year))
            logical_end = min(coverage_end, year_start_ms(year + 1))
            if logical_end <= logical_start:
                continue
            payload = {
                "schema_version": "1.0.0", "provider": "kraken", "instrument": "ETHUSD",
                "interval_or_metric": interval, "columns": COLUMNS, "partitioning": "yearly",
                "period": str(year), "closed_only": True, "records": records,
            }
            raw = compact(payload) + b"\n"
            name = f"kraken-full--ETHUSD--{interval}--{year}.json"
            path = target_dir / name
            path.write_bytes(raw)
            generated.append({
                "local_path": str(path), "asset_name": name, "provider": "kraken", "instrument": "ETHUSD",
                "interval_or_metric": interval, "first_timestamp": logical_start, "last_timestamp": logical_end - step,
                "row_count": len(records), "partitioning": "yearly", "closed_only": True,
                "size_bytes": len(raw), "sha256": sha_bytes(raw), "canonical_source_sha256": sha_bytes(compact(records)),
                "retrieved_at_utc": iso_now(), "source_route": SUPPORT_URL,
                "historical_availability": "MAX_AVAILABLE", "provider_history_limit": False, "known_gaps": [],
                "boundary_proof": {
                    "requested_start": 0, "earliest_accepted_timestamp": coverage_start,
                    "last_timestamp": coverage_end - step, "record_first_timestamp": records[0][0],
                    "record_last_timestamp": records[-1][0], "logical_coverage_start_ms": logical_start,
                    "logical_coverage_end_ms": logical_end, "provider_more_exhausted": True,
                    "boundary_status": "MAX_AVAILABLE", "coverage_semantics": "TRADES_ONLY_SPARSE",
                    "source_route": SUPPORT_URL, "google_drive_file_id": DRIVE_FILE_ID,
                    "archive_sha256": archive_sha, "archive_member": member, "overlap_rows_verified": matched,
                },
            })
    return generated, proof


def rebuild_series_inventory(assets: list[dict]) -> list[dict]:
    series = {}
    for asset in assets:
        key = (asset["provider"], asset["instrument"], asset["interval_or_metric"])
        item = series.setdefault(key, {
            "provider": key[0], "instrument": key[1], "interval_or_metric": key[2],
            "first_timestamp": asset["first_timestamp"], "last_timestamp": asset["last_timestamp"],
            "row_count": 0, "asset_count": 0, "release_tag": asset["release_tag"],
            "boundary_status": asset.get("boundary_proof", {}).get("boundary_status", "PROVIDER_HISTORY_LIMIT"),
        })
        if item["release_tag"] != asset["release_tag"]:
            raise RuntimeError(f"multiple release tags in one semantic series: {key}")
        item["first_timestamp"] = min(item["first_timestamp"], asset["first_timestamp"])
        item["last_timestamp"] = max(item["last_timestamp"], asset["last_timestamp"])
        item["row_count"] += int(asset["row_count"])
        item["asset_count"] += 1
        if asset.get("historical_availability") == "MAX_AVAILABLE":
            item["boundary_status"] = "MAX_AVAILABLE"
    return [series[key] for key in sorted(series)]


def build_manifest(archive: Path) -> tuple[dict, dict]:
    old = json.loads(Path("history/release-manifest.json").read_text())
    copied = download_old_assets(old_kraken_assets(old))
    archive_sha = sha_path(archive)
    extra, proof = build_archive_assets(archive, copied, archive_sha)
    chosen = copied + extra
    body = (
        "Immutable Kraken Spot successor history; official complete Kraken OHLCVT archive; "
        f"legacy_cutoff={rp.AS_OF_UTC}; drive_file_id={DRIVE_FILE_ID}; source_commit={os.environ.get('GITHUB_SHA','unknown')}"
    )
    release = rp.create_or_get_draft(TAG, body)
    if not release.get("draft") and not release.get("immutable"):
        raise RuntimeError("published Kraken successor release is not immutable")
    if release.get("draft"):
        for asset in chosen:
            rp.upload_verified(release, asset)
        remote = {item["name"]: item for item in rp.list_assets(release["id"])}
        for asset in chosen:
            item = remote.get(asset["asset_name"])
            if not item or item["size"] != asset["size_bytes"]:
                raise RuntimeError(f"draft Kraken successor inventory mismatch: {asset['asset_name']}")
        release = rp.gh(f"/releases/{release['id']}", method="PATCH", payload={"draft": False})
    release = rp.gh(f"/releases/{release['id']}")
    if not release.get("immutable"):
        raise RuntimeError("Kraken successor release immutability proof failed")
    remote = {item["name"]: item for item in rp.list_assets(release["id"])}
    for asset in chosen:
        item = remote.get(asset["asset_name"])
        if not item:
            raise RuntimeError(f"published Kraken successor asset missing: {asset['asset_name']}")
        raw = rp.download_release_asset(item["id"])
        if len(raw) != asset["size_bytes"] or sha_bytes(raw) != asset["sha256"]:
            raise RuntimeError(f"published Kraken successor read-back mismatch: {asset['asset_name']}")
        asset.update({
            "storage_backend": "GITHUB_RELEASE_ASSET", "release_tag": TAG, "release_id": release["id"],
            "release_url": release["html_url"], "asset_id": item["id"],
            "browser_download_url": item["browser_download_url"], "content_type": item["content_type"],
            "format": "compact-json", "schema_version": "1.0.0", "immutable": True, "integrity_status": "PASS",
        })
    non_kraken = [dict(item) for item in old["asset_inventory"] if item.get("provider") != "kraken"]
    inventory = non_kraken + [{key: value for key, value in item.items() if key != "local_path"} for item in chosen]
    releases = [dict(item) for item in old.get("release_inventory", []) if item.get("release_tag") != "history-kraken-spot-v1"]
    releases.append({"release_tag": TAG, "release_id": release["id"], "release_url": release["html_url"], "immutable": True, "asset_count": len(chosen)})
    manifest = dict(old)
    manifest["generated_at_utc"] = iso_now()
    manifest["release_inventory"] = releases
    manifest["series_inventory"] = rebuild_series_inventory(inventory)
    manifest["asset_inventory"] = inventory
    summary = dict(manifest.get("integrity_summary", {}))
    summary.update({
        "kraken_full_ohlcvt_archive": "PASS", "kraken_archive_sha256": archive_sha,
        "kraken_archive_overlap_5m": proof["overlap_rows"].get("5m", 0),
        "kraken_archive_overlap_1d": proof["overlap_rows"].get("1d", 0), "synthetic_gap_fill": 0,
    })
    manifest["integrity_summary"] = summary
    return manifest, proof


def plan(archive: Path) -> None:
    if not archive.is_file():
        raise RuntimeError(f"Kraken OHLCVT archive missing: {archive}")
    size = archive.stat().st_size
    free = shutil.disk_usage(ROOT.parent).free
    if free < size * 2 + 1_000_000_000:
        raise RuntimeError(f"insufficient runner disk for Kraken archive: free={free} archive={size}")
    with zipfile.ZipFile(archive) as zf:
        members = {interval: member_for(zf, minutes) for interval, minutes in TARGET.items()}
    print(f"KRAKEN_ARCHIVE_PLAN=PASS\nARCHIVE_BYTES={size}\nARCHIVE_SHA256={sha_path(archive)}\nMEMBERS={json.dumps(members,sort_keys=True)}\nSYNTHETIC_GAP_FILL=0")


def publish(archive: Path) -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    manifest, proof = build_manifest(archive)
    GENERATED.parent.mkdir(parents=True, exist_ok=True)
    GENERATED.write_bytes(compact(manifest) + b"\n")
    print("KRAKEN_FULL_OHLCVT_RELEASE=PASS")
    print(f"RELEASE_TAG={TAG}")
    print(f"OVERLAP_5M={proof['overlap_rows'].get('5m',0)}")
    print(f"OVERLAP_1D={proof['overlap_rows'].get('1d',0)}")
    print("SYNTHETIC_GAP_FILL=0")


def install_manifest() -> None:
    if not GENERATED.is_file():
        raise RuntimeError("generated Kraken successor release manifest missing")
    Path("history/release-manifest.json").write_bytes(GENERATED.read_bytes())
    print("KRAKEN_CONTROL_PLANE_INSTALL=PASS\nRAW_ARCHIVE_BYTES_IN_GIT=0")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish official Kraken full OHLCVT as canonical COLD successor")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "publish"):
        command = sub.add_parser(name)
        command.add_argument("--archive", required=True)
    sub.add_parser("install-manifest")
    args = parser.parse_args(argv)
    if args.command == "plan":
        plan(Path(args.archive))
    elif args.command == "publish":
        publish(Path(args.archive))
    else:
        install_manifest()


if __name__ == "__main__":
    main()
