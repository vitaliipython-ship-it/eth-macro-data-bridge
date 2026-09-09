from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

SOURCE_MODE = "KRAKEN_OFFICIAL_REST_TRADES_TAIL"
SOURCE_SCHEMA = "kraken-spot-rest-trades-tail/1.1.0"
ENDPOINT = "https://api.kraken.com/0/public/Trades"
DOCUMENTATION = "https://docs.kraken.com/api-reference/market-data/get-recent-trades"
PAIR = "ETHUSD"
RESULT_ID = "XETHZUSD"
USER_AGENT = "eth-macro-data-bridge-rest-tail/1.0"
OVERLAP_NS = 2 * 86_400 * 1_000_000_000
REQUEST_DELAY_SECONDS = float(os.environ.get("KRAKEN_REST_TRADES_DELAY_SECONDS", "1.0"))
MAX_PAGES = 20_000
MAX_RETRIES = 8
FRAME = struct.Struct(">Q")
TRADE_ID_INDEX = 6
TRADE_ROW_MIN_WIDTH = TRADE_ID_INDEX + 1
INTERVALS = {"5m": 300, "1d": 86_400}
DERIVED_MEMBERS = {"5m": "ETHUSD_5.csv", "1d": "ETHUSD_1440.csv"}


class RestTailIncomplete(RuntimeError):
    """Official REST Trades pagination cannot prove the requested bounded tail."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal(value, context: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RestTailIncomplete(f"invalid Kraken REST decimal {context}: {value!r}") from exc
    if not result.is_finite():
        raise RestTailIncomplete(f"non-finite Kraken REST decimal {context}: {value!r}")
    return result


def _timestamp_ns(value) -> int:
    timestamp = _decimal(value, "timestamp")
    scaled = timestamp * Decimal(1_000_000_000)
    if scaled != scaled.to_integral_value():
        raise RestTailIncomplete(f"Kraken REST timestamp exceeds nanosecond precision: {value!r}")
    result = int(scaled)
    if result < 0:
        raise RestTailIncomplete(f"negative Kraken REST timestamp: {value!r}")
    return result


def _trade_id(value, context: str) -> int:
    if isinstance(value, bool):
        raise RestTailIncomplete(f"invalid Kraken REST trade id {context}: {value!r}")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise RestTailIncomplete(f"invalid Kraken REST trade id {context}: {value!r}") from exc
    if result < 0 or str(value).strip() != str(result):
        raise RestTailIncomplete(f"invalid Kraken REST trade id {context}: {value!r}")
    return result


def _provider_row_fingerprint(row: list) -> tuple[str, ...]:
    return tuple(format(value, "f") if isinstance(value, Decimal) else str(value) for value in row)


def _open(opener, request):
    if opener is None:
        return urllib.request.urlopen(request, timeout=30)
    return opener.open(request, timeout=30)


def _request_page(cursor: int, opener=None, sleep_fn=time.sleep) -> tuple[bytes, list, int]:
    query = urllib.parse.urlencode({"pair": PAIR, "since": str(cursor), "count": "1000"})
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with _open(opener, request) as response:
                raw = response.read()
            payload = json.loads(raw.decode("utf-8"), parse_float=Decimal)
            if payload.get("error"):
                raise RestTailIncomplete(f"Kraken REST errors={payload['error']}")
            result = payload.get("result")
            if not isinstance(result, dict):
                raise RestTailIncomplete("Kraken REST result is not an object")
            keys = [key for key in result if key != "last"]
            if keys != [RESULT_ID]:
                raise RestTailIncomplete(f"unexpected Kraken REST pair identity: {keys}")
            rows = result[RESULT_ID]
            next_cursor = int(result["last"])
            if not rows:
                raise RestTailIncomplete(f"Kraken REST empty page before target end at cursor={cursor}")
            if next_cursor <= cursor:
                raise RestTailIncomplete(f"Kraken REST cursor did not advance: {cursor}->{next_cursor}")
            return raw, rows, next_cursor
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, RestTailIncomplete) as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            sleep_fn(min(3 * attempt, 15))
    raise RestTailIncomplete(f"Kraken REST page failed after retries: {last_error!r}")


def acquire_frozen_tail(
    root: Path,
    *,
    start_ns: int,
    end_ns: int,
    opener=None,
    sleep_fn=time.sleep,
    delay_seconds: float = REQUEST_DELAY_SECONDS,
) -> dict:
    if start_ns < 0 or end_ns <= start_ns:
        raise ValueError("invalid Kraken REST tail range")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    frames_path = root / "rest-pages.bin"
    rows_path = root / "rest-trades.csv"
    cursor = start_ns
    previous_timestamp_ns = None
    dedup_timestamp_ns = None
    seen_trade_ids_at_timestamp: dict[int, tuple[str, ...]] = {}
    first_stored_ns = None
    latest_stored_ns = None
    first_trade_id = None
    latest_trade_id = None
    raw_row_count = 0
    row_count = 0
    duplicate_trade_id_count = 0
    page_count = 0
    crossed_end = False
    transcript = hashlib.sha256()

    with frames_path.open("wb") as frames, rows_path.open("w", encoding="ascii", newline="") as rows_stream:
        writer = csv.writer(rows_stream, lineterminator="\n")
        while page_count < MAX_PAGES:
            raw, rows, next_cursor = _request_page(cursor, opener=opener, sleep_fn=sleep_fn)
            page_count += 1
            body_sha = hashlib.sha256(raw).hexdigest()
            transcript.update(
                _compact(
                    {
                        "body_sha256": body_sha,
                        "cursor": str(cursor),
                        "next": str(next_cursor),
                        "page": page_count,
                    }
                )
            )
            frames.write(FRAME.pack(len(raw)))
            frames.write(raw)
            for index, row in enumerate(rows):
                if not isinstance(row, list) or len(row) < TRADE_ROW_MIN_WIDTH:
                    raise RestTailIncomplete(
                        f"invalid Kraken REST trade row page={page_count} index={index} width="
                        f"{len(row) if isinstance(row, list) else 'non-list'}"
                    )
                price = _decimal(row[0], "price")
                volume = _decimal(row[1], "volume")
                timestamp = _decimal(row[2], "timestamp")
                trade_id = _trade_id(row[TRADE_ID_INDEX], f"page={page_count} index={index}")
                if price <= 0 or volume < 0:
                    raise RestTailIncomplete("invalid Kraken REST price/volume")
                timestamp_ns = _timestamp_ns(timestamp)
                if previous_timestamp_ns is not None and timestamp_ns < previous_timestamp_ns:
                    raise RestTailIncomplete("Kraken REST trade timestamp regression")
                previous_timestamp_ns = timestamp_ns

                if dedup_timestamp_ns != timestamp_ns:
                    dedup_timestamp_ns = timestamp_ns
                    seen_trade_ids_at_timestamp = {}
                fingerprint = _provider_row_fingerprint(row)
                duplicate = seen_trade_ids_at_timestamp.get(trade_id)
                if duplicate is None:
                    seen_trade_ids_at_timestamp[trade_id] = fingerprint
                elif duplicate != fingerprint:
                    raise RestTailIncomplete(
                        f"Kraken REST trade id conflict at timestamp={timestamp_ns} trade_id={trade_id}"
                    )

                if timestamp_ns >= end_ns:
                    crossed_end = True
                    continue
                if timestamp_ns < start_ns:
                    continue
                raw_row_count += 1
                if duplicate is not None:
                    duplicate_trade_id_count += 1
                    continue

                writer.writerow(
                    [
                        format(timestamp, "f"),
                        format(price, "f"),
                        format(volume, "f"),
                        str(trade_id),
                    ]
                )
                first_stored_ns = timestamp_ns if first_stored_ns is None else first_stored_ns
                latest_stored_ns = timestamp_ns
                first_trade_id = trade_id if first_trade_id is None else first_trade_id
                latest_trade_id = trade_id
                row_count += 1
            cursor = next_cursor
            if crossed_end:
                break
            if delay_seconds > 0:
                sleep_fn(delay_seconds)
        else:
            raise RestTailIncomplete(f"Kraken REST tail exceeded MAX_PAGES={MAX_PAGES}")

    if not crossed_end:
        raise RestTailIncomplete("Kraken REST pagination did not physically cross requested end")
    if row_count == 0 or first_stored_ns is None or latest_stored_ns is None:
        raise RestTailIncomplete("Kraken REST frozen tail contains no rows")
    if raw_row_count != row_count + duplicate_trade_id_count:
        raise RuntimeError("Kraken REST duplicate accounting invariant failed")

    material = {
        "schema_version": SOURCE_SCHEMA,
        "source_mode": SOURCE_MODE,
        "authority": "KRAKEN_OFFICIAL_REST_TRADES",
        "endpoint": ENDPOINT,
        "documentation": DOCUMENTATION,
        "authentication_required": False,
        "pair_identity": PAIR,
        "provider_result_identity": RESULT_ID,
        "provider_trade_id_field_index": TRADE_ID_INDEX,
        "page_overlap_deduplication": "EXACT_PROVIDER_TRADE_ID_AT_EQUAL_TIMESTAMP",
        "requested_start_ns": start_ns,
        "requested_end_ns": end_ns,
        "coverage_end_ns": end_ns,
        "first_trade_ns": first_stored_ns,
        "latest_trade_ns": latest_stored_ns,
        "first_trade_id": first_trade_id,
        "latest_trade_id": latest_trade_id,
        "page_count": page_count,
        "raw_row_count": raw_row_count,
        "row_count": row_count,
        "duplicate_trade_id_count": duplicate_trade_id_count,
        "final_cursor": str(cursor),
        "cursor_monotonic": True,
        "rows_monotonic": True,
        "raw_pages_frame_sha256": _sha256_file(frames_path),
        "normalized_rows_sha256": _sha256_file(rows_path),
        "page_transcript_sha256": transcript.hexdigest(),
        "gap_policy": "PROVIDER_NO_TRADE_OMISSION",
        "synthetic_fill": False,
        "acquired_at_utc": _utc_now(),
    }
    material["frozen_source_sha256"] = hashlib.sha256(_compact(material)).hexdigest()
    (root / "source.json").write_bytes(_compact(material))
    return {"metadata": material, "frames_path": str(frames_path), "rows_path": str(rows_path)}


def _iter_frozen_trades(frozen: dict, *, min_exclusive_ns: int | None = None):
    metadata = frozen["metadata"]
    rows_path = Path(frozen["rows_path"])
    if _sha256_file(rows_path) != metadata["normalized_rows_sha256"]:
        raise RuntimeError("frozen Kraken REST normalized rows digest mismatch")
    previous_timestamp_ns = None
    dedup_timestamp_ns = None
    trade_ids_at_timestamp: set[int] = set()
    with rows_path.open("r", encoding="ascii", newline="") as stream:
        for line_number, row in enumerate(csv.reader(stream), 1):
            if len(row) != 4:
                raise RuntimeError(f"invalid frozen Kraken REST row width line={line_number}")
            timestamp = _decimal(row[0], "frozen timestamp")
            price = _decimal(row[1], "frozen price")
            volume = _decimal(row[2], "frozen volume")
            trade_id = _trade_id(row[3], f"frozen line={line_number}")
            timestamp_ns = _timestamp_ns(timestamp)
            if previous_timestamp_ns is not None and timestamp_ns < previous_timestamp_ns:
                raise RuntimeError("frozen Kraken REST timestamp regression")
            previous_timestamp_ns = timestamp_ns
            if dedup_timestamp_ns != timestamp_ns:
                dedup_timestamp_ns = timestamp_ns
                trade_ids_at_timestamp = set()
            if trade_id in trade_ids_at_timestamp:
                raise RuntimeError(
                    f"duplicate trade id in normalized Kraken REST rows timestamp={timestamp_ns} trade_id={trade_id}"
                )
            trade_ids_at_timestamp.add(trade_id)
            if min_exclusive_ns is not None and timestamp_ns <= min_exclusive_ns:
                continue
            yield timestamp, price, volume


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


def _emit(stream, state: dict) -> None:
    stream.write(
        ",".join(
            [
                str(state["bucket"]),
                format(state["open"], "f"),
                format(state["high"], "f"),
                format(state["low"], "f"),
                format(state["close"], "f"),
                format(state["volume"], "f"),
                str(state["trade_count"]),
            ]
        )
        + "\n"
    )


def derive_ohlcvt_archive(
    frozen: dict,
    destination: Path,
    cutoff_ms: int,
    *,
    min_exclusive_ns: int | None = None,
) -> dict:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    csv_paths = {interval: destination.parent / f".{destination.name}.{interval}.csv" for interval in INTERVALS}
    streams = {interval: path.open("w", encoding="ascii", newline="") for interval, path in csv_paths.items()}
    states = {interval: None for interval in INTERVALS}
    row_counts = {interval: 0 for interval in INTERVALS}
    first_ns = None
    latest_ns = None
    try:
        for timestamp, price, volume in _iter_frozen_trades(frozen, min_exclusive_ns=min_exclusive_ns):
            timestamp_ns = _timestamp_ns(timestamp)
            timestamp_ms = timestamp_ns // 1_000_000
            if timestamp_ms >= cutoff_ms:
                continue
            first_ns = timestamp_ns if first_ns is None else first_ns
            latest_ns = timestamp_ns
            for interval, step in INTERVALS.items():
                bucket = (int(timestamp) // step) * step
                state = states[interval]
                if state is None:
                    states[interval] = _new_bucket(bucket, price, volume)
                elif bucket == state["bucket"]:
                    _update_bucket(state, price, volume)
                elif bucket > state["bucket"]:
                    _emit(streams[interval], state)
                    row_counts[interval] += 1
                    states[interval] = _new_bucket(bucket, price, volume)
                else:
                    raise RuntimeError("Kraken REST derived bucket ordering regression")
        for interval, state in states.items():
            if state is not None:
                _emit(streams[interval], state)
                row_counts[interval] += 1
    finally:
        for stream in streams.values():
            stream.close()
    if first_ns is None or latest_ns is None:
        raise RuntimeError("Kraken REST tail produced no derived trades")

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
    return {
        "derived_archive_sha256": _sha256_file(destination),
        "first_trade_ns": first_ns,
        "latest_trade_ns": latest_ns,
        "row_counts": row_counts,
    }


def _read_member(path: Path, interval: str) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        return list(csv.reader(io.StringIO(archive.read(DERIVED_MEMBERS[interval]).decode("ascii"))))


def _rows_equal(left: list[str], right: list[str]) -> bool:
    if int(left[0]) != int(right[0]) or int(left[6]) != int(right[6]):
        return False
    return all(_decimal(left[index], "overlap") == _decimal(right[index], "overlap") for index in range(1, 6))


def verify_archive_overlap(archive_path: Path, rest_path: Path, archive_latest_ns: int) -> dict:
    counts = {}
    for interval, step in INTERVALS.items():
        left = {int(row[0]): row for row in _read_member(archive_path, interval)}
        right = {int(row[0]): row for row in _read_member(rest_path, interval)}
        comparable = [
            key
            for key in sorted(set(left) & set(right))
            if (key + step) * 1_000_000_000 <= archive_latest_ns
        ]
        required = 3 if interval == "5m" else 1
        if len(comparable) < required:
            raise RuntimeError(f"insufficient Time & Sales/REST overlap for {interval}: {len(comparable)}")
        for key in comparable:
            if not _rows_equal(left[key], right[key]):
                raise RuntimeError(f"Time & Sales/REST overlap mismatch interval={interval} bucket={key}")
        counts[interval] = len(comparable)
    result = {"status": "PASS", "matches": counts, "conflicts": 0}
    print(f"KRAKEN_SOURCE_SEAM_OVERLAP={json.dumps(result, sort_keys=True, separators=(',', ':'))}")
    return result


def _combine(left: list[str], right: list[str]) -> list[str]:
    if int(left[0]) != int(right[0]):
        raise RuntimeError("cannot combine different Kraken derived buckets")
    high = left[2] if _decimal(left[2], "high") >= _decimal(right[2], "high") else right[2]
    low = left[3] if _decimal(left[3], "low") <= _decimal(right[3], "low") else right[3]
    volume = _decimal(left[5], "volume") + _decimal(right[5], "volume")
    return [
        left[0],
        left[1],
        high,
        low,
        right[4],
        format(volume, "f"),
        str(int(left[6]) + int(right[6])),
    ]


def merge_derived_archives(archive_path: Path, tail_path: Path, destination: Path) -> dict:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    merged = {}
    seam_buckets = {}
    for interval in ("5m", "1d"):
        rows = {int(row[0]): row for row in _read_member(archive_path, interval)}
        seams = 0
        for row in _read_member(tail_path, interval):
            key = int(row[0])
            if key in rows:
                rows[key] = _combine(rows[key], row)
                seams += 1
            else:
                rows[key] = row
        if seams > 1:
            raise RuntimeError(f"unexpected multiple Kraken source seam buckets for {interval}: {seams}")
        merged[interval] = [rows[key] for key in sorted(rows)]
        seam_buckets[interval] = seams
    temp = destination.with_suffix(destination.suffix + ".partial")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for interval in ("5m", "1d"):
                info = zipfile.ZipInfo(DERIVED_MEMBERS[interval], date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                raw = "".join(",".join(row) + "\n" for row in merged[interval]).encode("ascii")
                archive.writestr(info, raw)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return {
        "derived_archive_sha256": _sha256_file(destination),
        "row_counts": {interval: len(rows) for interval, rows in merged.items()},
        "seam_buckets": seam_buckets,
    }
