"""Control: the same pixels, without the convolution.

The main sweep compares three representations, but each one is read by a
different architecture, so 'pixels beat tokens' could be a fact about
convolutions rather than about images. This arm feeds the SAME rendered frames
to a plain MLP -- identical representation, no spatial inductive bias.

It is given the same hidden width as the other MLP arms, which makes it much
LARGER than everything else (the 4096-wide input layer dominates). If it still
loses, the pixel advantage is the convolution and not the image.

    python control_flat_pixels.py  ->  results_control.json
"""

import json
import statistics as st
import time

import torch
import torch.nn as nn

from pixels_vs_tokens import (GRID, K_OBS, make_dataset, train_once, n_params,
                              TRAIN_SIZES, SEEDS, LR_GRID, STEPS, BATCH,
                              N_VAL, N_TEST)


class FlatPixelNet(nn.Module):
    """The rendered frames, flattened, into the same MLP as the other arms."""

    def __init__(self, hidden=188):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Flatten(),
            nn.Linear(K_OBS * GRID * GRID, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2))

    def forward(self, fr, tk, nm):
        return self.mlp(fr)


def main():
    val = make_dataset(N_VAL, seed=10_001)
    test = make_dataset(N_TEST, seed=10_002)
    print(f"FlatPixelNet params: {n_params(FlatPixelNet()):,}  "
          f"(the other arms have ~147,000)\n")

    # pilot the learning rate the same way the main sweep does
    pilot = make_dataset(1000, seed=12345)
    best, lr_pick = float("inf"), LR_GRID[0]
    for lr in LR_GRID:
        v, _ = train_once(FlatPixelNet, pilot, val, test, lr, STEPS, BATCH, 0)
        if v < best:
            best, lr_pick = v, lr
    print(f"pilot lr: {lr_pick}\n")

    runs = []
    for size in TRAIN_SIZES:
        scores = []
        for seed in SEEDS:
            train = make_dataset(size, seed=seed * 7919 + size)
            t0 = time.time()
            v, te = train_once(FlatPixelNet, train, val, test, lr_pick,
                               STEPS, BATCH, seed)
            scores.append(te)
            runs.append({"model": "pixels_flat", "train_size": size,
                         "seed": seed, "val_rmse": v, "test_rmse": te,
                         "seconds": time.time() - t0})
        print(f"pixels_flat n={size:5d}  test RMSE "
              f"{st.mean(scores):6.3f} ± {st.pstdev(scores):.3f} px")

    with open("results_control.json", "w") as f:
        json.dump({"lr": lr_pick, "params": n_params(FlatPixelNet()),
                   "runs": runs}, f, indent=1)
    print("\nwrote results_control.json")


if __name__ == "__main__":
    main()
