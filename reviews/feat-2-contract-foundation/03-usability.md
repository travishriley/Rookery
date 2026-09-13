# Usability

Two audiences at this stage:

1. **The contributor** — someone cloning the repo to work on B01b. Their experience is the README's install block and `python -m unittest discover -s tests`.
2. **The integrator** — whoever calls `parse_record` from B02's importer. Their experience is the `Record` API and `ContractError`.

The integrator is served well. The API is one function taking `bytes`, the envelope exposes exactly four typed accessors plus an immutable `data` mapping, and the failure mode is a single exception type with a code and a field path. The README's usage snippet is four lines and includes the comment `# supplied_bytes is an explicitly provided synthetic JSON record, not a path` — which teaches the security property at the point of use rather than in a document nobody opens.

The contributor hits one sharp edge.

---

## <a id="u1"></a>U1 — Medium — `pip install -e .` fails the suite with no explanation

**Location:** `tests/test_contracts.py:89`

```python
# Exercise a real wheel install, not an accidentally importable source tree.
self.assertFalse(Path(contracts.__file__).resolve().is_relative_to(ROOT / "src"))
```

The intent is right and worth keeping: the doc says *"Tests run from an installed wheel, not an editable/source-path import"*, and this guard is what makes that true rather than aspirational. Without it, a stray `sys.path` entry would let the suite pass while never exercising `importlib.resources` against real package data — which is the specific thing `test_packaged_schema_is_the_authoritative_schema` exists to check.

The problem is what a contributor sees when they follow their instincts. Verified in a clean venv with `pip install -e .`:

```
FAIL: test_packaged_schema_is_the_authoritative_schema
  File "...\tests\test_contracts.py", line 89, in test_packaged_schema_is_the_authoritative_schema
    self.assertFalse(Path(contracts.__file__).resolve().is_relative_to(ROOT / "src"))
AssertionError: True is not false

Ran 22 tests in 0.654s
FAILED (failures=1)
```

`AssertionError: True is not false` says nothing about the cause. The package itself works perfectly under the editable install — I confirmed `parse_record` parses a record and resolves the bundled schema correctly — so nothing is actually broken, and the contributor has no way to tell that from the output. The natural next moves (re-read the assertion, check `ROOT`, suspect `importlib.resources`) all lead away from the answer.

Editable install is the default instinct for a `src/` layout, and nothing in the README warns against it. The README gives the wheel commands but does not say *"and don't use `-e`, the suite will fail"*.

**Suggested fix** — one line, no behaviour change:

```python
self.assertFalse(
    Path(contracts.__file__).resolve().is_relative_to(ROOT / "src"),
    "rookery is imported from the source tree. These tests must run against an "
    "installed wheel so that packaged-resource lookup is genuinely exercised; "
    "`pip install -e .` will not work. See README 'Contract Foundation'.",
)
```

Worth pairing with a sentence in the README's install block, since the error only appears after someone has already gone the wrong way.

---

## <a id="u2"></a>U2 — Low — the wheel filename is hardcoded in two places

**Location:** `.github/workflows/fixtures.yml:55`, `README.md`

```yaml
- run: python -m pip install --no-deps --no-index dist/rookery_core-0.1.0.dev1-py3-none-any.whl
```

Verified both literals track the declared version today:

```
  pyproject version              : 0.1.0.dev1
  workflow references that wheel : True
  README references that wheel   : True
    workflow: hardcoded -> rookery_core-0.1.0.dev1-py3-none-any.whl
    README:   hardcoded -> rookery_core-0.1.0.dev1-py3-none-any.whl
```

Bumping `version` in `pyproject.toml` — which B01b will do — breaks CI and the documented install command simultaneously, and the CI failure is a `pip` "file not found" several steps after the real cause. Three files must change together with nothing enforcing it.

**Suggested fix** — resolve by name rather than filename, which is version-agnostic and works identically in both places:

```powershell
python -m pip install --no-deps --no-index --find-links dist rookery-core
```

If the exact-artifact semantics of naming the file are wanted, a test asserting that the version in `pyproject.toml` appears in both the workflow and the README would at least make the coupling fail loudly. `tests/test_workflow.py` is already the natural home — it reads both the raw workflow text and `pyproject.toml` machinery is already present in `test_contracts.py` via `tomllib`.

---

## <a id="u3"></a>U3 — Low — the wheel is nearly undescribed

**Location:** `pyproject.toml`

Installed metadata, in full:

```
  Name                      : rookery-core
  Version                   : 0.1.0.dev1
  Requires-Python           : <3.14,>=3.13
  License                   : (absent)
  License-Expression        : (absent)
  Description-Content-Type  : (absent)
  Classifier                : (absent)
  Author                    : (absent)
  Project-URL               : (absent)
```

359 bytes of METADATA. The license absence is a deliberate open decision — the README and the implementation doc both say so, and inventing one would be worse. No argument there, and no publish workflow exists, so nothing leaves the machine.

The rest is free and makes the artifact self-describing if it is ever handed to anyone:

```toml
readme = "README.md"
[project.urls]
Repository = "https://github.com/travishriley/Rookery"
```

A wheel with no license metadata is genuinely awkward to receive — a recipient cannot tell whether they may use it, and "no license" defaults to all rights reserved rather than to permissive. Worth noting in `b01-contract-foundation.md` alongside the existing licensing paragraph that the wheel currently carries no license field, so that whenever the owner does select one, updating package metadata is on the same checklist.

---

## Smaller observations

**The README's two install blocks could be confused.** "Contract Foundation" installs `requirements-dev.txt` and builds a wheel; "Design Checks" installs `requirements-design.txt` and runs the design tooling. Both start with a `python -m pip install` line and a reader skimming may run only the second and then wonder why `tests/` fails to import `rookery`. One sentence noting that the design checks need only the design requirements, while the package tests need the wheel, would remove the ambiguity.

**`--force-reinstall` in the README but not in CI** (`README.md` vs `fixtures.yml:55`). Correct in both cases — CI starts from a clean runner, a developer does not — but the divergence is worth a short comment so nobody "fixes" the inconsistency by removing it from the README, which would leave developers silently testing a stale wheel after a code change. That failure mode is unpleasant: tests pass against code you did not write.

**Error messages are good.** `ContractError.__str__` is `"{code}: {path}"`, e.g. `schema_pattern: id`. Short, greppable, and it names the field. Combined with the codes being stable strings rather than prose, this is the right shape for something an importer will surface to an operator. See [M1](04-maintainability.md#m1) for the one caveat about where those codes come from.

**The verification-scope step is a good pattern, continued.** `fixtures.yml:58-60` ends every run — including failed ones, via `if: always()` — by printing what was *not* tested:

> `Fixture parsing and installed-package tests only. No worker isolation, source import, backup/restore, policy authorization, slicer or physical printer test was executed.`

This is the CI equivalent of the design checker's closing line, and carrying it forward is exactly what the Phase 0 review asked for. A green check on a repository that will later touch heating elements should say what it does not mean, and this one does.
