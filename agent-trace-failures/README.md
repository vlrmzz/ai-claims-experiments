# Can a decision model find where an agent failed?

Code and result files behind the post of the same name: a benchmark of TypeSafe's
Jev on failed AI-agent runs.

1. Jev measured against human labels (AgentRx, Who&When; 257 runs), against
   published results, and against Claude reading the same runs.
2. A second use on 159 failed runs of GPT-5 on tau2-bench (airline and retail),
   labelled by a model and checked against the benchmark's published corrections.

## Files

| File | What it is |
|---|---|
| `fetch.py` | Downloads the traces and the three task versions into `data/` (27 MB, not committed) |
| `traces.py` | Loader: runs, failed runs, task comparison |
| `revisions.py`, `task_revisions.csv` | Which tasks Amazon and Sierra later revised, and which parts |
| `flatten.py` | One run as plain text: script, grader diff, conversation (what the reader and Jev get) |
| `labelling_brief.md` | The brief the reader followed, verbatim |
| `consolidate.py`, `reference_labels.csv` | The reader's labels, 159 rows, with the free-text class folded into 8 patterns |
| `patterns.json` | The 8 patterns, with the exact yes/no question Jev is asked for each |
| `jev_score.py`, `jev_scores.csv`, `evaluate.py`, `results.json` | Jev on the 159 runs, compared with the reference labels and the revisions |
| `fetch_annotated.py` | Downloads the human-labelled datasets into `data/annotated/` (11 MB, not committed) |
| `jev_ground_truth.py`, `ground_truth_scores.csv`, `ground_truth_results.json` | Jev, untuned, on the 257 human-labelled runs |
| `jev_tune.py`, `tuned_test_scores.csv`, `tuning_results.json` | Tuning on one half of those runs, test on the other |
| `judge_export.py`, `judge_score.py`, `judge_scores.csv`, `judge_results.json` | Claude as judge on the held-out half, scored against the same labels |
| `figures.py` | The four figures of the post, written to `figures/` |
| `agent_trace_failures.ipynb` | The saved results as tables and charts. It does not call Jev, so it needs no key. |

## Run it

Python 3.10 or later. `figures.py` needs matplotlib; `fetch_annotated.py` needs pyarrow.
Jev needs a TypeSafe API key in `TYPESAFE_API_KEY` or in `~/.config/typesafe/key`.

    python fetch.py && python revisions.py && python flatten.py
    python consolidate.py          # from data/labels/batch_*.json, the reader's output
    python jev_score.py && python evaluate.py
    python fetch_annotated.py && python jev_ground_truth.py && python jev_tune.py
    python judge_export.py         # writes label-free run files for a text-model judge
    python judge_score.py          # from data/judge/answers/batch_*.json
    python figures.py

A trace id reads `domain-task-trial`, for example `retail-018-t1`. To find a run
in Sierra's file, match the task id and trial against `simulations[]`.

## Where the data comes from

- Traces: Sierra's leaderboard run of GPT-5 from August 2025, in the public bucket
  behind [taubench.com](https://taubench.com). 4 trials on each of 164 tasks, with
  the grader's verdict for every run, on the original task definitions
  (tau2-bench commit `964ef7a`). Not copied here: the tau2-bench code and tasks
  are MIT licensed, but I found no licence statement for the trajectory files.
- Corrections: [amazon-agi/tau2-bench-verified](https://github.com/amazon-agi/tau2-bench-verified)
  (commit `864350a`) and tau2-bench main (commit `5bfa7e3`).
- Human labels: [microsoft/AgentRx](https://github.com/microsoft/AgentRx) (MIT) and
  [Kevin355/Who_and_When](https://huggingface.co/datasets/Kevin355/Who_and_When).

## How the labels were made

The 159 runs were read by Claude (Fable 5.1) in 8 batches, one pass, following
`labelling_brief.md`. The reader did not see the published corrections. Fields:

- `labeller_class`: the reader's own name for the kind of failure; `pattern` is
  the one of 8 it was folded into (`consolidate.py` holds the mapping).
- `fault`: agent, task definition, grader, user simulator, agent and benchmark,
  or unclear.
- `cheapest_fix`: prompt or tool description, harness, model, benchmark fix, or
  none found.
- `what_went_wrong`, `fault_evidence`, `fix_note`, `summary`: the reader's notes.

Nobody checked these labels by hand. The check that exists is the comparison
with the published corrections in `results.json`.

The reader's raw batch files and Claude's judge answers live under `data/`,
which is not committed; the CSVs above hold everything the post quotes.
