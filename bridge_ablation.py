"""
Bridge ablation: Quantpedia baseline -> Version B, one deviation per step.

Diagnostic/expository ONLY (essay appendix). The Version B universe is locked
ex ante (SPEC 6 rule 3) — results here change NOTHING about the headline runs.

Ladder (config identical to phase0_validation unless stated: L in {10,25},
N=3, weekly W-WED, eval 2008-02-21 -> latest):
  0   QP 9-ETF baseline     SHY IEF UUP GLD USO SPY EFA QQQ EEM, 0% cash, no costs
  2   USO -> XLE
  3   drop UUP
  4   + MCHI/INDA at inception, EM gate (max one of MCHI/INDA held)
  5a  hatch 0% cash -> SHY
  5b  costs on, 10 bps one-way all ETF sleeves  == Phase 1 Version B config
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import (dual_momentum_weights, blend_weights, backtest,
                    equal_weight_returns, stats, to_weekly)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "prices_daily_usd.pkl")

ALL_TICKERS = ["SHY", "IEF", "UUP", "GLD", "USO", "XLE", "SPY", "QQQ",
               "EFA", "EEM", "MCHI", "INDA", "FXI"]
DATA_START = "2006-08-01"
EVAL_START = "2008-02-21"

QP9 = ["SHY", "IEF", "UUP", "GLD", "USO", "SPY", "EFA", "QQQ", "EEM"]
VB_CORE = ["SHY", "IEF", "GLD", "XLE", "SPY", "EFA", "QQQ", "EEM"]
VB_FULL = VB_CORE + ["MCHI", "INDA"]
EM_GATE = ["MCHI", "INDA"]
COSTS_10 = {t: 10.0 for t in VB_FULL}

STEPS = [
    ("0_qp_baseline",  dict(universe=QP9)),
    ("2_uso_to_xle",   dict(universe=["SHY", "IEF", "UUP", "GLD", "XLE",
                                      "SPY", "EFA", "QQQ", "EEM"])),
    ("3_drop_uup",     dict(universe=VB_CORE)),
    ("4_add_em_gate",  dict(universe=VB_FULL, gate=EM_GATE)),
    ("5a_hatch_shy",   dict(universe=VB_FULL, gate=EM_GATE, hatch="SHY")),
    ("5b_costs_10bps", dict(universe=VB_FULL, gate=EM_GATE, hatch="SHY",
                            cost_bps=COSTS_10)),
]


def load_prices(refresh=False):
    if os.path.exists(CACHE) and not refresh:
        return pd.read_pickle(CACHE)
    import yfinance as yf
    raw = yf.download(ALL_TICKERS, start=DATA_START, auto_adjust=True,
                      progress=False)["Close"]
    prices = raw[ALL_TICKERS].dropna(how="all")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    prices.to_pickle(CACHE)
    return prices


def run_step(weekly, universe, cost_bps=None, hatch=None, gate=None):
    pw = weekly[universe]
    w10 = dual_momentum_weights(pw, 10, 3, hatch=hatch, single_country_group=gate)
    w25 = dual_momentum_weights(pw, 25, 3, hatch=hatch, single_country_group=gate)
    wbl = blend_weights([w10, w25])
    net, _, _ = backtest(wbl, pw, cost_bps=cost_bps)
    return wbl, net.loc[EVAL_START:]


def yearly(r):
    return r.groupby(r.index.year).apply(lambda d: (1 + d).prod() - 1)


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    weekly = to_weekly(load_prices(refresh))

    rows, weights, returns = [], {}, {}
    for name, cfg in STEPS:
        wbl, r = run_step(weekly, **cfg)
        rows.append(stats(r, name))
        weights[name], returns[name] = wbl.loc[EVAL_START:], r
    rows.append(stats(equal_weight_returns(weekly[QP9]).loc[EVAL_START:],
                      "EW_qp9_benchmark"))

    pd.set_option("display.float_format", lambda x: f"{x:0.4f}")
    print(pd.DataFrame(rows).to_string())

    # step 4 diagnostics: EM sleeve usage + gate bindings
    w4 = weights["4_add_em_gate"]
    for t in EM_GATE:
        h = w4[t] > 0
        print(f"\n{t} held: {h.sum()} weeks ({h.mean():.1%}); by year:",
              dict(pd.Series(w4.index.year[h]).value_counts().sort_index()))
    wng, _ = run_step(weekly, VB_FULL, gate=None)
    wng = wng.loc[EVAL_START:]
    both = (wng["MCHI"] > 0) & (wng["INDA"] > 0)
    print(f"gate bindings (both would be held ungated): {both.sum()} weeks;",
          dict(pd.Series(wng.index.year[both]).value_counts().sort_index()))

    # step 5a diagnostics: hatch usage
    cash4 = w4["CASH"]
    print(f"\nstep 4 avg cash weight: {cash4.mean():0.3f} "
          f"(weeks any cash: {(cash4 > 0).mean():.1%})")
    shy_extra = weights["5a_hatch_shy"]["SHY"] - w4["SHY"]
    print(f"step 5a: hatch weight moved to SHY, avg {shy_extra[shy_extra > 0].mean():0.3f} "
          f"when active ({(shy_extra > 0).mean():.1%} of weeks)")

    # per-year deltas across the new steps
    yd = pd.DataFrame({n: yearly(returns[n]) for n in
                       ["3_drop_uup", "4_add_em_gate", "5a_hatch_shy", "5b_costs_10bps"]})
    yd["d_step4"] = yd["4_add_em_gate"] - yd["3_drop_uup"]
    yd["d_step5a"] = yd["5a_hatch_shy"] - yd["4_add_em_gate"]
    yd["d_step5b"] = yd["5b_costs_10bps"] - yd["5a_hatch_shy"]
    print("\nper-year returns and step deltas (%):")
    print((yd * 100).round(1).to_string())
