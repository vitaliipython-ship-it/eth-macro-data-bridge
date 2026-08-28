from pathlib import Path


def replace_exact(text, old, new, *, count=1, label="replacement"):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"{label}: expected {count} occurrences, found {actual}")
    return text.replace(old, new)


# State-aware global Kraken generation integrity.
path = Path("tools/validation/validate_v4.py")
text = path.read_text(encoding="utf-8")
text = replace_exact(
    text,
    "from event_window import nearest_v4\n",
    "from event_window import nearest_v4\nfrom current_data_request_scope import validate_kraken_generation_integrity\n",
    label="validate_v4 import",
)
text = replace_exact(
    text,
    '    assert all(not m["more"] and m["data_age_seconds"]<=600 and m["freshness_status"]=="LIVE_USABLE" for x in k["instruments"].values() for m in x["metrics"].values())\n'
    '    print("KRAKEN_MORE_HANDLING=PASS\\nKRAKEN_CURRENT_TAIL=PASS\\nCURRENT_DERIVATIVES_FRESHNESS=PASS")\n',
    '    analytics_current=json.loads(Path("analytics/manifest.json").read_text())\n'
    '    kraken_integrity=validate_kraken_generation_integrity(k, analytics_current)\n'
    '    assert kraken_integrity["generation_integrity_status"]=="PASS"\n'
    '    print("KRAKEN_MORE_HANDLING=PASS\\nKRAKEN_CURRENT_TAIL=STATE_AWARE\\nCURRENT_DERIVATIVES_FRESHNESS=STATE_AWARE")\n'
    '    print("KRAKEN_FUTURES_COLLECTION_STATUS="+kraken_integrity["collection_status"])\n'
    '    print("KRAKEN_FUTURES_METRIC_QUALIFICATION_STATUS="+kraken_integrity["metric_qualification_status"])\n'
    '    print("GENERATION_INTEGRITY_VS_REQUEST_SATISFACTION=SEPARATED")\n'
    '    print("COLLECTION_VS_METRIC_QUALIFICATION=SEPARATED")\n',
    label="validate_v4 blanket invariant",
)
path.write_text(text, encoding="utf-8")


# Fresh Current workflow: keep structural/global integrity before materialization,
# then run request-scoped satisfaction after resource index construction.
path = Path(".github/workflows/current-data-request.yml")
text = path.read_text(encoding="utf-8")
text = replace_exact(
    text,
    "      - tools/current_data_transport.py\n",
    "      - tools/current_data_transport.py\n      - tools/current_data_request_scope.py\n",
    count=2,
    label="workflow helper path filters",
)
text = replace_exact(
    text,
    "      - tests/deep_history/test_current_data_transport.py\n",
    "      - tests/deep_history/test_current_data_transport.py\n      - tests/deep_history/test_current_data_request_scope_qualification.py\n",
    count=2,
    label="workflow test path filters",
)
text = replace_exact(
    text,
    "      - name: Validate current generation before exposure\n        id: repository_validation\n",
    "      - name: Validate global generation integrity before exposure\n        id: generation_integrity\n",
    label="global integrity step",
)
text = text.replace("steps.repository_validation.outcome", "steps.generation_integrity.outcome")
text = replace_exact(
    text,
    "      - name: Validate requested generation semantics\n"
    "        id: generation_validation\n"
    "        if: steps.index.outcome == 'success'\n"
    "        continue-on-error: true\n"
    "        run: |\n"
    "          python tools/current_data_transport.py validate-generation \\\n"
    "            --request .current-data-work/request.json \\\n"
    "            --output-root .current-data-output\n",
    "      - name: Qualify exact requested generation semantics\n"
    "        id: request_satisfaction\n"
    "        if: steps.index.outcome == 'success'\n"
    "        continue-on-error: true\n"
    "        run: |\n"
    "          python tools/current_data_request_scope.py qualify-request \\\n"
    "            --request .current-data-work/request.json \\\n"
    "            --output-root .current-data-output \\\n"
    "            --github-output \"$GITHUB_OUTPUT\"\n",
    label="request satisfaction step",
)
text = text.replace("steps.generation_validation.outcome", "steps.request_satisfaction.outcome")
text = replace_exact(
    text,
    "          REPOSITORY_VALIDATION_OUTCOME: ${{ steps.generation_integrity.outcome }}\n",
    "          GENERATION_INTEGRITY_OUTCOME: ${{ steps.generation_integrity.outcome }}\n"
    "          REPOSITORY_VALIDATION_OUTCOME: ${{ steps.generation_integrity.outcome }}\n",
    label="generation integrity receipt env",
)
text = replace_exact(
    text,
    "          GENERATION_VALIDATION_OUTCOME: ${{ steps.request_satisfaction.outcome }}\n",
    "          REQUEST_SATISFACTION_OUTCOME: ${{ steps.request_satisfaction.outcome }}\n"
    "          GENERATION_VALIDATION_OUTCOME: ${{ steps.request_satisfaction.outcome }}\n",
    label="request satisfaction receipt env",
)
text = replace_exact(
    text,
    "          REQUIRED_DOMAINS: ${{ steps.request.outputs.required_domains }}\n",
    "          REQUIRED_DOMAINS: ${{ steps.request.outputs.required_domains }}\n"
    "          UNSATISFIED_REQUIRED_RESOURCE_COUNT: ${{ steps.request_satisfaction.outputs.unsatisfied_required_resource_count }}\n"
    "          UNSATISFIED_REQUIRED_DOMAIN_COUNT: ${{ steps.request_satisfaction.outputs.unsatisfied_required_domain_count }}\n"
    "          UNREQUESTED_DEGRADED_RESOURCE_COUNT: ${{ steps.request_satisfaction.outputs.unrequested_degraded_resource_count }}\n",
    label="bounded qualification diagnostics env",
)
text = text.replace("process.env.REPOSITORY_VALIDATION_OUTCOME", "process.env.GENERATION_INTEGRITY_OUTCOME")
text = text.replace("process.env.GENERATION_VALIDATION_OUTCOME", "process.env.REQUEST_SATISFACTION_OUTCOME")
text = replace_exact(
    text,
    "            else if (process.env.GENERATION_INTEGRITY_OUTCOME !== 'success') failureCategory = 'VALIDATION_FAILED';\n",
    "            else if (process.env.GENERATION_INTEGRITY_OUTCOME !== 'success') failureCategory = 'GENERATION_INTEGRITY_FAILED';\n",
    label="integrity failure category",
)
text = replace_exact(
    text,
    "            else if (process.env.INDEX_OUTCOME !== 'success' || process.env.REQUEST_SATISFACTION_OUTCOME !== 'success') failureCategory = 'GENERATION_VALIDATION_FAILED';\n",
    "            else if (process.env.INDEX_OUTCOME !== 'success') failureCategory = 'GENERATION_VALIDATION_FAILED';\n"
    "            else if (process.env.REQUEST_SATISFACTION_OUTCOME !== 'success') failureCategory = 'REQUEST_SATISFACTION_FAILED';\n",
    label="request failure category",
)
text = replace_exact(
    text,
    "              `REQUIRED_DOMAINS=${process.env.REQUIRED_DOMAINS}`,\n              'VALIDATION=PASS',\n",
    "              `REQUIRED_DOMAINS=${process.env.REQUIRED_DOMAINS}`,\n"
    "              'GENERATION_INTEGRITY_OUTCOME=success',\n"
    "              'SERIES_OUTCOME=success',\n"
    "              'RESOURCE_INDEX_OUTCOME=success',\n"
    "              'REQUEST_SATISFACTION_OUTCOME=success',\n"
    "              'GENERATION_VALIDATION_OUTCOME=success',\n"
    "              'RECEIPT_OUTCOME=success',\n"
    "              `UNSATISFIED_REQUIRED_RESOURCE_COUNT=${process.env.UNSATISFIED_REQUIRED_RESOURCE_COUNT || '0'}`,\n"
    "              `UNSATISFIED_REQUIRED_DOMAIN_COUNT=${process.env.UNSATISFIED_REQUIRED_DOMAIN_COUNT || '0'}`,\n"
    "              `UNREQUESTED_DEGRADED_RESOURCE_COUNT=${process.env.UNREQUESTED_DEGRADED_RESOURCE_COUNT || '0'}`,\n"
    "              'VALIDATION=PASS',\n",
    label="success receipt outcomes",
)
text = replace_exact(
    text,
    "              `REPOSITORY_VALIDATION_OUTCOME=${process.env.GENERATION_INTEGRITY_OUTCOME}`,\n"
    "              `SERIES_OUTCOME=${process.env.SERIES_OUTCOME}`,\n"
    "              `GENERATION_VALIDATION_OUTCOME=${process.env.REQUEST_SATISFACTION_OUTCOME}`,\n",
    "              `GENERATION_INTEGRITY_OUTCOME=${process.env.GENERATION_INTEGRITY_OUTCOME}`,\n"
    "              `REPOSITORY_VALIDATION_OUTCOME=${process.env.GENERATION_INTEGRITY_OUTCOME}`,\n"
    "              `SERIES_OUTCOME=${process.env.SERIES_OUTCOME}`,\n"
    "              `RESOURCE_INDEX_OUTCOME=${process.env.INDEX_OUTCOME}`,\n"
    "              `REQUEST_SATISFACTION_OUTCOME=${process.env.REQUEST_SATISFACTION_OUTCOME}`,\n"
    "              `GENERATION_VALIDATION_OUTCOME=${process.env.REQUEST_SATISFACTION_OUTCOME}`,\n"
    "              `UNSATISFIED_REQUIRED_RESOURCE_COUNT=${process.env.UNSATISFIED_REQUIRED_RESOURCE_COUNT || '0'}`,\n"
    "              `UNSATISFIED_REQUIRED_DOMAIN_COUNT=${process.env.UNSATISFIED_REQUIRED_DOMAIN_COUNT || '0'}`,\n"
    "              `UNREQUESTED_DEGRADED_RESOURCE_COUNT=${process.env.UNREQUESTED_DEGRADED_RESOURCE_COUNT || '0'}`,\n",
    label="failure receipt outcomes",
)
# The existing live candidate rehearsal and PR integration qualification use the same repaired qualification command.
text = replace_exact(
    text,
    "          python tools/current_data_transport.py validate-generation \\\n            --request .current-data-work/request.json \\\n            --output-root .current-data-output\n",
    "          python tools/current_data_request_scope.py qualify-request \\\n            --request .current-data-work/request.json \\\n            --output-root .current-data-output\n",
    label="candidate request qualification",
)
text = replace_exact(
    text,
    "    if: github.event_name == 'pull_request' && github.head_ref == 'agent/market-data/fresh-current-agent-transport-v1'\n",
    "    if: github.event_name == 'pull_request' && github.head_ref == 'agent/current-data/invocation-contract-hardening-v1'\n",
    label="PR qualification branch",
)
path.write_text(text, encoding="utf-8")

print("FRESH_CURRENT_REQUEST_SCOPE_REPAIR_APPLIED=YES")
