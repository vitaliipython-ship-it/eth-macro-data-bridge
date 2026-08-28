from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / ".github/workflows/current-data-request.yml"
SCHEDULED = ROOT / ".github/workflows/update-market.yml"


class FreshCurrentConcurrencyTests(unittest.TestCase):
    def test_production_acquisition_stays_serialized_with_hourly_publisher(self):
        current = CURRENT.read_text(encoding="utf-8")
        scheduled = SCHEDULED.read_text(encoding="utf-8")
        self.assertIn("group: market-bridge-update", current)
        self.assertIn("group: market-bridge-update", scheduled)
        self.assertIn("cancel-in-progress: false", current)

    def test_pull_request_qualification_cannot_cancel_pending_real_acceptance(self):
        current = CURRENT.read_text(encoding="utf-8")
        self.assertIn("group: market-bridge-update${{", current)
        self.assertIn("github.event_name == 'pull_request'", current)
        self.assertIn("format('-pr-{0}', github.event.pull_request.number)", current)
        self.assertIn("|| ''", current)


if __name__ == "__main__":
    unittest.main()
