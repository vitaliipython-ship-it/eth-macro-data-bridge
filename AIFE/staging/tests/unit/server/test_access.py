"""F3 access regression plus F5 exact-generation fail-closed semantics."""

from types import SimpleNamespace

import pytest

from server.access import (
    AccessError,
    AccessProvenance,
    AccessResult,
    AccessResultPage,
    AccessSourceRevision,
    PaginationCursor,
    ResultCompleteness,
    ResultIdentity,
    SnapshotIdentity,
)
from server.access.models import (
    ExactGenerationIdentityMismatch,
    ExactGenerationNotFound,
    ExactGenerationRequest,
    resolve_exact_generation,
)


def test_result_identity_and_provenance_are_preserved():
    """Exercise the mapped F5 acceptance case."""
    r = AccessResult(
        ("item-1",),
        ResultIdentity("result-1"),
        AccessSourceRevision("source-r1"),
        AccessProvenance("publication:1"),
        ResultCompleteness.COMPLETE,
        SnapshotIdentity("snapshot-1"),
        AccessResultPage(next_cursor=PaginationCursor("cursor-1")),
    )
    assert r.result_identity.value == "result-1" and r.source_revision.value == "source-r1"


def test_partial_and_failed_results_are_unambiguous():
    """Exercise the mapped F5 acceptance case."""
    p = AccessResult(
        ("item-1",),
        ResultIdentity("result-1"),
        AccessSourceRevision("source-r1"),
        AccessProvenance("publication:1"),
        ResultCompleteness.PARTIAL,
        page=AccessResultPage(
            errors=(AccessError("partition_unavailable", "p2 unavailable"),),
            unavailable_partitions=("p2",),
        ),
    )
    assert p.completeness is ResultCompleteness.PARTIAL
    with pytest.raises(ValueError):
        AccessResult(
            ("item",),
            ResultIdentity("r2"),
            AccessSourceRevision("s"),
            AccessProvenance("p"),
            ResultCompleteness.PARTIAL,
        )


class Repo:
    """Test helper `Repo` for the bounded F5 acceptance contour."""

    def __init__(self, row=None):
        """Exercise the mapped F5 acceptance case."""
        self.row = row
        self.calls = []

    def resolve_generation(self, scope, generation_identity=None):
        """Exercise the mapped F5 acceptance case."""
        self.calls.append((scope, generation_identity))
        return self.row


def test_exact_generation_never_falls_back_to_current():
    """Exercise the mapped F5 acceptance case."""
    repo = Repo()
    req = ExactGenerationRequest("artifact-a", "gen-old", "rev-old", "abc")
    with pytest.raises(ExactGenerationNotFound):
        resolve_exact_generation(repo, req)
    assert repo.calls == [("artifact-a", "gen-old")]


def test_exact_generation_checks_revision_and_content():
    """Exercise the mapped F5 acceptance case."""
    row = SimpleNamespace(
        generation_scope_identity="artifact-a",
        generation_identity="gen-old",
        generation_no=1,
        publication_id="p",
        source_revision="rev-new",
        content_checksum="abc",
        content_size=3,
        physical_locator="sha256/ab/abc",
    )
    with pytest.raises(ExactGenerationIdentityMismatch):
        resolve_exact_generation(Repo(row), ExactGenerationRequest("artifact-a", "gen-old", "rev-old", "abc"))
