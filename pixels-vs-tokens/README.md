# Is visual data really richer than text?

Post: [vlrmzz.github.io/writing/pixels-vs-tokens.html](https://vlrmzz.github.io/writing/pixels-vs-tokens.html)

A ball flies through a 32 × 32 world. Three models of the same size must predict where it goes. One
gets pictures, one gets the position as symbols, one gets the position as numbers. The picture is drawn
from the position and from nothing else, so the three inputs carry the same information.

| File | What it is |
|---|---|
| `pixels_vs_tokens.ipynb` | Start here. The setup, a short run, and the charts from the full run. |
| `pixels_vs_tokens.py` | The world, the three models, and the training. |
| `control_flat_pixels.py` | The control: the same pictures into a network with no convolution. |
| `viz.py` | The two figures of the post. |
| `results.json`, `results_control.json` | Every run of the full experiment and of the control. |

## Run it from a terminal

```
python pixels_vs_tokens.py smoke    # a quick check, 2 to 3 minutes
python pixels_vs_tokens.py run      # the full experiment, about 1 hour, writes results.json
python control_flat_pixels.py       # the control, writes results_control.json
python viz.py                       # the figures
```
