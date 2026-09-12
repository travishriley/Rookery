# What Is Good

A review that only lists problems gives a misleading picture of a PR like this one, and it risks the next revision "simplifying away" something load-bearing. These are the things I specifically checked, found correct, and think should be preserved.

## Safety architecture

**The model cannot escalate its own authority, and this is enforced structurally rather than by convention.** `DiagnosticResponse` forces `risk: bounded_slicer` whenever `outcome: propose_bounded_change`, which chains into `ProposalPayload` restricting `domain` to the three Orca domains, which means `klipper_audit_only` is unreachable from model output. Then `ApprovalRecord.risk_scope` has no enum value that could authorise an elevated proposal, so even a human-authored elevated proposal has no export path. Three independent layers, each of which would suffice, composed so that no single edit opens the path. I tried six attack shapes and all six were rejected.

**The human is outside the software boundary, and the architecture diagram says so.** The Mermaid flow ends at `M[Human import activation and print]` with the note "The final human node is outside Rookery. There is no software edge from the product to a printer control interface." Combined with `ActivationObservation` being a *record of what a human did* rather than a command, this keeps the "no actuation" claim structural rather than aspirational.

**Failure states are first-class.** `UNSAFE_BASELINE`, `BACKUP_FAILED`, `MANUAL_CHECK_NEEDED`, `BUDGET_EXHAUSTED`, `INSUFFICIENT_EVIDENCE` and `NO_CHANGE` all have documented triggers and documented recovery paths, and `state-machine.md` states "there is no generic force/skip-gate action". Systems that touch heating elements fail badly when the error path is an afterthought; here it is half the design.

**Distinguishing paused from idle (H05) and files from loaded configuration (H05/H16).** These are the two mistakes that get people hurt with 3D printers, and both are named explicitly with a "never equate" rule rather than a mitigation.

## Security engineering

**Remote `$ref` retrieval is blocked and independently asserted.** `no_remote_schema` raises `NoSuchResource` on any fetch, *and* `check_refs` separately walks the whole document asserting every `$ref` starts with `#/$defs/` and resolves locally. Belt and braces on a genuine SSRF / schema supply-chain vector that most projects leave open.

**Strict JSON parsing before schema validation.** Duplicate keys, `NaN`, `Infinity`, and overflow-to-infinity literals like `1e999` are all rejected at parse time, and all four are probed. For a project whose input is other people's config files, getting duplicate-key handling right at the parser layer is the correct instinct.

**The model-facing type is deliberately separate from the application-owned type.** `DiagnosticResponse` has `additionalProperties: false` and no `id`, `created_at`, or self-referential digests, so the model cannot mint record identity or hash its own output. `data-contracts.md` states the reasoning: "This avoids asking a model to invent or self-hash records." That is exactly right and is a pattern worth carrying into every future provider adapter.

**Synthetic examples use deliberately fictional keys and units** — `fictional_parameter_not_an_orca_key`, `fictional_units`, `synthetic-*` ids — so nothing in the public repo can be copy-pasted into a real profile. Small discipline, real benefit.

**ASCII-only identifiers.** `Id` is `^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$`, which sidesteps Unicode confusables and normalisation ambiguity in a field used for cross-record references.

## Honesty about evidence

This is the most unusual quality of the PR and the easiest to erode. Consistently, throughout:

- `verification.md` separates "Observed Checks" from "Design Validation" from "Unresolved Release Risks", and states what did **not** run in the same breath as what did.
- `inventory-and-capabilities.md` distinguishes "Installed OrcaSlicer is *registered* as 2.4.2" from "the binary matches upstream", and records the EXE/DLL hashes rather than asserting a version. "Registry version is a claim, not proof."
- `acceptance.md` is labelled "future product tests unless A00 explicitly identifies a Phase 0 document check" — the specifications are not presented as passing.
- `check_design.py` prints what it did not check immediately after `PASS`.
- `policies.md` records that `main` is unprotected and that no protection was configured, rather than quietly enabling something.
- The PR body's "Validation Executed" section lists the negative space: "No live printer access, slicer process, provider request, real backup/restore, worker isolation test, product test or physical-quality validation occurred."

I verified the two claims I could check independently and both held: the prompt SHA-256 matches the documented value, and the `-text` gitattribute genuinely preserves the file byte-for-byte through the index (`git hash-object --no-filters` equals the index blob).

**Keep this.** It is the property that makes the rest of the design trustworthy, and it is the first thing that tends to decay once a project starts shipping features.

## Schema craft

- `unevaluatedProperties: false` rather than `additionalProperties: false` on every record type — the correct Draft 2020-12 idiom for schemas composed with `allOf`. Getting this wrong is the single most common Draft 2020-12 mistake.
- `Draft202012Validator.check_schema()` is called before the schema is used.
- Every array has `maxItems` and every string has `maxLength`, bounding memory amplification from a hostile document.
- `MaybeDigest` as a named type makes "pending or unavailable" explicit rather than relying on absent keys, and `data-contracts.md` states that "Each null means pending or unavailable, not a wildcard."
- The `Capture` `if`/`then`/`else` correctly ties `frame_time_ms` to whether `source_video_digest` is present — video frames must carry a timestamp, stills must not.
- `check_design.py`'s negative probes are real adversarial shapes (escaping paths, unverified backups claiming `verified`, matched Klipper activation with no runtime evidence), not just missing-required-field tests. My mutation test confirmed four of five safety rules are genuinely load-bearing in the checker.

## Process

The bootstrap-empty-`main` approach to get a reviewable diff, the explicit refusal to self-approve or enable auto-merge, the note that "a solo owner cannot supply an independent approving review on a PR authored as that same account", and the linked issue/milestone structure are all handled carefully. `policies.md` separating "repository PR review" from "experiment authorization" as different protocols — and saying so in three places — is the correct distinction and an easy one to get wrong.
