"""Offline Phase 0 document/schema checks, not product or hardware tests."""

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

# datetime.fromisoformat only accepts a trailing "Z" from 3.11; on 3.10 every timestamp
# would be reported as an invalid format rather than as an unsupported interpreter.
if sys.version_info < (3, 11):
    raise SystemExit(
        "check_design.py requires Python 3.11 or newer "
        "(datetime.fromisoformat must accept a 'Z' suffix); running "
        f"{sys.version_info.major}.{sys.version_info.minor}"
    )

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import best_match
from markdown_it import MarkdownIt
from referencing import Registry
from referencing.exceptions import NoSuchResource


ROOT = Path(__file__).resolve().parents[1]
KINDS = {
    "PrinterIdentity", "SourceSnapshot", "BackupReceipt", "CalibrationDefinition",
    "ExperimentManifest", "EvidenceBundle", "DiagnosticReport", "ChangeProposal",
    "ApprovalRecord", "ActivationObservation", "ExperimentResult",
}
PROMPT_HASH = "1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e"
EXAMPLE_DIGEST = "sha256:" + "7" * 64


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Non-finite JSON constant: {value}")


def finite_float(text):
    value = float(text)
    require(math.isfinite(value), "JSON number exceeds finite float range")
    return value


def parse(text):
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=finite_float)


def no_remote_schema(uri):
    raise NoSuchResource(ref=uri)


FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=ValueError)
def utc_datetime(value):
    # The wire format intentionally uses a UTC subset supported by datetime.
    if not isinstance(value, str):
        return True
    # The regex pins the offset to UTC, so only the calendar remains to be checked.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value):
        return False
    # fromisoformat raises ValueError on impossible dates and on leap seconds; the
    # raises=ValueError declaration above turns that into a format failure.
    datetime.fromisoformat(value)
    return True


def make_validator(schema):
    return Draft202012Validator(schema, format_checker=FORMATS, registry=Registry(retrieve=no_remote_schema))


def subschema(schema, name):
    """Validate one named $def in isolation, without inheriting the document's $id."""
    branch = {key: value for key, value in schema.items() if key != "$id"}
    branch["oneOf"] = [{"$ref": f"#/$defs/{name}"}]
    return branch


def check_refs(node, schema):
    count = 0
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            require(ref.startswith("#/$defs/"), f"Non-local schema reference: {ref}")
            require(ref.removeprefix("#/$defs/") in schema["$defs"], f"Missing reference: {ref}")
            count += 1
        for value in node.values():
            count += check_refs(value, schema)
    elif isinstance(node, list):
        for value in node:
            count += check_refs(value, schema)
    return count


def explain(schema, value):
    """Name the offending field. The root oneOf has no discriminator, so dispatch on kind first."""
    kind = value.get("kind") if isinstance(value, dict) else None
    if kind not in KINDS:
        return "unknown record kind"
    failure = best_match(make_validator(subschema(schema, kind)).iter_errors(value))
    if failure is None:
        return "valid against its own kind but not against the record union"
    location = "/".join(str(part) for part in failure.absolute_path) or "(record root)"
    return f"{location}: {failure.message}"


def check_examples(schema, examples):
    validator = make_validator(schema)
    require({item["kind"] for item in examples} == KINDS, "Eleven record kinds must have examples")
    require(len(examples) == len(KINDS), "Exactly one example per record kind is expected")
    by_kind = {item["kind"]: item for item in examples}
    positive = 0
    negative = 0

    def accept(value):
        nonlocal positive
        require(validator.is_valid(value),
                f"Invalid positive shape {value.get('kind')}: {explain(schema, value)}")
        positive += 1

    def reject(value, label):
        nonlocal negative
        require(not validator.is_valid(value), f"Unexpectedly accepted: {label}")
        negative += 1

    for example in examples:
        accept(example)
        for field, value in [("schema_version", "999.0.0"), ("unexpected", "deny"), ("created_at", "2026-02-30T12:00:00Z")]:
            changed = deepcopy(example)
            changed[field] = value
            reject(changed, f"{example['kind']} invalid {field}")
        changed = deepcopy(example)
        del changed["id"]
        reject(changed, f"{example['kind']} missing id")

    changed = deepcopy(by_kind["PrinterIdentity"])
    changed["validation_scope"] = "klipper_observed"
    reject(changed, "unknown firmware claiming Klipper observation")
    for scope in ["klipper_static", "klipper_observed"]:
        changed = deepcopy(by_kind["PrinterIdentity"])
        changed.update(firmware="klipper", validation_scope=scope, identity_evidence_digests=[])
        reject(changed, f"{scope} without identity evidence")
    changed = deepcopy(by_kind["PrinterIdentity"])
    changed.update(firmware="klipper", validation_scope="klipper_observed",
                   identity_evidence_digests=[EXAMPLE_DIGEST], hardware_digest=None)
    reject(changed, "klipper_observed without a declared hardware reference")
    changed = deepcopy(by_kind["PrinterIdentity"])
    changed.update(firmware="klipper", validation_scope="klipper_observed",
                   identity_evidence_digests=[EXAMPLE_DIGEST], hardware_digest=EXAMPLE_DIGEST)
    accept(changed)

    # Traversal and absolute/UNC/stream escapes, then Windows-specific aliasing: reserved
    # device names in any case, trailing dot or space, empty segment, directory reference.
    for path in ["../outside.json", "nested/../../outside.json", "/absolute.json", "C:/outside.json",
                 "file.json:secret", "..\\outside.json",
                 "NUL", "CON", "PRN", "AUX", "COM1", "LPT1.json", "nul.txt", "CoN",
                 "aux/config.cfg", "dir/NUL",
                 "process.json.", "process.json ", "dir/", "a//b.json", "a /b.json", "a./b.json",
                 "process.json\n", "process.json\r\n", "dir/\nfile.json"]:
        changed = deepcopy(by_kind["SourceSnapshot"])
        changed["files"][0]["path"] = path
        reject(changed, f"escaping or aliasing path {path}")
    for path in ["console.json", "company.cfg", "nullable.json", "com10.cfg", "printer.cfg.bak"]:
        changed = deepcopy(by_kind["SourceSnapshot"])
        changed["files"][0]["path"] = path
        accept(changed)

    changed = deepcopy(by_kind["SourceSnapshot"])
    changed["files"] = [changed["files"][0], deepcopy(changed["files"][0])]
    reject(changed, "snapshot listing one file entry twice")

    receipt = deepcopy(by_kind["BackupReceipt"])
    receipt["status"] = "verified"
    reject(receipt, "verified backup without read-back/restore")
    receipt.update(readback_digest=receipt["archive_digest"], restore_manifest_digest=receipt["snapshot_digest"],
                   verified_at=receipt["created_at"], verification_method="readback_and_temporary_restore", failures=[])
    accept(receipt)

    complete = deepcopy(by_kind["EvidenceBundle"])
    complete.update(coverage="complete", bottom_cooled_and_removed_observed=True, issues=[])
    reject(complete, "complete coverage with one view")
    template = complete["captures"][0]
    complete["captures"] = []
    for view in ["front", "rear", "left", "right", "top", "bottom"]:
        capture = deepcopy(template)
        capture.update(id=f"synthetic-{view}", view=view, quality_issues=[])
        complete["captures"].append(capture)
    accept(complete)
    changed = deepcopy(complete)
    changed["captures"][0]["quality_issues"] = ["blur"]
    reject(changed, "complete coverage with a flagged capture")
    changed = deepcopy(complete)
    changed["captures"][-1]["view"] = "front"
    reject(changed, "six labels without bottom")
    changed = deepcopy(complete)
    changed["captures"][0]["source_video_digest"] = changed["artifact_digest"]
    reject(changed, "video frame without timestamp")
    changed = deepcopy(complete)
    changed["captures"].append(deepcopy(changed["captures"][0]))
    reject(changed, "bundle listing one capture twice")

    changed = deepcopy(by_kind["DiagnosticReport"])
    changed["outcome"] = "propose_bounded_change"
    reject(changed, "proposal outcome without proposal reference")
    changed = deepcopy(by_kind["ChangeProposal"])
    second = deepcopy(changed["changes"][0])
    second.update(key="a_second_fictional_parameter", current_value=3, proposed_value=4)
    changed["changes"].append(second)
    reject(changed, "two independent changes")
    changed = deepcopy(by_kind["ChangeProposal"])
    changed["changes"][0]["domain"] = "klipper_audit_only"
    reject(changed, "bounded slicer proposal with Klipper domain")
    for value in [None, "500", True]:
        changed = deepcopy(by_kind["ChangeProposal"])
        changed["changes"][0]["proposed_value"] = value
        reject(changed, f"proposed value {value!r} disagreeing with the current value type")
    for current, proposed in [("210", 500), (True, 1)]:
        changed = deepcopy(by_kind["ChangeProposal"])
        changed["changes"][0].update(current_value=current, proposed_value=proposed)
        reject(changed, f"type mismatch from {type(current).__name__} to {type(proposed).__name__}")
        changed["changes"][0]["proposed_value"] = current
        accept(changed)
    # A null current_value records a key absent from the source, so type agreement does not
    # apply; only the non-null rule stops the proposal from meaning "delete this key".
    changed = deepcopy(by_kind["ChangeProposal"])
    changed["changes"][0].update(current_value=None, proposed_value=None)
    reject(changed, "null proposed value against an absent source key")
    changed = deepcopy(by_kind["ChangeProposal"])
    changed["changes"][0].update(current_value=None, proposed_value=2)
    accept(changed)

    changed = deepcopy(by_kind["CalibrationDefinition"])
    del changed["ranges"][0]["domain"]
    reject(changed, "reviewed range without a domain to bind it to")

    for field in ["source_digest", "candidate_digest", "proposal_digest", "raw_gcode_digest", "toolchain_digest", "prompt_digest", "provider"]:
        changed = deepcopy(by_kind["ApprovalRecord"])
        changed["bindings"][field] = None
        reject(changed, f"candidate approval missing {field}")
    changed = deepcopy(by_kind["ApprovalRecord"])
    changed["authentication_mode"] = "github_human"
    reject(changed, "GitHub approval without repository/review evidence")
    baseline = deepcopy(by_kind["ApprovalRecord"])
    baseline.update(scope="baseline_package_review", risk_scope="baseline_review")
    baseline["bindings"].update(candidate_digest=None, proposal_digest=None, prompt_digest=None, provider=None)
    accept(baseline)
    changed = deepcopy(baseline)
    changed["bindings"]["candidate_digest"] = changed["bindings"]["source_digest"]
    reject(changed, "baseline approval with candidate content")
    changed = deepcopy(baseline)
    changed["bindings"]["proposal_digest"] = changed["bindings"]["source_digest"]
    reject(changed, "baseline approval carrying a change proposal")
    changed = deepcopy(by_kind["ActivationObservation"])
    changed.update(verification="matched", firmware_scope="klipper_observed")
    reject(changed, "matched Klipper activation without loaded/runtime evidence")
    changed = deepcopy(by_kind["ExperimentResult"])
    changed["recommendation"] = "promoted"
    reject(changed, "promotion with no candidate or evidence")

    for text in ['{"id":1,"id":2}', '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}']:
        try:
            parse(text)
        except ValueError:
            negative += 1
        else:
            raise ValueError("Non-strict JSON accepted")
    return positive, negative


def check_supplemental(schema, examples):
    validator = make_validator(subschema(schema, "DiagnosticResponse"))
    positive = 0
    negative = 0

    def accept(value, label):
        nonlocal positive
        require(validator.is_valid(value), f"Rejected a valid model response: {label}")
        positive += 1

    def reject(value, label):
        nonlocal negative
        require(not validator.is_valid(value), f"Unexpectedly accepted: {label}")
        negative += 1

    response = {
        "outcome": "insufficient_evidence", "observations": [], "measured_values": [],
        "hypotheses": [], "counterevidence": [], "missing_information": ["No real captures"],
        "confidence_limitations": ["Synthetic shape only"], "proposal": None,
    }
    accept(response, "abstention without a proposal")
    proposal = next(item for item in examples if item["kind"] == "ChangeProposal")
    response.update(outcome="propose_bounded_change", proposal={key: value for key, value in proposal.items()
                    if key not in {"schema_version", "kind", "id", "created_at"}})
    accept(response, "bounded slicer proposal")

    changed = deepcopy(response)
    changed["proposal"]["arbitrary_script"] = "must be rejected"
    reject(changed, "model proposal carrying an unknown script field")
    changed = deepcopy(response)
    changed["created_at"] = "2026-09-12T12:00:00Z"
    reject(changed, "model response carrying application-owned metadata")

    # The model must not be able to widen its own authority. These four shapes are the
    # containment boundary between untrusted interpretation and the deterministic policy.
    changed = deepcopy(response)
    changed["proposal"]["risk"] = "elevated_proposal_only"
    reject(changed, "model escalating its own proposal risk")
    changed = deepcopy(response)
    changed["proposal"]["changes"][0]["domain"] = "klipper_audit_only"
    reject(changed, "model proposing a Klipper domain change")
    changed = deepcopy(response)
    changed["proposal"]["risk"] = "elevated_proposal_only"
    changed["proposal"]["changes"][0]["domain"] = "klipper_audit_only"
    reject(changed, "model reaching a Klipper domain through an elevated risk level")
    for outcome in ["no_change", "insufficient_evidence", "manual_hardware_check"]:
        changed = deepcopy(response)
        changed["outcome"] = outcome
        reject(changed, f"model attaching a proposal to a {outcome} outcome")

    digest = "sha256:" + "a" * 64
    toolchain_validator = make_validator(subschema(schema, "ToolchainManifest"))
    toolchain = {key: digest for key in schema["$defs"]["ToolchainManifest"]["required"] if key.endswith("_digest")}
    toolchain.update(slicer_version="synthetic", binary_dependency_digests=[], os="fictional", architecture="fictional", argv=[])
    require(toolchain_validator.is_valid(toolchain), "Rejected a valid toolchain manifest")
    positive += 1
    changed = deepcopy(toolchain)
    del changed["executable_digest"]
    require(not toolchain_validator.is_valid(changed), "Toolchain accepted missing binary identity")
    negative += 1
    return positive, negative


def markdown_targets(text):
    """Read rendered Markdown links/images without treating code examples as links."""
    def targets(tokens):
        for token in tokens:
            if token.type == "link_open":
                yield token.attrGet("href")
            elif token.type == "image":
                yield token.attrGet("src")
            if token.children:
                yield from targets(token.children)

    yield from targets(MarkdownIt("commonmark").enable("table").parse(text))


def check_links(root=ROOT):
    count = 0
    # The supplied prompt is byte-frozen and is never edited to satisfy a link check.
    files = sorted(path for path in root.rglob("*.md")
                   if path.name != "ROOKERY_ASTRA_BUILD_PROMPT.md"
                   and not any(part.startswith(".") for part in path.relative_to(root).parts))
    for path in files:
        for target in markdown_targets(path.read_text(encoding="utf-8")):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            relative = path.relative_to(root)
            target_path = (path.parent / unquote(url.path)).resolve()
            require(target_path.is_relative_to(root), f"Link escapes repository: {relative}: {target}")
            # A directory target is a legitimate link; require existence, not a regular file.
            require(target_path.exists(), f"Missing link: {relative}: {target}")
            count += 1
    return count


def main():
    schema = parse((ROOT / "schemas/0.1.0/rookery.schema.json").read_text(encoding="utf-8"))
    examples = parse((ROOT / "schemas/0.1.0/examples.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    require("ApplyReceipt" not in schema["$defs"], "Live ApplyReceipt is out of scope")
    refs = check_refs(schema, schema)
    positive, negative = check_examples(schema, examples)
    extra_positive, extra_negative = check_supplemental(schema, examples)
    positive += extra_positive
    negative += extra_negative
    prompt_digest = hashlib.sha256((ROOT / "ROOKERY_ASTRA_BUILD_PROMPT.md").read_bytes()).hexdigest()
    require(prompt_digest == PROMPT_HASH, "Owner prompt bytes changed")
    links = check_links()
    print(f"PASS: Draft 2020-12 schema, {refs} local references, {positive} positive shapes, {negative} negative probes, {links} local links, original prompt SHA-256")
    print("Design checks only. No product policy, worker isolation, slicer runtime, live printer, restore destination, or physical-quality test was executed.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        # An expected check failure is a result, not a crash; report it without a traceback.
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
