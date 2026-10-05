"""Tune how Jev is asked, on one half of the annotated runs, and report on the other half.

    python jev_tune.py

Jev's weights cannot be trained, so "tuning" here means three things:

  wording   four ways of asking for the failing step
  windows   long runs are scanned in overlapping windows instead of being cut to fit
  category  the category is asked as one choice or as one yes/no per category,
            with the README's short definitions or the paper's longer ones

Every choice is made on the tune half only. The test half is scored once, with
the untuned setup and with the chosen one. The agent is not asked for at all in
the tuned setup: it is read off the step Jev picked.
"""

import csv
import hashlib
import json
from collections import Counter

from jev_ground_truth import (CATEGORIES, STATE_BUDGET, agent_name, fit_steps, load_all,
                              score as score_untuned)
from jev_score import MODEL, USD_PER_INPUT_TOKEN, api_key, post
from traces import DATA, HERE

CACHE = DATA / "jev_tune"
STEP_CAP = 12_000        # characters; a single step longer than this is cut in windowed mode
WINDOW_BUDGET = 60_000   # characters of step text per window
OVERLAP = 3              # steps shared by neighbouring windows
TOKENS = 0

STEP_WORDINGS = {
    "base": ("This run failed. `steps` lists everything that happened, in order. Which step contains the "
             "decisive mistake: the step where something is done wrong that causes the final failure?"),
    "first_unresolved": ("This run failed. `steps` lists everything that happened, in order. Scan from the start. "
                         "Which is the first step where an agent makes a mistake (a wrong action, a wrong claim, a "
                         "skipped requirement or a wrong plan) that is never corrected later in the run?"),
}
# name -> (wording, whether each option says who acted at that step)
STEP_VARIANTS = {"base": ("base", False), "base+who": ("base", True),
                 "first_unresolved": ("first_unresolved", False), "first_unresolved+who": ("first_unresolved", True)}

# The definitions the AgentRx paper gives its own LLM judge (appendix H.1), lightly shortened.
PAPER_CATEGORIES = {
    "Instruction/Plan Adherence Failure": "The agent fails to follow the directions or the agreed plan by ignoring directives and skipping policy steps. Covers missed steps and unplanned or unnecessary actions that deviate from the plan, the domain policy or the orchestrator's plan.",
    "Invention of New Information": "The agent introduces, removes or alters information that is not grounded in any available input, context or tool output: fabricated facts, hallucinated details, or relevant information left out without justification.",
    "Invalid Invocation": "The agent hits errors caused by inputs that cannot be parsed or validated, such as tool calls with bad or missing arguments. Not wrong logic, only invalid inputs.",
    "Misinterpretation of Tool Output": "The agent reasons incorrectly about its own or another agent's tool output, such as a computation or counting error, leading to wrong assumptions or actions. Includes using only part of a tool output.",
    "Intent-Plan Misalignment": "The agent misreads the user's goal or constraints and produces the wrong sequence of steps: bad ordering or structure, or a plan aimed at the wrong objective.",
    "Underspecified User Intent": "The agent was unable to complete the task because complete information was lacking at some point in the run.",
    "Intent Not Supported": "The agent or user asks for an action for which no tool is available, like listening to an audio file.",
    "Guardrails Triggered": "The agent is blocked by safety policies or by external access restrictions despite a valid plan: policy refusals, CAPTCHA or robot blocks, login walls, paywalls, 403 or robots.txt denials. An external block, not a planning or execution error.",
    "System Failure": "The agent faces a connectivity problem while calling a tool, such as an endpoint that cannot be reached.",
}


def half(item):
    digest = hashlib.sha1(f"{item['dataset']}/{item['id']}".encode()).hexdigest()
    return "test" if int(digest, 16) % 2 else "tune"


def ask(cache_key, build):
    """One request to Jev, cached on disk. `build(budget)` returns the request body for a
    character budget; if Jev says the request is too long it is rebuilt with a smaller one."""
    global TOKENS
    path = CACHE / f"{cache_key}.json"
    if path.exists():
        return json.loads(path.read_text())
    for shrink in (1, 0.75, 0.55, 0.4):
        try:
            answer = post(build(shrink), api_key())
            break
        except SystemExit as e:
            if "max_tokens_exceeded" not in str(e) or shrink == 0.4:
                raise
    TOKENS += answer["usage"]["input_tokens"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(answer))
    return answer


def base_state(item):
    state = {}
    if item["task"]:
        state["task"] = item["task"]
    if item["policy"]:
        state["policy"] = item["policy"]
    return state


def step_question(variant, ids, whos, elsewhere=False):
    wording, say_who = STEP_VARIANTS[variant]
    criteria = {i: (f"a step by {w}" if say_who else None) for i, w in zip(ids, whos)}
    if elsewhere:
        criteria["elsewhere"] = "The mistake is in a part of the run that is not shown in `steps`."
    return {"type": "choice", "instructions": STEP_WORDINGS[wording], "criteria": criteria}


def windows_of(steps):
    """Consecutive windows of step indices, each within the character budget, overlapping by a few steps."""
    out, start = [], 0
    while start < len(steps):
        end, used = start, 0
        while end < len(steps) and (end == start or used + len(steps[end][1]) <= WINDOW_BUDGET):
            used += len(steps[end][1])
            end += 1
        out.append(range(start, end))
        if end == len(steps):
            break
        start = max(end - OVERLAP, start + 1)
    return out


def step_scores(item, variant, windowed):
    """A score per step index (0-based position in the run); higher means more likely the failing step."""
    name = f"{item['dataset']}__{item['id']}"
    total = sum(len(c) for _, c in item["steps"])
    if not windowed or total <= STATE_BUDGET:
        if variant == "base":            # identical to the untuned request already paid for
            answer = score_untuned(item, api_key())["answer"]
        else:
            def build(shrink):
                steps, _ = fit_steps(item["steps"], int(STATE_BUDGET * shrink))
                ids = [f"step_{item['first_step'] + i}" for i in range(len(steps))]
                state = base_state(item)
                state["steps"] = [{"step": i, "who": w, "content": c} for i, (w, c) in zip(ids, steps)]
                return {"model": MODEL, "state": state,
                        "questions": {"step": step_question(variant, ids, [w for w, _ in steps])}}
            answer = ask(f"step/{variant}/trim/{name}", build)
        probabilities = answer["answers"]["step"]["probabilities"]
        return {int(k.split("_")[1]) - item["first_step"]: v for k, v in probabilities.items()}

    steps = [(w, c if len(c) <= STEP_CAP else c[:STEP_CAP] + " [cut]") for w, c in item["steps"]]
    ending = steps[-1][1][:1500]
    scores = {}
    for n, window in enumerate(windows_of(steps)):
        ids = [f"step_{item['first_step'] + i}" for i in window]

        def build(shrink, window=window, ids=ids):
            shown, _ = fit_steps([steps[k] for k in window], int(WINDOW_BUDGET * shrink))
            state = base_state(item)
            state["how_the_run_ended"] = ending
            state["steps"] = [{"step": i, "who": w, "content": c} for i, (w, c) in zip(ids, shown)]
            return {"model": MODEL, "state": state,
                    "questions": {"step": step_question(variant, ids, [steps[k][0] for k in window], elsewhere=True)}}
        answer = ask(f"step/{variant}/window/{name}__w{n}", build)
        for key, p in answer["answers"]["step"]["probabilities"].items():
            if key != "elsewhere":
                k = int(key.split("_")[1]) - item["first_step"]
                scores[k] = max(scores.get(k, 0), p)
    return scores


def step_outcome(item, variant, windowed):
    scores = step_scores(item, variant, windowed)
    best = max(scores, key=scores.get)
    human = item["human_step"] - item["first_step"]
    out = {"exact": best == human, "within_1": abs(best - human) <= 1, "probability": scores[best],
           "jev_step": best + item["first_step"]}
    if item["human_agent"]:
        out["agent_from_step"] = agent_name(item["steps"][best][0]) == item["human_agent"]
    return out


def category_answers(item, mode):
    """mode: choice_readme (untuned), choice_paper, nouls_paper. Returns a score per category."""
    name = f"{item['dataset']}__{item['id']}"
    if mode == "choice_readme":
        return score_untuned(item, api_key())["answer"]["answers"]["category"]["probabilities"]
    def state_for(shrink):
        steps, _ = fit_steps(item["steps"], int(STATE_BUDGET * shrink))
        state = base_state(item)
        state["steps"] = [{"step": f"step_{item['first_step'] + i}", "who": w, "content": c} for i, (w, c) in enumerate(steps)]
        return state

    if mode == "choice_paper":
        questions = {"category": {"type": "choice", "criteria": PAPER_CATEGORIES,
                                  "instructions": "This run failed. Which category best describes the root cause of the failure?"}}
        answer = ask(f"category/{mode}/{name}", lambda shrink: {"model": MODEL, "state": state_for(shrink), "questions": questions})
        return answer["answers"]["category"]["probabilities"]
    questions = {f"c{k}": {"type": "noul", "criteria": {"true": definition, "false": "The root cause of the failure is something else."},
                           "instructions": f"This run failed. Is the root cause of the failure a case of '{category}'?"}
                 for k, (category, definition) in enumerate(PAPER_CATEGORIES.items())}
    answers = ask(f"category/{mode}/{name}", lambda shrink: {"model": MODEL, "state": state_for(shrink), "questions": questions})["answers"]
    return {category: answers[f"c{k}"]["noul"] for k, category in enumerate(PAPER_CATEGORIES)}


def share(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def pct(v):
    return "  -" if v is None else f"{v:.0%}"


def main():
    items = load_all()
    tune = [i for i in items if half(i) == "tune"]
    test = [i for i in items if half(i) == "test"]
    datasets = list(dict.fromkeys(i["dataset"] for i in items))
    results = {"split": {d: {"tune": sum(i["dataset"] == d for i in tune), "test": sum(i["dataset"] == d for i in test)} for d in datasets}}
    print("split:", results["split"])

    # 1. wording of the step question, on the tune half, long runs cut to fit as before
    print("\nstep wording on the tune half (exact step):")
    wording = {}
    for variant in STEP_VARIANTS:
        outcomes = {d: [step_outcome(i, variant, False) for i in tune if i["dataset"] == d] for d in datasets}
        per = {d: share(o["exact"] for o in outcomes[d]) for d in datasets}
        wording[variant] = {"per_dataset": per, "mean_of_datasets": sum(per.values()) / len(per),
                            "pooled": share(o["exact"] for d in datasets for o in outcomes[d])}
        print(f"  {variant:22s} " + "  ".join(f"{d} {pct(per[d])}" for d in datasets)
              + f"   mean of datasets {wording[variant]['mean_of_datasets']:.1%}, pooled {wording[variant]['pooled']:.1%}")
    best_wording = max(wording, key=lambda v: wording[v]["mean_of_datasets"])
    results["step_wording_tune"] = wording
    results["chosen_wording"] = best_wording
    print(f"  chosen: {best_wording}")

    # 2. windows for long runs, on the long runs of the tune half
    long_tune = [i for i in tune if sum(len(c) for _, c in i["steps"]) > STATE_BUDGET]
    trimmed = [step_outcome(i, best_wording, False) for i in long_tune]
    scanned = [step_outcome(i, best_wording, True) for i in long_tune]
    results["windows_tune"] = {"long_runs": len(long_tune),
                               "cut_to_fit": {"exact": sum(o["exact"] for o in trimmed), "within_1": sum(o["within_1"] for o in trimmed)},
                               "windows": {"exact": sum(o["exact"] for o in scanned), "within_1": sum(o["within_1"] for o in scanned)}}
    use_windows = (sum(o["exact"] for o in scanned), sum(o["within_1"] for o in scanned)) > \
                  (sum(o["exact"] for o in trimmed), sum(o["within_1"] for o in trimmed))
    results["chosen_windows"] = use_windows
    print(f"\nlong runs in the tune half ({len(long_tune)}): cut to fit {results['windows_tune']['cut_to_fit']}, "
          f"windows {results['windows_tune']['windows']} -> {'windows' if use_windows else 'cut to fit'}")

    # 3. category, on the AgentRx runs of the tune half
    with_category = [i for i in tune if i["human_category"]]
    print(f"\ncategory on the tune half ({len(with_category)} AgentRx runs):")
    category = {}
    offsets = {}
    for mode in ("choice_readme", "choice_paper", "nouls_paper"):
        scores = [category_answers(i, mode) for i in with_category]
        hits = sum(max(s, key=s.get) == i["human_category"] for s, i in zip(scores, with_category))
        category[mode] = hits / len(with_category)
        print(f"  {mode:24s} {hits}/{len(with_category)}")
        if mode == "nouls_paper":       # subtract each category's average yes-probability, estimated on the tune half
            offsets = {c: sum(s[c] for s in scores) / len(scores) for c in PAPER_CATEGORIES}
            hits = sum(max(s, key=lambda c: s[c] - offsets[c]) == i["human_category"] for s, i in zip(scores, with_category))
            category["nouls_paper_centred"] = hits / len(with_category)
            print(f"  {'nouls_paper_centred':24s} {hits}/{len(with_category)}")
    best_category = max(category, key=category.get)
    results["category_tune"] = category
    results["chosen_category"] = best_category
    print(f"  chosen: {best_category}")

    # 4. the test half, scored once: untuned against the chosen setup
    print(f"\ntest half: untuned -> tuned ({best_wording}, {'windows' if use_windows else 'cut to fit'}, agent read off the step, category {best_category})")
    print(f"{'dataset':18s} runs | step exact      within 1       | agent          | category")
    results["test"] = {}
    rows = []
    for d in datasets + ["whowhen (both)", "all"]:
        group = [i for i in test if d == "all" or i["dataset"] == d or (d == "whowhen (both)" and i["dataset"].startswith("whowhen"))]
        before = [step_outcome(i, "base", False) for i in group]
        after = [step_outcome(i, best_wording, use_windows) for i in group]
        agents = [(i, a, b) for i, a, b in zip(group, after, before) if i["human_agent"]]
        asked = [score_untuned(i, api_key())["answer"]["answers"]["agent"]["choice"] == i["human_agent"] for i, _, _ in agents]
        cats = [i for i in group if i["human_category"]]
        def category_hit(i, mode):
            s = category_answers(i, "nouls_paper" if mode == "nouls_paper_centred" else mode)
            return max(s, key=(lambda c: s[c] - offsets[c]) if mode == "nouls_paper_centred" else s.get) == i["human_category"]
        r = {"runs": len(group),
             "step_exact": [share(o["exact"] for o in before), share(o["exact"] for o in after)],
             "step_within_1": [share(o["within_1"] for o in before), share(o["within_1"] for o in after)],
             "agent": [share(asked), share(a["agent_from_step"] for _, a, _ in agents)],
             "category": [share(category_hit(i, "choice_readme") for i in cats), share(category_hit(i, best_category) for i in cats)],
             "counts": {"step_exact": [sum(o["exact"] for o in before), sum(o["exact"] for o in after)],
                        "agent": [sum(asked), sum(a["agent_from_step"] for _, a, _ in agents), len(agents)],
                        "category_runs": len(cats)}}
        results["test"][d] = r
        print(f"{d:18s} {len(group):4d} | {pct(r['step_exact'][0]):>4s} -> {pct(r['step_exact'][1]):>4s}    {pct(r['step_within_1'][0]):>4s} -> {pct(r['step_within_1'][1]):>4s}   | "
              f"{pct(r['agent'][0]):>4s} -> {pct(r['agent'][1]):>4s}   | {pct(r['category'][0]):>4s} -> {pct(r['category'][1]):>4s}")
        if d in datasets:
            rows += [{"dataset": d, "id": i["id"], "human_step": i["human_step"], "untuned_step": b["jev_step"],
                      "tuned_step": a["jev_step"], "tuned_step_probability": a["probability"]} for i, a, b in zip(group, after, before)]

    confident = [(a, i) for i in test for a in [step_outcome(i, best_wording, use_windows)]]
    results["test_by_probability"] = []
    print("\ntuned step answer on the test half, by the score Jev gave it:")
    for lo, hi in ((0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.0001)):
        inside = [a for a, _ in confident if lo <= a["probability"] < hi]
        if inside:
            results["test_by_probability"].append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": len(inside), "exact": share(a["exact"] for a in inside)})
            print(f"  {lo:.1f}-{min(hi, 1):.1f}  n={len(inside):3d}  exact {share(a['exact'] for a in inside):.0%}")

    with open(HERE / "tuned_test_scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    results["new_input_tokens_this_run"] = TOKENS
    (HERE / "tuning_results.json").write_text(json.dumps(results, indent=1))
    print(f"\nnew requests this run: {TOKENS} input tokens, ${TOKENS * USD_PER_INPUT_TOKEN:.4f} at list price")


if __name__ == "__main__":
    main()
