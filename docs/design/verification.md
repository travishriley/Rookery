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

Run `python -m pip install -r requirements-design.txt`, then `python tools/check_design.py`, `python -m unittest discover -s tools -p test_check_design.py`, and `git diff main...HEAD --check` from the design branch. The last command checks committed PR changes on a clean checkout; use `git diff --check` and `git diff --cached --check` for local unstaged/staged edits. The checker requires Python 3.11 or newer and exits with that message on older interpreters, because `datetime.fromisoformat` only accepts a trailing `Z` from 3.11. It validates the Draft 2020-12 schema with installed jsonschema 4.25.1, all local schema references, eleven record examples plus constructed shape cases, malformed variants, local Markdown file links, and the unchanged supplied-prompt SHA-256. It rejects duplicate JSON keys/non-finite constants and explicitly validates the UTC date-time subset using Python's standard datetime parser because optional jsonschema format dependencies are not installed.

Executed successfully after the review follow-up: 230 local schema references, 26 positive shapes (eleven requested records plus supplemental/conditional examples), 117 negative probes, 25 local Markdown file links, and the original prompt SHA-256. The first validation run caught an incorrectly sized placeholder digest in an example; it was corrected before the passing run. The checks include model response ownership and containment, candidate/baseline approval completeness, six-view labels, timestamp presence, path shape, source identity, backup receipt structure and matched-activation evidence shape, not the corresponding product policies.

Counts are produced by the probes themselves rather than declared, so they move when probes are added. The containment probes assert that a model response cannot escalate its own risk level, reach a Klipper domain, or attach a proposal to an abstaining outcome; a mutation run confirmed that deleting any of the six conditional safety rules from the schema now fails the checker. Path probes cover Windows reserved device names in mixed case, trailing dot and space aliasing, empty segments and directory references, in addition to traversal and absolute/UNC/stream escapes. The prompt SHA-256 is a drift tripwire rather than an integrity control: the expected value lives in the same tree as the file, so one commit can change both, and it detects accidental modification only.

`git diff --cached --check` passed for the complete 20-file design package. The staged prompt Git blob was compared with `git hash-object --no-filters` and matches the unchanged working bytes. A filename-only scan found no selected GitHub/API token or private-key patterns in publishable files; this limited pattern scan is not a comprehensive secret audit. Staged file inventory contains no private data, temporary publication payloads, binaries, workflow or application code. GitHub `main` was re-read and remains the empty bootstrap commit `2aa42eb48996bdc5dc7e814cf12e46713c7352c0`.

No CI workflow, product behavior test, independent backup/restore, worker isolation, actual slicer help/slicing, provider request or hardware-quality test has run. Synthetic receipts/approvals/results are examples only and do not claim that those operations occurred.

## Initial Publication

[PR #14](https://github.com/travishriley/Rookery/pull/14) links [issue #1](https://github.com/travishriley/Rookery/issues/1), from `design/1-phase-0` to `main`. Authenticated GitHub read-back confirmed OPEN, non-draft, unmerged, `auto_merge: null`, no review decision, and an empty check rollup. Its twenty changed filenames match the staged design package; temporary publication payloads remain ignored locally. The twelve implementation/deferred-risk issues and six phase milestones were created and linked in the backlog. No self-approval, merge, protection change, or Phase 1 implementation was performed.

## Review Follow-up

The previous review pass had already supplied fixes and replies at `2b53adf` and `a705c44`; all nineteen inline threads were still marked unresolved when this follow-up began. Those changes were preserved and independently inspected. The remaining corrections are limited to design contracts, documentation and checker regression tests; the PR now includes one additional test file, for twenty-one files total.

| Comments | Verified disposition |
| --- | --- |
| S1 | Existing Windows device/alias exclusions retained; fixed acceptance of a final newline caused by regex `$` semantics and device names with spaces before an extension (`NUL .cfg`). Python and JavaScript probes reject these newline/device cases and accept ordinary relative paths, including spaces within filenames |
| S2 and invariant follow-up | Shared domain and exact key/unit match documented; inverted/duplicate ranges still require runtime enforcement. Reproduced that limit with schema-valid examples and expanded A08's required policy cases. No arbitrary unit vocabulary or hardware bounds invented |
| S3 | Non-null proposed value and type agreement retained; added string/boolean type probes so each of the three type conditionals is exercised. Large finite numbers still require hardware-specific policy bounds |
| S4, S6, M7 | Identity evidence, exact-duplicate array checks and proposal digest binding verified. Canonical-path and differing-object identifier uniqueness remain explicit runtime gates |
| S5, M1-M5 | Containment, real probe counts, validator factory, field-specific errors and distinct-change probes retained. Nine regression tests pass, including sixteen selected in-memory schema mutations that the checker must detect |
| M6 | Replaced incomplete Markdown regex handling with a pinned parser. Full/collapsed/shortcut references, images, autolinks and tables parse correctly; inline/indented/tilde/nested backtick code is excluded. Local target containment and encoded paths tested; external availability and fragments are not checked |
| S7-S8 | Existing private-file ignores verified with direct filename arguments, including uppercase JPG on this workspace. Prompt digest still matches and is described as an accidental-drift tripwire, not independent integrity protection |
| U1-U3 and scope note | Named error field/Python guard/dependency instructions retained; README now checks committed PR changes on a clean checkout, with staged/unstaged checks explained separately. The explicit design-only limitation remains in checker output |

The Moonraker query shapes and selected Klipper status fields were rechecked against public documentation; references and the `print_stats` estimate limitation are recorded in architecture. No endpoint, printer, slicer, device, or model was contacted. Runtime integration and Phase 1 implementation remain out of scope. Thread resolution records comment disposition only; final merge approval remains with the owner.

## Remaining Release Risks

Actual Orca CLI/plugin compatibility and worker boundary, unspecified printer/firmware identity and numeric policy, backup topology/encryption/key recovery, local human versus automation approval identity, source/runtime precedence, provider/privacy behavior, licensing, and repository review/protection configuration all require later evidence. They are tracked in [backlog.md](backlog.md) and [decisions.md](decisions.md). Phase 0 does not claim they are resolved by documents or schemas.
