from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from history_store import ImmutableHistoryConflict, append_partition

CONTRACT_ID = "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1"
CONTRACT_VERSION = "1.0.0"
HANDOFF_SCHEMA = "fresh-current-promotion-handoff/1.0.0"
CONSUMPTION_SCHEMA = "fresh-current-promotion-consumption/1.0.0"
DURABILITY_CLASSES = (
    "RECONSTRUCTIBLE",
    "PROMOTION_ELIGIBLE",
    "EPHEMERAL_ONLY",
    "NOT_APPLICABLE",
)
PROMOTION_LEDGER_PATH = Path("history/current-promotion-consumption.json")
COLLECTION_LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
ARTIFACT_NAME_RE = re.compile(r"^fresh-current-data-[1-9][0-9]*-[1-9][0-9]*$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

TARGETS: dict[str, dict[str, str]] = {
    "derivatives.deribit-perpetual.current-snapshot": {
        "provider": "deribit-perpetual",
        "source_semantics": "market-data-sampled-observation/1.0.0",
        "promotion_policy_id": "EXISTING_SAMPLED_DERIBIT_PERPETUAL_V1",
    },
    "options.deribit-options.ETH.surface-snapshots": {
        "provider": "deribit-options",
        "source_semantics": "options.deribit-options.ETH.surface-snapshots",
        "promotion_policy_id": "EXISTING_FORWARD_OPTIONS_SURFACE_V1",
    },
    "liquidity.orderbook-snapshots": {
        "provider": "multi-provider",
        "source_semantics": "liquidity.orderbook-snapshots",
        "promotion_policy_id": "EXISTING_FORWARD_LIQUIDITY_SNAPSHOT_V1",
    },
}


class PromotionError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionError("INVALID_JSON_RESOURCE", f"cannot read canonical JSON: {path}") from exc


def _parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or "\n" in value or "\r" in value:
        raise PromotionError("INVALID_UTC", f"{field} must use single-line UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PromotionError("INVALID_UTC", f"invalid {field}: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise PromotionError("INVALID_UTC", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _iso_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _timestamp_ms(value: str, field: str) -> int:
    return int(_parse_utc(value, field).timestamp() * 1000)


def _day_path(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).strftime("%Y/%m/%d")


def _date_text(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def _safe_payload_name(family: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", family) + ".json"


def _target_path(family: str, timestamp_ms: int) -> Path:
    day = _day_path(timestamp_ms)
    if family == "derivatives.deribit-perpetual.current-snapshot":
        return Path("derivatives/snapshots") / day / f"{timestamp_ms}.json"
    if family == "options.deribit-options.ETH.surface-snapshots":
        return Path("options/snapshots") / day / f"{timestamp_ms}.json"
    if family == "liquidity.orderbook-snapshots":
        return Path("liquidity/snapshots") / day / f"{timestamp_ms}.json"
    raise PromotionError("PROMOTION_TARGET_UNKNOWN", f"no approved existing target for {family}")


def _collection_run_id(family: str, timestamp_ms: int) -> str:
    prefix = {
        "derivatives.deribit-perpetual.current-snapshot": "deribit-perpetual-current",
        "options.deribit-options.ETH.surface-snapshots": "deribit-options-surface",
        "liquidity.orderbook-snapshots": "liquidity-orderbook",
    }.get(family)
    if prefix is None:
        raise PromotionError("PROMOTION_TARGET_UNKNOWN", f"no collection-run identity for {family}")
    return f"{prefix}:{timestamp_ms}"


def _collection_ledger_path(timestamp_ms: int) -> Path:
    return Path("history/collection-runs") / _day_path(timestamp_ms) / "runs.json"


def _manifest_generation_ms(root: Path) -> int:
    manifest = _load_json(root / "data/manifest.json")
    if not isinstance(manifest, Mapping):
        raise PromotionError("GENERATION_MANIFEST_INVALID", "data/manifest.json must be an object")
    generated = manifest.get("generated_at_utc")
    if not isinstance(generated, str):
        raise PromotionError("GENERATION_MANIFEST_INVALID", "generated_at_utc missing")
    return _timestamp_ms(generated, "data.generated_at_utc")


def _load_collection_run(root: Path, family: str, timestamp_ms: int) -> dict[str, Any]:
    path = root / _collection_ledger_path(timestamp_ms)
    ledger = _load_json(path)
    if not isinstance(ledger, Mapping) or ledger.get("schema_version") != COLLECTION_LEDGER_SCHEMA:
        raise PromotionError("COLLECTION_LEDGER_INVALID", f"invalid sampled collection ledger: {path}")
    expected_id = _collection_run_id(family, timestamp_ms)
    matches = [
        row
        for row in ledger.get("runs", [])
        if isinstance(row, Mapping) and row.get("run_id") == expected_id
    ]
    if len(matches) != 1:
        raise PromotionError("COLLECTION_RUN_MISSING", f"expected exactly one sampled run: {expected_id}")
    row = dict(matches[0])
    if row.get("status") != "OBSERVED_STATE":
        raise PromotionError("PROMOTION_SOURCE_NOT_OBSERVED", f"sampled source is not OBSERVED_STATE: {expected_id}")
    expected_target = _target_path(family, timestamp_ms).as_posix()
    if row.get("snapshot_ref") != expected_target:
        raise PromotionError(
            "PROMOTION_SOURCE_PATH_MISMATCH",
            f"sampled run snapshot_ref does not match existing canonical target family: {expected_id}",
        )
    return row


def _validate_payload(family: str, payload: Mapping[str, Any], timestamp_ms: int) -> None:
    if family == "derivatives.deribit-perpetual.current-snapshot":
        if (
            payload.get("schema_version") != "market-data-sampled-observation/1.0.0"
            or payload.get("provider") != "deribit-perpetual"
            or payload.get("timestamp_ms") != timestamp_ms
            or not isinstance(payload.get("instruments"), Mapping)
        ):
            raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"invalid Deribit perpetual sampled snapshot: {timestamp_ms}")
        return
    if family == "options.deribit-options.ETH.surface-snapshots":
        if (
            payload.get("provider") != "deribit"
            or payload.get("timestamp_ms") != timestamp_ms
            or payload.get("scope") != "FULL_ACTIVE_CHAIN_COMPACT"
            or not isinstance(payload.get("options"), list)
        ):
            raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"invalid Deribit options surface snapshot: {timestamp_ms}")
        return
    if family == "liquidity.orderbook-snapshots":
        if payload.get("timestamp_ms") != timestamp_ms or not isinstance(payload.get("snapshots"), list):
            raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"invalid liquidity snapshot: {timestamp_ms}")
        return
    raise PromotionError("PROMOTION_TARGET_UNKNOWN", f"no payload validator for {family}")


def _observation_identity(family: str, payload: Mapping[str, Any], timestamp_ms: int) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "provider": TARGETS[family]["provider"],
        "series_or_capability": family,
        "timestamp_ms": timestamp_ms,
    }
    if family == "options.deribit-options.ETH.surface-snapshots":
        identity["scope"] = payload.get("scope")
    return identity


def _semantic_resource_for_series(index_row: Mapping[str, Any], receipt: Mapping[str, Any], known_at: str) -> dict[str, Any]:
    series_id = str(index_row.get("series_id") or "")
    if not series_id:
        raise PromotionError("SERIES_DURABILITY_IDENTITY_INVALID", "series durability identity missing series_id")
    latest = receipt.get("latest_selection")
    latest_open_ms = latest.get("latest_open_timestamp_ms") if isinstance(latest, Mapping) else None
    if not isinstance(latest_open_ms, int):
        raise PromotionError("SERIES_DURABILITY_IDENTITY_INVALID", f"series latest anchor missing: {series_id}")
    semantic_output = str(index_row.get("semantic_output_sha256") or "")
    if not _HEX64.fullmatch(semantic_output):
        raise PromotionError("SERIES_DURABILITY_IDENTITY_INVALID", f"series semantic output invalid: {series_id}")
    return {
        "logical_resource_id": str(index_row["resource_logical_id"]),
        "semantic_series_id_or_domain_identity": series_id,
        "durability_class": "RECONSTRUCTIBLE",
        "durability_state": "RECONSTRUCTIBLE",
        "observation_identity": {
            "series_id": series_id,
            "latest_open_timestamp_ms": latest_open_ms,
            "latest_bars": int(index_row["latest_bars"]),
            "semantic_output_sha256": semantic_output,
        },
        "observation_time_utc": _iso_ms(latest_open_ms),
        "known_at_utc": known_at,
        "source_provider": series_id.split(".", 2)[1] if "." in series_id else "UNKNOWN",
        "source_semantics": "CANONICAL_SERIES_WINDOW_VIA_SEMANTIC_RECEIPT",
        "payload_member": None,
        "payload_sha256": None,
        "payload_size_bytes": 0,
        "existing_target_family": "DECLARED_PROVIDER_HISTORY",
        "promotion_policy_id": "RECONSTRUCTIBLE_PROVIDER_HISTORY_V1",
        "promotion_required": False,
        "validation_status": "PASS",
    }


def _domain_manifest_resource(index_row: Mapping[str, Any], known_at: str) -> dict[str, Any]:
    domain = str(index_row.get("domain_id") or "")
    generated = str(index_row.get("generated_at_utc") or "")
    digest = str(index_row.get("sha256") or "")
    if not domain or not generated or not _HEX64.fullmatch(digest):
        raise PromotionError("DOMAIN_DURABILITY_IDENTITY_INVALID", f"invalid domain resource durability identity: {domain}")
    durability_class = "EPHEMERAL_ONLY" if domain in {"ANALYTICS", "EVENTS"} else "NOT_APPLICABLE"
    policy = (
        "NO_APPROVED_DURABLE_CURRENT_DOMAIN_SAMPLE_V1"
        if durability_class == "EPHEMERAL_ONLY"
        else "DOMAIN_MANIFEST_NOT_OBSERVATION_V1"
    )
    return {
        "logical_resource_id": str(index_row["resource_logical_id"]),
        "semantic_series_id_or_domain_identity": domain,
        "durability_class": durability_class,
        "durability_state": durability_class,
        "observation_identity": {
            "domain_id": domain,
            "generation_resource_sha256": digest,
        },
        "observation_time_utc": generated,
        "known_at_utc": known_at,
        "source_provider": "MULTI_PROVIDER_OR_DERIVED",
        "source_semantics": "CURRENT_DOMAIN_MANIFEST_RESOURCE",
        "payload_member": None,
        "payload_sha256": None,
        "payload_size_bytes": 0,
        "existing_target_family": None,
        "promotion_policy_id": policy,
        "promotion_required": False,
        "validation_status": "PASS",
        "promotion_not_authorized_for_resource": durability_class == "EPHEMERAL_ONLY",
    }


def _reconstructible_domain_subresource(
    *,
    logical_id: str,
    semantic_id: str,
    generated_at: str,
    known_at: str,
    provider: str,
    policy: str,
) -> dict[str, Any]:
    return {
        "logical_resource_id": logical_id,
        "semantic_series_id_or_domain_identity": semantic_id,
        "durability_class": "RECONSTRUCTIBLE",
        "durability_state": "RECONSTRUCTIBLE",
        "observation_identity": {
            "series_or_capability": semantic_id,
            "generation_time_utc": generated_at,
        },
        "observation_time_utc": generated_at,
        "known_at_utc": known_at,
        "source_provider": provider,
        "source_semantics": "DECLARED_PROVIDER_HISTORY_RECOVERY",
        "payload_member": None,
        "payload_sha256": None,
        "payload_size_bytes": 0,
        "existing_target_family": "DECLARED_PROVIDER_HISTORY",
        "promotion_policy_id": policy,
        "promotion_required": False,
        "validation_status": "PASS",
    }


def _promotion_resource(
    *,
    root: Path,
    output_root: Path,
    family: str,
    timestamp_ms: int,
    generated_at: str,
    known_at: str,
    generation_mode: str,
) -> dict[str, Any]:
    target = _target_path(family, timestamp_ms)
    source = root / target
    if not source.is_file():
        raise PromotionError("PROMOTION_SOURCE_MISSING", f"sampled source payload missing: {target}")
    payload = _load_json(source)
    if not isinstance(payload, Mapping):
        raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"promotion payload must be an object: {target}")
    _validate_payload(family, payload, timestamp_ms)
    run = _load_collection_run(root, family, timestamp_ms)
    raw = source.read_bytes()
    digest = _sha256_bytes(raw)
    pending = generation_mode == "FRESH_ACQUISITION"
    member: str | None = None
    if pending:
        member = f"promotion-payload/{_safe_payload_name(family)}"
        destination = output_root / member
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    return {
        "logical_resource_id": f"promotion-candidate:{family}:{timestamp_ms}",
        "semantic_series_id_or_domain_identity": family,
        "durability_class": "PROMOTION_ELIGIBLE",
        "durability_state": "PROMOTION_PENDING" if pending else "CANONICAL_DURABLE",
        "observation_identity": _observation_identity(family, payload, timestamp_ms),
        "observation_time_utc": _iso_ms(timestamp_ms),
        "known_at_utc": known_at,
        "source_provider": TARGETS[family]["provider"],
        "source_semantics": TARGETS[family]["source_semantics"],
        "payload_member": member,
        "payload_sha256": digest if pending else None,
        "payload_size_bytes": len(raw) if pending else 0,
        "existing_target_family": family,
        "promotion_policy_id": TARGETS[family]["promotion_policy_id"],
        "promotion_required": pending,
        "validation_status": "PASS",
        "collection_run": run,
        "collection_run_identity": run["run_id"],
        "generated_at_utc": generated_at,
    }


def _handoff_identity_basis(handoff: Mapping[str, Any]) -> dict[str, Any]:
    resources = []
    for row in handoff.get("resources", []):
        if not isinstance(row, Mapping):
            raise PromotionError("HANDOFF_RESOURCE_INVALID", "handoff resources must be objects")
        resources.append(
            {
                "logical_resource_id": row.get("logical_resource_id"),
                "semantic_series_id_or_domain_identity": row.get("semantic_series_id_or_domain_identity"),
                "durability_class": row.get("durability_class"),
                "durability_state": row.get("durability_state"),
                "observation_identity": row.get("observation_identity"),
                "observation_time_utc": row.get("observation_time_utc"),
                "known_at_utc": row.get("known_at_utc"),
                "source_provider": row.get("source_provider"),
                "source_semantics": row.get("source_semantics"),
                "payload_sha256": row.get("payload_sha256"),
                "payload_size_bytes": row.get("payload_size_bytes"),
                "existing_target_family": row.get("existing_target_family"),
                "promotion_policy_id": row.get("promotion_policy_id"),
                "promotion_required": row.get("promotion_required"),
                "validation_status": row.get("validation_status"),
                "collection_run_identity": row.get("collection_run_identity"),
            }
        )
    resources.sort(key=lambda row: str(row["logical_resource_id"]))
    return {
        "schema_version": handoff.get("schema_version"),
        "contract_id": handoff.get("contract_id"),
        "contract_version": handoff.get("contract_version"),
        "control_plane_head": handoff.get("control_plane_head"),
        "control_plane_tree": handoff.get("control_plane_tree"),
        "generation_id": handoff.get("generation_id"),
        "generation_manifest_sha256": handoff.get("generation_manifest_sha256"),
        "generated_at_utc": handoff.get("generated_at_utc"),
        "known_at_utc": handoff.get("known_at_utc"),
        "request_sha256": handoff.get("request_sha256"),
        "generation_mode": handoff.get("generation_mode"),
        "resources": resources,
    }


def build_handoff(*, request_path: Path, output_root: Path, repository_root: Path = ROOT) -> dict[str, Any]:
    wrapper = _load_json(request_path)
    generation = _load_json(output_root / "current-generation.json")
    resource_index = _load_json(output_root / "resource-index.json")
    if not isinstance(wrapper, Mapping) or not isinstance(generation, Mapping) or not isinstance(resource_index, Mapping):
        raise PromotionError("HANDOFF_INPUT_INVALID", "request/generation/resource-index must be objects")
    if generation.get("contract_id") != CONTRACT_ID or generation.get("contract_version") != CONTRACT_VERSION:
        raise PromotionError("HANDOFF_INPUT_INVALID", "generation contract identity mismatch")
    if wrapper.get("request_sha256") != generation.get("request_sha256"):
        raise PromotionError("HANDOFF_INPUT_INVALID", "request/generation identity mismatch")
    if resource_index.get("request_sha256") != generation.get("request_sha256"):
        raise PromotionError("HANDOFF_INPUT_INVALID", "resource-index/generation identity mismatch")
    request = wrapper.get("request")
    if not isinstance(request, Mapping):
        raise PromotionError("HANDOFF_INPUT_INVALID", "normalized request missing")
    generation_mode = str(generation.get("generation_mode") or "")
    if generation_mode not in {"PERSISTED_REUSE", "FRESH_ACQUISITION"}:
        raise PromotionError("HANDOFF_INPUT_INVALID", "invalid generation mode")
    generated_at = str(generation.get("generated_at_utc") or "")
    known_at = str(generation.get("known_at_utc") or "")
    _parse_utc(generated_at, "generated_at_utc")
    _parse_utc(known_at, "known_at_utc")
    generated_ms = _timestamp_ms(generated_at, "generated_at_utc")
    repository_generation_ms = _manifest_generation_ms(repository_root)
    if repository_generation_ms != generated_ms:
        raise PromotionError("HANDOFF_GENERATION_MISMATCH", "repository current generation differs from generation receipt")

    resources: list[dict[str, Any]] = []
    series_rows = {
        row.get("series_id"): row
        for row in resource_index.get("series", [])
        if isinstance(row, Mapping)
    }
    for requested in request.get("required_series", []):
        if not isinstance(requested, Mapping):
            raise PromotionError("HANDOFF_INPUT_INVALID", "required_series item invalid")
        series_id = requested.get("series_id")
        row = series_rows.get(series_id)
        if not isinstance(row, Mapping):
            raise PromotionError("HANDOFF_INPUT_INVALID", f"series missing from resource index: {series_id}")
        normalized_member = str(row.get("artifact_member") or "")
        series_dir = output_root / Path(normalized_member).parent
        receipt = _load_json(series_dir / "receipt.json")
        if not isinstance(receipt, Mapping):
            raise PromotionError("HANDOFF_INPUT_INVALID", f"series receipt invalid: {series_id}")
        resources.append(_semantic_resource_for_series(row, receipt, known_at))

    domain_rows = {
        row.get("domain_id"): row
        for row in resource_index.get("domains", [])
        if isinstance(row, Mapping)
    }
    requested_domains = [str(value) for value in request.get("required_domains", [])]
    for domain in requested_domains:
        row = domain_rows.get(domain)
        if not isinstance(row, Mapping):
            raise PromotionError("HANDOFF_INPUT_INVALID", f"domain missing from resource index: {domain}")
        resources.append(_domain_manifest_resource(row, known_at))
        if domain == "DERIVATIVES":
            resources.append(
                _promotion_resource(
                    root=repository_root,
                    output_root=output_root,
                    family="derivatives.deribit-perpetual.current-snapshot",
                    timestamp_ms=generated_ms,
                    generated_at=generated_at,
                    known_at=known_at,
                    generation_mode=generation_mode,
                )
            )
            resources.append(
                _reconstructible_domain_subresource(
                    logical_id=f"reconstructible:derivatives.kraken-futures:{generated_ms}",
                    semantic_id="derivatives.kraken-futures.provider-history",
                    generated_at=generated_at,
                    known_at=known_at,
                    provider="kraken-futures",
                    policy="RECONSTRUCTIBLE_KRAKEN_FUTURES_HISTORY_V1",
                )
            )
        elif domain == "OPTIONS":
            resources.append(
                _promotion_resource(
                    root=repository_root,
                    output_root=output_root,
                    family="options.deribit-options.ETH.surface-snapshots",
                    timestamp_ms=generated_ms,
                    generated_at=generated_at,
                    known_at=known_at,
                    generation_mode=generation_mode,
                )
            )
            resources.append(
                _reconstructible_domain_subresource(
                    logical_id=f"reconstructible:options.deribit-options.ETH.dvol.1h:{generated_ms}",
                    semantic_id="options.deribit-options.ETH.dvol.1h",
                    generated_at=generated_at,
                    known_at=known_at,
                    provider="deribit-options",
                    policy="RECONSTRUCTIBLE_DERIBIT_DVOL_HISTORY_V1",
                )
            )
        elif domain == "LIQUIDITY":
            resources.append(
                _promotion_resource(
                    root=repository_root,
                    output_root=output_root,
                    family="liquidity.orderbook-snapshots",
                    timestamp_ms=generated_ms,
                    generated_at=generated_at,
                    known_at=known_at,
                    generation_mode=generation_mode,
                )
            )

    resources.sort(key=lambda row: str(row["logical_resource_id"]))
    handoff: dict[str, Any] = {
        "schema_version": HANDOFF_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "authority": "TEMPORARY_TRANSFER_EVIDENCE",
        "promotion_handoff_is_market_data_authority": False,
        "actions_artifact_is_durable_history_authority": False,
        "canonical_durability_occurs_only_after_existing_durable_publication": True,
        "control_plane_head": generation.get("control_plane_head"),
        "control_plane_tree": generation.get("control_plane_tree"),
        "generation_id": generation.get("generation_id"),
        "generation_manifest_sha256": generation.get("generation_manifest_sha256"),
        "generated_at_utc": generated_at,
        "known_at_utc": known_at,
        "request_sha256": generation.get("request_sha256"),
        "generation_mode": generation_mode,
        "durability_classes": list(DURABILITY_CLASSES),
        "resources": resources,
        "promotion_required": any(row.get("promotion_required") is True for row in resources),
        "promotion_pending_count": sum(row.get("promotion_required") is True for row in resources),
        "reconstructible_payload_included": False,
        "per_request_remote_git_mutation": False,
        "per_request_git_commit": False,
        "per_request_git_push": False,
        "durable_publisher": ".github/workflows/update-market.yml",
        "publication_mode": "HOURLY_BATCHED",
    }
    handoff["handoff_id"] = _sha256_json(_handoff_identity_basis(handoff))
    _write_json(output_root / "promotion-handoff.json", handoff)
    return handoff


def _forbidden_identity_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        token in lowered
        for token in ("path", "filename", "filesystem", "locator", "url", "artifact", "issue_number", "github_run_id")
    )


def _validate_observation_identity(value: Any) -> None:
    if not isinstance(value, Mapping) or not value:
        raise PromotionError("OBSERVATION_IDENTITY_INVALID", "observation_identity must be a non-empty object")
    for key, nested in value.items():
        if _forbidden_identity_key(str(key)):
            raise PromotionError("OBSERVATION_IDENTITY_PHYSICAL", f"physical field forbidden in observation identity: {key}")
        if isinstance(nested, Mapping):
            _validate_observation_identity(nested)


def _validate_generation_manifest(generation: Mapping[str, Any]) -> None:
    digest = str(generation.get("generation_manifest_sha256") or "")
    if not _HEX64.fullmatch(digest):
        raise PromotionError("GENERATION_MANIFEST_INVALID", "generation_manifest_sha256 invalid")
    core = dict(generation)
    core.pop("generation_manifest_sha256", None)
    if _sha256_json(core) != digest:
        raise PromotionError("GENERATION_MANIFEST_HASH_MISMATCH", "generation manifest hash mismatch")


def _validate_git_provenance(handoff: Mapping[str, Any], source_control_root: Path) -> None:
    head = str(handoff.get("control_plane_head") or "")
    tree = str(handoff.get("control_plane_tree") or "")
    if not _HEX40.fullmatch(head) or not _HEX40.fullmatch(tree):
        raise PromotionError("CONTROL_PLANE_GIT_INVALID", "handoff control-plane git identity invalid")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{head}^{{commit}}"],
        cwd=source_control_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if exists.returncode:
        raise PromotionError("CONTROL_PLANE_HEAD_UNKNOWN", f"handoff source commit is not available locally: {head}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", head, "HEAD"],
        cwd=source_control_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode:
        raise PromotionError("CONTROL_PLANE_HEAD_NOT_ANCESTOR", f"handoff source commit is not an ancestor of current publisher: {head}")
    actual_tree = subprocess.run(
        ["git", "rev-parse", f"{head}^{{tree}}"],
        cwd=source_control_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if actual_tree.returncode or actual_tree.stdout.strip().lower() != tree:
        raise PromotionError("CONTROL_PLANE_TREE_MISMATCH", f"handoff source tree mismatch: {head}")


def validate_artifact(
    artifact_root: Path,
    *,
    source_control_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    handoff = _load_json(artifact_root / "promotion-handoff.json")
    generation = _load_json(artifact_root / "current-generation.json")
    if not isinstance(handoff, Mapping) or not isinstance(generation, Mapping):
        raise PromotionError("HANDOFF_INVALID", "handoff/generation must be objects")
    if handoff.get("schema_version") != HANDOFF_SCHEMA:
        raise PromotionError("HANDOFF_SCHEMA_INVALID", "promotion handoff schema mismatch")
    if handoff.get("contract_id") != CONTRACT_ID or handoff.get("contract_version") != CONTRACT_VERSION:
        raise PromotionError("HANDOFF_CONTRACT_INVALID", "promotion handoff contract identity mismatch")
    _validate_generation_manifest(generation)
    binding = (
        "control_plane_head",
        "control_plane_tree",
        "generation_id",
        "generation_manifest_sha256",
        "generated_at_utc",
        "known_at_utc",
        "request_sha256",
        "generation_mode",
    )
    for field in binding:
        if handoff.get(field) != generation.get(field):
            raise PromotionError("HANDOFF_GENERATION_BINDING_MISMATCH", f"handoff field differs from generation: {field}")
    expected_id = _sha256_json(_handoff_identity_basis(handoff))
    if handoff.get("handoff_id") != expected_id:
        raise PromotionError("HANDOFF_ID_MISMATCH", "promotion handoff semantic identity mismatch")
    if handoff.get("authority") != "TEMPORARY_TRANSFER_EVIDENCE":
        raise PromotionError("HANDOFF_AUTHORITY_INVALID", "promotion handoff authority role invalid")
    if handoff.get("promotion_handoff_is_market_data_authority") is not False:
        raise PromotionError("HANDOFF_AUTHORITY_INVALID", "promotion handoff cannot be market-data authority")
    if handoff.get("actions_artifact_is_durable_history_authority") is not False:
        raise PromotionError("HANDOFF_AUTHORITY_INVALID", "Actions artifact cannot be durable history authority")

    resources = handoff.get("resources")
    if not isinstance(resources, list):
        raise PromotionError("HANDOFF_RESOURCE_INVALID", "handoff resources must be a list")
    for row in resources:
        if not isinstance(row, Mapping):
            raise PromotionError("HANDOFF_RESOURCE_INVALID", "handoff resource must be an object")
        durability = row.get("durability_class")
        if durability not in DURABILITY_CLASSES:
            raise PromotionError("UNKNOWN_DURABILITY_CLASS", f"unknown durability class: {durability}")
        _validate_observation_identity(row.get("observation_identity"))
        if row.get("validation_status") != "PASS":
            raise PromotionError("HANDOFF_RESOURCE_NOT_VALIDATED", f"resource not validated: {row.get('logical_resource_id')}")
        required = row.get("promotion_required") is True
        member = row.get("payload_member")
        digest = row.get("payload_sha256")
        size = row.get("payload_size_bytes")
        if durability == "PROMOTION_ELIGIBLE" and required:
            family = str(row.get("existing_target_family") or "")
            if family not in TARGETS:
                raise PromotionError("PROMOTION_TARGET_UNKNOWN", f"unapproved promotion family: {family}")
            if not isinstance(member, str) or not member.startswith("promotion-payload/"):
                raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"promotion payload member invalid: {member}")
            member_path = Path(member)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"unsafe promotion payload member: {member}")
            payload_path = artifact_root / member_path
            raw = payload_path.read_bytes()
            if _sha256_bytes(raw) != digest or len(raw) != size:
                raise PromotionError("PROMOTION_PAYLOAD_HASH_MISMATCH", f"promotion payload identity mismatch: {member}")
            payload = json.loads(raw)
            if not isinstance(payload, Mapping):
                raise PromotionError("PROMOTION_PAYLOAD_INVALID", f"promotion payload must be object: {member}")
            identity = row.get("observation_identity")
            timestamp_ms = identity.get("timestamp_ms") if isinstance(identity, Mapping) else None
            if not isinstance(timestamp_ms, int):
                raise PromotionError("OBSERVATION_IDENTITY_INVALID", f"promotion timestamp missing: {member}")
            _validate_payload(family, payload, timestamp_ms)
            run = row.get("collection_run")
            if not isinstance(run, Mapping) or row.get("collection_run_identity") != run.get("run_id"):
                raise PromotionError("COLLECTION_RUN_INVALID", f"promotion collection run invalid: {member}")
            expected_target = _target_path(family, timestamp_ms).as_posix()
            if run.get("snapshot_ref") != expected_target:
                raise PromotionError("COLLECTION_RUN_INVALID", f"promotion collection run target mismatch: {member}")
        else:
            if member is not None or digest is not None or size not in (0, None):
                raise PromotionError("UNAUTHORIZED_PROMOTION_PAYLOAD", f"non-pending resource contains promotion payload: {row.get('logical_resource_id')}")
        if durability == "EPHEMERAL_ONLY" and row.get("promotion_not_authorized_for_resource") is not True:
            raise PromotionError("EPHEMERAL_PROMOTION_POLICY_INVALID", "EPHEMERAL_ONLY must state promotion is not authorized")

    if source_control_root is not None:
        _validate_git_provenance(handoff, source_control_root)
    return dict(handoff), dict(generation)


def _read_consumption_ledger(root: Path) -> dict[str, Any]:
    path = root / PROMOTION_LEDGER_PATH
    if not path.exists():
        return {
            "schema_version": CONSUMPTION_SCHEMA,
            "authority": "PROMOTION_CONSUMPTION_STATE_ONLY",
            "market_data_authority": False,
            "entry_effective_only_after_successful_durable_publication_readback": True,
            "entries": [],
        }
    value = _load_json(path)
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != CONSUMPTION_SCHEMA
        or value.get("authority") != "PROMOTION_CONSUMPTION_STATE_ONLY"
        or value.get("market_data_authority") is not False
        or not isinstance(value.get("entries"), list)
    ):
        raise PromotionError("PROMOTION_CONSUMPTION_LEDGER_INVALID", "promotion consumption ledger invalid")
    return dict(value)


def _write_consumption_entry(
    root: Path,
    *,
    handoff: Mapping[str, Any],
    promotion_result: str,
    observation_identities: list[Any],
    target_families: list[str],
    processed_at_utc: str,
) -> None:
    ledger = _read_consumption_ledger(root)
    entries = [dict(row) for row in ledger["entries"] if isinstance(row, Mapping)]
    handoff_id = str(handoff["handoff_id"])
    if any(row.get("handoff_id") == handoff_id for row in entries):
        return
    entries.append(
        {
            "handoff_id": handoff_id,
            "generation_id": handoff["generation_id"],
            "promotion_result": promotion_result,
            "canonical_observation_identities": observation_identities,
            "canonical_target_families": sorted(set(target_families)),
            "processed_at_utc": processed_at_utc,
        }
    )
    entries.sort(key=lambda row: str(row["handoff_id"]))
    ledger["entries"] = entries
    ledger["last_staged_at_utc"] = processed_at_utc
    _write_json(root / PROMOTION_LEDGER_PATH, ledger)


def _install_payload(
    *,
    artifact_root: Path,
    target_root: Path,
    resource: Mapping[str, Any],
) -> tuple[bool, Path]:
    family = str(resource["existing_target_family"])
    identity = resource["observation_identity"]
    if not isinstance(identity, Mapping) or not isinstance(identity.get("timestamp_ms"), int):
        raise PromotionError("OBSERVATION_IDENTITY_INVALID", "promotion timestamp missing")
    timestamp_ms = int(identity["timestamp_ms"])
    target_rel = _target_path(family, timestamp_ms)
    target = target_root / target_rel
    member = Path(str(resource["payload_member"]))
    source = artifact_root / member
    raw = source.read_bytes()
    digest = str(resource["payload_sha256"])
    if target.exists():
        existing = target.read_bytes()
        if _sha256_bytes(existing) != digest:
            raise PromotionError(
                "IMMUTABLE_OBSERVATION_CONFLICT",
                f"canonical snapshot identity already exists with different payload: {family}:{timestamp_ms}",
            )
        changed = False
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        changed = True

    run = resource.get("collection_run")
    if not isinstance(run, Mapping):
        raise PromotionError("COLLECTION_RUN_INVALID", f"missing collection run for {family}")
    ledger_rel = _collection_ledger_path(timestamp_ms)
    metadata = {
        "schema_version": COLLECTION_LEDGER_SCHEMA,
        "date_utc": _date_text(timestamp_ms),
    }
    try:
        append_partition(
            target_root / ledger_rel,
            metadata,
            [dict(run)],
            records_field="runs",
            key=lambda row: row["run_id"],
        )
    except (ImmutableHistoryConflict, ValueError, KeyError) as exc:
        raise PromotionError("COLLECTION_RUN_CONFLICT", f"collection-run promotion conflict: {family}:{timestamp_ms}") from exc
    return changed, target_rel


def apply_artifact(
    artifact_root: Path,
    *,
    repository_root: Path,
    source_control_root: Path | None,
    processed_at_utc: str,
) -> dict[str, Any]:
    processed_at = _format_utc(_parse_utc(processed_at_utc, "processed_at_utc"))
    handoff, _generation = validate_artifact(artifact_root, source_control_root=source_control_root)
    pending = [
        resource
        for resource in handoff["resources"]
        if resource.get("durability_class") == "PROMOTION_ELIGIBLE"
        and resource.get("promotion_required") is True
    ]
    if not pending:
        return {
            "handoff_id": handoff["handoff_id"],
            "status": "NO_PROMOTION_REQUIRED",
            "changed": False,
            "promoted_resources": 0,
            "deduplicated_resources": 0,
        }

    ledger = _read_consumption_ledger(repository_root)
    existing = {
        row.get("handoff_id")
        for row in ledger.get("entries", [])
        if isinstance(row, Mapping)
    }
    if handoff["handoff_id"] in existing:
        return {
            "handoff_id": handoff["handoff_id"],
            "status": "ALREADY_CONSUMED",
            "changed": False,
            "promoted_resources": 0,
            "deduplicated_resources": 0,
        }

    promoted = 0
    deduplicated = 0
    observation_identities: list[Any] = []
    target_families: list[str] = []
    for resource in pending:
        changed, _target = _install_payload(
            artifact_root=artifact_root,
            target_root=repository_root,
            resource=resource,
        )
        if changed:
            promoted += 1
        else:
            deduplicated += 1
        observation_identities.append(resource["observation_identity"])
        target_families.append(str(resource["existing_target_family"]))

    result = "PROMOTED" if promoted else "DEDUPLICATED"
    _write_consumption_entry(
        repository_root,
        handoff=handoff,
        promotion_result=result,
        observation_identities=observation_identities,
        target_families=target_families,
        processed_at_utc=processed_at,
    )
    return {
        "handoff_id": handoff["handoff_id"],
        "status": result,
        "changed": promoted > 0,
        "promoted_resources": promoted,
        "deduplicated_resources": deduplicated,
    }


def _discover_artifact_roots(inbox: Path) -> list[Path]:
    roots: list[Path] = []
    for handoff in sorted(inbox.rglob("promotion-handoff.json")):
        root = handoff.parent
        if not (root / "current-generation.json").is_file():
            raise PromotionError("HARVEST_ARTIFACT_INVALID", f"promotion handoff lacks generation manifest: {root}")
        roots.append(root)
    return roots


def apply_inbox(
    inbox: Path,
    *,
    repository_root: Path,
    source_control_root: Path | None,
    processed_at_utc: str,
) -> dict[str, Any]:
    results = []
    for root in _discover_artifact_roots(inbox):
        results.append(
            apply_artifact(
                root,
                repository_root=repository_root,
                source_control_root=source_control_root,
                processed_at_utc=processed_at_utc,
            )
        )
    return {
        "schema_version": "fresh-current-promotion-apply-summary/1.0.0",
        "status": "PASS",
        "artifact_count": len(results),
        "handoffs": results,
        "promoted_resources": sum(int(row["promoted_resources"]) for row in results),
        "deduplicated_resources": sum(int(row["deduplicated_resources"]) for row in results),
    }


def _github_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "eth-macro-data-bridge-current-promotion/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise PromotionError("ACTIONS_API_FAILED", f"GitHub Actions API request failed: {url}") from exc


class _ArtifactRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        target = urllib.parse.urlsplit(newurl)
        if (
            target.scheme.lower() != "https"
            or not target.hostname
            or target.username is not None
            or target.password is not None
        ):
            raise urllib.error.URLError("unsafe artifact redirect destination")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def _artifact_api_request(url: str, token: str) -> urllib.request.Request:
    source = urllib.parse.urlsplit(url)
    if (
        source.scheme.lower() != "https"
        or source.hostname != "api.github.com"
        or source.username is not None
        or source.password is not None
    ):
        raise PromotionError(
            "ACTIONS_ARTIFACT_DOWNLOAD_FAILED",
            "artifact download refused: source_host=INVALID_OR_UNTRUSTED exception=ValueError",
        )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "eth-macro-data-bridge-current-promotion/1.0",
        },
    )
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    return request


def _github_bytes(url: str, token: str) -> bytes:
    source_host = urllib.parse.urlsplit(url).hostname or "unknown"
    try:
        request = _artifact_api_request(url, token)
        opener = urllib.request.build_opener(_ArtifactRedirectHandler())
        with opener.open(request, timeout=60) as response:
            return response.read()
    except PromotionError:
        raise
    except urllib.error.HTTPError as exc:
        target_host = urllib.parse.urlsplit(getattr(exc, "url", "")).hostname or "unknown"
        raise PromotionError(
            "ACTIONS_ARTIFACT_DOWNLOAD_FAILED",
            f"artifact download failed: status={exc.code} source_host={source_host} "
            f"target_host={target_host} exception=HTTPError",
        ) from None
    except urllib.error.URLError as exc:
        reason_class = type(getattr(exc, "reason", None)).__name__
        raise PromotionError(
            "ACTIONS_ARTIFACT_DOWNLOAD_FAILED",
            f"artifact download failed: source_host={source_host} exception=URLError reason_class={reason_class}",
        ) from None
    except (OSError, ValueError) as exc:
        raise PromotionError(
            "ACTIONS_ARTIFACT_DOWNLOAD_FAILED",
            f"artifact download failed: source_host={source_host} exception={type(exc).__name__}",
        ) from None


def _safe_extract_zip(raw: bytes, destination: Path) -> None:
    with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
        handle.write(raw)
        handle.flush()
        with zipfile.ZipFile(handle.name) as archive:
            for member in archive.infolist():
                path = Path(member.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise PromotionError("ACTIONS_ARTIFACT_UNSAFE", f"unsafe Actions artifact member: {member.filename}")
            archive.extractall(destination)


def harvest_actions(
    *,
    repository: str,
    token: str,
    inbox: Path,
    max_pages: int = 10,
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise PromotionError("REPOSITORY_ID_INVALID", "repository must use owner/name")
    if not token:
        raise PromotionError("ACTIONS_TOKEN_MISSING", "GitHub Actions token is required")
    inbox.mkdir(parents=True, exist_ok=True)
    accepted = []
    seen = set()
    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/{repository}/actions/artifacts?per_page=100&page={page}"
        response = _github_json(url, token)
        artifacts = response.get("artifacts") if isinstance(response, Mapping) else None
        if not isinstance(artifacts, list):
            raise PromotionError("ACTIONS_API_INVALID", "Actions artifact list response invalid")
        for artifact in artifacts:
            if not isinstance(artifact, Mapping):
                continue
            artifact_id = artifact.get("id")
            name = artifact.get("name")
            if (
                not isinstance(artifact_id, int)
                or artifact_id in seen
                or not isinstance(name, str)
                or not ARTIFACT_NAME_RE.fullmatch(name)
                or artifact.get("expired") is True
            ):
                continue
            seen.add(artifact_id)
            workflow_run = artifact.get("workflow_run")
            if not isinstance(workflow_run, Mapping) or workflow_run.get("head_branch") != "main":
                continue
            run_id = workflow_run.get("id")
            if not isinstance(run_id, int):
                continue
            run = _github_json(f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", token)
            if not isinstance(run, Mapping):
                raise PromotionError("ACTIONS_API_INVALID", f"workflow run response invalid: {run_id}")
            if (
                run.get("status") != "completed"
                or run.get("conclusion") != "success"
                or run.get("event") != "issues"
                or run.get("name") != "Fresh current agent transport"
            ):
                continue
            download = artifact.get("archive_download_url")
            if not isinstance(download, str) or not download.startswith("https://api.github.com/"):
                raise PromotionError("ACTIONS_ARTIFACT_INVALID", f"artifact download URL invalid: {artifact_id}")
            destination = inbox / f"artifact-{artifact_id}"
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True)
            _safe_extract_zip(_github_bytes(download, token), destination)
            roots = _discover_artifact_roots(destination)
            if len(roots) != 1:
                raise PromotionError("HARVEST_ARTIFACT_INVALID", f"artifact must contain exactly one promotion handoff: {artifact_id}")
            accepted.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_name": name,
                    "workflow_run_id": run_id,
                    "workflow_head_sha": run.get("head_sha"),
                    "artifact_root": roots[0].as_posix(),
                }
            )
        if len(artifacts) < 100:
            break
    accepted.sort(key=lambda row: int(row["artifact_id"]))
    return {
        "schema_version": "fresh-current-promotion-harvest/1.0.0",
        "status": "PASS",
        "accepted_artifacts": accepted,
        "accepted_count": len(accepted),
        "completed_successful_only": True,
    }


def _append_output(path: Path | None, name: str, value: object) -> None:
    if path is None:
        return
    text = str(value)
    if "\n" in text or "\r" in text:
        raise PromotionError("UNSAFE_GITHUB_OUTPUT", f"unsafe multiline output: {name}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={text}\n")


def _command_build(args: argparse.Namespace) -> int:
    handoff = build_handoff(
        request_path=Path(args.request),
        output_root=Path(args.output_root),
        repository_root=Path(args.repository_root),
    )
    github_output = Path(args.github_output) if args.github_output else None
    _append_output(github_output, "handoff_id", handoff["handoff_id"])
    _append_output(github_output, "handoff_schema", HANDOFF_SCHEMA)
    _append_output(github_output, "promotion_required", str(handoff["promotion_required"]).lower())
    _append_output(github_output, "promotion_pending_count", handoff["promotion_pending_count"])
    print(
        f"CURRENT_DATA_PROMOTION_HANDOFF=PASS handoff_id={handoff['handoff_id']} "
        f"promotion_pending={handoff['promotion_pending_count']}"
    )
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    source = Path(args.source_control_root) if args.source_control_root else None
    handoff, _generation = validate_artifact(Path(args.artifact_root), source_control_root=source)
    print(f"CURRENT_DATA_PROMOTION_HANDOFF_VALIDATION=PASS handoff_id={handoff['handoff_id']}")
    return 0


def _command_apply(args: argparse.Namespace) -> int:
    result = apply_artifact(
        Path(args.artifact_root),
        repository_root=Path(args.repository_root),
        source_control_root=Path(args.source_control_root) if args.source_control_root else None,
        processed_at_utc=args.processed_at_utc or _format_utc(datetime.now(timezone.utc)),
    )
    if args.summary_output:
        _write_json(Path(args.summary_output), result)
    print(
        f"CURRENT_DATA_PROMOTION_APPLY=PASS handoff_id={result['handoff_id']} "
        f"status={result['status']} promoted={result['promoted_resources']} "
        f"deduplicated={result['deduplicated_resources']}"
    )
    return 0


def _command_apply_inbox(args: argparse.Namespace) -> int:
    result = apply_inbox(
        Path(args.inbox),
        repository_root=Path(args.repository_root),
        source_control_root=Path(args.source_control_root) if args.source_control_root else None,
        processed_at_utc=args.processed_at_utc or _format_utc(datetime.now(timezone.utc)),
    )
    if args.summary_output:
        _write_json(Path(args.summary_output), result)
    print(
        f"CURRENT_DATA_PROMOTION_INBOX=PASS artifacts={result['artifact_count']} "
        f"promoted={result['promoted_resources']} deduplicated={result['deduplicated_resources']}"
    )
    return 0


def _command_harvest(args: argparse.Namespace) -> int:
    token = os.environ.get(args.token_env, "")
    result = harvest_actions(
        repository=args.repository,
        token=token,
        inbox=Path(args.inbox),
        max_pages=args.max_pages,
    )
    if args.summary_output:
        _write_json(Path(args.summary_output), result)
    print(f"CURRENT_DATA_PROMOTION_HARVEST=PASS accepted={result['accepted_count']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded durable promotion handoff for fresh/current market-data evidence")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-handoff")
    build.add_argument("--request", required=True)
    build.add_argument("--output-root", required=True)
    build.add_argument("--repository-root", default=".")
    build.add_argument("--github-output")
    build.set_defaults(func=_command_build)

    validate = sub.add_parser("validate-artifact")
    validate.add_argument("--artifact-root", required=True)
    validate.add_argument("--source-control-root")
    validate.set_defaults(func=_command_validate)

    apply = sub.add_parser("apply-artifact")
    apply.add_argument("--artifact-root", required=True)
    apply.add_argument("--repository-root", required=True)
    apply.add_argument("--source-control-root")
    apply.add_argument("--processed-at-utc")
    apply.add_argument("--summary-output")
    apply.set_defaults(func=_command_apply)

    apply_many = sub.add_parser("apply-inbox")
    apply_many.add_argument("--inbox", required=True)
    apply_many.add_argument("--repository-root", required=True)
    apply_many.add_argument("--source-control-root")
    apply_many.add_argument("--processed-at-utc")
    apply_many.add_argument("--summary-output")
    apply_many.set_defaults(func=_command_apply_inbox)

    harvest = sub.add_parser("harvest-actions")
    harvest.add_argument("--repository", required=True)
    harvest.add_argument("--token-env", default="GITHUB_TOKEN")
    harvest.add_argument("--inbox", required=True)
    harvest.add_argument("--max-pages", type=int, default=10)
    harvest.add_argument("--summary-output")
    harvest.set_defaults(func=_command_harvest)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PromotionError as exc:
        print(f"CURRENT_DATA_PROMOTION={exc.code} error={exc}", file=sys.stderr)
        raise SystemExit(2)
