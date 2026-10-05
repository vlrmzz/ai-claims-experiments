"""Compare Jev's scores with the reference labels and with the published task revisions.

    python evaluate.py      # prints the tables and writes results.json

The reference labels are one model's reading (see labelling_brief.md), not
ground truth. The task revisions are independent of both.
"""

import csv
import json
from collections import Counter, defaultdict

from traces import DATA, HERE

FAULT_GROUP = {"agent": "agent", "agent and benchmark": "both", "task definition": "benchmark",
               "grader": "benchmark", "user simulator": "benchmark"}


def read_csv(name):
    with open(HERE / name, newline="") as f:
        return list(csv.DictReader(f))


def auc(scores, labels):
    """Probability that a random positive scores above a random negative (ties count half)."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def calibration(probabilities, correct, edges=(0, 0.5, 0.7, 0.9, 1.0001)):
    rows = []
    for lo, hi in zip(edges, edges[1:]):
        inside = [(p, c) for p, c in zip(probabilities, correct) if lo <= p < hi]
        if inside:
            rows.append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": len(inside),
                         "mean_probability": sum(p for p, _ in inside) / len(inside),
                         "share_correct": sum(c for _, c in inside) / len(inside)})
    return rows


def main():
    patterns = json.loads((HERE / "patterns.json").read_text())
    ids = [p["id"] for p in patterns]
    ref = {r["trace_id"]: r for r in read_csv("reference_labels.csv")}
    jev = {r["trace_id"]: r for r in read_csv("jev_scores.csv")}
    raw = {t: json.loads((DATA / "jev" / f"{t}.json").read_text()) for t in ref}
    revised = {(r["domain"], int(r["task_id"])): bool(r["amazon_changed"] or r["sierra_changed"])
               for r in read_csv("task_revisions.csv")}
    traces = sorted(ref)
    n = len(traces)
    out = {"runs": n}

    # 1. main pattern: Jev's single choice against the reference pattern
    hits = [jev[t]["main_pattern"] == ref[t]["pattern"] for t in traces]
    majority = Counter(ref[t]["pattern"] for t in traces).most_common(1)[0]
    out["pattern_accuracy"] = sum(hits) / n
    out["pattern_majority_baseline"] = majority[1] / n
    print(f"main pattern: Jev agrees with the reference on {sum(hits)} of {n} runs ({sum(hits) / n:.0%}); "
          f"always answering '{majority[0]}' would give {majority[1] / n:.0%}")
    print(f"\n{'pattern':28s} ref  jev  both  precision recall   AUC(yes/no)")
    out["per_pattern"] = {}
    for p in ids:
        in_ref = [ref[t]["pattern"] == p for t in traces]
        in_jev = [jev[t]["main_pattern"] == p for t in traces]
        both = sum(a and b for a, b in zip(in_ref, in_jev))
        precision = both / sum(in_jev) if sum(in_jev) else None
        recall = both / sum(in_ref)
        a = auc([float(jev[t][f"p_{p}"]) for t in traces], in_ref)
        out["per_pattern"][p] = {"reference": sum(in_ref), "jev": sum(in_jev), "both": both,
                                 "precision": precision, "recall": recall, "auc": a}
        print(f"{p:28s} {sum(in_ref):3d}  {sum(in_jev):3d}  {both:4d}  "
              f"{'   -  ' if precision is None else f'{precision:6.0%}'}    {recall:5.0%}   {a:.2f}")

    confusion = Counter((ref[t]["pattern"], jev[t]["main_pattern"]) for t in traces)
    out["confusion"] = [{"reference": a, "jev": b, "runs": k} for (a, b), k in sorted(confusion.items())]
    print("\nlargest disagreements (reference -> Jev):")
    for (a, b), k in sorted(confusion.items(), key=lambda x: -x[1]):
        if a != b and k >= 3:
            print(f"  {k:3d}  {a} -> {b}")

    # 2. is the confidence worth anything?
    p_chosen = [raw[t]["graded"]["answers"]["main_pattern"]["probabilities"][jev[t]["main_pattern"]] for t in traces]
    out["pattern_calibration"] = calibration(p_chosen, hits)
    print("\nmain pattern, by the probability Jev gave its own answer:")
    for row in out["pattern_calibration"]:
        print(f"  {row['bin']}  n={row['n']:3d}  mean probability {row['mean_probability']:.2f}  agrees with reference {row['share_correct']:.0%}")

    # 3. whose fault
    ref_fault = [FAULT_GROUP[ref[t]["fault"]] for t in traces]
    jev_fault = [jev[t]["fault"] for t in traces]
    agree = sum(a == b for a, b in zip(ref_fault, jev_fault))
    out["fault_accuracy"] = agree / n
    out["fault_majority_baseline"] = Counter(ref_fault).most_common(1)[0][1] / n
    out["fault_table"] = [{"reference": a, "jev": b, "runs": k}
                          for (a, b), k in sorted(Counter(zip(ref_fault, jev_fault)).items())]
    print(f"\nfault: Jev agrees with the reference on {agree} of {n} ({agree / n:.0%}); "
          f"always answering 'benchmark' would give {out['fault_majority_baseline']:.0%}")
    print("  reference -> Jev:", dict(Counter(zip(ref_fault, jev_fault))))
    p_bench = [float(jev[t]["p_fault_benchmark"]) for t in traces]
    out["fault_auc_vs_reference"] = auc(p_bench, [f == "benchmark" for f in ref_fault])
    print(f"  P(benchmark) separates reference benchmark-only runs from the rest with AUC {out['fault_auc_vs_reference']:.2f}")

    # 4. the independent check: tasks that Amazon or Sierra later revised
    is_revised = [revised[(ref[t]["domain"], int(ref[t]["task_id"]))] for t in traces]
    out["revised_runs"] = sum(is_revised)
    out["fault_auc_vs_revisions"] = {
        "jev": auc(p_bench, is_revised),
        "reference": auc([f == "benchmark" for f in ref_fault], is_revised),
    }
    print(f"\nlater revised tasks ({sum(is_revised)} of {n} runs): AUC of Jev's P(benchmark) {out['fault_auc_vs_revisions']['jev']:.2f}, "
          f"of the reference's benchmark-only label {out['fault_auc_vs_revisions']['reference']:.2f}")
    for name, values in (("reference", ref_fault), ("Jev", jev_fault)):
        table = Counter((v, r) for v, r in zip(values, is_revised))
        print(f"  {name:9s} " + "  ".join(f"{g}: {table[(g, True)]} revised / {table[(g, False)]} not" for g in ("benchmark", "both", "agent")))

    # 5. do the four trials of a task get the same answer?
    by_task = defaultdict(list)
    for t in traces:
        by_task[(ref[t]["domain"], ref[t]["task_id"])].append(t)
    multi = {k: v for k, v in by_task.items() if len(v) > 1}
    same_ref = sum(len({ref[t]["pattern"] for t in v}) == 1 for v in multi.values())
    same_jev = sum(len({jev[t]["main_pattern"] for t in v}) == 1 for v in multi.values())
    out["trial_consistency"] = {"tasks_with_several_failed_runs": len(multi), "reference_same_pattern": same_ref, "jev_same_pattern": same_jev}
    print(f"\ntasks with several failed runs: {len(multi)}; same pattern on all of them: reference {same_ref}, Jev {same_jev}")

    # 6. without the grader's information: agent-side patterns from the conversation alone
    print("\nagent-side patterns, yes/no AUC against the reference:   with grader info   conversation only")
    out["blind"] = {}
    for p in patterns:
        if p["side"] == "benchmark":
            continue
        in_ref = [ref[t]["pattern"] == p["id"] for t in traces]
        graded = auc([float(jev[t][f"p_{p['id']}"]) for t in traces], in_ref)
        blind = auc([float(jev[t][f"blind_p_{p['id']}"]) for t in traces], in_ref)
        out["blind"][p["id"]] = {"graded_auc": graded, "blind_auc": blind, "reference": sum(in_ref)}
        print(f"  {p['id']:28s} (n={sum(in_ref):2d})              {graded:.2f}               {blind:.2f}")

    (HERE / "results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
