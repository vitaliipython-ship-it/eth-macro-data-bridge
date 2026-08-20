from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from d8_d9_forwarder_integrity import D8ToD9Forwarder as IntegrityBoundD8Source
from github_history_publication import GitHubFirstV1Adapter, GitHubHTTPTransport
from history_publication_port import (
    BoundedPublicationBatchPolicy,
    HistoryPublicationPort,
    PublicationPortError,
    build_batch_from_pending,
)

CANONICAL_FORWARD_SCHEMA = "d8-d9-canonical-publication-forward/1.0.0"


class CanonicalForwardError(PublicationPortError):
    """Fail-closed canonical D8 PENDING -> FORWARDED transition violation."""


class CanonicalD8ToD9Forwarder:
    """Integrity-bound D8 source plus canonical remote publication ACK transition."""

    def __init__(
        self,
        state_root: Path,
        publication_port: HistoryPublicationPort,
        *,
        batch_policy: BoundedPublicationBatchPolicy | None = None,
        forwarded_retention_seconds: int = 7 * 86400,
    ):
        self.state_root = Path(state_root)
        self.publication_port = publication_port
        self.batch_policy = batch_policy or BoundedPublicationBatchPolicy()
        # The inherited source validates SQLite/checkpoint evidence and owns the
        # atomic PENDING->FORWARDED transaction. Its warm_root is deliberately
        # unused on the canonical remote publication path.
        self.source = IntegrityBoundD8Source(
            self.state_root,
            self.state_root / ".canonical-publication-local-warm-unused",
            forwarded_retention_seconds=forwarded_retention_seconds,
        )

    def forward_pending(
        self,
        *,
        expected_remote_base: str,
        now_ms: int | None = None,
        force_batch: bool = False,
        failpoint: Any | None = None,
    ) -> dict[str, Any]:
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        read_limit = max(self.batch_policy.max_observations, self.batch_policy.spool_pressure_count)
        pending = self.source._pending(read_limit)
        selected = self.batch_policy.select(pending, now_ms=now_ms, force=force_batch)
        if not selected:
            return {
                "schema_version": CANONICAL_FORWARD_SCHEMA,
                "batch_id": None,
                "canonical_publication_ack": "NOOP",
                "ack_state": "NOOP",
                "accepted_observation_ids": [],
                "provider_reacquisition_count": 0,
                "provider_fallback_count": 0,
                "synthetic_fill_count": 0,
            }
        batch, envelopes = build_batch_from_pending(selected)
        ack = self.publication_port.publish(
            batch,
            envelopes,
            expected_remote_base=expected_remote_base,
            failpoint=failpoint,
        )
        if ack.get("ack_state") != "PASS" or ack.get("partial_ack") is not False:
            raise CanonicalForwardError("CANONICAL_PUBLICATION_ACK did not PASS as a whole batch")
        expected_ids = batch["member_observation_ids"]
        if ack.get("accepted_observation_ids") != expected_ids:
            raise CanonicalForwardError("CANONICAL_PUBLICATION_ACK membership mismatch")
        if failpoint:
            failpoint("after_canonical_ack_before_d8_ack")
        self.source._mark_forwarded(expected_ids, now_ms)
        return {
            "schema_version": CANONICAL_FORWARD_SCHEMA,
            "batch_id": batch["batch_id"],
            "canonical_publication_ack": "PASS",
            "ack_state": "ACKED",
            "accepted_observation_ids": expected_ids,
            "publication_ack": ack,
            "provider_reacquisition_count": 0,
            "provider_fallback_count": 0,
            "synthetic_fill_count": 0,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Canonical D8 spool -> GITHUB_FIRST_V1 WARM publication forwarder (source candidate, not activated)"
    )
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--repository", default="vitaliipython-ship-it/eth-macro-data-bridge")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--expected-remote-base")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--force-batch", action="store_true")
    parser.add_argument("--max-observations", type=int, default=500)
    parser.add_argument("--max-serialized-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--max-oldest-age-seconds", type=int, default=300)
    parser.add_argument("--spool-pressure-count", type=int, default=1000)
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args(argv)

    token = os.environ.get(args.token_env)
    transport = GitHubHTTPTransport(args.repository, args.branch, token=token)
    expected_remote_base = args.expected_remote_base or transport.read_head()
    backend = GitHubFirstV1Adapter(transport)
    port = HistoryPublicationPort(backend)
    policy = BoundedPublicationBatchPolicy(
        max_observations=args.max_observations,
        max_serialized_bytes=args.max_serialized_bytes,
        max_oldest_age_seconds=args.max_oldest_age_seconds,
        spool_pressure_count=args.spool_pressure_count,
    )
    forwarder = CanonicalD8ToD9Forwarder(Path(args.state_root), port, batch_policy=policy)
    result = forwarder.forward_pending(
        expected_remote_base=expected_remote_base,
        now_ms=args.now_ms,
        force_batch=args.force_batch,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
