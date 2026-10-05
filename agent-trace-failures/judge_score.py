"""Score the text-model judge against the human labels, next to Jev, on the held-out half.

    python judge_score.py       # reads data/judge/answers/batch_*.json, writes judge_results.json

The judge is Claude reading each run in full (see judge_export.py for exactly what it was
given). Jev's numbers are the tuned setup from jev_tune.py on the same runs.
"""

import csv
import json
from collections import Counter

from jev_ground_truth import agent_name, load_all
from jev_tune import half
from traces import DATA, HERE


def share(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def pct(v):
    return "   -" if v is None else f"{v:4.0%}"


def main():
    test = {f"{i['dataset']}__{i['id']}": i for i in load_all() if half(i) == "test"}
    answers = {}
    for path in sorted((DATA / "judge" / "answers").glob("batch_*.json")):
        for a in json.loads(path.read_text()):
            answers[a["run"]] = a
    missing = sorted(set(test) - set(answers))
    print(f"{len(answers)} answers for {len(test)} runs; missing: {len(missing)}")

    tuned = {(r["dataset"], r["id"]): r for r in csv.DictReader(open(HERE / "tuned_test_scores.csv"))}
    tuning = json.loads((HERE / "tuning_results.json").read_text())["test"]
    datasets = list(dict.fromkeys(i["dataset"] for i in test.values()))
    out = {"answered": len(answers), "missing": missing, "by_dataset": {}}

    rows = []
    for name, item in test.items():
        a = answers.get(name)
        if a is None:
            continue
        jev = tuned[(item["dataset"], item["id"])]
        rows.append({
            "dataset": item["dataset"], "id": item["id"], "long": sum(len(c) for _, c in item["steps"]) > 80_000,
            "human_step": item["human_step"], "judge_step": int(a["step"]), "jev_step": int(jev["tuned_step"]),
            "judge_confidence": float(a.get("confidence") or 0),
            "human_agent": item["human_agent"], "judge_agent": agent_name(a["agent"]) if a.get("agent") else None,
            "human_category": item["human_category"], "judge_category": a.get("category"),
        })

    print(f"\n{'dataset':18s} runs | step exact: judge  Jev | within 1: judge  Jev | agent: judge  Jev | category: judge  Jev")
    for d in datasets + ["whowhen (both)", "all"]:
        g = [r for r in rows if d == "all" or r["dataset"] == d or (d == "whowhen (both)" and r["dataset"].startswith("whowhen"))]
        with_agent = [r for r in g if r["human_agent"]]
        with_cat = [r for r in g if r["human_category"]]
        s = {"runs": len(g),
             "step_exact": {"judge": share(r["judge_step"] == r["human_step"] for r in g),
                            "jev": share(r["jev_step"] == r["human_step"] for r in g)},
             "step_within_1": {"judge": share(abs(r["judge_step"] - r["human_step"]) <= 1 for r in g),
                               "jev": share(abs(r["jev_step"] - r["human_step"]) <= 1 for r in g)},
             "agent": {"judge": share(r["judge_agent"] == r["human_agent"] for r in with_agent), "jev": tuning[d]["agent"][1]},
             "category": {"judge": share(r["judge_category"] == r["human_category"] for r in with_cat), "jev": tuning[d]["category"][1]},
             "counts": {"judge_step_exact": sum(r["judge_step"] == r["human_step"] for r in g),
                        "jev_step_exact": sum(r["jev_step"] == r["human_step"] for r in g),
                        "judge_agent": sum(r["judge_agent"] == r["human_agent"] for r in with_agent), "agent_runs": len(with_agent),
                        "judge_category": sum(r["judge_category"] == r["human_category"] for r in with_cat), "category_runs": len(with_cat)}}
        out["by_dataset"][d] = s
        print(f"{d:18s} {len(g):4d} |             {pct(s['step_exact']['judge'])} {pct(s['step_exact']['jev'])} |"
              f"           {pct(s['step_within_1']['judge'])} {pct(s['step_within_1']['jev'])} |"
              f"        {pct(s['agent']['judge'])} {pct(s['agent']['jev'])} |           {pct(s['category']['judge'])} {pct(s['category']['jev'])}")

    long_runs = [r for r in rows if r["long"]]
    out["long_runs"] = {"runs": len(long_runs),
                        "judge_exact": sum(r["judge_step"] == r["human_step"] for r in long_runs),
                        "jev_exact": sum(r["jev_step"] == r["human_step"] for r in long_runs)}
    print(f"\nlong runs (over 80k characters): {out['long_runs']}")

    both = Counter((r["judge_step"] == r["human_step"], r["jev_step"] == r["human_step"]) for r in rows)
    out["overlap"] = {"both_right": both[(True, True)], "judge_only": both[(True, False)],
                      "jev_only": both[(False, True)], "neither": both[(False, False)],
                      "judge_and_jev_same_step": sum(r["judge_step"] == r["jev_step"] for r in rows)}
    print(f"step: both right {both[(True, True)]}, judge only {both[(True, False)]}, Jev only {both[(False, True)]}, "
          f"neither {both[(False, False)]}; judge and Jev picked the same step in {out['overlap']['judge_and_jev_same_step']} runs")

    out["judge_by_confidence"] = []
    print("\njudge's step answer, by its own stated confidence:")
    for lo, hi in ((0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.0001)):
        inside = [r for r in rows if lo <= r["judge_confidence"] < hi]
        if inside:
            exact = share(r["judge_step"] == r["human_step"] for r in inside)
            out["judge_by_confidence"].append({"bin": f"{lo:.2f}-{min(hi, 1):.2f}", "n": len(inside), "exact": exact})
            print(f"  {lo:.2f}-{min(hi, 1):.2f}  n={len(inside):3d}  exact {exact:.0%}")

    (HERE / "judge_results.json").write_text(json.dumps(out, indent=1))
    with open(HERE / "judge_scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
