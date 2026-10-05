# Nobody told it what a noun is

Post: [vlrmzz.github.io/writing/nobody-told-it-what-a-noun-is.html](https://vlrmzz.github.io/writing/nobody-told-it-what-a-noun-is.html)

A model with one attention head reads four novels. Its only task is to predict the next word. Afterwards,
nouns, verbs, adjectives and adverbs sit in different regions of its embedding space. In the control, the
words inside each sentence are shuffled, and no such structure appears.

| File | What it is |
|---|---|
| `nobody_told_it.ipynb` | Start here. The text, a short run, the figures from the full run and the control, and nearest neighbours. |
| `attn_emergence.py` | The text preparation, the model, the two measures and the training. |
| `viz_emergence.py` | The two figures. |
| `run_real.npz`, `run_shuffled.npz` | The full run and the control: the curves, and the embeddings of the measured words. |

## Run it from a terminal

```
python attn_emergence.py 4000             # the real run, about 5 minutes
python attn_emergence.py 4000 --shuffle   # the control, about 5 minutes
python viz_emergence.py                   # the figures and the table
```

The first run downloads the novels and the tagger through NLTK (about 40 MB).

## What this code gives

|  | real text | shuffled | chance |
|---|---|---|---|
| neighbours with the same class | 64 % | 36 % | 34 % |
| linear probe | 83 % | 47 % | 47 % |
| loss after 4,000 steps | 4.25 | 5.45 | |

This code is a rebuild. The scripts of my first run were not kept, so I wrote the experiment again from its
description. All numbers and figures in the post come from this code.
