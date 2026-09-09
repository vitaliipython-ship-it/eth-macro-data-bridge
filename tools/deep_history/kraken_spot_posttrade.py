from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

SOURCE_MODE = "KRAKEN_OFFICIAL_POSTTRADE_BULK"
SOURCE_SCHEMA = "kraken-spot-posttrade-segment/1.0.0"
ENDPOINT = "https://api.kraken.com/0/public/PostTrade"
DOCUMENTATION = "https://docs.kraken.com/api/docs/rest-api/get-post-trade"
SYMBOL = "ETH/USD"
USER_AGENT = "eth-macro-data-bridge-posttrade/1.0"
COUNT = 1000
REQUEST_DELAY_SECONDS = float(os.environ.get("KRAKEN_POSTTRADE_DELAY_SECONDS", "1.0"))
MAX_PAGES = 20_000
MAX_RETRIES = 3
MAX_PARALLEL = 1
FRAME = struct.Struct(">Q")
INTERVALS = {"5m": 300, "1d": 86_400}
STATUS_VALUES = {"PENDING", "IN_PROGRESS", "COMPLETE", "FAILED"}
GAP_POLICY = "PROVIDER_NO_TRADE_OMISSION"
MARKET_INCEPTION_UTC = "2015-08-07T00:00:00Z"
QUALIFIED_CONSERVATIVE_QUARTER_SECONDS = Decimal("3080.819716")
FINAL_ASSEMBLY_RESERVE_SECONDS = 21_600
ARTIFACT_RETENTION_DAYS = 7


class PostTradeIncomplete(RuntimeError):
    """Official PostTrade acquisition cannot prove the requested segment."""


class SegmentInterrupted(PostTradeIncomplete):
    """Intentional bounded qualification interruption; partial segment is invalid."""


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"timestamp must be UTC RFC3339 Z form: {value!r}")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"timestamp must be UTC: {value!r}")
    return parsed.astimezone(timezone.utc)


def timestamp_decimal(value: str) -> Decimal:
    parse_utc(value)
    text = value[:-1]
    if "." in text:
        whole, fraction = text.split(".", 1)
    else:
        whole, fraction = text, ""
    base = datetime.strptime(whole, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    result = Decimal(int(base.timestamp()))
    if fraction:
        if not fraction.isdigit():
            raise ValueError(f"invalid UTC fractional timestamp: {value!r}")
        result += Decimal(f"0.{fraction}")
    return result


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _quarter_boundary_after(value: datetime) -> datetime:
    month = ((value.month - 1) // 3 + 1) * 3 + 1
    year = value.year
    if month == 13:
        month = 1
        year += 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def segment_id(start_utc: str, end_utc: str) -> str:
    parse_utc(start_utc)
    parse_utc(end_utc)
    material = {
        "source_authority": SOURCE_MODE,
        "source_schema_version": SOURCE_SCHEMA,
        "symbol": SYMBOL,
        "segment_start_utc": start_utc,
        "segment_end_utc": end_utc,
    }
    return hashlib.sha256(compact(material)).hexdigest()


def segment_descriptor(start_utc: str, end_utc: str, *, status: str = "PENDING") -> dict:
    start = parse_utc(start_utc)
    end = parse_utc(end_utc)
    if end <= start:
        raise ValueError("segment end must be after start")
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid segment status: {status}")
    return {
        "segment_id": segment_id(start_utc, end_utc),
        "source_mode": SOURCE_MODE,
        "symbol": SYMBOL,
        "requested_start_utc": start_utc,
        "requested_end_utc": end_utc,
        "status": status,
    }


def build_segment_inventory(requested_start_utc: str, requested_end_utc: str) -> list[dict]:
    start = parse_utc(requested_start_utc)
    end = parse_utc(requested_end_utc)
    if end <= start:
        raise ValueError("requested end must be after start")
    result: list[dict] = []
    current = start
    while current < end:
        segment_end = min(_quarter_boundary_after(current), end)
        result.append(segment_descriptor(iso_utc(current), iso_utc(segment_end)))
        current = segment_end
    return result


def retention_plan(requested_start_utc: str, requested_end_utc: str) -> dict:
    segment_count = len(build_segment_inventory(requested_start_utc, requested_end_utc))
    required_seconds = Decimal(segment_count) * QUALIFIED_CONSERVATIVE_QUARTER_SECONDS + Decimal(FINAL_ASSEMBLY_RESERVE_SECONDS)
    configured_seconds = Decimal(ARTIFACT_RETENTION_DAYS * 86_400)
    if configured_seconds <= required_seconds:
        raise PostTradeIncomplete("COMPLETED_SEGMENT_PERSISTENCE_LIFETIME_INSUFFICIENT")
    return {
        "segment_count": segment_count,
        "qualified_conservative_quarter_seconds": str(QUALIFIED_CONSERVATIVE_QUARTER_SECONDS),
        "final_assembly_reserve_seconds": FINAL_ASSEMBLY_RESERVE_SECONDS,
        "required_retention_seconds": str(required_seconds),
        "configured_retention_days": ARTIFACT_RETENTION_DAYS,
        "configured_retention_seconds": str(configured_seconds),
        "retention_safety_margin_seconds": str(configured_seconds - required_seconds),
        "status": "PASS",
    }


def _decimal(value, context: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PostTradeIncomplete(f"invalid PostTrade decimal {context}: {value!r}") from exc
    if not result.is_finite():
        raise PostTradeIncomplete(f"non-finite PostTrade decimal {context}: {value!r}")
    return result


def _provider_fingerprint(trade: dict) -> str:
    return hashlib.sha256(compact(trade)).hexdigest()


def _open(opener, request):
    if opener is None:
        return urllib.request.urlopen(request, timeout=30)
    return opener.open(request, timeout=30)


def _request_page(cursor: str, end_utc: str, opener=None, sleep_fn=time.sleep) -> tuple[bytes, list[dict], str]:
    query = urllib.parse.urlencode({"symbol": SYMBOL, "from_ts": cursor, "to_ts": end_utc, "count": str(COUNT)})
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with _open(opener, request) as response:
                raw = response.read()
                retry_after = response.headers.get("Retry-After", "") if hasattr(response, "headers") else ""
                status = getattr(response, "status", 200)
            if status != 200:
                raise PostTradeIncomplete(f"PostTrade HTTP status={status}")
            if retry_after:
                raise PostTradeIncomplete(f"PostTrade provider throttle Retry-After={retry_after}")
            payload = json.loads(raw.decode("utf-8"))
            if payload.get("error"):
                raise PostTradeIncomplete(f"PostTrade errors={payload['error']}")
            result = payload.get("result")
            if not isinstance(result, dict):
                raise PostTradeIncomplete("PostTrade result is not an object")
            trades = result.get("trades")
            next_cursor = result.get("last_ts")
            count = result.get("count")
            if not isinstance(trades, list) or not isinstance(next_cursor, str):
                raise PostTradeIncomplete("PostTrade malformed result schema")
            if count is not None and int(count) != len(trades):
                raise PostTradeIncomplete("PostTrade result.count does not match trades length")
            if timestamp_decimal(next_cursor) <= timestamp_decimal(cursor):
                raise PostTradeIncomplete(f"POSTTRADE_PRODUCTION_CURSOR_NON_ADVANCING {cursor}->{next_cursor}")
            return raw, trades, next_cursor
        except PostTradeIncomplete:
            raise
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            sleep_fn(min(attempt, 2))
    raise PostTradeIncomplete(f"PostTrade transport failed after bounded retries: {last_error!r}")


def _state_path(root: Path, descriptor: dict) -> Path:
    return Path(root) / "states" / f"{descriptor['segment_id']}.json"


def _write_state(root: Path, descriptor: dict, status: str, **extra) -> None:
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid status {status}")
    path = _state_path(root, descriptor)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SOURCE_SCHEMA,
        "segment_id": descriptor["segment_id"],
        "requested_start_utc": descriptor["requested_start_utc"],
        "requested_end_utc": descriptor["requested_end_utc"],
        "status": status,
        **extra,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(compact(payload))
    temporary.replace(path)


def _normalize_trade(trade: dict) -> dict:
    required = ("trade_ts", "trade_id", "price", "quantity", "symbol")
    if not isinstance(trade, dict) or any(key not in trade for key in required):
        raise PostTradeIncomplete("POSTTRADE_PRODUCTION_SCHEMA_NOT_QUALIFIED")
    if trade["symbol"] != SYMBOL:
        raise PostTradeIncomplete(f"unexpected PostTrade symbol: {trade['symbol']!r}")
    trade_id = trade["trade_id"]
    if not isinstance(trade_id, str) or not trade_id or len(trade_id) > 19:
        raise PostTradeIncomplete(f"invalid PostTrade trade_id: {trade_id!r}")
    parse_utc(trade["trade_ts"])
    price = _decimal(trade["price"], "price")
    quantity = _decimal(trade["quantity"], "quantity")
    if price <= 0 or quantity < 0:
        raise PostTradeIncomplete("invalid PostTrade price/quantity")
    return {"trade_ts": trade["trade_ts"], "trade_id": trade_id, "price": format(price, "f"), "quantity": format(quantity, "f")}


def _acquire_to_partial(descriptor: dict, partial_dir: Path, *, opener=None, sleep_fn=time.sleep, delay_seconds: float = REQUEST_DELAY_SECONDS, interrupt_after_pages: int | None = None) -> dict:
    start_utc = descriptor["requested_start_utc"]
    end_utc = descriptor["requested_end_utc"]
    start = parse_utc(start_utc)
    start_key = timestamp_decimal(start_utc)
    end_key = timestamp_decimal(end_utc)
    query_start = iso_utc(start - timedelta(seconds=1))
    raw_path = partial_dir / "raw-pages.bin"
    rows_path = partial_dir / "normalized.jsonl"
    partial_dir.mkdir(parents=True, exist_ok=True)
    cursor = query_start
    previous_ts_key: Decimal | None = None
    seen: dict[str, str] = {}
    page_count = raw_row_count = unique_count = duplicate_count = 0
    first_ts = first_id = last_ts = last_id = None
    complete = False
    transcript = hashlib.sha256()
    with raw_path.open("wb") as raw_stream, rows_path.open("wb") as row_stream:
        while page_count < MAX_PAGES:
            raw, trades, next_cursor = _request_page(cursor, end_utc, opener=opener, sleep_fn=sleep_fn)
            page_count += 1
            raw_stream.write(FRAME.pack(len(raw))); raw_stream.write(raw)
            transcript.update(compact({"page": page_count, "cursor": cursor, "next_cursor": next_cursor, "body_sha256": hashlib.sha256(raw).hexdigest()}))
            for trade in trades:
                normalized = _normalize_trade(trade)
                current_ts_key = timestamp_decimal(normalized["trade_ts"])
                if previous_ts_key is not None and current_ts_key < previous_ts_key:
                    raise PostTradeIncomplete("PostTrade trade timestamp regression")
                previous_ts_key = current_ts_key
                if current_ts_key < start_key or current_ts_key >= end_key:
                    continue
                raw_row_count += 1
                trade_id = normalized["trade_id"]
                fingerprint = _provider_fingerprint(trade)
                prior = seen.get(trade_id)
                if prior is not None:
                    if prior != fingerprint:
                        raise PostTradeIncomplete(f"POSTTRADE_PRODUCTION_TRADE_ID_CONFLICT trade_id={trade_id}")
                    duplicate_count += 1
                    continue
                seen[trade_id] = fingerprint
                row_stream.write(compact(normalized))
                unique_count += 1
                first_ts = normalized["trade_ts"] if first_ts is None else first_ts
                first_id = trade_id if first_id is None else first_id
                last_ts, last_id = normalized["trade_ts"], trade_id
            cursor = next_cursor
            if interrupt_after_pages is not None and page_count >= interrupt_after_pages:
                raise SegmentInterrupted("intentional qualification interruption")
            if len(trades) < COUNT or timestamp_decimal(cursor) >= end_key:
                complete = True
                break
            if delay_seconds > 0:
                sleep_fn(delay_seconds)
        else:
            raise PostTradeIncomplete(f"PostTrade segment exceeded MAX_PAGES={MAX_PAGES}")
    if not complete:
        raise PostTradeIncomplete("PostTrade segment did not prove requested end")
    if raw_row_count != unique_count + duplicate_count:
        raise RuntimeError("PostTrade duplicate accounting invariant failed")
    metadata = {
        "schema_version": SOURCE_SCHEMA,
        "source_mode": SOURCE_MODE,
        "symbol": SYMBOL,
        "segment_id": descriptor["segment_id"],
        "requested_start_utc": start_utc,
        "requested_end_utc": end_utc,
        "first_provider_trade_ts": first_ts,
        "first_provider_trade_id": first_id,
        "last_provider_trade_ts": last_ts,
        "last_provider_trade_id": last_id,
        "page_count": page_count,
        "raw_row_count": raw_row_count,
        "unique_trade_count": unique_count,
        "duplicate_trade_id_count": duplicate_count,
        "trade_id_conflict_count": 0,
        "initial_cursor": query_start,
        "final_cursor": cursor,
        "cursor_monotonic": True,
        "frozen_source_digest": sha256_file(rows_path),
        "raw_pages_digest": sha256_file(raw_path),
        "page_transcript_digest": transcript.hexdigest(),
        "gap_policy": GAP_POLICY,
        "synthetic_fill": False,
        "completion_status": "COMPLETE",
    }
    (partial_dir / "source.json").write_bytes(compact(metadata))
    return metadata


def _iter_frozen_rows(rows_path: Path, expected_digest: str):
    if sha256_file(rows_path) != expected_digest:
        raise RuntimeError("frozen PostTrade source read-back digest mismatch")
    previous_ts_key: Decimal | None = None
    seen_ids: set[str] = set()
    with Path(rows_path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if set(row) != {"trade_ts", "trade_id", "price", "quantity"}:
                raise RuntimeError(f"invalid frozen PostTrade row schema line={line_number}")
            current_ts_key = timestamp_decimal(row["trade_ts"])
            if previous_ts_key is not None and current_ts_key < previous_ts_key:
                raise RuntimeError("frozen PostTrade timestamp regression")
            previous_ts_key = current_ts_key
            if row["trade_id"] in seen_ids:
                raise RuntimeError(f"duplicate trade_id in frozen source: {row['trade_id']}")
            seen_ids.add(row["trade_id"])
            yield row


def _new_bucket(bucket_ms: int, price: Decimal, quantity: Decimal) -> list:
    return [bucket_ms, format(price, "f"), format(price, "f"), format(price, "f"), format(price, "f"), format(quantity, "f"), 1, None]


def build_from_frozen(rows_path: Path, frozen_source_digest: str) -> tuple[dict, str]:
    buckets: dict[str, dict[int, list]] = {name: {} for name in INTERVALS}
    for row in _iter_frozen_rows(rows_path, frozen_source_digest):
        timestamp = parse_utc(row["trade_ts"])
        epoch_seconds = int(timestamp.timestamp())
        price = _decimal(row["price"], "frozen price")
        quantity = _decimal(row["quantity"], "frozen quantity")
        for interval, step_seconds in INTERVALS.items():
            bucket_seconds = (epoch_seconds // step_seconds) * step_seconds
            bucket_ms = bucket_seconds * 1000
            current = buckets[interval].get(bucket_ms)
            if current is None:
                current = _new_bucket(bucket_ms, price, quantity)
                current[7] = bucket_ms + step_seconds * 1000 - 1
                buckets[interval][bucket_ms] = current
            else:
                current[2] = format(max(Decimal(current[2]), price), "f")
                current[3] = format(min(Decimal(current[3]), price), "f")
                current[4] = format(price, "f")
                current[5] = format(Decimal(current[5]) + quantity, "f")
                current[6] += 1
    output = {interval: [buckets[interval][key] for key in sorted(buckets[interval])] for interval in ("5m", "1d")}
    return output, frozen_source_digest


def _digest_records(records: list[list]) -> str:
    return hashlib.sha256(compact(records)).hexdigest()


def _provider_ids(rows_path: Path) -> list[str]:
    return [json.loads(line)["trade_id"] for line in rows_path.read_text(encoding="utf-8").splitlines() if line]


def execute_segment(root: Path, descriptor: dict, *, opener=None, sleep_fn=time.sleep, delay_seconds: float = REQUEST_DELAY_SECONDS, interrupt_after_pages: int | None = None) -> dict:
    root = Path(root)
    final_dir = root / "segments" / descriptor["segment_id"]
    evidence_path = final_dir / "evidence.json"
    if evidence_path.is_file():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence.get("completion_status") != "COMPLETE":
            raise RuntimeError("persisted PostTrade segment is not COMPLETE")
        _write_state(root, descriptor, "COMPLETE", evidence_digest=sha256_file(evidence_path))
        return {"descriptor": descriptor, "directory": str(final_dir), "evidence": evidence, "reused": True}
    if not _state_path(root, descriptor).is_file():
        _write_state(root, descriptor, "PENDING")
    _write_state(root, descriptor, "IN_PROGRESS")
    partial_dir = root / ".partial" / descriptor["segment_id"]
    if partial_dir.exists(): shutil.rmtree(partial_dir)
    try:
        metadata = _acquire_to_partial(descriptor, partial_dir, opener=opener, sleep_fn=sleep_fn, delay_seconds=delay_seconds, interrupt_after_pages=interrupt_after_pages)
        rows_path = partial_dir / "normalized.jsonl"
        source_digest = metadata["frozen_source_digest"]
        build_a, build_a_source = build_from_frozen(rows_path, source_digest)
        build_b, build_b_source = build_from_frozen(rows_path, source_digest)
        if build_a_source != build_b_source or build_a_source != source_digest or build_a != build_b:
            raise RuntimeError("POSTTRADE_PRODUCTION_BUILD_AB_MISMATCH")
        output_path = partial_dir / "segment-output.json"
        output_path.write_bytes(compact(build_a))
        ids = _provider_ids(rows_path)
        (partial_dir / "provider-trade-ids.txt").write_text("\n".join(ids) + ("\n" if ids else ""), encoding="ascii")
        evidence = {
            **metadata,
            "build_a_source_digest": build_a_source,
            "build_b_source_digest": build_b_source,
            "derived_5m_digest": _digest_records(build_a["5m"]),
            "derived_1d_digest": _digest_records(build_a["1d"]),
            "segment_output_digest": sha256_file(output_path),
            "persistence_model": "S2_MINIMUM_SEGMENT_OUTPUT_AND_EVIDENCE",
            "resume_granularity": "COMPLETED_SEGMENT",
            "page_level_checkpointing": False,
            "max_parallel": MAX_PARALLEL,
            "completion_status": "COMPLETE",
        }
        (partial_dir / "evidence.json").write_bytes(compact(evidence))
        (partial_dir / "raw-pages.bin").unlink(); rows_path.unlink(); (partial_dir / "source.json").unlink()
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        if final_dir.exists(): shutil.rmtree(final_dir)
        partial_dir.replace(final_dir)
        _write_state(root, descriptor, "COMPLETE", evidence_digest=sha256_file(final_dir / "evidence.json"))
        return {"descriptor": descriptor, "directory": str(final_dir), "evidence": evidence, "reused": False}
    except Exception as exc:
        if partial_dir.exists(): shutil.rmtree(partial_dir)
        _write_state(root, descriptor, "FAILED", error_type=type(exc).__name__)
        raise


def _load_output(segment_directory: Path) -> dict:
    payload = json.loads((Path(segment_directory) / "segment-output.json").read_text(encoding="utf-8"))
    if set(payload) != {"5m", "1d"}: raise RuntimeError("invalid completed segment output schema")
    return payload


def _merge_record(left: list, right: list) -> list:
    if left[0] != right[0] or left[7] != right[7]: raise RuntimeError("cannot merge different OHLCVT buckets")
    return [left[0], left[1], format(max(Decimal(left[2]), Decimal(right[2])), "f"), format(min(Decimal(left[3]), Decimal(right[3])), "f"), right[4], format(Decimal(left[5]) + Decimal(right[5]), "f"), int(left[6]) + int(right[6]), left[7]]


def assemble_segment_outputs(segment_directories: list[Path]) -> dict:
    assembled: dict[str, dict[int, list]] = {"5m": {}, "1d": {}}
    seen_provider_ids: set[str] = set()
    for directory in segment_directories:
        directory = Path(directory)
        evidence = json.loads((directory / "evidence.json").read_text(encoding="utf-8"))
        if evidence.get("completion_status") != "COMPLETE": raise RuntimeError("cannot assemble non-COMPLETE segment")
        for trade_id in (directory / "provider-trade-ids.txt").read_text(encoding="ascii").splitlines():
            if trade_id in seen_provider_ids: raise RuntimeError(f"POSTTRADE_PRODUCTION_TRADE_ID_CONFLICT across segments {trade_id}")
            seen_provider_ids.add(trade_id)
        output = _load_output(directory)
        for interval in ("5m", "1d"):
            for row in output[interval]:
                existing = assembled[interval].get(row[0])
                assembled[interval][row[0]] = row[:] if existing is None else _merge_record(existing, row)
    return {interval: [assembled[interval][key] for key in sorted(assembled[interval])] for interval in ("5m", "1d")}


def output_digest(output: dict) -> str:
    return hashlib.sha256(compact(output)).hexdigest()


def execute_inventory(root: Path, requested_start_utc: str, requested_end_utc: str, *, opener=None, sleep_fn=time.sleep, delay_seconds: float = REQUEST_DELAY_SECONDS) -> dict:
    root = Path(root)
    inventory = build_segment_inventory(requested_start_utc, requested_end_utc)
    inventory_path = root / "inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    results = [execute_segment(root, descriptor, opener=opener, sleep_fn=sleep_fn, delay_seconds=delay_seconds) for descriptor in inventory]
    state = [json.loads(_state_path(root, descriptor).read_text(encoding="utf-8")) for descriptor in inventory]
    inventory_path.write_bytes(compact({"schema_version": SOURCE_SCHEMA, "source_mode": SOURCE_MODE, "requested_start_utc": requested_start_utc, "requested_end_utc": requested_end_utc, "segments": state}))
    directories = [Path(result["directory"]) for result in results]
    return {"inventory": inventory, "results": results, "directories": directories, "assembled": assemble_segment_outputs(directories)}


def write_derived_archive(output: dict, destination: Path) -> dict:
    import zipfile
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    member_names = {"5m": "ETHUSD_5.csv", "1d": "ETHUSD_1440.csv"}
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for interval in ("5m", "1d"):
            lines = [",".join(str(value) for value in [row[0] // 1000, *row[1:7]]) for row in output[interval]]
            archive.writestr(member_names[interval], ("\n".join(lines) + ("\n" if lines else "")).encode("ascii"))
    temporary.replace(destination)
    return {"derived_archive_sha256": sha256_file(destination), "derived_archive_size_bytes": destination.stat().st_size, "row_counts": {interval: len(output[interval]) for interval in ("5m", "1d")}}
