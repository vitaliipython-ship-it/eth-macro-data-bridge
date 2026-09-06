from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "probe-kraken-overlap.yml"
LIVE_COMMAND = "python tools/deep_history/qualify_kraken_overlap_policy.py"


def _top_level_block(text: str, key: str) -> str:
    marker = f"{key}:\n"
    start = text.index(marker)
    tail = text[start + len(marker) :]
    lines = tail.splitlines(keepends=True)
    block = []
    for line in lines:
        if line and not line.startswith((" ", "\t", "\n", "\r")):
            break
        block.append(line)
    return "".join(block)


def _job_block(text: str, job_name: str) -> str:
    jobs = _top_level_block(text, "jobs")
    marker = f"  {job_name}:\n"
    start = jobs.index(marker)
    tail = jobs[start + len(marker) :]
    lines = tail.splitlines(keepends=True)
    block = []
    for line in lines:
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            break
        block.append(line)
    return "".join(block)


class ProbeKrakenOverlapWorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.on = _top_level_block(cls.text, "on")
        cls.offline = _job_block(cls.text, "offline_policy")
        cls.live = _job_block(cls.text, "live_policy")

    def test_probe_push_trigger_exists(self):
        self.assertIn("  push:\n", self.on)
        self.assertIn("  workflow_dispatch:\n", self.on)

    def test_probe_offline_policy_on_push(self):
        self.assertIn("Run offline policy tests", self.offline)
        self.assertNotIn(LIVE_COMMAND, self.offline)
        self.assertNotIn("github.event_name == 'workflow_dispatch'", self.offline)

    def test_probe_live_policy_push_unreachable(self):
        self.assertIn("if: github.event_name == 'workflow_dispatch'", self.live)
        self.assertIn(LIVE_COMMAND, self.live)
        self.assertEqual(self.text.count(LIVE_COMMAND), 1)

    def test_probe_live_policy_workflow_dispatch_reachable(self):
        self.assertIn("  workflow_dispatch:\n", self.on)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", self.live)
        self.assertIn(LIVE_COMMAND, self.live)


if __name__ == "__main__":
    unittest.main()
