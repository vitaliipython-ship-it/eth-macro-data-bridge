from __future__ import annotations

import json
import re
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {text.count(old)}")
    return text.replace(old, new, 1)


def patch_time_sales() -> None:
    path = Path("tools/deep_history/kraken_spot_time_sales.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "    first_trade_ms: int | None = None\n    latest_trade_ms: int | None = None\n",
        "    first_trade_ms: int | None = None\n    latest_trade_ms: int | None = None\n"
        "    first_trade_ns: int | None = None\n    latest_trade_ns: int | None = None\n",
        "time-sales state",
    )
    text = replace_once(
        text,
        "                timestamp_ms = int(timestamp * 1000)\n                if timestamp_ms >= cutoff_ms:\n",
        "                timestamp_ns = int(timestamp * 1_000_000_000)\n"
        "                timestamp_ms = timestamp_ns // 1_000_000\n"
        "                if timestamp_ms >= cutoff_ms:\n",
        "time-sales timestamp",
    )
    text = replace_once(
        text,
        "                first_trade_ms = timestamp_ms if first_trade_ms is None else first_trade_ms\n"
        "                latest_trade_ms = timestamp_ms\n",
        "                first_trade_ms = timestamp_ms if first_trade_ms is None else first_trade_ms\n"
        "                latest_trade_ms = timestamp_ms\n"
        "                first_trade_ns = timestamp_ns if first_trade_ns is None else first_trade_ns\n"
        "                latest_trade_ns = timestamp_ns\n",
        "time-sales exact ns",
    )
    text = replace_once(
        text,
        "        \"first_trade_ms\": first_trade_ms,\n        \"latest_trade_ms\": latest_trade_ms,\n",
        "        \"first_trade_ms\": first_trade_ms,\n        \"latest_trade_ms\": latest_trade_ms,\n"
        "        \"first_trade_ns\": first_trade_ns,\n        \"latest_trade_ns\": latest_trade_ns,\n",
        "time-sales result",
    )
    path.write_text(text, encoding="utf-8")


def patch_backfill() -> None:
    path = Path("tools/deep_history/kraken_spot_ohlcvt_backfill.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from tools.deep_history import kraken_spot_time_sales as time_sales\n",
        "from tools.deep_history import kraken_spot_rest_trades as rest_trades\n"
        "from tools.deep_history import kraken_spot_time_sales as time_sales\n",
        "backfill import",
    )
    text = replace_once(
        text,
        "SOURCE_SCHEMA = time_sales.SOURCE_SCHEMA\nSOURCE_MODE = time_sales.SOURCE_MODE\n",
        "SOURCE_SCHEMA = \"kraken-spot-hybrid-trade-source/1.0.0\"\n"
        "SOURCE_MODE = \"KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL\"\n",
        "backfill source mode",
    )
    text = replace_once(
        text,
        "FROZEN_SOURCE_ROOT = ROOT / \"source\" / \"time-sales\"\n"
        "ARCHIVE = ROOT / \"source\" / \"kraken-timesales-derived-ohlcvt.zip\"\n",
        "FROZEN_SOURCE_ROOT = ROOT / \"source\" / \"time-sales\"\n"
        "REST_SOURCE_ROOT = ROOT / \"source\" / \"rest-trades\"\n"
        "ARCHIVE_ONLY = ROOT / \"source\" / \"kraken-timesales-derived-ohlcvt.zip\"\n"
        "REST_OVERLAP_ARCHIVE = ROOT / \"source\" / \"kraken-rest-overlap-derived-ohlcvt.zip\"\n"
        "REST_TAIL_ARCHIVE = ROOT / \"source\" / \"kraken-rest-tail-derived-ohlcvt.zip\"\n"
        "ARCHIVE = ROOT / \"source\" / \"kraken-hybrid-derived-ohlcvt.zip\"\n",
        "backfill source paths",
    )
    text, count = re.subn(
        r"def _quarter_for_timestamp\(.*?\n\ndef _warm_first_timestamp",
        "def _warm_first_timestamp",
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError(f"backfill quarter guard removal: {count}")

    acquire = '''def acquire_archive(
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
    rest_end_ns = int(cutoff_ms) * 1_000_000
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
            "coverage_declared_end_ms": cutoff_ms,
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
'''
    text, count = re.subn(
        r"def acquire_archive\(.*?\n\ndef _member_for_interval",
        acquire + "\n\ndef _member_for_interval",
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError(f"backfill acquire replacement: {count}")
    text = replace_once(
        text,
        '"source_semantics": "KRAKEN_TIME_SALES_DERIVED_OHLCVT",',
        '"source_semantics": "KRAKEN_TIME_SALES_PLUS_REST_TRADES_DERIVED_OHLCVT",',
        "backfill source semantics",
    )
    text = replace_once(
        text,
        '            "source_archive_sha256": source["archive_sha256"],\n'
        '            "source_archive_size_bytes": source["archive_size_bytes"],\n'
        '            "source_archive_file_ids": source["file_ids"],\n'
        '            "derived_archive_sha256": source["derived_archive_sha256"],\n',
        '            "source_archive_sha256": source["archive_sha256"],\n'
        '            "source_archive_size_bytes": source["archive_size_bytes"],\n'
        '            "source_archive_file_ids": source["file_ids"],\n'
        '            "archive_component_sha256": source["archive_component_sha256"],\n'
        '            "rest_tail_source_sha256": source["rest_tail_source_sha256"],\n'
        '            "rest_tail_page_count": source["rest_tail_page_count"],\n'
        '            "source_seam_overlap": source["source_seam_overlap"],\n'
        '            "derived_archive_sha256": source["derived_archive_sha256"],\n',
        "backfill boundary proof",
    )
    text = replace_once(
        text,
        '        "Immutable Kraken official Time & Sales-derived OHLCVT full-history successor; "\n',
        '        "Immutable Kraken official Time & Sales + bounded REST Trades tail-derived OHLCVT successor; "\n',
        "backfill release body",
    )
    text, count = re.subn(
        r"    try:\n        source = acquire_archive\(cutoff_ms=cutoff_ms, warm_first_ms=warm_first_ms\)\n"
        r"    except time_sales\.SourceInventoryIncomplete as exc:\n"
        r"        print\(\"KRAKEN_TIME_SALES_SOURCE_INVENTORY=INCOMPLETE\"\)\n"
        r"        print\(f\"KRAKEN_TIME_SALES_BLOCKER=\{exc\}\"\)\n"
        r"        print\(\"KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=false\"\)\n"
        r"        raise SystemExit\(76\) from exc\n",
        "    try:\n"
        "        source = acquire_archive(cutoff_ms=cutoff_ms, warm_first_ms=warm_first_ms)\n"
        "    except rest_trades.RestTailIncomplete as exc:\n"
        "        print(\"KRAKEN_REST_TRADES_TAIL=INCOMPLETE\")\n"
        "        print(f\"KRAKEN_REST_TRADES_BLOCKER={exc}\")\n"
        "        print(\"KRAKEN_OHLCVT_CAPABILITY_ACTIVATED=false\")\n"
        "        raise SystemExit(76) from exc\n",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"backfill fail-closed replacement: {count}")
    text = replace_once(
        text,
        '    print(f"KRAKEN_OHLCVT_QUARTER_FOLDER_ID={time_sales.QUARTER_FOLDER_ID}")\n',
        '    print(f"KRAKEN_OHLCVT_QUARTER_FOLDER_ID={time_sales.QUARTER_FOLDER_ID}")\n'
        '    print(f"KRAKEN_OHLCVT_REST_TAIL_ENDPOINT={rest_trades.ENDPOINT}")\n'
        '    print(f"KRAKEN_OHLCVT_REST_TAIL_OVERLAP_NS={rest_trades.OVERLAP_NS}")\n',
        "backfill plan",
    )
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    path = Path("tests/deep_history/test_kraken_spot_ohlcvt_backfill.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '        "source_mode": backfill.SOURCE_MODE,\n        "authority": "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE",\n',
        '        "source_mode": backfill.SOURCE_MODE,\n'
        '        "authority": "KRAKEN_OFFICIAL_TIME_SALES_PLUS_REST_TRADES",\n',
        "test source authority",
    )
    text = replace_once(
        text,
        '        "archive_sha256": "a" * 64,\n'
        '        "archive_size_bytes": 123,\n'
        '        "derived_archive_sha256": "b" * 64,\n',
        '        "archive_sha256": "a" * 64,\n'
        '        "archive_component_sha256": "c" * 64,\n'
        '        "archive_size_bytes": 123,\n'
        '        "rest_tail_source_sha256": "d" * 64,\n'
        '        "rest_tail_page_count": 9,\n'
        '        "source_seam_overlap": {\n'
        '            "status": "PASS", "matches": {"5m": 3, "1d": 1}, "conflicts": 0\n'
        '        },\n'
        '        "derived_archive_sha256": "b" * 64,\n',
        "test source metadata",
    )
    text = replace_once(
        text,
        '        self.assertEqual("KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE", backfill.SOURCE_MODE)\n',
        '        self.assertEqual(\n'
        '            "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL",\n'
        '            backfill.SOURCE_MODE,\n'
        '        )\n',
        "test source mode",
    )
    text, count = re.subn(
        r"    def test_quarter_inventory_guard_is_fail_closed\(self\):.*?"
        r"    def test_parser_preserves_trade_count_and_provider_gaps",
        "    def test_rest_tail_is_selected_for_missing_quarter_seam(self):\n"
        "        self.assertEqual(\n"
        "            \"KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL\",\n"
        "            backfill.SOURCE_MODE,\n"
        "        )\n"
        "        self.assertEqual(\"https://api.kraken.com/0/public/Trades\", backfill.rest_trades.ENDPOINT)\n"
        "        self.assertGreater(backfill.rest_trades.OVERLAP_NS, 0)\n\n"
        "    def test_parser_preserves_trade_count_and_provider_gaps",
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError(f"test quarter guard replacement: {count}")
    text = replace_once(
        text,
        '            self.assertEqual("KRAKEN_TIME_SALES_DERIVED_OHLCVT", payload["source_semantics"])\n',
        '            self.assertEqual(\n'
        '                "KRAKEN_TIME_SALES_PLUS_REST_TRADES_DERIVED_OHLCVT",\n'
        '                payload["source_semantics"],\n'
        '            )\n',
        "test source semantics",
    )
    path.write_text(text, encoding="utf-8")


def patch_contract() -> None:
    path = Path("contracts/provider-contracts.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    target = next(
        item
        for item in payload["contracts"]
        if item.get("contract_id") == "KRAKEN_SPOT_HISTORICAL_TIME_SALES_V1"
    )
    target.update(
        {
            "contract_id": "KRAKEN_SPOT_HISTORICAL_TRADE_SOURCES_V1",
            "endpoint": (
                "Official downloadable Time & Sales archives for bulk history; bounded REST "
                "/0/public/Trades tail completion from latest archive trade through canonical WARM/cutoff seam"
            ),
            "historical_support": "MARKET_INCEPTION_ARCHIVE_PLUS_BOUNDED_REST_TRADES_TAIL_TO_CANONICAL_WARM",
            "purpose": (
                "internal official trade-source authority for the existing history-kraken-spot-v2 publisher; "
                "Time & Sales supplies bulk history and REST Trades closes only the bounded post-archive seam; "
                "no consumer/provider route change"
            ),
            "rate_limit": (
                "REST Trades is used only for bounded post-archive seam completion with official result.last "
                "cursor pagination, conservative pacing, bounded retries and hard MAX_PAGES; it is not used "
                "for 2015-to-present bulk crawling"
            ),
            "selected_source_mode": "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL",
            "source_gap_semantics": (
                "PROVIDER_NO_TRADE_OMISSION only inside physically contiguous archive+REST trade coverage; "
                "missing REST page, non-advancing cursor, timestamp regression or failure to cross requested "
                "end is ACQUISITION_GAP and fail-closed; synthetic_fill=false"
            ),
            "source_ordering_semantics": (
                "archive provider row order is retained for equal timestamps; REST provider response row order "
                "is retained and result.last must advance monotonically; timestamp regression fails closed"
            ),
            "source_seam_semantics": (
                "REST acquisition starts with a bounded overlap before the exact latest archive trade; "
                "independently derived 5m/1d overlap must match archive OHLCVT before tail-only rows are merged; "
                "WARM overlap is separately required before publication"
            ),
            "physical_rest_tail_qualification": "RUN_33812044395_Q2_Q3_PRE_WARM_POINT_PROBES_PASS",
        }
    )
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def patch_docs() -> None:
    path = Path("docs/semantics/capability-index.md")
    text = path.read_text(encoding="utf-8")
    old = '''Source-code support для `history-kraken-spot-v2` реализован под существующей D6 semantic boundary, но **не активирован**. Selected internal source mode — `KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE`; он не создаёт новый catalog/resolver/reader и не меняет `series_id`.

До verified publication текущий derived capability index обязан сохранять Kraken Spot profile как `PROVIDER_LIMITED` / `history-kraken-spot-v1`. Переход к `MAX_AVAILABLE` / `PASS` разрешён только после физически непрерывного official Time & Sales source inventory до M5 WARM boundary, deterministic Build A/B, WARM overlap, immutable Release read-back, successor manifest install и canonical consumer proof. Отсутствующая quarterly partition классифицируется как acquisition gap, а не как provider no-trade omission.'''
    new = '''Source-code support для `history-kraken-spot-v2` реализован под существующей D6 semantic boundary, но **не активирован**. Selected internal source mode — `KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL`: официальный Time & Sales остаётся bulk authority от market inception, а официальный `/0/public/Trades` используется только как bounded tail-completion от последнего archive trade через canonical M5 WARM/cutoff seam. Это не создаёт новый catalog/resolver/reader и не меняет `series_id`.

Physical REST qualification run `33812044395` доказал доступность ETHUSD начиная с `2026-04-01`, `2026-07-01` и непосредственно перед canonical WARM (`2026-08-12T06:30:00Z`), monotonic `since → result.last` pagination и provider result identity `XETHZUSD`. Production publisher обязан freeze-ить REST tail один раз, проверять archive↔REST overlap на независимо derived 5m/1d buckets, затем строить deterministic Build A/B из одного frozen hybrid source set и отдельно доказывать overlap с существующим WARM.

До verified publication текущий derived capability index обязан сохранять Kraken Spot profile как `PROVIDER_LIMITED` / `history-kraken-spot-v1`. Переход к `MAX_AVAILABLE` / `PASS` разрешён только после физически непрерывного combined archive+REST source coverage, deterministic Build A/B, source-seam overlap, WARM overlap, immutable Release read-back, successor manifest install и canonical consumer proof. Missing quarterly ZIP сам по себе больше не является terminal blocker; missing/non-advancing REST page или недоказанный seam остаётся acquisition gap и не может быть объявлен provider no-trade omission.'''
    path.write_text(replace_once(text, old, new, "capability docs"), encoding="utf-8")


def patch_agents() -> None:
    path = Path("AGENTS.md")
    text = path.read_text(encoding="utf-8")
    old = '''`history-kraken-spot-v2` использует один существующий canonical publisher `tools/deep_history/kraken_spot_ohlcvt_backfill.py`. Внутренний selected source mode — `KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE`: официальный Kraken Time & Sales trade history freeze-ится один раз, из тех же frozen bytes детерминированно строятся 5m/1d OHLCVT и затем используется существующая Release/manifest/capability/resolver/reader цепочка.

Это **IMPLEMENTED_NOT_ACTIVE** до owner merge и физически непрерывного official source inventory через canonical Kraken ETHUSD M5 WARM boundary. Missing quarterly partition является `MISSING_PARTITION`/acquisition gap и fail-closed; он не может быть объявлен `PROVIDER_NO_TRADE_OMISSION`.'''
    new = '''`history-kraken-spot-v2` использует один существующий canonical publisher `tools/deep_history/kraken_spot_ohlcvt_backfill.py`. Внутренний selected source mode — `KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL`: официальный Kraken Time & Sales freeze-ится как bulk source, а официальный `/0/public/Trades` разрешён только как bounded post-archive tail-completion до canonical WARM/cutoff. REST pagination использует только provider `result.last`, freeze-ится один раз и не становится consumer route.

Это **IMPLEMENTED_NOT_ACTIVE** до owner merge и физически непрерывного combined official source coverage через canonical Kraken ETHUSD M5 WARM boundary. Archive↔REST overlap и REST↔WARM overlap обязательны. Missing quarterly ZIP может быть закрыт bounded REST tail; missing/non-advancing REST page, timestamp regression или недоказанный seam является acquisition gap и fail-closed и не может быть объявлен `PROVIDER_NO_TRADE_OMISSION`.'''
    path.write_text(replace_once(text, old, new, "AGENTS source policy"), encoding="utf-8")


if __name__ == "__main__":
    patch_time_sales()
    patch_backfill()
    patch_tests()
    patch_contract()
    patch_docs()
    patch_agents()
    print("KRAKEN_HYBRID_PATCH=MATERIALIZED")
