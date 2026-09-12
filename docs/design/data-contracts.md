# Proposed Data Contracts

Status: draft `0.1.0`, JSON Schema Draft 2020-12. [rookery.schema.json](../../schemas/0.1.0/rookery.schema.json) defines the eleven requested record types and shared value types in `$defs`. There is deliberately no ApplyReceipt. [Synthetic examples](../../schemas/0.1.0/examples.json) are shape examples with placeholder digests and fictional actors; none is a real backup, approval, activation or experiment result.

## Typed Model Plan

Phase 1 introduces frozen Python models matching each schema name, strict parsing without coercion and typed enums/value objects. Use `str`-backed validated `Digest`/`RecordId`, timezone-aware `datetime`, immutable sequences, and `Decimal` for policy comparisons; avoid float rounding at safety bounds. Candidate numerical input must be finite. A later model library is not chosen or vendored by this design.

| Record / proposed Python class | Key fields | Cross-record/semantic validation (not supplied by JSON Schema) |
| --- | --- | --- |
| `PrinterIdentity` | ID, label, firmware enum, scope, declared hardware reference, identity evidence | Match intended physical identity; slicer-only cannot imply firmware validation; unknown identity blocks physical package approval |
| `SourceSnapshot` | Printer digest, original file entries, dependency edges, source digest, capture times, completeness, provenance | Hash bytes/closure, preserve order/includes/metadata, detect drift/escapes/duplicates; incomplete closure cannot pass backup gate |
| `BackupReceipt` | Snapshot/destination/domain, object version, full-fidelity flag, read-back and restore hashes, verification/failure data | Verify actual bytes and independent domain evidence; sanitized history never qualifies; cryptographic/object identity binding; receipt authenticity/freshness |
| `CalibrationDefinition` | Geometry/project/license/version/orientation/features, reviewed parameter ranges, metrics/floors, budgets and controls | Verify asset license and region diagnostic claims; ranges require hardware review; known model is not proof of safe testing |
| `ExperimentManifest` | State/revision, binding tuple, baseline/candidate runs, controls and frozen rubric, budgets | Enforce state guards, reference consistency, run identity, evidence/approval completeness and budget monotonicity |
| `EvidenceBundle` | Run identity, image/video/frame descriptors, six-view coverage assessment, measurements and capture issues | Hash assets; verify identity, view sufficiency and quality; video timestamps/derivation and calibration; schema cannot inspect pixels |
| `DiagnosticReport` | Provider/model, prompt/preprocessing hashes, outcome, observations, measurements, hypotheses, counterevidence and proposal ref | Validate evidence/regions, exact source values, bounds, provider privacy/capabilities and replay; interpretation is untrusted |
| `ChangeProposal` | Source/printer refs, one structured file/key/value change, rationale, validation, rollback, risk | Key/domain/unit/current-value/policy checks; elevated changes advisory only, never staged; no scripts/free-form edits |
| `ApprovalRecord` | Complete binding scope, actor/authentication, review evidence, expiry, rationale, revocation | Authenticate human/reviewer/checks; re-evaluate withdrawal/freshness/source drift; parsing is not authorization |
| `ActivationObservation` | Candidate/printer/base refs, actor/time, loaded/runtime evidence, firmware scope, verification status | Record actual human action independently; absent/stale/mismatched accessible runtime evidence blocks relevant interpretation |
| `ExperimentResult` | Binding scope, baseline/candidate metrics/repetitions, actual/estimated times, recommendation/rationale | Quality floors, controlled comparisons, frozen reviewer, failed outcomes and repeat proposal history; promotion never activates |

## Bound Values and Required Invariants

A reviewed `Range` is the only thing that bounds a proposed value, so how a range is matched to a change is itself a safety rule. `Range` and `Change` both carry the same `domain` enum. A range authorises a change only when `domain` is equal and `parameter` equals the change's `key` compared as **exact bytes, case-sensitively**. No normalisation, case folding, whitespace trimming, alias table, prefix or fuzzy match may be introduced; an unmatched key is denied, never approximated. `Range.units` must equal `Change.units` by the same comparison, and a change whose units differ from its governing range is denied rather than converted. Units are free text in v0.1.0 because no hardware-specific vocabulary has been reviewed; B06 replaces this with an enumerated unit set before any range is populated.

JSON Schema cannot compare two values in one document, so the following are normative runtime invariants that the typed model and policy must enforce and test independently. The Phase 0 checker does not verify them.

| Record | Invariant | Failure behaviour |
| --- | --- | --- |
| `CalibrationDefinition` | `minimum <= maximum` for every range | Reject the definition. A comparison must be written so that an inverted or unparseable bound denies, never `v >= minimum or v <= maximum` |
| `CalibrationDefinition` | At most one range per `(domain, parameter)` | Reject the definition; never merge, widen or prefer one silently |
| `ChangeProposal` | `current_value` and `proposed_value` are the same JSON type, except that a null `current_value` records a key absent from the source | Reject the proposal |
| `ChangeProposal` | `proposed_value` is finite and, for numeric parameters, within the governing range compared as `Decimal` | Reject the proposal; float comparison at a safety bound is not acceptable |
| `SourceSnapshot` | `(root_id, path)` is unique across `files` | Reject the snapshot as ambiguous; it cannot become a backup base |
| `EvidenceBundle` | `capture.id` is unique across `captures` | Reject the bundle; `Finding.capture_ids` must dereference exactly one capture |
| `ApprovalRecord` | `approved_at < expires_at`, and both are checked against the evaluation clock at export | Treat as expired |

`proposed_value` cannot be null. Deleting a key, or resetting one to an inherited value, is a different operation with different hardware consequences and is out of scope for v0.1.0; it requires its own reviewed operation type rather than an overloaded null. Schema-level type agreement is enforced where expressible, but the `Decimal` and range comparisons above are not, and remain the policy engine's responsibility.

## Hash and Identity Rules

`sha256:<64 lowercase hex>` identifies exact bytes. Original files, raw G-code, prompt bytes, images, video, extracted frames and provider output retain raw digests. Structured records are proposed to use RFC 8785 JSON canonicalization plus domain/type/version prefix before hashing; a vetted implementation and test vectors must be selected in B01 before any persistent product record is authoritative. Do not implement canonicalization with ordinary dictionary sorting and assume equivalence. Schemas validate digest shape only.

Records have `schema_version`, `kind`, immutable `id`, and UTC `created_at`. IDs are labels; references/authorizations use digests. A record digest is stored in the containing manifest/event, avoiding self-reference. `source_digest` in bindings/proposals and `snapshot_digest` in receipts both reference the complete SourceSnapshot record digest; SourceSnapshot's separate `content_manifest_digest` hashes its original-byte closure manifest, not itself. `proposal_digest` in bindings references the immutable ChangeProposal that a candidate came from, so the DiagnosticReport, proposal and approval chain is traceable by digest rather than only through the opaque `review_packet_digest`. It is null for a baseline package review, which has no proposal, and required wherever a candidate digest is required. Experiment revisions refer to separately hashed records, not to their own digest. Each baseline/candidate run ID must resolve through a journal event to an immutable manifest revision with that run's exact artifact/settings/identity bindings. Events bind preceding event and record digests; human Markdown reports are separately hashed views of the same machine data.

All external `$ref` fetching is disabled; schema references resolve locally. Unknown versions/kinds/properties and invalid date-times fail. The proposed UTC timestamp profile uses uppercase `T`/`Z`, seconds and optional fractional seconds; leap seconds and numeric timezone offsets are not accepted in v0.1.0. Duplicate JSON keys and non-finite numbers must fail in the parser before schema validation. New fields require a schema version; migrations produce new records with original links, never silently edit historical approved bytes.

Supplemental `$defs/ToolchainManifest` describes the object behind `toolchain_digest`: executable/binary hashes, version, OS/architecture, library/plugin/postprocessor manifests, recorded argv, complete resolved presets, geometry/placement, capability receipt and raw output. Recorded argv is evidence, never a command the model can ask the application to execute. Empty plugin/postprocessor manifests must be explicit hashed objects.

The model-facing `$defs/DiagnosticResponse` is distinct from the application-owned DiagnosticReport. It returns observations and an inline structured proposal (or null), not generated record IDs, timestamps, hashes of its own output, approval or toolchain metadata. The application hashes the raw provider response, validates supplied evidence/source references and policy, creates the immutable ChangeProposal, then wraps a DiagnosticReport with that proposal digest and trusted request provenance. This avoids asking a model to invent or self-hash records. No text in the response is executed. The versioned [diagnostic prompt](../../prompts/diagnostic-v0.1.0.md) is paired with this response schema; v0.1.0 caps proposals at one change even though future reviewed test designs may permit more.

## Completeness Versus Shape

Early manifests permit null candidate/artifact/toolchain/prompt/provider refs. Each null means pending or unavailable, not a wildcard. The [state machine](state-machine.md) requires the appropriate bindings before advancement. Approved candidate records require populated source, candidate, raw artifact, toolchain, calibration, effective settings, prompt/provider and evidence bindings; baseline review can precede diagnosis. Optional unknown material/environment observations need explicit `unknown` entries in the controls document and cannot be invented.

Schema-valid examples may still fail semantic policy: a claimed verified backup can be corrupt, three domain labels can name one disk, six image labels can depict one face, or an approval actor can be forged. Product gate tests must demonstrate those failures independently. The Phase 0 checker validates all eleven shapes and selected malformed variants; it does not implement these semantic checks.

## Proposed Journal and Index

SQLite tables: `records(digest, kind, schema_version, object_ref)`, `events(stream_id, sequence, previous_digest, payload_digest, actor_ref, created_at, operation_id)`, `experiment_heads(experiment_id, revision_digest, last_event_digest)`, `artifact_refs(owner_digest, target_digest)`, `destination_verifications(receipt_digest, policy_digest)`, and `approval_verdicts(approval_digest, evaluated_at, verdict, facts_digest)`. Unique stream sequence/operation IDs prevent replay races. Hashes/foreign keys and publish journaling enforce object existence. Append-only history is a policy plus integrity checks with external checkpoints, not database tamper-proofing.

Private storage schema migrations, canonical byte encoding, encryption/key references, signature/authentication envelopes, retention and garbage collection transactions must be designed in the relevant implementation issue before private data persists. No live-file transaction schema is in scope.
