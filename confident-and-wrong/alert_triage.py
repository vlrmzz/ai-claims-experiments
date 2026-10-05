"""Confident and wrong: does the training reward decide whether a decision model is calibrated?

A toy security-operations world in which the true probability of every label is
known exactly, a tiny decision model (one slot per option, read off in a single
forward pass), and three ways of training it:

    ce     ordinary cross-entropy
    acc    reward 1 for the right answer (expected reward = p[gold])
    rlcd   policy gradient on a proper-scoring-rule reward, as Laya's author describes it

Each trained model is then measured where it was trained and under three shifts:
more options than it ever saw, a log format it cannot read, and a base rate of
90 % benign traffic.

    python alert_triage.py smoke     # under a minute, checks the setup
    python alert_triage.py run       # the full sweep -> results.json
    python alert_triage.py example   # one worked session -> example.json

Each method is trained at four training-set sizes, three seeds each. Needs PyTorch and
NumPy, runs on CPU in four worker processes, and the full sweep takes about 45 minutes on an M1.
"""
import json
import math
import sys
import time

import numpy as np
import torch
import torch.nn as nn

# --------------------------------------------------------------------------- the world
EVENTS = ["login_ok", "login_fail", "mfa_prompt", "password_reset", "port_probe", "new_conn",
          "dns_query", "dns_long", "http_200", "http_404", "http_500", "sql_error", "param_fuzz",
          "file_read", "file_write", "large_upload", "large_download", "proc_spawn", "priv_change",
          "new_admin", "cron_edit", "smb_conn", "kerberos_req", "beacon", "archive_create",
          "mail_send", "mail_link_click", "usb_mount", "log_clear", "av_alert"]

# what ordinary traffic looks like; every class emits these most of the time
BACKGROUND = {"login_ok": 6, "http_200": 8, "dns_query": 6, "file_read": 5, "new_conn": 4, "mail_send": 3,
              "file_write": 2, "proc_spawn": 2, "http_404": 1.5, "login_fail": 1, "mfa_prompt": 1,
              "large_download": 1}

# the events each class emits more often than the background does
SIGNATURE = {
    "benign": {},
    "brute_force": {"login_fail": 5, "password_reset": 1},
    "credential_stuffing": {"login_fail": 3, "login_ok": 2, "mfa_prompt": 2},
    "port_scan": {"port_probe": 5, "new_conn": 2},
    "sql_injection": {"sql_error": 4, "http_500": 2, "param_fuzz": 2},
    "web_fuzzing": {"http_404": 4, "param_fuzz": 3, "http_500": 1},
    "data_exfiltration": {"large_upload": 4, "archive_create": 2, "dns_long": 1},
    "lateral_movement": {"smb_conn": 4, "kerberos_req": 3, "new_conn": 1},
    "privilege_escalation": {"priv_change": 4, "new_admin": 2, "proc_spawn": 2},
    "c2_beaconing": {"beacon": 4, "dns_long": 3, "dns_query": 1},
    "phishing": {"mail_link_click": 4, "mail_send": 2, "login_ok": 1},
    "ransomware": {"file_write": 4, "log_clear": 2, "av_alert": 2, "proc_spawn": 1},
}
CLASSES = list(SIGNATURE)
C, V = len(CLASSES), len(EVENTS)
SIGNAL = 0.30          # share of a session's events drawn from the class signature
L_MIN, L_MAX = 4, 10   # events per session
TRAIN_K = (2, 3, 4, 5, 6)  # option counts seen in training


def _dist(weights):
    v = np.full(V, 0.02)                       # every event is possible, a little
    for name, w in weights.items():
        v[EVENTS.index(name)] += w
    return v / v.sum()


BG = _dist(BACKGROUND)
THETA = np.stack([BG if not SIGNATURE[c] else (1 - SIGNAL) * BG + SIGNAL * _dist(SIGNATURE[c]) for c in CLASSES])
LOG_THETA = np.log(THETA)
UNIFORM = np.full(C, 1 / C)
MOSTLY_BENIGN = np.array([0.90] + [0.10 / (C - 1)] * (C - 1))


def sample_sessions(n, rng, prior=UNIFORM):
    """n sessions: the true class, the events, and how many events are real (the rest is padding)."""
    gold = rng.choice(C, size=n, p=prior)
    length = rng.integers(L_MIN, L_MAX + 1, size=n)
    u = rng.random((n, L_MAX))
    events = (u[..., None] > np.cumsum(THETA, 1)[gold][:, None, :]).sum(-1).clip(max=V - 1)
    return gold, events, length


def sample_options(gold, k, rng):
    """k options per session: the true class plus k-1 others, in random order."""
    n = len(gold)
    r = rng.random((n, C))
    r[np.arange(n), gold] = -1.0               # the true class always makes the cut
    opts = np.argsort(r, 1)[:, :k]
    opts = np.take_along_axis(opts, np.argsort(rng.random((n, k)), 1), 1)
    return opts, (opts == gold[:, None]).argmax(1)


def true_posterior(opts, events, length, prior=UNIFORM, readable=True):
    """Exact P(class | events) over the offered options. This is what a perfect model would report."""
    n, k = opts.shape
    if not readable:                           # nothing in the session can be interpreted
        return np.full((n, k), 1 / k)
    valid = np.arange(L_MAX)[None, :] < length[:, None]
    ll = LOG_THETA[opts[:, :, None], events[:, None, :]]           # [n, k, L]
    logp = (ll * valid[:, None, :]).sum(-1) + np.log(prior)[opts]
    logp -= logp.max(1, keepdims=True)
    p = np.exp(logp)
    return p / p.sum(1, keepdims=True)


# --------------------------------------------------------------------------- the model
PAD, CLS, QUESTION, MASK = 0, 1, 2, 3
N_SPECIAL = 4
EVENT0 = N_SPECIAL + C            # event tokens
UNSEEN0 = EVENT0 + V              # the same events in a format the model never sees in training
N_TOKENS = UNSEEN0 + V


class DecisionModel(nn.Module):
    """[CLS] [QUESTION] option slots ... events ...  ->  one logit per option slot.

    An option slot is the [MASK] embedding plus the embedding of that option's name, which is
    the one-token version of Laya's "[MASK] billing: invoices, refunds". Events are exchangeable
    in this world, so there are no position embeddings and no option count is "out of range"
    for the architecture itself.
    """

    def __init__(self, d=64, layers=2, heads=4):
        super().__init__()
        self.tok = nn.Embedding(N_TOKENS, d, padding_idx=PAD)
        self.kind = nn.Embedding(3, d)         # 0 special, 1 option slot, 2 event
        layer = nn.TransformerEncoderLayer(d, heads, 2 * d, dropout=0.0, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.scorer = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))

    def forward(self, opts, events, length, readable=True):
        n, k = opts.shape
        head = torch.tensor([CLS, QUESTION]).expand(n, 2)
        slots = self.tok(torch.full((n, k), MASK)) + self.tok(opts + N_SPECIAL) + self.kind(torch.ones(n, k, dtype=torch.long))
        ev_tok = events + (EVENT0 if readable else UNSEEN0)
        x = torch.cat([self.tok(head) + self.kind(torch.zeros(n, 2, dtype=torch.long)), slots,
                       self.tok(ev_tok) + self.kind(torch.full((n, L_MAX), 2))], 1)
        pad = torch.zeros(n, 2 + k + L_MAX, dtype=torch.bool)
        pad[:, 2 + k:] = torch.arange(L_MAX)[None, :] >= length[:, None]
        h = self.encoder(x, src_key_padding_mask=pad)
        return self.scorer(h[:, 2:2 + k]).squeeze(-1)          # one logit per option


# --------------------------------------------------------------------------- three rewards
def loss_ce(z, gold, _progress):
    return nn.functional.cross_entropy(z, gold)


def loss_acc(z, gold, _progress):
    """Reward 1 if the sampled answer is right. Its expectation is p[gold], so maximise that."""
    return -torch.softmax(z, -1).gather(1, gold[:, None]).mean()


def loss_rlcd(z, gold, progress, group=8, w_sph=0.5, log_floor=-9.21):
    """RLCD as the author's write-up describes it: explore around the logits with Gaussian noise,
    score each noisy distribution with a strictly proper rule (log + 0.5 * spherical), and move
    the logits toward the samples that scored above their group's mean. No cross-entropy term."""
    sigma = 1.0 + (0.3 - 1.0) * progress
    eps = torch.randn((group,) + z.shape) * sigma
    eps = eps - eps.mean(-1, keepdim=True)                      # a shift of all logits changes nothing
    zn = z.detach().unsqueeze(0) + eps
    q = torch.softmax(zn, -1)
    q_gold = q.gather(2, gold.expand(group, -1)[..., None]).squeeze(-1)
    reward = torch.log(q_gold.clamp_min(1e-12)).clamp_min(log_floor) + w_sph * q_gold / q.norm(dim=-1)
    adv = reward - reward.mean(0, keepdim=True)
    adv = adv / (adv.std() + 1e-6)
    logp = -((zn - z.unsqueeze(0)) ** 2).sum(-1) / (2 * sigma ** 2)
    return -(adv * logp).mean()


ARMS = {"ce": loss_ce, "acc": loss_acc, "rlcd": loss_rlcd}


def train(arm, seed, n_train, steps, batch=256, lr=1e-3):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    gold, events, length = sample_sessions(n_train, np.random.default_rng(1000 + seed))   # a fixed, finite training set
    model = DecisionModel()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    for step in range(steps):
        idx = rng.integers(0, n_train, batch)
        k = int(rng.choice(TRAIN_K))
        opts, gi = sample_options(gold[idx], k, rng)             # fresh option sets every step
        z = model(torch.from_numpy(opts), torch.from_numpy(events[idx]), torch.from_numpy(length[idx]))
        loss = ARMS[arm](z, torch.from_numpy(gi), step / max(1, steps - 1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
    return model.eval()


# --------------------------------------------------------------------------- measuring
CONDITIONS = {
    "trained": dict(k=4, label="as trained: 4 options"),
    "k8": dict(k=8, label="8 options"),
    "k12": dict(k=12, label="12 options"),
    "unreadable": dict(k=4, readable=False, label="unreadable log format"),
    "benign90": dict(k=4, prior=MOSTLY_BENIGN, label="90 % benign traffic"),
}
BINS = 10


def ece(conf, correct, bins=15):
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for i in range(bins):
        sel = (conf > edges[i]) & (conf <= edges[i + 1]) if i else (conf <= edges[1])
        if sel.any():
            e += sel.mean() * abs(conf[sel].mean() - correct[sel].mean())
    return float(e)


def fit_temperature(z, gi):
    """The one-parameter repair: the T that minimises negative log-likelihood on held-out data."""
    z, gi = torch.from_numpy(z), torch.from_numpy(gi)
    grid = np.exp(np.linspace(math.log(0.05), math.log(100), 500))
    nll = [nn.functional.cross_entropy(z / t, gi).item() for t in grid]
    return float(grid[int(np.argmin(nll))])


def softmax(z, t=1.0):
    z = z / t
    z = z - z.max(1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(1, keepdims=True)


def logits_of(model, opts, events, length, readable):
    out = []
    with torch.no_grad():
        for i in range(0, len(opts), 1000):
            s = slice(i, i + 1000)
            out.append(model(torch.from_numpy(opts[s]), torch.from_numpy(events[s]),
                             torch.from_numpy(length[s]), readable=readable).numpy())
    return np.concatenate(out).astype(np.float64)


def describe(p, gi, truth):
    """Accuracy, confidence and calibration of a set of reported distributions."""
    n = len(gi)
    pred = p.argmax(1)
    conf = p.max(1)
    correct = (pred == gi).astype(float)
    p_true_of_pred = truth[np.arange(n), pred]          # the real probability that this answer is right
    edges = np.linspace(0, 1, BINS + 1)
    rel = []
    for i in range(BINS):
        sel = (conf > edges[i]) & (conf <= edges[i + 1])
        rel.append([int(sel.sum()), float(conf[sel].mean()) if sel.any() else None,
                    float(correct[sel].mean()) if sel.any() else None])
    gate = conf >= 0.9
    return {
        "accuracy": float(correct.mean()),
        "confidence": float(conf.mean()),
        "ece": ece(conf, correct),
        "gap_to_truth": float(np.abs(conf - p_true_of_pred).mean()),
        "gate90_share": float(gate.mean()),
        "gate90_precision": float(correct[gate].mean()) if gate.any() else None,
        "reliability": rel,
    }


def evaluate(model, seed, n_test):
    out = {}
    for name, cond in CONDITIONS.items():
        rng = np.random.default_rng(50_000 + seed * 100 + list(CONDITIONS).index(name))
        prior, readable, k = cond.get("prior", UNIFORM), cond.get("readable", True), cond["k"]
        gold, events, length = sample_sessions(2 * n_test, rng, prior)
        opts, gi = sample_options(gold, k, rng)
        truth = true_posterior(opts, events, length, prior, readable)
        z = logits_of(model, opts, events, length, readable)
        a, b = slice(0, n_test), slice(n_test, 2 * n_test)       # a: held out for the refit, b: test
        t = fit_temperature(z[a], gi[a])
        out[name] = {
            "model": describe(softmax(z[b]), gi[b], truth[b]),
            "model_refit": dict(describe(softmax(z[b], t), gi[b], truth[b]), temperature=t),
            "truth": describe(truth[b], gi[b], truth[b]),
        }
    return out


def one_run(job):
    arm, seed, n_train, steps, n_test = job
    torch.set_num_threads(1)
    t0 = time.time()
    model = train(arm, seed, n_train, steps)
    return arm, seed, n_train, evaluate(model, seed, n_test), time.time() - t0


def main(mode):
    import multiprocessing as mp
    smoke = mode == "smoke"
    cfg = dict(train_sizes=[4000] if smoke else [1000, 4000, 16000, 64000],
               steps=400 if smoke else 3000, n_test=1000 if smoke else 5000,
               seeds=[0] if smoke else [0, 1, 2])
    print(f"{C} classes, {V} event types, {N_TOKENS} tokens; "
          f"{sum(p.numel() for p in DecisionModel().parameters()):,} parameters")
    results = {"config": dict(cfg, signal=SIGNAL, session_length=[L_MIN, L_MAX], train_k=list(TRAIN_K),
                              classes=CLASSES, events=EVENTS,
                              conditions={k: v["label"] for k, v in CONDITIONS.items()}),
               "runs": {}}
    jobs = [(arm, seed, n, cfg["steps"], cfg["n_test"])
            for n in cfg["train_sizes"] for arm in ARMS for seed in cfg["seeds"]]
    with mp.get_context("spawn").Pool(min(4, len(jobs))) as pool:
        for arm, seed, n, res, secs in pool.imap_unordered(one_run, jobs):
            results["runs"][f"{arm}/{n}/{seed}"] = res
            line = " | ".join(f"{name}: acc {r['model']['accuracy']:.3f} conf {r['model']['confidence']:.3f} "
                              f"ece {r['model']['ece']:.3f}" for name, r in res.items())
            print(f"{arm} n={n} seed {seed} ({secs:.0f}s)  {line}", flush=True)
    first = next(iter(results["runs"].values()))
    print("truth  " + " | ".join(f"{name}: acc {r['truth']['accuracy']:.3f} conf {r['truth']['confidence']:.3f}"
                                 for name, r in first.items()))
    results["runs"] = dict(sorted(results["runs"].items()))
    path = "results_smoke.json" if smoke else "results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=1)
    print("wrote", path)


def example():
    """One session and its exact probabilities, for the illustration in the post."""
    events = ["login_fail", "login_ok", "http_200", "login_fail", "dns_query"]
    options = ["brute_force", "credential_stuffing", "phishing", "benign"]
    ev = np.zeros((1, L_MAX), dtype=int)
    ev[0, :len(events)] = [EVENTS.index(e) for e in events]
    opts = np.array([[CLASSES.index(c) for c in options]])
    p = true_posterior(opts, ev, np.array([len(events)]))[0]
    with open("example.json", "w") as f:
        json.dump({"events": events, "options": options, "posterior": [round(float(x), 4) for x in p]}, f, indent=1)
    print("wrote example.json")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    example() if mode == "example" else main(mode)
