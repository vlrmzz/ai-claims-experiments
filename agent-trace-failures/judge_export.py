"""Write the held-out annotated runs as label-free text files for a text-model judge.

    python judge_export.py      # data/judge/runs/<dataset>__<id>.txt, batches.json, BRIEF.md

The judge sees exactly what Jev was asked about (the task, the policy if any, the numbered
steps, the agent names, the category definitions) but the whole run, with nothing cut. The
human annotations are not written anywhere under data/judge/.
"""

import json
import textwrap

from jev_ground_truth import load_all
from jev_tune import PAPER_CATEGORIES, STEP_WORDINGS, half
from traces import DATA

OUT = DATA / "judge"
BATCH_CHARS = 400_000


def render(item):
    lines = [f"RUN {item['dataset']}__{item['id']}", ""]
    if item["task"]:
        lines += ["== TASK ==", item["task"], ""]
    if item["policy"]:
        lines += ["== POLICY GIVEN TO THE AGENT ==", item["policy"], ""]
    if item["agents"]:
        lines += ["== AGENTS ==", ", ".join(item["agents"]), ""]
    lines.append("== STEPS ==")
    for k, (who, content) in enumerate(item["steps"]):
        lines.append(f"--- step_{item['first_step'] + k} | {who} ---")
        for paragraph in content.split("\n"):      # wrap so no line is too long to read in one piece
            lines += textwrap.wrap(paragraph, 1000, break_long_words=True, replace_whitespace=False) or [""]
    return "\n".join(lines) + "\n"


BRIEF = """# Judge brief: where did this failed agent run go wrong?

Each file in `runs/` is one FAILED run of an AI agent system: the task (if given), the policy
(if any), the list of agents (if several), and every step in order, marked `--- step_N | who ---`.
For each run in your batch, read the whole run and answer:

1. `step` (integer N): {step_question}
2. `agent`: only if the file has an AGENTS section. Which agent made the decisive mistake that
   caused the failure? Use a name exactly as listed there. Otherwise null.
3. `category`: only for runs whose name starts with `agentrx_`. Which category best describes
   the root cause of the failure? Use a name exactly as written below. Otherwise null.
4. `confidence`: your probability, from 0 to 1, that your `step` answer is exactly right.

Categories:
{categories}

Rules:
- Read only `BRIEF.md`, `batches.txt` and the run files of your batch. Do not open any other
  file or folder, and do not use the web. These runs come from public datasets with published
  answers; your answers must come only from reading the run.
- Read each run in full, including long tool outputs. Long runs span several reads.
- Answer every run, even when unsure.

Output: write one JSON array to the path you were given, one object per run in batch order:
{{"run": "<file name without .txt>", "step": <int>, "agent": <string or null>,
  "category": <string or null>, "confidence": <number>, "reason": "<one sentence>"}}
Then check that it parses and has one object per run. Reply with the number of runs answered
and nothing else of substance.
"""


def main():
    runs = OUT / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    test = [i for i in load_all() if half(i) == "test"]
    sizes = {}
    for item in test:
        name = f"{item['dataset']}__{item['id']}"
        text = render(item)
        (runs / f"{name}.txt").write_text(text)
        sizes[name] = len(text)

    batches, current, used = [], [], 0
    for name in sorted(sizes, key=lambda n: (n.split("__")[0], sizes[n])):
        if current and used + sizes[name] > BATCH_CHARS:
            batches.append(current)
            current, used = [], 0
        current.append(name)
        used += sizes[name]
    batches.append(current)
    (OUT / "batches.json").write_text(json.dumps(batches, indent=1))
    (OUT / "batches.txt").write_text("\n".join(f"{n} {' '.join(b)}" for n, b in enumerate(batches, 1)) + "\n")
    categories = "\n".join(f"- {name}: {definition}" for name, definition in PAPER_CATEGORIES.items())
    (OUT / "BRIEF.md").write_text(BRIEF.format(step_question=STEP_WORDINGS["base"].replace("`steps` lists", "The STEPS section lists"),
                                               categories=categories))
    for n, b in enumerate(batches, 1):
        print(f"batch {n}: {len(b)} runs, {sum(sizes[x] for x in b) / 1e3:.0f} KB, {b[0].split('__')[0]} .. {b[-1].split('__')[0]}")
    print(f"{len(test)} runs, {sum(sizes.values()) / 1e6:.1f} MB of text, {len(batches)} batches")


if __name__ == "__main__":
    main()
