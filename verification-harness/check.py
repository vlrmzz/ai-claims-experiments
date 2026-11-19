"""Run one task's test cases against one candidate solution file.

Usage: python check.py <solution.py> <tests.py> [visible|all]

tests.py holds CASES, the cases the harness may see, and optionally HIDDEN, held-out
cases used only for scoring. "visible" runs CASES; "all" (the default) runs both.

The runner calls this in a subprocess (with a timeout) so a crashing or looping
candidate cannot take the experiment down. It runs every selected case, prints one line
per failure, and exits 0 only if all of them pass. The "visible" output is exactly what
the harness condition feeds back to the model.
"""

import copy
import importlib.util
import sys
import traceback

MAX_FAILURES_SHOWN = 8


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expects_exception(expected):
    return isinstance(expected, type) and issubclass(expected, BaseException)


def main(solution_path, tests_path, which="all"):
    tests = load(tests_path, "tests")
    cases = tests.CASES + (getattr(tests, "HIDDEN", []) if which == "all" else [])
    try:
        solution = load(solution_path, "solution")
        fn = getattr(solution, tests.FUNCTION)
    except Exception:
        # Syntax errors, import errors, or a missing function: show the traceback tail.
        print("Could not load the solution:")
        print("".join(traceback.format_exc(limit=-2)).rstrip())
        return 1

    failures = []
    for args, expected in cases:
        call = f"{tests.FUNCTION}({', '.join(repr(a) for a in args)})"
        try:
            got = fn(*copy.deepcopy(args))
        except Exception as exc:
            if expects_exception(expected) and isinstance(exc, expected):
                continue
            want = f"raise {expected.__name__}" if expects_exception(expected) else repr(expected)
            failures.append(f"FAIL {call}: expected {want}, but raised {type(exc).__name__}: {exc}")
            continue
        if expects_exception(expected):
            failures.append(f"FAIL {call}: expected raise {expected.__name__}, got {got!r}")
        elif got != expected or type(got) is not type(expected):
            failures.append(f"FAIL {call}: expected {expected!r}, got {got!r}")

    for line in failures[:MAX_FAILURES_SHOWN]:
        print(line)
    if len(failures) > MAX_FAILURES_SHOWN:
        print(f"... and {len(failures) - MAX_FAILURES_SHOWN} more failures")
    print(f"{len(cases) - len(failures)}/{len(cases)} test cases passed")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
