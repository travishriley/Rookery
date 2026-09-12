# Summary and Verdict

**Approve with changes.** This is unusually disciplined work. The safety posture is coherent, the documents are honest about what was and was not executed, and `tools/check_design.py` genuinely validates the artifacts rather than asserting success. I found no defect that blocks merging a *design* PR.

I did find gaps that will become real defects the moment B01–B06 write code against these contracts. Four of them are worth fixing while the schema is still cheap to change.

## Findings

Severity is "consequence if this contract is implemented as written", not "consequence today". Nothing in this PR touches hardware.

| # | Severity | Area | Finding | Location |
| --- | --- | --- | --- | --- |
| [S1](01-safety.md#s1) | High | Safety | `Path` accepts Windows device names (`NUL`, `CON`, `COM1`) and trailing-dot/space aliases; a restore can silently discard or overwrite printer config | `rookery.schema.json:27` |
| [S2](01-safety.md#s2) | High | Safety | A reviewed `Range` cannot be reliably bound to a proposed `Change`: no `domain`, no unit agreement, no `minimum <= maximum` | `rookery.schema.json:132,187` |
| [S3](01-safety.md#s3) | Medium | Safety | `proposed_value`/`current_value` are unconstrained `Scalar` — a temperature may be `null`, `"500"`, `true`, or `1e308` | `rookery.schema.json:28,187` |
| [S4](01-safety.md#s4) | Medium | Safety | `PrinterIdentity` may claim `klipper_static`/`klipper_observed` with zero identity evidence | `rookery.schema.json:201` |
| [S5](02-security.md#s5) | Medium | Security | The model-containment invariant has no negative probe — mutation test shows the checker still prints PASS after it is deleted | `check_design.py:190` |
| [S6](02-security.md#s6) | Medium | Security | `SourceSnapshot.files` and `EvidenceBundle.captures` have no uniqueness constraint | `rookery.schema.json:220,283` |
| [S7](02-security.md#s7) | Low | Security | `.gitignore` protects directory names but not evidence file types named in H08 | `.gitignore` |
| [S8](02-security.md#s8) | Low | Security | `PROMPT_HASH` is a co-located tripwire, not an integrity control | `check_design.py:22` |
| [U1](03-usability.md#u1) | Medium | Usability | Validation failures print a raw traceback and "not valid under any of the given schemas" without naming the field | `check_design.py:96,235` |
| [U2](03-usability.md#u2) | Medium | Usability | No minimum Python version is declared or enforced; on 3.10 every record fails with a misleading message | `check_design.py` |
| [U3](03-usability.md#u3) | Low | Usability | README never tells the reader to install `requirements-design.txt` | `README.md:26` |
| [M1](04-maintainability.md#m1) | Low | Maint. | `check_supplemental` returns a hardcoded `(3, 3)` while the PR advertises exact probe counts as evidence | `check_design.py:217` |
| [M2](04-maintainability.md#m2) | Low | Maint. | `toolchain_validator` silently omits `format_checker` | `check_design.py:211` |
| [M3](04-maintainability.md#m3) | Low | Maint. | Derived schemas built by dict-spread keep the same `$id` | `check_design.py:191,210` |
| [M4](04-maintainability.md#m4) | Low | Maint. | `utc_datetime`'s final comparison is tautological; the real check is the swallowed `ValueError` | `check_design.py:66` |
| [M5](04-maintainability.md#m5) | Low | Maint. | `changes *= 2` probe is mislabeled — it duplicates one change, it does not test two independent ones | `check_design.py:154` |
| [M6](04-maintainability.md#m6) | Low | Maint. | `check_links` skips `prompts/` and scans fenced code blocks | `check_design.py:220` |
| [M7](04-maintainability.md#m7) | Low | Maint. | `ApprovalRecord.bindings` has no proposal digest; the report→proposal→approval chain joins only via an opaque `review_packet_digest` | `rookery.schema.json:63,91` |

## What to fix first

1. **S1** — one regex change plus negative probes. It is the cheapest fix here and it protects the exact-byte restore guarantee that gates every candidate write.
2. **S5** — three added probes. Without them the schema rule that stops an untrusted model from escalating its own proposal risk is unenforced by CI forever.
3. **S2 / S3** — these shape B06's policy engine. Deciding now how a reviewed bound binds to a proposed change is far cheaper than retrofitting it after `ChangeProposal` records exist.
4. **U1 / U2** — small, and they decide whether the next person can actually run the checker.

S4, S6, S7, S8 and all M-items are cleanup; batch them whenever convenient.

## Two notes on scope

**The empty allowlist is doing a lot of work.** ADR-006 and requirements.md are explicit that the parameter allowlist is empty, so no numeric bound is authorized today and S2/S3 cannot currently harm a printer. That is the right default. But it also means the *contract* for expressing a reviewed bound has never been exercised, and S2 shows it is underspecified. The first hardware-specific policy review will have to invent the matching rule under time pressure. Better to settle it now.

**The documents are more rigorous than the schema.** `architecture.md` commits to rejecting "absolute/UNC/device paths", "case-colliding destinations", and "duplicate/ambiguous settings". `Path` implements about half of that and `files` implements none of it. That is legitimate — the docs say these are runtime checks — but S1 and S6 are cases where JSON Schema *can* carry the constraint, and where leaving it to unwritten runtime code is a needless risk.
