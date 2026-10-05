"""Loader for the tau2-bench result files fetched by fetch.py.

A "run" is one simulated conversation: one task, one trial. Each task was run
four times, so failed runs cluster on tasks and are not independent.
"""

import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
DOMAINS = ("airline", "retail")

# The parts of a task that decide what the simulated user says and what the
# grader accepts. reward_basis is left out: it differs between the three task
# versions for every task, as a global setting rather than a per-task fix.
USER_FIELDS = ("reason_for_call", "known_info", "unknown_info", "task_instructions")


def trace_id(domain, task_id, trial):
    return f"{domain}-{int(task_id):03d}-t{trial}"


def load_results(domain):
    path = DATA / f"traces_{domain}.json"
    if not path.exists():
        raise SystemExit(f"{path} is missing: run `python fetch.py` first")
    return json.loads(path.read_text())


def load_runs():
    """Every run of both domains, with a readable trace id attached."""
    runs = []
    for domain in DOMAINS:
        results = load_results(domain)
        tasks = {t["id"]: t for t in results["tasks"]}
        for sim in results["simulations"]:
            runs.append({
                "trace_id": trace_id(domain, sim["task_id"], sim["trial"]),
                "domain": domain,
                "task_id": sim["task_id"],
                "trial": sim["trial"],
                "sim_id": sim["id"],
                "reward": sim["reward_info"]["reward"],
                "sim": sim,
                "task": tasks[sim["task_id"]],
            })
    runs.sort(key=lambda r: r["trace_id"])
    return runs


def failed(runs):
    return [r for r in runs if r["reward"] < 1]


def load_tasks(version, domain):
    """version: 'original' (as run), 'amazon' (tau2-bench-verified) or 'sierra' (current main)."""
    if version == "original":
        tasks = load_results(domain)["tasks"]
    else:
        tasks = json.loads((DATA / f"tasks_{version}_{domain}.json").read_text())
    return {t["id"]: t for t in tasks}


def task_parts(task):
    instructions = (task.get("user_scenario") or {}).get("instructions") or {}
    criteria = task.get("evaluation_criteria") or {}
    return {
        "user_instructions": {k: (instructions.get(k) or "").strip() for k in USER_FIELDS},
        "expected_actions": [
            {"name": a.get("name"), "arguments": a.get("arguments")}
            for a in (criteria.get("actions") or [])
        ],
        "nl_assertions": criteria.get("nl_assertions") or [],
        "communicate_info": criteria.get("communicate_info") or [],
    }


def changed_parts(task_a, task_b):
    a, b = task_parts(task_a), task_parts(task_b)
    return [k for k in a if json.dumps(a[k], sort_keys=True) != json.dumps(b[k], sort_keys=True)]


def write_tools(domain):
    """Names of the state-changing tools, read from the benchmark's own tool file."""
    source = (DATA / f"tools_{domain}.py").read_text()
    return re.findall(r"@is_tool\(ToolType\.WRITE\)\s+def (\w+)", source)
