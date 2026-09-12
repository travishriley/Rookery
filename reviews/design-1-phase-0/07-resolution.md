# Resolution

All 18 findings from the review are resolved or answered. Fixes landed on `design/1-phase-0` in `2b53adf` and `a705c44`; every inline comment on [PR #14](https://github.com/travishriley/Rookery/pull/14) has a threaded reply.

| # | Finding | Outcome |
| --- | --- | --- |
| [S1](01-safety.md#s1) | `Path` accepts device names and aliases | **Fixed in schema** — pattern rejects reserved basenames in any case, trailing dot/space at any segment boundary, empty segments, trailing slash. 22 reject + 5 accept probes |
| [S2](01-safety.md#s2) | `Range` cannot be bound to a `Change` | **Partially fixed** — `domain` added to `Range` via a shared `ChangeDomain` enum. `min <= max`, one-range-per-`(domain, parameter)` and unit agreement are **not schema-expressible** and are now normative runtime invariants in `data-contracts.md`. Units enum deferred to B06 |
| [S3](01-safety.md#s3) | `proposed_value` untyped | **Fixed in schema** — `NonNullScalar` plus paired `if`/`then` type agreement with `current_value`. `1e308` remains valid by design; bounding is the `Range` comparison's job, now required to use `Decimal` |
| [S4](01-safety.md#s4) | Klipper scope with no evidence | **Fixed in schema** — both Klipper scopes require identity evidence; `klipper_observed` additionally requires a hardware reference |
| [S5](02-security.md#s5) | Model containment unprobed | **Fixed in checker** — 6 containment probes added. Mutation run now fails for all 16 conditional safety rules |
| [S6](02-security.md#s6) | No uniqueness on `files` / `captures` | **Fixed in schema** — `uniqueItems` on both; `(root_id, path)` and `capture.id` uniqueness documented as runtime invariants |
| [S7](02-security.md#s7) | `.gitignore` misses evidence types | **Fixed** — location-independent patterns for captures, geometry and journal files |
| [S8](02-security.md#s8) | `PROMPT_HASH` overstated | **Fixed in docs** — `verification.md` states it is a drift tripwire, not an integrity control |
| [U1](03-usability.md#u1) | Errors never name the field | **Fixed** — `kind` dispatch plus `best_match`; failures report without a traceback |
| [U2](03-usability.md#u2) | Undeclared Python floor | **Fixed** — explicit 3.11 guard ahead of third-party imports; recorded in README and `verification.md` |
| [U3](03-usability.md#u3) | README omits dependency install | **Fixed** — install step added; `git diff --check` corrected to `--cached` |
| [M1](04-maintainability.md#m1) | Hardcoded probe counts | **Fixed** — counts produced by the probes; 24 positive / 110 negative |
| [M2](04-maintainability.md#m2) | Missing `format_checker` | **Fixed** — single `make_validator` factory |
| [M3](04-maintainability.md#m3) | Derived schemas keep `$id` | **Fixed** — `subschema()` drops the inherited `$id` |
| [M4](04-maintainability.md#m4) | Tautological comparison | **Fixed** — rewritten with the intent stated |
| [M5](04-maintainability.md#m5) | Mislabeled probe | **Fixed** — two distinct changes |
| [M6](04-maintainability.md#m6) | `check_links` scope | **Fixed** — whole-repo `rglob`, code fences stripped, reference-style links now fail loudly |
| [M7](04-maintainability.md#m7) | No proposal digest in bindings | **Fixed in schema** — `proposal_digest` added, required for candidate scopes, null for baseline |

## What changed in the verdict

Nothing. The review's verdict was **approve with changes** and no blocking defect; the changes have landed.

The one substantive correction to the review itself: [01-safety.md#s2](01-safety.md#s2) implied the `Range` invariants could be fixed in the schema. They cannot. `minimum <= maximum` and duplicate-range detection require comparing two values in one document, which JSON Schema has no operator for. This was caught during verification rather than assumed — an early probe run appeared to reject an inverted bound, but only because the probe omitted the newly required `domain` field. With `domain` supplied, `{"minimum": 300, "maximum": 10}` still validates. Those invariants now live in `data-contracts.md` with explicit failure behaviour.

## New-rule mutation testing

The ten schema rules added in response to this review were mutation-tested on the same basis as the original six. Two were initially unprotected and neither would have been caught by inspection:

- Reverting `proposed_value` to `Scalar` still passed, because the null probe was being caught by the new type-agreement rule rather than by the non-null rule. Isolating it needed a probe with `current_value: null`.
- Removing `domain` from `Range.required` still passed, because the example supplies it and nothing probed its absence.

Both now have probes. Current state: **0 of 16 conditional safety rules can be deleted without failing the checker.**

## Verified after the fixes

```console
$ python tools/check_design.py
PASS: Draft 2020-12 schema, 230 local references, 24 positive shapes, 110 negative probes, 60 local links, original prompt SHA-256
```

(The link count is 60 on this branch because the checker now scans these review notes too; it is 25 on `design/1-phase-0`.)

All four probe scripts under [evidence/](evidence/) were re-run against the fixed tree. `probe_paths.py` reports every previously-accepted path now rejected; `probe_schema_gaps.py` reports the S3/S4/S6 shapes rejected, with the S2 range invariants and the `ApprovalRecord` time ordering correctly still schema-valid as documented invariants; `probe_model_containment.py` reports all containment terms now present in the checker; `mutation_test.py` reports full coverage.

The prompt SHA-256 is unchanged at `1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e`.

## Still open, by design

Not defects — recorded so they are not mistaken for oversights:

- **Range and unit invariants are documented, not enforced.** B06 must implement and independently test them. `data-contracts.md` states the failure behaviour, including that an inverted bound must deny rather than widen.
- **Units remain free text** until B06 reviews a hardware-specific vocabulary. Inventing an enum now would be the kind of unfounded specificity the design set out to avoid.
- **`ApprovalRecord` time ordering** is a runtime invariant for the same reason as the range bounds.
- **The upstream Orca, Klipper and Moonraker citations were not re-read** in either round. The Moonraker operation allowlist still deserves a reviewer who knows that API.
- **No product behaviour, worker isolation, slicer runtime, backup destination or hardware test has run.** That was true before this review and remains true; nothing here changes what Phase 0 claims.
