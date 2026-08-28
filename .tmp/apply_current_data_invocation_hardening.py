from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one anchor in {path}, got {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1. Canonical agent entrypoint: make the wire contract explicit and require preflight.
agents = ROOT / "AGENTS.md"
replace_once(
    agents,
    "Request body содержит только semantic requirements: canonical `required_series`, `required_domains`, `max_generation_age_seconds` и `current_policy=FINALIZED_ONLY`. `series_id` должен быть найден/проверен через `tools/capability_index.py`; не синтезировать его из provider/instrument strings.\n",
    "Request body — canonical JSON object контракта `fresh-current-agent-request/1.0.0`. Поле `request_type` ОБЯЗАТЕЛЬНО и имеет единственное допустимое значение `FRESH_CURRENT`; отсутствие этого поля является `INVALID_REQUEST_TYPE` и fail-closed. Минимальная wire-форма:\n\n"
    "```json\n"
    "{\n"
    "  \"request_type\": \"FRESH_CURRENT\",\n"
    "  \"required_series\": [],\n"
    "  \"required_domains\": [],\n"
    "  \"max_generation_age_seconds\": 600,\n"
    "  \"current_policy\": \"FINALIZED_ONLY\"\n"
    "}\n"
    "```\n\n"
    "Агент не должен вручную импровизировать wire protocol. При наличии checkout request сначала строится через `python tools/current_data_transport.py build-request ...`, затем обязательно preflight-ится через `python tools/current_data_transport.py parse-request --request-file <request.json> --output <normalized.json>` и только после PASS exact validated JSON используется как body `[current-data]` Issue. В connector-only среде, где локальный preflight недоступен, использовать exact `bridge-contract.json.semantic_resolution.current_data.request.canonical_template`, меняя только semantic requirements. После любой ошибки/unknown результата `create_issue` запрещено считать remote mutation отсутствующей без read-back по ожидаемому `[current-data]` title/request identity; retry допускается только после доказанного отсутствия Issue. `series_id` должен быть найден/проверен через `tools/capability_index.py`; не синтезировать его из provider/instrument strings.\n",
)

# 2. Machine contract: explicit required fields/template/preflight/read-back semantics.
bridge_path = ROOT / "bridge-contract.json"
bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
current_data = bridge["semantic_resolution"]["current_data"]
request = current_data["request"]
request["schema_version"] = "fresh-current-agent-request/1.0.0"
request["required_fields"] = [
    "request_type",
    "required_series",
    "required_domains",
    "max_generation_age_seconds",
    "current_policy",
]
request["request_type_required"] = True
request["request_type_const"] = "FRESH_CURRENT"
request["canonical_template"] = {
    "request_type": "FRESH_CURRENT",
    "required_series": [],
    "required_domains": [],
    "max_generation_age_seconds": 600,
    "current_policy": "FINALIZED_ONLY",
}
request["preflight"] = {
    "builder": "python tools/current_data_transport.py build-request",
    "validator": "python tools/current_data_transport.py parse-request --request-file <request.json> --output <normalized.json>",
    "required_before_issue_mutation_when_checkout_available": True,
    "connector_only_fallback": "USE_CANONICAL_TEMPLATE_WITHOUT_OMITTING_REQUIRED_FIELDS",
    "parser_remains_fail_closed": True,
}
agent_transport = current_data["agent_transport"]
agent_transport["mutation_outcome_readback"] = {
    "tool_error_or_unknown_does_not_prove_remote_mutation_absent": True,
    "required_action": "READ_BACK_EXPECTED_ISSUE_IDENTITY_BEFORE_RETRY",
    "retry_only_if_remote_issue_absence_proven": True,
    "duplicate_issue_creation_on_unknown_outcome": "FORBIDDEN",
}
bridge_path.write_text(json.dumps(bridge, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

# 3. Human implementation-facing semantics: canonical builder/preflight and ambiguous mutation handling.
semantics = ROOT / "docs/semantics/fresh-current-agent-transport-v1.md"
anchor = """`latest_bars` bounded: `1..4096` в v1. Plain string shorthand означает default `256`.\n"""
addition = """

### Canonical invocation / pre-mutation preflight

`request_type` — обязательный wire-level discriminator, а не необязательная подсказка агенту:

```text
REQUEST_SCHEMA=fresh-current-agent-request/1.0.0
REQUEST_TYPE_REQUIRED=YES
REQUEST_TYPE_CONST=FRESH_CURRENT
MISSING_REQUEST_TYPE=INVALID_REQUEST_TYPE
```

Canonical invocation state machine:

```text
semantic intent
→ canonical request builder/template
→ local parse/normalize preflight when checkout is available
→ exact validated JSON bytes
→ create owner-only [current-data] Issue
→ remote Issue read-back
→ GitHub workflow independently parses the same body again
```

Repository-owned builder для обычной wire-формы:

```bash
python tools/current_data_transport.py build-request \\
  --series spot.binance-spot.ETHUSDT.ohlcv.5m \\
  --domain SPOT \\
  --domain DERIVATIVES \\
  --max-generation-age-seconds 600 \\
  --current-policy FINALIZED_ONLY \\
  --output request.json

python tools/current_data_transport.py parse-request \\
  --request-file request.json \\
  --output normalized-request.json
```

Parser остаётся fail-closed и НЕ подставляет `FRESH_CURRENT` за отсутствующий `request_type`. В connector-only среде canonical template берётся из `bridge-contract.json.semantic_resolution.current_data.request.canonical_template`; агент меняет semantic lists/threshold, но не удаляет required protocol fields.

Mutation acknowledgement не является remote authority. Если `create_issue` вернул error/unknown, это означает `MUTATION_OUTCOME_UNKNOWN`, а не доказанное отсутствие side effect:

```text
create_issue error/unknown
→ read back expected [current-data] issue identity
→ issue exists: REMOTE_COMMIT_SUCCEEDED_LOCAL_ACK_UNKNOWN; continue from remote truth
→ issue absent: retry may be attempted idempotently
```

Повторное создание Issue до read-back запрещено.
"""
replace_once(semantics, anchor, anchor + addition)

# 4. Add repository-owned canonical request builder while preserving strict parser semantics.
transport = ROOT / "tools/current_data_transport.py"
command_anchor = """def _command_parse(args: argparse.Namespace) -> int:\n"""
builder_fn = """def _command_build_request(args: argparse.Namespace) -> int:\n    payload = {\n        \"request_type\": \"FRESH_CURRENT\",\n        \"required_series\": list(args.series),\n        \"required_domains\": list(args.domain),\n        \"max_generation_age_seconds\": args.max_generation_age_seconds,\n        \"current_policy\": args.current_policy,\n    }\n    normalized = normalize_request(payload)\n    _write_json(Path(args.output), normalized)\n    print(f\"CURRENT_DATA_REQUEST_BUILD=PASS output={args.output} request_sha256={_sha256_json(normalized)}\")\n    return 0\n\n\n"""
replace_once(transport, command_anchor, builder_fn + command_anchor)

parser_anchor = """    parse = sub.add_parser(\"parse-request\")\n"""
builder_parser = """    build = sub.add_parser(\"build-request\")\n    build.add_argument(\"--series\", action=\"append\", default=[])\n    build.add_argument(\"--domain\", action=\"append\", default=[])\n    build.add_argument(\"--max-generation-age-seconds\", type=int, default=DEFAULT_MAX_GENERATION_AGE_SECONDS)\n    build.add_argument(\"--current-policy\", default=D6_CURRENT_POLICY)\n    build.add_argument(\"--output\", required=True)\n    build.set_defaults(func=_command_build_request)\n\n"""
replace_once(transport, parser_anchor, builder_parser + parser_anchor)

# 5. Surface deterministic parser error code in the canonical Issue receipt.
workflow = ROOT / ".github/workflows/current-data-request.yml"
old_request_step = """      - name: Validate semantic issue request\n        id: request\n        continue-on-error: true\n        run: |\n          mkdir -p .current-data-output .current-data-work\n          python tools/current_data_transport.py parse-request \\\n            --event \"$GITHUB_EVENT_PATH\" \\\n            --output .current-data-work/request.json \\\n            --github-output \"$GITHUB_OUTPUT\"\n"""
new_request_step = """      - name: Validate semantic issue request\n        id: request\n        continue-on-error: true\n        shell: bash\n        run: |\n          set +e\n          mkdir -p .current-data-output .current-data-work\n          output=\"$(python tools/current_data_transport.py parse-request \\\n            --event \"$GITHUB_EVENT_PATH\" \\\n            --output .current-data-work/request.json \\\n            --github-output \"$GITHUB_OUTPUT\" 2>&1)\"\n          rc=$?\n          printf '%s\\n' \"$output\"\n          if [ \"$rc\" -ne 0 ]; then\n            error_code=\"$(printf '%s\\n' \"$output\" | sed -n 's/^CURRENT_DATA_TRANSPORT=\\([^ ]*\\).*/\\1/p' | tail -n 1)\"\n            if [ -z \"$error_code\" ]; then error_code=\"UNKNOWN_REQUEST_ERROR\"; fi\n            echo \"error_code=$error_code\" >> \"$GITHUB_OUTPUT\"\n            exit \"$rc\"\n          fi\n          echo \"error_code=NONE\" >> \"$GITHUB_OUTPUT\"\n"""
replace_once(workflow, old_request_step, new_request_step)
replace_once(
    workflow,
    """          REQUEST_OUTCOME: ${{ steps.request.outcome }}\n""",
    """          REQUEST_OUTCOME: ${{ steps.request.outcome }}\n          REQUEST_ERROR_CODE: ${{ steps.request.outputs.error_code }}\n""",
)
replace_once(
    workflow,
    """              `REQUEST_OUTCOME=${process.env.REQUEST_OUTCOME}`,\n""",
    """              `REQUEST_OUTCOME=${process.env.REQUEST_OUTCOME}`,\n              `REQUEST_ERROR_CODE=${process.env.REQUEST_ERROR_CODE || 'UNKNOWN_REQUEST_ERROR'}`,\n""",
)

# 6. New deterministic regression tests for the invocation contract.
test_path = ROOT / "tests/deep_history/test_current_data_invocation_contract.py"
test_path.write_text(
    '''from __future__ import annotations\n\nimport json\nimport tempfile\nimport unittest\nfrom pathlib import Path\n\nfrom tools.current_data_transport import CurrentDataTransportError, main, normalize_request\n\n\nROOT = Path(__file__).resolve().parents[2]\n\n\nclass CurrentDataInvocationContractTests(unittest.TestCase):\n    def test_machine_template_is_complete_and_parser_accepts_it(self) -> None:\n        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))\n        request = bridge["semantic_resolution"]["current_data"]["request"]\n        required = request["required_fields"]\n        self.assertEqual(\n            required,\n            [\n                "request_type",\n                "required_series",\n                "required_domains",\n                "max_generation_age_seconds",\n                "current_policy",\n            ],\n        )\n        self.assertTrue(request["request_type_required"])\n        self.assertEqual(request["request_type_const"], "FRESH_CURRENT")\n        template = dict(request["canonical_template"])\n        template["required_domains"] = ["SPOT"]\n        normalized = normalize_request(template)\n        self.assertEqual(normalized["request_type"], "FRESH_CURRENT")\n\n    def test_missing_request_type_remains_fail_closed(self) -> None:\n        with self.assertRaises(CurrentDataTransportError) as ctx:\n            normalize_request(\n                {\n                    "required_series": [],\n                    "required_domains": ["SPOT"],\n                    "max_generation_age_seconds": 600,\n                    "current_policy": "FINALIZED_ONLY",\n                }\n            )\n        self.assertEqual(ctx.exception.code, "INVALID_REQUEST_TYPE")\n\n    def test_repository_builder_materializes_required_discriminator(self) -> None:\n        with tempfile.TemporaryDirectory() as tmp:\n            output = Path(tmp) / "request.json"\n            rc = main(\n                [\n                    "build-request",\n                    "--domain",\n                    "SPOT",\n                    "--max-generation-age-seconds",\n                    "600",\n                    "--current-policy",\n                    "FINALIZED_ONLY",\n                    "--output",\n                    str(output),\n                ]\n            )\n            self.assertEqual(rc, 0)\n            payload = json.loads(output.read_text(encoding="utf-8"))\n            self.assertEqual(payload["request_type"], "FRESH_CURRENT")\n            self.assertEqual(payload["required_domains"], ["SPOT"])\n            self.assertEqual(normalize_request(payload), payload)\n\n    def test_entrypoint_and_semantics_require_preflight_and_remote_readback(self) -> None:\n        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")\n        semantics = (ROOT / "docs/semantics/fresh-current-agent-transport-v1.md").read_text(encoding="utf-8")\n        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))\n        transport = bridge["semantic_resolution"]["current_data"]["agent_transport"]\n        self.assertIn('"request_type": "FRESH_CURRENT"', agents)\n        self.assertIn("build-request", agents)\n        self.assertIn("parse-request --request-file", agents)\n        self.assertIn("MUTATION_OUTCOME_UNKNOWN", semantics)\n        self.assertTrue(transport["mutation_outcome_readback"]["tool_error_or_unknown_does_not_prove_remote_mutation_absent"])\n        self.assertTrue(transport["mutation_outcome_readback"]["retry_only_if_remote_issue_absence_proven"])\n\n    def test_workflow_surfaces_request_error_code(self) -> None:\n        workflow = (ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")\n        self.assertIn("REQUEST_ERROR_CODE: ${{ steps.request.outputs.error_code }}", workflow)\n        self.assertIn("error_code=$error_code", workflow)\n        self.assertIn("REQUEST_ERROR_CODE=${process.env.REQUEST_ERROR_CODE", workflow)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
    encoding="utf-8",
)

print("CURRENT_DATA_INVOCATION_HARDENING_PATCH=APPLIED")
