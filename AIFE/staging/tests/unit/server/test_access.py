"""Проверки ACCESS-контракта F3."""

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


def test_result_identity_and_provenance_are_preserved() -> None:
    """Проверить сохранение identity и provenance результата."""
    result = AccessResult(
        items=("item-1",),
        result_identity=ResultIdentity("result-1"),
        source_revision=AccessSourceRevision("source-r1"),
        provenance=AccessProvenance("publication:1"),
        completeness=ResultCompleteness.COMPLETE,
        snapshot_identity=SnapshotIdentity("snapshot-1"),
        page=AccessResultPage(next_cursor=PaginationCursor("cursor-1")),
    )
    assert result.result_identity.value == "result-1"
    assert result.source_revision.value == "source-r1"
    assert result.provenance.value == "publication:1"


def test_partial_and_failed_results_are_unambiguous() -> None:
    """Проверить однозначность partial и failed результатов."""
    partial = AccessResult(
        items=("item-1",),
        result_identity=ResultIdentity("result-1"),
        source_revision=AccessSourceRevision("source-r1"),
        provenance=AccessProvenance("publication:1"),
        completeness=ResultCompleteness.PARTIAL,
        page=AccessResultPage(
            errors=(AccessError("partition_unavailable", "partition p2 unavailable"),),
            unavailable_partitions=("p2",),
        ),
    )
    assert partial.completeness is ResultCompleteness.PARTIAL
    with pytest.raises(ValueError):
        AccessResult(
            items=("item-1",),
            result_identity=ResultIdentity("result-2"),
            source_revision=AccessSourceRevision("source-r1"),
            provenance=AccessProvenance("publication:1"),
            completeness=ResultCompleteness.PARTIAL,
        )
