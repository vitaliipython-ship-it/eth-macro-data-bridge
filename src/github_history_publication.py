from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Protocol

from canonical_json import canonical_json_bytes
from d8_capability_routing import route_capability_series
from history_publication_port import GITHUB_FIRST_V1, PORT_EVIDENCE_SCHEMA, PublicationPortError

DATA_SCHEMA = "market-data-d8-origin-github-warm/1.0.0"
CONTROL_SCHEMA = "market-data-d8-origin-publication-manifest/1.0.0"
REPRESENTATION = "EXACT_D8_ENVELOPE"
CONTROL_PATH = "history/d8-origin/manifest.json"
RESOURCE_ROOT = "history/d8-origin/resources"
SOURCE_AUTHORITY_PREFIXES = ("src/", "tools/", "tests/", "contracts/", "schema/", "docs/", ".github/")
SOURCE_AUTHORITY_FILES = {"AGENTS.md", "bridge-contract.json"}
ELIGIBLE_D8_PUBLICATION_POLICIES = {"VALIDATED_TERMINAL_CHECKPOINT_V2"}
INTERVAL_MS = {"5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000, "1d": 86400000, "1w": 604800000}


class GitHubPublicationError(PublicationPortError):
    """Fail-closed GITHUB_FIRST_V1 publication failure."""


class GitHubCASConflict(GitHubPublicationError):
    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(f"GitHub CAS conflict expected={expected} actual={actual}")


class GitHubRepositoryTransport(Protocol):
    repository: str
    branch: str

    def read_head(self) -> str: ...
    def read_file(self, path: str, ref: str) -> bytes | None: ...
    def commit_files(self, expected_head: str, files: dict[str, bytes], message: str) -> str: ...
    def compare_paths(self, base: str, head: str) -> list[str]: ...
    def download_archive(self, ref: str) -> bytes: ...


def _compact(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_utc_ms(value: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GitHubPublicationError("publication timestamp must be UTC RFC3339 with Z")
    try:
        from datetime import datetime
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GitHubPublicationError(f"invalid publication timestamp: {value}") from exc
    return int(parsed.timestamp() * 1000)


def _effective_timestamp_ms(envelope: dict[str, Any], lifecycle_class: str) -> int:
    if lifecycle_class == "FIXED_GRID":
        value = envelope.get("value")
        if isinstance(value, dict) and isinstance(value.get("open_time_ms"), int):
            return int(value["open_time_ms"])
        source = envelope.get("provider_timestamp_at") or envelope.get("canonical_slot")
    else:
        source = envelope.get("canonical_slot") or envelope.get("known_at")
    if not isinstance(source, str):
        raise GitHubPublicationError("D8 envelope lacks effective publication timestamp")
    return _parse_utc_ms(source)


def _interval_ms(series_id: str, normalization_family: str, lifecycle_class: str) -> int | None:
    if lifecycle_class != "FIXED_GRID":
        return None
    suffix = series_id.rsplit(".", 1)[-1]
    value = INTERVAL_MS.get(suffix)
    if value is None:
        raise GitHubPublicationError(
            f"fixed-grid publication interval is not derivable from declared series: {series_id}:{normalization_family}"
        )
    return value


def _resource_path(batch_id: str) -> str:
    if not isinstance(batch_id, str) or not batch_id.startswith("pub-"):
        raise GitHubPublicationError("invalid PublicationBatch identity for GitHub resource")
    return f"{RESOURCE_ROOT}/{batch_id}.json"


def materialize_data_resource(batch: dict[str, Any], envelopes: list[dict[str, Any]]) -> tuple[str, bytes]:
    by_id = {row["observation_id"]: row for row in envelopes}
    try:
        ordered = [by_id[oid] for oid in batch["member_observation_ids"]]
    except KeyError as exc:
        raise GitHubPublicationError("PublicationBatch member missing from D8 envelopes") from exc
    payload = {
        "schema_version": DATA_SCHEMA,
        "representation": REPRESENTATION,
        "batch_id": batch["batch_id"],
        "target_residence_role": "WARM",
        "member_count": batch["member_count"],
        "member_observation_ids": batch["member_observation_ids"],
        "membership_sha256": batch["membership_sha256"],
        "payload_sha256": batch["payload_sha256"],
        "observations": ordered,
    }
    return _resource_path(batch["batch_id"]), _compact(payload)


def _series_bindings(batch: dict[str, Any], envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_series: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for envelope in envelopes:
        routing = route_capability_series(envelope["capability_id"], envelope["provider"], envelope["series_id"])
        if (
            routing["publication_eligibility"] not in ELIGIBLE_D8_PUBLICATION_POLICIES
            or routing["target_residence_role"] != "WARM"
        ):
            raise GitHubPublicationError("D8 capability is not eligible for canonical WARM publication")
        row = dict(envelope)
        row["_routing"] = routing
        by_series[envelope["series_id"]].append(row)
    result: list[dict[str, Any]] = []
    batch_positions = {oid: pos for pos, oid in enumerate(batch["member_observation_ids"])}
    for series_id in sorted(by_series):
        rows = by_series[series_id]
        first = rows[0]
        routing = first["_routing"]
        if any(
            row["capability_id"] != first["capability_id"]
            or row["provider"] != first["provider"]
            or row["_routing"] != routing
            for row in rows
        ):
            raise GitHubPublicationError(f"inconsistent D8 publication routing within series: {series_id}")
        observations = []
        for row in sorted(rows, key=lambda item: batch_positions[item["observation_id"]]):
            observations.append(
                {
                    "observation_id": row["observation_id"],
                    "effective_timestamp_ms": _effective_timestamp_ms(row, routing["lifecycle_class"]),
                    "known_at": row["known_at"],
                    "finality": row["finality"],
                    "payload_fingerprint": row["fingerprint"],
                }
            )
        interval_ms = _interval_ms(series_id, routing["normalization_family"], routing["lifecycle_class"])
        result.append(
            {
                "series_id": series_id,
                "capability_id": first["capability_id"],
                "provider": first["provider"],
                "lifecycle_class": routing["lifecycle_class"],
                "normalization_family": routing["normalization_family"],
                "finality_policy": routing["finality_policy"],
                "allowed_finality": list(routing["allowed_finality"]),
                "interval_ms": interval_ms,
                "observations": observations,
            }
        )
    return result


def publication_control_entry(
    batch: dict[str, Any],
    envelopes: list[dict[str, Any]],
    *,
    data_commit_sha: str,
    resource_path: str,
    resource_bytes: bytes,
) -> dict[str, Any]:
    if not isinstance(data_commit_sha, str) or len(data_commit_sha) != 40:
        raise GitHubPublicationError("data durability commit SHA is invalid")
    return {
        "batch_id": batch["batch_id"],
        "residence_role": "WARM",
        "adapter_profile": GITHUB_FIRST_V1,
        "resource_ref": f"d8-publication:{batch['batch_id']}",
        "resource_path": resource_path,
        "sha256": _sha256(resource_bytes),
        "size_bytes": len(resource_bytes),
        "data_commit_sha": data_commit_sha,
        "member_count": batch["member_count"],
        "member_observation_ids": batch["member_observation_ids"],
        "membership_sha256": batch["membership_sha256"],
        "payload_sha256": batch["payload_sha256"],
        "series": _series_bindings(batch, envelopes),
    }


def _empty_control_manifest() -> dict[str, Any]:
    return {
        "schema_version": CONTROL_SCHEMA,
        "backend_profile": GITHUB_FIRST_V1,
        "representation": REPRESENTATION,
        "publications": [],
    }


def _decode_control_manifest(current: bytes | None) -> dict[str, Any] | None:
    if current is None:
        return None
    try:
        payload = json.loads(current)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitHubPublicationError("canonical publication control manifest is invalid JSON") from exc
    if (
        payload.get("schema_version") != CONTROL_SCHEMA
        or payload.get("backend_profile") != GITHUB_FIRST_V1
        or payload.get("representation") != REPRESENTATION
        or not isinstance(payload.get("publications"), list)
    ):
        raise GitHubPublicationError("canonical publication control manifest identity mismatch")
    ids = [row.get("batch_id") for row in payload["publications"] if isinstance(row, dict)]
    if len(ids) != len(payload["publications"]) or len(ids) != len(set(ids)):
        raise GitHubPublicationError("canonical publication control manifest has invalid batch membership")
    return payload


def merge_control_manifest(current: bytes | None, entry: dict[str, Any]) -> bytes:
    payload = _decode_control_manifest(current) or _empty_control_manifest()
    index = {row["batch_id"]: row for row in payload["publications"]}
    existing = index.get(entry["batch_id"])
    if existing is not None and existing != entry:
        raise GitHubPublicationError("same PublicationBatch identity is bound to different remote content")
    index[entry["batch_id"]] = entry
    payload["publications"] = [index[key] for key in sorted(index)]
    return _compact(payload)


def classify_remote_drift(changed_paths: list[str], owned_paths: set[str]) -> str:
    paths = set(changed_paths)
    if paths & owned_paths:
        return "REAL_SOURCE_OVERLAP"
    if not paths:
        return "NONE"
    if all(path not in SOURCE_AUTHORITY_FILES and not path.startswith(SOURCE_AUTHORITY_PREFIXES) for path in paths):
        return "GENERATED_ONLY"
    return "UNRELATED_SOURCE_REQUIRES_COMPATIBILITY_RECHECK"


class GitHubHTTPTransport:
    """Thin GitHub Git-data REST transport with non-force optimistic CAS writes."""

    def __init__(
        self,
        repository: str,
        branch: str,
        *,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        opener: Any = urllib.request.urlopen,
    ):
        if repository.count("/") != 1:
            raise ValueError("repository must be owner/name")
        self.repository = repository
        self.branch = branch
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.api_url = api_url.rstrip("/")
        self.opener = opener

    def _request(self, method: str, path: str, payload: Any | None = None, *, accept: str = "application/vnd.github+json") -> bytes:
        url = f"{self.api_url}/repos/{self.repository}{path}"
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "eth-macro-data-bridge-canonical-publication-port",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubPublicationError(f"GitHub API {method} {path} failed status={exc.code} body={detail[:400]}") from exc

    def _json(self, method: str, path: str, payload: Any | None = None) -> dict[str, Any]:
        try:
            value = json.loads(self._request(method, path, payload))
        except json.JSONDecodeError as exc:
            raise GitHubPublicationError(f"GitHub API returned invalid JSON for {path}") from exc
        if not isinstance(value, dict):
            raise GitHubPublicationError(f"GitHub API object response required for {path}")
        return value

    def read_head(self) -> str:
        branch = urllib.parse.quote(self.branch, safe="")
        sha = self._json("GET", f"/git/ref/heads/{branch}").get("object", {}).get("sha")
        if not isinstance(sha, str) or len(sha) != 40:
            raise GitHubPublicationError("remote branch HEAD is invalid")
        return sha

    def read_file(self, path: str, ref: str) -> bytes | None:
        quoted = urllib.parse.quote(path, safe="/")
        query = urllib.parse.urlencode({"ref": ref})
        url_path = f"/contents/{quoted}?{query}"
        try:
            payload = self._json("GET", url_path)
        except GitHubPublicationError as exc:
            if "status=404" in str(exc):
                return None
            raise
        content = payload.get("content")
        if payload.get("encoding") != "base64" or not isinstance(content, str):
            raise GitHubPublicationError(f"remote file content encoding invalid: {path}")
        try:
            return base64.b64decode(content, validate=False)
        except ValueError as exc:
            raise GitHubPublicationError(f"remote file base64 invalid: {path}") from exc

    def commit_files(self, expected_head: str, files: dict[str, bytes], message: str) -> str:
        current = self.read_head()
        if current != expected_head:
            raise GitHubCASConflict(expected_head, current)
        parent = self._json("GET", f"/git/commits/{expected_head}")
        base_tree = parent.get("tree", {}).get("sha")
        if not isinstance(base_tree, str):
            raise GitHubPublicationError("remote parent tree missing")
        tree = []
        for path in sorted(files):
            blob = self._json(
                "POST",
                "/git/blobs",
                {"content": base64.b64encode(files[path]).decode("ascii"), "encoding": "base64"},
            )
            blob_sha = blob.get("sha")
            if not isinstance(blob_sha, str):
                raise GitHubPublicationError(f"GitHub blob creation failed: {path}")
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_sha})
        tree_sha = self._json("POST", "/git/trees", {"base_tree": base_tree, "tree": tree}).get("sha")
        if not isinstance(tree_sha, str):
            raise GitHubPublicationError("GitHub tree creation failed")
        commit_sha = self._json(
            "POST",
            "/git/commits",
            {"message": message, "tree": tree_sha, "parents": [expected_head]},
        ).get("sha")
        if not isinstance(commit_sha, str):
            raise GitHubPublicationError("GitHub commit creation failed")
        branch = urllib.parse.quote(self.branch, safe="")
        try:
            self._json("PATCH", f"/git/refs/heads/{branch}", {"sha": commit_sha, "force": False})
        except GitHubPublicationError as exc:
            actual = self.read_head()
            raise GitHubCASConflict(expected_head, actual) from exc
        if self.read_head() != commit_sha:
            raise GitHubPublicationError("GitHub branch did not advance to committed publication")
        return commit_sha

    def compare_paths(self, base: str, head: str) -> list[str]:
        base_q = urllib.parse.quote(base, safe="")
        head_q = urllib.parse.quote(head, safe="")
        payload = self._json("GET", f"/compare/{base_q}...{head_q}")
        files = payload.get("files")
        if not isinstance(files, list):
            raise GitHubPublicationError("GitHub compare response lacks files")
        return sorted(row["filename"] for row in files if isinstance(row, dict) and isinstance(row.get("filename"), str))

    def download_archive(self, ref: str) -> bytes:
        quoted = urllib.parse.quote(ref, safe="")
        return self._request("GET", f"/tarball/{quoted}", accept="application/vnd.github+json")


class RemoteSnapshotSemanticVerifier:
    """Run the public existing v2 resolver/reader from an independently downloaded remote snapshot."""

    def __init__(self, transport: GitHubRepositoryTransport):
        self.transport = transport

    @staticmethod
    def _extract(archive: bytes, destination: Path) -> Path:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
            members = tf.getmembers()
            destination_resolved = destination.resolve()
            for member in members:
                target = (destination / member.name).resolve()
                if destination_resolved not in target.parents and target != destination_resolved:
                    raise GitHubPublicationError("GitHub archive contains unsafe path")
            tf.extractall(destination)
        roots = [path for path in destination.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise GitHubPublicationError("GitHub archive root is ambiguous")
        return roots[0]

    def verify(self, control_commit: str, envelopes: list[dict[str, Any]]) -> dict[str, Any]:
        archive = self.transport.download_archive(control_commit)
        with tempfile.TemporaryDirectory(prefix="eth-macro-publication-readback-") as temporary:
            root = self._extract(archive, Path(temporary))
            request_path = Path(temporary) / "publication-proof.json"
            request_path.write_bytes(_compact({"envelopes": envelopes}))
            script = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
request = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.path[:0] = [str(root / "src"), str(root / "tools"), str(root / "tools" / "deep_history")]
from capability_index import resolve_capability_v2
from history_access import materialize_resolution_plan_any

def parse_ms(value):
    from datetime import datetime
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)

def effective(env):
    if env["d9_forward_seam"]["target"] == "FIXED_GRID":
        value = env.get("value")
        if isinstance(value, dict) and isinstance(value.get("open_time_ms"), int):
            return value["open_time_ms"]
        return parse_ms(env.get("provider_timestamp_at") or env["canonical_slot"])
    return parse_ms(env.get("canonical_slot") or env["known_at"])

def semantic_value(env):
    value = env.get("value")
    if env["d9_forward_seam"]["target"] == "FIXED_GRID" and isinstance(value, dict):
        fields = ("open", "high", "low", "close", "volume")
        if all(field in value for field in fields):
            return {field: value[field] for field in fields}
    return value

intervals = {"5m":300000,"15m":900000,"1h":3600000,"4h":14400000,"1d":86400000,"1w":604800000}
by_series = {}
for env in request["envelopes"]:
    by_series.setdefault(env["series_id"], []).append(env)
proofs = []
for series_id, envs in sorted(by_series.items()):
    lifecycle = envs[0]["d9_forward_seam"]["target"]
    step = intervals.get(series_id.rsplit(".",1)[-1], 1) if lifecycle == "FIXED_GRID" else 1
    from datetime import datetime, timezone
    iso = lambda ms: datetime.fromtimestamp(ms/1000, timezone.utc).isoformat().replace("+00:00", "Z")
    receipts = []
    plan_sha256s = []
    materialized_rows = 0
    for env in sorted(envs, key=lambda item: (effective(item), item["observation_id"])):
        timestamp = effective(env)
        plan = resolve_capability_v2(series_id, iso(timestamp), iso(timestamp + step), qualification_mode=True)
        rows, diagnostics = materialize_resolution_plan_any(plan, mode="strict")
        matches = [row for row in rows if row.get("observation_id") == env["observation_id"]]
        if len(matches) != 1:
            raise SystemExit(f"READER_MATERIALIZATION_MISSING:{env['observation_id']}")
        row = matches[0]
        if row.get("known_at") != env["known_at"] or row.get("finality") != env["finality"]:
            raise SystemExit(f"D8_SEMANTIC_PRESERVATION_MISMATCH:{env['observation_id']}")
        if row.get("provenance") != env["provenance"] or row.get("payload_fingerprint") != env["fingerprint"]:
            raise SystemExit(f"D8_PROVENANCE_BINDING_MISMATCH:{env['observation_id']}")
        if row.get("value") != semantic_value(env):
            raise SystemExit(f"D8_VALUE_BINDING_MISMATCH:{env['observation_id']}")
        receipt = diagnostics.get("receipt", {})
        if diagnostics.get("status") != "PASS" or receipt.get("series_id") != series_id:
            raise SystemExit(f"SEMANTIC_RECEIPT_FAILURE:{env['observation_id']}")
        receipts.append(receipt)
        plan_sha256s.append(plan["plan_sha256"])
        materialized_rows += len(rows)
    proofs.append({"series_id": series_id, "rows": materialized_rows, "plan_sha256s": plan_sha256s, "receipts": receipts})
print(json.dumps({"status":"PASS","proofs":proofs}, sort_keys=True, separators=(",", ":")))
'''
            completed = subprocess.run(
                [sys.executable, "-c", script, str(root), str(request_path)],
                cwd=root,
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                check=False,
            )
            if completed.returncode != 0:
                raise GitHubPublicationError(
                    "remote resolver/reader materialization failed: "
                    f"rc={completed.returncode} stderr={completed.stderr[-1200:]}"
                )
            try:
                proof = json.loads(completed.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError) as exc:
                raise GitHubPublicationError("remote semantic verifier did not return proof JSON") from exc
            if proof.get("status") != "PASS":
                raise GitHubPublicationError("remote semantic verifier did not PASS")
            return proof


class GitHubFirstV1Adapter:
    """Two-phase GitHub WARM adapter: data durability/read-back precedes control visibility."""

    profile = GITHUB_FIRST_V1

    def __init__(
        self,
        transport: GitHubRepositoryTransport,
        *,
        semantic_verifier: Any | None = None,
        max_cas_retries: int = 4,
        allow_unrelated_source_drift: bool = False,
    ):
        if max_cas_retries <= 0:
            raise ValueError("max_cas_retries must be positive")
        self.transport = transport
        self.semantic_verifier = semantic_verifier or RemoteSnapshotSemanticVerifier(transport)
        self.max_cas_retries = max_cas_retries
        self.allow_unrelated_source_drift = allow_unrelated_source_drift

    def _reconcile_base(
        self,
        expected: str,
        *,
        owned_paths: set[str],
        exact_resource: tuple[str, bytes] | None = None,
    ) -> str:
        current = self.transport.read_head()
        if current == expected:
            return current
        changed_paths = self.transport.compare_paths(expected, current)
        effective_owned_paths = set(owned_paths)
        if exact_resource is not None:
            path, raw = exact_resource
            existing = self.transport.read_file(path, current)
            if existing is not None:
                if existing != raw:
                    raise GitHubPublicationError("same PublicationBatch remote resource exists with different content")
                changed_paths = [changed for changed in changed_paths if changed != path]
                effective_owned_paths.discard(path)
        classification = classify_remote_drift(changed_paths, effective_owned_paths)
        if classification == "REAL_SOURCE_OVERLAP":
            raise GitHubCASConflict(expected, current)
        if classification == "UNRELATED_SOURCE_REQUIRES_COMPATIBILITY_RECHECK" and not self.allow_unrelated_source_drift:
            raise GitHubCASConflict(expected, current)
        return current

    def _bound_control_entry(
        self,
        ref: str,
        batch: dict[str, Any],
        envelopes: list[dict[str, Any]],
        path: str,
        raw: bytes,
    ) -> dict[str, Any] | None:
        payload = _decode_control_manifest(self.transport.read_file(CONTROL_PATH, ref))
        if payload is None:
            return None
        matches = [row for row in payload["publications"] if row.get("batch_id") == batch["batch_id"]]
        if not matches:
            return None
        if len(matches) != 1:
            raise GitHubPublicationError("same PublicationBatch appears more than once in control plane")
        bound = matches[0]
        data_commit = bound.get("data_commit_sha")
        if not isinstance(data_commit, str) or len(data_commit) != 40:
            raise GitHubPublicationError("existing PublicationBatch control entry lacks durability SHA")
        expected = publication_control_entry(
            batch,
            envelopes,
            data_commit_sha=data_commit,
            resource_path=path,
            resource_bytes=raw,
        )
        if bound != expected:
            raise GitHubPublicationError("existing PublicationBatch control binding conflicts with exact logical batch")
        return bound

    def _publish_data(
        self,
        batch: dict[str, Any],
        envelopes: list[dict[str, Any]],
        expected: str,
    ) -> tuple[str, str, bytes, bool]:
        path, raw = materialize_data_resource(batch, envelopes)
        base = expected
        for _ in range(self.max_cas_retries):
            base = self._reconcile_base(base, owned_paths={path}, exact_resource=(path, raw))
            existing = self.transport.read_file(path, base)
            if existing is not None:
                if existing != raw:
                    raise GitHubPublicationError("same PublicationBatch identity has conflicting remote bytes")
                bound = self._bound_control_entry(base, batch, envelopes, path, raw)
                durability_sha = bound["data_commit_sha"] if bound is not None else base
                return durability_sha, path, raw, True
            try:
                commit = self.transport.commit_files(base, {path: raw}, f"data: publish D8 history batch {batch['batch_id']}")
            except GitHubCASConflict as conflict:
                base = self._reconcile_base(
                    conflict.expected,
                    owned_paths={path},
                    exact_resource=(path, raw),
                )
                continue
            readback = self.transport.read_file(path, commit)
            if readback != raw:
                raise GitHubPublicationError("independent remote data read-back mismatch")
            return commit, path, raw, False
        raise GitHubPublicationError("GitHub data publication CAS retry budget exhausted")

    def _publish_control(
        self,
        batch: dict[str, Any],
        envelopes: list[dict[str, Any]],
        *,
        data_commit: str,
        path: str,
        raw: bytes,
    ) -> tuple[str, bytes, bool]:
        base = self.transport.read_head()
        for _ in range(self.max_cas_retries):
            durable = self.transport.read_file(path, base)
            if durable != raw:
                raise GitHubPublicationError("durable D8 batch is not present on control-plane publication base")
            entry = publication_control_entry(
                batch,
                envelopes,
                data_commit_sha=data_commit,
                resource_path=path,
                resource_bytes=raw,
            )
            current_manifest = self.transport.read_file(CONTROL_PATH, base)
            merged = merge_control_manifest(current_manifest, entry)
            if current_manifest == merged:
                return base, merged, True
            try:
                commit = self.transport.commit_files(base, {CONTROL_PATH: merged}, f"data: bind D8 history batch {batch['batch_id']}")
            except GitHubCASConflict as conflict:
                base = self._reconcile_base(
                    conflict.expected,
                    owned_paths={path},
                    exact_resource=(path, raw),
                )
                continue
            readback = self.transport.read_file(CONTROL_PATH, commit)
            if readback != merged:
                raise GitHubPublicationError("independent canonical control-plane read-back mismatch")
            return commit, merged, False
        raise GitHubPublicationError("GitHub control-plane CAS retry budget exhausted")

    def publish_canonical(
        self,
        batch: dict[str, Any],
        envelopes: list[dict[str, Any]],
        *,
        expected_remote_base: str,
        failpoint: Any | None = None,
    ) -> dict[str, Any]:
        attempt_id = "ghpub-" + uuid.uuid4().hex
        if failpoint:
            failpoint("before_remote_publication")
        data_commit, path, raw, data_already_present = self._publish_data(batch, envelopes, expected_remote_base)
        current_after_data = self.transport.read_head()
        if self.transport.read_file(path, current_after_data) != raw:
            raise GitHubPublicationError("remote durability/read-back gate failed")
        if failpoint:
            failpoint("after_remote_data_before_control")
        control_commit, control_raw, control_already_present = self._publish_control(
            batch,
            envelopes,
            data_commit=data_commit,
            path=path,
            raw=raw,
        )
        try:
            manifest = json.loads(control_raw)
        except json.JSONDecodeError as exc:
            raise GitHubPublicationError("control-plane read-back is not JSON") from exc
        entry = next((row for row in manifest["publications"] if row.get("batch_id") == batch["batch_id"]), None)
        expected_entry = publication_control_entry(
            batch,
            envelopes,
            data_commit_sha=data_commit,
            resource_path=path,
            resource_bytes=raw,
        )
        if entry != expected_entry:
            raise GitHubPublicationError("canonical control-plane binding mismatch")
        if failpoint:
            failpoint("after_control_before_semantic")
        semantic = self.semantic_verifier.verify(control_commit, envelopes)
        if not isinstance(semantic, dict) or semantic.get("status") != "PASS":
            raise GitHubPublicationError("resolver/reader materialization proof failed")
        gates = {
            "REMOTE_DURABILITY": "PASS",
            "REMOTE_READBACK": "PASS",
            "EXACT_BATCH_MEMBERSHIP": "PASS",
            "EXACT_PAYLOAD_BINDING": "PASS",
            "INTEGRITY_BINDING": "PASS",
            "CONTROL_PLANE_VISIBILITY": "PASS",
            "RESOLVER_VISIBILITY": "PASS",
            "READER_MATERIALIZATION": "PASS",
        }
        return {
            "schema_version": PORT_EVIDENCE_SCHEMA,
            "batch_id": batch["batch_id"],
            "publication_attempt_id": attempt_id,
            "backend_profile": self.profile,
            "accepted_observation_ids": batch["member_observation_ids"],
            "membership_sha256": batch["membership_sha256"],
            "payload_sha256": batch["payload_sha256"],
            "partial_ack": False,
            "gates": gates,
            "durability_evidence": {
                "repository": self.transport.repository,
                "branch": self.transport.branch,
                "data_commit_sha": data_commit,
                "verified_head_sha": current_after_data,
                "resource_path": path,
                "resource_ref": expected_entry["resource_ref"],
                "sha256": expected_entry["sha256"],
                "size_bytes": expected_entry["size_bytes"],
                "already_present_retry": data_already_present,
            },
            "control_plane_visibility_evidence": {
                "control_commit_sha": control_commit,
                "control_path": CONTROL_PATH,
                "already_present_retry": control_already_present,
            },
            "semantic_materialization_evidence": semantic,
        }
