"""Merge the reference labeller's batch files into reference_labels.csv.

    python consolidate.py

The labeller (see labelling_brief.md) named failure classes freely, batch by
batch. CLASS_TO_PATTERN folds those 48 names into the eight patterns of
patterns.json. The mapping was made by hand from the class names and notes.
"""

import csv
import json

from traces import DATA, HERE

CLASS_TO_PATTERN = {
    "expected_violates_policy": [
        "Expected action contradicts policy", "Expected actions violate stated policy",
        "Expected cancellation violates insurance-reason rule", "Expected action violates written policy",
        "Expected action contradicts written policy"],
    "expected_contradicts_data": [
        "Expected outcome built on wrong arithmetic", "Expected actions contradict database records",
        "Expected argument not derivable from script or data", "Expected action impossible given data"],
    "script_underspecified": [
        "Script silent on graded argument", "Expected payment method not derivable from script",
        "Unspecified payment method; valid alternative rejected"],
    "simulator_off_script": [
        "Simulator departed from script", "Simulator invented details missing from script",
        "Simulator accepted changes script forbade", "Simulator ignored scripted conditional branch",
        "Simulator invented details contradicting database", "Simulator omitted scripted constraint or request",
        "Customer omitted scripted request", "Customer invented details not in script",
        "Customer simulator chose option contradicting script", "Customer simulator misstated scripted fallback request",
        "Simulator gave wrong details about own order", "Simulator picked variant script did not specify"],
    "unrequested_offer_accepted": [
        "Unrequested alternative offered, simulator accepts off-script",
        "Simulator accepted agent-suggested off-script action", "Agent offered extra write; simulator accepted",
        "Customer accepted unscripted alternative", "Customer simulator accepted unscripted extra action",
        "Simulator accepted unscripted agent-offered change"],
    "write_without_check": [
        "Paid write confirmed without quoting price", "Cancelled on customer's claim without verifying record",
        "Wrote without restating changed action for confirmation", "Write without final explicit confirmation"],
    "rule_misapplied": [
        "Agent wrongly says tools cannot do it", "Invented fee rule, unrequested extra write",
        "Restricted fare bypassed via cabin upgrade", "Agent invented restriction, refused allowed request",
        "Agent modified reservation with already-flown segment", "Pending-order item change wrongly refused"],
    "other_agent_error": [
        "Premature transfer to human agent", "Wrong total stated to customer",
        "Agent guessed ambiguous detail instead of asking", "Agent sequenced writes so later one blocked",
        "Agent steered customer to destructive workaround"],
}
PATTERN_OF = {name: pattern for pattern, names in CLASS_TO_PATTERN.items() for name in names}

COLUMNS = ["trace_id", "domain", "task_id", "trial", "pattern", "fault", "cheapest_fix", "confidence",
           "first_error_turn", "labeller_class", "what_went_wrong", "fault_evidence", "fix_note", "summary"]


def main():
    rows = []
    for path in sorted((DATA / "labels").glob("batch_*.json")):
        for r in json.loads(path.read_text()):
            domain, task, trial = r["trace_id"].split("-")
            rows.append({**{c: r.get(c) for c in COLUMNS},
                         "domain": domain, "task_id": int(task), "trial": int(trial[1:]),
                         "labeller_class": r["proposed_class"], "pattern": PATTERN_OF[r["proposed_class"]]})
    rows.sort(key=lambda r: r["trace_id"])
    with open(HERE / "reference_labels.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote reference_labels.csv: {len(rows)} runs, {len(set(r['pattern'] for r in rows))} patterns")


if __name__ == "__main__":
    main()
