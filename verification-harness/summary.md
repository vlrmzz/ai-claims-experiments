# Results: cli claude-haiku-4-5, 2026-10-21

Backend `cli`, model `claude-haiku-4-5`, thinking on, temperature not set, 10 tasks × 3 repeats, loops stop after 3 code attempts.

## Success rate

| Condition | Passed | Rate | 95% CI (Wilson) |
|---|---|---|---|
| Baseline | 29/30 | 97% | 83%–99% |
| Harness (visible tests), first attempt only | 29/30 | 97% | 83%–99% |
| Harness (visible tests) (≤3 attempts) | 30/30 | 100% | 89%–100% |

Every first attempt uses the same prompt as the baseline. Differences between those rows are sampling noise, not the harness.

## By difficulty

| Difficulty | Baseline | Harness (visible tests) |
|---|---|---|
| easy | 12/12 | 12/12 |
| medium | 17/18 | 18/18 |

## Per task

| Task | Difficulty | Baseline | Harness (visible tests) | Harness (visible tests): mean attempts |
|---|---|---|---|---|
| t01_palindrome | easy | 3/3 | 3/3 | 1.00 |
| t02_roman | easy | 3/3 | 3/3 | 1.00 |
| t03_rle | easy | 3/3 | 3/3 | 1.00 |
| t04_intervals | medium | 3/3 | 3/3 | 1.00 |
| t05_duration | medium | 3/3 | 3/3 | 1.00 |
| t06_english | medium | 3/3 | 3/3 | 1.00 |
| t07_rpn | medium | 2/3 | 3/3 | 1.33 |
| t08_versions | easy | 3/3 | 3/3 | 1.00 |
| t09_snake | medium | 3/3 | 3/3 | 1.00 |
| t10_wrap | medium | 3/3 | 3/3 | 1.00 |

## Loop attempts

| Condition | Mean attempts | Code correct at attempt 1 / 2 / 3 | Needed a repair | Repair ended correct | Repair ended with loop's tests passing but code wrong | Repair never passed the loop's tests | Loop broke code that was correct |
|---|---|---|---|---|---|---|---|
| Harness (visible tests) | 1.03 | 97% / 100% / 100% | 1 | 1 | 0 | 0 | 0 |

A loop keeps going while its own tests fail, so with wrong self-written tests it can rewrite code that was already correct; the last column counts the times that made it wrong.

## Paired comparisons

Same task and same repeat. Discordant pairs are the ones where exactly one condition passed.

| Comparison | Both pass | Only first | Only second | Both fail | McNemar p |
|---|---|---|---|---|---|
| Harness (visible tests) vs. Baseline | 29 | 1 | 0 | 0 | 1.000 |

The repeats of one task are not independent, so these p-values are optimistic. The per-task table is the more honest view.

## Failure patterns

Final code that failed, by kind:

| Kind | Baseline | Harness (visible tests) |
|---|---|---|
| wrong answer | 1 | 0 |

Most common first failing case of the final code, per task (count over all conditions):

- t07_rpn: `eval_rpn(['123456789012345678901', '1', '/'])` (1)

## Cost

| Condition | Model calls | Input tokens | Output tokens | Reasoning tokens | Cost (USD) | Time (s) |
|---|---|---|---|---|---|---|
| Baseline | 30 | 19,692 | 122,673 | 0 | 0.000 | 748 |
| Harness (visible tests) | 31 | 20,804 | 146,026 | 0 | 0.000 | 887 |
