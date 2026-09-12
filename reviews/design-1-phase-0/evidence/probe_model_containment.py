"""Evidence for S5: the model-containment rules work, but are not probed by check_design.py.

Read-only. Confirms the schema rejects every escalation shape, then shows that the
string 'elevated_proposal_only' never appears in the checker.
"""

from copy import deepcopy

from _common import EXAMPLES, REPO, branch_validator, heading

V = branch_validator("DiagnosticResponse")

PROPOSAL = {key: value for key, value in EXAMPLES["ChangeProposal"].items()
            if key not in {"schema_version", "kind", "id", "created_at"}}
BASELINE = {
    "outcome": "propose_bounded_change", "observations": [], "measured_values": [],
    "hypotheses": [], "counterevidence": [], "missing_information": ["synthetic"],
    "confidence_limitations": ["synthetic"], "proposal": deepcopy(PROPOSAL),
}


def check(label, response):
    errors = list(V.iter_errors(response))
    print(f"  {'ACCEPTED    ' if not errors else 'rejected(ok)'}  {label}")
    return not errors


def probe_containment():
    heading("S5 part 1: do the model-containment rules actually hold?")
    check("baseline: bounded_slicer proposal in an orca_process domain", BASELINE)

    escalated = deepcopy(BASELINE)
    escalated["proposal"]["risk"] = "elevated_proposal_only"
    check("model escalates its own risk to elevated_proposal_only", escalated)

    both = deepcopy(BASELINE)
    both["proposal"]["risk"] = "elevated_proposal_only"
    both["proposal"]["changes"][0]["domain"] = "klipper_audit_only"
    check("model reaches a Klipper domain via the elevated risk level", both)

    klipper = deepcopy(BASELINE)
    klipper["proposal"]["changes"][0]["domain"] = "klipper_audit_only"
    check("model proposes a Klipper domain under bounded_slicer", klipper)

    attached = deepcopy(BASELINE)
    attached["outcome"] = "no_change"
    check("model attaches a proposal to a no_change outcome", attached)

    multiple = deepcopy(BASELINE)
    multiple["proposal"]["changes"] = multiple["proposal"]["changes"] * 2
    check("model returns more than one change", multiple)


def probe_coverage():
    heading("S5 part 2: does check_design.py probe any of them?")
    source = (REPO / "tools" / "check_design.py").read_text(encoding="utf-8")
    for term in ["elevated_proposal_only", "klipper_audit_only", "no_change",
                 "arbitrary_script", "bounded_slicer"]:
        print(f"  {term:24} appears in check_design.py: {term in source}")
    print("\n  'klipper_audit_only' appears only at check_design.py:157, which probes the"
          "\n  application-owned ChangeProposal record, not the model-facing DiagnosticResponse."
          "\n  Run mutation_test.py for the consequence.")


if __name__ == "__main__":
    probe_containment()
    probe_coverage()
