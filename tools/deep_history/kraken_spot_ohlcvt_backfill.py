from __future__ import annotations

import csv
import hashlib
import http.cookiejar
import io
import json
import os
import shutil
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from tools.deep_history import release_publisher as release

SCHEMA = "1.0.0"
SOURCE_SCHEMA = "kraken-spot-ohlcvt-source/1.0.0"
GAP_POLICY = "PROVIDER_NO_TRADE_OMISSION"
SUPPORT_URL = (
    "https://support.kraken.com/articles/360047124832-"
    "downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data"
)
FILE_ID = "1ptNqWYidLkhb2VAKuLCxmp2OXEfGO-AP"
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
ARCHIVE = ROOT / "source" / "kraken-ohlcvt-complete.zip"
SOURCE_META = ROOT / "source" / "source.json"
BUILD_A = ROOT / "build-a"
BUILD_B = ROOT / "build-b"
GENERATED = ROOT / "release-manifest.generated.json"
MIN_FREE_MARGIN = 2 * 1024 * 1024 * 1024


class UpstreamQuotaBlocked(RuntimeError):
    """Official Kraken Drive authority is temporarily quota-blocked."""


class DownloadFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self._current: dict | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "form":
            self._current = {
                "action": values.get("action"),
                "method": values.get("method", "get").lower(),
                "inputs": {},
            }
            self.forms.append(self._current)
        elif tag == "input" and self._current is not None and values.get("name"):
            self._current["inputs"][values["name"]] = values.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current = None


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _confirmed_download_url(html: bytes) -> str:
    parser = DownloadFormParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    form = next(
        (
            item
            for item in parser.forms
            if item.get("action") and "download" in item["action"] and item.get("method") == "get"
        ),
        None,
    )
    if form is None:
        raise RuntimeError("official Kraken Drive confirmation form missing")
    required = {"id", "export", "confirm", "uuid"}
    if not required <= set(form["inputs"]):
        raise RuntimeError("official Kraken Drive confirmation fields incomplete")
    return form["action"] + "?" + urllib.parse.urlencode(form["inputs"])


def _classify_html_response(raw: bytes) -> None:
    text = raw.decode("utf-8", errors="replace")
    if "Quota exceeded" in text or "Too many users have viewed or downloaded" in text:
        raise UpstreamQuotaBlocked("official Kraken OHLCVT Google Drive asset is quota-blocked")
    raise RuntimeError("official Kraken OHLCVT download returned unexpected HTML")


def acquire_archive(destination: Path = ARCHIVE, opener=None) -> dict:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    jar = http.cookiejar.CookieJar()
    opener = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    headers = {"User-Agent": "Mozilla/5.0 eth-macro-data-bridge/1.0"}

    landing_request = urllib.request.Request(LANDING_URL, headers=headers)
    with opener.open(landing_request, timeout=120) as response:
        landing = response.read(128 * 1024)
        if "text/html" not in (response.headers.get("Content-Type") or ""):
            raise RuntimeError("official Kraken Drive landing response changed unexpectedly")
    download_url = _confirmed_download_url(landing)

    request = urllib.request.Request(download_url, headers=headers)
    with opener.open(request, timeout=180) as response:
        content_type = response.headers.get("Content-Type") or ""
        if "text/html" in content_type:
            _classify_html_response(response.read(128 * 1024))
        content_length = response.headers.get("Content-Length")
        expected_size = int(content_length) if content_length and content_length.isdigit() else None
        free = shutil.disk_usage(destination.parent).free
        if expected_size is not None and free < expected_size + MIN_FREE_MARGIN:
            raise RuntimeError(
                f"insufficient runner disk for Kraken OHLCVT archive: free={free} required={expected_size + MIN_FREE_MARGIN}"
            )
        digest = hashlib.sha256()
        size = 0
        temp = destination.with_suffix(destination.suffix + ".partial")
        try:
            with temp.open("wb") as output:
                while True:
                    chunk = response.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if expected_size is not None and size != expected_size:
                raise RuntimeError(f"Kraken OHLCVT archive size mismatch: {size} != {expected_size}")
            os.replace(temp, destination)
        finally:
            temp.unlink(missing_ok=True)

    if not zipfile.is_zipfile(destination):
        raise RuntimeError("official Kraken OHLCVT response is not a ZIP archive")
    metadata = {
        "schema_version": SOURCE_SCHEMA,
        "authority": "KRAKEN_OFFICIAL_DOWNLOADABLE_OHLCVT",
        "support_url": SUPPORT_URL,
        "file_id": FILE_ID,
        "landing_url": LANDING_URL,
        "acquired_at_utc": _utc_now(),
        "archive_sha256": digest.hexdigest(),
        "archive_size_bytes": size,
    }
    SOURCE_META.write_bytes(compact(metadata))
    return metadata


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


def _asset_descriptor(path: Path, interval: str, period: str, records: list[list], summary: dict, source: dict) -> dict:
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
            "source_archive_sha256": source["archive_sha256"],
            "source_archive_size_bytes": source["archive_size_bytes"],
            "source_archive_file_id": FILE_ID,
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
            # archive.open() validates the member CRC while the stream is consumed completely.
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
                    "source_semantics": "KRAKEN_OHLCVT",
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
        "Immutable Kraken official downloadable OHLCVT full-history successor; "
        f"source_sha256={source['archive_sha256']}; authority={SUPPORT_URL}"
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
        }
    )
    result["integrity_summary"] = integrity
    return result


def publish() -> None:
    current_manifest = json.loads(Path("history/release-manifest.json").read_text(encoding="utf-8"))
    cutoff_ms = int(current_manifest["backfill_as_of_ms"])
    try:
        source = acquire_archive()
    except UpstreamQuotaBlocked as exc:
        print("KRAKEN_OHLCVT_UPSTREAM=QUOTA_BLOCKED")
        print("KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=false")
        raise SystemExit(75) from exc

    source["backfill_cutoff_ms"] = cutoff_ms
    SOURCE_META.write_bytes(compact(source))
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
    print(f"KRAKEN_OHLCVT_AUTHORITY={SUPPORT_URL}")
    print(f"KRAKEN_OHLCVT_FILE_ID={FILE_ID}")
    print(f"KRAKEN_OHLCVT_RELEASE_TAG={RELEASE_TAG}")
    print("KRAKEN_OHLCVT_INTERVALS=5m,1d")
    print("KRAKEN_OHLCVT_SYNTHETIC_FILL=false")
    print(f"KRAKEN_OHLCVT_GAP_POLICY={GAP_POLICY}")


if __name__ == "__main__":
    commands = {"plan": plan, "publish": publish, "install-manifest": install_manifest}
    if len(os.sys.argv) != 2 or os.sys.argv[1] not in commands:
        raise SystemExit("usage: kraken_spot_ohlcvt_backfill.py plan|publish|install-manifest")
    commands[os.sys.argv[1]]()
