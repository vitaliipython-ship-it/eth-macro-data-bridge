from __future__ import annotations

import unittest

from tools.current_tail_admission import CurrentTailAdmissionError, _generated_at_utc


class CurrentTailGeneratedAtUtcTests(unittest.TestCase):
    def test_v11_projects_exact_canonical_manifest_time(self) -> None:
        generation = {
            "schema_version": "fresh-current-generation/1.1.0",
            "ordinary_generation": {
                "data_manifest_generated_at_utc": "2026-08-31T22:38:50.679Z",
            },
        }

        value, epoch_ms = _generated_at_utc(generation)

        self.assertEqual(value, "2026-08-31T22:38:50.679Z")
        self.assertEqual(epoch_ms, 1788215930679)

    def test_v10_legacy_projection_is_preserved(self) -> None:
        generation = {
            "schema_version": "fresh-current-generation/1.0.0",
            "generated_at_utc": "2026-08-31T10:40:00Z",
        }

        value, epoch_ms = _generated_at_utc(generation)

        self.assertEqual(value, "2026-08-31T10:40:00Z")
        self.assertEqual(epoch_ms, 1788172800000)

    def test_missing_v11_manifest_time_fails_closed_without_fabrication(self) -> None:
        generation = {
            "schema_version": "fresh-current-generation/1.1.0",
            "ordinary_generation": {},
        }

        with self.assertRaises(CurrentTailAdmissionError) as caught:
            _generated_at_utc(generation)

        self.assertEqual(caught.exception.code, "CURRENT_TAIL_TIME_INVALID")
        self.assertIn("ordinary_generation.data_manifest_generated_at_utc", str(caught.exception))

    def test_missing_v11_ordinary_generation_fails_closed(self) -> None:
        generation = {"schema_version": "fresh-current-generation/1.1.0"}

        with self.assertRaises(CurrentTailAdmissionError) as caught:
            _generated_at_utc(generation)

        self.assertEqual(caught.exception.code, "CURRENT_TAIL_GENERATION_INVALID")

    def test_unknown_generation_schema_fails_closed(self) -> None:
        generation = {"schema_version": "fresh-current-generation/9.9.9"}

        with self.assertRaises(CurrentTailAdmissionError) as caught:
            _generated_at_utc(generation)

        self.assertEqual(caught.exception.code, "CURRENT_TAIL_GENERATION_INVALID")


if __name__ == "__main__":
    unittest.main()
