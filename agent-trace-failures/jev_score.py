"""Score every failed run against the failure patterns with Jev.

    python jev_score.py --dry-run     # build the requests, print sizes, send nothing
    python jev_score.py               # send them; raw answers cached in data/jev/

Jev (TypeSafe) is a decision model: it reads a state and
answers typed questions with probabilities, and writes no text. Each run is
sent twice, with two different states:

  graded  policy + the customer's script + the grader's expectation + the
          conversation. Questions: one yes/no per pattern, one choice of the
          main pattern, and whose fault the failed verdict was.
  blind   policy + conversation only, as a production trace would look.
          Questions: one yes/no for each pattern that concerns the agent's
          own behaviour, since the others cannot be seen without the script.

The key is read from TYPESAFE_API_KEY, or from ~/.config/typesafe/key.
"""

import argparse
import csv
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

from flatten import conversation, flatten
from traces import DATA, HERE, failed, load_results, load_runs

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
USD_PER_INPUT_TOKEN = 0.042 / 1e6   # list price; output tokens are free
CACHE = DATA / "jev"

FAULT_QUESTION = {
    "type": "choice",
    "instructions": ("This run was marked failed by the benchmark's grader. Reading `policy`, "
                     "`run` and the grader's expectation inside `run`, who is responsible for the failed verdict?"),
    "criteria": {
        "agent": "The agent broke the policy, used a tool wrongly, decided wrongly, or did not do something the customer clearly asked for and the policy allows.",
        "benchmark": "The agent followed the policy and served the customer. The verdict comes from a defect in the benchmark: the expected actions contradict the policy or the data, the grader rejects an equally valid outcome, or the simulated customer departed from its script.",
        "both": "The agent made a real error and the benchmark also has a defect that contributed.",
    },
}


def api_key():
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        path = pathlib.Path.home() / ".config" / "typesafe" / "key"
        if path.exists():
            key = path.read_text().strip()
    if not key:
        raise SystemExit("no key: set TYPESAFE_API_KEY or write it to ~/.config/typesafe/key")
    return key


def load_patterns():
    return json.loads((HERE / "patterns.json").read_text())


def noul(pattern):
    return {"type": "noul", "instructions": pattern["question"],
            "criteria": {"true": pattern["definition"], "false": "This does not happen in the run."}}


def requests_for(run, policy, patterns):
    graded = {f"has_{p['id']}": noul(p) for p in patterns}
    graded["main_pattern"] = {
        "type": "choice",
        "instructions": "This run was marked failed by the grader. Which one of these best describes why, judging `run` against `policy`?",
        "criteria": {p["id"]: p["definition"] for p in patterns},
    }
    graded["fault"] = FAULT_QUESTION
    blind = {f"has_{p['id']}": noul(p) for p in patterns if p["side"] != "benchmark"}
    return {
        "graded": {"model": MODEL, "state": {"policy": policy, "run": flatten(run)}, "questions": graded},
        "blind": {"model": MODEL, "state": {"policy": policy, "run": conversation(run)}, "questions": blind},
    }


def post(body, key, attempts=5):
    data = json.dumps(body).encode()
    for attempt in range(attempts):
        req = urllib.request.Request(URL, data=data, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                time.sleep(2 ** attempt)
                continue
            raise SystemExit(f"HTTP {e.code} from Jev: {detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only the first N runs")
    args = ap.parse_args()

    patterns = load_patterns()
    policies = {d: load_results(d)["info"]["environment_info"]["policy"] for d in ("airline", "retail")}
    runs = failed(load_runs())[: args.limit]
    CACHE.mkdir(exist_ok=True)

    if args.dry_run:
        sizes = [len(json.dumps(body)) for run in runs
                 for body in requests_for(run, policies[run["domain"]], patterns).values()]
        print(f"{len(runs)} runs, {len(sizes)} requests, {len(patterns)} patterns")
        print(f"request size in characters: median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)}, total {sum(sizes) / 1e6:.1f} M")
        return

    key = api_key()
    tokens = 0
    for i, run in enumerate(runs, 1):
        path = CACHE / f"{run['trace_id']}.json"
        if path.exists():
            continue
        result = {"trace_id": run["trace_id"]}
        for name, body in requests_for(run, policies[run["domain"]], patterns).items():
            answer = post(body, key)
            result[name] = answer
            tokens += answer["usage"]["input_tokens"]
        path.write_text(json.dumps(result, indent=1))
        print(f"{i}/{len(runs)} {run['trace_id']}  input tokens so far {tokens}")

    rows = []
    for run in runs:
        result = json.loads((CACHE / f"{run['trace_id']}.json").read_text())
        graded, blind = result["graded"]["answers"], result["blind"]["answers"]
        row = {"trace_id": run["trace_id"],
               "main_pattern": graded["main_pattern"]["choice"],
               "main_pattern_confidence": graded["main_pattern"]["confidence"],
               "fault": graded["fault"]["choice"],
               "fault_confidence": graded["fault"]["confidence"],
               "p_fault_benchmark": graded["fault"]["probabilities"]["benchmark"]}
        row.update({f"p_{p['id']}": graded[f"has_{p['id']}"]["noul"] for p in patterns})
        row.update({f"blind_p_{p['id']}": blind[f"has_{p['id']}"]["noul"] for p in patterns if p["side"] != "benchmark"})
        rows.append(row)
    with open(HERE / "jev_scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote jev_scores.csv ({len(rows)} runs); this session: {tokens} input tokens, "
          f"${tokens * USD_PER_INPUT_TOKEN:.4f} at list price")


if __name__ == "__main__":
    main()
