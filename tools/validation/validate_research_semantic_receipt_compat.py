from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_validator(research_root: Path):
    module_path = research_root / "tools/validation/validate_research.py"
    spec = importlib.util.spec_from_file_location("research_receipt_compat", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Research validator module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--bridge-head", required=True)
    args = parser.parse_args()

    research_root = Path(args.research_root).resolve()
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    schema = json.loads((research_root / "control/schemas/market-data-ref.schema.json").read_text(encoding="utf-8"))
    if schema["properties"]["semantic_receipt"]["properties"]["receipt_schema_version"]["enum"] != ["history-access-receipt/2.0.0"]:
        raise RuntimeError("unexpected Research semantic receipt schema authority")

    vr = load_validator(research_root)
    fixture = json.loads((research_root / "tools/validation/fixtures/f1/valid-semantic-receipt.json").read_text(encoding="utf-8"))
    end = receipt["request"]["to_utc"]
    end_dt = parse_utc(end)
    fixture["as_of_utc"] = end
    fixture["known_at_utc"] = iso(end_dt + timedelta(minutes=10))
    fixture["created_at_utc"] = iso(end_dt + timedelta(minutes=11))
    fixture["payload"]["market_data_ref"] = {
        "repository": "vitaliipython-ship-it/eth-macro-data-bridge",
        "head": args.bridge_head,
        "contract_path": "bridge-contract.json",
        "as_of_utc": end,
        "semantic_receipt": receipt,
    }
    fixture["source_refs"] = [
        f"market-data:bridge:{args.bridge_head}:history-read:qualification:"
        f"plan={receipt['resolution_plan_sha256']}:output={receipt['output_sha256']}"
    ]

    validator = vr.ResearchValidator(research_root)

    def codes(obj) -> set[str]:
        validator.issues = []
        validator.validate_source_provenance(obj, Path("data-bridge-semantic-receipt-qualification.json"))
        return {issue.code for issue in validator.issues}

    positive = codes(fixture)
    if positive:
        raise RuntimeError(f"Research positive compatibility failed: {sorted(positive)}")

    cases = []

    obj = copy.deepcopy(fixture)
    obj["source_refs"][0] = obj["source_refs"][0].replace(args.bridge_head, "1" * 40)
    cases.append(("head_mismatch", obj, {"MARKET_HEAD_MISMATCH"}))

    obj = copy.deepcopy(fixture)
    obj["source_refs"][0] = obj["source_refs"][0].replace(receipt["resolution_plan_sha256"], "2" * 64)
    cases.append(("plan_mismatch", obj, {"MARKET_PLAN_MISMATCH"}))

    obj = copy.deepcopy(fixture)
    obj["source_refs"][0] = obj["source_refs"][0].replace(receipt["output_sha256"], "3" * 64)
    cases.append(("output_mismatch", obj, {"MARKET_OUTPUT_MISMATCH"}))

    obj = copy.deepcopy(fixture)
    request = obj["payload"]["market_data_ref"]["semantic_receipt"]["request"]
    request.pop("from_utc", None); request.pop("to_utc", None)
    cases.append(("missing_request_identity", obj, {"SEMANTIC_REQUEST_IDENTITY"}))

    obj = copy.deepcopy(fixture)
    obj["payload"]["market_data_ref"]["semantic_receipt"]["series_id"] = "bad series id"
    cases.append(("malformed_series_id", obj, {"SEMANTIC_SERIES_ID"}))

    obj = copy.deepcopy(fixture)
    obj["payload"]["market_data_ref"]["semantic_receipt"]["finality"] = "INVALID"
    cases.append(("invalid_finality", obj, set()))

    obj = copy.deepcopy(fixture)
    obj["payload"]["market_data_ref"]["semantic_receipt"]["storage_path"] = "history/forbidden"
    cases.append(("unsupported_storage_field", obj, {"SCHEMA_ADDITIONAL_PROPERTY"}))

    obj = copy.deepcopy(fixture)
    rec = obj["payload"]["market_data_ref"]["semantic_receipt"]
    cutoff = end_dt + timedelta(minutes=1)
    rec["request"]["cutoff_utc"] = iso(cutoff)
    rec["revision_context"] = {
        "observation_time_utc": rec["request"]["from_utc"],
        "effective_time_utc": rec["request"]["from_utc"],
        "revision_known_at_utc": iso(cutoff + timedelta(minutes=1)),
        "evidence_sha256": "e" * 64,
    }
    obj["known_at_utc"] = iso(cutoff + timedelta(minutes=5))
    cases.append(("revision_known_after_cutoff", obj, {"SEMANTIC_REVISION_CUTOFF"}))

    for name, obj, expected in cases:
        got = codes(obj)
        if not got:
            raise RuntimeError(f"Research negative case did not fail closed: {name}")
        if expected and not (got & expected):
            raise RuntimeError(f"Research negative case {name} missing expected code {sorted(expected)}; got {sorted(got)}")
        print(f"RESEARCH_NEGATIVE_{name.upper()}=PASS codes={','.join(sorted(got))}")

    print("DATA_BRIDGE_V2_RECEIPT_TO_RESEARCH_SCHEMA=PASS")
    print("RESEARCH_SCHEMA_HEAD=" + args.bridge_head)
    print("SEMANTIC_RECEIPT_SCHEMA=" + receipt["receipt_schema_version"])
    print("SEMANTIC_RECEIPT_PLAN_SHA256=" + receipt["resolution_plan_sha256"])
    print("SEMANTIC_RECEIPT_OUTPUT_SHA256=" + receipt["output_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
