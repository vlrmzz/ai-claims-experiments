"""Figures for the pixels-vs-tokens experiment.

    python viz.py          # reads results.json, writes the two PNGs
"""

import json
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pixels_vs_tokens import (GRID, K_OBS, HORIZON, make_dataset,
                              sample_trajectories, render)

PAPER = "#FBFAF7"
INK = "#1A1C1A"
MUTED = "#6B7069"
RULE = "#D8D5CB"
COLOR = {"pixels": "#1F5C46", "tokens": "#B4531F", "numeric": "#2B4C8C",
         "pixels_flat": "#7A8F85"}
LABEL = {"pixels": "pixels, CNN",
         "pixels_flat": "pixels, plain MLP (5.7x the parameters)",
         "tokens": "tokens (positions as symbols)",
         "numeric": "numeric (positions as floats)"}
ARM_ORDER = ("numeric", "pixels", "pixels_flat", "tokens")

plt.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": RULE, "font.size": 10,
    "font.family": "sans-serif",
    "font.sans-serif": ["IBM Plex Sans", "Helvetica Neue", "Arial", "DejaVu Sans"],
})


def fig_representations(path="fig-representations.png"):
    """One trajectory, both ways: the frames and the integers behind them."""
    rng = np.random.default_rng(7)
    cols, rows = sample_trajectories(1, rng)
    frames = render(cols[:, :K_OBS], rows[:, :K_OBS])[0]

    n = K_OBS + 1
    fig, axes = plt.subplots(1, n, figsize=(9.2, 2.6))
    for j in range(K_OBS):
        axes[j].imshow(1.0 - frames[j], cmap="gray", vmin=0, vmax=1,
                       interpolation="nearest")
        axes[j].set_title(f"t = {j}", fontsize=9, color=INK, pad=6)
        axes[j].set_xlabel(f"({cols[0, j]}, {rows[0, j]})", fontsize=8.5,
                           color=MUTED, labelpad=4)

    tgt = render(cols[:, -1:], rows[:, -1:])[0, 0]
    axes[-1].imshow(1.0 - tgt, cmap="gray", vmin=0, vmax=1,
                    interpolation="nearest")
    axes[-1].set_title(f"t = {K_OBS - 1 + HORIZON}  (target)", fontsize=9,
                       color=COLOR["pixels"], pad=6)
    axes[-1].set_xlabel(f"({cols[0, -1]}, {rows[0, -1]})", fontsize=8.5,
                        color=COLOR["pixels"], labelpad=4)
    for a in axes:
        a.set_xticks([]); a.set_yticks([])
        for s in a.spines.values():
            s.set_color(RULE)

    fig.suptitle("The same trajectory, two representations", fontsize=12,
                 color=INK, y=1.04)
    fig.text(0.5, -0.10,
             "Top: what the pixel model sees.  Bottom: the integers the token "
             "model reads.\nThe disc is a deterministic function of the "
             "quantised (col, row), so neither side\nhas access to anything "
             "the other does not.",
             ha="center", fontsize=9, color=MUTED, linespacing=1.6)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    print("wrote", path)


def fig_curves(results, path="fig-sample-efficiency.png"):
    runs = [r for r in results["runs"] if not r["model"].endswith("_4x")]
    by = defaultdict(lambda: defaultdict(list))
    for r in runs:
        by[r["model"]][r["train_size"]].append(r["test_rmse"])

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for arm in ARM_ORDER:
        if arm not in by:
            continue
        sizes = sorted(by[arm])
        mean = np.array([np.mean(by[arm][s]) for s in sizes])
        sd = np.array([np.std(by[arm][s], ddof=1) if len(by[arm][s]) > 1 else 0.0
                       for s in sizes])
        style = "o--" if arm == "pixels_flat" else "o-"
        ax.plot(sizes, mean, style, color=COLOR[arm], label=LABEL[arm],
                lw=1.8, ms=5, zorder=3)
        ax.fill_between(sizes, mean - sd, mean + sd, color=COLOR[arm],
                        alpha=0.15, lw=0, zorder=2)

    ax.set_xscale("log")
    ax.set_xticks(sorted(by["pixels"]))
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel("training trajectories")
    ax.set_ylabel("test error (pixels, RMSE)")
    ax.set_title("Predicting where the projectile lands, "
                 f"{HORIZON} steps ahead", fontsize=12, pad=12, loc="left")
    ax.grid(True, which="major", color=RULE, lw=0.7, alpha=0.7, zorder=1)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    leg = ax.legend(frameon=False, fontsize=9.5, loc="upper right")
    for t in leg.get_texts():
        t.set_color(INK)
    fig.text(0.0, -0.06,
             "Mean over 3 seeds; band is ±1 sd. The three solid arms share a "
             "parameter budget (within 0.2%)\nand a step budget. The dashed arm "
             "is the same pixels without the convolution: it tracks the token\n"
             "arm despite 5.7x the parameters, which is where the pixel "
             "advantage actually comes from.",
             fontsize=9, color=MUTED, linespacing=1.6)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    print("wrote", path)


def summary(results):
    """Print the table the write-up needs."""
    by = defaultdict(lambda: defaultdict(list))
    for r in results["runs"]:
        by[r["model"]][r["train_size"]].append(r["test_rmse"])
    sizes = sorted(by["pixels"])
    print(f"\n{'n':>6} | " + " | ".join(f"{a:>16}" for a in ARM_ORDER))
    print("-" * 64)
    for s in sizes:
        cells = []
        for a in ARM_ORDER:
            v = by[a][s]
            if not v:
                cells.append(" " * 16); continue
            cells.append(f"{np.mean(v):6.2f} ± {np.std(v, ddof=1):4.2f}")
        print(f"{s:>6} | " + " | ".join(f"{c:>16}" for c in cells))
    for k in ("tokens_4x", "numeric_4x"):
        if k in by:
            print(f"{k}: {np.mean(by[k][4000]):.3f} px")
    print(f"\nnaive quadratic extrapolation: "
          f"{results['naive_extrapolation']:.3f} px")
    med = defaultdict(list)
    for r in results["runs"]:
        if not r["model"].endswith("_4x"):
            med[r["model"]].append(r["seconds"])
    for a in ARM_ORDER:
        if med[a]:
            print(f"median seconds per run, {a}: {np.median(med[a]):.1f}")


def merge_control(results, path="results_control.json"):
    try:
        results["runs"] += json.load(open(path))["runs"]
    except FileNotFoundError:
        pass
    return results


if __name__ == "__main__":
    results = merge_control(json.load(open("results.json")))
    fig_representations()
    fig_curves(results)
    summary(results)
