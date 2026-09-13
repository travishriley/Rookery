# State Machine

Status: proposed guarded transitions. No physical action is performed by a transition. Record human actions as observations with evidence and timestamps; approval is not an observation of activation or print start.

## Main Progression

| From -> To | Required guard and event |
| --- | --- |
| DISCOVERED -> SNAPSHOT_VERIFIED | Lossless complete graph, drift checks, integrity and backup policy receipts valid |
| SNAPSHOT_VERIFIED -> AUDITED | Semantic resolution and source/runtime uncertainty recorded; audit immutable |
| AUDITED -> BASELINE_PACKAGE_REVIEWED | Baseline considered suitable by explicit human package review; raw G-code, dependencies, ranges, macros and geometry scoped; no unresolved blocking hazard |
| BASELINE_PACKAGE_REVIEWED -> AWAITING_HUMAN_BASELINE_PRINT | Valid baseline package authorization; baseline activation/setup observation adequate; instructions exported locally |
| AWAITING_HUMAN_BASELINE_PRINT -> BASELINE_EVIDENCE_ACCEPTED | Human run observation linked to exact baseline artifact; capture coverage/identity/controls/measurements gates pass |
| BASELINE_EVIDENCE_ACCEPTED -> DIAGNOSED | Frozen prompt/provider/preprocessing/rubric; bounded diagnosis validates; insufficient/manual outcomes branch out |
| DIAGNOSED -> CANDIDATE_STAGED | One allowed independent change, exact source/value preconditions, backup policy reverified; protected changes cannot be staged |
| CANDIDATE_STAGED -> VALIDATED | Complete staged dependencies, raw generated artifact and semantic/raw diff checks, reproducibility manifest, calibration ranges and macro review pass |
| VALIDATED -> AWAITING_APPROVAL | Complete readable evidence packet; source rehash, budget, privacy and policy checks current |
| AWAITING_APPROVAL -> APPROVED_FOR_EXPORT | Authenticated, unexpired, unrevoked human `candidate_export` approval binds all required digests and exact operation |
| APPROVED_FOR_EXPORT -> AWAITING_HUMAN_IMPORT_AND_ACTIVATION | Recheck source/evidence/policy/approval and export bytes; publish local immutable export receipt; no upload |
| AWAITING_HUMAN_IMPORT_AND_ACTIVATION -> ACTIVATION_OBSERVED | Human import/activation statement plus available loaded/runtime evidence match candidate; unsupported firmware scoped explicitly; unknown activation blocks |
| ACTIVATION_OBSERVED -> AWAITING_HUMAN_CANDIDATE_PRINT | Separate candidate `test_package_review`, fresh activation/setup observation, budget and controls pass |
| AWAITING_HUMAN_CANDIDATE_PRINT -> CANDIDATE_EVIDENCE_ACCEPTED | Human reports this run and artifact; complete evidence passes same baseline criteria |
| CANDIDATE_EVIDENCE_ACCEPTED -> COMPARED | Frozen comparison method, required repetitions and controls pass; independent metrics plus uncertainty retained |
| COMPARED -> PROMOTED / REJECTED / NO_CHANGE | Human recommendation decision with rationale; quality floors/budgets respected; promotion is a recommendation only |

`baseline_package_review`, `candidate_export`, and `test_package_review` are different approval scopes. A baseline-only package has no candidate digest; candidate scopes require one. Raw artifacts can exist without being authorized for use. Each physical print is independently started by the human; the application records a run observation only after the fact and cannot send the start instruction.

A read-only audit/diagnosis may be recorded while DISCOVERED before a fresh backup. It does not advance this main path, produce staged candidate bytes, or claim SNAPSHOT_VERIFIED. This separates useful diagnosis from backup-gated materialization.

## Exceptional States

| State | Trigger | Permitted recovery |
| --- | --- | --- |
| INSUFFICIENT_EVIDENCE | Missing/blurred/wrong views, identity/measurement/control gap | Append new bundle, revalidate, return to relevant evidence gate; previous diagnosis invalidated |
| UNSAFE_BASELINE | Unknown dangerous macro, protection issue, unreviewed range | Human hardware/config audit outside app; new snapshot/baseline revision; never auto-repair safety controls |
| APPROVAL_EXPIRED | Expiry, revocation, reviewer change or stale checks | New explicit approval over freshly checked scope; cannot resurrect old record |
| CONFIGURATION_DRIFT | Source/candidate/runtime identity mismatch | New snapshot/revision and baseline as required; invalidate downstream approval |
| BACKUP_FAILED | Policy unsatisfied, corrupt/missing read-back, unavailable destination | Preserve last verified copies; retry within budget and verify independently before candidate work |
| INTERRUPTED | Worker crash, timeout, journal/staging I/O failure | Quarantine incomplete outputs, recover durable event boundary, recheck gates before resuming |
| MANUAL_CHECK_NEEDED | Protected edit, unresolved precedence, uncertain physical cause or activation | Human evidence required; append decision, return to responsible gate only if resolved |
| BUDGET_EXHAUSTED | Request/frame/token/storage/retry/experiment/time/material limit | Freeze; human reviews explicit new budget revision, which invalidates affected approval |
| NO_CHANGE | Human choice or valid diagnosis with no improvement proposed | Terminal for that revision; preserve evidence, no candidate required |

Each blocked event stores previous state, reason codes, related digests, recovery gate, and required actor. Recovery always traverses the relevant guards; there is no generic force/skip-gate action. All unspecified transitions are denied. Terminal runs are immutable; retests create a new run with changed-conditions rationale.

## Concurrency and Invalidation

Use journal sequence plus expected previous event digest for optimistic concurrency. Duplicate operation IDs return the prior result only if inputs match. Concurrent approval/export and source changes require fresh snapshot checks and immutable local output; external edits after the final read cannot be prevented, so export records the observation time and manual import must verify intended bytes. Before interpretation, activation/runtime observations are checked again.

Any candidate bytes, source, relevant policy, evidence freshness, scope, calibration artifact, or toolchain change invalidates downstream authorization. A rebase with identical content can retain eligible approval only after the configured review protocol verifies content, reviewer state, checks, and revocations. A merge alone advances no experiment state.
