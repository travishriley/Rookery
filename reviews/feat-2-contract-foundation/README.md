# Code Review: `feat/2-contract-foundation` (PR #15)

Review of [PR #15 "B01a: offline contract envelopes and fixture CI"](https://github.com/travishriley/Rookery/pull/15).

| Field | Value |
| --- | --- |
| Reviewed branch | `feat/2-contract-foundation` |
| Reviewed commit | `c0f329cd7ad8a787d9b3dbe405fe80e4bb9f4004` |
| Base | `main` (`0079194`, the merged Phase 0) |
| Scope | 16 files, +733 / −8 |
| Review date | 2026-09-13 |
| Reviewer | Claude Opus 5 (automated review) |
| Verdict | **Approve with changes.** No blocking defect. 4 items are worth landing before B01b. |

## Contents

| File | Contents |
| --- | --- |
| [00-summary.md](00-summary.md) | Verdict, finding table, what to fix first |
| [01-safety.md](01-safety.md) | Design safety: the contract layer that will carry heater-relevant values |
| [02-security.md](02-security.md) | Code security: parser robustness, CI supply chain, workflow privilege |
| [03-usability.md](03-usability.md) | Contributor and end-user experience of the package and its tests |
| [04-maintainability.md](04-maintainability.md) | Code quality and best practice |
| [05-what-is-good.md](05-what-is-good.md) | What is right and should not be refactored away |
| [06-verification-log.md](06-verification-log.md) | Every command run, with raw output |
| [evidence/](evidence/) | Four re-runnable probe scripts backing each finding |

## How to reproduce

Every result in this review came from a clean virtual environment with the project wheel installed, matching what CI does.

```powershell
python -m venv .venv-review
.venv-review\Scripts\python -m pip install --only-binary=:all: -r requirements-dev.txt
.venv-review\Scripts\python -m pip wheel . --no-deps --no-build-isolation --no-index --wheel-dir dist
.venv-review\Scripts\python -m pip install --no-deps --no-index dist\rookery_core-0.1.0.dev1-py3-none-any.whl
.venv-review\Scripts\python reviews\feat-2-contract-foundation\evidence\probe_parser_robustness.py
.venv-review\Scripts\python reviews\feat-2-contract-foundation\evidence\probe_validation_cost.py
.venv-review\Scripts\python reviews\feat-2-contract-foundation\evidence\probe_schema_contract.py
.venv-review\Scripts\python reviews\feat-2-contract-foundation\evidence\probe_packaging.py
```

All four probes are read-only. None contacts a network, device, printer or model provider, and none writes to the repository.

## Review posture

This PR is the first one containing product code, so unlike the Phase 0 review this one could execute what it was reviewing. I built the wheel, installed it, ran the full suite, reproduced every number in the PR body, and then probed for failure modes the tests do not cover.

The PR's own claims held up under independent execution without exception — see [06-verification-log.md](06-verification-log.md). Findings are therefore not about accuracy of the description; they are about behaviour at the edges of the stated limits, and about the contract as it will be consumed by later milestones.

Nothing here asks B01a to do B01b's work. Where the PR already names something as a follow-up, I say so rather than re-raising it as new.
