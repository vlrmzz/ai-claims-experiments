# Does a verification harness make a coding model succeed more often?

The claim: a model that runs the tests and fixes its own failures solves far more coding tasks
than the same model answering once from a plain prompt. This experiment runs both on the same
small Python tasks.

| Condition | What happens |
|---|---|
| **baseline** | One generation from the problem statement. |
| **harness** | Generate, run the visible tests, and if they fail, send the code and the test output back with a request for a short critique and a fix. At most 3 generations. Every attempt is logged. |
| **selftest** | As harness, but first the model writes its own test cases from the specification, without seeing any code (as Reflexion and AlphaCodium do). The loop runs the visible tests plus those. |

All conditions are scored the same way: the final code must pass the visible tests **and** a
larger set of held-out tests that no loop ever sees. That is the situation of a real agent:
its own tests pass, and the question is whether the code is right.

## Results so far

On the 10 hard tasks, share of runs whose final code passed every test, held-out ones included:

| Model | Repeats | Baseline | Harness (visible tests) | Self-test harness | Folder |
|---|---|---|---|---|---|
| `claude-haiku-4-5` (CLI, thinking off) | 10 | 43% | 48% (p = 0.42) | – | `hard/` |
| `deepseek/deepseek-v4.1-flash` (reasoning off) | 10 | 77% | 81% (p = 0.48) | 87% (p = 0.05) | `hard_models/deepseek-v4.1-flash/` |
| `z-ai/glm-5.3-flash` (reasoning cannot be switched off) | 10 | 56% | 78% (p < 0.001) | 77% (p = 0.001) | `hard_models/glm-5.3-flash/` |
| same, an earlier run that crashed (recovered from its log) | 7 | 37% | 57% (p = 0.007) | 64% (p < 0.001) | same folder, `summary_crashed_run.md` |

p is an exact McNemar test against the baseline on the same task and repeat. The repeats of one
task are not independent, so the p-values are optimistic; the per-task tables in each
`summary.md` are the more honest view.

The two GLM runs disagree on the level (a baseline of 56% against 37%) but agree on the effect:
about +20 points for both loops. GLM's reasoning cannot be switched off and is uneven: most
calls reason for a dozen tokens, some for thousands. Why the level moved is not known; the
provider OpenRouter routed to was not recorded.

What the runs show:

- A loop over a few fixed tests helped one model a lot (GLM, +20 points, in two separate runs)
  and two models little (+4 and +5, within noise). It fixes the bugs its tests reveal. With Haiku
  it got the visible tests passing in 90 of 100 runs, but only 48 of those programs were correct.
- Writing its own tests first beat the baseline for both models that tried it, and beat the
  fixed-test loop for DeepSeek (87% against 81%) but not for GLM (77% against 78%). The
  self-written cases were 96% correct for both models. The costs: about 4 times the baseline's
  spend, loops that chase a wrong self-written test until they run out of attempts, and correct
  code made wrong (once for DeepSeek, 4 times for GLM). Both models also often wrote far more
  cases than asked and ran out of output tokens, so 17% (DeepSeek) and 35% (GLM) of self-test runs
  fell back to the visible tests only.
- The gain depends on the model and the task: the same task can be fixed by the loop for one
  model and not for another.

Limits: 10 tasks, written for this experiment, all about following an exact specification;
small, cheap models only; for the CLI runs, no temperature control. There is no notebook yet.

## Files

| File | What it is |
|---|---|
| `run.py` | The experiment: both conditions on every task, the stats, `summary.md` and the chart |
| `check.py` | Runs one task's test cases on one candidate file, in a subprocess with a 10 s timeout |
| `tasks_hard/<id>/` | The main task set: 10 tasks with long, exact specifications |
| `tasks/<id>/` | The first, easier task set, kept because the first run used it |
| `…/prompt.md` | The problem statement, the only thing the model sees |
| `…/tests.py` | `FUNCTION`, `DIFFICULTY`, `CASES` (visible to the harness) and `HIDDEN` (held out), each a list of `(args, expected)`; an exception class as `expected` means "must raise" |
| `…/reference.py` | A reference solution, used only to check the tests |
| `hard/results.json` | The Haiku run: config, then every run and every attempt (reply, code, visible and full test output, failure kind, tokens, time) |
| `hard/results.csv`, `hard/summary.md` | One row per run; and the summary: success rates with 95% intervals, visible vs. held-out, the model's own tests, per task, loop attempts, paired McNemar tests, failure patterns, cost |
| `hard_models/<model>/` | The same files for each OpenRouter model; `glm-5.3-flash/` also holds the log of an earlier run that crashed and the numbers recovered from it |
| `results.json`, `results.csv`, `summary.md` | The first run, on the easy set |
| `figures/`, `hard/figures/` | `chart.svg`: success per task for both conditions, and the harness pass rate after 1, 2 and 3 attempts (not committed) |

## Run it

Python 3.10 or later and the `anthropic` package. The key goes in `ANTHROPIC_API_KEY`.

    pip install anthropic
    python run.py --task-set hard --verify-references   # every reference solution must pass its tests
    python run.py --task-set hard --backend fake        # offline smoke test, no model, writes to _out/
    python run.py --task-set hard --repeats 10          # the main run, writes to hard/

Defaults: model `claude-haiku-4-5`, temperature 0.2, 3 repeats per task per condition, at most 3
harness attempts, 4 runs in parallel. `run.py` refuses to replace an existing `results.json`.
Pass `--out` to write somewhere else, or `--overwrite`.

Other options:

    python run.py --task-set hard --backend openrouter --model deepseek/deepseek-v4.1-flash \
        --repeats 10 --max-cost 0.90 --out hard_models/deepseek-v4.1-flash   # needs OPENROUTER_API_KEY
    python run.py ... --resume                                 # continue a run that stopped; finished runs are kept
    python run.py --summarize hard_models/deepseek-v4.1-flash  # rebuild summary.md and the chart, no model calls
    python run.py --conditions baseline harness                # run only some conditions
    python run.py --backend cli                                # the `claude` CLI login instead of an API key
    python run.py --backend cli --thinking                     # let the model think before answering
    python run.py --model claude-opus-5-5 --temperature none   # newer models reject the temperature parameter
    python run.py --task-set hard --tasks h04_calc --repeats 10 --out _out/calc

With no `ANTHROPIC_API_KEY`, `run.py` uses the `claude` CLI. That backend turns off every tool, so
the model cannot run code itself, and it cannot set a temperature (the results record `null`).
It also turns off Claude Code's thinking by default, so that the baseline is a plain one-shot
answer, as with the API. With thinking on, a call used about 15,000 output tokens, mostly hidden
reasoning, for about 800 tokens of code, and the baseline passed 9 of 10 hard tasks in a pilot.

## The tasks

`tasks_hard/`, the main set:

| Task | Difficulty | Visible / held-out cases | What tends to go wrong |
|---|---|---|---|
| `h01_semver` | hard | 3 / 19 | SemVer 2.0 validation (leading zeros in pre-release ids), precedence of mixed identifiers |
| `h02_glob` | hard | 5 / 39 | `**` as a whole segment only, `[]a]`, `[!…]` never matching `/`, escapes |
| `h03_cron` | hard | 3 / 22 | Day-of-month OR day-of-week, Sunday as 0 or 7, leap days, malformed fields |
| `h04_calc` | hard | 5 / 32 | `-2^2` is −4, `2^-1`, right-associative `^`, exact fractions, syntax errors |
| `h05_iso_duration` | hard | 4 / 32 | Strict ISO 8601: component order, `W` only alone, a fraction only on the last component |
| `h06_strict_roman` | medium | 3 / 26 | Rejecting every non-canonical numeral, including the empty string |
| `h07_bytes` | medium | 4 / 16 | Round-half-up (Python rounds half to even), rolling over to the next unit |
| `h08_csv` | medium | 4 / 19 | Empty line and trailing commas, strict quote errors |
| `h09_lcs` | hard | 3 / 9 | Lexicographically smallest longest common subsequence, 300-character inputs in time |
| `h10_ttl_cache` | medium | 2 / 10 | Expiry at exactly `time + ttl`, expired entries not counting toward capacity |

The visible cases are the examples in the prompt plus one or two more, about what a developer
would write first. The held-out cases cover the rest of the specification. Every expected value
comes from the reference solution, and the cron cases were also checked by a separate
minute-by-minute brute force, the LCS reference against brute force on 400 random pairs.

`tasks/`, the first set (no held-out cases): `t01_palindrome`, `t02_roman`, `t03_rle`,
`t04_intervals`, `t05_duration`, `t06_english`, `t07_rpn`, `t08_versions`, `t09_snake`, `t10_wrap`.

To add a task, make a folder with the three files and run `python run.py --verify-references`.

## Read the numbers with this in mind

- **The harness's first attempt repeats the baseline.** Both use the same prompt, and they are
  sampled independently. If their pass rates differ, the difference is noise, not the harness.
- **The harness sees the failing visible cases, expected values included**, never the held-out ones.
  It stops as soon as the visible cases pass, even if the code is still wrong.
- **The tests are the only judge.** A solution that passes every case counts as correct.
- **Generated code runs on your machine** in a subprocess with a 10 s timeout and no other sandbox.
- **An API or CLI error stops the run.** It is not counted as a model failure.
- **The first run (easy set) used the CLI with thinking on**, before thinking was turned off by default.
