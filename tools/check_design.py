"""Offline Phase 0 document/schema checks, not product or hardware tests."""

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry
from referencing.exceptions import NoSuchResource


ROOT = Path(__file__).resolve().parents[1]
KINDS = {
    "PrinterIdentity", "SourceSnapshot", "BackupReceipt", "CalibrationDefinition",
    "ExperimentManifest", "EvidenceBundle", "DiagnosticReport", "ChangeProposal",
    "ApprovalRecord", "ActivationObservation", "ExperimentResult",
}
PROMPT_HASH = "1a43def02cdd4ab169de593217dc7ca595950c18bd2991a6ddb5a4090763fa4e"


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
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value):
        return False
    return datetime.fromisoformat(value).utcoffset().total_seconds() == 0


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


def check_examples(schema, examples):
    validator = Draft202012Validator(schema, format_checker=FORMATS, registry=Registry(retrieve=no_remote_schema))
    require({item["kind"] for item in examples} == KINDS, "Eleven record kinds must have examples")
    require(len(examples) == len(KINDS), "Exactly one example per record kind is expected")
    by_kind = {item["kind"]: item for item in examples}
    positive = 0
    negative = 0

    def accept(value):
        nonlocal positive
        errors = list(validator.iter_errors(value))
        require(not errors, f"Invalid positive shape {value.get('kind')}: {[e.message for e in errors]}")
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

    for path in ["../outside.json", "nested/../../outside.json", "/absolute.json", "C:/outside.json", "file.json:secret", "..\\outside.json"]:
        changed = deepcopy(by_kind["SourceSnapshot"])
        changed["files"][0]["path"] = path
        reject(changed, f"escaping path {path}")

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

    changed = deepcopy(by_kind["DiagnosticReport"])
    changed["outcome"] = "propose_bounded_change"
    reject(changed, "proposal outcome without proposal reference")
    changed = deepcopy(by_kind["ChangeProposal"])
    changed["changes"] *= 2
    reject(changed, "two independent changes")
    changed = deepcopy(by_kind["ChangeProposal"])
    changed["changes"][0]["domain"] = "klipper_audit_only"
    reject(changed, "bounded slicer proposal with Klipper domain")

    for field in ["source_digest", "candidate_digest", "raw_gcode_digest", "toolchain_digest", "prompt_digest", "provider"]:
        changed = deepcopy(by_kind["ApprovalRecord"])
        changed["bindings"][field] = None
        reject(changed, f"candidate approval missing {field}")
    changed = deepcopy(by_kind["ApprovalRecord"])
    changed["authentication_mode"] = "github_human"
    reject(changed, "GitHub approval without repository/review evidence")
    baseline = deepcopy(by_kind["ApprovalRecord"])
    baseline.update(scope="baseline_package_review", risk_scope="baseline_review")
    baseline["bindings"].update(candidate_digest=None, prompt_digest=None, provider=None)
    accept(baseline)
    baseline["bindings"]["candidate_digest"] = baseline["bindings"]["source_digest"]
    reject(baseline, "baseline approval with candidate content")
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
    response_schema = {**schema, "oneOf": [{"$ref": "#/$defs/DiagnosticResponse"}]}
    validator = Draft202012Validator(response_schema, format_checker=FORMATS, registry=Registry(retrieve=no_remote_schema))
    response = {
        "outcome": "insufficient_evidence", "observations": [], "measured_values": [],
        "hypotheses": [], "counterevidence": [], "missing_information": ["No real captures"],
        "confidence_limitations": ["Synthetic shape only"], "proposal": None,
    }
    validator.validate(response)
    proposal = next(item for item in examples if item["kind"] == "ChangeProposal")
    response.update(outcome="propose_bounded_change", proposal={key: value for key, value in proposal.items()
                    if key not in {"schema_version", "kind", "id", "created_at"}})
    validator.validate(response)
    response["proposal"]["arbitrary_script"] = "must be rejected"
    require(not validator.is_valid(response), "Model proposal accepted an unknown script field")
    del response["proposal"]["arbitrary_script"]
    response["created_at"] = "2026-09-12T12:00:00Z"
    require(not validator.is_valid(response), "Model response accepted application-owned metadata")

    digest = "sha256:" + "a" * 64
    toolchain_schema = {**schema, "oneOf": [{"$ref": "#/$defs/ToolchainManifest"}]}
    toolchain_validator = Draft202012Validator(toolchain_schema, registry=Registry(retrieve=no_remote_schema))
    toolchain = {key: digest for key in schema["$defs"]["ToolchainManifest"]["required"] if key.endswith("_digest")}
    toolchain.update(slicer_version="synthetic", binary_dependency_digests=[], os="fictional", architecture="fictional", argv=[])
    toolchain_validator.validate(toolchain)
    del toolchain["executable_digest"]
    require(not toolchain_validator.is_valid(toolchain), "Toolchain accepted missing binary identity")
    return 3, 3


def check_links():
    count = 0
    files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            require(target_path.is_relative_to(ROOT), f"Link escapes repository: {path.name}: {target}")
            require(target_path.is_file(), f"Missing link: {path.name}: {target}")
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
    main()
