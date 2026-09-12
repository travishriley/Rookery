# Phase 0 Verification Record

Date: 2026-09-12. Status: checks are recorded below as executed; product tests remain acceptance specifications. No live printer, slicer process, profile, firmware service, device, or machine-control API was accessed.

## Observed Checks

- Workspace inventory and ancestor instructions inspected before edits; initially only the supplied prompt and no Git repository.
- GitHub repository identity, initial contents, issues and PRs read; repository confirmed empty/public with stable ID `1367605870`.
- Existing local installation metadata inspected: OrcaSlicer registered 2.4.2; executable and DLL hashed, no runtime launch. Python 3.13.7 and installed validator package versions read.
- Public upstream Orca plugin/host/audit/CLI and fixed `v2.4.2` source, Klipper macro/config/host-failure and Moonraker observation/control/upload/authentication documentation read. Installed CLI support remains untested.
- GitHub rulesets returned empty; host CLI branch-protection endpoint returned `404 Branch not protected`. No protection or required check was enabled or claimed.
- Connector issue creation/protection read returned 403. Sandbox GitHub CLI login failed; host CLI login succeeded and completed authorized GitHub writes. Git metadata writes required sandbox escalation and a command-scoped ownership exception. No credential was copied into the repository.

## Design Validation

Run `python -m pip install -r requirements-design.txt`, then `python tools/check_design.py` and `git diff --cached --check` from the repository. The checker requires Python 3.11 or newer and exits with that message on older interpreters, because `datetime.fromisoformat` only accepts a trailing `Z` from 3.11. It validates the Draft 2020-12 schema with installed jsonschema 4.25.1, all local schema references, eleven record examples plus constructed shape cases, malformed variants, local Markdown file links, and the unchanged supplied-prompt SHA-256. It rejects duplicate JSON keys/non-finite constants and explicitly validates the UTC date-time subset using Python's standard datetime parser because optional jsonschema format dependencies are not installed.

Executed successfully: 230 local schema references, 24 positive shapes (eleven requested records plus supplemental/conditional examples), 110 negative probes, 25 local Markdown file links, and the original prompt SHA-256. The first validation run caught an incorrectly sized placeholder digest in an example; it was corrected before the passing run. The checks include model response ownership and containment, candidate/baseline approval completeness, six-view labels, timestamp presence, path shape, source identity, backup receipt structure and matched-activation evidence shape, not the corresponding product policies.

Counts are produced by the probes themselves rather than declared, so they move when probes are added. The containment probes assert that a model response cannot escalate its own risk level, reach a Klipper domain, or attach a proposal to an abstaining outcome; a mutation run confirmed that deleting any of the six conditional safety rules from the schema now fails the checker. Path probes cover Windows reserved device names in mixed case, trailing dot and space aliasing, empty segments and directory references, in addition to traversal and absolute/UNC/stream escapes. The prompt SHA-256 is a drift tripwire rather than an integrity control: the expected value lives in the same tree as the file, so one commit can change both, and it detects accidental modification only.

`git diff --cached --check` passed for the complete 20-file design package. The staged prompt Git blob was compared with `git hash-object --no-filters` and matches the unchanged working bytes. A filename-only scan found no selected GitHub/API token or private-key patterns in publishable files; this limited pattern scan is not a comprehensive secret audit. Staged file inventory contains no private data, temporary publication payloads, binaries, workflow or application code. GitHub `main` was re-read and remains the empty bootstrap commit `2aa42eb48996bdc5dc7e814cf12e46713c7352c0`.

No CI workflow, product behavior test, independent backup/restore, worker isolation, actual slicer help/slicing, provider request or hardware-quality test has run. Synthetic receipts/approvals/results are examples only and do not claim that those operations occurred.

## Published Review

[PR #14](https://github.com/travishriley/Rookery/pull/14) links [issue #1](https://github.com/travishriley/Rookery/issues/1), from `design/1-phase-0` to `main`. Authenticated GitHub read-back confirmed OPEN, non-draft, unmerged, `auto_merge: null`, no review decision, and an empty check rollup. Its twenty changed filenames match the staged design package; temporary publication payloads remain ignored locally. The twelve implementation/deferred-risk issues and six phase milestones were created and linked in the backlog. No self-approval, merge, protection change, or Phase 1 implementation was performed.

## Unresolved Release Risks

Actual Orca CLI/plugin compatibility and worker boundary, unspecified printer/firmware identity and numeric policy, backup topology/encryption/key recovery, local human versus automation approval identity, source/runtime precedence, provider/privacy behavior, licensing, and repository review/protection configuration all require later evidence. They are tracked in [backlog.md](backlog.md) and [decisions.md](decisions.md). Phase 0 does not claim they are resolved by documents or schemas.
