# PR effective-integration requalification v1

## Назначение

`pr-effective-integration-requalification/1.0.0` — repository-native read-only route для повторной qualification уже существующего open same-repository PR после движения `main`, когда изменение PR head ради refresh base запрещено или не требуется.

Закрываемый риск:

```text
STALE_PR_SYNTHETIC_QUALIFICATION_AFTER_MONOTONIC_MAIN_DRIFT
```

Route не заменяет обычную PR qualification и не меняет merge authority. Он существует только для late-bound owner-readiness evidence перед отдельным owner pre-merge gate.

## Canonical route

```text
workflow_dispatch on current main
→ exact pr_number + expected_pr_head_sha
→ fresh GitHub PR metadata readback
→ same-repository/open/unmerged/main-base checks
→ fresh origin/main effective base
→ exact remote PR head readback
→ local git merge-tree --write-tree
→ local git commit-tree(parent1=effective base,parent2=PR head)
→ tools/current_data_pr_binding.py verify
→ detach checkout exact synthetic SHA/tree
→ repository-native qualification contour
→ fresh origin/main readback
→ require_no_final_main_drift
```

Workflow authority:

```text
WORKFLOW_PATH=.github/workflows/qualify-pr-effective-integration.yml
TRIGGER=workflow_dispatch
REQUIRED_INPUTS=pr_number,expected_pr_head_sha
WORKFLOW_DEFINITION_AUTHORITY=current main only
```

Dispatch from any ref other than current `main`, or a `GITHUB_SHA` that no longer equals fresh `origin/main` at the authority gate, fails closed.

## Security boundary

Permissions are read-only:

```text
contents=read
pull-requests=read
```

Target PR must satisfy all predicates:

```text
PR_STATE=open
PR_MERGED=false
PR_BASE_REF=main
PR_HEAD_REPOSITORY=github.repository
PR_BASE_REPOSITORY=github.repository
PR_HEAD_SHA=expected_pr_head_sha
```

Fork/cross-repository PRs are rejected. `persist-credentials=false` is mandatory. The route does not push synthetic commits, create qualification branches/tags, change PR metadata, write Issues, create Fresh Current requests, or merge anything.

```text
REMOTE_REF_MUTATION_COUNT=0
TARGET_PR_MUTATION_COUNT=0
```

## Effective integration identity

Existing authority remains unchanged:

```text
PREMERGE_EFFECTIVE_INTEGRATION_IDENTITY=BASE_SHA+PR_HEAD_SHA+INTEGRATION_TREE_SHA
SYNTHETIC_PARENT_1_SHA=PR_EFFECTIVE_BASE_SHA
SYNTHETIC_PARENT_2_SHA=TARGET_PR_HEAD_SHA
SYNTHETIC_MERGE_SHA_ROLE=EPHEMERAL_PROVENANCE_ONLY
```

`tools/current_data_pr_binding.py` remains the only PR binding authority. This route reuses `verify_binding()` and `require_no_final_main_drift()` without changing their semantics.

A conflict from `git merge-tree --write-tree` is terminal for the run:

```text
LATE_BOUND_PR_EFFECTIVE_INTEGRATION_CONFLICT
```

No working-tree merge, rebase, empty commit, force-push or target-PR update is used to resolve base drift.

## Qualification and evidence

Qualification runs on detached exact local synthetic bytes, never on PR head alone, current `main` alone, or a predecessor GitHub synthetic SHA. The contour is intentionally no weaker than current repository validation and includes compile checks, repository validators, current-data binding regressions, recovery-policy tests and full deep-history tests.

Each successful run logs machine-readable evidence including:

```text
QUALIFICATION_ROUTE_SCHEMA
TARGET_PR_NUMBER
TARGET_PR_STATE
TARGET_PR_HEAD_SHA
TARGET_PR_HEAD_TREE
PR_EVENT_BASE_SHA
PR_EFFECTIVE_BASE_SHA
PR_EFFECTIVE_BASE_TREE
PR_EFFECTIVE_INTEGRATION_SHA
PR_EFFECTIVE_INTEGRATION_TREE
SYNTHETIC_PARENT_1_SHA
SYNTHETIC_PARENT_2_SHA
PR_EFFECTIVE_INTEGRATION_BINDING
QUALIFICATION_CHECKOUT_SHA
QUALIFICATION_CHECKOUT_TREE
TEST_COUNT
FAILURE_COUNT
SKIP_COUNT
SKIP_CLASS
POSTQUAL_FINAL_MAIN_SHA
OWNER_READINESS_FINAL_MAIN_DRIFT
REMOTE_REF_MUTATION_COUNT
TARGET_PR_MUTATION_COUNT
```

The evidence JSON is an Actions run artifact-in-log/step-summary evidence object, not repository authority.

## Final-main race and retry

After all tests the route fresh-fetches `origin/main` and invokes existing `require_no_final_main_drift()`.

```text
PASS iff POSTQUAL_FINAL_MAIN_SHA == PR_EFFECTIVE_BASE_SHA
```

If `main` moves during qualification, the workflow fails. This is not a source defect. The same unchanged PR may be re-dispatched with the same exact head input; every retry performs fresh PR readback, fresh main pin, a new local synthetic integration and a new final-main gate.

```text
RETRY_REQUIRES_PR_MUTATION=NO
RETRY_REQUIRES_EMPTY_COMMIT=NO
RETRY_REQUIRES_REBASE=NO
RETRY_REQUIRES_REMOTE_BRANCH=NO
```

## Non-change proof

This route does not change request, recovery, provider, storage, normal finalizer or binding semantics:

```text
REQUEST_SCHEMA_CHANGED=NO
REQUEST_SHA_SEMANTICS_CHANGED=NO
RECOVERY_POLICY_CHANGED=NO
RECOVERY_RECEIPT_SCHEMA_CHANGED=NO
PROVIDER_SEMANTICS_CHANGED=NO
STORAGE_SEMANTICS_CHANGED=NO
NORMAL_FINALIZER_SEMANTICS_CHANGED=NO
CURRENT_DATA_PR_BINDING_SEMANTICS_CHANGED=NO
FINAL_MAIN_DRIFT_SEMANTICS_CHANGED=NO
SECOND_MARKET_DATA_AUTHORITY=NO
SECOND_CURRENT_DATA_TRANSPORT=NO
```
