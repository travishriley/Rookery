# What Is Good

The first PR with product code is where a project's real habits show. These are the things I specifically tried to break, or checked carefully, and found right — recorded so they survive future refactors.

## <a id="robustness"></a>The parser genuinely does not break

I fuzzed `parse_record` with 4,030 inputs: null bytes, raw control characters, overlong UTF-8, truncated multibyte sequences, split surrogate pairs, UTF-16-encoded documents, a 500 KB key, 300-level nesting, `1E+999999999999999999`, JavaScript-isms (`+1`, `.5`, `0x10`), duplicate keys across nesting levels, non-object roots, and 4,000 seeded byte-level mutations of a valid record.

```
cases=4030  accepted=100  ContractError=3930  UNEXPECTED=0
```

**Not one input produced an exception other than the documented `ContractError`.** No escaped `RecursionError`, `UnicodeDecodeError`, `KeyError`, `OverflowError` or `decimal.InvalidOperation`. For an ingress boundary whose whole contract is "expect `ContractError`", that is the property that matters, and it is rare to get right on the first attempt.

Two design choices are doing the work. The `except ContractError: raise` clause ahead of the broad `(ValueError, ArithmeticError)` catch preserves specific codes raised from inside `json.loads` hooks. And `_check_tree` uses an explicit stack rather than recursion, so the routine that bounds nesting cannot itself overflow the stack.

## The `pull_request` / `pull_request_target` decision

`fixtures.yml:4` uses `pull_request`. This is the single most consequential line in the file. `pull_request_target` runs fork-authored code with a write-capable token and access to repository secrets, and it is the most common serious GitHub Actions vulnerability in the wild — usually introduced by someone trying to make a check work on fork PRs.

Combined with `permissions: contents: read`, SHA-pinned actions, `persist-credentials: false`, no secrets, hosted runners and 10-minute timeouts, the workflow's security posture is correct on every point that matters. Please do not relax any of these to make a future check work on forks; there are safer patterns.

## Pinning that is itself tested

`tests/test_workflow.py` asserts the action pins are 40 hex characters and match an expected map, that `persist-credentials` is `False`, that no `secrets.` expression appears in the raw file text, and that each job's key set is a subset of `{name, runs-on, timeout-minutes, strategy, steps}`.

That last one is the clever one: adding `container:`, `services:`, `env:` or `permissions:` to a job fails the test rather than passing silently. Most repositories pin actions and then never notice when someone unpins them.

Checking `secrets.` against the raw text rather than the parsed YAML is also right — it catches a secret in a comment or in a region the parser normalises away.

## The design-checker parity harness

`test_design_record_probes_also_exercise_the_product_parser` is the best idea in this PR. It monkey-patches `design.make_validator` with a shim that runs every one of the design checker's ~119 negative probes and ~26 positive shapes through **both** the reference validator and the real `parse_record`, asserting the verdicts agree.

That means the Phase 0 review's entire adversarial corpus — Windows device paths, trailing-dot aliasing, model containment, identity-evidence requirements, uniqueness — is now automatically enforced against the product parser, for free, forever. It also means schema and parser cannot drift apart silently. Two suites that would normally be independent are wired into one.

## Exactness where exactness will matter

- `0.10000000000000000000001` round-trips as a `Decimal`, not a float.
- `9007199254740993` (2⁵³ + 1) survives without binary64 rounding.
- `created_at` returns the original string, with the reason in a comment: *"Do not silently truncate fractional seconds to datetime's microseconds."*
- `1e309` and `1e-9999` are rejected as `number_out_of_range` rather than clamped to infinity or zero.
- The float conversion in `_decimal` is explicitly a magnitude check and never the stored value.

`data-contracts.md` requires `Decimal` comparison at safety bounds because *"float rounding at a safety bound is the failure mode that matters"*. This PR implements that at the point where the value enters the system, which is the only place it can be done without already having lost precision. A later `float()` somewhere would be a real defect; getting it right here means it never has to be retrofitted.

## The type-checker extension is narrow and correct

```python
def _is_integer(_checker, value):
    return (type(value) is int or
            isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value())
```

`type(value) is int` rather than `isinstance` correctly excludes `bool`, which subclasses `int` — the classic trap, avoided. The `Decimal` branch checks `is_finite()` before comparing to `to_integral_value()`, so a NaN could not slip through even if one could be constructed. `1.0` satisfies `"type": "integer"` as JSON Schema specifies, while `true` and `"1"` do not, and there is a test for each.

## Errors that say what failed without saying what was in the record

```
  unknown property   -> code='schema_unevaluatedProperties'  path=()
  bad id value       -> code='schema_pattern'  path=('id',)   value echoed: False
```

`ContractError` composes its message from the code and field path only, and `repr=False` on both dataclass fields means `repr(record)` discloses nothing. An unknown property reports the record root rather than putting the attacker-chosen key name into `path`, so a caller logging `error.path` cannot be induced to log arbitrary text.

H08 ranks private data reaching logs as High severity and `policies.md` requires logs to hold *"IDs/digests and redacted failure details, not credentials/full requests"*. Building that in at the first commit, with a test asserting it, is much cheaper than retrofitting redaction later.

## Tests that encode what the system deliberately does not do

`test_shape_acceptance_explicitly_does_not_enforce_semantic_policy` asserts that an inverted range (`minimum=300, maximum=10`) and duplicate-identity files **do** parse, and closes with:

```python
# These acceptance results are limitations, never backup/authorization verdicts.
```

Writing a test whose purpose is to pin down a limitation — and to stop someone later mistaking schema acceptance for policy approval — is unusual and exactly right for this project. It is the Phase 0 review's conclusion about runtime invariants, encoded as an executable assertion.

The same instinct shows in `test_unknown_properties_and_script_strings_are_inert_data`, which parses a record containing a URL while patching `socket.socket` and `subprocess.Popen` to raise on use.

## Continued honesty about scope

- Every CI run ends, including failed ones via `if: always()`, by printing what was *not* tested: *"No worker isolation, source import, backup/restore, policy authorization, slicer or physical printer test was executed."*
- The implementation doc records the failures as well as the successes: the first package-test run caught the newline bug; the first CI attempt failed YAML validation before any job ran; a first venv hit a pre-existing unrelated dependency conflict. None of this had to be written down.
- It refuses to create placeholder green checks: *"It deliberately does not create placeholder green `boundary-fixtures` or `restore-fixtures` checks before those implementations exist."* Creating those would make the required-checks list look complete while proving nothing, and the temptation to do it will grow.
- The workflow tests' own limitation is stated: *"They guard configuration regressions, not malicious changes to both a workflow and its tests."*

Every number in the PR body reproduced exactly under independent execution — 22 package tests, 9 design-tool tests, 230 references, 26 positive shapes, 119 negative probes, 33 links, clean `pip check`, and a wheel containing only the five expected files. Nothing was overstated.
