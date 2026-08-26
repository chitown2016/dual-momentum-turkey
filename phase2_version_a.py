"""
Phase 2 — Version A: the full Turkish saver's menu (SPEC 2, 3, 3a, 4, 6a).

Universe (locked): 10 USD ETF sleeves (as Version B) + TL layer:
  DEPOSIT_TL  rolled 1-3mo TL time deposit (TP.TRY.MT02 flow rate, weekly
              compounding at annual/52, step function between observations)
  BIST_TL     BIST-100 TOTAL RETURN index (TP.MK.G.BILESIK), already TL
USDTRY is the conversion backbone, not a sleeve (SHY-in-TL == holding USD).

SIGNAL CURRENCY RULE (SPEC 2, pinned): ALL signals in NOMINAL TL. Every USD
sleeve is converted (USD price x same-date Wednesday USDTRY mid, TCMB) and the
signal series IS the accounting series.

Escape hatch (two-way, SPEC 2): a slot failing the absolute filter goes to
whichever of {DEPOSIT_TL, SHY} has the higher 10w RoC in nominal TL.

Mechanics: L in {10,25}, N=3, 50/50 blend, weekly Wednesday, EM gate
(max one of MCHI/INDA per sub-strategy top-3). Costs: 10 bps one-way on all
sleeves except DEPOSIT_TL (0 per SPEC); 25 bps sensitivity.

Benchmarks (SPEC 4): B1 100% rolled TL deposits | B2 100% SHY-in-TL |
B3 100% GLD-in-TL | B4 100% BIST TR | B5 EW of the full 12-sleeve universe |
B6 50/50 deposits/BIST, weekly rebalanced (stylized).

Required output: A-B GAP — real-TL performance of VA_net10 minus VB_net10
(VB USD returns from phase1, converted with the SAME TCMB fx + EVDS CPI).

Primary window 2013-01-01 -> latest; TL-real truncates at CPI's last month.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import (dual_momentum_weights, blend_weights, backtest,
                    equal_weight_returns, stats, to_weekly)
from bridge_ablation import load_prices
from data_evds import load as evds_load
from phase1_version_b import run_phase1, REGIMES

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

USD_SLEEVES = ["SHY", "IEF", "GLD", "XLE", "SPY", "QQQ", "EFA", "EEM", "MCHI", "INDA"]
TL_SLEEVES = ["DEPOSIT_TL", "BIST_TL"]
UNIVERSE_A = USD_SLEEVES + TL_SLEEVES
EM_GATE = ["MCHI", "INDA"]
HATCH = ("DEPOSIT_TL", "SHY")
HATCH_LOOKBACK = 10
PRIMARY_START = "2013-01-01"

COSTS_10 = {t: (0.0 if t == "DEPOSIT_TL" else 10.0) for t in UNIVERSE_A}
COSTS_25 = {t: (0.0 if t == "DEPOSIT_TL" else 25.0) for t in UNIVERSE_A}


def build_tl_panel(refresh=False):
    """Weekly (W-WED) nominal-TL price panel for the 12 Version A sleeves,
    plus weekly fx (TCMB mid) and monthly CPI for reporting."""
    usd_weekly = to_weekly(load_prices(refresh))[USD_SLEEVES]
    fx_weekly = to_weekly(evds_load("usdtry", refresh).to_frame()).squeeze()
    fx_weekly = fx_weekly.reindex(usd_weekly.index).ffill()
    panel = usd_weekly.mul(fx_weekly, axis=0)

    bist = to_weekly(evds_load("bist100_tr", refresh).to_frame()).squeeze()
    panel["BIST_TL"] = bist.reindex(panel.index)

    rate = evds_load("deposit_flow_3m", refresh)          # Friday-dated, %
    r = rate.reindex(rate.index.union(panel.index)).ffill().reindex(panel.index)
    # price_t compounds rates known BEFORE t: pct_change t->t+1 == r_t/52
    dep = (1 + r.shift(1).fillna(0.0) / 100 / 52).cumprod()
    panel["DEPOSIT_TL"] = dep

    cpi = evds_load("cpi", refresh)                       # monthly, 2025=100
    return panel[UNIVERSE_A], fx_weekly, cpi


def tl_numeraire_curves(tl_returns, fx_weekly, cpi_monthly, start=PRIMARY_START):
    """Value curves from TL returns: TL nominal (base), USD, TL real."""
    r = tl_returns.loc[start:].dropna()
    tl = (1 + r).cumprod()
    fx = fx_weekly.reindex(tl.index).ffill()
    usd = tl / (fx / fx.iloc[0])
    months = tl.index.to_period("M")
    cpi_w = pd.Series([cpi_monthly.get(m.to_timestamp(), np.nan) for m in months],
                      index=tl.index)
    real = (tl / (cpi_w / cpi_w.dropna().iloc[0])).dropna()
    return {"TL_nominal": tl, "USD": usd, "TL_real": real}


def run_phase2(refresh=False):
    panel, fx_weekly, cpi = build_tl_panel(refresh)
    cpi_ts = pd.Series(cpi.values, index=cpi.index)

    def make(cost_bps, hatch=HATCH):
        kw = dict(hatch=hatch, single_country_group=EM_GATE)
        if hatch == HATCH:
            kw["hatch_lookback"] = HATCH_LOOKBACK
        w10 = dual_momentum_weights(panel, 10, 3, **kw)
        w25 = dual_momentum_weights(panel, 25, 3, **kw)
        wbl = blend_weights([w10, w25])
        net, gross, turnover = backtest(wbl, panel, cost_bps=cost_bps)
        return wbl, net, gross, turnover

    wbl, net10, gross, turnover = make(COSTS_10)
    _, net25, _, _ = make(COSTS_25)
    wcash, _, _, _ = make(None, hatch=None)      # CASH column == hatch triggers

    dep_r = panel["DEPOSIT_TL"].pct_change()
    bist_r = panel["BIST_TL"].pct_change()
    strategies = {
        "VA_gross": gross.dropna(),
        "VA_net10": net10,
        "VA_net25": net25,
        "B1_deposits": dep_r.dropna(),
        "B2_SHY_TL": panel["SHY"].pct_change().dropna(),
        "B3_GLD_TL": panel["GLD"].pct_change().dropna(),
        "B4_BIST": bist_r.dropna(),
        "B5_EW": equal_weight_returns(panel),
        "B6_50_50": (0.5 * dep_r + 0.5 * bist_r).dropna(),
    }

    curves = {n: tl_numeraire_curves(r, fx_weekly, cpi_ts) for n, r in strategies.items()}

    # Version B in the SAME numeraire machinery (TCMB fx + EVDS CPI) for the gap
    p1 = run_phase1(refresh)
    vb_usd_r = p1["curves"]["VB_net10"]["USD"].pct_change().dropna()
    fx_vb = fx_weekly.reindex(vb_usd_r.index).ffill()
    vb_tl_r = (1 + vb_usd_r) * (fx_vb / fx_vb.shift(1)) - 1
    curves["VB_net10"] = tl_numeraire_curves(vb_tl_r.dropna(), fx_weekly, cpi_ts)

    tables = {}
    for num in ["TL_real", "TL_nominal", "USD"]:
        tables[num] = pd.DataFrame(
            [stats(curves[n][num].pct_change().dropna(), n)
             for n in list(strategies) + ["VB_net10"]])

    # regime table + A-B gap (real TL, annualized), SPEC 7
    reg_rows, gap_rows = [], []
    windows = [("full period", PRIMARY_START, None)] + \
              [(lbl, a, b) for lbl, a, b in REGIMES]
    for label, a, b in windows:
        row = {"window": label}
        for n in ["VA_net10", "VB_net10", "B1_deposits", "B2_SHY_TL",
                  "B4_BIST", "B6_50_50", "B5_EW"]:
            c = curves[n]["TL_real"].loc[a:b]
            if len(c) < 8:
                row[n] = np.nan
                continue
            total = c.iloc[-1] / c.iloc[0] - 1
            row[n] = (1 + total) ** (52 / len(c)) - 1
        row["A_minus_B_gap"] = row["VA_net10"] - row["VB_net10"]
        gap_rows.append(row)
    gap = pd.DataFrame(gap_rows).set_index("window")

    w = wbl.dropna(how="all").loc[PRIMARY_START:]
    wc = wcash.dropna(how="all").loc[PRIMARY_START:]
    hatch_active = wc["CASH"] > 1e-9
    dep_w = w["DEPOSIT_TL"]
    holdings = {
        "mean_weekly_oneway_turnover": float(turnover.loc[PRIMARY_START:].mean()),
        "avg_sleeves_held": float((w[UNIVERSE_A] > 1e-9).sum(axis=1).mean()),
        "pct_weeks_in_deposit_sleeve": float((dep_w > 1e-9).mean()),
        "avg_deposit_weight_when_held": float(dep_w[dep_w > 1e-9].mean()),
        "pct_weeks_hatch_triggered": float(hatch_active.mean()),
    }

    os.makedirs(RESULTS, exist_ok=True)
    w.round(6).to_csv(os.path.join(RESULTS, "version_a_weekly_weights.csv"))
    for num, t in tables.items():
        t.to_csv(os.path.join(RESULTS, "version_a_stats_" + num + ".csv"))
    gap.to_csv(os.path.join(RESULTS, "a_minus_b_gap_real_tl.csv"))

    return dict(tables=tables, gap=gap, holdings=holdings, curves=curves,
                weights=w, panel=panel, cpi_last=str(cpi.index[-1].date()),
                fx_weekly=fx_weekly)


if __name__ == "__main__":
    res = run_phase2(refresh="--refresh" in sys.argv)
    pd.set_option("display.float_format", lambda x: "%0.4f" % x)
    for num in ["TL_real", "USD"]:
        tail = " (real to CPI " + res["cpi_last"] + ")" if num == "TL_real" else ""
        print("\n=== " + num + tail + " ===")
        print(res["tables"][num].to_string())
    print("\n=== holdings (primary window) ===")
    for k, v in res["holdings"].items():
        print("  %s: %0.3f" % (k, v))
    print("\n=== A-B gap table, real-TL annualized (%) ===")
    print((res["gap"] * 100).round(1).to_string())
