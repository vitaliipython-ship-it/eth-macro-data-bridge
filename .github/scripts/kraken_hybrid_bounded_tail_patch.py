from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {text.count(old)}")
    return text.replace(old, new, 1)


def main() -> None:
    backfill = Path("tools/deep_history/kraken_spot_ohlcvt_backfill.py")
    text = backfill.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'GENERATED = ROOT / "release-manifest.generated.json"\n',
        'GENERATED = ROOT / "release-manifest.generated.json"\n'
        'REST_WARM_OVERLAP_MS = 4 * 86_400_000\n',
        "warm overlap constant",
    )
    marker = '''def acquire_archive(
    destination: Path = ARCHIVE,
'''
    helper = '''def _rest_tail_end_ms(cutoff_ms: int, warm_first_ms: int) -> int:
    return min(int(cutoff_ms), int(warm_first_ms) + REST_WARM_OVERLAP_MS)


def acquire_archive(
    destination: Path = ARCHIVE,
'''
    text = replace_once(text, marker, helper, "rest tail end helper")
    text = replace_once(
        text,
        '    rest_end_ns = int(cutoff_ms) * 1_000_000\n',
        '    rest_end_ms = _rest_tail_end_ms(cutoff_ms, warm_first_ms)\n'
        '    rest_end_ns = rest_end_ms * 1_000_000\n',
        "bounded REST end",
    )
    text = replace_once(
        text,
        '            "coverage_declared_end_ms": cutoff_ms,\n',
        '            "coverage_declared_end_ms": rest_end_ms,\n'
        '            "rest_tail_coverage_end_ms": rest_end_ms,\n',
        "bounded coverage metadata",
    )
    text = replace_once(
        text,
        '    print(f"KRAKEN_OHLCVT_REST_TAIL_OVERLAP_NS={rest_trades.OVERLAP_NS}")\n',
        '    print(f"KRAKEN_OHLCVT_REST_TAIL_OVERLAP_NS={rest_trades.OVERLAP_NS}")\n'
        '    print(f"KRAKEN_OHLCVT_REST_WARM_OVERLAP_MS={REST_WARM_OVERLAP_MS}")\n',
        "bounded plan marker",
    )
    backfill.write_text(text, encoding="utf-8")

    tests = Path("tests/deep_history/test_kraken_spot_ohlcvt_backfill.py")
    text = tests.read_text(encoding="utf-8")
    insert = '''
    def test_rest_tail_end_is_bounded_to_warm_overlap(self):
        warm = 1_800_000_000_000
        far_cutoff = warm + 30 * 86_400_000
        self.assertEqual(
            warm + backfill.REST_WARM_OVERLAP_MS,
            backfill._rest_tail_end_ms(far_cutoff, warm),
        )
        near_cutoff = warm + 2 * 86_400_000
        self.assertEqual(near_cutoff, backfill._rest_tail_end_ms(near_cutoff, warm))

'''
    text = replace_once(
        text,
        '\n\nif __name__ == "__main__":\n',
        '\n' + insert + '\nif __name__ == "__main__":\n',
        "bounded tail test insertion",
    )
    tests.write_text(text, encoding="utf-8")
    print("KRAKEN_HYBRID_BOUNDED_TAIL_PATCH=MATERIALIZED")


if __name__ == "__main__":
    main()
