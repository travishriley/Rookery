# Requirements and Traceability

Status: proposed derived specification; the [supplied prompt](../../ROOKERY_ASTRA_BUILD_PROMPT.md) remains authoritative. All requirements below are normative design targets, not implemented controls. Acceptance IDs refer to [acceptance.md](acceptance.md); backlog IDs to [backlog.md](backlog.md).

## Scope

Phase 0 delivers design, schemas, tracking, and acceptance specifications only. First useful release (Phases 1-2): read-only inventory, verified lossless backups, one calibration evidence bundle, one bounded reviewed offline candidate, and a comparison report. Typed Python CLI/core is the starting architecture. No AI or live device is required for Phase 1.

| ID | Requirement | Prompt section | Acceptance | Backlog |
| --- | --- | --- | --- | --- |
| R01 | No start/enqueue/resume/remote print, arbitrary G-code, heaters/motors/fans/pins, homing/probing/extrusion, macros, PID/resonance, SAVE_CONFIG, restart, or power control through app/model/plugin/CI | 2.1, 2.4-6 | A01, A02 | B02, B09 |
| R02 | No printer upload or live source writer; local staging/export only; humans independently import/activate/start every physical run | 1, 2.2, 2.7-8 | A01, A09, A13 | B06, B08 |
| R03 | Review raw generated artifact, calibration bounds, start/end sequences, reachable macros, and effective settings; unknown behavior cannot pass | 2.3, 2.9 | A08, A19 | B06 |
| R04 | Model/slicer workers cannot reach printer networks, devices, sockets, live roots, shell tools, or approval credentials; no execution of repository/config/model instructions | 2.4-6, 6-8 | A01, A02, A07 | B02, B05, B06 |
| R05 | Protected hardware/macro changes audit/proposal-only; no weakening thermal/motion safeguards; stop-only subsystem excluded from MVP | 2.9-10 | A08, A20 | B06, B12 |
| R06 | Preserve originals and resolve Orca printer/filament/process inheritance/project overrides and Klipper includes/saved state with provenance; missing/cyclic/ambiguous/escaping content fails closed | 1, 4, 6, 9 | A03, A04 | B02, B03 |
| R07 | Backup policy verified before any modified candidate bytes; recheck sources before approval/export; independent destinations, read-back, temporary restore, retention and key recovery | 9 | A04, A05, A06, A09 | B04 |
| R08 | Explicit immutable experiment state machine with first-class failures, no-change, manual checkpoints, budgets, and restart-free recovery | 5-6 | A06, A12, A13, A17 | B05 |
| R09 | Versioned typed records bind identity, base/candidate/raw G-code, toolchain/geometry/settings, evidence/policy/prompt/provider, and approval scope | 5, 6, 10 | A09, A10, A14 | B01, B05 |
| R10 | Six labeled views; video coverage/frame provenance; blur/glare/occlusion/identity checks; calibrated/manual measurements; evidence limits and non-config causes explicit | 7 | A10, A11, A18 | B05 |
| R11 | Advisory model returns structured limited outcomes with image/region references; strict schema and deterministic policy; replay and capability errors; no hidden remote fallback | 7-8 | A07, A11, A12, A14 | B05, B07 |
| R12 | Cloud data/provider-specific opt-in, preview/redaction, credential storage, budgets, durable private evidence; public history sanitized separately | 3, 7, 9 | A07, A15 | B04, B07 |
| R13 | Approval authenticated and bound to exact reviewed content, scope, actor/time/rationale; invalidate on drift, stale evidence, changed policy, revocation; never infer from merge/label | 10 | A09, A16 | B06, B08 |
| R14 | Baseline before optimization; one independent variable initially; metric floors/tolerances, material/time/run limits and stop conditions predefined; replicated comparisons with controls and model frozen | 6 | A12, A18 | B05, B06 |
| R15 | Preserve failed/rejected runs; equivalent repeat proposals flagged, retest justified; distinguish estimated/actual time, software determinism/physical variation/model variability | 6 | A14, A18 | B06 |
| R16 | Verified capability/version-specific Orca adapter with file fallback; optional read-only plugin not a sandbox; no assumed headless calibration generation | 4, 11 | A19 | B06, B09 |
| R17 | Local explicit approval and GitHub first; GitLab later; thin UI/plugin uses core policy; software PR review is separate from experiment authorization | 3-4, 10 | A16 | B08, B09 |
| R18 | Issues/milestones, issue branches and human-reviewed PRs; fixture-only CI with least privilege and immutable Actions; verify actual branch protections | 3, 13 | A00, A20 | B01 |
| R19 | Existing licensed calibration first; original parametric rook artifact/feature manifest and evaluation corpus later; do not claim universal calibration or untested time/quality | 6, 11 | A18, A19 | B10, B11 |
| R20 | No future ApplyReceipt/live deployment/stop-only monitor until separate design and human authorization; may remain excluded | 2, 5, 12 | A20 | B12 |

## Product Behavior

A source-only audit may run before a fresh backup. It returns findings and an optional structured proposal, never modified candidate files. An unsafe baseline stops preparation for physical testing. A complete machine-independent parser result is not a hardware safety determination.

The first bounded experiment is provisionally a human-exported Orca flow-ratio project, contingent on license, capability, and hardware review. There are no default temperature, speed, flow, acceleration, or other hardware ranges in this design. An empty parameter allowlist denies all candidate changes until a human-approved hardware-specific policy exists. Macro/hardware-critical findings stay advisory even if someone requests export.

Every comparison retains setup controls (nozzle, surface, filament/spool/batch/drying, ambient/chamber observations, maintenance, manual interventions), independent quality metrics and floors, intended repetitions, raw failures, actual elapsed times where supplied, and uncertainty. Unknown values are explicit, never invented. Policy determines which missing controls block interpretation.

## Non-Goals

No printer control, deployment, restart/rollback activation, automatic upload, automatic optimizer, novel CAD, cloud service, consumer-login automation, or safety certification. No slicer fork and no model embedded in Klipper. Phase 0 does not install/upgrade Orca or change profiles, repository protection settings, or CI settings.

## Reversible Assumptions

Use a single-user Windows CLI initially, a typed Python core, SQLite plus a content store, synthetic fixtures, and replay diagnosis. Add Linux support only when independently tested; Windows paths and reparse points are first-class risks. Pin product dependencies and runtime support in B01 after compatibility review. Human backup destinations, printer identity, numeric ranges, reviewer identities, model privacy settings, and any actual print results remain unknown and do not block design.
