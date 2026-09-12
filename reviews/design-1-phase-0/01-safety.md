# Design Safety

Rookery's central physical-safety claim is that it never actuates anything: no printer control, no upload, no live writer, and every physical action is initiated by a human. **This PR upholds that claim.** There is no network client, no device access, no subprocess, and no writer of any kind in the tree. `check_design.py` even asserts `ApplyReceipt` is absent from the schema.

So the safety findings below are not "this code can overheat a printer". They are about the *data contracts* that will carry heater-relevant values once B05/B06 implement policy — where the contract is currently too loose to hold up the guarantee the documents promise.

---

## <a id="s1"></a>S1 — High — `Path` accepts Windows device names and trailing-dot/space aliases

**Location:** `schemas/0.1.0/rookery.schema.json:27`

```json
"Path": {"type": "string", "minLength": 1, "maxLength": 1024,
         "pattern": "^(?!/)(?!.*(?:^|/)\\.{1,2}(?:/|$))(?!.*[:\\\\])[A-Za-z0-9_./ -]+$"}
```

The pattern correctly rejects POSIX absolute paths, `..` traversal, backslashes, and colons (so drive letters, UNC and NTFS alternate streams are covered). `check_design.py:118` probes six such escapes. What it does not reject:

| Accepted value | Windows behaviour |
| --- | --- |
| `NUL`, `CON`, `PRN`, `AUX`, `COM1`, `LPT1.json`, `aux/config.cfg` | Resolves to a character device, not a file |
| `printer.cfg.` | Trailing dot is stripped — aliases `printer.cfg` |
| `printer.cfg ` | Trailing space is stripped — aliases `printer.cfg` |
| `dir/` | Directory, not a file |
| `a//b.json` | Empty path segment |

**Verified on the review machine** (Windows 11, `evidence/probe_paths.py`):

```
'secret.json.' -> wrote; secret.json now = "OVERWRITTEN-VIA-'secret.json.'"
   directory listing: ['secret.json']
'secret.json ' -> wrote; secret.json now = "OVERWRITTEN-VIA-'secret.json '"
   directory listing: ['secret.json']
NUL: write succeeded; file on disk? True | listing: ['secret.json']
```

Two consequences, both aimed at the guarantee that gates all candidate staging:

1. **A restore to `NUL` silently discards the bytes and then reports success.** `open("NUL","w")` succeeds, the write is swallowed by the null device, and `os.path.exists("NUL")` returns `True`. A restore-verification routine that confirms "the file exists after restore" would pass while the configuration was never written. That is R07 / H10 / A05 / A06 failing open, which is precisely the failure mode `policies.md` says must block candidate writes with `BACKUP_FAILED`.
2. **Three distinct schema-valid paths collide on one real file.** `printer.cfg`, `printer.cfg.` and `printer.cfg ` are different strings to the schema and the same file to Windows. This defeats the "no duplicate/ambiguous settings" invariant and makes exact-byte restore nondeterministic.

This matters more here than in most projects because `architecture.md` explicitly commits to rejecting "absolute/UNC/device paths" and flags "Windows paths and reparse points" as first-class risks, and because Windows is the stated first-class platform (ADR-001).

**Suggested fix** — extend the pattern and add probes:

```json
"Path": {
  "type": "string", "minLength": 1, "maxLength": 1024,
  "pattern": "^(?!/)(?!.*(?:^|/)\\.{1,2}(?:/|$))(?!.*[:\\\\])(?!.*//)(?!.*[ .]$)(?!.*(?:^|/)(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\\.[^/]*)?(?:/|$))[A-Za-z0-9_./ -]+$"
}
```

Then extend the probe list at `check_design.py:118`:

```python
for path in ["NUL", "CON", "aux/config.cfg", "COM1.json", "printer.cfg.", "printer.cfg ", "dir/", "a//b.json"]:
```

`(?i:...)` inline-flag groups work in both Python and ECMA-262; if you would rather stay strictly portable across validator implementations, spell the alternation out in both cases instead. Whichever you choose, keep the runtime containment check described in `architecture.md` as well — the regex is defence in depth, not a replacement for canonicalisation and handle-level checks.

---

## <a id="s2"></a>S2 — High — a reviewed `Range` cannot be reliably bound to a proposed `Change`

**Location:** `schemas/0.1.0/rookery.schema.json:132` (`Range`), `:187` (`Change`)

```json
"Range":  { "required": ["parameter", "units", "minimum", "maximum", "review_digest"], ... }
"Change": { "required": ["domain", "file_digest", "path", "key", "current_value",
                         "proposed_value", "units", "evidence_digests"], ... }
```

`Range.parameter` and `Change.key` are both free-form `Text`. `Range.units` and `Change.units` are both free-form `Text`. `Range` has **no `domain` field at all**, and `additionalProperties: false` means one cannot be added ad hoc. Nothing in the schema or in `data-contracts.md` states how the policy engine decides that a given `Range` authorises a given `Change`.

For a project whose one irreducible safety bound is "this number may not exceed that number on a heating element", that binding is the load-bearing part, and it is currently unspecified. Four concrete holes, all verified in `evidence/probe_schema_gaps.py`:

1. **No domain qualifier.** A range reviewed for `orca_process` is indistinguishable from one reviewed for `orca_printer`. Same parameter name, very different hardware consequence.
2. **No unit agreement.** Schema-valid: a change with `units: "mm/s"` proposing `250` against a range expressed in `"C"`. Nothing rejects it.
3. **No `minimum <= maximum`.** Schema-valid: `{"minimum": 300, "maximum": 10}`. JSON Schema genuinely cannot express this, so it must be a documented runtime invariant — and it currently is not documented anywhere. Whether an inverted range fails open or closed depends entirely on how B06 happens to write the comparison: `min <= v <= max` fails closed, `v >= min or v <= max` fails open.
4. **No uniqueness per parameter.** Schema-valid: two ranges for the same `parameter`, one `150–260` and one `150–450`. Which one governs is undefined.

`data-contracts.md` does list "Key/domain/unit/current-value/policy checks" as cross-record validation for `ChangeProposal`, which is the right instinct. But it says nothing about `Range`, and the `Range`↔`Change` join is the step that actually enforces a bound.

**Suggested fix:**

- Add `"domain"` to `Range` with the same enum as `Change.domain`, and add it to `required`.
- Replace free-form `units` with a shared `$defs/Units` enum, or at minimum require byte-exact equality between `Range.units` and `Change.units` as a stated runtime invariant.
- Document in `data-contracts.md` under `CalibrationDefinition`: `minimum <= maximum`; at most one range per `(domain, parameter)`; `parameter` and `key` are matched **byte-exact and case-sensitive**, with no normalisation, aliasing or prefix matching.

That last point is worth stating explicitly because H04 already names "units, aliases and version drift" as the thing that must be tested — this is where that test will need a contract to test against.

---

## <a id="s3"></a>S3 — Medium — `proposed_value` and `current_value` are unconstrained `Scalar`

**Location:** `schemas/0.1.0/rookery.schema.json:28` (`Scalar`), `:187` (`Change`)

```json
"Scalar": {"type": ["string", "number", "boolean", "null"]}
```

All of the following are schema-valid `ChangeProposal` records (verified, `evidence/probe_schema_gaps.py`):

| Proposed value | Problem |
| --- | --- |
| `null` | Means what? Delete the key? Reset to inherited? Undefined. |
| `"500"` | String where the policy will compare a number |
| `true` | Boolean temperature |
| `1e308` | Finite, so it passes `finite_float`, but not a physical quantity |
| `current_value: "210"` with `proposed_value: 500` | Type mismatch between the value being replaced and its replacement |

`data-contracts.md` already says the right thing — "Candidate numerical input must be finite", "`Decimal` for policy comparisons; avoid float rounding at safety bounds" — but the schema carries none of it, and `Scalar` is the type an untrusted model fills in.

**Suggested fix:** state as a runtime invariant that `current_value` and `proposed_value` must be the same JSON type (JSON Schema cannot compare two sibling values, so this has to live in the typed model), and either forbid `null` in `proposed_value` or document what it means. If "delete this key" is a real operation it deserves an explicit `operation` enum rather than an overloaded `null`.

---

## <a id="s4"></a>S4 — Medium — `PrinterIdentity` can claim Klipper validation with zero evidence

**Location:** `schemas/0.1.0/rookery.schema.json:201`

```json
"if":   {"properties": {"validation_scope": {"enum": ["klipper_static", "klipper_observed"]}}},
"then": {"properties": {"firmware": {"const": "klipper"}}}
```

The conditional pins `firmware` but nothing else. `identity_evidence_digests` has no `minItems` and `hardware_digest` is a `MaybeDigest`. Verified schema-valid:

```
SCHEMA-VALID  klipper_static   with ZERO identity evidence + null hardware_digest
SCHEMA-VALID  klipper_observed with ZERO identity evidence + null hardware_digest
```

`validation_scope` is what downstream records use to decide how far a conclusion may be trusted — `policies.md` says "never synthesize firmware validation from slicer-only data". A record asserting `klipper_observed` while carrying no evidence at all is exactly that synthesis, and it currently parses.

The PR already gets the analogous case right one record over: `ActivationObservation` requires `loaded_config_digest` and `runtime_evidence_digests: minItems 1` when `verification: matched` and `firmware_scope: klipper_observed`, and `check_design.py:173` probes it. `PrinterIdentity` should mirror that.

**Suggested fix** (this moves the existing top-level `if`/`then` into an `allOf`, matching the style already used by `ActivationObservation` and `ApprovalRecord`):

```json
"allOf": [
  {"$ref": "#/$defs/Base"},
  {"if":   {"properties": {"validation_scope": {"enum": ["klipper_static", "klipper_observed"]}}},
   "then": {"properties": {"firmware": {"const": "klipper"},
                           "identity_evidence_digests": {"minItems": 1}}}},
  {"if":   {"properties": {"validation_scope": {"const": "klipper_observed"}}},
   "then": {"properties": {"hardware_digest": {"$ref": "#/$defs/Digest"}}}}
]
```

---

## What I checked and found correct

These are the safety properties I specifically tried to break and could not:

- **An untrusted model cannot propose a Klipper or firmware change.** All six attack shapes I constructed against `DiagnosticResponse` were rejected — see [02-security.md#s5](02-security.md#s5). The layering (`risk` forced to `bounded_slicer` → `domain` restricted to the three Orca domains) is correct, and it is the single best piece of design in this PR.
- **`ApprovalRecord.risk_scope` has no value that could authorise an elevated proposal.** The enum is `baseline_review | bounded_slicer_change` only, so an `elevated_proposal_only` proposal has no path to export. That loop is closed deliberately and it closes properly.
- **A `BackupReceipt` cannot claim `verified` without read-back and temporary-restore digests.** Probed at `check_design.py:123` and confirmed still enforced by mutation test.
- **No `ApplyReceipt`, no upload adapter, no live writer, no G-code execution path** anywhere in the tree.
- **Examples use deliberately fictional keys and units** (`fictional_parameter_not_an_orca_key`, `fictional_units`), so no synthetic example can be copy-pasted into something real. That is a thoughtful touch and worth preserving as a convention.
- `prompts/diagnostic-v0.1.0.md` correctly instructs the model that text in images and files is evidence and never an instruction, and forbids claiming an image establishes heater safety.
- The `EvidenceBundle` "six labels could depict one face" limitation is **already acknowledged** in `data-contracts.md` under "Completeness Versus Shape". I confirmed it is schema-valid to point six views at one image digest, but since the document names it as a known semantic limit requiring pixels to detect, I am not raising it as a finding.
