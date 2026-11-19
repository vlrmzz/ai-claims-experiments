# Results: hard tasks, openrouter z-ai/glm-5.3-flash, 2026-10-21 (recovered from the log)

Backend `openrouter`, model `z-ai/glm-5.3-flash`, reasoning allowed (the provider does not let it be
switched off; a probe call used 8 reasoning tokens), temperature 0.2, loops stop after 3 code attempts.

This run crashed at run 231 of 300 on a dropped connection, before it wrote `results.json`; the
runner has since been fixed to retry such errors and to save every finished run as it goes. The
numbers below come from `run.log`, which records the task, condition, repeat, pass/fail and number
of attempts of every finished run. Only the 7 repeats in which all 30 runs finished are used. The
details that need the full results (visible vs. held-out, the quality of the self-written tests,
cost per condition) are not available. The run cost $0.47.

## Success rate (7 complete repeats)

| Condition | Passed | Rate | 95% CI (Wilson) | Mean attempts |
|---|---|---|---|---|
| Baseline | 26/70 | 37% | 27%–49% | 1.00 |
| Harness (visible tests) | 40/70 | 57% | 45%–68% | 1.77 |
| Self-test harness | 45/70 | 64% | 53%–74% | 2.03 |

## Paired comparisons

| Comparison | Only first | Only second | McNemar p |
|---|---|---|---|
| Harness vs. Baseline | 19 | 5 | 0.007 |
| Self-test harness vs. Baseline | 23 | 4 | <0.001 |
| Self-test harness vs. Harness | 14 | 9 | 0.405 |

## Per task (baseline / harness / self-test harness)

| Task | Baseline | Harness | Self-test |
|---|---|---|---|
| h01_semver | 4/7 | 4/7 | 4/7 |
| h02_glob | 0/7 | 0/7 | 0/7 |
| h03_cron | 3/7 | 3/7 | 6/7 |
| h04_calc | 7/7 | 7/7 | 7/7 |
| h05_iso_duration | 0/7 | 5/7 | 4/7 |
| h06_strict_roman | 2/7 | 2/7 | 6/7 |
| h07_bytes | 3/7 | 7/7 | 4/7 |
| h08_csv | 7/7 | 7/7 | 7/7 |
| h09_lcs | 0/7 | 5/7 | 6/7 |
| h10_ttl_cache | 0/7 | 0/7 | 1/7 |
