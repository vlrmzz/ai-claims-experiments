# Results: hard tasks, cli claude-haiku-4-5, 2026-10-21

Backend `cli`, model `claude-haiku-4-5`, thinking off, temperature not set, 10 tasks × 10 repeats, loops stop after 3 code attempts.

## Success rate

| Condition | Passed | Rate | 95% CI (Wilson) |
|---|---|---|---|
| Baseline | 43/100 | 43% | 34%–53% |
| Harness (visible tests), first attempt only | 45/100 | 45% | 36%–55% |
| Harness (visible tests) (≤3 attempts) | 48/100 | 48% | 38%–58% |

Every first attempt uses the same prompt as the baseline. Differences between those rows are sampling noise, not the harness.

## What the loop saw vs. what was true

Loops see the 36 visible test cases (and, for the self-test harness, the model's own cases); 224 more are held out and used only for scoring.

| Condition | Final code passes the loop's tests | Passes visible | Passes held-out too | Loop's tests pass, code still wrong |
|---|---|---|---|---|
| Baseline | – | 75/100 | 43/100 | – |
| Harness (visible tests) | 90/100 | 90/100 | 48/100 | 42 |

## By difficulty

| Difficulty | Baseline | Harness (visible tests) |
|---|---|---|
| medium | 27/40 | 28/40 |
| hard | 16/60 | 20/60 |

## Per task

| Task | Difficulty | Baseline | Harness (visible tests) | Harness (visible tests): mean attempts |
|---|---|---|---|---|
| h01_semver | hard | 2/10 | 7/10 | 1.20 |
| h02_glob | hard | 1/10 | 2/10 | 1.30 |
| h03_cron | hard | 7/10 | 5/10 | 1.30 |
| h04_calc | hard | 2/10 | 1/10 | 1.00 |
| h05_iso_duration | hard | 0/10 | 0/10 | 1.20 |
| h06_strict_roman | medium | 8/10 | 8/10 | 1.20 |
| h07_bytes | medium | 9/10 | 10/10 | 1.10 |
| h08_csv | medium | 0/10 | 0/10 | 2.80 |
| h09_lcs | hard | 4/10 | 5/10 | 1.30 |
| h10_ttl_cache | medium | 10/10 | 10/10 | 1.00 |

## Loop attempts

| Condition | Mean attempts | Code correct at attempt 1 / 2 / 3 | Needed a repair | Repair ended correct | Repair ended with loop's tests passing but code wrong | Repair never passed the loop's tests | Loop broke code that was correct |
|---|---|---|---|---|---|---|---|
| Harness (visible tests) | 1.34 | 45% / 48% / 48% | 22 | 3 | 9 | 10 | 0 |

A loop keeps going while its own tests fail, so with wrong self-written tests it can rewrite code that was already correct; the last column counts the times that made it wrong.

## Paired comparisons

Same task and same repeat. Discordant pairs are the ones where exactly one condition passed.

| Comparison | Both pass | Only first | Only second | Both fail | McNemar p |
|---|---|---|---|---|---|
| Harness (visible tests) vs. Baseline | 33 | 15 | 10 | 42 | 0.424 |

The repeats of one task are not independent, so these p-values are optimistic. The per-task table is the more honest view.

## Failure patterns

Final code that failed, by kind:

| Kind | Baseline | Harness (visible tests) |
|---|---|---|
| crash (IndexError) | 2 | 0 |
| crash (TypeError) | 1 | 0 |
| crash (ValueError) | 6 | 6 |
| missing exception | 14 | 9 |
| timeout | 3 | 6 |
| wrong answer | 31 | 31 |

Most common first failing case of the final code, per task (count over all conditions):

- h01_semver: `sort_versions(['1.0.0-01'])` (9), `sort_versions(['1.0.0', '1.0.0-rc.1', '1.0.0-alpha', '1.0.0-beta.11', ` (1), `sort_versions(['1.0'])` (1)
- h02_glob: `glob_match('[]a]', ']')` (3), `glob_match('a**b', 'axxb')` (3), `glob_match('[ab', '[ab')` (3)
- h03_cron: `next_cron('0 0 */10 * 1', '2024-01-01T00:00')` (4), `next_cron('0 9 * * 1-5', '2024-01-05T09:00')` (3), `Tests timed out after 10 s (infinite loo` (1)
- h04_calc: `evaluate('-2^2')` (15), `evaluate('1 + 2 * 3')` (1), `evaluate('2^-1')` (1)
- h05_iso_duration: `iso_duration_seconds('P1.5Y2M')` (5), `iso_duration_seconds('P1WT1H')` (4), `iso_duration_seconds('P3W')` (3)
- h06_strict_roman: `parse_roman('MCMXCIV')` (2), `parse_roman('VV')` (1), `parse_roman('')` (1)
- h07_bytes: `humanize_bytes(1536)` (1)
- h08_csv: `parse_csv_line('a,,')` (12), `parse_csv_line('')` (4), `parse_csv_line('"say ""hi"""')` (2)
- h09_lcs: `Tests timed out after 10 s (infinite loo` (7), `smallest_lcs('abcbdab', 'bdcaba')` (3), `smallest_lcs('baab', 'abba')` (1)

## Cost

| Condition | Model calls | Input tokens | Output tokens | Reasoning tokens | Cost (USD) | Time (s) |
|---|---|---|---|---|---|---|
| Baseline | 100 | 83,300 | 133,586 | 0 | 0.000 | 1089 |
| Harness (visible tests) | 134 | 146,600 | 180,994 | 0 | 0.000 | 1490 |
