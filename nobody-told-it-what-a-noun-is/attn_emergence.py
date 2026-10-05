"""Nobody told it what a noun is.

A one-head attention model is trained to predict the next word of four novels.
Nothing in the training mentions grammar. Afterwards, the embeddings of nouns,
verbs, adjectives and adverbs sit in different regions, and a linear probe can
read a word's part of speech from its vector.

    python attn_emergence.py 4000             # the real run     -> run_real.npz
    python attn_emergence.py 4000 --shuffle   # the control      -> run_shuffled.npz

The control uses the same text with the words inside each sentence shuffled.
Every word keeps its frequency and its sentence-mates. Only the order is gone.

Needs PyTorch, NumPy and NLTK. Runs on CPU in about five minutes.
"""
import collections
import math
import random
import sys
import time

import nltk
import numpy as np
import torch
import torch.nn as nn

FILES = ["austen-emma.txt", "austen-persuasion.txt", "austen-sense.txt", "carroll-alice.txt"]
CLASSES = ["NOUN", "VERB", "ADJ", "ADV"]
MIN_COUNT = 8          # a word seen fewer times than this becomes <unk>
CONTENT_MIN = 25       # the measurements use content words seen at least this often
DIM, CONTEXT, BATCH, LR = 64, 96, 32, 3e-3
NEIGHBOURS = 10
SNAPSHOT_EVERY = 100


# ----------------------------------------------------------------------------- the text
def load(shuffle, seed=0):
    for package in ["gutenberg", "punkt_tab", "averaged_perceptron_tagger_eng", "universal_tagset"]:
        nltk.download(package, quiet=True)
    from nltk.corpus import gutenberg

    sentences = [s for f in FILES for s in gutenberg.sents(f)]
    # The tagger sees the original sentences, with punctuation, in both conditions.
    # The model never sees a tag.
    tagged = nltk.pos_tag_sents(sentences, tagset="universal")

    count, tags, words = collections.Counter(), collections.defaultdict(collections.Counter), []
    for sentence in tagged:
        kept = [(w.lower(), t) for w, t in sentence if w.isalpha()]
        for w, t in kept:
            count[w] += 1
            tags[w][t] += 1
        words.append([w for w, _ in kept])

    if shuffle:
        rng = random.Random(seed)
        for sentence in words:
            rng.shuffle(sentence)

    vocab = ["<unk>"] + sorted(w for w, c in count.items() if c >= MIN_COUNT)
    index = {w: i for i, w in enumerate(vocab)}
    ids = torch.tensor([index.get(w, 0) for sentence in words for w in sentence])

    content = []                                   # (word, id, class) for the words we measure
    for w in vocab[1:]:
        majority = tags[w].most_common(1)[0][0]
        if count[w] >= CONTENT_MIN and majority in CLASSES:
            content.append((w, index[w], CLASSES.index(majority)))
    return ids, vocab, content


# ----------------------------------------------------------------------------- the model
class OneHead(nn.Module):
    """Embeddings, one causal self-attention head with a residual connection, an output layer."""

    def __init__(self, vocab_size):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, DIM)
        self.pos = nn.Embedding(CONTEXT, DIM)
        self.q = nn.Linear(DIM, DIM, bias=False)
        self.k = nn.Linear(DIM, DIM, bias=False)
        self.v = nn.Linear(DIM, DIM, bias=False)
        self.out = nn.Linear(DIM, vocab_size)
        self.register_buffer("causal", torch.tril(torch.ones(CONTEXT, CONTEXT)).bool())

    def forward(self, x):
        h = self.emb(x) + self.pos(torch.arange(x.shape[1]))
        scores = self.q(h) @ self.k(h).transpose(1, 2) / math.sqrt(DIM)
        weights = scores.masked_fill(~self.causal, float("-inf")).softmax(-1)
        return self.out(h + weights @ self.v(h))


# ----------------------------------------------------------------------------- the two measures
def neighbour_purity(vectors, labels):
    """For each word: the share of its 10 nearest neighbours that have the same class."""
    unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    sim = unit @ unit.T
    np.fill_diagonal(sim, -np.inf)
    nearest = np.argsort(-sim, axis=1)[:, :NEIGHBOURS]
    same = (labels[nearest] == labels[:, None]).mean(1)
    return float(same.mean()), [float(same[labels == c].mean()) for c in range(len(CLASSES))]


def probe_accuracy(vectors, labels, folds=5, seed=0):
    """A linear classifier reads the class from the vector. Accuracy on held-out words."""
    x = torch.tensor((vectors - vectors.mean(0)) / (vectors.std(0) + 1e-8), dtype=torch.float32)
    y = torch.tensor(labels)
    order = torch.randperm(len(y), generator=torch.Generator().manual_seed(seed))
    correct = 0
    for f in range(folds):
        test = order[f::folds]
        train = torch.tensor(sorted(set(order.tolist()) - set(test.tolist())))
        clf = nn.Linear(x.shape[1], len(CLASSES))
        opt = torch.optim.Adam(clf.parameters(), lr=0.05, weight_decay=1e-3)
        for _ in range(300):
            loss = nn.functional.cross_entropy(clf(x[train]), y[train])
            opt.zero_grad()
            loss.backward()
            opt.step()
        correct += int((clf(x[test]).argmax(1) == y[test]).sum())
    return correct / len(y)


# ----------------------------------------------------------------------------- the run
def run(steps, shuffle, seed=0, save=True):
    torch.manual_seed(seed)
    ids, vocab, content = load(shuffle, seed)
    content_ids = np.array([i for _, i, _ in content])
    labels = np.array([c for _, _, c in content])
    share = np.bincount(labels, minlength=len(CLASSES)) / len(labels)

    model = OneHead(len(vocab))
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    print(f"{'shuffled' if shuffle else 'real'} text: {len(ids):,} words, vocabulary {len(vocab):,}, "
          f"{len(content):,} content words, {sum(p.numel() for p in model.parameters()):,} parameters")
    print("chance: neighbours " + f"{float((share ** 2).sum()):.0%}, probe (always guess noun) {share.max():.0%}; "
          + "classes " + " / ".join(f"{c} {s:.0%}" for c, s in zip(CLASSES, share)))

    log = {"step": [], "loss": [], "purity": [], "purity_by_class": [], "probe": [], "snapshots": []}

    def measure(step, loss):
        vectors = model.emb.weight.detach().numpy()[content_ids].copy()
        purity, by_class = neighbour_purity(vectors, labels)
        probe = probe_accuracy(vectors, labels)
        for key, value in zip(("step", "loss", "purity", "purity_by_class", "probe", "snapshots"),
                              (step, loss, purity, by_class, probe, vectors)):
            log[key].append(value)
        if step % 500 == 0 or step == steps:
            print(f"step {step:5d}  loss {loss:5.2f}  neighbours {purity:.0%} "
                  f"({' / '.join(f'{p:.0%}' for p in by_class)})  probe {probe:.0%}", flush=True)

    start, recent = time.time(), []
    for step in range(steps + 1):
        at = torch.randint(0, len(ids) - CONTEXT - 1, (BATCH,))
        x = torch.stack([ids[a:a + CONTEXT] for a in at])
        y = torch.stack([ids[a + 1:a + CONTEXT + 1] for a in at])
        loss = nn.functional.cross_entropy(model(x).flatten(0, 1), y.flatten())
        recent = (recent + [loss.item()])[-50:]
        if step % SNAPSHOT_EVERY == 0:
            measure(step, loss.item() if step == 0 else sum(recent) / len(recent))
        if step < steps:
            opt.zero_grad()
            loss.backward()
            opt.step()
    print(f"{time.time() - start:.0f} s")
    if not save:
        return log

    # Keep the first and the last embeddings in full. For the steps between, keep only their
    # position on the two main axes of the FINAL embeddings, so that the picture shows real motion.
    snapshots = np.array(log["snapshots"])
    centre = snapshots[-1].mean(0)
    axes = np.linalg.svd(snapshots[-1] - centre, full_matrices=False)[2][:2]
    path = "run_shuffled.npz" if shuffle else "run_real.npz"
    np.savez_compressed(path, words=np.array([w for w, _, _ in content]), labels=labels, share=share,
                        step=np.array(log["step"]), loss=np.array(log["loss"]), purity=np.array(log["purity"]),
                        purity_by_class=np.array(log["purity_by_class"]), probe=np.array(log["probe"]),
                        initial=snapshots[0], final=snapshots[-1],
                        path2d=((snapshots - centre) @ axes.T).astype(np.float32))
    print("wrote", path)
    return log


if __name__ == "__main__":
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    run(int(numbers[0]) if numbers else 4000, shuffle="--shuffle" in sys.argv)
