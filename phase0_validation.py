"""
Phase 0 — validation run (SPEC 6a, mandatory gate).

Reproduce the Quantpedia setup: 9 ETFs (SHY, IEF, UUP, GLD, USO, SPY, EFA,
QQQ, EEM), weekly Wednesday, L in {10, 25}, N=3, 0% cash hatch, USD only,
no costs. Their window: data 2007-02-21 -> 2026-03-25, final-strategy
evaluation from 2008-02-21 (Figure 5 / Table 5).

PASS (neighborhood, data vendor differs): blend Sharpe ~ 0.8-1.0; blend
max-DD visibly better than the EW benchmark; both sub-strategies reasonable.

This file is the PERMANENT regression test for all later engine changes —
do not tune parameters to force a match.

Run:  python phase0_validation.py [--refresh]
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import (dual_momentum_weights, blend_weights, backtest,
                    equal_weight_returns, stats, to_weekly)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "phase0_prices_daily.pkl")

UNIVERSE = ["SHY", "IEF", "UUP", "GLD", "USO", "SPY", "EFA", "QQQ", "EEM"]
DATA_START = "2006-08-01"          # runway before 2007-02-21
EVAL_START = "2008-02-21"          # Quantpedia Figure 5 window
EVAL_END = None                    # -> latest; set "2026-03-25" to mirror QP


def load_prices(refresh=False):
    if os.path.exists(CACHE) and not refresh:
        return pd.read_pickle(CACHE)
    import yfinance as yf
    raw = yf.download(UNIVERSE, start=DATA_START, auto_adjust=True,
                      progress=False)["Close"]
    prices = raw[UNIVERSE].dropna(how="all")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    prices.to_pickle(CACHE)
    return prices


def run(refresh=False):
    daily = load_prices(refresh)
    weekly = to_weekly(daily)

    w10 = dual_momentum_weights(weekly, lookback=10, n_select=3, hatch=None)
    w25 = dual_momentum_weights(weekly, lookback=25, n_select=3, hatch=None)
    wbl = blend_weights([w10, w25])

    window = slice(EVAL_START, EVAL_END)
    rows, curves = [], {}
    for name, w in [("sub_10w", w10), ("sub_25w", w25), ("blend", wbl)]:
        net, _, turnover = backtest(w, weekly)
        r = net.loc[window]
        rows.append(stats(r, name))
        curves[name] = (1 + r).cumprod()
        if name == "blend":
            blend_turnover = turnover.loc[window].mean()
    ew = equal_weight_returns(weekly).loc[window]
    rows.append(stats(ew, "EW_benchmark"))
    curves["EW_benchmark"] = (1 + ew).cumprod()

    table = pd.DataFrame(rows)
    blend, bench = table.loc[table.index[2]], table.loc[table.index[3]]

    checks = {
        "blend Sharpe in [0.8, 1.0] neighborhood (>=0.75)":
            blend["sharpe"] >= 0.75,
        "blend Sharpe > EW Sharpe": blend["sharpe"] > bench["sharpe"],
        "blend max-DD visibly better than EW (<= 0.75x)":
            abs(blend["max_dd"]) <= 0.75 * abs(bench["max_dd"]),
        "both sub-strategies Sharpe > EW":
            (table["sharpe"].iloc[0] > bench["sharpe"])
            and (table["sharpe"].iloc[1] > bench["sharpe"]),
    }
    return table, checks, curves, wbl, blend_turnover


if __name__ == "__main__":
    table, checks, curves, wbl, to_ = run(refresh="--refresh" in sys.argv)
    pd.set_option("display.float_format", lambda x: f"{x:0.4f}")
    print(table.to_string())
    print(f"\nblend mean weekly one-way turnover: {to_:0.3f}")
    print()
    for k, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {k}")
    print("\nPHASE 0:", "PASS" if all(checks.values()) else "FAIL")
