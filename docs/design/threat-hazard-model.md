# Threat and Hazard Model

Status: proposed controls, not an implemented or certified safety system. Owner review is required before implementation and before each later hardware-specific experimental policy.

## Assets, Actors, and Boundaries

Assets: human safety, printer/hardware, original configuration and recoverability, approval integrity, household images, credentials, evidence provenance, and experiment conclusions. Adversaries include malicious imported configurations/images/model output, compromised dependencies/plugins/providers, hostile PR content, and a compromised low-trust worker. Accidental failures include wrong printer identity, drift, mislabeling, stale review, disk exhaustion, outages and interruption.

Trust boundaries: imported bytes -> parser; captures -> decoder/model; untrusted model -> deterministic policy; policy -> restricted staging; private store -> public/cloud export; automation -> authenticated human approval; worker -> OS/network/device denial; optional observation gateway -> Moonraker. Host administrator compromise can defeat local controls and is a residual risk; a hash chain does not remove that risk.

Severity below describes potential consequence before controls: critical = serious injury/fire/unsafe machinery operation; high = major privacy/integrity/recovery loss; medium = misleading experiments or wasted resources. Likelihood is not estimated without deployment evidence.

| ID | Threat or hazardous sequence | Severity | Proposed prevention/detection and fail state | Evidence needed; residual risk |
| --- | --- | --- | --- | --- |
| H01 | Model/plugin/CLI reaches control route, device, socket or printer hook | Critical | No printer control implementation; OS/network/device isolation; independent gateway deny-by-default; A01/A02 | Adversarial worker bypass tests against fake endpoints. Host admin or changed network can defeat controls |
| H02 | Upload triggers queue/event automation even without explicit start | Critical | No upload capability, local export only; no printer/cloud-sync destination; A01 | Verify egress and exported path controls. Human can import into external automation outside Rookery |
| H03 | Safe-looking preset diff hides dangerous startup/end commands or dynamic macros | Critical | Review complete raw artifact, reachable static macro graph, hardware bounds and provenance; unknown dynamic behavior blocks; A08 | Human machine-specific review remains necessary; static analysis cannot prove arbitrary macros safe |
| H04 | Proposed changes weaken thermal/motion protections or change pins/current/kinematics | Critical | Protected fields and macros remain audit-only; positive hardware-specific allowlist; no generic text patch path; A08 | Units, aliases and version drift must be tested; unsupported settings fail closed |
| H05 | Paused job mistaken for idle; edited files confused with loaded configuration | Critical | No live writer; separate activation observation; paused/unknown never idle; A13 | No software claim of physical quiescence based solely on files/API state |
| H06 | Kill/restart/automatic rollback described as emergency safety | Critical | No such route; no MVP stop-only subsystem; manual independent emergency arrangement and presence outside software scope; A20 | MCU/watchdog behavior does not cover every hardware fault |
| H07 | Traversal, archive bomb, duplicate keys, reparse/hardlink escape or TOCTOU leaks/overwrites files | High | Root handles, limits, lossless strict parsing, closure rehash, immutable staging; A03/A04/A06 | Platform semantics and race tests required on supported OS/filesystems |
| H08 | Secrets/EXIF/household photos leak into Git, logs, cloud requests or CI artifacts | High | Separate private store; sanitized derivatives with preview; specific opt-in; credential broker; bounded retention; A07/A15 | Automated redaction may miss image content; explicit review still required |
| H09 | Backup counts multiple folders on same disk, sanitized Git diff, or upload ACK as recovery | High | Three verified full-fidelity copies, distinct documented failure domains, off-device, read-back and temporary restore; A05 | Independence needs physical/provider evidence; offline media may have no off-site protection |
| H10 | Corruption/disk-full/interruption destroys last verified snapshot or yields partial candidate | High | Append-only objects, previous snapshots retained, publication journal, quarantine, no destructive sync; A05/A06 | Filesystem durability varies; restore drills and key recovery remain necessary |
| H11 | Forged model approval, stale review, changed artifact under version label, replayed authorization | High | Digest-bound scope, human authentication, expiry/revocation/reviewer/check validation, export rehash; A09/A16 | Host compromise or stolen human credentials remain outside model/schema guarantees |
| H12 | Prompt injection from comments/images/logs/provider or imported chat response asks for tools/control | High | Data-only context, tool-free model, schema gate, evidence/key references, protected policy; A07 | Malicious advice may remain plausible; human and deterministic checks needed |
| H13 | Missing bottom view, wrong run/scale, blur or AI inference mistaken for metrology/root cause | Medium | Six-view identity/coverage checks; manual/calibrated measurements; observation/hypothesis separation; abstention; A10/A11 | Images cannot establish heater safety, strength or a unique cause |
| H14 | Model/provider/preprocessing changes or moisture/maintenance drift bias comparison | Medium | Freeze reviewer/rubric; preserve control history and repeats; rebaseline, no significance claims from screening; A14/A18 | Physical variability and confounding remain; human-labeled evaluation needed |
| H15 | Dependency or PR executes with printer secrets/network or changes policy/approval logic | Critical | Fixture-only runners; no printer-host runners, secret-bearing PR jobs or unreviewed hooks; pinned Actions; reviewed dependency provenance; A20 | CI platform/supply-chain compromise remains possible |
| H16 | Missing API fields or stale observations silently interpreted as valid activation | High | Explicit unknowns, monotonic/session plus wall-clock provenance, freshness bounds, manual-check state; A02/A13 | Observations cannot prove all runtime behavior; adapter version must match |
| H17 | Endless retries/repeated rejected proposals consume resources or invent success | Medium | Request/storage/token/run budgets, failure events, duplicate proposal detection and explicit retest; A12/A18 | Bounds require product tests and hardware-specific manual limits |

## Review Gates

No application code in Phase 0 means no implemented access-control assurance. B02 proves the fixture importer boundary; B06 proves the slicer boundary before executing any binary; B09 separately proves the observation gateway. Passing mocks alone does not satisfy these gates. Tests use fake network services, disposable filesystems, isolated workers and captured traffic/device denial logs, never a live printer.

Before a physical experiment outside this project session, a human must establish a suitable baseline, reviewed ranges and stop conditions, be present, and have an independently validated emergency arrangement. Rookery does not provide or certify that arrangement and cannot restart, resume or recover machinery.

Any expansion of authority (upload, live file deployment, stop-only monitoring, new gateway method, macro mutation, privileged UI/plugin) requires a new reviewed threat/hazard revision and acceptance evidence. Phase 5 is not preauthorization.
