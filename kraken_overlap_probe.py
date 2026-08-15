from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

KRAKEN_ANALYTICS = "https://futures.kraken.com/api/charts/v1/analytics"
DEFAULT_TARGET_MS = 1786738500000
DEFAULT_CUTOFF_MS = 1786791600000
DEFAULT_INSTRUMENT = "PI_ETHUSD"
DEFAULT_INSTRUMENTS = ("PI_ETHUSD", "PI_XBTUSD")
DEFAULT_METRICS = (
    "open-interest",
    "aggressor-differential",
    "trade-volume",
    "trade-count",
    "liquidation-volume",
    "rolling-volatility",
    "long-short-ratio",
    "cvd",
    "spreads",
    "liquidity",
    "slippage",
    "future-basis",
    "funding",
)


def compact(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def request_json(url, retries=4):
    headers = {"Accept": "application/json", "User-Agent": "eth-macro-kraken-overlap-probe/1.1"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            if exc.code in (403, 429, 500, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(min(10, 2**attempt))
                continue
            raise RuntimeError(f"HTTP {exc.code} {url}: {raw[:500]!r}") from exc
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(min(10, 2**attempt))
    raise AssertionError("unreachable")


def flatten_kraken(result):
    timestamps = result.get("timestamp", [])
    data = result.get("data", [])

    def normalize_timestamp(value):
        number = int(value)
        return number * 1000 if number < 10**12 else number

    if isinstance(data, list):
        return [[normalize_timestamp(timestamp), data[index]] for index, timestamp in enumerate(timestamps)]

    fields = []

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                walk(prefix + [key], value)
        elif isinstance(obj, list):
            fields.append((".".join(prefix), obj))

    walk([], data)
    return [
        [normalize_timestamp(timestamp), {key: value[index] for key, value in fields}]
        for index, timestamp in enumerate(timestamps)
    ]


def fetch_window(instrument, metric, since_seconds, to_seconds):
    params = {"since": since_seconds, "interval": 300}
    if to_seconds is not None:
        params["to"] = to_seconds
    url = f"{KRAKEN_ANALYTICS}/{instrument}/{metric}?{urllib.parse.urlencode(params)}"
    payload = request_json(url)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"missing Kraken result for {instrument}/{metric}")
    if payload.get("errors"):
        raise RuntimeError(f"Kraken errors for {instrument}/{metric}: {payload['errors']}")
    return {"url": url, "more": bool(result.get("more")), "rows": flatten_kraken(result)}


def fetch_range(instrument, metric, start_ms, end_ms):
    cursor = start_ms // 1000
    to_seconds = end_ms // 1000
    pages = 0
    unique = {}
    while cursor <= to_seconds:
        response = fetch_window(instrument, metric, cursor, to_seconds)
        page = response["rows"]
        pages += 1
        for row in page:
            if row[0] < start_ms or row[0] > end_ms:
                continue
            old = unique.get(row[0])
            if old is not None and old != row:
                raise RuntimeError(f"provider conflicting duplicate {instrument}/{metric} {row[0]}")
            unique[row[0]] = row
        if not response["more"]:
            break
        if not page:
            raise RuntimeError(f"provider pagination empty-more {instrument}/{metric}")
        next_cursor = page[-1][0] // 1000 + 1
        if next_cursor <= cursor:
            raise RuntimeError(f"provider pagination stalled {instrument}/{metric}")
        cursor = next_cursor
        if pages > 1000:
            raise RuntimeError(f"provider pagination safety bound {instrument}/{metric}")
    return [unique[key] for key in sorted(unique)], pages


def archive_path(instrument, metric, target_ms):
    day = datetime.fromtimestamp(target_ms / 1000, timezone.utc).strftime("%Y/%m/%d")
    return Path("derivatives/archive") / day / "kraken-futures" / f"{instrument}-{metric}.json"


def archive_rows(instrument, metric, target_ms):
    path = archive_path(instrument, metric, target_ms)
    if not path.exists():
        return path, []
    return path, json.loads(path.read_text()).get("records", [])


def all_archive_rows(instrument, metric, cutoff_ms):
    unique = {}
    paths = sorted(Path("derivatives/archive").rglob(f"{instrument}-{metric}.json"))
    for path in paths:
        if "kraken-futures" not in path.parts:
            continue
        payload = json.loads(path.read_text())
        for row in payload.get("records", []):
            timestamp = int(row[0])
            if timestamp > cutoff_ms:
                continue
            old = unique.get(timestamp)
            if old is not None and old != row:
                raise RuntimeError(f"Git conflicting duplicate {instrument}/{metric} {timestamp} {path}")
            unique[timestamp] = row
    return [unique[key] for key in sorted(unique)], paths


def row_index(rows):
    return {int(row[0]): row for row in rows}


def decimal_equal(left, right):
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError, TypeError):
        return left == right


def cvd_invariants_equal(left, right):
    if not isinstance(left, list) or not isinstance(right, list) or left[0] != right[0]:
        return False
    if not isinstance(left[1], dict) or not isinstance(right[1], dict):
        return False
    for field in ("buy_volume", "sell_volume"):
        if field not in left[1] or field not in right[1] or not decimal_equal(left[1][field], right[1][field]):
            return False
    return True


def classify(metric, git_row, provider_rows):
    present = [row for row in provider_rows.values() if row is not None]
    if not present:
        return "PROVIDER_TARGET_MISSING"
    first = present[0]
    provider_equal = all(row == first for row in present[1:])
    if metric == "cvd" and git_row is not None and all(cvd_invariants_equal(git_row, row) for row in present):
        return "CVD_INVARIANTS_MATCH" if provider_equal else "CVD_WINDOW_VARIANT_NATIVE"
    if not provider_equal:
        return "WINDOW_OR_TO_VARIANT"
    if git_row is None:
        return "NO_GIT_ROW"
    if git_row == first:
        return "EXACT_MATCH"
    return "GIT_PROVIDER_CONFLICT_STABLE_ACROSS_PROBED_WINDOWS"


def conflict_summary(git_rows, provider_rows, start_ms, end_ms, metric):
    git = row_index(row for row in git_rows if start_ms <= int(row[0]) <= end_ms)
    provider = row_index(row for row in provider_rows if start_ms <= int(row[0]) <= end_ms)
    common = sorted(set(git) & set(provider))
    exact = []
    semantic = []
    conflicts = []
    for timestamp in common:
        if git[timestamp] == provider[timestamp]:
            exact.append(timestamp)
        elif metric == "cvd" and cvd_invariants_equal(git[timestamp], provider[timestamp]):
            semantic.append(timestamp)
        else:
            conflicts.append(timestamp)
    return {
        "git_rows": len(git),
        "provider_rows": len(provider),
        "common": len(common),
        "git_only": len(set(git) - set(provider)),
        "provider_only": len(set(provider) - set(git)),
        "exact": len(exact),
        "semantic": len(semantic),
        "conflicts": len(conflicts),
        "first_conflicts": conflicts[:5],
        "last_conflicts": conflicts[-5:] if conflicts else [],
    }


def targeted_probe(args, metrics):
    target_seconds = args.target_ms // 1000
    cutoff_seconds = args.cutoff_ms // 1000
    probe_start_ms = args.target_ms - 3600_000
    probe_end_ms = args.target_ms + 3600_000
    windows = (
        ("near_fixed", target_seconds - 3600, target_seconds + 3600),
        ("wide_fixed", target_seconds - 6 * 3600, target_seconds + 3600),
        ("near_cutoff", target_seconds - 3600, cutoff_seconds),
        ("near_open_end", target_seconds - 3600, None),
    )

    print(f"PROBE_INSTRUMENT={args.instrument}")
    print(f"PROBE_TARGET_MS={args.target_ms}")
    print(f"PROBE_TARGET_UTC={datetime.fromtimestamp(args.target_ms/1000, timezone.utc).isoformat().replace('+00:00','Z')}")
    print(f"PROBE_CUTOFF_MS={args.cutoff_ms}")
    print(f"PROBE_METRIC_COUNT={len(metrics)}")
    print("PROBE_NETWORK_SCOPE=KRAKEN_FUTURES_ANALYTICS_READ_ONLY")

    classifications = {}
    for metric in metrics:
        path, git_rows = archive_rows(args.instrument, metric, args.target_ms)
        git = row_index(git_rows)
        git_target = git.get(args.target_ms)
        provider_targets = {}
        fetched = {}
        print(f"METRIC_BEGIN={metric}")
        print(f"GIT_ARCHIVE_PATH={path.as_posix()}")
        print(f"GIT_TARGET_ROW={compact(git_target) if git_target is not None else 'MISSING'}")
        for label, since_seconds, to_seconds in windows:
            response = fetch_window(args.instrument, metric, since_seconds, to_seconds)
            index = row_index(response["rows"])
            target = index.get(args.target_ms)
            provider_targets[label] = target
            fetched[label] = response
            print(f"WINDOW={label} SINCE={since_seconds} TO={to_seconds if to_seconds is not None else 'NOW'} MORE={str(response['more']).lower()} ROWS={len(response['rows'])}")
            print(f"PROVIDER_TARGET_ROW_{label.upper()}={compact(target) if target is not None else 'MISSING'}")
        classification = classify(metric, git_target, provider_targets)
        classifications[metric] = classification
        print(f"METRIC_CLASSIFICATION={classification}")
        summary = conflict_summary(git_rows, fetched["near_fixed"]["rows"], probe_start_ms, probe_end_ms, metric)
        print(f"NEAR_OVERLAP_SUMMARY={compact(summary)}")
        provider_index = row_index(fetched["near_fixed"]["rows"])
        for timestamp in summary["first_conflicts"]:
            print(f"CONFLICT_TS={timestamp} GIT={compact(git[timestamp])} PROVIDER={compact(provider_index[timestamp])}")
        print(f"METRIC_END={metric}")

    counts = {}
    for classification in classifications.values():
        counts[classification] = counts.get(classification, 0) + 1
    print(f"CLASSIFICATION_COUNTS={compact(counts)}")
    print(f"CLASSIFICATIONS={compact(classifications)}")


def full_overlap_audit(cutoff_ms, metrics):
    print("FULL_GIT_OVERLAP_AUDIT=BEGIN")
    totals = {"series": 0, "common": 0, "exact": 0, "semantic": 0, "conflicts": 0, "git_only": 0, "provider_only": 0, "requests": 0}
    conflict_series = {}
    for instrument in DEFAULT_INSTRUMENTS:
        for metric in metrics:
            git_rows, paths = all_archive_rows(instrument, metric, cutoff_ms)
            if not git_rows:
                print(f"FULL_SERIES={instrument}/{metric} STATUS=NO_GIT_ROWS")
                continue
            provider_rows, pages = fetch_range(instrument, metric, git_rows[0][0], cutoff_ms)
            summary = conflict_summary(git_rows, provider_rows, git_rows[0][0], cutoff_ms, metric)
            totals["series"] += 1
            totals["requests"] += pages
            for key in ("common", "exact", "semantic", "conflicts", "git_only", "provider_only"):
                totals[key] += summary[key]
            status = "PASS" if summary["conflicts"] == 0 and summary["git_only"] == 0 else "CONFLICT"
            print(f"FULL_SERIES={instrument}/{metric} STATUS={status} PAGES={pages} FILES={len(paths)} SUMMARY={compact(summary)}")
            if summary["conflicts"]:
                conflict_series[f"{instrument}/{metric}"] = summary["conflicts"]
                git_index = row_index(git_rows)
                provider_index = row_index(provider_rows)
                for timestamp in summary["first_conflicts"]:
                    print(f"FULL_CONFLICT={instrument}/{metric} TS={timestamp} GIT={compact(git_index[timestamp])} PROVIDER={compact(provider_index[timestamp])}")
    print(f"FULL_GIT_OVERLAP_TOTALS={compact(totals)}")
    print(f"FULL_GIT_OVERLAP_CONFLICT_SERIES={compact(conflict_series)}")
    print("FULL_GIT_OVERLAP_AUDIT=PASS_DIAGNOSTIC_COMPLETED")


def main():
    parser = argparse.ArgumentParser(description="Read-only Kraken Futures Git/provider overlap diagnostic")
    parser.add_argument("--target-ms", type=int, default=DEFAULT_TARGET_MS)
    parser.add_argument("--cutoff-ms", type=int, default=DEFAULT_CUTOFF_MS)
    parser.add_argument("--instrument", default=DEFAULT_INSTRUMENT)
    parser.add_argument("--metric", action="append", dest="metrics")
    parser.add_argument("--full-git-overlap", action="store_true")
    args = parser.parse_args()
    metrics = tuple(args.metrics or DEFAULT_METRICS)
    targeted_probe(args, metrics)
    if args.full_git_overlap:
        full_overlap_audit(args.cutoff_ms, metrics)
    print("PROBE_RESULT=PASS")


if __name__ == "__main__":
    main()
