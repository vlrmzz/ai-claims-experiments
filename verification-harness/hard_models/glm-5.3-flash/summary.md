# Results: hard tasks, openrouter z-ai/glm-5.3-flash, 2026-10-22

Backend `openrouter`, model `z-ai/glm-5.3-flash`, thinking on, temperature 0.2, 10 tasks × 10 repeats, loops stop after 3 code attempts.

## Success rate

| Condition | Passed | Rate | 95% CI (Wilson) |
|---|---|---|---|
| Baseline | 56/100 | 56% | 46%–65% |
| Harness (visible tests), first attempt only | 63/100 | 63% | 53%–72% |
| Harness (visible tests) (≤3 attempts) | 78/100 | 78% | 69%–85% |
| Self-test harness, first attempt only | 56/100 | 56% | 46%–65% |
| Self-test harness (≤3 attempts) | 77/100 | 77% | 68%–84% |

Every first attempt uses the same prompt as the baseline. Differences between those rows are sampling noise, not the harness.

## What the loop saw vs. what was true

Loops see the 36 visible test cases (and, for the self-test harness, the model's own cases); 224 more are held out and used only for scoring.

| Condition | Final code passes the loop's tests | Passes visible | Passes held-out too | Loop's tests pass, code still wrong |
|---|---|---|---|---|
| Baseline | – | 77/100 | 56/100 | – |
| Harness (visible tests) | 97/100 | 97/100 | 78/100 | 19 |
| Self-test harness | 69/100 | 93/100 | 77/100 | 13 |

## The model's own tests

- Usable test files: 65/100 (the rest fell back to the visible tests only)
- Test cases written: 1746 (26.9 per run)
- Cases the reference solution passes, i.e. correct tests: 1668/1746 (96%)
- Runs where every self-written case was correct: 35/65
- Why test files were unusable: no code block (34); AssertionError: SELF_CASES must be a list of (args_tuple, expected) pairs (1)

## By difficulty

| Difficulty | Baseline | Harness (visible tests) | Self-test harness |
|---|---|---|---|
| medium | 33/40 | 33/40 | 36/40 |
| hard | 23/60 | 45/60 | 41/60 |

## Per task

| Task | Difficulty | Baseline | Harness (visible tests) | Self-test harness | Harness (visible tests): mean attempts | Self-test harness: mean attempts |
|---|---|---|---|---|---|---|
| h01_semver | hard | 6/10 | 10/10 | 7/10 | 1.00 | 1.70 |
| h02_glob | hard | 1/10 | 4/10 | 5/10 | 1.90 | 2.60 |
| h03_cron | hard | 5/10 | 5/10 | 6/10 | 1.40 | 1.20 |
| h04_calc | hard | 8/10 | 10/10 | 10/10 | 1.20 | 1.70 |
| h05_iso_duration | hard | 2/10 | 6/10 | 3/10 | 1.50 | 1.90 |
| h06_strict_roman | medium | 3/10 | 3/10 | 10/10 | 1.10 | 2.10 |
| h07_bytes | medium | 10/10 | 10/10 | 8/10 | 1.00 | 2.80 |
| h08_csv | medium | 10/10 | 10/10 | 10/10 | 1.00 | 1.20 |
| h09_lcs | hard | 1/10 | 10/10 | 10/10 | 1.80 | 2.00 |
| h10_ttl_cache | medium | 10/10 | 10/10 | 8/10 | 1.00 | 2.40 |

## Loop attempts

| Condition | Mean attempts | Code correct at attempt 1 / 2 / 3 | Needed a repair | Repair ended correct | Repair ended with loop's tests passing but code wrong | Repair never passed the loop's tests | Loop broke code that was correct |
|---|---|---|---|---|---|---|---|
| Harness (visible tests) | 1.29 | 63% / 75% / 78% | 23 | 15 | 5 | 3 | 0 |
| Self-test harness | 1.96 | 56% / 73% / 77% | 59 | 43 | 6 | 31 | 4 |

A loop keeps going while its own tests fail, so with wrong self-written tests it can rewrite code that was already correct; the last column counts the times that made it wrong.

## Paired comparisons

Same task and same repeat. Discordant pairs are the ones where exactly one condition passed.

| Comparison | Both pass | Only first | Only second | Both fail | McNemar p |
|---|---|---|---|---|---|
| Harness (visible tests) vs. Baseline | 52 | 26 | 4 | 18 | 0.000 |
| Self-test harness vs. Baseline | 46 | 31 | 10 | 13 | 0.001 |
| Self-test harness vs. Harness (visible tests) | 64 | 13 | 14 | 9 | 1.000 |

The repeats of one task are not independent, so these p-values are optimistic. The per-task table is the more honest view.

## Failure patterns

Final code that failed, by kind:

| Kind | Baseline | Harness (visible tests) | Self-test harness |
|---|---|---|---|
| crash (IndexError) | 3 | 0 | 0 |
| crash (UnboundLocalError) | 2 | 0 | 0 |
| crash (ValueError) | 7 | 2 | 2 |
| missing exception | 13 | 11 | 9 |
| no code block | 14 | 3 | 4 |
| wrong answer | 5 | 6 | 8 |

Most common first failing case of the final code, per task (count over all conditions):

- h01_semver: `sort_versions(['1.0.0-01'])` (5), `sort_versions(['1.0.0', '1.0.0-rc.1', '1.0.0-alpha', '1.0.0-beta.11', ` (2)
- h02_glob: `No code block found in the reply.` (11), `glob_match('a/**', 'a')` (3), `glob_match('a/**', 'ab')` (1)
- h03_cron: `next_cron('0 0 */10 * 1', '2024-01-01T00:00')` (7), `next_cron('30 6 * * 7', '2024-01-01T00:00')` (3), `next_cron('0 12 29 2 *', '2025-03-01T00:00')` (3)
- h04_calc: `evaluate('1 + 2 * 3')` (2)
- h05_iso_duration: `iso_duration_seconds('P1WT1H')` (8), `iso_duration_seconds('P1YT')` (4), `iso_duration_seconds('PT36H')` (2)
- h06_strict_roman: `parse_roman('')` (13), `parse_roman('MCMXCIV')` (1)
- h07_bytes: `humanize_bytes(1208925819614629174706177)` (1), `humanize_bytes(1180591620717411303424)` (1)
- h09_lcs: `No code block found in the reply.` (9)
- h10_ttl_cache: `No code block found in the reply.` (1), `simulate_cache(2, [('put', 'a', 1, 0, None), ('put', 'b', 2, 1, None),` (1)

## Cost

| Condition | Model calls | Input tokens | Output tokens | Reasoning tokens | Cost (USD) | Time (s) |
|---|---|---|---|---|---|---|
| Baseline | 100 | 43,090 | 180,423 | 116,515 | 0.036 | 2430 |
| Harness (visible tests) | 129 | 66,841 | 276,425 | 194,522 | 0.054 | 3909 |
| Self-test harness | 296 | 191,969 | 757,534 | 541,385 | 0.163 | 9066 |
