# Labelling brief: failed customer-service agent runs

You are labelling failed runs of a tool-calling customer-service agent on a public benchmark (tau2-bench). Each run is one conversation between a simulated customer and the agent. A grader marked every run in your batch as FAILED. Your job is to read each run in full and record what actually went wrong and whose fault it was. In a real share of runs the agent may have done nothing wrong and the benchmark is at fault; in others the agent made a real mistake. Do not assume either. Decide from the evidence.

## What to read
- `flat/<trace_id>.txt` for each trace id in your batch. Each file has: the script given to the simulated customer (the agent never sees it), what the grader expected, a factual diff of why the run was marked failed, and the full conversation with tool calls and tool results.
- `flat/policy_<domain>.md`: the policy the agent was given. Read it first, carefully. It is the only rulebook. Judge the agent against this policy, not against what seems reasonable.

Read only those files. Do NOT open any other file in `data/` or its parent folder (in particular nothing named tasks_*, FIXES*, task_revisions*, sample*, coded_sheet*), and do not search the web. Your labels must be independent of any published corrections to the benchmark.

## How the grader works
A run passes if (1) the final database equals the database you get by applying the task author's expected actions, and (2) the agent stated any required information. Read-only calls do not matter. So a run fails when the agent made a write the author did not expect, did not make a write the author expected, made it with different arguments, or left out required information.

## What to record for each run
- `trace_id`
- `summary`: 2-3 plain sentences: what the customer wanted, what the agent did, what the grader expected instead.
- `first_error_turn`: the turn number (in square brackets in the conversation) where the outcome was decided, or null if nothing in the conversation is an error.
- `what_went_wrong`: 1-2 sentences naming the specific cause of the failed verdict. Be concrete: name the tool call, the rule, the argument.
- `proposed_class`: a short label of your own (at most 8 words) for the KIND of failure, general enough to recur across runs, specific enough to act on. Reuse a label when the same thing happens again. Do not use a pre-existing taxonomy.
- `fault`: exactly one of
  - `agent`: the agent broke the policy, used a tool wrongly, decided wrongly, or did not do something the customer clearly asked for and the policy allows.
  - `task definition`: the expected actions contradict the policy or the data shown in tool results, or the customer script is contradictory, impossible or so ambiguous that an agent following the policy would still fail.
  - `grader`: the agent reached an outcome that satisfies the customer's script and the policy, and the comparison rejects it only because it differs from the one expected sequence (an equally valid alternative).
  - `user simulator`: the simulated customer departed from its script (left out something it was told to ask for, asked for something else, gave wrong details, ended early) and that is what caused the failure.
  - `agent and benchmark`: both a real agent error and a benchmark defect contributed.
  - `unclear`: you cannot decide from the files.
- `fault_evidence`: one sentence with the decisive evidence: quote the policy rule, the script line or the tool result.
- `cheapest_fix`: exactly one of `prompt or tool description`, `harness`, `model`, `benchmark fix`, `none found`. This is the cheapest change that would plausibly have prevented this failure. `harness` means a change to the code around the model (for example a confirmation check before writes, a validation step, retries, a calculator for totals). Choose `model` only if nothing cheaper would plausibly help.
- `fix_note`: one line saying what the fix would be.
- `confidence`: `high`, `medium` or `low`.

## Care
- Check the agent's claims against the tool results in the conversation (prices, statuses, dates, membership level, payment methods). The policy states the current date for the airline domain.
- When the agent refuses something or does something different from the expected actions, check the policy before deciding who is right.
- Runs of the same task (same task number, different trial) share a script and expected actions but the conversations differ. Judge each run on its own conversation.
- Do not skim. The decisive detail is often one argument in one tool call.

## Output
Write a single JSON file at the path given to you: a JSON array with one object per trace, in the order of your batch, using exactly the field names above. Write valid JSON only (no comments). When done, reply with a short report: number of runs labelled, the classes you used with counts, and any run you were unsure about.
