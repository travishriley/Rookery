# Usability

"End user" here means two audiences, because Phase 0 has no product yet:

1. **The reviewer** — someone cloning this branch to check the design. Their entire experience is the README plus `python tools/check_design.py`.
2. **The future operator** — the solo owner who will eventually run experiments. Phase 0 shapes their experience through the state machine, the approval protocol, and the error vocabulary.

The second audience is served well. The state machine's exceptional states (`INSUFFICIENT_EVIDENCE`, `UNSAFE_BASELINE`, `BACKUP_FAILED`, `MANUAL_CHECK_NEEDED`, `BUDGET_EXHAUSTED`, `NO_CHANGE`) are genuinely good UX design: every failure has a name, a documented trigger, and a documented recovery path, and `NO_CHANGE` being a first-class terminal outcome rather than a failure is the kind of detail that prevents an operator from feeling obliged to keep tuning. The approval-packet contents list in `policies.md` is the right level of detail for a human to actually make a decision.

The first audience hits friction immediately.

---

## <a id="u1"></a>U1 — Medium — validation failures print a traceback and never name the failing field

**Location:** `tools/check_design.py:96`, `:235` (`main` has no error handling)

I introduced one bad character into an example `id` and ran the checker. This is what a reviewer sees:

```
Traceback (most recent call last):
  File "...\tools\check_design.py", line 105, in check_examples
    accept(example)
  File "...\tools\check_design.py", line 96, in accept
    require(not errors, f"Invalid positive shape {value.get('kind')}: ...")
  File "...\tools\check_design.py", line 27, in require
    raise ValueError(message)
ValueError: Invalid positive shape PrinterIdentity: ["{'schema_version': '0.1.0', 'kind':
'PrinterIdentity', 'id': 'bad id with spaces', 'created_at': '2026-09-12T12:00:00Z', 'label':
'Fictional schema example, no hardware', 'firmware': 'unknown', 'validation_scope': 'slicer_only',
'hardware_digest': None, 'identity_evidence_digests': []} is not valid under any of the given schemas"]
```

Two separate problems:

**The message is useless.** Because the schema root is an 11-branch `oneOf` with no discriminator, `jsonschema` cannot tell which branch was intended and falls back to "is not valid under any of the given schemas", dumping the whole record without ever naming `id`. This gets worse as records grow. Note that `best_match` alone does **not** fix it — I tried; it returns the same root-level error with an empty path, because the ambiguity is structural.

Dispatching on `kind` first does fix it:

```python
def errors_for(schema, value):
    branch = {**schema, "oneOf": [{"$ref": f"#/$defs/{value['kind']}"}]}
    v = Draft202012Validator(branch, format_checker=FORMATS, registry=Registry(retrieve=no_remote_schema))
    return v.iter_errors(value)
```

Verified output with that change:

```
path   : ['id']
message: 'bad id with spaces' does not match '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$'
```

That is the difference between a 30-second fix and a 10-minute bisect. It is worth doing now rather than in B01, because these are the error messages the Phase 1 typed models will inherit.

**The traceback is noise.** `require` raises a bare `ValueError` and `main` does not catch it, so every failure — including entirely expected ones like "you edited an example" — arrives as a stack trace. Suggested:

```python
if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
```

The exit code is already 1 either way; this just stops the output from looking like a crash.

---

## <a id="u2"></a>U2 — Medium — no minimum Python version is declared or enforced

**Location:** `tools/check_design.py` (whole file), `README.md:26`

The checker requires **Python 3.11 or newer**, for a reason that is easy to miss:

| Construct | Introduced |
| --- | --- |
| `datetime.fromisoformat("...Z")` accepting a `Z` suffix (`check_design.py:66`) | 3.11 |
| `str.removeprefix` (`:75`) | 3.9 |
| `Path.is_relative_to` (`:229`) | 3.9 |

Nothing declares this. There is no `pyproject.toml`, no `requires-python`, and no runtime guard. `README.md` says "Observed environment: Windows 11 AMD64, Python 3.13.7", but that is phrased as an observation, and the surrounding sentence explicitly disclaims it as a support promise.

The failure mode on 3.10 is actively misleading. `fromisoformat` raises `ValueError` on the `Z`, the format checker is declared `raises=ValueError`, so the exception is swallowed and every timestamp is reported as an invalid format. The reviewer sees `Invalid positive shape PrinterIdentity: [...]` on a record that is perfectly valid, with no hint that their interpreter is the cause. They would reasonably conclude the PR is broken.

**Suggested fix** — three lines at the top of `check_design.py`:

```python
if sys.version_info < (3, 11):
    raise SystemExit("check_design.py requires Python 3.11+ (datetime.fromisoformat must accept a 'Z' suffix)")
```

and one word in the README: "Requires Python 3.11+". The `requires-python` metadata can wait for B01's packaging work, but the guard should not — B01 is gated on this PR being reviewable.

---

## <a id="u3"></a>U3 — Low — the README never says to install the dependencies

**Location:** `README.md:26-33`

The README's "Design Checks" section says:

```powershell
python tools/check_design.py
git diff --check
```

`requirements-design.txt` is linked one sentence earlier, but only as a record of "existing validator dependencies". Nothing tells the reader to install it. A reviewer with a clean Python gets `ModuleNotFoundError: No module named 'jsonschema'` as their first interaction with the project.

**Suggested fix:**

```powershell
python -m pip install -r requirements-design.txt
python tools/check_design.py
git diff --check
```

Worth a parenthetical that this installs into whatever environment is active, since `.gitignore` anticipates a `.venv/` but the README never mentions creating one.

---

## Smaller observations

**`git diff --check` in the README vs `git diff --cached --check` in the docs.** `README.md:31` says `git diff --check`; `verification.md` and the PR body report running `git diff --cached --check`. On a clean tree the former checks nothing at all, so a reviewer following the README runs a no-op and believes they reproduced the recorded check. Make them the same command, or say which one the record refers to.

**The success output is well judged.** The final two lines are worth keeping exactly as they are:

```
PASS: Draft 2020-12 schema, 225 local references, 17 positive shapes, 76 negative probes, 25 local links, original prompt SHA-256
Design checks only. No product policy, worker isolation, slicer runtime, live printer, restore destination, or physical-quality test was executed.
```

Printing what was *not* checked immediately after `PASS` is the single most user-respecting thing in this PR. It prevents the exact misreading — "the checks passed, so the design is validated" — that the whole document set is trying to avoid. Keep this pattern in B01's CI checks.

**Document navigation is good.** The README's numbered reading order, the "Start with README.md, then decisions.md and architecture.md" line in the PR body, and the consistent `Status:` line at the top of every document all make a 1,590-line design package approachable. The requirement→acceptance→backlog ID cross-referencing (R01→A01/A02→B02/B09) works and is checked by the link checker.
