from __future__ import annotations

import math
import unittest

from canonical_json import canonical_json_bytes


class CanonicalJsonTests(unittest.TestCase):
    def test_standard_values_sorted_unicode_and_no_trailing_newline(self):
        encoded = canonical_json_bytes({"z": "Δ", "a": None, "n": 7, "ok": True})
        self.assertEqual(encoded, b'{"a":null,"n":7,"ok":true,"z":"\xce\x94"}')
        self.assertFalse(encoded.endswith(b"\n"))

    def test_non_finite_values_fail_closed(self):
        for name, value in (
            ("nan", math.nan),
            ("positive-infinity", math.inf),
            ("negative-infinity", -math.inf),
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    canonical_json_bytes({"value": value})


if __name__ == "__main__":
    unittest.main()
