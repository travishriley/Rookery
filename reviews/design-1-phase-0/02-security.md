# Code Security

There is one executable file in this PR (`tools/check_design.py`, 253 lines) and it is a local, offline validator. It opens no sockets, spawns no subprocesses, writes no files, and evaluates no input. Threat surface is small and handled well. The strict-parsing work in particular is better than most production code.

The findings below are about **coverage** — whether the checker will keep enforcing the security properties the schema encodes once other people start editing the schema.

---

## <a id="s5"></a>S5 — Medium — the model-containment invariant has no negative probe

**Location:** `tools/check_design.py:190-217` (`check_supplemental`)

The `DiagnosticResponse` contract is the trust boundary between an untrusted vision model and the deterministic policy engine. It encodes the most important security property in the design: *the model cannot escalate its own authority*. Specifically (`rookery.schema.json:340`):

```json
"if":   {"properties": {"outcome": {"const": "propose_bounded_change"}}},
"then": {"properties": {"proposal": {"type": "object",
                                     "properties": {"risk": {"const": "bounded_slicer"}}}}},
"else": {"properties": {"proposal": {"type": "null"}}}
```

Forcing `risk: bounded_slicer` chains into `ProposalPayload`'s conditional, which restricts `domain` to the three Orca domains — so the model can never reach `klipper_audit_only`.

**The rule works.** I tried six attack shapes and every one was rejected (`evidence/probe_model_containment.py`):

```
ACCEPTED      baseline: bounded_slicer orca_process proposal
rejected(ok)  model escalates risk -> elevated_proposal_only
rejected(ok)  model proposes a KLIPPER change via elevated risk
rejected(ok)  model proposes klipper domain under bounded_slicer
rejected(ok)  outcome=no_change but proposal still attached
rejected(ok)  model returns two changes
```

**But none of them is probed.** `check_supplemental` tests exactly three things: an unknown `arbitrary_script` field, an application-owned `created_at` field, and a missing `executable_digest`. The string `elevated_proposal_only` does not appear anywhere in `check_design.py`.

The consequence is demonstrable. I copied the repo to a temp directory, deleted the `if`/`then` from `DiagnosticResponse`, and re-ran the checker (`evidence/mutation_test.py`):

```
  checker result   mutation
--------------------------------------------------------------------------------------------------
            PASS   DELETE DiagnosticResponse if/then (model may escalate risk)  <-- STILL PASSES
            FAIL   DELETE ProposalPayload if/then (model may propose klipper_audit_only domain)
            FAIL   WIDEN Path pattern to allow traversal
            FAIL   DELETE ActivationObservation matched+klipper_observed evidence rule
            FAIL   DELETE BackupReceipt verified-status if/then
```

Four of five safety rules are covered by the existing 76 probes. The fifth — the one guarding H12 / A07, prompt injection and model containment — can be deleted silently and `check_design.py` still prints `PASS`. Since this checker is slated to become the required `design-contracts` CI check (B01, `policies.md`), that hole would become permanent.

**Suggested fix** — three probes in `check_supplemental`, after the existing `arbitrary_script` check:

```python
escalated = deepcopy(response)
escalated["proposal"]["risk"] = "elevated_proposal_only"
require(not validator.is_valid(escalated), "Model escalated its own proposal risk")

klipper = deepcopy(response)
klipper["proposal"]["changes"][0]["domain"] = "klipper_audit_only"
require(not validator.is_valid(klipper), "Model proposed a Klipper domain change")

attached = deepcopy(response)
attached["outcome"] = "no_change"
require(not validator.is_valid(attached), "Model attached a proposal to a no_change outcome")
```

(and bump the negative count — see [M1](04-maintainability.md#m1), which is why that count should not be hardcoded).

---

## <a id="s6"></a>S6 — Medium — `SourceSnapshot.files` and `EvidenceBundle.captures` have no uniqueness constraint

**Location:** `schemas/0.1.0/rookery.schema.json:220`, `:283`

```json
"files":    {"type": "array", "items": {"$ref": "#/$defs/FileEntry"}, "minItems": 1, "maxItems": 10000},
"captures": {"type": "array", "items": {"$ref": "#/$defs/Capture"},   "maxItems": 1000},
```

Neither has `uniqueItems`. Verified schema-valid:

- Two `FileEntry` records with identical `root_id` and `path` but **different `digest`** — an ambiguous snapshot. Which bytes does restore write?
- Two `FileEntry` records for `process.json` and `process.json.` — the same Windows file (see [S1](01-safety.md#s1)).
- Two `Capture` records with an identical `id`. `Finding.capture_ids` references captures by `id`, so a duplicate makes every diagnostic citation ambiguous — which undercuts R10 and the "cite the supplied image/frame IDs" instruction in the diagnostic prompt.

This one is a small omission rather than an oversight of principle: `Digests` at line 22 already uses `"uniqueItems": true`, so the idiom is clearly known. It just was not applied to the two arrays where identity actually matters.

**Suggested fix:** add `"uniqueItems": true` to both (it catches the fully-identical case cheaply), and add to `data-contracts.md` the runtime invariants that `(root_id, path)` is unique within a `SourceSnapshot` and `capture.id` is unique within an `EvidenceBundle` — `uniqueItems` alone will not catch same-path-different-digest.

---

## <a id="s7"></a>S7 — Low — `.gitignore` protects directory names but not evidence file types

**Location:** `.gitignore`

```
private/
records/
backups/
staging/
```

H08 ranks "Secrets/EXIF/household photos leak into Git" as a High-severity threat, and `policies.md` is emphatic that original photographs stay in an access-controlled private store. The current ignores only help if the user places files in exactly those four directories. A photo dropped at the repo root as `IMG_0001.jpg`, or a real `printer.cfg` copied in for a quick look, is not ignored and will show up in `git add -A`.

There are no such files in the repo today, so this is purely preventive — but it is a two-line fix that matches the project's own threat model.

**Suggested fix:**

```gitignore
# Evidence and machine artifacts are private by default regardless of location (H08).
*.jpg
*.jpeg
*.png
*.mp4
*.mov
*.gcode
*.3mf
*.cfg
*.sqlite
*.sqlite-*
```

Add `!docs/**/*.png` or similar exceptions if the docs ever need images. Worth noting in `policies.md` that this is a secondary safeguard, consistent with the comment already above the `private/` block.

---

## <a id="s8"></a>S8 — Low — `PROMPT_HASH` is a co-located tripwire, not an integrity control

**Location:** `tools/check_design.py:22`, `:245-246`

```python
PROMPT_HASH = "1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e"
...
require(prompt_digest == PROMPT_HASH, "Owner prompt bytes changed")
```

I verified this works and that the byte-preservation machinery around it is correct:

```
working tree sha256: 1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e   (matches)
no-filters blob: 80fff9e81564bd456dc2dae1e7e01b6e1ed1fc5a
index blob     : 80fff9e81564bd456dc2dae1e7e01b6e1ed1fc5a   MATCH
git check-attr: ROOKERY_ASTRA_BUILD_PROMPT.md -> text: unset, eol: lf
```

The `.gitattributes` `-text` override is correctly ordered after `*.md text eol=lf` (later rules win per attribute) and the file survives the checkout round trip byte-for-byte. Good.

The only note: because the expected hash lives in the same tree as the file it protects, a single commit can change both, and the check still passes. It detects accidental drift — an editor rewriting line endings, a careless edit — not deliberate modification. `verification.md` and the PR body both list "original prompt SHA-256" alongside genuinely adversarial checks, which slightly overstates it.

**Suggested fix:** one clause in `verification.md` noting the hash detects accidental modification only, since an authorised committer can update both. If stronger assurance is wanted later, the hash could be recorded in the design issue or a signed tag rather than the working tree.

---

## What I checked and found correct

- **Remote `$ref` retrieval is blocked.** `no_remote_schema` raises `NoSuchResource` for any non-local reference, and `check_refs` independently asserts every `$ref` starts with `#/$defs/` and resolves. That closes both SSRF-via-schema and the schema supply-chain path. This is the right call and is often missed.
- **Strict JSON parsing.** `unique_object` rejects duplicate keys, `reject_constant` rejects `NaN`/`Infinity`/`-Infinity`, and `finite_float` rejects overflow-to-infinity literals like `1e999`. All four are probed at `check_design.py:180`. Duplicate-key handling in particular is the right instinct for a config-parsing project.
- **`unevaluatedProperties: false` on every record type**, which is the correct Draft 2020-12 idiom for closing a schema composed with `allOf` — `additionalProperties: false` would have broken composition here.
- **`Id` is ASCII-only** (`^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$`), which sidesteps Unicode confusables and normalisation ambiguity in identifiers. Verified full-width `ＡＢＣ` is rejected and the 128-character bound holds.
- **The model-facing response type is deliberately separate from the application-owned record type**, and `DiagnosticResponse.additionalProperties: false` stops the model from supplying its own `id`, `created_at` or digests. The rationale in `data-contracts.md` ("avoids asking a model to invent or self-hash records") is exactly right.
- **No credentials, tokens, private keys or personal data** in any of the 20 files. I checked the full diff.
- **Bounded array and string sizes throughout** (`maxItems`, `maxLength` on every collection), which limits memory amplification from a hostile document.
