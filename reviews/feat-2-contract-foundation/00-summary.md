# Summary and Verdict

**Approve with changes.** This is high-quality work. The parser is genuinely robust — I fuzzed it with 4,030 adversarial and mutated inputs and it never once raised anything other than the documented `ContractError`. The CI workflow is built correctly on the points that actually matter for a repository that will later touch hardware. Every claim in the PR body reproduced exactly under independent execution.

I found no blocking defect. The findings below are about behaviour at the edges of the stated limits, and about the schema now being a *shipped artifact* rather than an internal document.

## Findings

| # | Severity | Area | Finding | Location |
| --- | --- | --- | --- | --- |
| [A1](01-safety.md#a1) | Medium | Safety | `Time` has no usable pattern, so `created_at` / `approved_at` / `expires_at` accept `"garbageZ"` for any consumer that does not enable format assertion — in a schema this PR packages for exactly that use | `rookery.schema.json:26` |
| [A2](01-safety.md#a2) | Medium | Safety | The documented limits bound input size but not validation cost: a record satisfying every limit takes **4.8 s**, 40× an equivalent record without `uniqueItems` on objects | `contracts.py:26-29` |
| [A3](01-safety.md#a3) | Low | Safety | `files.maxItems: 10000` is unreachable — `MAX_NODES` caps the array at ~3,846 entries, so the schema states a bound that can never apply | `rookery.schema.json`, `contracts.py:28` |
| [S1](02-security.md#s1) | Medium | Security | CI installs unhashed dependencies from PyPI on every run; `--only-binary=:all:` blocks sdist execution but a hijacked wheel for a pinned version is still installed and imported | `fixtures.yml:30,53` |
| [S2](02-security.md#s2) | Low | Security | `cancel-in-progress: true` also applies to `push: main`, so a rapid second push can leave a main commit with no completed check | `fixtures.yml:11-13` |
| [S3](02-security.md#s3) | Low | Security | `ContractError` subclasses `ValueError`, so a caller's unrelated `except ValueError` silently swallows a fail-closed boundary error | `contracts.py:48` |
| [U1](03-usability.md#u1) | Medium | Usability | `pip install -e .` fails the suite with a bare `AssertionError: True is not false` and no explanation; the package itself works fine | `test_contracts.py:89` |
| [U2](03-usability.md#u2) | Low | Usability | The wheel filename is hardcoded in CI and the README, so bumping `version` silently breaks both | `fixtures.yml:55`, `README.md` |
| [U3](03-usability.md#u3) | Low | Usability | Wheel metadata has no License, Classifier, readme or Project-URL — 359 bytes of METADATA | `pyproject.toml` |
| [M1](04-maintainability.md#m1) | Low | Maint. | Error codes are `f"schema_{failure.validator}"`, coupling a documented-stable API to JSON Schema keyword names and `best_match` heuristics; no test pins any `schema_*` code | `contracts.py:204` |
| [M2](04-maintainability.md#m2) | Low | Maint. | `__hash__ = None` depends on a documented-as-heuristic dataclass behaviour and has no comment explaining it is deliberate | `contracts.py:190` |
| [M3](04-maintainability.md#m3) | Low | Maint. | `tools` and `tests` are implicit namespace packages, so the suite only imports correctly when the working directory is the repository root | `test_contracts.py:18` |

## What to fix first

1. **A1** — one line. The schema is now published as `rookery.schemas` specifically so other implementations can treat it as authoritative, and `format` is annotation-only by default in JSON Schema. This PR already fixed the identical class of bug for `Digest` and `Id`; `Time` is the one that was missed.
2. **A2** — this is the moment the limits are being chosen, and B02 is the milestone that will feed this parser untrusted imported files. Cheaper to set the bound correctly now than to discover it under a real import.
3. **U1** — one line (add a message to the assertion). It decides whether the next contributor's first hour is productive.
4. **S1** — already named as a B01 follow-up in the implementation doc, so this is a confirmation rather than a new finding. Worth stating the concrete exposure so it is prioritised correctly.

A3, S2, S3, U2, U3 and all M-items are cleanup; batch them whenever convenient.

## Two notes on scope

**The schema changed status in this PR, and that raises the bar for it.** In Phase 0 `rookery.schema.json` was a design document read by one checker that always enabled format assertion. This PR packages it into a wheel as the authoritative contract, and the implementation doc says tests "compare the installed resource byte-for-byte with the source". That is the right design — but it means every weakness in the schema is now exported to consumers who will not necessarily replicate `contracts.py`'s validator configuration. A1 is the concrete instance; the general point is worth holding onto for B01b.

**The limits are the safety story at this layer.** There is no printer path in this PR at all — no network client, no subprocess, no file open, no writer. I checked. So "design safety" here means: does the ingress boundary hold when fed hostile input, and are the bounds it advertises the bounds it actually has? The first answer is an emphatic yes ([05-what-is-good.md](05-what-is-good.md)). The second is where A2 and A3 sit.
