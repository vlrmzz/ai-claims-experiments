# AI claims, tested

Code for the experiments I write about at [vlrmzz.github.io/writing](https://vlrmzz.github.io/writing/).
Each post takes a popular claim about AI and tests it with a small experiment. Each folder here holds
one experiment: the code, the results of the full run, and a notebook.

| Folder | Question | Short run | Full run |
|---|---|---|---|
| [`pixels-vs-tokens`](pixels-vs-tokens/) | Does a model that sees a scene learn more than a model that reads the same facts? | 1 minute | 1 hour |
| [`confident-and-wrong`](confident-and-wrong/) | When can you trust the confidence a model reports? | 1 minute | 45 minutes |
| [`nobody-told-it-what-a-noun-is`](nobody-told-it-what-a-noun-is/) | Does a model learn word classes when nobody teaches them? | 1 minute | 10 minutes |

Times are for a laptop CPU. No GPU is necessary.

## Run a notebook

In your browser, with nothing to install:

- [Open `pixels_vs_tokens.ipynb` in Colab](https://colab.research.google.com/github/vlrmzz/ai-claims-experiments/blob/main/pixels-vs-tokens/pixels_vs_tokens.ipynb)
- [Open `confident_and_wrong.ipynb` in Colab](https://colab.research.google.com/github/vlrmzz/ai-claims-experiments/blob/main/confident-and-wrong/confident_and_wrong.ipynb)
- [Open `nobody_told_it.ipynb` in Colab](https://colab.research.google.com/github/vlrmzz/ai-claims-experiments/blob/main/nobody-told-it-what-a-noun-is/nobody_told_it.ipynb)

On your own machine (Python 3.10 or later):

```
git clone https://github.com/vlrmzz/ai-claims-experiments
cd ai-claims-experiments
pip install -r requirements.txt
jupyter notebook
```

## How each folder is organised

- **The scripts are the experiment.** They run from a terminal and write a results file.
- **The results file is the full run**, saved, so that you can examine the numbers without the wait.
- **The notebook calls the scripts.** It shows the setup, does a short run, then loads the saved results
  and draws the charts. The notebooks are saved with their output, so you can read them here on GitHub
  without running anything.

If a number in a post does not agree with what you get, tell me: vlrmzz.github.io has my contact details.
