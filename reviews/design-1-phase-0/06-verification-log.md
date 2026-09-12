# Verification Log

Every finding in this review was checked by execution against commit `5123a7db0f35e49827a5fa8141521404c63ec41f`. This file records the commands and their raw output so the findings can be audited rather than taken on trust.

**Environment:** Windows 11 Pro (build 26200), AMD64, Python 3.13.7, Git 2.51.1.windows.1, jsonschema 4.25.1 — the same environment recorded in `inventory-and-capabilities.md`.

**Nothing outside the repository and a temporary directory was touched.** No printer, device, network service, slicer process, or model provider was contacted. The only write outside the review branch was to `%TEMP%`, removed afterwards.

---

## 1. Baseline: the checker passes as advertised

```console
$ python --version
Python 3.13.7

$ python tools/check_design.py
PASS: Draft 2020-12 schema, 225 local references, 17 positive shapes, 76 negative probes, 25 local links, original prompt SHA-256
Design checks only. No product policy, worker isolation, slicer runtime, live printer, restore destination, or physical-quality test was executed.
$ echo $?
0
```

The counts match `verification.md` and the PR body exactly: 225 / 17 / 76 / 25. **Confirmed.**

---

## 2. The frozen prompt really is byte-preserved

`verification.md` claims the supplied prompt is preserved unchanged and hash-verified. Checked independently:

```console
$ git check-attr -a ROOKERY_ASTRA_BUILD_PROMPT.md
ROOKERY_ASTRA_BUILD_PROMPT.md: text: unset
ROOKERY_ASTRA_BUILD_PROMPT.md: eol: lf

$ git check-attr -a README.md
README.md: text: set
README.md: eol: lf
```

```
working tree sha256: 1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e
has CRLF: False | bytes: 30182
no-filters blob: 80fff9e81564bd456dc2dae1e7e01b6e1ed1fc5a
index blob     : 80fff9e81564bd456dc2dae1e7e01b6e1ed1fc5a   MATCH
```

The working-tree hash equals `PROMPT_HASH` in `check_design.py:22` and the value recorded in `inventory-and-capabilities.md`. The size matches the documented 30,182 bytes. The `-text` override at `.gitattributes:6` is correctly ordered after `*.md text eol=lf` (later rules win per attribute), and `git hash-object --no-filters` equals the index blob, so no filter is applied on either side. **Confirmed — this claim holds.** See [S8](02-security.md#s8) for the one caveat about what the hash can and cannot establish.

---

## 3. S1 — Path pattern and Windows filesystem behaviour

```console
$ python reviews/design-1-phase-0/evidence/probe_paths.py
```

```
--- S1 part 1: what the Path pattern accepts ---
  pattern: ^(?!/)(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*[:\\])[A-Za-z0-9_./ -]+$

  already probed by check_design.py:118 (all correctly rejected):
    rejected  '../outside.json'
    rejected  'nested/../../outside.json'
    rejected  '/absolute.json'
    rejected  'C:/outside.json'
    rejected  'file.json:secret'
    rejected  '..\\outside.json'

  NOT probed by check_design.py:
    ACCEPTED <-- finding  'NUL'
    ACCEPTED <-- finding  'CON'
    ACCEPTED <-- finding  'PRN'
    ACCEPTED <-- finding  'AUX'
    ACCEPTED <-- finding  'COM1'
    ACCEPTED <-- finding  'LPT1.json'
    ACCEPTED <-- finding  'aux/config.cfg'
    ACCEPTED <-- finding  'printer.cfg.'
    ACCEPTED <-- finding  'printer.cfg '
    ACCEPTED <-- finding  'dir/'
    ACCEPTED <-- finding  'a//b.json'
    ACCEPTED <-- finding  '...'
    ACCEPTED <-- finding  'a/.../b'

--- S1 part 2: what Windows actually does with those paths ---
  wrote 'secret.json.' -> secret.json now reads "OVERWRITTEN-VIA-'secret.json.'"
    directory listing: ['secret.json']
  wrote 'secret.json ' -> secret.json now reads "OVERWRITTEN-VIA-'secret.json '"
    directory listing: ['secret.json']
  wrote 'NUL' -> os.path.exists reports True, but listing is ['secret.json']
    (the bytes went to the null device and were discarded; an existence check after restore would still report success)
```

The six escapes the checker already probes are all correctly rejected — that part of the pattern is sound. The thirteen it does not probe are all accepted, and three of them have real filesystem consequences on the project's stated first-class platform.

---

## 4. S2 / S3 / S4 / S6 — schema shapes that parse but should not

```console
$ python reviews/design-1-phase-0/evidence/probe_schema_gaps.py
```

```
--- S2/S3: ChangeProposal accepts unbounded and untyped values ---
  SCHEMA-VALID  nozzle_temperature -> 500 (no Range is bound to this Change)
  SCHEMA-VALID  proposed_value = 1e308 (finite, so finite_float passes)
  SCHEMA-VALID  proposed_value = null (delete key? semantics undefined)
  SCHEMA-VALID  proposed_value = '500' (string where policy compares a number)
  SCHEMA-VALID  proposed_value = true (boolean temperature)
  SCHEMA-VALID  units mismatch: proposes 250 with units 'mm/s'
  SCHEMA-VALID  current_value is a string, proposed_value is a number

--- S2: CalibrationDefinition Range invariants ---
  Range has a 'domain' field: False
  Range additionalProperties: False
  (so a domain cannot be added ad hoc either)

  SCHEMA-VALID  minimum(300) > maximum(10) -- inverted bound
  SCHEMA-VALID  two contradictory ranges for the SAME parameter (150-260 and 150-450)

--- S4: PrinterIdentity can claim Klipper validation with no evidence ---
  SCHEMA-VALID  klipper_static with zero identity evidence and null hardware_digest
  SCHEMA-VALID  klipper_observed with zero identity evidence and null hardware_digest

--- S6: no uniqueness constraint on files or captures ---
  SourceSnapshot.files uniqueItems: None
  EvidenceBundle.captures uniqueItems: None
  Digests uniqueItems: True   <- the idiom is already used elsewhere

  SCHEMA-VALID  files 'process.json' and 'process.json.' (same file on Windows)
  SCHEMA-VALID  two entries, identical path 'process.json', different digests
  SCHEMA-VALID  two captures sharing one id (Finding.capture_ids becomes ambiguous)

--- Context for M7: ApprovalRecord field ordering is not expressible in JSON Schema ---
  SCHEMA-VALID  expires_at precedes approved_at (must be a runtime invariant)
```

---

## 5. S5 — model containment works, but is untested

```console
$ python reviews/design-1-phase-0/evidence/probe_model_containment.py
```

```
--- S5 part 1: do the model-containment rules actually hold? ---
  ACCEPTED      baseline: bounded_slicer proposal in an orca_process domain
  rejected(ok)  model escalates its own risk to elevated_proposal_only
  rejected(ok)  model reaches a Klipper domain via the elevated risk level
  rejected(ok)  model proposes a Klipper domain under bounded_slicer
  rejected(ok)  model attaches a proposal to a no_change outcome
  rejected(ok)  model returns more than one change

--- S5 part 2: does check_design.py probe any of them? ---
  elevated_proposal_only   appears in check_design.py: False
  klipper_audit_only       appears in check_design.py: True
  no_change                appears in check_design.py: False
  arbitrary_script         appears in check_design.py: True
  bounded_slicer           appears in check_design.py: False
```

All five containment rules hold. None is probed.

### Mutation test

```console
$ python reviews/design-1-phase-0/evidence/mutation_test.py
```

```
   checker   safety rule removed from the schema
--------------------------------------------------------------------------------------------
      PASS   DiagnosticResponse if/then  (model may escalate its own risk)  <-- UNPROTECTED
      FAIL   ProposalPayload if/then     (proposal may reach a klipper_audit_only domain)
      FAIL   Path pattern                (traversal and device paths become valid)
      FAIL   ActivationObservation rule  (matched Klipper activation needs no evidence)
      FAIL   BackupReceipt if/then       (a backup may claim verified with no read-back)
      FAIL   ProposalPayload maxItems    (a proposal may carry two independent changes)
--------------------------------------------------------------------------------------------
1 of 6 safety rules can be deleted without check_design.py noticing:
  - DiagnosticResponse if/then  (model may escalate its own risk)
```

Five of six safety rules are genuinely load-bearing in the checker — the existing 76 probes are doing real work. The sixth is not covered.

---

## 6. U1 — error message quality

Introduced one invalid character into an example `id` and ran the checker. Abbreviated output:

```
Traceback (most recent call last):
  ...
  File "...\tools\check_design.py", line 27, in require
    raise ValueError(message)
ValueError: Invalid positive shape PrinterIdentity: ["{'schema_version': '0.1.0', 'kind':
'PrinterIdentity', 'id': 'bad id with spaces', ... } is not valid under any of the given schemas"]
```

Then compared three error-reporting strategies against the same bad record:

| Strategy | Reported path | Message |
| --- | --- | --- |
| Current (`iter_errors` on the root `oneOf`) | — | `... is not valid under any of the given schemas` |
| `jsonschema.exceptions.best_match` alone | `[]` | `... is not valid under any of the given schemas` |
| Dispatch on `kind`, then `best_match` | `['id']` | `'bad id with spaces' does not match '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$'` |

`best_match` alone does not help, because the ambiguity is structural: an 11-branch `oneOf` with no discriminator gives the library nothing to prefer. Dispatching on `kind` first resolves it.

---

## 7. U2 / M4 — date-time handling and the Python floor

```
regex=True   2026-09-12T12:00:00Z              parsed offset=0.0
regex=True   2026-09-12T12:00:00.123Z          parsed offset=0.0
regex=True   2026-09-12T12:00:00.1234Z         parsed offset=0.0
regex=True   2026-09-12T12:00:00.1Z            parsed offset=0.0
regex=True   2026-09-12T12:00:00.1234567890Z   parsed offset=0.0
regex=True   2026-02-30T12:00:00Z              ValueError: day is out of range for month
regex=True   2026-09-12T23:59:60Z              ValueError: second must be in 0..59
```

Three things established:

- The `utcoffset() == 0` comparison at `check_design.py:66` is never false — the regex has already pinned the trailing `Z`. The real work is done by the `ValueError` from `fromisoformat`, which `raises=ValueError` converts into a format failure ([M4](04-maintainability.md#m4)).
- Calendar validation and leap-second rejection both behave as `data-contracts.md` documents. **Confirmed.**
- Arbitrary fractional-second precision is accepted, consistent with the documented "optional fractional seconds".
- `datetime.fromisoformat` only accepts a `Z` suffix on **Python 3.11+**, which is the undeclared floor described in [U2](03-usability.md#u2).

---

## 8. Repository hygiene checks

```console
$ git status --short
(clean)

$ git rev-parse HEAD origin/design/1-phase-0
5123a7db0f35e49827a5fa8141521404c63ec41f
5123a7db0f35e49827a5fa8141521404c63ec41f
```

Local branch matched the remote exactly at review time, so the review applies to what is in the PR.

Also checked by hand across all 20 files: no credentials, tokens, private keys, personal data, real printer identifiers, or non-synthetic configuration. No workflow files, no binaries, no application code — consistent with what `verification.md` claims about the staged package.

Line lengths in the schema (context for the style note in [04-maintainability.md](04-maintainability.md)): longest line is 581 characters (`State` enum, line 199); `ToolchainManifest.required` at line 52 is 331.

---

## What this review did not check

Stated plainly, in the spirit of the PR's own verification record:

- **No product behaviour was tested**, because none exists. Every finding concerns contracts and tooling.
- **No printer, firmware, slicer, network service, or model provider was contacted.** I did not launch OrcaSlicer or verify the recorded EXE/DLL hashes against the installed binary.
- **The GitHub-side claims in `verification.md` were partially checked.** I confirmed PR #14 is open, unmerged, targets `main` from `design/1-phase-0`, and that the head SHA matches. I did not re-verify the repository ID, the twelve linked issues, the six milestones, or the branch-protection state.
- **The upstream documentation citations were not re-read.** The Orca, Klipper, and Moonraker claims in `inventory-and-capabilities.md` and `architecture.md` are taken at face value; the Moonraker operation allowlist in particular deserves a second reviewer who knows that API.
- **No judgement is offered on whether the proposed design is the right product.** This is a code and contract review.
- **The `Path` filesystem behaviour was verified only on this Windows 11 host.** Behaviour on other Windows versions, on network shares, and on Linux/macOS (where these names are ordinary files) will differ — which is itself part of why S1 matters for a cross-platform ambition.
