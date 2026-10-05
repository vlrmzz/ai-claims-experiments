"""
Pixels vs tokens in a toy 2D projectile world.

The question: does a model that SEES a trajectory learn its physics better than
one that READS the same trajectory as numbers?

The setup is built so the representations carry PROVABLY IDENTICAL information.
A projectile is quantised to a pixel of a G x G grid. The rendered frame is a
deterministic function of that (col, row) pair and nothing else; the token
encoding is that same pair. Neither side can see anything the other cannot.

Three arms, matched to within 0.2% on parameter count and trained for the same
number of steps on the same loss and the same targets:

  pixels   a small CNN over the rendered frames
  tokens   embedding lookups for col and row -- positions as OPAQUE SYMBOLS,
           so nothing tells it that 12 sits next to 13
  numeric  the same positions as normalised floats -- the metric handed over
           for free

'tokens' is the like-for-like comparison with 'pixels': neither is told the
geometry. 'numeric' isolates how much of any gap is about the geometry of the
representation rather than the modality.

Task: observe K frames, predict the position H steps after the last one.

Usage:
    python pixels_vs_tokens.py smoke     # quick check
    python pixels_vs_tokens.py run       # full sweep -> results.json
"""

import json
import sys
import time

import numpy as np
import torch
import torch.nn as nn

torch.set_num_threads(8)

# ----------------------------------------------------------------------------
# world
# ----------------------------------------------------------------------------

GRID = 32
K_OBS = 4
HORIZON = 4
RADIUS = 1.4

X0, Y0 = (2.0, 7.0), (2.0, 7.0)
SPEED, ANGLE_DEG, GRAVITY = (2.8, 5.0), (30.0, 75.0), (0.35, 0.80)


def sample_trajectories(n, rng):
    """Integer (col, row) arrays, shape (n, K_OBS + HORIZON).

    Rejection-samples launch parameters until the whole flight stays in frame,
    so nothing is clipped and every trajectory is fully observable.
    """
    steps = K_OBS + HORIZON
    t = np.arange(steps, dtype=np.float64)
    cols = np.empty((n, steps), dtype=np.int64)
    rows = np.empty((n, steps), dtype=np.int64)

    filled = 0
    while filled < n:
        b = max(256, (n - filled) * 2)
        x0, y0 = rng.uniform(*X0, b), rng.uniform(*Y0, b)
        v = rng.uniform(*SPEED, b)
        th = np.radians(rng.uniform(*ANGLE_DEG, b))
        g = rng.uniform(*GRAVITY, b)

        x = x0[:, None] + (v * np.cos(th))[:, None] * t[None, :]
        y = y0[:, None] + (v * np.sin(th))[:, None] * t[None, :] \
            - 0.5 * g[:, None] * (t[None, :] ** 2)

        c = np.rint(x).astype(np.int64)
        r = np.rint(GRID - 1 - y).astype(np.int64)     # row 0 = top
        ok = ((c >= 0) & (c < GRID) & (r >= 0) & (r < GRID)).all(axis=1)

        take = min(int(ok.sum()), n - filled)
        if take:
            cols[filled:filled + take] = c[ok][:take]
            rows[filled:filled + take] = r[ok][:take]
            filled += take
    return cols, rows


def render(cols, rows):
    """(n, K) int positions -> (n, K, GRID, GRID) frames.

    A disc of fixed radius centred on the quantised pixel: a deterministic
    function of (col, row), so the frame carries exactly what those two
    integers carry.
    """
    n, k = cols.shape
    yy, xx = np.mgrid[0:GRID, 0:GRID]
    frames = np.zeros((n, k, GRID, GRID), dtype=np.float32)
    for j in range(k):
        dx = xx[None] - cols[:, j, None, None]
        dy = yy[None] - rows[:, j, None, None]
        frames[:, j] = ((dx * dx + dy * dy) <= RADIUS * RADIUS).astype(np.float32)
    return frames


def make_dataset(n, seed):
    rng = np.random.default_rng(seed)
    cols, rows = sample_trajectories(n, rng)
    oc, orr = cols[:, :K_OBS], rows[:, :K_OBS]
    target = np.stack([cols[:, -1], rows[:, -1]], axis=1).astype(np.float32)
    target = target / (GRID - 1) * 2.0 - 1.0          # -> [-1, 1]
    tokens = np.stack([oc, orr], axis=2).astype(np.int64)         # (n, K, 2)
    numeric = (tokens.astype(np.float32) / (GRID - 1) * 2.0 - 1.0).reshape(n, -1)
    return (torch.from_numpy(render(oc, orr)), torch.from_numpy(tokens),
            torch.from_numpy(numeric), torch.from_numpy(target))


# ----------------------------------------------------------------------------
# models -- parameter budgets matched to within 0.2%
# ----------------------------------------------------------------------------

class PixelNet(nn.Module):
    def __init__(self, ch=16, hidden=188):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(K_OBS, ch, 3, 2, 1), nn.ReLU(),        # 16x16
            nn.Conv2d(ch, ch * 2, 3, 2, 1), nn.ReLU(),       # 8x8
            nn.Conv2d(ch * 2, ch * 2, 3, 2, 1), nn.ReLU(),   # 4x4
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(ch * 2 * 16, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2))

    def forward(self, fr, tk, nm):
        return self.head(self.conv(fr))


class TokenNet(nn.Module):
    def __init__(self, emb=48, hidden=188):
        super().__init__()
        self.col_emb = nn.Embedding(GRID, emb)
        self.row_emb = nn.Embedding(GRID, emb)
        self.mlp = nn.Sequential(
            nn.Linear(K_OBS * 2 * emb, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2))

    def forward(self, fr, tk, nm):
        x = torch.cat([self.col_emb(tk[:, :, 0]), self.row_emb(tk[:, :, 1])], 2)
        return self.mlp(x.flatten(1))


class NumericNet(nn.Module):
    def __init__(self, hidden=268):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(K_OBS * 2, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2))

    def forward(self, fr, tk, nm):
        return self.mlp(nm)


ARMS = {"pixels": PixelNet, "tokens": TokenNet, "numeric": NumericNet}


def n_params(m):
    return sum(p.numel() for p in m.parameters())


# ----------------------------------------------------------------------------
# training
# ----------------------------------------------------------------------------

@torch.no_grad()
def rmse_px(model, data):
    """RMSE in PIXELS, so the number means something physical."""
    fr, tk, nm, tg = data
    err = (model(fr, tk, nm) - tg) * (GRID - 1) / 2.0
    return float(torch.sqrt((err ** 2).sum(1).mean()))


def train_once(model_fn, train, val, test, lr, steps, batch, seed):
    torch.manual_seed(seed)
    model = model_fn()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps)
    lossf = nn.MSELoss()

    fr, tk, nm, tg = train
    n = tg.shape[0]
    g = torch.Generator().manual_seed(seed + 1)

    best_val, best_test = float("inf"), float("inf")
    for step in range(steps):
        idx = torch.randint(0, n, (min(batch, n),), generator=g)
        loss = lossf(model(fr[idx], tk[idx], nm[idx]), tg[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        if (step + 1) % 200 == 0 or step == steps - 1:
            model.eval()
            v = rmse_px(model, val)
            if v < best_val:
                best_val, best_test = v, rmse_px(model, test)
            model.train()
    return best_val, best_test


# ----------------------------------------------------------------------------
# reference points
# ----------------------------------------------------------------------------

def naive_extrapolation(n=20000, seed=999):
    """Least-squares quadratic through the 4 quantised observations, then
    extrapolated. NOT a lower bound -- a learned model can beat it by using the
    prior over launch parameters, which this estimator ignores."""
    rng = np.random.default_rng(seed)
    cols, rows = sample_trajectories(n, rng)
    t = np.arange(K_OBS, dtype=np.float64)
    T = K_OBS - 1 + HORIZON
    A = np.stack([np.ones_like(t), t, t ** 2], 1)
    proj = np.linalg.pinv(A).T @ np.array([1.0, T, T ** 2])
    pc, pr = cols[:, :K_OBS] @ proj, rows[:, :K_OBS] @ proj
    e2 = (pc - cols[:, -1]) ** 2 + (pr - rows[:, -1]) ** 2
    return float(np.sqrt(e2.mean()))


# ----------------------------------------------------------------------------
# experiment
# ----------------------------------------------------------------------------

TRAIN_SIZES = [125, 250, 500, 1000, 2000, 4000]
SEEDS = [0, 1, 2]
LR_GRID = [1e-3, 3e-3]
STEPS = 2500
BATCH = 128
N_VAL, N_TEST = 2000, 4000


def pick_lr(fn, val, test, steps, size=1000, seed=0):
    """One LR pilot per arm, chosen on validation only."""
    train = make_dataset(size, seed=12345)
    best, best_lr = float("inf"), LR_GRID[0]
    for lr in LR_GRID:
        v, _ = train_once(fn, train, val, test, lr, steps, BATCH, seed)
        if v < best:
            best, best_lr = v, lr
    return best_lr


def run(smoke=False):
    sizes, seeds = TRAIN_SIZES, SEEDS
    steps = STEPS
    if smoke:
        sizes, seeds, steps = [250, 1000], [0], 400

    val = make_dataset(N_VAL, seed=10_001)
    test = make_dataset(N_TEST, seed=10_002)
    naive = naive_extrapolation(n=2000 if smoke else 20000)

    print(f"naive quadratic extrapolation: {naive:.3f} px  "
          f"(a baseline, not a bound)\n")
    for a, fn in ARMS.items():
        print(f"  {a:8s} {n_params(fn()):,} params")

    lrs = {a: pick_lr(fn, val, test, steps) for a, fn in ARMS.items()}
    print(f"\npilot learning rates: {lrs}\n")

    res = {"naive_extrapolation": naive, "grid": GRID, "k_obs": K_OBS,
           "horizon": HORIZON, "steps": steps, "lrs": lrs,
           "params": {a: n_params(fn()) for a, fn in ARMS.items()}, "runs": []}

    for size in sizes:
        for seed in seeds:
            train = make_dataset(size, seed=seed * 7919 + size)
            for arm, fn in ARMS.items():
                t0 = time.time()
                v, te = train_once(fn, train, val, test, lrs[arm],
                                   steps, BATCH, seed)
                dt = time.time() - t0
                res["runs"].append({"model": arm, "train_size": size,
                                    "seed": seed, "val_rmse": v,
                                    "test_rmse": te, "seconds": dt})
                print(f"{arm:8s} n={size:5d} seed={seed}  "
                      f"test RMSE {te:6.3f} px   ({dt:5.1f}s)")
        print()

    # control: are the cheap arms simply under-trained at matched steps?
    print("control: 4x steps for the cheap arms at n=4000")
    big = make_dataset(4000, seed=4000)
    for arm in ("tokens", "numeric"):
        v, te = train_once(ARMS[arm], big, val, test, lrs[arm],
                           steps * 4, BATCH, 0)
        res["runs"].append({"model": arm + "_4x", "train_size": 4000,
                            "seed": 0, "val_rmse": v, "test_rmse": te,
                            "seconds": 0})
        print(f"  {arm}_4x  test RMSE {te:.3f} px")

    with open("results.json", "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote results.json")
    return res


if __name__ == "__main__":
    run(smoke=(sys.argv[1] if len(sys.argv) > 1 else "smoke") == "smoke")
