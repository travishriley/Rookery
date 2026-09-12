# Maintainability and Best Practice

`tools/check_design.py` is 253 lines and is easy to follow. Functions are small and single-purpose, the `require(condition, message)` helper keeps assertions readable, and the separation between `check_refs` / `check_examples` / `check_supplemental` / `check_links` maps cleanly onto what each one validates. The schema is consistent in style and composes correctly with `allOf` + `unevaluatedProperties`.

Everything below is low severity. None of it affects correctness today.

---

## <a id="m1"></a>M1 — `check_supplemental` returns a hardcoded `(3, 3)`

**Location:** `tools/check_design.py:217`

```python
    require(not toolchain_validator.is_valid(toolchain), "Toolchain accepted missing binary identity")
    return 3, 3
```

`check_examples` counts its probes as it runs, via the `positive` / `negative` closures. `check_supplemental` does not — it returns a literal tally that happens to match its three `validate` calls and three `require(not ...)` calls.

The counts are not cosmetic. The PR body and `verification.md` both cite "17 positive shapes, 76 negative probes" as validation evidence, and `README.md` frames the checker as the thing that substantiates the design. A hardcoded tally silently decouples the advertised number from reality the first time someone adds or removes a probe — and [S5](02-security.md#s5) asks for exactly that.

**Suggested fix:** use the same counter pattern as `check_examples`, or have both return a list of probe labels and let `main` report `len(...)`. The label list would also make the output self-documenting.

---

## <a id="m2"></a>M2 — `toolchain_validator` silently omits `format_checker`

**Location:** `tools/check_design.py:211`

```python
validator           = Draft202012Validator(schema,           format_checker=FORMATS, registry=...)   # line 86
validator           = Draft202012Validator(response_schema,  format_checker=FORMATS, registry=...)   # line 192
toolchain_validator = Draft202012Validator(toolchain_schema,                         registry=...)   # line 211
```

Two of three validators assert formats; the third does not. It is harmless right now because `ToolchainManifest` has no `date-time` field — but that is a coincidence, not a design. If a `built_at` or `probed_at` field is added later (and a capability receipt plausibly wants one), it would silently skip UTC validation while the other records enforce it.

This is worth fixing mainly because `format` in JSON Schema is annotation-only by default, so an omitted `format_checker` fails *open* and silently. It is the kind of thing that is invisible in review.

**Suggested fix:** add `format_checker=FORMATS`, or better, a single factory:

```python
def make_validator(schema):
    return Draft202012Validator(schema, format_checker=FORMATS, registry=Registry(retrieve=no_remote_schema))
```

which removes the possibility of the three call sites drifting at all.

---

## <a id="m3"></a>M3 — derived schemas built by dict-spread keep the same `$id`

**Location:** `tools/check_design.py:191`, `:210`

```python
response_schema  = {**schema, "oneOf": [{"$ref": "#/$defs/DiagnosticResponse"}]}
toolchain_schema = {**schema, "oneOf": [{"$ref": "#/$defs/ToolchainManifest"}]}
```

Both carry `"$id": "urn:rookery:schema:0.1.0"` inherited from the spread, so three structurally different schema documents claim the same identity. It works today because the `Registry` is empty and every `$ref` is a local JSON pointer resolved against the document being validated. It would stop working the moment anyone registers the base schema as a named resource — a plausible B01 step once the schema is consumed by product code rather than one script.

**Suggested fix:** a small helper that also drops the inherited `$id`, which makes the intent ("validate one named `$def` in isolation") obvious:

```python
def subschema(schema, name):
    branch = {key: value for key, value in schema.items() if key != "$id"}
    branch["oneOf"] = [{"$ref": f"#/$defs/{name}"}]
    return branch
```

This pairs naturally with the `make_validator` factory in M2 and with the `kind`-dispatch fix in [U1](03-usability.md#u1), which needs the same construction.

---

## <a id="m4"></a>M4 — `utc_datetime`'s final comparison is tautological

**Location:** `tools/check_design.py:59-66`

```python
@FORMATS.checks("date-time", raises=ValueError)
def utc_datetime(value):
    # The wire format intentionally uses a UTC subset supported by datetime.
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value):
        return False
    return datetime.fromisoformat(value).utcoffset().total_seconds() == 0
```

The regex already requires a literal trailing `Z`, so on Python 3.11+ `fromisoformat` always yields a UTC-aware datetime and `utcoffset().total_seconds()` is always `0.0`. The comparison can never be false. I verified this across the full range of accepted shapes.

The line is not dead, though — it is load-bearing for a different reason. The `fromisoformat` call is what performs **calendar validation**, and it does so by raising `ValueError`, which the `raises=ValueError` declaration converts into a format failure. That is what rejects the `2026-02-30T12:00:00Z` probe at `check_design.py:106`, and it also rejects leap seconds (`23:59:60Z`), matching the documented "leap seconds ... not accepted" rule in `data-contracts.md`. Verified:

```
regex=True   2026-09-12T12:00:00Z              parsed offset=0.0
regex=True   2026-09-12T12:00:00.1234567890Z   parsed offset=0.0
regex=True   2026-02-30T12:00:00Z              ValueError: day is out of range for month
regex=True   2026-09-12T23:59:60Z              ValueError: second must be in 0..59
```

So the behaviour is correct and matches the spec; the code just does not read that way. A future reader "simplifying" the tautological comparison away would remove the calendar check without noticing.

**Suggested fix** — make the intent explicit rather than incidental:

```python
    # fromisoformat raises ValueError on impossible dates and leap seconds; raises=ValueError
    # converts that into a format failure. The regex has already pinned the offset to UTC.
    datetime.fromisoformat(value)
    return True
```

(Also worth noting in `data-contracts.md`: the regex accepts arbitrarily many fractional digits — `.1234567890Z` passes. That is consistent with the documented "optional fractional seconds", but if a precision limit is intended, now is the time to say so.)

---

## <a id="m5"></a>M5 — the `changes *= 2` probe is mislabeled

**Location:** `tools/check_design.py:153-155`

```python
changed = deepcopy(by_kind["ChangeProposal"])
changed["changes"] *= 2
reject(changed, "two independent changes")
```

`list * 2` produces `[a, a]` — the same change twice, not two independent ones. The rule under test (`ProposalPayload.changes.maxItems: 1`) rejects both cases identically, so the probe does pass for the right reason. But R14's actual requirement is "one independent variable initially", and the label claims to test that while the data tests duplication.

**Suggested fix** — make the probe match its label, since the distinction is the whole point of R14:

```python
changed = deepcopy(by_kind["ChangeProposal"])
second = deepcopy(changed["changes"][0])
second.update(key="a_second_fictional_parameter", current_value=3, proposed_value=4)
changed["changes"].append(second)
reject(changed, "two independent changes")
```

---

## <a id="m6"></a>M6 — `check_links` skips `prompts/` and scans fenced code blocks

**Location:** `tools/check_design.py:220-232`

```python
files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
...
for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
```

Three small gaps, none currently biting:

- **`prompts/` is not scanned.** `prompts/diagnostic-v0.1.0.md` is a versioned product artifact that will accrue links. Excluding `ROOKERY_ASTRA_BUILD_PROMPT.md` is correct (it is byte-frozen), but `prompts/` should be in scope. Changing the glob to `ROOT.rglob("*.md")` with an explicit exclusion for the frozen prompt would be more robust than an allowlist of two directories.
- **Fenced code blocks are scanned.** A Markdown example containing `[x](y)` would be link-checked as if real. No current instance.
- **Reference-style links (`[text][ref]`) and autolinks (`<https://...>`) are not detected**, so they silently skip validation.

The containment check itself (`target_path.is_relative_to(ROOT)`) is good and worth keeping.

---

## <a id="m7"></a>M7 — `ApprovalRecord.bindings` has no proposal digest

**Location:** `schemas/0.1.0/rookery.schema.json:63` (`Bindings`), `:91` (`CandidateBindings`)

`Bindings` binds printer, source, candidate, toolchain, calibration, raw G-code, effective settings, evidence, policy, prompt and provider. It does not bind the `ChangeProposal`. So the chain `DiagnosticReport → ChangeProposal → ApprovalRecord` is joined in one direction only: the report points forward via `proposal_digest`, but the approval never points back.

This is defensible — `candidate_digest` binds the actual bytes that get exported, which is what matters for safety, and `review_packet_digest` covers the human-facing packet that contained the proposal. So there is no hole in authorization. But the proposal is where `risk`, `rollback_snapshot_digest`, `validation_test` and the stated rationale live, and none of those are reachable from an approval by digest — only through an opaque packet hash whose composition is not specified.

**Suggested fix:** either add `proposal_digest` to `CandidateBindings` (it would be `null` for `baseline_package_review`, matching how `candidate_digest` already works), or state in `data-contracts.md` exactly what `review_packet_digest` covers and that the proposal is reachable through it. The second is cheaper and may be sufficient; the first makes the chain machine-checkable, which A09's drift tests will want.

---

## Style notes (no action needed)

- **Line length.** The schema uses very long single-line JSON — the `State` enum at line 199 is 581 characters and `ToolchainManifest.required` at line 52 is 331. It is consistent and keeps the file at 416 lines rather than ~1200, which is a reasonable trade for a reference document. Just be aware that GitHub's diff view wraps these poorly, which will make schema review harder as it grows, and that a one-word change to the `State` enum shows up as a 581-character diff line.
- **`check_refs` counts but does not verify reachability.** It confirms every `$ref` resolves; it does not confirm every `$def` is referenced. An orphaned `$def` would go unnoticed. Not worth fixing unless the schema grows.
- **`Draft202012Validator.check_schema(schema)` at `:238` runs before anything else.** Good — meta-validating the schema before using it is a step most projects skip.
- **`requirements-design.txt` pins exact versions but without hashes.** Given H15 names supply-chain compromise explicitly, `--require-hashes` would be the consistent choice. The file's own comment ("Versions already installed ... no product dependencies") makes this defensible for Phase 0; worth revisiting in B01 when these become real CI dependencies.
