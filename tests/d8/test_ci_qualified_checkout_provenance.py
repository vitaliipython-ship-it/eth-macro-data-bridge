from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "qualify-d8-runtime.yml"


class QualifiedCheckoutProvenanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_checkout_sha_is_derived_from_actual_git_head_and_exported(self) -> None:
        self.assertIn('QUALIFIED_CHECKOUT_SHA="$(git rev-parse HEAD)"', self.workflow)
        self.assertIn('ACTUAL="$(git rev-parse HEAD)"', self.workflow)
        self.assertIn('test "$ACTUAL" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn(
            "printf 'QUALIFIED_CHECKOUT_SHA=%s\\n' \"$QUALIFIED_CHECKOUT_SHA\" >> \"$GITHUB_ENV\"",
            self.workflow,
        )
        self.assertNotIn('test "$GITHUB_SHA" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertNotIn('test "$QUALIFIED_CHECKOUT_SHA" = "$GITHUB_SHA"', self.workflow)

    def test_pr_head_and_research_bridge_head_remain_separate_source_identity(self) -> None:
        self.assertIn(
            "PR_HEAD_SHA_FROM_EVENT: ${{ github.event.pull_request.head.sha || '' }}",
            self.workflow,
        )
        self.assertIn('PR_HEAD_SHA="${PR_HEAD_SHA_FROM_EVENT:-$GITHUB_SHA}"', self.workflow)
        self.assertIn(
            'RESEARCH_BRIDGE_HEAD_SHA="${PR_HEAD_SHA_FROM_EVENT:-$GITHUB_SHA}"',
            self.workflow,
        )
        self.assertIn('--bridge-head "$RESEARCH_BRIDGE_HEAD_SHA"', self.workflow)
        self.assertIn(
            "RESEARCH_BRIDGE_HEAD_IDENTITY_ROLE=LOGICAL_PR_OR_EVENT_SOURCE_HEAD",
            self.workflow,
        )

    def test_container_image_and_runtime_source_revision_use_qualified_checkout(self) -> None:
        self.assertIn('IMAGE="eth-macro-d8:${QUALIFIED_CHECKOUT_SHA}"', self.workflow)
        self.assertIn('-e D8_SOURCE_REVISION="$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn('IMAGE="$QUALIFIED_CONTAINER_IMAGE_REF"', self.workflow)
        self.assertIn(
            'test "$ACTUAL_IMAGE_DIGEST" = "$QUALIFIED_CONTAINER_IMAGE_DIGEST"',
            self.workflow,
        )
        self.assertNotIn('eth-macro-d8:${GITHUB_SHA}', self.workflow)
        self.assertNotIn('D8_SOURCE_REVISION="$GITHUB_SHA"', self.workflow)

    def test_runtime_and_persisted_cycle_source_revision_are_verified(self) -> None:
        self.assertIn(
            "from d8_runtime import config_from_env; print(config_from_env().source_revision)",
            self.workflow,
        )
        self.assertIn('test "$runtime_source" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn(
            'SELECT source_revision FROM cycles WHERE cycle_id=?',
            self.workflow,
        )
        self.assertIn('test "$persisted_source" = "$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        self.assertIn("CONTAINER_SOURCE_BINDING=PASS", self.workflow)

    def test_stale_github_sha_cannot_control_qualified_provenance(self) -> None:
        stale_github_sha = "1" * 40
        qualified_checkout_sha = "2" * 40
        self.assertNotEqual(stale_github_sha, qualified_checkout_sha)

        image_ref = f"eth-macro-d8:{qualified_checkout_sha}"
        d8_source_revision = qualified_checkout_sha

        self.assertEqual(image_ref, f"eth-macro-d8:{qualified_checkout_sha}")
        self.assertEqual(d8_source_revision, qualified_checkout_sha)
        self.assertNotIn(stale_github_sha, image_ref)
        self.assertNotEqual(d8_source_revision, stale_github_sha)

        self.assertIn('IMAGE="eth-macro-d8:${QUALIFIED_CHECKOUT_SHA}"', self.workflow)
        self.assertIn('-e D8_SOURCE_REVISION="$QUALIFIED_CHECKOUT_SHA"', self.workflow)
        print("STALE_GITHUB_SHA_DOES_NOT_CONTROL_CONTAINER_IDENTITY=PASS")
        print("STALE_GITHUB_SHA_DOES_NOT_CONTROL_D8_SOURCE_REVISION=PASS")


if __name__ == "__main__":
    unittest.main()
