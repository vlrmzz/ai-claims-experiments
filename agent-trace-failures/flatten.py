"""Turn one run into plain text: what the customer was told, what the grader
expected, what the agent changed, and the conversation.

    python flatten.py       # writes data/flat/<trace_id>.txt for every failed run

The same text is what the reference labeller reads and what the scorer sends.
"""

import json

from traces import DATA, DOMAINS, failed, load_results, load_runs, write_tools

FLAT = DATA / "flat"


def call_text(name, arguments):
    args = ", ".join(f"{k}={json.dumps(v)}" for k, v in (arguments or {}).items())
    return f"{name}({args})"


def write_calls(run):
    """The state-changing calls the agent made, in order."""
    writes = set(write_tools(run["domain"]))
    return [c for m in run["sim"]["messages"] if m["role"] == "assistant"
            for c in (m.get("tool_calls") or []) if c["name"] in writes]


def grader_diff(run):
    """Expected write actions the agent did not make, and writes it made that were not expected."""
    writes = set(write_tools(run["domain"]))
    key = lambda name, arguments: name + json.dumps(arguments or {}, sort_keys=True)
    expected = [a["action"] for a in (run["sim"]["reward_info"].get("action_checks") or [])
                if a["action"]["name"] in writes]
    made = write_calls(run)
    made_keys = {key(c["name"], c.get("arguments")) for c in made}
    expected_keys = {key(a["name"], a.get("arguments")) for a in expected}
    missing = [a for a in expected if key(a["name"], a.get("arguments")) not in made_keys]
    extra = [c for c in made if key(c["name"], c.get("arguments")) not in expected_keys]
    return missing, extra


def conversation(run):
    lines = []
    for m in run["sim"]["messages"]:
        turn = m.get("turn_idx")
        if m["role"] == "tool":
            flag = " ERROR" if m.get("error") else ""
            lines.append(f"[{turn}] TOOL RESULT{flag}: {m.get('content') or ''}")
            continue
        who = "AGENT" if m["role"] == "assistant" else "CUSTOMER"
        if m.get("content"):
            lines.append(f"[{turn}] {who}: {m['content']}")
        for c in m.get("tool_calls") or []:
            lines.append(f"[{turn}] AGENT CALLS: {call_text(c['name'], c.get('arguments'))}")
    return "\n".join(lines)


def flatten(run):
    task, reward = run["task"], run["sim"]["reward_info"]
    instructions = task["user_scenario"]["instructions"]
    missing, extra = grader_diff(run)
    unsaid = [c["info"] for c in (reward.get("communicate_checks") or []) if not c["met"]]
    expected = [a["action"] for a in (reward.get("action_checks") or [])]

    out = [f"TRACE {run['trace_id']}  ({run['domain']} task {run['task_id']}, trial {run['trial']})", ""]
    out.append("== SCRIPT GIVEN TO THE SIMULATED CUSTOMER (the agent never sees this) ==")
    purpose = (task.get("description") or {}).get("purpose")
    if purpose:
        out.append(f"Task author's note: {purpose}")
    for field in ("reason_for_call", "known_info", "unknown_info", "task_instructions"):
        if instructions.get(field):
            out.append(f"{field}: {instructions[field]}")
    out += ["", "== WHAT THE GRADER EXPECTED =="]
    out.append("Expected actions, in order: " + ("; ".join(call_text(a["name"], a.get("arguments")) for a in expected) or "none"))
    assertions = (task.get("evaluation_criteria") or {}).get("nl_assertions") or []
    if assertions:
        out.append("Task author's assertions (not counted in the reward): " + " | ".join(assertions))
    out += ["", "== WHY THE RUN WAS MARKED FAILED =="]
    if (reward.get("db_check") or {}).get("db_match") is False:
        out.append("The final database differs from the database after the expected actions.")
        out.append("Expected change the agent did not make: " + ("; ".join(call_text(a["name"], a.get("arguments")) for a in missing) or "none"))
        out.append("Change the agent made that was not expected: " + ("; ".join(call_text(c["name"], c.get("arguments")) for c in extra) or "none"))
    if unsaid:
        out.append("Information the agent had to state but did not: " + ", ".join(unsaid))
    out += ["", "== CONVERSATION ==", conversation(run)]
    return "\n".join(out)


def main():
    FLAT.mkdir(exist_ok=True)
    runs = failed(load_runs())
    for run in runs:
        (FLAT / f"{run['trace_id']}.txt").write_text(flatten(run))
    for domain in DOMAINS:
        policy = load_results(domain)["info"]["environment_info"]["policy"]
        (FLAT / f"policy_{domain}.md").write_text(policy)
    size = sum(p.stat().st_size for p in FLAT.iterdir())
    print(f"{len(runs)} failed runs flattened into {FLAT}, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
