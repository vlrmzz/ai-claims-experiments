"""Figures for "Nobody told it what a noun is", from the files that attn_emergence.py writes.

    python viz_emergence.py     # writes fig-emergence.png and fig-control.png
"""
import numpy as np
import matplotlib.pyplot as plt

CLASSES = ["nouns", "verbs", "adjectives", "adverbs"]
COLOUR = ["#1F5C46", "#B4531F", "#2B4C8C", "#8A6FB0"]


def load(path):
    return dict(np.load(path))


def fig_emergence(run, moments=(0, 500, 1500, 4000)):
    """Top: the same words at four moments, on axes fixed from the final state.
    Bottom: the loss, which is the only thing trained, and the two measures."""
    steps = run["step"]
    fig = plt.figure(figsize=(11, 6.6))
    grid = fig.add_gridspec(2, 4, height_ratios=[1, 0.95], hspace=0.38, wspace=0.3)
    limit = np.abs(run["path2d"][-1]).max() * 1.05
    for j, moment in enumerate(moments):
        i = int(np.argmin(np.abs(steps - moment)))
        ax = fig.add_subplot(grid[0, j])
        for c, name in enumerate(CLASSES):
            sel = run["labels"] == c
            ax.scatter(*run["path2d"][i][sel].T, s=5, color=COLOUR[c], alpha=0.6, linewidths=0, label=name)
        ax.set_title(f"step {steps[i]}", fontsize=10)
        ax.set_xlim(-limit, limit); ax.set_ylim(-limit, limit)
        ax.set_xticks([]); ax.set_yticks([])
        if j == 0:
            ax.legend(frameon=False, fontsize=8, markerscale=2.5, loc="upper left")

    ax = fig.add_subplot(grid[1, :2])
    ax.plot(steps, run["loss"], color="black")
    ax.set_title("loss: the only thing that is trained", fontsize=10, loc="left")
    ax.set_xlabel("training step"); ax.set_ylabel("next-word loss")

    ax = fig.add_subplot(grid[1, 2:])
    for c, name in enumerate(CLASSES):
        ax.plot(steps, run["purity_by_class"][:, c], color=COLOUR[c], label=name)
        ax.axhline(run["share"][c], color=COLOUR[c], linestyle=":", linewidth=1)
    ax.plot(steps, run["probe"], color="black", linestyle="--", label="linear probe")
    ax.set_title("same-class neighbours (dotted: chance), and the probe", fontsize=10, loc="left")
    ax.set_xlabel("training step"); ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    return fig


def fig_control(real, shuffled):
    """Real text against the same text with the words of each sentence shuffled."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.1))
    chance = float((real["share"] ** 2).sum())
    for ax, key, title, base in ((axes[0], "loss", "loss", None),
                                 (axes[1], "purity", "neighbours with the same class", chance),
                                 (axes[2], "probe", "linear probe", float(real["share"].max()))):
        ax.plot(real["step"], real[key], color=COLOUR[0], label="real text")
        ax.plot(shuffled["step"], shuffled[key], color=COLOUR[1], label="shuffled")
        if base is not None:
            ax.axhline(base, color="grey", linestyle=":", linewidth=1, label="chance")
            ax.set_ylim(0, 1)
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("training step")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


def summary(real, shuffled):
    print(f"{'':34s}{'real text':>11s}{'shuffled':>11s}{'chance':>9s}")
    print(f"{'loss after training':34s}{real['loss'][-1]:>11.2f}{shuffled['loss'][-1]:>11.2f}{'':>9s}")
    print(f"{'neighbours with the same class':34s}{real['purity'][-1]:>11.0%}{shuffled['purity'][-1]:>11.0%}"
          f"{float((real['share'] ** 2).sum()):>9.0%}")
    for c, name in enumerate(CLASSES):
        print(f"{'  ' + name:34s}{real['purity_by_class'][-1][c]:>11.0%}{shuffled['purity_by_class'][-1][c]:>11.0%}"
              f"{real['share'][c]:>9.0%}")
    print(f"{'linear probe':34s}{real['probe'][-1]:>11.0%}{shuffled['probe'][-1]:>11.0%}{real['share'].max():>9.0%}")


if __name__ == "__main__":
    real, shuffled = load("run_real.npz"), load("run_shuffled.npz")
    summary(real, shuffled)
    fig_emergence(real).savefig("fig-emergence.png", dpi=170, bbox_inches="tight")
    fig_control(real, shuffled).savefig("fig-control.png", dpi=170, bbox_inches="tight")
    print("wrote fig-emergence.png, fig-control.png")
