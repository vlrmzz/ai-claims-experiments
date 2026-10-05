"""Compare the task definitions the run used with two later revisions.

    python revisions.py     # writes task_revisions.csv

Two groups revised tau2-bench after this run: Amazon (tau2-bench-verified) and
Sierra itself (current main). For each task this records which parts changed.
A changed task is not proof that a failure on it was the benchmark's fault;
it is the reference the hand-coded "fault" column is checked against.
"""

import csv
from collections import Counter

from traces import DOMAINS, HERE, changed_parts, failed, load_runs, load_tasks


def table():
    runs = load_runs()
    n_failed = Counter((r["domain"], r["task_id"]) for r in failed(runs))
    rows = []
    for domain in DOMAINS:
        original = load_tasks("original", domain)
        amazon = load_tasks("amazon", domain)
        sierra = load_tasks("sierra", domain)
        for task_id in sorted(original, key=int):
            rows.append({
                "domain": domain,
                "task_id": task_id,
                "failed_runs_of_4": n_failed[(domain, task_id)],
                "amazon_changed": "; ".join(changed_parts(original[task_id], amazon[task_id])),
                "sierra_changed": "; ".join(changed_parts(original[task_id], sierra[task_id])),
            })
    return rows


def main():
    rows = table()
    with open(HERE / "task_revisions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    for domain in DOMAINS:
        d = [r for r in rows if r["domain"] == domain]
        a = sum(bool(r["amazon_changed"]) for r in d)
        s = sum(bool(r["sierra_changed"]) for r in d)
        both = sum(bool(r["amazon_changed"]) and bool(r["sierra_changed"]) for r in d)
        print(f"{domain}: {len(d)} tasks, changed by Amazon {a}, by Sierra {s}, by both {both}")
    f_runs = sum(r["failed_runs_of_4"] for r in rows)
    f_amazon = sum(r["failed_runs_of_4"] for r in rows if r["amazon_changed"])
    f_sierra = sum(r["failed_runs_of_4"] for r in rows if r["sierra_changed"])
    f_either = sum(r["failed_runs_of_4"] for r in rows if r["amazon_changed"] or r["sierra_changed"])
    print(f"failed runs: {f_runs}; on tasks later changed by Amazon {f_amazon}, "
          f"by Sierra {f_sierra}, by either {f_either}")


if __name__ == "__main__":
    main()
