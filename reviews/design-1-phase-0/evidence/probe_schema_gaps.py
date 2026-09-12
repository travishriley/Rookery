"""Evidence for S2, S3, S4 and S6: schema shapes that parse but should not.

Read-only. Builds records in memory from schemas/0.1.0/examples.json and validates them.
"""

from copy import deepcopy

from _common import DIGEST, EXAMPLES, SCHEMA, heading, report, validator

V = validator()


def probe_change_values():
    heading("S2/S3: ChangeProposal accepts unbounded and untyped values")
    base = deepcopy(EXAMPLES["ChangeProposal"])
    for label, mutation in [
        ("nozzle_temperature -> 500 (no Range is bound to this Change)",
         {"key": "nozzle_temperature", "units": "C", "current_value": 210, "proposed_value": 500}),
        ("proposed_value = 1e308 (finite, so finite_float passes)", {"proposed_value": 1e308}),
        ("proposed_value = null (delete key? semantics undefined)", {"proposed_value": None}),
        ("proposed_value = '500' (string where policy compares a number)", {"proposed_value": "500"}),
        ("proposed_value = true (boolean temperature)", {"proposed_value": True}),
        ("units mismatch: proposes 250 with units 'mm/s'",
         {"key": "nozzle_temperature", "units": "mm/s", "proposed_value": 250}),
        ("current_value is a string, proposed_value is a number",
         {"current_value": "210", "proposed_value": 500}),
    ]:
        record = deepcopy(base)
        record["changes"][0].update(mutation)
        report(label, record, V)


def probe_ranges():
    heading("S2: CalibrationDefinition Range invariants")
    print(f"  Range has a 'domain' field: {'domain' in SCHEMA['$defs']['Range']['properties']}")
    print(f"  Range additionalProperties: {SCHEMA['$defs']['Range'].get('additionalProperties')}")
    print("  (so a domain cannot be added ad hoc either)\n")
    base = deepcopy(EXAMPLES["CalibrationDefinition"])
    for label, ranges in [
        ("minimum(300) > maximum(10) -- inverted bound",
         [{"parameter": "nozzle_temperature", "units": "C", "minimum": 300, "maximum": 10,
           "review_digest": DIGEST}]),
        ("two contradictory ranges for the SAME parameter (150-260 and 150-450)",
         [{"parameter": "nozzle_temperature", "units": "C", "minimum": 150, "maximum": 260,
           "review_digest": DIGEST},
          {"parameter": "nozzle_temperature", "units": "C", "minimum": 150, "maximum": 450,
           "review_digest": DIGEST}]),
    ]:
        record = deepcopy(base)
        record["ranges"] = ranges
        report(label, record, V)


def probe_printer_identity():
    heading("S4: PrinterIdentity can claim Klipper validation with no evidence")
    base = deepcopy(EXAMPLES["PrinterIdentity"])
    for scope in ["klipper_static", "klipper_observed"]:
        record = deepcopy(base)
        record.update(firmware="klipper", validation_scope=scope,
                      identity_evidence_digests=[], hardware_digest=None)
        report(f"{scope} with zero identity evidence and null hardware_digest", record, V)


def probe_uniqueness():
    heading("S6: no uniqueness constraint on files or captures")
    print(f"  SourceSnapshot.files uniqueItems: "
          f"{SCHEMA['$defs']['SourceSnapshot']['properties']['files'].get('uniqueItems')}")
    print(f"  EvidenceBundle.captures uniqueItems: "
          f"{SCHEMA['$defs']['EvidenceBundle']['properties']['captures'].get('uniqueItems')}")
    print(f"  Digests uniqueItems: {SCHEMA['$defs']['Digests'].get('uniqueItems')}   "
          f"<- the idiom is already used elsewhere\n")

    snapshot = deepcopy(EXAMPLES["SourceSnapshot"])
    first = snapshot["files"][0]

    alias = deepcopy(first)
    alias["path"] = first["path"] + "."
    alias["digest"] = "sha256:" + "b" * 64
    record = deepcopy(snapshot)
    record["files"] = [first, alias]
    report(f"files {first['path']!r} and {alias['path']!r} (same file on Windows)", record, V)

    collide = deepcopy(first)
    collide["digest"] = "sha256:" + "c" * 64
    record = deepcopy(snapshot)
    record["files"] = [first, collide]
    report(f"two entries, identical path {first['path']!r}, different digests", record, V)

    bundle = deepcopy(EXAMPLES["EvidenceBundle"])
    record = deepcopy(bundle)
    record["captures"] = [bundle["captures"][0], deepcopy(bundle["captures"][0])]
    report("two captures sharing one id (Finding.capture_ids becomes ambiguous)", record, V)


def probe_approval_times():
    heading("Context for M7: ApprovalRecord field ordering is not expressible in JSON Schema")
    base = deepcopy(EXAMPLES["ApprovalRecord"])
    record = deepcopy(base)
    record.update(approved_at="2026-09-12T12:00:00Z", expires_at="2020-01-01T00:00:00Z")
    report("expires_at precedes approved_at (must be a runtime invariant)", record, V)


if __name__ == "__main__":
    probe_change_values()
    probe_ranges()
    probe_printer_identity()
    probe_uniqueness()
    probe_approval_times()
    print("\nEvery line above marked SCHEMA-VALID parses cleanly against "
          "schemas/0.1.0/rookery.schema.json.")
