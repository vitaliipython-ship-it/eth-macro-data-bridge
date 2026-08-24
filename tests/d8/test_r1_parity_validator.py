from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class R1ParityValidatorCase(unittest.TestCase):
    def test_fail_closed_parity_validator(self):
        subprocess.run(
            [sys.executable, "tools/validation/validate_d8_r1_parity.py"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
