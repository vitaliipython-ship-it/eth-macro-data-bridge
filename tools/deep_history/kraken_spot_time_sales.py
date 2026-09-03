from __future__ import annotations

import binascii
import hashlib
import http.cookiejar
import json
import os
import re
import struct
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

SOURCE_MODE = "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE"
SOURCE_SCHEMA = "kraken-spot-time-sales-source/1.0.0"
SUPPORT_URL = (
    "https://support.kraken.com/articles/360047543791-"
    "downloadable-historical-market-data-time-and-sales-"
)
TRADES_DOC_URL = "https://support.kraken.com/articles/360000919966-api-faqs"
TRADES_ENDPOINT = "https://api.kraken.com/0/public/Trades"
COMPLETE_FILE_ID = "10zh3tDpqANYvVtYVgczwVz3UZFRUb1el"
COMPLETE_FILENAME = "Kraken_Trading_History.zip"
QUARTER_FOLDER_ID = "188O9xQjZTythjyLNes_5zfMEFaMbTT22"
QUARTER_FOLDER_URL = f"https://drive.google.com/drive/mobile/folders/{QUARTER_FOLDER_ID}?usp=sharing"
USER_AGENT = "Mozilla/5.0 eth-macro-data-bridge/1.0"
RANGE_CHUNK = 8 * 1024 * 1024
CENTRAL_DIRECTORY_TAIL = 32 * 1024 * 1024
TARGET_MEMBERS = {"ETHUSD.CSV", "XETHZUSD.CSV"}
INTERVALS = {"5m": 300, "1d": 86400}
DERIVED_MEMBERS = {"5m": "ETHUSD_5.csv", "1d": "ETHUSD_1440.csv"}


class SourceInventoryIncomplete(RuntimeError):
    """Official archive inventory cannot prove contiguous coverage to canonical WARM."""


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(RANGE_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _opener(opener=None):
    if opener is not None:
        return opener
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _confirmed_download_url(raw: bytes) -> str:
    parser = DownloadFormParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
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
    return form["action"] + "?" + urllib.parse.urlencode(form["inputs"])


def _drive_download_url(file_id: str, opener=None) -> tuple[str, object]:
    opener = _opener(opener)
    landing = f"https://drive.google.com/uc?export=download&id={file_id}"
    request = urllib.request.Request(landing, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=120) as response:
        raw = response.read(256 * 1024)
        content_type = response.headers.get("Content-Type") or ""
    if "text/html" in content_type:
        return _confirmed_download_url(raw), opener
    return landing, opener


def _range_read(opener, url: str, start: int, end: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Range": f"bytes={start}-{end}"},
    )
    with opener.open(request, timeout=180) as response:
        raw = response.read(end - start + 2)
        if response.status != 206:
            raise RuntimeError(f"official Kraken Drive range request not honored: status={response.status}")
        if len(raw) != end - start + 1:
            raise RuntimeError(f"official Kraken Drive short range: {len(raw)} != {end - start + 1}")
        return raw


def _zip64_values(extra: bytes, need_uncomp: bool, need_comp: bool, need_offset: bool) -> dict:
    pos = 0
    while pos + 4 <= len(extra):
        field_id, size = struct.unpack_from("<HH", extra, pos)
        pos += 4
        data = extra[pos : pos + size]
        pos += size
        if field_id != 0x0001:
            continue
        values: dict[str, int] = {}
        cursor = 0
        if need_uncomp:
            values["uncompressed_size"], = struct.unpack_from("<Q", data, cursor)
            cursor += 8
        if need_comp:
            values["compressed_size"], = struct.unpack_from("<Q", data, cursor)
            cursor += 8
        if need_offset:
            values["local_offset"], = struct.unpack_from("<Q", data, cursor)
        return values
    return {}


def _inspect_remote_zip(file_id: str, filename: str, opener=None) -> dict:
    url, opener = _drive_download_url(file_id, opener)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=180) as response:
        content_type = response.headers.get("Content-Type") or ""
        if "text/html" in content_type:
            text = response.read(256 * 1024).decode("utf-8", errors="replace")
            if "Quota exceeded" in text or "Too many users have viewed or downloaded" in text:
                raise RuntimeError(f"official Kraken Time & Sales archive quota-blocked: {filename}")
            raise RuntimeError(f"official Kraken Time & Sales archive returned HTML: {filename}")
        length = response.headers.get("Content-Length")
        if not length or not length.isdigit():
            raise RuntimeError(f"official Kraken Time & Sales archive size unavailable: {filename}")
        archive_size = int(length)
        if response.read(4) != b"PK\x03\x04":
            raise RuntimeError(f"official Kraken Time & Sales asset is not ZIP: {filename}")

    tail_size = min(CENTRAL_DIRECTORY_TAIL, archive_size)
    tail = _range_read(opener, url, archive_size - tail_size, archive_size - 1)
    matches: list[dict] = []
    pos = 0
    while True:
        index = tail.find(b"PK\x01\x02", pos)
        if index < 0:
            break
        if index + 46 > len(tail):
            break
        fields = struct.unpack_from("<4s6H3I5H2I", tail, index)
        method = fields[4]
        crc32_value = fields[7]
        compressed_size = fields[8]
        uncompressed_size = fields[9]
        name_length, extra_length, comment_length = fields[10], fields[11], fields[12]
        local_offset = fields[16]
        stop = index + 46 + name_length + extra_length + comment_length
        if stop > len(tail):
            pos = index + 4
            continue
        name = tail[index + 46 : index + 46 + name_length].decode("utf-8", errors="strict")
        extra = tail[index + 46 + name_length : index + 46 + name_length + extra_length]
        zip64 = _zip64_values(
            extra,
            uncompressed_size == 0xFFFFFFFF,
            compressed_size == 0xFFFFFFFF,
            local_offset == 0xFFFFFFFF,
        )
        uncompressed_size = zip64.get("uncompressed_size", uncompressed_size)
        compressed_size = zip64.get("compressed_size", compressed_size)
        local_offset = zip64.get("local_offset", local_offset)
        if name.split("/")[-1].upper() in TARGET_MEMBERS:
            matches.append(
                {
                    "member_name": name,
                    "compression_method": method,
                    "crc32": crc32_value,
                    "compressed_size": compressed_size,
                    "uncompressed_size": uncompressed_size,
                    "local_offset": local_offset,
                }
            )
        pos = stop
    if len(matches) != 1:
        raise RuntimeError(f"expected one ETHUSD Time & Sales member in {filename}, found {matches}")
    member = matches[0]
    if member["compression_method"] != 8:
        raise RuntimeError(f"unsupported Kraken Time & Sales ZIP compression method: {member['compression_method']}")
    local = _range_read(opener, url, member["local_offset"], member["local_offset"] + 29)
    signature, _, _, method, _, _, _, _, _, name_length, extra_length = struct.unpack("<4s5H3I2H", local)
    if signature != b"PK\x03\x04" or method != member["compression_method"]:
        raise RuntimeError(f"Kraken Time & Sales local header mismatch: {filename}")
    member.update(
        {
            "file_id": file_id,
            "filename": filename,
            "archive_size_bytes": archive_size,
            "download_url": url,
            "data_offset": member["local_offset"] + 30 + name_length + extra_length,
        }
    )
    return member


def discover_quarterly_archives(opener=None) -> list[dict]:
    opener = _opener(opener)
    request = urllib.request.Request(QUARTER_FOLDER_URL, headers={"User-Agent": USER_AGENT})
    with opener.open(request, timeout=120) as response:
        text = response.read().decode("utf-8", errors="replace")
    pattern = re.compile(
        r'data-id="([A-Za-z0-9_-]+)".{0,1200}?data-tooltip="(Kraken_Trading_History_Q([1-4])_(\d{4})\.zip)',
        re.DOTALL,
    )
    found: dict[str, dict] = {}
    for match in pattern.finditer(text):
        file_id, filename, quarter, year = match.groups()
        found[filename] = {
            "file_id": file_id,
            "filename": filename,
            "quarter": int(quarter),
            "year": int(year),
        }
    if not found:
        raise RuntimeError("official Kraken quarterly Time & Sales inventory is empty/unparseable")
    return sorted(found.values(), key=lambda item: (item["year"], item["quarter"]))


def _freeze_member(descriptor: dict, destination: Path, opener=None) -> dict:
    opener = _opener(opener)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    remaining = int(descriptor["compressed_size"])
    cursor = int(descriptor["data_offset"])
    temp = destination.with_suffix(destination.suffix + ".partial")
    try:
        with temp.open("wb") as output:
            while remaining:
                take = min(RANGE_CHUNK, remaining)
                raw = _range_read(opener, descriptor["download_url"], cursor, cursor + take - 1)
                output.write(raw)
                digest.update(raw)
                cursor += take
                remaining -= take
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    result = dict(descriptor)
    result.pop("download_url", None)
    result["compressed_sha256"] = digest.hexdigest()
    result["frozen_path"] = str(destination)
    return result


def acquire_frozen_sources(root: Path, opener=None) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    opener = _opener(opener)
    sources: list[dict] = []

    complete = _inspect_remote_zip(COMPLETE_FILE_ID, COMPLETE_FILENAME, opener)
    sources.append(_freeze_member(complete, root / "complete.deflate", opener))

    quarterly = discover_quarterly_archives(opener)
    # The physically qualified complete source currently reaches the end of 2025.
    # Download only successor incremental partitions; older quarter files are already
    # represented by the complete source and must not be replayed as duplicate trades.
    for item in quarterly:
        if item["year"] < 2026:
            continue
        descriptor = _inspect_remote_zip(item["file_id"], item["filename"], opener)
        descriptor.update({"quarter": item["quarter"], "year": item["year"]})
        name = f"{item['year']}-Q{item['quarter']}.deflate"
        sources.append(_freeze_member(descriptor, root / name, opener))

    source_set = [
        {
            key: value
            for key, value in source.items()
            if key not in {"frozen_path", "local_offset", "data_offset"}
        }
        for source in sources
    ]
    metadata = {
        "schema_version": SOURCE_SCHEMA,
        "source_mode": SOURCE_MODE,
        "authority": "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE",
        "support_url": SUPPORT_URL,
        "trades_documentation": TRADES_DOC_URL,
        "trades_endpoint": TRADES_ENDPOINT,
        "authentication_required": False,
        "pair_identity": "ETHUSD",
        "provider_result_identity": "XETHZUSD",
        "acquired_at_utc": _utc_now(),
        "file_ids": [source["file_id"] for source in sources],
        "source_members": source_set,
        "archive_sha256": hashlib.sha256(_compact(source_set)).hexdigest(),
        "archive_size_bytes": sum(int(source["compressed_size"]) for source in sources),
        "raw_source_count": len(sources),
        "gap_policy": "PROVIDER_NO_TRADE_OMISSION",
        "synthetic_fill": False,
    }
    (root / "source.json").write_bytes(_compact(metadata))
    return {"metadata": metadata, "sources": sources}


def _quarter_bounds_ms(year: int, quarter: int) -> tuple[int, int]:
    month = 1 + (quarter - 1) * 3
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if quarter == 4:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 3, 1, tzinfo=timezone.utc)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _iter_trades(source: dict):
    path = Path(source["frozen_path"])
    if _sha256_file(path) != source["compressed_sha256"]:
        raise RuntimeError(f"frozen Kraken source digest mismatch: {source['filename']}")
    decompressor = zlib.decompressobj(-15)
    crc = 0
    uncompressed_size = 0
    pending = b""
    first_line = True
    previous_timestamp: Decimal | None = None
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(RANGE_CHUNK)
            if not chunk:
                break
            decoded = decompressor.decompress(chunk)
            crc = binascii.crc32(decoded, crc)
            uncompressed_size += len(decoded)
            pending += decoded
            lines = pending.split(b"\n")
            pending = lines.pop()
            for raw in lines:
                if not raw.strip():
                    continue
                text = raw.decode("ascii")
                parts = text.split(",")
                if len(parts) != 3:
                    raise RuntimeError(f"invalid Kraken Time & Sales row width in {source['filename']}: {text!r}")
                try:
                    timestamp = Decimal(parts[0])
                    price = Decimal(parts[1])
                    volume = Decimal(parts[2])
                except InvalidOperation as exc:
                    if first_line:
                        first_line = False
                        continue
                    raise RuntimeError(f"invalid Kraken Time & Sales numeric row: {text!r}") from exc
                first_line = False
                if not timestamp.is_finite() or not price.is_finite() or not volume.is_finite():
                    raise RuntimeError("non-finite Kraken Time & Sales value")
                if price <= 0 or volume < 0:
                    raise RuntimeError("invalid Kraken Time & Sales price/volume")
                if previous_timestamp is not None and timestamp < previous_timestamp:
                    raise RuntimeError(f"Kraken Time & Sales timestamp regression in {source['filename']}")
                previous_timestamp = timestamp
                yield timestamp, price, volume
        decoded = decompressor.flush()
        crc = binascii.crc32(decoded, crc)
        uncompressed_size += len(decoded)
        pending += decoded
    if pending.strip():
        parts = pending.strip().decode("ascii").split(",")
        if len(parts) != 3:
            raise RuntimeError(f"invalid Kraken Time & Sales final row in {source['filename']}")
        timestamp, price, volume = map(Decimal, parts)
        if previous_timestamp is not None and timestamp < previous_timestamp:
            raise RuntimeError(f"Kraken Time & Sales timestamp regression in {source['filename']}")
        yield timestamp, price, volume
    if uncompressed_size != int(source["uncompressed_size"]):
        raise RuntimeError(
            f"Kraken Time & Sales uncompressed size mismatch: {uncompressed_size} != {source['uncompressed_size']}"
        )
    if crc & 0xFFFFFFFF != int(source["crc32"]):
        raise RuntimeError(f"Kraken Time & Sales CRC mismatch: {source['filename']}")


def _format_decimal(value: Decimal) -> str:
    return format(value, "f")


def _new_bucket(bucket: int, price: Decimal, volume: Decimal) -> dict:
    return {
        "bucket": bucket,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": volume,
        "trade_count": 1,
    }


def _update_bucket(state: dict, price: Decimal, volume: Decimal) -> None:
    state["high"] = max(state["high"], price)
    state["low"] = min(state["low"], price)
    state["close"] = price
    state["volume"] += volume
    state["trade_count"] += 1


def _emit_bucket(stream, state: dict) -> None:
    stream.write(
        ",".join(
            [
                str(state["bucket"]),
                _format_decimal(state["open"]),
                _format_decimal(state["high"]),
                _format_decimal(state["low"]),
                _format_decimal(state["close"]),
                _format_decimal(state["volume"]),
                str(state["trade_count"]),
            ]
        )
        + "\n"
    )


def derive_ohlcvt_archive(frozen: dict, destination: Path, cutoff_ms: int) -> dict:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    csv_paths = {interval: destination.parent / f".{destination.name}.{interval}.csv" for interval in INTERVALS}
    streams = {interval: path.open("w", encoding="ascii", newline="") for interval, path in csv_paths.items()}
    states: dict[str, dict | None] = {interval: None for interval in INTERVALS}
    row_counts = {interval: 0 for interval in INTERVALS}
    first_trade_ms: int | None = None
    latest_trade_ms: int | None = None
    previous_global_timestamp: Decimal | None = None
    complete_latest_ms: int | None = None
    coverage_declared_end_ms: int | None = None
    quarter_keys: list[tuple[int, int]] = []

    try:
        for index, source in enumerate(frozen["sources"]):
            quarter_bounds = None
            if source.get("year") and source.get("quarter"):
                quarter_bounds = _quarter_bounds_ms(int(source["year"]), int(source["quarter"]))
                quarter_keys.append((int(source["year"]), int(source["quarter"])))
            source_first_ms = None
            source_latest_ms = None
            for timestamp, price, volume in _iter_trades(source):
                timestamp_ms = int(timestamp * 1000)
                if timestamp_ms >= cutoff_ms:
                    continue
                if previous_global_timestamp is not None and timestamp < previous_global_timestamp:
                    raise RuntimeError("Kraken Time & Sales source partition ordering regression")
                previous_global_timestamp = timestamp
                if quarter_bounds and not (quarter_bounds[0] <= timestamp_ms < quarter_bounds[1]):
                    raise RuntimeError(
                        f"Kraken Time & Sales row outside declared quarter {source['filename']}: {timestamp_ms}"
                    )
                source_first_ms = timestamp_ms if source_first_ms is None else source_first_ms
                source_latest_ms = timestamp_ms
                first_trade_ms = timestamp_ms if first_trade_ms is None else first_trade_ms
                latest_trade_ms = timestamp_ms
                for interval, step_seconds in INTERVALS.items():
                    bucket = (int(timestamp) // step_seconds) * step_seconds
                    state = states[interval]
                    if state is None:
                        states[interval] = _new_bucket(bucket, price, volume)
                    elif bucket == state["bucket"]:
                        _update_bucket(state, price, volume)
                    elif bucket > state["bucket"]:
                        _emit_bucket(streams[interval], state)
                        row_counts[interval] += 1
                        states[interval] = _new_bucket(bucket, price, volume)
                    else:
                        raise RuntimeError("Kraken Time & Sales bucket ordering regression")
            if source_first_ms is None or source_latest_ms is None:
                raise RuntimeError(f"Kraken Time & Sales source produced no rows: {source['filename']}")
            if index == 0:
                complete_latest_ms = source_latest_ms
                coverage_declared_end_ms = source_latest_ms + 1
            else:
                assert quarter_bounds is not None
                if complete_latest_ms is not None and source_first_ms <= complete_latest_ms:
                    raise RuntimeError("Kraken Time & Sales complete/quarter source overlap")
                coverage_declared_end_ms = max(coverage_declared_end_ms or 0, quarter_bounds[1])
        for interval, state in states.items():
            if state is not None:
                _emit_bucket(streams[interval], state)
                row_counts[interval] += 1
    finally:
        for stream in streams.values():
            stream.close()

    if first_trade_ms is None or latest_trade_ms is None:
        raise RuntimeError("Kraken Time & Sales produced no canonical trades")

    import zipfile

    temp = destination.with_suffix(destination.suffix + ".partial")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for interval in ("5m", "1d"):
                info = zipfile.ZipInfo(DERIVED_MEMBERS[interval], date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                archive.writestr(info, csv_paths[interval].read_bytes())
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
        for path in csv_paths.values():
            path.unlink(missing_ok=True)

    result = {
        "source_mode": SOURCE_MODE,
        "derived_archive_sha256": _sha256_file(destination),
        "derived_archive_size_bytes": destination.stat().st_size,
        "first_trade_ms": first_trade_ms,
        "latest_trade_ms": latest_trade_ms,
        "complete_latest_ms": complete_latest_ms,
        "coverage_declared_end_ms": coverage_declared_end_ms,
        "quarter_partitions": [f"{year}-Q{quarter}" for year, quarter in quarter_keys],
        "row_counts": row_counts,
    }
    return result


def assert_source_covers_warm(derived: dict, warm_first_ms: int) -> None:
    coverage_end = int(derived["coverage_declared_end_ms"])
    if coverage_end < int(warm_first_ms):
        raise SourceInventoryIncomplete(
            "official Kraken Time & Sales inventory does not cover canonical M5 WARM boundary: "
            f"declared_end={coverage_end} warm_first={warm_first_ms} "
            f"quarters={derived['quarter_partitions']}"
        )


def compare_derived_archives(left: Path, right: Path) -> None:
    left_sha = _sha256_file(left)
    right_sha = _sha256_file(right)
    if left_sha != right_sha:
        raise RuntimeError(f"Kraken Time & Sales deterministic derivation mismatch: {left_sha} != {right_sha}")


def frozen_source_set_digest(frozen: dict) -> str:
    normalized = [
        {
            key: value
            for key, value in source.items()
            if key not in {"frozen_path", "local_offset", "data_offset"}
        }
        for source in frozen["sources"]
    ]
    return hashlib.sha256(_compact(normalized)).hexdigest()
