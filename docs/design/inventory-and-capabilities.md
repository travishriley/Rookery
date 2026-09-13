# Inventory and Capability Evidence

Status: observed 2026-09-12; proposals explicitly identified. No printer endpoint, device, live configuration, user slicer profile, or cloud account was inspected. Public documentation was read over the internet; this session was offline with respect to machinery.

## Workspace and Repository

| Item | Evidence and result |
| --- | --- |
| Workspace | Owner-supplied Rookery directory; initially exactly `ROOKERY_ASTRA_BUILD_PROMPT.md`, 30,182 bytes; no `.git` |
| Prompt SHA-256 | `1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e` |
| Instructions | No `AGENTS.md` in workspace or checked ancestors through `C:\`; no existing code, tests, fixtures, CI, or dependency manifest |
| GitHub identity | `travishriley/Rookery`, repository ID `1367605870`, public, default branch name `main`; API initially reported empty; no issues/PRs |
| Bootstrap | Empty commit `2aa42eb` establishes `main` for a PR comparison; no design content pushed to `main` |
| Tracking | [Design issue #1](https://github.com/travishriley/Rookery/issues/1), [milestone 1](https://github.com/travishriley/Rookery/milestone/1), `design/1-phase-0` |
| Environment | Windows 11 build 26200, AMD64; Python 3.13.7; Git 2.51.1.windows.1; Node 22.13.1 observed, not selected for the product |
| Authorization | Connector metadata reports admin/push, but connector issue creation and protection read returned 403. Sandbox CLI authentication failed; host CLI authenticated through existing keyring and successfully created tracking records |
| Rules | Rulesets API returned `[]`; authenticated host CLI protection read returned 404 `Branch not protected` after bootstrap. No rules were configured or weakened |

No existing work was reverted. `.gitattributes` excludes the supplied prompt from newline conversion. Git writes needed sandbox escalation; a command-scoped `safe.directory` exception addressed sandbox/owner identity differences without changing global Git settings.

## OrcaSlicer: Local Evidence Versus Upstream

| Capability | Observed evidence | Design consequence |
| --- | --- | --- |
| Installed executable | `C:\Program Files\OrcaSlicer\orca-slicer.exe`, 303,104 bytes; not found on PATH | Installation presence is verified; invocation and runtime behavior are not |
| Version | Windows uninstall metadata identifies OrcaSlicer 2.4.2, publisher SoftFever; EXE/DLL version fields are empty | Registry version is a claim, not proof the installed binary matches upstream |
| Binary identities | EXE SHA-256 `481c9f071fdb3cda033d1677ce7a9442c41a25cbeeb42cfc808af179b4dc85c3`; DLL SHA-256 `865c231ffc3b4942c40df90d56689072218c739d62e583ee1a8357bce3a3ae27` | Both are required in any later local capability receipt |
| Plugin availability | Upstream lists nightlies or releases greater than 2.4.2 | Do not select the plugin path for the detected 2.4.2 install; do not upgrade it automatically |
| Plugin host API | Documented `orca.host` provides read access to model/plater/preset bundle | Optional future UI/export integration; no supported preset mutation assumed |
| Plugin permissions | Upstream describes interactive audit permissions, with native-code/thread/context gaps | They cannot enforce Rookery's worker isolation |
| CLI | Version 2.4.2 source contains CLI help, config loading, and slice/export paths; current wiki also documents headless operation | Fixed-argument adapter must be verified against the actual executable; current wiki flags are not automatically valid on 2.4.2 |
| GUI calibration | Guide documents specialized calibration workflows | No verified headless calibration generator. Start from a human-exported, license-reviewed existing project |

Sources: [plugin availability](https://github.com/OrcaSlicer/OrcaSlicer/wiki/plugins_getting_started), [host API](https://github.com/OrcaSlicer/OrcaSlicer/wiki/host), [audit limitations](https://github.com/OrcaSlicer/OrcaSlicer/wiki/plugin_audit_hook), [CLI documentation](https://github.com/OrcaSlicer/OrcaSlicer/wiki/cli_mode), [import/export](https://github.com/OrcaSlicer/OrcaSlicer/wiki/import_export), [calibration guide](https://github.com/OrcaSlicer/OrcaSlicer/wiki/calibration_guide).

The upstream `v2.4.2` tag resolved to `8500fcdccaa10b5099ac20d252af3a7c560046f1`. [Pinned CLI source](https://github.com/OrcaSlicer/OrcaSlicer/blob/8500fcdccaa10b5099ac20d252af3a7c560046f1/src/OrcaSlicer.cpp) has a `normative_check`-conditional rejection of post-processing. That conditional is insufficient as our access boundary; Rookery must reject hook-bearing projects before launching a worker. This is source review, not a runtime smoke test or proof of local binary equivalence.

No Orca process was launched. A printer-network/device/profile-isolated worker was not available or validated in Phase 0. The actual CLI help/flag probe remains explicitly unverified. Phase 2 must first establish disposable configuration, no printer network or devices, no live profile mounts, no cloud sync or plugin credentials, and no hooks. Then record executable/DLL hashes, version/help output, exact argv, dependency/profile inventory, timeouts, and one synthetic slice. Reject unsupported capabilities; preserve human export/import as the fallback. Do not probe by opening the normal GUI.

## Klipper and Moonraker

No supplied fixture establishes a printer model, firmware/version, host, or Moonraker installation. Nothing was discovered on the LAN. Support remains a design target, independently selectable from Orca support.

- Klipper includes, saved variables, and runtime settings require separate provenance layers. Its Jinja macros can inspect state and invoke actions at evaluation time; nested macro evaluation happens later. Static parsing must never render templates. See [template semantics](https://www.klipper3d.org/Command_Templates.html) and [configuration reference](https://www.klipper3d.org/Config_Reference.html).
- Moonraker documents `printer.info`, object listing/query, control routes, and multiple transports. Query responses may omit unknown fields without returning an error. A missing field must remain unknown. Only the narrow future boundary in [architecture](architecture.md) is proposed; no generic read-only credential is established. See [printer API](https://moonraker.readthedocs.io/en/latest/external_api/printer/) and [authentication](https://moonraker.readthedocs.io/en/latest/external_api/authorization/).
- Upload responses report whether a file was started or queued. Rookery will not upload to printer roots. See [file API](https://moonraker.readthedocs.io/en/latest/external_api/file_manager/).
- Klipper documents MCU watchdog and heater checks. This does not validate the owner's hardware or make killing a host process a complete emergency-stop arrangement. See [host-failure behavior](https://www.klipper3d.org/FAQ.html#will-the-heaters-be-left-on-if-the-raspberry-pi-crashes).

Mutable upstream pages were checked on the date above. Before shipping an adapter, pin its upstream source/version and retain a capability receipt; recheck semantics against that version. Hardware capability and effective state cannot be inferred from a web page.

## Provenance and Deferred Leads

No upstream source, model mesh, plugin, or third-party implementation was copied. Orca's installation contains `LICENSE.txt`; redistribution and model-specific licenses remain a review gate. The following owner-supplied leads are deferred discovery, not selected dependencies or verified feature claims: JusPrin, PressureAdvanceCamera, Shake&Tune, Obico, Klipper-Backup. Phase 3/4 issues must record exact revision, author/source, license and asset-level exceptions, intended use, notices, compatibility, and security review before incorporation. Public availability alone is insufficient.

Provider adapters for OpenAI, Claude, Gemini, and local vision endpoints are planned only. No API key, model, video support, consumer subscription entitlement, or provider privacy promise has been verified. No external inference was performed.

The only third-party code used locally for design verification was already installed Python tooling; none was copied or vendored. Distribution metadata inspected on 2026-09-12 reports MIT for jsonschema 4.25.1, attrs 25.3.0, jsonschema-specifications 2025.4.1, referencing 0.36.2 and rpds-py 0.27.0. Package metadata identifies upstream projects [jsonschema](https://github.com/python-jsonschema/jsonschema), [attrs](https://github.com/python-attrs/attrs), [specifications](https://github.com/python-jsonschema/jsonschema-specifications), [referencing](https://github.com/python-jsonschema/referencing), and [rpds-py](https://github.com/crate-py/rpds). Compatibility scope here is local design validation only; retain notices if redistributed and review the eventual product license/dependency tree separately. The version list is not a supply-chain hash lock or a claim to have audited native/transitive code.

The PR review follow-up also uses the already installed [markdown-it-py](https://github.com/executablebooks/markdown-it-py) 4.2.0 and its [mdurl](https://github.com/executablebooks/mdurl) 0.1.2 dependency to parse Markdown links. Their installed license files (including upstream markdown-it and node URL notices) were read and contain MIT terms. They are pinned for design tooling only; nothing was installed, copied or vendored in this follow-up. The parser reads links, references, images and code fences without fetching URLs. External URL availability, fragment existence and raw HTML links remain outside this offline check.
