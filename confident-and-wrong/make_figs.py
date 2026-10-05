"""Figures for "Confident and wrong".

    python make_figs.py            # writes the SVGs to figures/
    python make_figs.py some/dir   # or to a folder you name

Standard library only. It reads:

    results.json, example.json     written by alert_triage.py (the experiment)
    data/*.json                    copied unchanged from the Laya repository
                                   (github.com/NandhaKishorM/laya, Apache 2.0, research/results/)

The diagrams and the two concept charts (scoring rules, temperature) are drawn from
definitions, not from data. The SVGs carry their own light and dark palette and follow
the reader's colour-scheme setting, like the rest of the site.
"""
import json
import math
import os
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "figures")
W = 640  # the post column is ~580px wide, so text set at 12-13px stays readable

# colour roles; the values live in STYLE so they can switch with the colour scheme
PAPER, PANEL, SOFT = "var(--paper)", "var(--panel)", "var(--soft)"
INK, MUTED = "var(--ink)", "var(--muted)"
GRID, AXIS, BORDER = "var(--grid)", "var(--axis)", "var(--border)"
ACCENT, ON_ACCENT = "var(--accent)", "var(--on-accent)"
S1, S2, S3, CONTEXT = "var(--s1)", "var(--s2)", "var(--s3)", "var(--context)"

STYLE = """
svg { --paper:#FBFAF7; --panel:#FFFFFF; --soft:#F2F1EC; --ink:#1A1C1A; --muted:#6B7069;
      --grid:#E4E2DA; --axis:#C9C6BB; --border:#D8D5CB; --accent:#1F5C46; --on-accent:#FFFFFF;
      --s1:#2E8B68; --s2:#C9622A; --s3:#3A6BC4; --context:#A3A89F; }
@media (prefers-color-scheme: dark) {
  svg { --paper:#131614; --panel:#181C19; --soft:#1B1F1C; --ink:#E9E8E2; --muted:#969C93;
        --grid:#272B27; --axis:#3D433D; --border:#343A35; --accent:#7FC8A3; --on-accent:#131614;
        --s1:#3FA27A; --s2:#D9703A; --s3:#5B8DEF; --context:#5F665F; }
}
text { font-family: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
.mono { font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
"""


def tw(s, size, weight=400, mono=False):
    """Rough text width, good enough to size chips and boxes."""
    if mono:
        return len(s) * size * 0.602
    return len(s) * size * (0.57 if weight >= 600 else 0.535)


class Svg:
    def __init__(self, h, title=None):
        self.h = h
        self.parts = []
        self.rect(0, 0, W, h, fill=PAPER)
        if title:
            self.text(16, 28, title, size=14, weight=600)

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill=PANEL, rx=0, stroke=None, sw=1):
        st = f"fill:{fill}" + (f";stroke:{stroke};stroke-width:{sw}" if stroke else "")
        r = f' rx="{rx}"' if rx else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"{r} style="{st}"/>')

    def line(self, x1, y1, x2, y2, stroke=GRID, sw=1, cap=None):
        st = f"stroke:{stroke};stroke-width:{sw}" + (f";stroke-linecap:{cap}" if cap else "")
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" style="{st}"/>')

    def text(self, x, y, s, size=12.5, fill=INK, weight=400, anchor="start", mono=False, rotate=None):
        cls = ' class="mono"' if mono else ""
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}"{cls} font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{tr} style="fill:{fill}">{escape(s)}</text>')

    def circle(self, x, y, r, fill=S1, ring=True):
        st = f"fill:{fill}" + (f";stroke:{PAPER};stroke-width:1.5" if ring else "")
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" style="{st}"/>')

    def path(self, d, stroke=S1, sw=2, extra=""):
        self.add(f'<path d="{d}" {extra} style="fill:none;stroke:{stroke};stroke-width:{sw};'
                 f'stroke-linejoin:round;stroke-linecap:round"/>')

    def arrow(self, x1, y1, x2, y2, stroke=MUTED, sw=1.4):
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - 7 * math.cos(ang), y2 - 7 * math.sin(ang)
        self.line(x1, y1, bx, by, stroke=stroke, sw=sw)
        pts = [(x2, y2), (bx + 3.6 * math.sin(ang), by - 3.6 * math.cos(ang)),
               (bx - 3.6 * math.sin(ang), by + 3.6 * math.cos(ang))]
        self.add('<polygon points="%s" style="fill:%s"/>' % (" ".join(f"{a:.1f},{b:.1f}" for a, b in pts), stroke))

    def box(self, x, y, w, h, label, sub=None, size=13, accent=False):
        self.rect(x, y, w, h, fill=PANEL, rx=7, stroke=BORDER)
        if accent:
            self.rect(x, y + 7, 3, h - 14, fill=ACCENT, rx=1.5)
        if sub:
            self.text(x + w / 2, y + h / 2 - 2, label, size=size, weight=600, anchor="middle")
            self.text(x + w / 2, y + h / 2 + 14, sub, size=12, fill=MUTED, anchor="middle")
        else:
            self.text(x + w / 2, y + h / 2 + 4.5, label, size=size, weight=600, anchor="middle")

    def chip(self, x, y, s, kind="plain", size=12):
        """A token chip. Returns its width."""
        mono = kind in ("special", "mask", "code")
        w = tw(s, size, mono=mono) + 14
        if kind == "mask":
            self.rect(x, y, w, 26, fill=ACCENT, rx=5)
            self.text(x + w / 2, y + 17.5, s, size=size, weight=500, anchor="middle", mono=True, fill=ON_ACCENT)
        elif kind == "special":
            self.rect(x, y, w, 26, fill=PAPER, rx=5, stroke=AXIS)
            self.text(x + w / 2, y + 17.5, s, size=size, anchor="middle", mono=True, fill=MUTED)
        else:
            self.rect(x, y, w, 26, fill=PANEL, rx=5, stroke=BORDER)
            self.text(x + w / 2, y + 17.5, s, size=size, anchor="middle", mono=(kind == "code"))
        return w

    def column(self, x, y0, w, h, fill=S1):
        """Column rising from the baseline y0, rounded at the data end only."""
        if h < 0.5:
            return
        r, top = min(3.5, h, w / 2), y0 - h
        d = (f"M{x:.1f},{y0:.1f} L{x:.1f},{top + r:.1f} Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} "
             f"L{x + w - r:.1f},{top:.1f} Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f} L{x + w:.1f},{y0:.1f} Z")
        self.add(f'<path d="{d}" style="fill:{fill}"/>')

    def hbar(self, x0, y, w, h, fill=S1):
        if w < 0.5:
            return
        r = min(3.5, w, h / 2)
        d = (f"M{x0:.1f},{y:.1f} L{x0 + w - r:.1f},{y:.1f} Q{x0 + w:.1f},{y:.1f} {x0 + w:.1f},{y + r:.1f} "
             f"L{x0 + w:.1f},{y + h - r:.1f} Q{x0 + w:.1f},{y + h:.1f} {x0 + w - r:.1f},{y + h:.1f} L{x0:.1f},{y + h:.1f} Z")
        self.add(f'<path d="{d}" style="fill:{fill}"/>')

    def save(self, name, desc):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {self.h}" width="{W * 2}" '
               f'height="{self.h * 2}" role="img" aria-label="{escape(desc)}">\n<title>{escape(desc)}</title>\n'
               f'<style>{STYLE}</style>\n' + "\n".join(self.parts) + "\n</svg>\n")
        with open(os.path.join(OUT, name), "w") as f:
            f.write(svg)
        print(f"{name}  {W * 2}x{self.h * 2}")


# ---------------------------------------------------------------------------
def fig_llm_vs_decision():
    s = Svg(346, "Two ways to get a decision out of a model")
    # --- generative LLM
    y = 46
    s.rect(16, y, 608, 138, fill=PAPER, rx=8, stroke=BORDER)
    s.text(30, y + 24, "Generative LLM", size=13, weight=600)
    s.text(30 + tw("Generative LLM", 13, 600) + 10, y + 24, "the network runs once for every piece of output", size=12, fill=MUTED)
    by = y + 44
    s.box(30, by, 112, 40, "session + prompt", size=12.5)
    s.arrow(142, by + 20, 162, by + 20)
    s.box(164, by, 60, 40, "LLM", size=13, accent=True)
    s.arrow(224, by + 20, 244, by + 20)
    x = 246
    for t in ['{"type":', '"brute', '_force"', '}']:
        x += s.chip(x, by + 7, t, "code") + 4
    chips_end = x - 4
    s.arrow(chips_end, by + 20, chips_end + 20, by + 20)
    s.box(chips_end + 22, by, 610 - (chips_end + 22), 40, "parse the text", size=12.5)
    lx1, lx2, ly = 330, 194, by + 62
    s.path(f"M{lx1},{by + 33} L{lx1},{ly} L{lx2},{ly} L{lx2},{by + 48}", stroke=S2, sw=1.4)
    s.arrow(lx2, by + 50, lx2, by + 41, stroke=S2)
    s.text(lx1 + 10, ly + 4, "each new piece is fed back in", size=12, fill=MUTED)
    # --- decision model
    y2 = y + 152
    s.rect(16, y2, 608, 132, fill=PAPER, rx=8, stroke=BORDER)
    s.text(30, y2 + 24, "Decision model", size=13, weight=600)
    s.text(30 + tw("Decision model", 13, 600) + 10, y2 + 24, "the network runs once; nothing is written", size=12, fill=MUTED)
    by2 = y2 + 60
    s.box(30, by2, 112, 40, "session + options", size=12.5)
    s.arrow(142, by2 + 20, 162, by2 + 20)
    s.box(164, by2, 116, 40, "the model", size=13, accent=True)
    s.arrow(280, by2 + 20, 300, by2 + 20)
    bx = 312
    s.text(bx, y2 + 48, "one probability per option", size=12, fill=MUTED)
    for i, (lab, p) in enumerate([("brute_force", 0.63), ("credential_stuffing", 0.34), ("benign", 0.02)]):
        yy = y2 + 58 + i * 22
        s.text(bx, yy + 11, lab, size=12.5)
        s.rect(bx + 134, yy + 1, 124, 12, fill=GRID, rx=3)
        s.hbar(bx + 134, yy + 1, 124 * p, 12)
        s.text(bx + 266, yy + 11.5, f"{p:.2f}", size=12.5)
    s.save("confident-and-wrong-llm-vs-decision.svg",
           "A generative LLM writes its answer one piece at a time, feeding each piece back in, and the text then has "
           "to be parsed. A decision model takes the session and the options and returns one probability per option "
           "in a single run of the network.")


# ---------------------------------------------------------------------------
def fig_architecture():
    s = Svg(604, "Inside a decision model")

    def step(n, y, l1, l2=None, x=16):
        s.text(x, y, n, size=12.5, weight=600, fill=ACCENT)
        s.text(x + 16, y, l1, size=12.5, weight=600)
        if l2:
            s.text(x + 16, y + 16, l2, size=12, fill=MUTED)

    # 1. input sequence
    step("1", 58, "The input: the question, one [MASK] per option, then the session to judge")
    rows = [[("[CLS]", "special"), ("choice question: Which attack is this session?", "plain"), ("[SEP]", "special")],
            [("[MASK]", "mask"), ("brute_force", "plain"), ("[MASK]", "mask"), ("port_scan", "plain"),
             ("[MASK]", "mask"), ("benign", "plain"), ("[SEP]", "special")],
            [("login_fail login_fail login_ok mfa_prompt login_fail", "code"), ("[SEP]", "special")]]
    for i, row in enumerate(rows):
        x = 32
        for t, kind in row:
            x += s.chip(x, 70 + i * 32, t, kind) + 5
    # 2. encoder
    ey = 184
    s.arrow(W / 2, 166, W / 2, ey - 3)
    s.rect(16, ey, 608, 56, fill=PANEL, rx=7, stroke=BORDER)
    s.rect(16, ey + 7, 3, 42, fill=ACCENT, rx=1.5)
    step("2", ey + 23, "Encoder: ModernBERT-large", x=32)
    s.text(48, ey + 41, "28 layers. Every word can look at every other word, so options and session are read together.", size=12, fill=MUTED)
    s.text(610, ey + 23, "395M parameters", size=12, fill=MUTED, anchor="end")
    # 3. head
    hy = 262
    s.arrow(W / 2, ey + 56, W / 2, hy - 3)
    s.rect(16, hy, 608, 56, fill=PANEL, rx=7, stroke=BORDER)
    s.rect(16, hy + 7, 3, 42, fill=ACCENT, rx=1.5)
    step("3", hy + 23, "Decision head: two more layers", x=32)
    s.text(48, hy + 41, "Told which kind of question this is: choice, score or yes/no.", size=12, fill=MUTED)
    s.text(610, hy + 23, "26.5M with the scorer", size=12, fill=MUTED, anchor="end")
    # 4-7. lanes
    lanes = [("brute_force", 3.1), ("port_scan", -0.7), ("benign", 0.0)]
    lx, half = [286, 424, 562], 54
    gy = 350
    T = 1.76
    ex = [math.exp(z / T) for _, z in lanes]
    probs = [e / sum(ex) for e in ex]
    step("4", gy + 16, "Keep the model's output", "at the three [MASK] positions")
    step("5", gy + 66, "Score each one", "one raw score z per option")
    for (lab, z), x in zip(lanes, lx):
        s.arrow(x, hy + 56, x, gy - 3)
        s.rect(x - half, gy, half * 2, 28, fill=ACCENT, rx=5)
        s.text(x, gy + 18.5, lab, size=11.5, weight=500, anchor="middle", mono=True, fill=ON_ACCENT)
        s.arrow(x, gy + 28, x, gy + 47)
        s.rect(x - half, gy + 50, half * 2, 28, fill=PANEL, rx=5, stroke=BORDER)
        s.text(x, gy + 68.5, "scorer", size=12.5, anchor="middle")
        s.arrow(x, gy + 78, x, gy + 97)
        s.text(x, gy + 113, f"z = {z:+.1f}", size=12.5, anchor="middle", mono=True)
        s.line(x, gy + 120, x, gy + 134, stroke=MUTED, sw=1.4)
    sy = gy + 134
    s.rect(lx[0] - half, sy, lx[2] + half - (lx[0] - half), 40, fill=PANEL, rx=7, stroke=BORDER)
    s.rect(lx[0] - half, sy + 7, 3, 26, fill=S2, rx=1.5)
    s.text(lx[0] - half + 16, sy + 25, "p = softmax(z / T)", size=13, weight=500, mono=True)
    s.text(lx[0] - half + 176, sy + 25, "T is the temperature", size=12, fill=MUTED)
    step("6", sy + 17, "Turn scores into", "probabilities that add up to 1")
    oy = sy + 40
    step("7", oy + 36, "Read off the answer", "largest probability wins")
    for (lab, _), x, p in zip(lanes, lx, probs):
        s.arrow(x, oy, x, oy + 19)
        s.rect(x - half, oy + 23, half * 2, 9, fill=GRID, rx=3)
        s.hbar(x - half, oy + 23, half * 2 * p, 9)
        s.text(x, oy + 50, f"{lab} {p:.2f}", size=12.5, anchor="middle", weight=600 if p == max(probs) else 400)
    s.save("confident-and-wrong-architecture.svg",
           "The input sequence holds the question, one MASK token per option, and the session. It passes through a "
           "ModernBERT-large encoder and a two-layer decision head. The output at each MASK position is scored "
           "into one raw score per option, and a softmax with temperature T turns the scores into probabilities.")


# ---------------------------------------------------------------------------
def fig_pipeline():
    s = Svg(470, "Where a decision model sits in alert triage")
    y = 46
    s.box(98, y, 168, 44, "Alert", "a session of log events")
    s.arrow(266, y + 22, 296, y + 22)
    s.box(298, y, 244, 44, "Format check", "can the model read this log source?")
    by = y + 68
    s.arrow(W / 2, y + 44, W / 2, by - 3)
    s.rect(16, by, 608, 124, fill=PAPER, rx=8, stroke=BORDER)
    s.rect(16, by + 8, 3, 108, fill=ACCENT, rx=1.5)
    s.text(32, by + 24, "Decision model", size=13, weight=600)
    s.text(32 + tw("Decision model", 13, 600) + 10, by + 24, "all questions answered in one forward pass", size=12, fill=MUTED)
    cards = [("Attack type", "choice", "Which kind of attack is it?"),
             ("Severity", "score", "How severe, 0 to 3?"),
             ("Exfiltration", "yes/no", "Is data leaving?")]
    cw = 186
    for i, (name, typ, q) in enumerate(cards):
        cx = 32 + i * (cw + 9)
        s.rect(cx, by + 40, cw, 68, fill=PANEL, rx=6, stroke=BORDER)
        s.text(cx + 12, by + 62, name, size=13, weight=600)
        chw = tw(typ, 11.5, mono=True) + 12
        s.rect(cx + cw - 12 - chw, by + 49, chw, 19, fill=PAPER, rx=4, stroke=AXIS)
        s.text(cx + cw - 12 - chw / 2, by + 62.5, typ, size=11.5, fill=MUTED, anchor="middle", mono=True)
        s.text(cx + 12, by + 90, q, size=12, fill=MUTED)
    gy = by + 148
    s.arrow(W / 2, by + 124, W / 2, gy - 3)
    s.rect(210, gy, 220, 44, fill=PANEL, rx=7, stroke=BORDER)
    s.rect(210, gy + 7, 3, 30, fill=S2, rx=1.5)
    s.text(W / 2, gy + 20, "Confidence gate", size=13, weight=600, anchor="middle")
    s.text(W / 2, gy + 36, "is it above the threshold?", size=12, fill=MUTED, anchor="middle")
    oy = gy + 90
    outs = [("Close as benign", "no analyst time spent"), ("Contain automatically", "block, isolate, reset"),
            ("Escalate", "to an analyst")]
    ow = 190
    bus = gy + 62
    s.line(W / 2, gy + 44, W / 2, bus, stroke=MUTED, sw=1.4)
    centres = [16 + ow / 2 + i * (ow + 19) for i in range(3)]
    s.line(centres[0], bus, centres[2], bus, stroke=MUTED, sw=1.4)
    for (lab, sub), cx in zip(outs, centres):
        s.arrow(cx, bus, cx, oy - 3)
        s.box(cx - ow / 2, oy, ow, 44, lab, sub)
    s.text(centres[0] + 8, bus + 17, "confident", size=12, fill=MUTED)
    s.text(centres[1] + 8, bus + 17, "confident", size=12, fill=MUTED)
    s.text(centres[2] + 8, bus + 17, "unsure", size=12, fill=MUTED)
    ly = oy + 62
    s.rect(16, ly, 608, 34, fill=SOFT, rx=7)
    s.text(W / 2, ly + 21.5, "Log each decision with its probabilities, compare with outcomes, refit the threshold.",
           size=12, fill=MUTED, anchor="middle")
    s.save("confident-and-wrong-pipeline.svg",
           "An alert passes a format check, then a decision model answers an attack-type question, a severity question "
           "and an exfiltration question in one forward pass. A confidence gate sends the result to one of three "
           "outcomes: close as benign, contain automatically, or escalate to an analyst.")


# ---------------------------------------------------------------------------
PANELS = dict(pw=164, gap=38, left=50)


def fig_scoring_rules():
    p = 0.7
    s = Svg(318, "Which reward makes honesty the best policy?")
    pw, gap, left = PANELS["pw"], PANELS["gap"], PANELS["left"]
    top, ph = 94, 160

    def acc(q):
        return p * q + (1 - p) * (1 - q)

    def log(q):
        return p * math.log(q) + (1 - p) * math.log(1 - q)

    def sph(q):
        return (p * q + (1 - p) * (1 - q)) / math.sqrt(q * q + (1 - q) * (1 - q))

    panels = [("One point if right", "best report: 100%", acc, (0.25, 0.80), 1.0),
              ("Log score", "best report: 70%", log, (-2.0, -0.5), p),
              ("Spherical score", "best report: 70%", sph, (0.25, 0.80), p)]
    for i, (name, verdict, fn, (lo, hi), best) in enumerate(panels):
        x0 = left + i * (pw + gap)
        s.text(x0, top - 30, name, size=13, weight=600)
        s.text(x0, top - 13, verdict, size=12, fill=MUTED)
        for g in range(5):
            yy = top + ph * g / 4
            s.line(x0, yy, x0 + pw, yy, stroke=GRID if g < 4 else AXIS)
        for t in (0, 1.0):
            s.text(x0 + pw * t, top + ph + 17, f"{t:.0%}", size=12, fill=MUTED, anchor="middle")
        xt = x0 + pw * p
        yt = top if best == 1.0 else top + ph * (1 - (fn(p) - lo) / (hi - lo))
        s.line(xt, yt, xt, top + ph, stroke=AXIS)
        s.text(xt, top + ph + 17, "70%", size=12, anchor="middle", weight=600)
        qs = [k / 200 for k in range(0 if fn is acc else 1, 201 if fn is acc else 200)]
        pts = [(x0 + pw * q, top + ph * (1 - (min(hi, fn(q)) - lo) / (hi - lo))) for q in qs]
        s.add(f'<clipPath id="clip{i}"><rect x="{x0}" y="{top - 3}" width="{pw + 4}" height="{ph + 3}"/></clipPath>')
        s.path("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts), extra=f'clip-path="url(#clip{i})"')
        bx, by = x0 + pw * best, top + ph * (1 - (fn(best) - lo) / (hi - lo))
        s.circle(bx, by, 4.5, fill=S2)
        if best == 1.0:
            s.text(bx - 9, by - 6, "maximum", size=12, anchor="end")
        else:
            s.text(bx, by - 9, "maximum", size=12, anchor="middle")
    s.text(left + pw / 2, top + ph + 38, "reported probability", size=12, fill=MUTED, anchor="middle")
    s.text(left - 8, top + 4, "more", size=12, fill=MUTED, anchor="end")
    s.text(left - 8, top + ph + 1, "less", size=12, fill=MUTED, anchor="end")
    s.save("confident-and-wrong-scoring-rules.svg",
           "Expected reward against reported probability when the event is truly 70 percent likely. One point for a right "
           "answer peaks at a report of 100 percent. The log score and the spherical score both peak at 70 percent.")


# ---------------------------------------------------------------------------
def fig_languages():
    d = json.load(open(os.path.join(DATA, "cpu_51_language_sweep_refreshed.json")))
    s = Svg(486, "Confidence stays high while accuracy collapses")
    left, top, size = 62, 50, 380
    for t in range(0, 11, 2):
        v = t / 10
        x, y = left + size * v, top + size * (1 - v)
        s.line(left, y, left + size, y, stroke=GRID if t else AXIS)
        s.line(x, top, x, top + size, stroke=GRID if t else AXIS)
        s.text(left - 9, y + 4, f"{v:.1f}", size=12, fill=MUTED, anchor="end")
        s.text(x, top + size + 18, f"{v:.1f}", size=12, fill=MUTED, anchor="middle")
    s.text(left + size / 2, top + size + 40, "mean confidence", size=12, fill=MUTED, anchor="middle")
    s.text(22, top + size / 2, "accuracy", size=12, fill=MUTED, anchor="middle", rotate=-90)
    s.line(left, top + size, left + size, top, stroke=MUTED, sw=1.2)
    s.text(left + size * 0.33, top + size * 0.67 - 8, "perfectly calibrated", size=12, fill=MUTED,
           anchor="middle", rotate=-45)
    series = [("multilingual", S2, "laya-multilingual"), ("english", S1, "laya (English)")]
    pos = {}
    for key, col, _ in series:
        for lang, row in d["by_model"][key]["per_language"].items():
            r = row["refreshed_clamped"]
            x, y = left + size * r["mean_confidence"], top + size * (1 - r["accuracy"])
            pos[(key, lang)] = (x, y)
            s.circle(x, y, 4, fill=col)
    x, y = pos[("english", "en")]
    s.text(x + 9, y + 4, "English", size=12.5)
    x, y = pos[("english", "km")]
    s.line(x - 5, y - 4, x - 34, y - 20, stroke=MUTED)
    s.text(x - 38, y - 31, "Khmer: 0% right,", size=12.5, anchor="end")
    s.text(x - 38, y - 16, "71% confident", size=12.5, anchor="end")
    lx = left + size + 54
    s.text(lx, top + 12, "checkpoint", size=12, fill=MUTED)
    for i, (_, col, lab) in enumerate(reversed(series)):
        s.circle(lx + 5, top + 32 + i * 21, 4.5, fill=col, ring=False)
        s.text(lx + 17, top + 36 + i * 21, lab, size=12.5)
    s.text(lx, top + 96, "one dot per", size=12, fill=MUTED)
    s.text(lx, top + 112, "language, 51 each", size=12, fill=MUTED)
    s.save("confident-and-wrong-languages.svg",
           "Mean confidence against accuracy for 51 languages and two Laya checkpoints. Every point lies below the "
           "diagonal of perfect calibration. For Khmer the English checkpoint is 0 percent accurate at 71 percent "
           "mean confidence.")


# ---------------------------------------------------------------------------
def fig_temperature():
    s = Svg(296, "Temperature changes how sure the model sounds, not what it picks")
    z = [2.0, 1.2, 0.6, 0.0, -0.5]
    pw, gap, left = PANELS["pw"], PANELS["gap"], PANELS["left"]
    top, ph = 94, 150
    temps = [(0.5, "T = 0.5", "sounds more sure"), (1.0, "T = 1", "unchanged"), (2.0, "T = 2", "sounds less sure")]
    tops = []
    for i, (T, name, note) in enumerate(temps):
        x0 = left + i * (pw + gap)
        ex = [math.exp(v / T) for v in z]
        pr = [e / sum(ex) for e in ex]
        tops.append(pr[0])
        s.text(x0, top - 30, name, size=13, weight=600)
        s.text(x0, top - 13, note, size=12, fill=MUTED)
        for g in range(5):
            yy = top + ph * g / 4
            s.line(x0, yy, x0 + pw, yy, stroke=GRID if g < 4 else AXIS)
            if i == 0:
                s.text(x0 - 8, yy + 4, ["1.0", "", "0.5", "", "0"][g], size=12, fill=MUTED, anchor="end")
        band, bw = pw / 5, 20
        for j, pj in enumerate(pr):
            bx = x0 + band * j + (band - bw) / 2
            s.column(bx, top + ph, bw, ph * pj, fill=S1 if j == 0 else CONTEXT)
            s.text(bx + bw / 2, top + ph + 17, "ABCDE"[j], size=12, fill=MUTED, anchor="middle")
            if j == 0:
                s.text(bx + bw / 2, top + ph - ph * pj - 7, f"{pj:.2f}", size=12.5, anchor="middle", weight=600)
    s.text(left + pw / 2, top + ph + 38, "option", size=12, fill=MUTED, anchor="middle")
    s.text(18, top + ph / 2, "probability", size=12, fill=MUTED, anchor="middle", rotate=-90)
    s.save("confident-and-wrong-temperature.svg",
           "The same five logits through a softmax at temperatures 0.5, 1 and 2. The top option's probability is "
           "%.2f, %.2f and %.2f, and the order of the options never changes." % tuple(tops))


# ---------------------------------------------------------------------------
def beeswarm(xs, r, pad=0.8):
    """Deterministic dodge: vertical offsets so that circles do not overlap."""
    placed, out = [], [0.0] * len(xs)
    for i in sorted(range(len(xs)), key=lambda k: xs[k]):
        k = 0
        while True:
            for c in ([0.0] if k == 0 else [k * r * 0.5, -k * r * 0.5]):
                if all((xs[i] - px) ** 2 + (c - py) ** 2 >= (2 * r + pad) ** 2 for px, py in placed):
                    out[i] = c
                    placed.append((xs[i], c))
                    break
            else:
                k += 1
                continue
            break
    return out


def fig_refit():
    t = json.load(open(os.path.join(DATA, "t4_colab_benchmark.json")))
    left, right, top, R = 108, 616, 44, 3.2
    sx = lambda v: left + (right - left) * v / 0.9
    rows, y = [], top
    for key, name in [("laya", "laya (English)"), ("laya-multilingual", "laya-multilingual")]:
        cr = t["calibration_repair"][key]
        y += 24
        rows.append(("head", name, y))
        for lab, field, col, mean in [("as shipped", "ece_shipped", CONTEXT, cr["mean_ece_shipped"]),
                                      ("after refit", "ece_refit", S1, cr["mean_ece_refit"])]:
            xs = [sx(v[field]) for v in cr["per_suite"].values()]
            offs = beeswarm(xs, R)
            half = max(abs(o) for o in offs) + R
            cy = y + 28 + half
            rows.append(("strip", lab, cy, xs, offs, col, mean, half))
            y = cy + half + 4
        y += 8
    axis_y = y + 2
    s = Svg(int(axis_y + 50), "Calibration error on 49 benchmark suites, before and after a refit")
    for k in range(10):
        v = k / 10
        s.line(sx(v), top + 6, sx(v), axis_y, stroke=GRID if k else AXIS)
        s.text(sx(v), axis_y + 17, f"{v:.1f}", size=12, fill=MUTED, anchor="middle")
    s.text((left + right) / 2, axis_y + 38, "calibration error (lower is better)", size=12, fill=MUTED, anchor="middle")
    for r in rows:
        if r[0] == "head":
            s.rect(12, r[2] - 14, tw(r[1], 13, 600) + 12, 20, fill=PAPER)
            s.text(16, r[2], r[1], size=13, weight=600)
            continue
        _, lab, cy, xs, offs, col, mean, half = r
        s.text(left - 12, cy + 4, lab, size=12, fill=MUTED, anchor="end")
        for x, o in zip(xs, offs):
            s.circle(x, cy + o, R, fill=col)
        mx = sx(mean)
        s.line(mx, cy - half - 4, mx, cy + half + 4, stroke=INK, sw=2, cap="round")
        s.text(mx, cy - half - 10, f"mean {mean:.3f}", size=12.5, anchor="middle", weight=600)
    s.save("confident-and-wrong-refit.svg",
           "Expected calibration error on 49 benchmark suites for two Laya checkpoints. As shipped the means are "
           "0.466 and 0.314. After refitting the temperature on held-out data they are 0.081 and 0.106.")


# ---------------------------------------------------------------------------
# The experiment (results.json, example.json)
ARMS = [("ce", "cross-entropy", S3), ("rlcd", "Laya's method", S1), ("acc", "one point if right", S2)]
CONDITIONS = [("trained", "like training (4 options)"), ("k8", "8 options"), ("k12", "12 options"),
              ("unreadable", "unreadable log format"), ("benign90", "90% benign traffic")]


def load_results():
    r = json.load(open(os.path.join(HERE, "results.json")))
    sizes, seeds = r["config"]["train_sizes"], r["config"]["seeds"]

    def stat(arm, n, cond, key, which="model"):
        v = [r["runs"][f"{arm}/{n}/{sd}"][cond][which][key] for sd in seeds]
        m = sum(v) / len(v)
        return m, (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5

    return r, sizes, stat


def fig_world():
    ex = json.load(open(os.path.join(HERE, "example.json")))
    s = Svg(214, "One session, and the probabilities a perfect model would report")
    s.text(16, 58, "the session", size=12, fill=MUTED)
    x = 16
    for e in ex["events"]:
        x += s.chip(x, 66, e, "code") + 5
    s.text(16, 122, "the true probability of each option, computed from the model that generated the events", size=12, fill=MUTED)
    for i, (lab, p) in enumerate(zip(ex["options"], ex["posterior"])):
        yy = 134 + i * 20
        s.text(16, yy + 11, lab, size=12.5)
        s.rect(160, yy + 1, 400, 12, fill=GRID, rx=3)
        s.hbar(160, yy + 1, 400 * p, 12)
        s.text(570, yy + 11.5, f"{p:.2f}", size=12.5)
    s.save("confident-and-wrong-world.svg",
           "An example session of five log events and the exact probability of each of four offered classes: "
           + ", ".join(f"{l} {p:.2f}" for l, p in zip(ex["options"], ex["posterior"])) + ".")


def fig_sizes():
    r, sizes, stat = load_results()
    s = Svg(366, "Calibration error against the amount of training data (lower is better)")
    left, right, top, ph = 62, 446, 50, 250
    ymax = 0.25
    sx = lambda n: left + (right - left) * (math.log(n) - math.log(sizes[0])) / (math.log(sizes[-1]) - math.log(sizes[0]))
    sy = lambda v: top + ph * (1 - min(v, ymax) / ymax)
    for g in range(6):
        v = ymax * g / 5
        s.line(left, sy(v), right, sy(v), stroke=GRID if g else AXIS)
        s.text(left - 9, sy(v) + 4, f"{v:.2f}", size=12, fill=MUTED, anchor="end")
    for n in sizes:
        s.line(sx(n), top + ph, sx(n), top + ph + 4, stroke=AXIS)
        s.text(sx(n), top + ph + 19, f"{n:,}", size=12, fill=MUTED, anchor="middle")
    s.text((left + right) / 2, top + ph + 42, "training sessions", size=12, fill=MUTED, anchor="middle")
    s.text(18, top + ph / 2, "calibration error", size=12, fill=MUTED, anchor="middle", rotate=-90)
    floor = stat("ce", sizes[-1], "trained", "ece", "truth")[0]
    s.line(left, sy(floor), right, sy(floor), stroke=MUTED, sw=1.2)
    ends = []
    for arm, name, col in ARMS:
        pts = [(sx(n),) + stat(arm, n, "trained", "ece") for n in sizes]
        band = ([f"{x:.1f},{sy(m + sd):.1f}" for x, m, sd in pts] + [f"{x:.1f},{sy(max(0, m - sd)):.1f}" for x, m, sd in reversed(pts)])
        s.add(f'<polygon points="{" ".join(band)}" style="fill:{col};opacity:0.14"/>')
        s.path("M" + " L".join(f"{x:.1f},{sy(m):.1f}" for x, m, _ in pts), stroke=col)
        for x, m, _ in pts:
            s.circle(x, sy(m), 4, fill=col)
        ends.append((sy(pts[-1][1]), name, col, pts[-1][1]))
    # direct labels at the right end; where the lines converge, stack the labels upward
    ends.append((sy(floor), "best possible", MUTED, floor))
    ends.sort(key=lambda e: (-e[0], e[3]))
    pos = []
    for y, *_ in ends:
        pos.append(min(y, pos[-1] - 19) if pos else min(y, top + ph - 4))
    for (y, name, col, v), ly in zip(ends, pos):
        s.line(right + 7, y, right + 20, ly, stroke=col, sw=1.2)
        s.text(right + 25, ly + 4, name, size=12.5)
        s.text(W - 16, ly + 4, f"{v:.3f}", size=12, fill=MUTED, anchor="end")
    s.save("confident-and-wrong-sizes.svg",
           "Calibration error where the models were trained, against training-set size, for the three rewards. "
           + " ".join(f"{name}: " + ", ".join(f"{stat(arm, n, 'trained', 'ece')[0]:.3f}" for n in sizes) + "."
                      for arm, name, _ in ARMS))


def fig_conditions():
    r, sizes, stat = load_results()
    n = sizes[-1]
    s = Svg(352, f"What each model claims and what it delivers, trained on {n:,} sessions")
    labw, pw, gap, top, rowh = 152, 130, 34, 96, 40
    # legend
    s.circle(22, 49, 5, fill=INK, ring=False)
    s.text(33, 53, "accuracy", size=12.5)
    s.add(f'<circle cx="112" cy="49" r="4.2" style="fill:{PAPER};stroke:{INK};stroke-width:1.8"/>')
    s.text(123, 53, "mean confidence", size=12.5)
    s.line(250, 43, 250, 55, stroke=MUTED, sw=2, cap="round")
    s.text(259, 53, "best possible accuracy", size=12.5)
    for j, (arm, name, col) in enumerate(ARMS):
        x0 = labw + j * (pw + gap)
        s.rect(x0, top - 26, 9, 9, fill=col, rx=2)
        s.text(x0 + 14, top - 17, name, size=12.5, weight=600)
        for t in (0, 0.5, 1.0):
            x = x0 + pw * t
            s.line(x, top - 6, x, top + rowh * len(CONDITIONS) - 10, stroke=GRID if t else AXIS)
            s.text(x, top + rowh * len(CONDITIONS) + 8, f"{t:.0%}", size=12, fill=MUTED, anchor="middle")
        for i, (cond, lab) in enumerate(CONDITIONS):
            cy = top + 10 + i * rowh
            if j == 0:
                s.text(16, cy + 4, lab, size=12.5)
            acc, conf = stat(arm, n, cond, "accuracy")[0], stat(arm, n, cond, "confidence")[0]
            best = stat(arm, n, cond, "accuracy", "truth")[0]
            s.line(x0 + pw * best, cy - 9, x0 + pw * best, cy + 9, stroke=MUTED, sw=2, cap="round")
            s.line(x0 + pw * acc, cy, x0 + pw * conf, cy, stroke=col, sw=2)
            s.circle(x0 + pw * acc, cy, 5, fill=col)
            s.add(f'<circle cx="{x0 + pw * conf:.1f}" cy="{cy:.1f}" r="4.2" style="fill:{PAPER};stroke:{col};stroke-width:1.8"/>')
    desc = []
    for arm, name, _ in ARMS:
        desc.append(name + ": " + "; ".join(
            f"{lab} accuracy {stat(arm, n, c, 'accuracy')[0]:.2f}, confidence {stat(arm, n, c, 'confidence')[0]:.2f}"
            for c, lab in CONDITIONS) + ".")
    s.save("confident-and-wrong-conditions.svg", "Accuracy and mean confidence in five conditions. " + " ".join(desc))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_llm_vs_decision()
    fig_architecture()
    fig_pipeline()
    fig_scoring_rules()
    fig_world()
    fig_sizes()
    fig_conditions()
    fig_temperature()
    fig_languages()
    fig_refit()
