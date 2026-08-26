# -*- coding: utf-8 -*-
"""Publication figures for essay_draft.md — reader-facing labels only
(no Version A/B, no B1..B6 codes, no internal sleeve variable names).
Lab versions in the notebooks stay unchanged. Rerun after data refresh."""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phase2_version_a import run_phase2, UNIVERSE_A

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
S = "#fcfcfb"


def style_axes(ax):
    ax.set_facecolor(S)
    ax.grid(axis="y", color="#e6e5e1", lw=0.8)
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#c9c8c4")
    ax.tick_params(colors="#52514e", length=0)


def log2_axis(ax, curves):
    vals = [np.log2(np.asarray(c, dtype=float)) for c in curves]
    lo = min(0, min(v.min() for v in vals))
    hi = max(v.max() for v in vals)
    ticks = range(int(np.floor(lo)), int(np.ceil(hi)) + 1)
    ax.set_yticks(list(ticks))
    ax.set_yticklabels(["%gx" % (2.0 ** k) for k in ticks])


def direct_labels(ax, items, min_gap):
    last = sorted((np.log2(c.iloc[-1]), name, c, col) for name, c, col in items)
    prev = None
    for y, name, c, col in last:
        if prev is not None and y - prev < min_gap:
            y = prev + min_gap
        prev = y
        ax.annotate("  %s  %.1fx" % (name, c.iloc[-1]),
                    xy=(c.index[-1], y), xytext=(6, 0),
                    textcoords="offset points", va="center", color=col,
                    fontsize=9, fontweight="bold")


res = run_phase2()

# ---- Figure 1: faiz mi dolar mi ----
fig, ax = plt.subplots(figsize=(10.5, 5.2), facecolor=S)
pairs = [("B1_deposits", "#eb6834", "Roll TL deposits"),
         ("B2_SHY_TL", "#e87ba4", "Hold dollars")]
for key, col, lbl in pairs:
    c = res["curves"][key]["TL_real"]
    ax.plot(c.index, np.log2(c.values), color=col, lw=2.0, label=lbl)
direct_labels(ax, [(lbl.split(" (")[0], res["curves"][k]["TL_real"], col)
                   for k, col, lbl in pairs], 0.14)
ax.axhline(0, color="#c9c8c4", lw=1.0)
ax.annotate("2021–23: deposits lose about half\ntheir purchasing power",
            xy=(pd.Timestamp("2022-10-01"), -0.85), color="#eb6834",
            fontsize=8.5, ha="center")
ax.annotate("2023→: dollars lose\n~10%/yr real",
            xy=(pd.Timestamp("2025-05-01"), 0.95), color="#e87ba4",
            fontsize=8.5, ha="center")
log2_axis(ax, [res["curves"][k]["TL_real"].values for k, _, _ in pairs])
style_axes(ax)
ax.set_title("Interest or dollars? Both answers, in real purchasing power "
             "(Jan 2013 – Jul 2026; each gridline = a doubling)",
             color="#0b0b0b", fontsize=11, loc="left", pad=12)
ax.legend(loc="lower left", frameon=False, fontsize=9, labelcolor="#0b0b0b")
ax.margins(x=0.14)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS, "fig1_faiz_mi_dolar_mi.png"), dpi=150,
            bbox_inches="tight", facecolor=S)
plt.close(fig)

# ---- Figure 2: the menu vs the strategy ----
SERIES = [
    ("VA_net10",    "#2a78d6", 2.4, "-",  "The strategy (all 12 assets)", "Strategy"),
    ("VB_net10",    "#1baf7a", 1.5, "-",  "Dollar-ETFs only",         "Dollar-ETFs only"),
    ("B1_deposits", "#eb6834", 1.4, "-",  "Roll TL deposits",         "TL deposits"),
    ("B2_SHY_TL",   "#e87ba4", 1.4, "-",  "Hold dollars",             "Hold dollars"),
    ("B3_GLD_TL",   "#008300", 1.4, "-",  "Gold",                     "Gold"),
    ("B4_BIST",     "#eda100", 1.4, "-",  "BIST-100 (total return)",  "BIST-100"),
    ("B6_50_50",    "#6b6a67", 1.3, "--", "50/50 deposits/BIST",      "50/50"),
]
fig, ax = plt.subplots(figsize=(11.5, 6.2), facecolor=S)
for key, col, lw, ls, lbl, _ in SERIES:
    c = res["curves"][key]["TL_real"]
    ax.plot(c.index, np.log2(c.values), color=col, lw=lw, ls=ls, label=lbl)
direct_labels(ax, [(short, res["curves"][k]["TL_real"], col)
                   for k, col, _, _, _, short in SERIES], 0.18)
log2_axis(ax, [res["curves"][k]["TL_real"].values for k, *_ in SERIES])
style_axes(ax)
ax.set_title("A Turkish saver's choices in real purchasing power, net of costs "
             "(Jan 2013 – Jul 2026; each gridline = a doubling)",
             color="#0b0b0b", fontsize=11, loc="left", pad=12)
ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor="#0b0b0b")
ax.margins(x=0.15)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS, "fig2_all_choices_compared.png"), dpi=150,
            bbox_inches="tight", facecolor=S)
plt.close(fig)

# ---- Figure 3: holdings timeline ----
READER_NAME = {"DEPOSIT_TL": "TL deposit", "BIST_TL": "BIST-100",
               "SHY": "T-bills (SHY)", "IEF": "Treasuries (IEF)",
               "GLD": "Gold (GLD)", "XLE": "Energy (XLE)",
               "SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq (QQQ)",
               "EFA": "Developed (EFA)", "EEM": "Emerging (EEM)",
               "MCHI": "China (MCHI)", "INDA": "India (INDA)"}
w = res["weights"][UNIVERSE_A]
fig, ax = plt.subplots(figsize=(11.5, 4.8), facecolor=S)
ax.set_facecolor(S)
mesh = ax.pcolormesh(w.index.append(w.index[-1:] + pd.Timedelta(weeks=1)),
                     np.arange(len(UNIVERSE_A) + 1), w.T.values,
                     cmap="Blues", vmin=0, vmax=2.0 / 3, shading="flat")
ax.set_yticks(np.arange(len(UNIVERSE_A)) + 0.5)
ax.set_yticklabels([READER_NAME[c] for c in UNIVERSE_A], fontsize=8.5,
                   color="#0b0b0b")
ax.tick_params(colors="#52514e", length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
cb = fig.colorbar(mesh, ax=ax, fraction=0.03, pad=0.01)
cb.set_label("share of portfolio", color="#52514e", fontsize=8.5)
cb.ax.tick_params(colors="#52514e", labelsize=8)
cb.outline.set_visible(False)
ax.set_title("What the strategy held, week by week (Jan 2013 – Aug 2026)",
             color="#0b0b0b", fontsize=10.5, loc="left", pad=8)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS, "fig3_holdings_timeline.png"), dpi=150,
            bbox_inches="tight", facecolor=S)
plt.close(fig)

print("figures written")
