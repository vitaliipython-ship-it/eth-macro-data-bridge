from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "qualify-d8-runtime.yml"


class QualifiedCheckoutProvenanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_checkout_matches_event_tested_object(self) -> None:
        self.assertIn('QUALIFIED_CHECKOUT_SHA="$(git rev-parse HEAD)"', self.workflow)
        self.assertIn('ACTUAL="$(git rev-parse HEAD)"', self.workflow)
        self.assertIn('test "$ACTUAL" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn('test "$QUALIFIED_CHECKOUT_SHA" = "$GITHUB_SHA"', self.workflow)
        self.assertIn("ACTUAL_CHECKOUT_SHA_MATCH=PASS", self.workflow)
        self.assertIn("PHYSICAL_IDENTITY_PROOF=PASS", self.workflow)

    def test_actual_tested_pr_head_matches_event_logical_head(self) -> None:
        self.assertIn("EVENT_PR_HEAD_SHA: ${{ github.event.pull_request.head.sha || '' }}", self.workflow)
        self.assertIn('ACTUAL_TESTED_PR_HEAD_SHA="${parents[1]}"', self.workflow)
        self.assertIn('test "$ACTUAL_TESTED_PR_HEAD_SHA" = "$EVENT_PR_HEAD_SHA"', self.workflow)
        self.assertIn("ACTUAL_TESTED_PR_HEAD_EQUALS_EVENT_PR_HEAD=PASS", self.workflow)
        self.assertIn('RESEARCH_BRIDGE_HEAD_SHA="${EVENT_PR_HEAD_SHA:-$GITHUB_SHA}"', self.workflow)
        self.assertIn('--bridge-head "$RESEARCH_BRIDGE_HEAD_SHA"', self.workflow)

    def test_event_base_is_metadata_not_parent1_authority(self) -> None:
        self.assertIn("EVENT_PR_BASE_SHA: ${{ github.event.pull_request.base.sha || '' }}", self.workflow)
        self.assertIn('ACTUAL_TESTED_BASE_SHA="${parents[0]}"', self.workflow)
        self.assertIn("EVENT_PR_BASE_SHA_ROLE=EVENT_METADATA_ONLY", self.workflow)
        self.assertIn("ACTUAL_TESTED_BASE_SHA_ROLE=SYNTHETIC_PARENT1", self.workflow)
        self.assertNotIn('test "$ACTUAL_TESTED_BASE_SHA" = "$EVENT_PR_BASE_SHA"', self.workflow)
        self.assertNotIn('test "${parents[0]}" = "$PR_BASE_SHA_FROM_EVENT"', self.workflow)

    def test_moving_base_is_allowed(self) -> None:
        self.assertIn("SCENARIO_MOVING_BASE=PASS", self.workflow)
        self.assertIn("EVENT_BASE_DIFFERS_FROM_ACTUAL_TESTED_BASE=YES", self.workflow)

    def test_head_substitution_is_rejected(self) -> None:
        self.assertIn("SCENARIO_HEAD_SUBSTITUTION=FAIL_EXPECTED", self.workflow)
        self.assertIn('test "$actual_head" = "$event_head"', self.workflow)

    def test_container_identity_uses_qualified_checkout(self) -> None:
        self.assertIn('IMAGE="eth-macro-d8:${QUALIFIED_CHECKOUT_SHA}"', self.workflow)
        self.assertIn('IMAGE="$QUALIFIED_CONTAINER_IMAGE_REF"', self.workflow)
        self.assertIn('test "$ACTUAL_IMAGE_DIGEST" = "$QUALIFIED_CONTAINER_IMAGE_DIGEST"', self.workflow)
        self.assertNotIn('eth-macro-d8:${GITHUB_SHA}', self.workflow)

    def test_runtime_source_revision_uses_qualified_checkout(self) -> None:
        self.assertIn('-e D8_SOURCE_REVISION="$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn('test "$runtime_source" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn('test "$persisted_source" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertNotIn('D8_SOURCE_REVISION="$GITHUB_SHA"', self.workflow)

    def test_non_pr_behavior_remains_valid(self) -> None:
        self.assertIn("NON_PR_BEHAVIOR=PASS", self.workflow)
        self.assertIn('if [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]; then', self.workflow)
        self.assertIn('echo "PR_EFFECTIVE_INTEGRATION_BINDING=N/A"', self.workflow)
        self.assertIn('PR_HEAD_SHA="${EVENT_PR_HEAD_SHA:-$GITHUB_SHA}"', self.workflow)


if __name__ == "__main__":
    unittest.main()
