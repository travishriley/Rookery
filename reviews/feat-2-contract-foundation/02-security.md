# Code Security

Two surfaces: the parser (untrusted input) and the CI workflow (untrusted pull requests). Both are built correctly on the points that matter most. The parser survived 4,030 adversarial inputs without a single unhandled exception, and the workflow gets the one decision right that most repositories get wrong — `pull_request`, not `pull_request_target`.

Findings are about supply chain and about one API-shape choice.

---

## <a id="s1"></a>S1 — Medium — CI installs unhashed dependencies on every run

**Location:** `.github/workflows/fixtures.yml:30`, `:53`

```yaml
- run: |
    python -m pip install --only-binary=:all: -r requirements-design.txt
```

`requirements-design.txt` and `requirements-dev.txt` pin exact versions with `==` but carry no hashes, and there is no `--require-hashes`. Every CI run resolves those pins against live PyPI and installs whatever is served.

**To be clear about what is already right here.** `--only-binary=:all:` is a genuinely good control and not a common one — it refuses source distributions, so no `setup.py` from a dependency executes arbitrary code at install time. The wheel build uses `--no-build-isolation --no-index`, so it does not reach the network at all. Version pinning is exact rather than floating. The implementation doc names the remaining gap explicitly: *"Version pins are not artifact-hash locks; dependency hash locking and a release vulnerability review remain B01 follow-ups."*

So this is a confirmation of an acknowledged item rather than a new finding. I am raising it because the concrete exposure is worth stating so it gets prioritised correctly rather than deferred as paperwork:

- `--only-binary=:all:` stops code execution *at install time*. It does not stop a hijacked wheel from being installed and then **imported** — which `tools/check_design.py` and both test suites do, on every run, as the first thing they do.
- The threat model ranks this Critical. H15 reads *"Dependency or PR executes with printer secrets/network or changes policy/approval logic"*, and its stated control is *"pinned Actions; reviewed dependency provenance"*. Actions are pinned to SHAs; Python dependencies are pinned only to versions.
- The asymmetry is visible in the same file: `actions/checkout` is pinned to `3d3c42e5aac5ba805825da76410c181273ba90b1`, an immutable content identifier. `jsonschema==4.25.1` is a mutable name. Both are third-party code running in the same job.

Today the blast radius is small: `contents: read`, no secrets, no printer access, hosted runners. That is why this is Medium and not High. It grows the moment any job gains a credential.

**Suggested fix.** `pip` already supports this and the change is mechanical:

```powershell
python -m pip install --only-binary=:all: --require-hashes -r requirements-design.txt
```

once the requirements files carry `--hash=sha256:...` lines. Generating them needs a resolver run (`pip-compile --generate-hashes`, or `pip download` plus `pip hash`), which is why it is reasonably a follow-up rather than in-scope here. Note that `--require-hashes` forces *every* requirement to be hashed including transitives, which `requirements-design.txt` already lists — so the file is close to ready.

**Related, smaller:** `python-version: '3.13.7'` and the runner images (`ubuntu-24.04`, `windows-2025`) are mutable labels too. The implementation doc already says so — *"Hosted images are versioned labels, not immutable OS image digests"* — which is the right level of honesty. No action; noted so the hash-locking work is scoped to what it can actually cover.

---

## <a id="s2"></a>S2 — Low — `cancel-in-progress` also applies to pushes to `main`

**Location:** `.github/workflows/fixtures.yml:11-13`

```yaml
concurrency:
  group: fixtures-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

For pull requests this is correct and desirable — `github.ref` is `refs/pull/N/merge`, so each PR has its own group and superseded runs are cancelled.

For `push: branches: [main]` the group is `refs/heads/main` for every push. Two commits landing close together cancel the first run, and the earlier commit ends with a cancelled check rather than a completed one. The implementation doc recommends these become required checks:

> Recommended eventual required checks are `design-contracts`, `unit-fixtures (ubuntu-24.04)` and `unit-fixtures (windows-2025)`

A commit on `main` with no completed check is a hole in exactly the record those required checks exist to create — and `main` is the branch whose history the project treats as authoritative.

**Suggested fix:**

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

The literal `fixtures-` prefix is also redundant with `${{ github.workflow }}` and can go at the same time.

---

## <a id="s3"></a>S3 — Low — `ContractError` subclasses `ValueError`

**Location:** `src/rookery/contracts.py:48`

```python
class ContractError(ValueError):
    """Stable error code and field location, without echoing input values."""
```

`ValueError` is one of the most commonly caught builtins. A caller writing a broad `except ValueError` for unrelated reasons — around an `int()` conversion, a `Decimal()` construction, a `datetime.fromisoformat()` — silently swallows a fail-closed boundary rejection and continues as though nothing happened.

That matters more here than in ordinary code because the entire value of this module is that it fails closed and the caller notices. The docstring for `Record` is explicit that parsing *"is not an authenticated approval or verified operation"*; a swallowed `ContractError` inverts that from "did not validate" to "no error occurred".

There is a real argument on the other side: `ValueError` is the conventional base for "well-formed call, bad value", and inheriting from it means naive callers get sensible behaviour from generic error handling. `json.JSONDecodeError` makes the same choice. So this is a judgement call rather than a defect, and I would not push hard on it.

If it stays, it is worth one line in `b01-contract-foundation.md` warning integrators not to catch bare `ValueError` around `parse_record`. If it changes, deriving from `Exception` directly — or keeping `ValueError` but adding a distinct sentinel base that callers are told to catch — makes the boundary explicit before B02 starts calling this from an importer.

---

## What I checked and found correct

### <a id="robustness"></a>The parser does not break

I fuzzed `parse_record` with 4,030 inputs: hand-built structural and encoding edges (null bytes, raw control characters, overlong UTF-8, truncated multibyte sequences, split surrogate pairs, UTF-16 input, 500 KB keys, 300-level nesting, `1E+999999999999999999`, `+1`, `.5`, `0x10`, duplicate keys across nesting levels, non-object roots) plus 4,000 seeded byte-level mutations of a valid record.

```
cases=4030  accepted=100  ContractError=3930  UNEXPECTED=0
```

**Zero inputs produced an exception other than `ContractError`.** No `RecursionError` escaped, no `UnicodeDecodeError`, no `KeyError`, no `TypeError`, no `OverflowError`, no `decimal.InvalidOperation`. For an ingress boundary whose entire contract is "expect `ContractError`", that is the property that matters, and it holds. The exception ordering in `_decode` (re-raising `ContractError` before the broad `(ValueError, ArithmeticError)` catch) is what makes it work, and it is correct.

### The workflow gets the important decisions right

- **`pull_request`, not `pull_request_target`.** This is the single most consequential choice in the file. `pull_request_target` would run fork-authored code with a write-capable token and repository secrets. Getting this wrong is the most common serious GitHub Actions vulnerability; getting it right deserves explicit credit.
- **`permissions: contents: read`** at workflow level, so every job inherits least privilege.
- **Actions pinned to full 40-character commit SHAs**, with version comments, and a test (`test_only_reviewed_immutable_actions_without_persisted_credentials`) that asserts the pins are 40 hex characters and match an expected map. Pinning that is itself tested is unusual and good.
- **`persist-credentials: false`** on both checkouts, asserted by the same test, so the job's token is not left in `.git/config` for subsequent steps.
- **No `secrets.` expression anywhere**, asserted by a test on the raw file text rather than the parsed YAML — which is the right way to check, since it catches a secret in a comment or an unparsed region.
- **Hosted runners only**, `timeout-minutes: 10` on every job, and a test asserting each job's key set is a subset of `{name, runs-on, timeout-minutes, strategy, steps}` — so adding `container:`, `services:` or `env:` fails the test rather than passing silently.
- **The workflow is only self-testing, and the doc says so.** *"They guard configuration regressions, not malicious changes to both a workflow and its tests."* That limitation is real and correctly stated rather than glossed.
- **`pip check` after a `--no-deps` wheel install** is a neat way to confirm the `pyproject.toml` pins actually match what `requirements-dev.txt` installed, rather than asserting it in a comment.

### Error messages do not leak record content

Verified directly:

```
  unknown property   -> code='schema_unevaluatedProperties'  path=()
                        str='schema_unevaluatedProperties: (record root)'
  bad id value       -> code='schema_pattern'  path=('id',)
                        value echoed: False
```

`ContractError` builds its message from the code and the field path only. Notably, an unknown property does **not** put the attacker-chosen property name into `path` — it reports the record root. So a caller logging `error.path` cannot be induced to log arbitrary attacker text through a key name. `Record` also sets `repr=False` on both fields, so `repr(record)` discloses nothing. `test_validation_errors_do_not_echo_private_values` covers this and it passes.

Given H08 ranks private-data leakage into logs as High severity, and `policies.md` requires that logs record *"IDs/digests and redacted failure details, not credentials/full requests"*, this is the right behaviour built in at the start rather than retrofitted.

### The wheel contains only what it should

```
rookery/__init__.py                          219
rookery/contracts.py                       7,564
rookery/py.typed                               1
rookery/schemas/0.1.0/rookery.schema.json 29,695
rookery/schemas/__init__.py                   85
rookery_core-0.1.0.dev1.dist-info/...
```

No build prompt, no fixtures, no examples, no tests, no private data — matching the doc's claim. `include-package-data = false` with explicit `package-data` is the right way to get that guarantee rather than relying on defaults.

### No secrets in the diff

I swept the full PR diff for credential patterns. The only hits are prose about JSON number *tokens* and the workflow's own description of not using secrets.
