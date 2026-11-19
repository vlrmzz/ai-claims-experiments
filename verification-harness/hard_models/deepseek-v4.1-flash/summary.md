# Results: hard tasks, openrouter deepseek/deepseek-v4.1-flash, 2026-10-21

Backend `openrouter`, model `deepseek/deepseek-v4.1-flash`, thinking off, temperature 0.2, 10 tasks × 10 repeats, loops stop after 3 code attempts.

## Success rate

| Condition | Passed | Rate | 95% CI (Wilson) |
|---|---|---|---|
| Baseline | 77/100 | 77% | 68%–84% |
| Harness (visible tests), first attempt only | 71/100 | 71% | 61%–79% |
| Harness (visible tests) (≤3 attempts) | 81/100 | 81% | 72%–87% |
| Self-test harness, first attempt only | 75/100 | 75% | 66%–82% |
| Self-test harness (≤3 attempts) | 87/100 | 87% | 79%–92% |

Every first attempt uses the same prompt as the baseline. Differences between those rows are sampling noise, not the harness.

## What the loop saw vs. what was true

Loops see the 36 visible test cases (and, for the self-test harness, the model's own cases); 224 more are held out and used only for scoring.

| Condition | Final code passes the loop's tests | Passes visible | Passes held-out too | Loop's tests pass, code still wrong |
|---|---|---|---|---|
| Baseline | – | 85/100 | 77/100 | – |
| Harness (visible tests) | 98/100 | 98/100 | 81/100 | 17 |
| Self-test harness | 62/100 | 97/100 | 87/100 | 8 |

## The model's own tests

- Usable test files: 72/100 (the rest fell back to the visible tests only)
- Test cases written: 2997 (41.6 per run)
- Cases the reference solution passes, i.e. correct tests: 2886/2997 (96%)
- Runs where every self-written case was correct: 34/72
- Why test files were unusable: no code block (17); AssertionError: SELF_CASES must be a list of (args_tuple, expected) pairs (10); SyntaxError: closing parenthesis ')' does not match opening parenthesis '[' on line 7 (1)

## By difficulty

| Difficulty | Baseline | Harness (visible tests) | Self-test harness |
|---|---|---|---|
| medium | 38/40 | 39/40 | 40/40 |
| hard | 39/60 | 42/60 | 47/60 |

## Per task

| Task | Difficulty | Baseline | Harness (visible tests) | Self-test harness | Harness (visible tests): mean attempts | Self-test harness: mean attempts |
|---|---|---|---|---|---|---|
| h01_semver | hard | 10/10 | 8/10 | 9/10 | 1.00 | 1.00 |
| h02_glob | hard | 1/10 | 1/10 | 3/10 | 1.70 | 2.60 |
| h03_cron | hard | 2/10 | 9/10 | 10/10 | 1.90 | 3.00 |
| h04_calc | hard | 10/10 | 10/10 | 9/10 | 1.00 | 2.00 |
| h05_iso_duration | hard | 6/10 | 4/10 | 7/10 | 1.10 | 1.10 |
| h06_strict_roman | medium | 8/10 | 9/10 | 10/10 | 1.20 | 1.00 |
| h07_bytes | medium | 10/10 | 10/10 | 10/10 | 1.00 | 2.60 |
| h08_csv | medium | 10/10 | 10/10 | 10/10 | 1.00 | 1.00 |
| h09_lcs | hard | 10/10 | 10/10 | 9/10 | 1.20 | 2.80 |
| h10_ttl_cache | medium | 10/10 | 10/10 | 10/10 | 1.00 | 1.90 |

## Loop attempts

| Condition | Mean attempts | Code correct at attempt 1 / 2 / 3 | Needed a repair | Repair ended correct | Repair ended with loop's tests passing but code wrong | Repair never passed the loop's tests | Loop broke code that was correct |
|---|---|---|---|---|---|---|---|
| Harness (visible tests) | 1.21 | 71% / 80% / 81% | 18 | 10 | 6 | 2 | 0 |
| Self-test harness | 1.90 | 75% / 77% / 87% | 47 | 39 | 3 | 38 | 1 |

A loop keeps going while its own tests fail, so with wrong self-written tests it can rewrite code that was already correct; the last column counts the times that made it wrong.

## Paired comparisons

Same task and same repeat. Discordant pairs are the ones where exactly one condition passed.

| Comparison | Both pass | Only first | Only second | Both fail | McNemar p |
|---|---|---|---|---|---|
| Harness (visible tests) vs. Baseline | 70 | 11 | 7 | 12 | 0.481 |
| Self-test harness vs. Baseline | 71 | 16 | 6 | 7 | 0.052 |
| Self-test harness vs. Harness (visible tests) | 77 | 10 | 4 | 9 | 0.180 |

The repeats of one task are not independent, so these p-values are optimistic. The per-task table is the more honest view.

## Failure patterns

Final code that failed, by kind:

| Kind | Baseline | Harness (visible tests) | Self-test harness |
|---|---|---|---|
| crash (IndexError) | 1 | 0 | 1 |
| crash (NameError) | 1 | 0 | 0 |
| crash (TypeError) | 0 | 2 | 0 |
| crash (ValueError) | 6 | 1 | 2 |
| load error | 2 | 0 | 1 |
| missing exception | 1 | 7 | 3 |
| no code block | 2 | 1 | 0 |
| wrong answer | 10 | 8 | 6 |

Most common first failing case of the final code, per task (count over all conditions):

- h01_semver: `sort_versions(['1.0.0-01'])` (3)
- h02_glob: `glob_match('*', '')` (15), `Could not load the solution:` (3), `glob_match('a/**', 'a')` (3)
- h03_cron: `next_cron('0 9 * * 1-5', '2024-01-05T09:00')` (8), `next_cron('0 0 */10 * 1', '2024-01-01T00:00')` (1)
- h04_calc: `evaluate('2^64 / 2^62')` (1)
- h05_iso_duration: `iso_duration_seconds('P1WT1H')` (7), `iso_duration_seconds('P1Y2M10DT2H30M')` (5), `iso_duration_seconds('PT36H')` (1)
- h06_strict_roman: `parse_roman('MCMXCIV')` (1), `parse_roman('III')` (1), `No code block found in the reply.` (1)
- h09_lcs: `smallest_lcs('abcbdab', 'bdcaba')` (1)

## Cost

| Condition | Model calls | Input tokens | Output tokens | Reasoning tokens | Cost (USD) | Time (s) |
|---|---|---|---|---|---|---|
| Baseline | 100 | 43,340 | 121,038 | 0 | 0.105 | 660 |
| Harness (visible tests) | 121 | 89,008 | 148,011 | 0 | 0.135 | 763 |
| Self-test harness | 290 | 261,872 | 494,147 | 40,000 | 0.450 | 3772 |
