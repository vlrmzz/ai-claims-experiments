"""Test Jev against human annotations of failed agent runs.

    python fetch_annotated.py          # the datasets, about 11 MB, into data/annotated/
    python jev_ground_truth.py --dry-run
    python jev_ground_truth.py         # scores every run, caches answers, prints the comparison

Three public sets where people marked where a failed run went wrong:

  agentrx_tau        29 runs of a tau-bench retail agent (AgentRx, Microsoft)
  agentrx_magentic   44 runs of Magentic-One, a multi-agent web system (AgentRx)
  whowhen_hand       58 runs of Magentic-One (Who&When)
  whowhen_auto      126 runs of generated multi-agent teams (Who&When)

For each run Jev is asked, with no examples and no tuning: at which step is the
decisive mistake, which agent made it, and (AgentRx only) which category it is.
"""

import argparse
import csv
import json
import re
from collections import Counter

from jev_score import MODEL, USD_PER_INPUT_TOKEN, api_key, post
from traces import DATA, HERE

ANNOTATED = DATA / "annotated"
CACHE = DATA / "jev_ground_truth"
STATE_BUDGET = 80_000     # characters of step text per request; Jev accepts 32k tokens of state
MIN_STEP_CHARS = 200

# AgentRx's taxonomy, with the descriptions from its README. "Inconclusive" is left out:
# no run has it as the human label.
CATEGORIES = {
    "Instruction/Plan Adherence Failure": "The agent skips required steps or adds unnecessary actions; it does not follow its instructions or plan.",
    "Invention of New Information": "The agent fabricates facts or states information that is not grounded in what it was given.",
    "Invalid Invocation": "A malformed tool call: wrong arguments, types or schema.",
    "Misinterpretation of Tool Output": "The agent reasons incorrectly about what a tool returned.",
    "Intent-Plan Misalignment": "The agent pursues the wrong objective for what the user wants.",
    "Underspecified User Intent": "The user did not give the information needed to proceed.",
    "Intent Not Supported": "The requested action cannot be performed with the available tools.",
    "Guardrails Triggered": "The agent was blocked by safety, responsible-AI or access policies.",
    "System Failure": "An infrastructure error such as a timeout or an unreachable endpoint.",
}
CATEGORY_ALIASES = {
    "instruction adherence failure": "Instruction/Plan Adherence Failure",
    "instruction/plan adherence failure": "Instruction/Plan Adherence Failure",
    "invention of new information": "Invention of New Information",
    "invalid invocation": "Invalid Invocation",
    "misinterpretation of tool output": "Misinterpretation of Tool Output",
    "intent plan misalignment": "Intent-Plan Misalignment",
    "underspecified user intent": "Underspecified User Intent",
    "intent not supported": "Intent Not Supported",
    "guardrails triggered": "Guardrails Triggered",
    "system failure": "System Failure",
}


def agent_name(who):
    """'Orchestrator (-> WebSurfer)' and 'Orchestrator (thought)' are both the Orchestrator."""
    name = re.sub(r"\s*\(.*\)$", "", who or "").strip()
    return {"websurfer": "WebSurfer", "filesurfer": "FileSurfer"}.get(name.lower(), name)


def message_text(m):
    text = m.get("content") or ""
    for call in m.get("tool_calls") or []:
        f = call.get("function") or {}
        text += f"\n[tool call] {f.get('name')}({f.get('arguments')})"
    return str(text).strip()


def root_failure(g):
    wanted = str(g["root_cause"].get("failure_id"))
    return next((f for f in g["failures"] if str(f["failure_id"]) == wanted), None)


def load_agentrx_tau():
    runs = {t["task_id"]: t for t in json.loads((ANNOTATED / "agentrx" / "tau_dataset_failed.json").read_text())}
    policy = (ANNOTATED / "agentrx" / "retail_policy.txt").read_text()
    for g in json.loads((ANNOTATED / "agentrx" / "tau_ground_truth.json").read_text()):
        root = root_failure(g)
        traj = runs[g["trajectory_id"]]["traj"]
        steps = [("system" if m["role"] == "system" else m["role"],
                  "(the policy, given in `policy`)" if m["role"] == "system" else message_text(m)) for m in traj]
        yield {"dataset": "agentrx_tau", "id": str(g["trajectory_id"]), "task": None, "policy": policy,
               "steps": steps, "first_step": 1, "agents": None,
               "human_step": root["step_number"], "human_agent": None,
               "human_any_step": sorted({f["step_number"] for f in g["failures"]}),
               "human_category": CATEGORY_ALIASES[root["failure_category"].lower()]}


def load_agentrx_magentic():
    for g in json.loads((ANNOTATED / "agentrx" / "magentic_one_ground_truth.json").read_text()):
        root = root_failure(g)
        if root is None:
            continue
        traj = json.loads((ANNOTATED / "agentrx" / "magentic" / f"{g['trajectory_id']}.json").read_text())
        steps = [(m["role"], message_text(m)) for m in traj]
        yield {"dataset": "agentrx_magentic", "id": g["trajectory_id"], "task": None, "policy": None,
               "steps": steps, "first_step": 1,
               "agents": sorted({agent_name(w) for w, _ in steps} - {"human"}),
               "human_step": root["step_number"], "human_agent": agent_name(root["failed_agent"]),
               "human_any_step": sorted({f["step_number"] for f in g["failures"]}),
               "human_category": CATEGORY_ALIASES[root["failure_category"].lower()]}


def load_whowhen(name, dataset):
    for r in json.loads((ANNOTATED / "whowhen" / f"{name}.json").read_text()):
        steps = [(m.get("name") or m["role"], message_text(m)) for m in r["history"]]
        yield {"dataset": dataset, "id": r["question_ID"], "task": r["question"], "policy": None,
               "steps": steps, "first_step": 0,
               "agents": sorted({agent_name(w) for w, _ in steps} - {"human"}),
               "human_step": int(r["mistake_step"]), "human_agent": agent_name(r["mistake_agent"]),
               "human_any_step": [int(r["mistake_step"])], "human_category": None}


def load_all():
    return (list(load_agentrx_tau()) + list(load_agentrx_magentic())
            + list(load_whowhen("Hand-Crafted", "whowhen_hand"))
            + list(load_whowhen("Algorithm-Generated", "whowhen_auto")))


def fit_steps(steps, budget):
    """Cut every step to the same maximum length, the largest that fits the budget."""
    if sum(len(c) for _, c in steps) <= budget:
        return steps, None
    lo, hi = MIN_STEP_CHARS, max(len(c) for _, c in steps)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(min(len(c), mid) for _, c in steps) <= budget:
            lo = mid
        else:
            hi = mid - 1
    cut = [(w, c if len(c) <= lo else c[:lo] + " [cut]") for w, c in steps]
    return cut, lo


def request_for(item, budget=STATE_BUDGET):
    steps, cap = fit_steps(item["steps"], budget)
    ids = [f"step_{item['first_step'] + i}" for i in range(len(steps))]
    state = {"steps": [{"step": i, "who": w, "content": c} for i, (w, c) in zip(ids, steps)]}
    if item["task"]:
        state["task"] = item["task"]
    if item["policy"]:
        state["policy"] = item["policy"]
    questions = {"step": {
        "type": "choice",
        "instructions": ("This run failed. `steps` lists everything that happened, in order. Which step contains the "
                         "decisive mistake: the step where something is done wrong that causes the final failure?"),
        "criteria": {i: None for i in ids}}}
    if item["agents"]:
        questions["agent"] = {
            "type": "choice",
            "instructions": "This run failed. Which agent made the decisive mistake that caused the failure?",
            "criteria": {a: None for a in item["agents"]}}
    if item["human_category"]:
        questions["category"] = {
            "type": "choice",
            "instructions": "This run failed. Which category best describes the root cause of the failure?",
            "criteria": CATEGORIES}
    return {"model": MODEL, "state": state, "questions": questions}, cap


def score(item, key):
    path = CACHE / item["dataset"] / f"{item['id']}.json"
    if path.exists():
        return json.loads(path.read_text())
    budget = STATE_BUDGET
    while True:
        body, cap = request_for(item, budget)
        try:
            answer = post(body, key)
            break
        except SystemExit as e:      # too long for the context window: cut harder and retry
            if budget <= 20_000 or not re.search(r"HTTP (400|413|422)", str(e)):
                raise
            budget = int(budget * 0.75)
    result = {"answer": answer, "step_cap": cap, "budget": budget}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1))
    return result


def row_for(item, result):
    answers = result["answer"]["answers"]
    step = answers["step"]
    human = f"step_{item['human_step']}"
    ranked = sorted(step["probabilities"], key=lambda k: -step["probabilities"][k])
    row = {"dataset": item["dataset"], "id": item["id"], "steps": len(item["steps"]),
           "step_cap": result["step_cap"] or "",
           "human_step": item["human_step"], "jev_step": int(step["choice"].split("_")[1]),
           "jev_step_probability": step["probabilities"][step["choice"]],
           "human_step_probability": step["probabilities"].get(human, ""),
           "human_step_rank": ranked.index(human) + 1 if human in ranked else "",
           "jev_step_is_any_annotated": int(int(step["choice"].split("_")[1]) in item["human_any_step"]),
           "human_agent": item["human_agent"] or "", "jev_agent": "", "jev_agent_probability": "",
           "human_category": item["human_category"] or "", "jev_category": "", "jev_category_probability": ""}
    for name in ("agent", "category"):
        if name in answers:
            row[f"jev_{name}"] = answers[name]["choice"]
            row[f"jev_{name}_probability"] = answers[name]["probabilities"][answers[name]["choice"]]
    return row


def share(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def summarise(rows):
    out = {}
    print(f"\n{'dataset':18s} runs  cut |  step: exact  within 1  in top 3  chance | agent: exact  majority | category: exact  majority")
    for dataset in dict.fromkeys(r["dataset"] for r in rows):
        d = [r for r in rows if r["dataset"] == dataset]
        with_agent = [r for r in d if r["human_agent"]]
        with_cat = [r for r in d if r["human_category"]]
        s = {
            "runs": len(d),
            "runs_cut_to_fit": sum(bool(r["step_cap"]) for r in d),
            "step_exact": share(r["jev_step"] == r["human_step"] for r in d),
            "step_within_1": share(abs(r["jev_step"] - r["human_step"]) <= 1 for r in d),
            "step_in_top_3": share(r["human_step_rank"] != "" and r["human_step_rank"] <= 3 for r in d),
            "step_chance": share(1 / r["steps"] for r in d),
            "agent_exact": share(r["jev_agent"] == r["human_agent"] for r in with_agent),
            "agent_majority": Counter(r["human_agent"] for r in with_agent).most_common(1)[0][1] / len(with_agent) if with_agent else None,
            "category_exact": share(r["jev_category"] == r["human_category"] for r in with_cat),
            "category_majority": Counter(r["human_category"] for r in with_cat).most_common(1)[0][1] / len(with_cat) if with_cat else None,
        }
        out[dataset] = s
        pct = lambda v: "   -  " if v is None else f"{v:6.0%}"
        print(f"{dataset:18s} {s['runs']:4d} {s['runs_cut_to_fit']:4d} |      {pct(s['step_exact'])}    {pct(s['step_within_1'])}    {pct(s['step_in_top_3'])}  {pct(s['step_chance'])} |"
              f"       {pct(s['agent_exact'])}    {pct(s['agent_majority'])} |          {pct(s['category_exact'])}    {pct(s['category_majority'])}")

    print("\nstep answer, by the probability Jev gave it (all datasets):")
    out["step_calibration"] = []
    for lo, hi in ((0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.0001)):
        inside = [r for r in rows if lo <= r["jev_step_probability"] < hi]
        if inside:
            exact = share(r["jev_step"] == r["human_step"] for r in inside)
            out["step_calibration"].append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": len(inside), "exact": exact})
            print(f"  {lo:.1f}-{min(hi, 1):.1f}  n={len(inside):3d}  exact {exact:.0%}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = load_all()
    if args.dry_run:
        for dataset, n in Counter(i["dataset"] for i in items).items():
            sizes = [len(json.dumps(request_for(i)[0])) for i in items if i["dataset"] == dataset]
            cut = sum(request_for(i)[1] is not None for i in items if i["dataset"] == dataset)
            print(f"{dataset:18s} {n:4d} runs, {cut:3d} cut to fit, request characters median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)}")
        return

    key = api_key()
    rows, tokens = [], 0
    for n, item in enumerate(items, 1):
        result = score(item, key)
        tokens += result["answer"]["usage"]["input_tokens"]
        rows.append(row_for(item, result))
        if n % 25 == 0:
            print(f"{n}/{len(items)} scored")
    with open(HERE / "ground_truth_scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = summarise(rows)
    summary["input_tokens"] = tokens
    summary["usd_at_list_price"] = tokens * USD_PER_INPUT_TOKEN
    (HERE / "ground_truth_results.json").write_text(json.dumps(summary, indent=1))
    print(f"\n{len(rows)} runs, {tokens} input tokens, ${tokens * USD_PER_INPUT_TOKEN:.4f} at list price")


if __name__ == "__main__":
    main()
