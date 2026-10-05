# Confident and wrong

Post: [vlrmzz.github.io/writing/confident-and-wrong.html](https://vlrmzz.github.io/writing/confident-and-wrong.html)

A toy security world in which the true probability of every label is known. A small decision model is
trained in three ways. Its reported confidence is then compared with the truth, as trained and under
four changes: more options, a log format it cannot read, and traffic that is 90 % benign.

| File | What it is |
|---|---|
| `confident_and_wrong.ipynb` | Start here. The setup, a short run, and the charts from the full run. |
| `alert_triage.py` | The world, the model, the three training methods, and the measurements. |
| `make_figs.py` | The figures of the post, as SVG. Standard library only. |
| `results.json` | Every run of the full experiment. |
| `example.json` | The worked session shown in the post. |
| `data/` | Two result files copied unchanged from the [Laya](https://github.com/NandhaKishorM/laya) repository (Apache 2.0). `make_figs.py` uses them. |

## Run it from a terminal

```
python alert_triage.py smoke     # a quick check, under 1 minute
python alert_triage.py run       # the full experiment, about 45 minutes, writes results.json
python alert_triage.py example   # writes example.json
python make_figs.py              # the figures, into figures/
```
