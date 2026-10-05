"""Figures for the post, from the result files in this folder.

    python figures.py       # needs matplotlib; writes four PNGs into figures/

  agent-trace-failures-sample.png      every GPT-5 run on tau2-bench, failed runs marked
  agent-trace-failures-patterns.png    the eight failure patterns, split by whose fault
  agent-trace-failures-step.png        who finds the failing step: Jev, Claude, on the held-out runs
  agent-trace-failures-confidence.png  how often each model is right, by its own confidence
"""

import csv
import json
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

from traces import DOMAINS, HERE, failed, load_runs

OUT = HERE / "figures"

PAPER = "#FBFAF7"
INK = "#1A1C1A"
MUTED = "#6B7069"
RULE = "#D8D5CB"
GREEN = "#1F5C46"
GREEN_LIGHT = "#9DBBAE"
ORANGE = "#B4531F"
GREY = "#7A8F85"
EMPTY = "#E9E6DC"

FAULT_GROUPS = [
    ("agent", GREEN, {"agent"}),
    ("both, or unclear", GREY, {"agent and benchmark", "unclear"}),
    ("benchmark", ORANGE, {"task definition", "grader", "user simulator"}),
]
DATASET_NAMES = {"agentrx_tau": "AgentRx\ntau-bench retail", "agentrx_magentic": "AgentRx\nMagentic-One",
                 "whowhen_hand": "Who&When\nMagentic-One", "whowhen_auto": "Who&When\ngenerated teams"}

plt.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": RULE, "font.size": 10,
    "font.family": "sans-serif",
    "font.sans-serif": ["IBM Plex Sans", "Helvetica Neue", "Arial", "DejaVu Sans"],
})


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def bare(ax):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def fig_sample():
    runs = load_runs()
    n_failed = sum(r["reward"] < 1 for r in runs)
    n_tasks = len({(r["domain"], r["task_id"]) for r in runs})
    n_failed_tasks = len({(r["domain"], r["task_id"]) for r in runs if r["reward"] < 1})
    widest = max(len({r["task_id"] for r in runs if r["domain"] == d}) for d in DOMAINS)

    fig, axes = plt.subplots(len(DOMAINS), 1, figsize=(9.2, 2.0))
    fig.subplots_adjust(hspace=0.9, top=0.78, bottom=0.2)
    for ax, domain in zip(axes, DOMAINS):
        for r in (r for r in runs if r["domain"] == domain):
            color = EMPTY if r["reward"] >= 1 else GREEN
            ax.add_patch(Rectangle((int(r["task_id"]) + 0.1, r["trial"] + 0.1), 0.8, 0.8, color=color, lw=0))
        n = len({r["task_id"] for r in runs if r["domain"] == domain})
        ax.set_xlim(0, widest)
        ax.set_ylim(4, 0)
        ax.set_aspect("equal")
        ax.set_yticks([2])
        ax.set_yticklabels(["4 trials"], fontsize=8.5)
        ax.set_xticks([0.5, n - 0.5])
        ax.set_xticklabels(["task 0", f"task {n - 1}"], fontsize=8.5)
        ax.set_title(f"{domain}, {n} tasks", fontsize=9.5, loc="left", pad=5)
        bare(ax)
    fig.suptitle(f"GPT-5 on tau2-bench: {n_failed} failed runs, on {n_failed_tasks} of {n_tasks} tasks",
                 fontsize=12, x=0.125, ha="left", y=1.06)
    fig.legend(handles=[Patch(color=GREEN, label=f"failed ({n_failed})"), Patch(color=EMPTY, label="passed")],
               loc="lower left", bbox_to_anchor=(0.115, -0.12), ncol=2, frameon=False, fontsize=9)
    save(fig, "agent-trace-failures-sample.png")


def fault_group(fault):
    for name, _, members in FAULT_GROUPS:
        if fault in members:
            return name
    raise ValueError(fault)


def fig_patterns():
    """The eight patterns from the reference reading, by number of runs, split by whose fault."""
    rows = read_csv(HERE / "reference_labels.csv")
    names = {p["id"]: p["name"] for p in json.loads((HERE / "patterns.json").read_text())}
    by_pattern = defaultdict(Counter)
    tasks = defaultdict(set)
    for r in rows:
        by_pattern[r["pattern"]][fault_group(r["fault"])] += 1
        tasks[r["pattern"]].add((r["domain"], r["task_id"]))
    order = sorted(by_pattern, key=lambda p: sum(by_pattern[p].values()))
    top = max(sum(c.values()) for c in by_pattern.values())

    fig, ax = plt.subplots(figsize=(7.4, 0.42 * len(order) + 1.3))
    gap = 0.012 * top
    for y, p in enumerate(order):
        left = 0
        for group, color, _ in FAULT_GROUPS:
            n = by_pattern[p][group]
            if n:
                ax.barh(y, max(n - gap, 0.2 * n), left=left, height=0.62, color=color, lw=0)
                left += n
        ax.text(left + gap * 2, y, f"{left} runs, {len(tasks[p])} tasks", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([names[p] for p in order], fontsize=9.5, color=INK)
    ax.set_xlim(0, top * 1.3)
    ax.set_xticks([])
    bare(ax)
    ax.set_title(f"What went wrong in {len(rows)} failed runs, as read by a model", fontsize=12, loc="left", pad=28)
    ax.legend(handles=[Patch(color=c, label=f"fault: {g}") for g, c, _ in FAULT_GROUPS],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=9,
              borderaxespad=0.2, handlelength=1.2)
    save(fig, "agent-trace-failures-patterns.png")


def fig_step():
    """On the held-out half of the annotated runs: how often each model names the human's step."""
    judge = json.loads((HERE / "judge_results.json").read_text())["by_dataset"]
    order = ["agentrx_tau", "agentrx_magentic", "whowhen_hand", "whowhen_auto"]
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    width = 0.36
    for i, d in enumerate(order):
        n = judge[d]["runs"]
        for k, (who, color) in enumerate((("jev", GREEN), ("judge", ORANGE))):
            v = judge[d]["step_exact"][who]
            ax.bar(i + (k - 0.5) * width, v, width=width - 0.03, color=color, lw=0)
            ax.text(i + (k - 0.5) * width, v + 0.015, f"{v:.0%}", ha="center", fontsize=8.5, color=INK)
        ax.text(i, -0.07, f"{n} runs", ha="center", fontsize=8, color=MUTED, transform=ax.get_xaxis_transform())
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([DATASET_NAMES[d] for d in order], fontsize=9, color=INK)
    ax.tick_params(axis="x", pad=14)
    ax.set_ylim(0, 0.7)
    ax.set_yticks([0, 0.25, 0.5])
    ax.set_yticklabels(["0", "25%", "50%"], fontsize=8.5)
    ax.grid(True, axis="y", color=RULE, lw=0.7, alpha=0.7, zorder=0)
    ax.set_axisbelow(True)
    bare(ax)
    ax.set_title("Share of failed runs where the model names the same step as the human annotator",
                 fontsize=11, loc="left", pad=26)
    ax.legend(handles=[Patch(color=GREEN, label="Jev, decision model"), Patch(color=ORANGE, label="Claude, reading the full run")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9, borderaxespad=0.2, handlelength=1.2)
    save(fig, "agent-trace-failures-step.png")


def fig_confidence():
    """Share of exact step answers, by the confidence each model gave its own answer."""
    jev = json.loads((HERE / "tuning_results.json").read_text())["test_by_probability"]
    judge = json.loads((HERE / "judge_results.json").read_text())["judge_by_confidence"]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9), sharey=True)
    for ax, bins, color, title in ((axes[0], jev, GREEN, "Jev, probability of its answer"),
                                   (axes[1], judge, ORANGE, "Claude, stated confidence")):
        for i, b in enumerate(bins):
            ax.bar(i, b["exact"], width=0.7, color=color, lw=0)
            ax.text(i, b["exact"] + 0.02, f"{b['exact']:.0%}", ha="center", fontsize=8.5, color=INK)
            ax.text(i, -0.08, f"n={b['n']}", ha="center", fontsize=8, color=MUTED, transform=ax.get_xaxis_transform())
        ax.set_xticks(range(len(bins)))
        ax.set_xticklabels([b["bin"].replace("0.00", "0").replace("1.00", "1").replace("1.0", "1").replace("0.0-", "0-") for b in bins], fontsize=8.5)
        ax.tick_params(axis="x", pad=12)
        ax.set_title(title, fontsize=10, loc="left", pad=8)
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.5, 1])
        ax.set_yticklabels(["0", "50%", "100%"], fontsize=8.5)
        ax.grid(True, axis="y", color=RULE, lw=0.7, alpha=0.7, zorder=0)
        ax.set_axisbelow(True)
        bare(ax)
    fig.suptitle("Share of step answers that match the human, by the model's own confidence (130 held-out runs)",
                 fontsize=10.5, x=0.125, ha="left", y=1.04)
    save(fig, "agent-trace-failures-confidence.png")


if __name__ == "__main__":
    fig_sample()
    fig_patterns()
    fig_step()
    fig_confidence()
