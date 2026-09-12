# Code Review: `design/1-phase-0` (PR #14)

Review of [PR #14 "Phase 0: offline architecture, safety boundaries, and data contracts"](https://github.com/travishriley/Rookery/pull/14).

| Field | Value |
| --- | --- |
| Reviewed branch | `design/1-phase-0` |
| Reviewed commit | `5123a7db0f35e49827a5fa8141521404c63ec41f` |
| Base | `main` (`2aa42eb`) |
| Scope | 20 files, +1590 / -0 |
| Review date | 2026-09-12 |
| Reviewer | Claude Opus 5 (automated review) |
| Verdict | **Approve with changes.** No blocking defect. 4 safety/security items should land before B01. |

## Contents

| File | Contents |
| --- | --- |
| [00-summary.md](00-summary.md) | Verdict, finding table, what to fix first |
| [01-safety.md](01-safety.md) | Design safety: heater/motion-relevant gaps in the data contracts |
| [02-security.md](02-security.md) | Code security: model containment, path handling, parser strictness, privacy |
| [03-usability.md](03-usability.md) | End-user experience of the Phase 0 tooling |
| [04-maintainability.md](04-maintainability.md) | Code quality and best practice in `tools/check_design.py` and the schema |
| [05-what-is-good.md](05-what-is-good.md) | Things that are right and should not be refactored away |
| [06-verification-log.md](06-verification-log.md) | Every command run, with raw output |
| [evidence/](evidence/) | Re-runnable probe scripts backing each finding |

## How to reproduce

```powershell
git checkout review/design-1-phase-0
python -m pip install -r requirements-design.txt
python tools/check_design.py
python reviews/design-1-phase-0/evidence/probe_paths.py
python reviews/design-1-phase-0/evidence/probe_schema_gaps.py
python reviews/design-1-phase-0/evidence/probe_model_containment.py
python reviews/design-1-phase-0/evidence/mutation_test.py
```

`probe_paths.py` writes to a temporary directory and deletes it afterwards. `mutation_test.py` copies the repository to a temporary directory and never modifies the working tree.

## Review posture

This review takes the PR at its word about scope: it is a design proposal with no product implementation, and it says so repeatedly and accurately. Findings are therefore about **the contracts themselves** — whether the schema and the checker will hold up the safety properties the documents promise once B01–B06 start writing code against them. Nothing here asks Phase 0 to implement Phase 1.

Every finding was verified by execution on the reviewed commit. Claims I could not verify are marked as such.
