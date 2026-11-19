# /// script
# requires-python = ">=3.10"
# dependencies = ["anthropic>=0.40"]
# ///
"""Baseline vs. verification harnesses on small Python coding tasks.

Conditions (run on every task, `--repeats` times each):
  baseline  one generation from the problem statement.
  harness   generate -> run the visible tests -> on failure, send the code and the test
            output back and ask for a critique and a fix. At most `--max-attempts` generations.
  selftest  as harness, but the model first writes its own test cases from the specification
            (without seeing any code), and the loop runs the visible tests plus those.

Every condition is scored the same way: the final code must pass the visible tests and the
held-out tests, which no condition ever sees. All conditions use the same first prompt, so the
first attempt of each loop is an independent replicate of the baseline: comparing them tells
you how much of any difference is just sampling noise.

Outputs: results.json (every attempt, raw), results.csv (one row per run), summary.md and
figures/chart.svg, in this folder for the easy set and in hard/ for the hard set.

Examples:
  python run.py --task-set hard                       # Anthropic API, needs ANTHROPIC_API_KEY
  python run.py --task-set hard --backend openrouter --model openai/gpt-4o-mini
  python run.py --task-set hard --backend cli         # the local `claude` CLI login
  python run.py --task-set hard --backend fake        # offline smoke test, no model
  python run.py --task-set hard --verify-references   # every reference solution passes its tests
"""

import argparse
import csv
import http.client
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK_SETS = {"easy": ROOT / "tasks", "hard": ROOT / "tasks_hard"}
CHECKER = ROOT / "check.py"
TEST_TIMEOUT_S = 10
MAX_FEEDBACK_CHARS = 3000
CONDITIONS = ["baseline", "harness", "selftest"]
LABELS = {"baseline": "Baseline", "harness": "Harness (visible tests)", "selftest": "Self-test harness"}
COLOURS = {"baseline": "#8c96a8", "harness": "#2f6fdf", "selftest": "#d9772b"}

SYSTEM_PROMPT = (
    "You are an expert Python programmer. Solve the task with a single self-contained Python "
    "module that uses only the standard library. Reply with the complete code in one "
    "```python fenced block."
)

TESTS_SYSTEM_PROMPT = (
    "You are an expert Python tester. You write precise test cases from a specification. "
    "Reply with one ```python fenced block."
)


def first_prompt(task):
    return f"{task['prompt']}\n\nReturn the complete solution."


def tests_prompt(task):
    return (
        f"{task['prompt']}\n\n"
        "No code has been written yet. Write test cases for this function from the specification "
        "above, so that they can check an implementation later. Cover every rule, edge case and "
        "error condition the specification states.\n\n"
        "Reply with one ```python fenced block that defines `SELF_CASES`: a list of 10 to 25 "
        "`(args, expected)` pairs. `args` is a tuple of positional arguments. `expected` is the "
        "exact return value, or an exception class such as `ValueError` if the call must raise it. "
        "Use only literals, simple expressions and exception classes: no imports, no function calls "
        "other than built-in constructors."
    )


def repair_prompt(task, code, test_output, own_tests=False):
    # The whole history goes into one user message, so every backend sees the same input.
    caveat = (
        "Some of these test cases were written from the specification before the code existed and "
        "may themselves be wrong. If a test contradicts the specification, follow the specification.\n\n"
        if own_tests else ""
    )
    return (
        f"{task['prompt']}\n\n"
        f"Here is your previous solution:\n```python\n{code}\n```\n\n"
        f"Running the test suite on it gave this output:\n```\n{test_output}\n```\n\n"
        f"{caveat}"
        "First explain briefly (2-4 sentences) what is wrong. Then give the complete "
        "corrected solution in one ```python fenced block."
    )


# --------------------------------------------------------------------------- tasks and tests

def load_tasks(tasks_dir, only=None):
    tasks = []
    for task_dir in sorted(p for p in tasks_dir.iterdir() if p.is_dir()):
        if only and task_dir.name not in only:
            continue
        meta = {}
        exec((task_dir / "tests.py").read_text(), meta)  # tests.py is plain data
        tasks.append({
            "id": task_dir.name,
            "dir": task_dir,
            "prompt": (task_dir / "prompt.md").read_text().strip(),
            "function": meta["FUNCTION"],
            "difficulty": meta["DIFFICULTY"],
            "n_visible": len(meta["CASES"]),
            "n_hidden": len(meta.get("HIDDEN", [])),
        })
    if not tasks:
        sys.exit(f"No tasks found in {tasks_dir} (filter: {only})")
    return tasks


def run_tests(task, code, which="all", tests_path=None):
    """Run test cases on `code` in a fresh temp dir. Returns (passed, output).

    which="visible" runs only CASES (what a loop may see); "all" adds the held-out HIDDEN cases.
    tests_path defaults to the task's own tests.py.
    """
    tests_path = tests_path or task["dir"] / "tests.py"
    with tempfile.TemporaryDirectory(prefix="vh_") as tmp:
        solution = Path(tmp) / "solution.py"
        solution.write_text(code)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(CHECKER), str(solution), str(tests_path), which],
                cwd=tmp, capture_output=True, text=True, timeout=TEST_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return False, f"Tests timed out after {TEST_TIMEOUT_S} s (infinite loop or very slow code)."
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output[:MAX_FEEDBACK_CHARS]


def write_self_tests(task, block, folder):
    """Turn the model's SELF_CASES block into two tests files for check.py.

    Returns (combined_path, self_only_path, n_cases, error). combined = the task's visible
    cases plus the model's; self_only = just the model's, used to grade the tests themselves.
    """
    header = (
        "import importlib.util as _u\n"
        f"_s = _u.spec_from_file_location('task_tests', {str(task['dir'] / 'tests.py')!r})\n"
        "_m = _u.module_from_spec(_s)\n_s.loader.exec_module(_m)\n"
        "FUNCTION = _m.FUNCTION\nDIFFICULTY = _m.DIFFICULTY\n"
    )
    combined, self_only = folder / "selftests_combined.py", folder / "selftests_only.py"
    combined.write_text(f"{header}{block}\nCASES = list(_m.CASES) + list(SELF_CASES)\n")
    self_only.write_text(f"{header}{block}\nCASES = list(SELF_CASES)\n")
    probe = (
        "import sys, runpy\n"
        "ns = runpy.run_path(sys.argv[1])\n"
        "cases = ns['CASES']\n"
        "assert isinstance(cases, list) and all(isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], tuple) "
        "for c in cases), 'SELF_CASES must be a list of (args_tuple, expected) pairs'\n"
        "print(len(cases))\n"
    )
    try:
        proc = subprocess.run([sys.executable, "-I", "-c", probe, str(self_only)],
                              capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, None, 0, "loading the self-written tests timed out"
    if proc.returncode != 0:
        return None, None, 0, (proc.stderr.strip().splitlines() or ["unknown error"])[-1][:200]
    return combined, self_only, int(proc.stdout.strip()), None


def extract_code(text):
    """Return the last ```python block (repairs put an explanation first), else None."""
    blocks = re.findall(r"```(?:python|py)\s*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        blocks = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
    return blocks[-1].strip() + "\n" if blocks else None


def failure_kind(output):
    """Coarse label for a failed attempt, used for the failure-pattern table."""
    if output.startswith("No code block"):
        return "no code block"
    if output.startswith("Tests timed out"):
        return "timeout"
    if output.startswith("Could not load"):
        return "syntax error" if "SyntaxError" in output else "load error"
    raised = re.search(r"but raised (\w+)", output)
    if raised:
        return f"crash ({raised.group(1)})"
    if "expected raise" in output:
        return "missing exception"
    return "wrong answer"


def first_failing_case(output):
    """The call of the first failing case, e.g. "evaluate('-2^2')", or a short reason."""
    for line in output.splitlines():
        match = re.match(r"FAIL (.*?\)): ", line)
        if match:
            return match.group(1)[:70]
        if line.startswith(("Tests timed out", "No code block", "Could not load")):
            return line[:40]
    return "?"


# --------------------------------------------------------------------------- backends

def make_backend(args):
    """Return generate(task, system, user, attempt) -> dict(text, input_tokens, output_tokens, cost).

    `attempt` is 0 for the test-writing call of the selftest condition, else 1, 2, 3.
    Only the fake backend looks at it.
    """
    if args.backend == "api":
        import anthropic

        client = anthropic.Anthropic(max_retries=5)  # reads ANTHROPIC_API_KEY from the environment

        def generate(task, system, user, attempt):
            kwargs = {
                "model": args.model,
                "max_tokens": 8000,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
            if args.temperature is not None:
                kwargs["temperature"] = args.temperature
            response = client.messages.create(**kwargs)
            return {
                "text": "".join(b.text for b in response.content if b.type == "text"),
                "stop_reason": response.stop_reason,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        return generate

    if args.backend == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            sys.exit("Set OPENROUTER_API_KEY to use the openrouter backend.")

        def generate(task, system, user, attempt):
            body = {
                "model": args.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": 8000,
                "usage": {"include": True},  # ask OpenRouter to report the cost of the call
            }
            if args.temperature is not None:
                body["temperature"] = args.temperature
            if not args.thinking:
                # A plain one-shot answer: switch reasoning off where the model allows it.
                # Models that always reason ignore this; their reasoning tokens are recorded.
                body["reasoning"] = {"enabled": False}
            request = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "X-Title": "ai-claims-experiments verification-harness"},
            )
            error = None
            for retry in range(6):
                try:
                    with urllib.request.urlopen(request, timeout=300) as response:
                        data = json.loads(response.read())
                    if "error" in data or not data.get("choices"):
                        error = str(data.get("error", "empty response"))[:300]
                    else:
                        usage = data.get("usage") or {}
                        message = data["choices"][0]["message"]
                        return {
                            "text": message.get("content") or "",
                            "stop_reason": data["choices"][0].get("finish_reason"),
                            "input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0),
                            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                            "cost": usage.get("cost", 0.0),
                            "provider": data.get("provider"),
                        }
                except urllib.error.HTTPError as exc:
                    error = f"HTTP {exc.code}: {exc.read()[:300].decode(errors='replace')}"
                    if exc.code in (400, 401, 402, 403, 404):
                        break  # not worth retrying: bad request, key, credit or model id
                except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
                    # Dropped or reset connections, timeouts, truncated bodies: all worth a retry.
                    error = f"{type(exc).__name__}: {exc}"
                time.sleep(min(60, 5 * 2 ** retry))
            raise RuntimeError(f"OpenRouter call failed: {error}")

        return generate

    if args.backend == "cli":
        # Headless Claude Code with every tool disabled, so the model cannot run code itself.
        # The CLI has no temperature setting; results record temperature as null.
        workdir = Path(tempfile.mkdtemp(prefix="vh_cli_"))  # empty dir: no CLAUDE.md is picked up

        def generate(task, system, user, attempt):
            cmd = [
                "claude", "-p", user, "--model", args.model, "--system-prompt", system,
                "--tools", "", "--setting-sources", "", "--strict-mcp-config",
                "--disable-slash-commands", "--no-session-persistence", "--output-format", "json",
                # Claude Code thinks before answering by default. The experiment is about a plain
                # one-shot answer (as with the api backend), so thinking is off unless asked for.
                "--settings", json.dumps({"alwaysThinkingEnabled": args.thinking}),
            ]
            for retry in range(3):
                proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=600)
                try:
                    data = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    data = {"is_error": True, "result": (proc.stdout + proc.stderr)[-500:]}
                if not data.get("is_error"):
                    usage = data.get("usage", {})
                    return {
                        "text": data.get("result", ""),
                        "stop_reason": data.get("stop_reason"),
                        "input_tokens": usage.get("input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                    }
                time.sleep(5 * (retry + 1))
            raise RuntimeError(f"claude CLI failed: {data.get('result')}")

        return generate

    if args.backend == "fake":
        # Offline smoke test: a broken stub on the first attempt, the reference on repairs, and
        # one correct plus one wrong self-written test. Exercises every code path without a
        # model. Its numbers mean nothing.
        def generate(task, system, user, attempt):
            if attempt == 0:
                ns = {}
                exec((task["dir"] / "tests.py").read_text(), ns)
                (args0, expected) = ns["CASES"][0]
                block = (f"SELF_CASES = [({args0!r}, {expected!r}), ({args0!r}, 'deliberately wrong')]"
                         if not (isinstance(expected, type) and issubclass(expected, BaseException))
                         else f"SELF_CASES = [({args0!r}, {expected.__name__})]")
                return {"text": f"```python\n{block}\n```", "input_tokens": len(user) // 4, "output_tokens": 20}
            if attempt == 1:
                code = f"def {task['function']}(*args):\n    return None\n"
            else:
                code = (task["dir"] / "reference.py").read_text()
            return {"text": f"Stub.\n```python\n{code}```", "stop_reason": "end_turn",
                    "input_tokens": len(user) // 4, "output_tokens": len(code) // 4}

        return generate

    raise ValueError(args.backend)


# --------------------------------------------------------------------------- conditions

def attempt_once(generate, task, user_prompt, n, loop_tests=None):
    """One generation and its tests. loop_tests: the tests file the loop sees (default: visible)."""
    started = time.time()
    reply = generate(task, SYSTEM_PROMPT, user_prompt, n)
    code = extract_code(reply["text"])
    if code is None:
        passed = passed_visible = passed_loop = False
        output = feedback = "No code block found in the reply."
    else:
        passed_visible, visible_out = run_tests(task, code, "visible")
        if loop_tests:
            passed_loop, feedback = run_tests(task, code, "visible", loop_tests)  # visible + own tests
        else:
            passed_loop, feedback = passed_visible, visible_out
        passed, output = run_tests(task, code, "all")  # the score: visible plus held-out cases
    return {
        "attempt": n,
        "passed": passed,
        "passed_visible": passed_visible,
        "passed_loop": passed_loop,
        "code": code,
        "feedback": feedback,
        "test_output": output,
        "failure_kind": None if passed else failure_kind(output),
        "response": reply["text"],
        "stop_reason": reply.get("stop_reason"),
        "input_tokens": reply.get("input_tokens", 0),
        "output_tokens": reply.get("output_tokens", 0),
        "reasoning_tokens": reply.get("reasoning_tokens", 0),
        "cost": reply.get("cost", 0.0),
        "seconds": round(time.time() - started, 2),
    }


def write_tests(generate, task, folder):
    """selftest only: the model writes test cases from the spec. Returns a record of the step."""
    started = time.time()
    reply = generate(task, TESTS_SYSTEM_PROMPT, tests_prompt(task), 0)
    block = extract_code(reply["text"])
    record = {
        "response": reply["text"],
        "input_tokens": reply.get("input_tokens", 0),
        "output_tokens": reply.get("output_tokens", 0),
        "reasoning_tokens": reply.get("reasoning_tokens", 0),
        "cost": reply.get("cost", 0.0),
        "valid": False, "n_cases": 0, "n_correct": 0, "error": None, "combined_path": None,
    }
    if block is None:
        record["error"] = "no code block"
    else:
        combined, self_only, n_cases, error = write_self_tests(task, block, folder)
        record.update(n_cases=n_cases, error=error, valid=error is None and n_cases > 0)
        if record["valid"]:
            record["combined_path"] = str(combined)
            # Grade the tests themselves: how many does the reference solution pass?
            _, ref_out = run_tests(task, (task["dir"] / "reference.py").read_text(), "visible", self_only)
            match = re.search(r"(\d+)/(\d+) test cases passed", ref_out)
            record["n_correct"] = int(match.group(1)) if match else 0
    record["seconds"] = round(time.time() - started, 2)
    return record


def run_condition(generate, task, condition, repeat, max_attempts):
    with tempfile.TemporaryDirectory(prefix="vh_self_") as folder:
        test_writing, loop_tests = None, None
        if condition == "selftest":
            test_writing = write_tests(generate, task, Path(folder))
            loop_tests = test_writing["combined_path"]  # None if the tests were unusable: visible only
        attempts = [attempt_once(generate, task, first_prompt(task), 1, loop_tests)]
        if condition != "baseline":
            # A loop only knows about the tests it runs: it stops as soon as those pass.
            while not attempts[-1]["passed_loop"] and len(attempts) < max_attempts:
                last = attempts[-1]
                prompt = repair_prompt(task, last["code"] or last["response"], last["feedback"],
                                       own_tests=loop_tests is not None)
                attempts.append(attempt_once(generate, task, prompt, len(attempts) + 1, loop_tests))
    final = attempts[-1]
    if test_writing:
        test_writing.pop("combined_path")
    return {
        "task_id": task["id"],
        "difficulty": task["difficulty"],
        "condition": condition,
        "repeat": repeat,
        "success": final["passed"],
        "attempts_used": len(attempts),
        "final_code": final["code"],
        "errors": [a["test_output"] for a in attempts if not a["passed"]],
        "test_writing": test_writing,
        "attempts": attempts,
    }


# --------------------------------------------------------------------------- stats

def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the two discordant-pair counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def pct(x):
    return f"{100 * x:.0f}%"


def rate_row(label, successes, n):
    lo, hi = wilson(successes, n)
    return f"| {label} | {successes}/{n} | {pct(successes / n if n else 0)} | {pct(lo)}–{pct(hi)} |"


def loop_passed(attempt):
    """Did this attempt pass the tests its loop runs? (Older result files lack some fields.)"""
    return attempt.get("passed_loop", attempt.get("passed_visible", attempt["passed"]))


def correct_at(run, k):
    """Was the code correct at attempt k? A loop that stopped earlier keeps its last code."""
    return run["attempts"][min(k, len(run["attempts"])) - 1]["passed"]


def calls_of(group):
    """Every model call in a group of runs: test writing (selftest) and code attempts."""
    calls = [a for r in group for a in r["attempts"]]
    calls += [r["test_writing"] for r in group if r.get("test_writing")]
    return calls


def summarize(runs, tasks, config):
    conds = [c for c in config["conditions"] if any(r["condition"] == c for r in runs)]
    loops = [c for c in conds if c != "baseline"]
    by = {c: [r for r in runs if r["condition"] == c] for c in conds}
    max_attempts = config["max_attempts"]
    L = []
    L.append(f"# Results: {config['run_name']}\n")
    temp = "not set" if config["temperature"] is None else config["temperature"]
    thinking = "on" if config.get("thinking") else "off"
    L.append(f"Backend `{config['backend']}`, model `{config['model']}`, thinking {thinking}, temperature {temp}, "
             f"{len(tasks)} tasks × {config['repeats']} repeats, loops stop after {max_attempts} code attempts.\n")

    L.append("## Success rate\n")
    L.append("| Condition | Passed | Rate | 95% CI (Wilson) |")
    L.append("|---|---|---|---|")
    for c in conds:
        group = by[c]
        if c != "baseline":
            L.append(rate_row(f"{LABELS[c]}, first attempt only", sum(r["attempts"][0]["passed"] for r in group), len(group)))
        L.append(rate_row(LABELS[c] if c == "baseline" else f"{LABELS[c]} (≤{max_attempts} attempts)",
                          sum(r["success"] for r in group), len(group)))
    L.append("")
    L.append("Every first attempt uses the same prompt as the baseline. Differences between those rows "
             "are sampling noise, not the harness.\n")

    n_visible = sum(t["n_visible"] for t in tasks)
    n_hidden = sum(t["n_hidden"] for t in tasks)
    if n_hidden:
        L.append("## What the loop saw vs. what was true\n")
        L.append(f"Loops see the {n_visible} visible test cases (and, for the self-test harness, the model's own "
                 f"cases); {n_hidden} more are held out and used only for scoring.\n")
        L.append("| Condition | Final code passes the loop's tests | Passes visible | Passes held-out too | Loop's tests pass, code still wrong |")
        L.append("|---|---|---|---|---|")
        for c in conds:
            group = by[c]
            loop_ok = sum(loop_passed(r["attempts"][-1]) for r in group)
            vis = sum(r["attempts"][-1]["passed_visible"] for r in group)
            both = sum(r["success"] for r in group)
            wrong = sum(loop_passed(r["attempts"][-1]) and not r["success"] for r in group)
            L.append(f"| {LABELS[c]} | {f'{loop_ok}/{len(group)}' if c != 'baseline' else '–'} | {vis}/{len(group)} | "
                     f"{both}/{len(group)} | {wrong if c != 'baseline' else '–'} |")
        L.append("")

    if "selftest" in conds:
        tw = [r["test_writing"] for r in by["selftest"]]
        valid = [t for t in tw if t["valid"]]
        n_cases = sum(t["n_cases"] for t in valid)
        n_correct = sum(t["n_correct"] for t in valid)
        L.append("## The model's own tests\n")
        L.append(f"- Usable test files: {len(valid)}/{len(tw)} (the rest fell back to the visible tests only)")
        if valid:
            L.append(f"- Test cases written: {n_cases} ({n_cases / len(valid):.1f} per run)")
            L.append(f"- Cases the reference solution passes, i.e. correct tests: {n_correct}/{n_cases} "
                     f"({pct(n_correct / n_cases) if n_cases else '–'})")
            L.append(f"- Runs where every self-written case was correct: {sum(t['n_correct'] == t['n_cases'] for t in valid)}/{len(valid)}")
        errors = Counter(t["error"] for t in tw if t["error"])
        if errors:
            L.append("- Why test files were unusable: " + "; ".join(f"{e} ({n})" for e, n in errors.most_common(3)))
        L.append("")

    L.append("## By difficulty\n")
    L.append("| Difficulty | " + " | ".join(LABELS[c] for c in conds) + " |")
    L.append("|---" * (len(conds) + 1) + "|")
    for level in ("easy", "medium", "hard"):
        cells = []
        for c in conds:
            group = [r for r in by[c] if r["difficulty"] == level]
            cells.append(f"{sum(r['success'] for r in group)}/{len(group)}")
        if any(r["difficulty"] == level for r in runs):
            L.append(f"| {level} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## Per task\n")
    L.append("| Task | Difficulty | " + " | ".join(LABELS[c] for c in conds)
             + "".join(f" | {LABELS[c]}: mean attempts" for c in loops) + " |")
    L.append("|---" * (len(conds) + len(loops) + 2) + "|")
    for t in tasks:
        cells = []
        for c in conds:
            group = [r for r in by[c] if r["task_id"] == t["id"]]
            cells.append(f"{sum(r['success'] for r in group)}/{len(group)}")
        for c in loops:
            group = [r for r in by[c] if r["task_id"] == t["id"]]
            cells.append(f"{sum(r['attempts_used'] for r in group) / len(group):.2f}")
        L.append(f"| {t['id']} | {t['difficulty']} | " + " | ".join(cells) + " |")
    L.append("")

    cumulative = {}
    if loops:
        L.append("## Loop attempts\n")
        L.append("| Condition | Mean attempts | Code correct at attempt 1 / 2 / 3 | Needed a repair | Repair ended correct | Repair ended with loop's tests passing but code wrong | Repair never passed the loop's tests | Loop broke code that was correct |")
        L.append("|---|---|---|---|---|---|---|---|")
        for c in loops:
            group = by[c]
            cumulative[c] = [sum(correct_at(r, k) for r in group) / len(group) for k in range(1, max_attempts + 1)]
            repaired = [r for r in group if not loop_passed(r["attempts"][0])]
            ok = sum(r["success"] for r in repaired)
            wrong = sum(loop_passed(r["attempts"][-1]) and not r["success"] for r in repaired)
            never = sum(not loop_passed(r["attempts"][-1]) for r in repaired)
            broke = sum(r["attempts"][0]["passed"] and not r["success"] for r in group)
            L.append(f"| {LABELS[c]} | {sum(r['attempts_used'] for r in group) / len(group):.2f} | "
                     + " / ".join(pct(x) for x in cumulative[c])
                     + f" | {len(repaired)} | {ok} | {wrong} | {never} | {broke} |")
        L.append("")
        L.append("A loop keeps going while its own tests fail, so with wrong self-written tests it can rewrite "
                 "code that was already correct; the last column counts the times that made it wrong.\n")

    L.append("## Paired comparisons\n")
    L.append("Same task and same repeat. Discordant pairs are the ones where exactly one condition passed.\n")
    L.append("| Comparison | Both pass | Only first | Only second | Both fail | McNemar p |")
    L.append("|---|---|---|---|---|---|")
    outcome = {(r["task_id"], r["repeat"], r["condition"]): r["success"] for r in runs}
    pairs_to_compare = [(c, "baseline") for c in loops] + ([("selftest", "harness")] if {"selftest", "harness"} <= set(conds) else [])
    for a, b in pairs_to_compare:
        pairs = Counter((outcome[(t["id"], rep, a)], outcome[(t["id"], rep, b)])
                        for t in tasks for rep in range(config["repeats"]))
        L.append(f"| {LABELS[a]} vs. {LABELS[b]} | {pairs[(True, True)]} | {pairs[(True, False)]} | "
                 f"{pairs[(False, True)]} | {pairs[(False, False)]} | {mcnemar_exact(pairs[(True, False)], pairs[(False, True)]):.3f} |")
    L.append("")
    L.append("The repeats of one task are not independent, so these p-values are optimistic. The per-task "
             "table is the more honest view.\n")

    L.append("## Failure patterns\n")
    L.append("Final code that failed, by kind:\n")
    L.append("| Kind | " + " | ".join(LABELS[c] for c in conds) + " |")
    L.append("|---" * (len(conds) + 1) + "|")
    kinds = {c: Counter(r["attempts"][-1]["failure_kind"] for r in by[c] if not r["success"]) for c in conds}
    for kind in sorted(set().union(*kinds.values())):
        L.append(f"| {kind} | " + " | ".join(str(kinds[c].get(kind, 0)) for c in conds) + " |")
    L.append("")
    L.append("Most common first failing case of the final code, per task (count over all conditions):\n")
    for t in tasks:
        failing = Counter(first_failing_case(r["attempts"][-1]["test_output"])
                          for r in runs if r["task_id"] == t["id"] and not r["success"])
        if failing:
            L.append(f"- {t['id']}: " + ", ".join(f"`{case}` ({n})" for case, n in failing.most_common(3)))
    L.append("")

    L.append("## Cost\n")
    L.append("| Condition | Model calls | Input tokens | Output tokens | Reasoning tokens | Cost (USD) | Time (s) |")
    L.append("|---|---|---|---|---|---|---|")
    for c in conds:
        calls = calls_of(by[c])
        L.append(f"| {LABELS[c]} | {len(calls)} | {sum(a['input_tokens'] for a in calls):,} | "
                 f"{sum(a['output_tokens'] for a in calls):,} | {sum(a.get('reasoning_tokens', 0) for a in calls):,} | "
                 f"{sum(a.get('cost', 0) or 0 for a in calls):.3f} | {sum(a['seconds'] for a in calls):.0f} |")
    L.append("")
    return "\n".join(L), cumulative


def chart_svg(runs, tasks, cumulative, config):
    """Two panels: per-task success for each condition, and each loop's pass rate by attempt."""
    conds = [c for c in config["conditions"] if any(r["condition"] == c for r in runs)]
    groups = []
    for t in tasks + [{"id": "ALL"}]:
        sel = [r for r in runs if t["id"] == "ALL" or r["task_id"] == t["id"]]
        rates = []
        for c in conds:
            mine = [r for r in sel if r["condition"] == c]
            rates.append(sum(r["success"] for r in mine) / max(1, len(mine)))
        groups.append((t["id"].split("_", 1)[-1] if t["id"] != "ALL" else "ALL", rates))
    base_rate = groups[-1][1][conds.index("baseline")] if "baseline" in conds else None

    W, H, top, plot_h = 960, 380, 54, 220
    left1, w1 = 50, 620
    gw = w1 / len(groups)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           'font-family="system-ui, -apple-system, sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="{left1}" y="22" font-size="14" font-weight="600" fill="#1d2330">Success rate per task</text>',
           f'<text x="{left1}" y="38" fill="#5b6475">{config["model"]} · {config["repeats"]} repeats · '
           f'loops ≤{config["max_attempts"]} attempts · scored on held-out tests</text>']
    for frac in (0, 0.5, 1):
        y = top + plot_h * (1 - frac)
        out.append(f'<line x1="{left1}" x2="{left1 + w1}" y1="{y}" y2="{y}" stroke="#e3e6ec"/>')
        out.append(f'<text x="{left1 - 6}" y="{y + 4}" text-anchor="end" fill="#5b6475">{pct(frac)}</text>')
    for i, (label, rates) in enumerate(groups):
        bw = gw * 0.7 / len(conds)
        x = left1 + i * gw + gw * 0.15
        for j, (c, val) in enumerate(zip(conds, rates)):
            bh = plot_h * val
            out.append(f'<rect x="{x + j * bw:.1f}" y="{top + plot_h - bh:.1f}" width="{bw - 1:.1f}" '
                       f'height="{bh:.1f}" fill="{COLOURS[c]}" rx="1.5"/>')
        cx = left1 + i * gw + gw / 2
        weight = "600" if label == "ALL" else "400"
        out.append(f'<text x="{cx:.1f}" y="{top + plot_h + 14}" text-anchor="end" fill="#1d2330" '
                   f'font-weight="{weight}" transform="rotate(-35 {cx:.1f} {top + plot_h + 14})">{label}</text>')

    # Panel 2: each loop's cumulative pass rate by attempt, the baseline as a dashed line.
    left2, w2 = 740, 190
    out.append(f'<text x="{left2 - 10}" y="22" font-size="14" font-weight="600" fill="#1d2330">Loops by attempt</text>')
    out.append(f'<line x1="{left2}" x2="{left2 + w2}" y1="{top + plot_h}" y2="{top + plot_h}" stroke="#e3e6ec"/>')
    loops = list(cumulative)
    if loops:
        k_max = len(cumulative[loops[0]])
        slot = w2 / k_max
        bw = slot * 0.7 / len(loops)
        for k in range(k_max):
            for j, c in enumerate(loops):
                val = cumulative[c][k]
                bh = plot_h * val
                x = left2 + k * slot + slot * 0.15 + j * bw
                out.append(f'<rect x="{x:.1f}" y="{top + plot_h - bh:.1f}" width="{bw - 1:.1f}" height="{bh:.1f}" '
                           f'fill="{COLOURS[c]}" rx="1.5"/>')
                out.append(f'<text x="{x + bw / 2:.1f}" y="{top + plot_h - bh - 4:.1f}" text-anchor="middle" '
                           f'font-size="9" fill="#1d2330">{pct(val)}</text>')
            out.append(f'<text x="{left2 + k * slot + slot / 2:.1f}" y="{top + plot_h + 14}" text-anchor="middle" '
                       f'fill="#5b6475">≤{k + 1}</text>')
    if base_rate is not None:
        y = top + plot_h * (1 - base_rate)
        out.append(f'<line x1="{left2}" x2="{left2 + w2}" y1="{y:.1f}" y2="{y:.1f}" stroke="{COLOURS["baseline"]}" '
                   'stroke-width="2" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{left2 - 10}" y="38" fill="#5b6475">dashed line: baseline {pct(base_rate)}</text>')

    ly = H - 22
    for k, c in enumerate(conds):
        out.append(f'<rect x="{left1 + k * 170}" y="{ly - 9}" width="10" height="10" fill="{COLOURS[c]}" rx="1.5"/>')
        out.append(f'<text x="{left1 + k * 170 + 15}" y="{ly}" fill="#1d2330">{LABELS[c]}</text>')
    out.append("</svg>")
    return "\n".join(out)


# --------------------------------------------------------------------------- main

def verify_references(tasks):
    ok = True
    for task in tasks:
        passed, output = run_tests(task, (task["dir"] / "reference.py").read_text())
        print(f"{'PASS' if passed else 'FAIL'}  {task['id']}: {output.splitlines()[-1]}")
        ok &= passed
    return ok


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend", choices=["api", "openrouter", "cli", "fake"],
                   default="api" if os.environ.get("ANTHROPIC_API_KEY") else "cli",
                   help="api: Anthropic SDK (default when ANTHROPIC_API_KEY is set); openrouter: any "
                        "OpenRouter model (needs OPENROUTER_API_KEY); cli: local `claude` CLI; fake: offline smoke test")
    p.add_argument("--model", default="claude-haiku-4-5", help="model id for the backend")
    p.add_argument("--temperature", type=lambda s: None if s.lower() == "none" else float(s), default=0.2,
                   help="sampling temperature for the api and openrouter backends; 'none' to omit "
                        "(required for models that reject it, e.g. claude-opus-5-5)")
    p.add_argument("--thinking", action="store_true",
                   help="cli and openrouter backends: let the model reason before answering (off by default)")
    p.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=CONDITIONS)
    p.add_argument("--repeats", type=int, default=3, help="runs per task per condition")
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--workers", type=int, default=4, help="runs executed in parallel")
    p.add_argument("--task-set", choices=sorted(TASK_SETS), default="easy",
                   help="easy: tasks/ (the first run); hard: tasks_hard/, with held-out tests")
    p.add_argument("--tasks", nargs="*", help="only these task ids (default: all)")
    p.add_argument("--out", type=Path,
                   help="where to write results (default: this folder for easy, hard/ for hard; "
                        "_out/<set> for the fake backend)")
    p.add_argument("--max-cost", type=float,
                   help="stop once the reported cost (USD) of this run reaches this amount; only whole "
                        "repeats are kept, so every condition covers the same tasks")
    p.add_argument("--overwrite", action="store_true", help="replace an existing results.json in --out")
    p.add_argument("--resume", action="store_true",
                   help="continue an interrupted run: keep the runs saved in --out/partial.jsonl, do the rest")
    p.add_argument("--verify-references", action="store_true", help="check reference solutions and exit")
    p.add_argument("--summarize", type=Path, metavar="DIR",
                   help="rebuild summary.md and figures/chart.svg from DIR/results.json, without calling a model")
    return p.parse_args()


def resummarize(out_dir):
    data = json.loads((out_dir / "results.json").read_text())
    config, runs = data["config"], data["runs"]
    config.setdefault("conditions", ["baseline", "harness"])  # result files from before selftest existed
    tasks = load_tasks(TASK_SETS[config.get("task_set", "easy")], config["tasks"])
    summary, cumulative = summarize(runs, tasks, config)
    (out_dir / "summary.md").write_text(summary)
    (out_dir / "figures").mkdir(exist_ok=True)
    (out_dir / "figures" / "chart.svg").write_text(chart_svg(runs, tasks, cumulative, config))
    print(f"Rebuilt summary.md and figures/chart.svg in {out_dir}")


def main():
    args = parse_args()
    if args.summarize:
        return resummarize(args.summarize)
    tasks = load_tasks(TASK_SETS[args.task_set], args.tasks)
    if args.verify_references:
        sys.exit(0 if verify_references(tasks) else 1)
    if args.backend == "cli":
        if not shutil.which("claude"):
            sys.exit("No ANTHROPIC_API_KEY set and no `claude` CLI found. Set ANTHROPIC_API_KEY or pass --backend fake.")
        args.temperature = None
    if args.backend == "fake":
        args.model, args.temperature = "fake", None
    conditions = [c for c in CONDITIONS if c in args.conditions]

    if args.backend == "fake":
        out_dir = args.out or ROOT / "_out" / args.task_set
    else:
        out_dir = args.out or (ROOT if args.task_set == "easy" else ROOT / args.task_set)
    if (out_dir / "results.json").exists() and not args.overwrite:
        # The saved full run cost money to make; a partial or test run must not replace it by accident.
        sys.exit(f"{out_dir / 'results.json'} exists. Pass --out somewhere else, or --overwrite to replace it.")
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    run_name = f"{args.task_set} tasks, {args.backend} {args.model}, {datetime.now():%Y-%m-%d}"
    config = {"run_name": run_name, "task_set": args.task_set, "backend": args.backend, "model": args.model,
              "thinking": args.thinking if args.backend in ("cli", "openrouter") else False,
              "temperature": args.temperature, "conditions": conditions, "repeats": args.repeats,
              "max_attempts": args.max_attempts, "tasks": [t["id"] for t in tasks],
              "started": datetime.now().isoformat(timespec="seconds")}

    # Every finished run is appended here at once, so a crash never loses paid-for work.
    partial = out_dir / "partial.jsonl"
    runs = []
    if partial.exists():
        if not args.resume:
            sys.exit(f"{partial} holds runs from an interrupted run. Pass --resume to continue it, "
                     "or delete the file to start again.")
        runs = [json.loads(line) for line in partial.read_text().splitlines() if line.strip()]
        print(f"Resuming: {len(runs)} runs already saved in {partial}", flush=True)
    done = {(r["task_id"], r["condition"], r["repeat"]) for r in runs}

    generate = make_backend(args)
    jobs = [(t, cond, rep) for rep in range(args.repeats) for t in tasks for cond in conditions
            if (t["id"], cond, rep) not in done]
    print(f"{run_name}: {len(jobs)} runs to do ({len(tasks)} tasks × {len(conditions)} conditions × "
          f"{args.repeats} repeats, {len(done)} already done)", flush=True)

    spent, stopped = sum(a.get("cost", 0) or 0 for a in calls_of(runs)), False
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        # Jobs are ordered repeat by repeat, so a budget stop loses the last repeats, not whole tasks.
        futures = {pool.submit(run_condition, generate, t, cond, rep, args.max_attempts): (t, cond, rep)
                   for t, cond, rep in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            t, cond, rep = futures[fut]
            if fut.cancelled():
                continue
            try:
                r = fut.result()
            except Exception as exc:  # an API/CLI failure is not a model failure: stop loudly
                pool.shutdown(cancel_futures=True)
                sys.exit(f"Run {t['id']}/{cond}/r{rep} failed: {type(exc).__name__}: {exc}\n"
                         f"The {len(runs)} finished runs are saved; rerun the same command with --resume.")
            runs.append(r)
            with open(partial, "a") as f:
                f.write(json.dumps(r) + "\n")
            spent += sum(a.get("cost", 0) or 0 for a in calls_of([r]))
            print(f"[{i:3}/{len(jobs)}] {r['task_id']:17} {cond:8} r{rep}  "
                  f"{'PASS' if r['success'] else 'fail'}  attempts={r['attempts_used']}"
                  + (f"  ${spent:.3f}" if spent else ""), flush=True)
            if args.max_cost is not None and spent >= args.max_cost and not stopped:
                stopped = True
                print(f"Budget of ${args.max_cost:.2f} reached: cancelling the remaining runs "
                      "(the ones already running will finish).", flush=True)
                for other in futures:
                    other.cancel()

    if stopped:
        # Keep only repeats in which every task ran under every condition.
        complete = [rep for rep in range(args.repeats)
                    if sum(r["repeat"] == rep for r in runs) == len(tasks) * len(conditions)]
        runs = [r for r in runs if r["repeat"] in complete]
        runs = [dict(r, repeat=complete.index(r["repeat"])) for r in runs]
        config.update(repeats=len(complete), stopped_by_budget=True)
        if not complete:
            sys.exit(f"Budget reached before one full repeat finished (spent ${spent:.3f}). Nothing written.")
        print(f"Kept {len(complete)} complete repeat(s).", flush=True)
    config["cost_usd"] = round(spent, 4)

    runs.sort(key=lambda r: (r["task_id"], conditions.index(r["condition"]), r["repeat"]))
    config["finished"] = datetime.now().isoformat(timespec="seconds")
    (out_dir / "results.json").write_text(json.dumps({"config": config, "runs": runs}, indent=2))
    partial.unlink(missing_ok=True)  # results.json now holds everything
    with open(out_dir / "results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "difficulty", "condition", "repeat", "success", "attempts_used",
                    "final_failure_kind", "self_tests", "self_tests_correct", "errors", "final_code"])
        for r in runs:
            tw = r.get("test_writing") or {}
            w.writerow([r["task_id"], r["difficulty"], r["condition"], r["repeat"], r["success"],
                        r["attempts_used"], r["attempts"][-1]["failure_kind"] or "",
                        tw.get("n_cases", ""), tw.get("n_correct", ""),
                        "\n---\n".join(r["errors"]), r["final_code"] or ""])

    summary, cumulative = summarize(runs, tasks, config)
    (out_dir / "summary.md").write_text(summary)
    (out_dir / "figures" / "chart.svg").write_text(chart_svg(runs, tasks, cumulative, config))
    print("\n" + summary)
    print(f"Wrote results.json, results.csv, summary.md and figures/chart.svg to {out_dir}")


if __name__ == "__main__":
    main()
