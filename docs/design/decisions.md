# Architecture Decisions

All ADRs are proposed for human review. Changes are reversible until implementation or private data migration; this design PR approval does not approve a printer experiment.

| ADR | Decision and rationale | Tradeoff / reversal trigger |
| --- | --- | --- |
| ADR-001 | Independent typed Python core, CLI, SQLite journal and filesystem SHA-256 store; one local application | Windows/Python 3.13.7 is observed, not final support matrix. Confirm OS/runtime and parser dependencies in B01; no distributed services |
| ADR-002 | File import/export first; separate Orca and firmware adapters | Installed Orca is registered 2.4.2; no supported plugin dependency established. Add a thin optional read/export/UI plugin only after compatible build testing |
| ADR-003 | No printer control/upload/live writer; workers denied network/devices/live roots by OS boundary | More manual work. Future read-only gateway requires its own proven boundary; Phase 5 needs a new design and may be abandoned |
| ADR-004 | Immutable artifacts and digest-bound event/approval records; mutable DB is only an index | More storage and explicit migrations. Canonical JSON algorithm and test vectors must be pinned before product records become durable |
| ADR-005 | Three independently verified full-fidelity copies with at least one off-device before candidate mutation | Conservative burden for a solo owner. Owner can explicitly review a different policy with disclosed risk; never automatic fallback. No real backup topology chosen |
| ADR-006 | One independent variable; empty change allowlist until hardware-specific policy review; protected edits advisory only | Reduces optimization breadth. Wider experiment design requires controlled evaluation and reviewed bounds |
| ADR-007 | Replay provider/local-only first; multi-view evidence plus manual/calibrated measures; frozen reviewer within comparison | Delays live provider integration, enables repeatable testing and privacy. Providers added only after capability/privacy evaluation |
| ADR-008 | Local explicit human approval first; separate broker identity; GitHub experiment approval later | Authentication must distinguish automation from human. Solo GitHub software reviews need collaborator/account decision; no self-approval |
| ADR-009 | Baseline package review, candidate export authorization, activation observation and each manual run are distinct | Additional records/checkpoints, necessary to avoid treating a merge or file write as physical evidence |
| ADR-010 | Existing human-exported calibration project before original CAD | Exact project/license unresolved. Original rook/feature manifest and corpus deferred to Phase 4; no printed quality/time claims |

## Decisions Requiring Owner Review

1. Accept file-first integration and the typed Python/Windows-first CLI approach; the installed Orca runtime probe stays pending isolation.
2. Accept the three-copy backup default and proposed retention/key-recovery approach; select actual independent destinations only before candidate staging.
3. Review OS-enforced worker isolation and separate local human approval identity as release gates, including unsupported-deployment behavior.
4. Choose a software PR reviewer/account arrangement and enable supported protections after checks exist. Current rules are not enforced.
5. Confirm first experiment category, project/license and machine-specific bounds before Phase 2 physical-package use; design currently authorizes no parameter values.
6. Select project license and evaluate dependency/asset provenance before distributing code or third-party calibration objects. Working name is unvetted.

These are review items, not blocking questions for Phase 0. Printer identity, firmware version, hardware ranges, private evidence, provider choice and credentials remain unset. No live discovery is needed to approve the offline Phase 1 milestone.
