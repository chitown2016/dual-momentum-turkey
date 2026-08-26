"""
ROBUSTNESS VARIANT (SPEC 6 rule 1: appendix, NEVER headline) — risk-free hurdle.

Provenance, stated plainly: this variant was conceived AFTER seeing Phase 2
results (Version A underperformed Version B in the 2023H2 orthodox regime
despite deposits earning +19.1%/yr real). It is therefore post-hoc and does
NOT replace the pre-registered headline. Both numbers get published.

The change (exactly ONE thing): the absolute-momentum hurdle.
  headline  : a selected slot is held if its RoC > 0
  variant   : ... if its RoC > the RISK-FREE sleeve's RoC over the SAME lookback
Rationale (ex ante, not result-driven): Antonacci's absolute momentum is
defined as excess return over T-bills, not over zero. Quantpedia simplified to
zero, which is ~harmless in USD during ZIRP but meaningless in a currency with
8-50% deposit rates. Diagnostic: under the zero hurdle the filter rejects 0.9%
(10w) / 0.4% (25w) of top-3 slots — the absolute leg of "dual momentum" is
effectively inert in the headline Version A run.

BOTH versions get the same treatment, so the A-B gap keeps measuring deposit
INTEGRATION rather than "who got the better filter":
  Version A hurdle = DEPOSIT_TL RoC (nominal TL)   hatch = two-way (unchanged)
  Version B hurdle = SHY RoC (USD)                 hatch = SHY   (unchanged)
Everything else — universe, L in {10,25}, N=3, EM gate, weekly Wednesday,
costs, the two-way hatch design — is identical to the headline runs.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import (dual_momentum_weights, blend_weights, backtest, stats,
                    to_weekly)
from bridge_ablation import load_prices
from phase1_version_b import UNIVERSE_B, REGIMES
from phase2_version_a import (build_tl_panel, tl_numeraire_curves, UNIVERSE_A,
                              EM_GATE, HATCH, HATCH_LOOKBACK, PRIMARY_START,
                              COSTS_10, COSTS_25)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
COSTS_B10 = {t: 10.0 for t in UNIVERSE_B}


def _blend(panel, hatch, gate, hurdle, hatch_lb=None):
    kw = dict(hatch=hatch, single_country_group=gate, hurdle=hurdle)
    if hatch_lb is not None:
        kw["hatch_lookback"] = hatch_lb
    w10 = dual_momentum_weights(panel, 10, 3, **kw)
    w25 = dual_momentum_weights(panel, 25, 3, **kw)
    return blend_weights([w10, w25])


def run(refresh=False):
    panel, fx_weekly, cpi = build_tl_panel(refresh)
    cpi_ts = pd.Series(cpi.values, index=cpi.index)
    usd_weekly = to_weekly(load_prices(refresh))[UNIVERSE_B]

    out, weights = {}, {}

    # ---- Version A: headline (zero) vs variant (deposit hurdle) ----
    for tag, hurdle in [("VA_headline", None), ("VA_hurdle", "DEPOSIT_TL")]:
        w = _blend(panel, HATCH, EM_GATE, hurdle, HATCH_LOOKBACK)
        net10, _, turn = backtest(w, panel, cost_bps=COSTS_10)
        net25, _, _ = backtest(w, panel, cost_bps=COSTS_25)
        out[tag] = tl_numeraire_curves(net10, fx_weekly, cpi_ts)
        out[tag + "_25bps"] = tl_numeraire_curves(net25, fx_weekly, cpi_ts)
        weights[tag] = w.dropna(how="all").loc[PRIMARY_START:]
        weights[tag + "_turnover"] = turn.loc[PRIMARY_START:].mean()

    # ---- Version B: headline (zero) vs variant (SHY hurdle), USD signals ----
    for tag, hurdle in [("VB_headline", None), ("VB_hurdle", "SHY")]:
        w = _blend(usd_weekly, "SHY", EM_GATE, hurdle)
        net10, _, turn = backtest(w, usd_weekly, cost_bps=COSTS_B10)
        usd_r = net10.loc[PRIMARY_START:]
        fxb = fx_weekly.reindex(usd_r.index).ffill()
        tl_r = ((1 + usd_r) * (fxb / fxb.shift(1)) - 1).dropna()
        out[tag] = tl_numeraire_curves(tl_r, fx_weekly, cpi_ts)
        weights[tag] = w.dropna(how="all").loc[PRIMARY_START:]
        weights[tag + "_turnover"] = turn.loc[PRIMARY_START:].mean()

    names = ["VA_headline", "VA_hurdle", "VA_headline_25bps", "VA_hurdle_25bps",
             "VB_headline", "VB_hurdle"]
    table = pd.DataFrame([stats(out[n]["TL_real"].pct_change().dropna(), n)
                          for n in names])

    # gap table under both rules
    rows = []
    windows = [("full period", PRIMARY_START, None)] + list(REGIMES)
    for label, a, b in windows:
        row = {"window": label}
        for n in ["VA_headline", "VB_headline", "VA_hurdle", "VB_hurdle"]:
            c = out[n]["TL_real"].loc[a:b]
            row[n] = ((c.iloc[-1] / c.iloc[0]) ** (52 / len(c)) - 1
                      if len(c) >= 8 else np.nan)
        row["gap_headline"] = row["VA_headline"] - row["VB_headline"]
        row["gap_variant"] = row["VA_hurdle"] - row["VB_hurdle"]
        rows.append(row)
    gap = pd.DataFrame(rows).set_index("window")

    # deposit weight + hatch activity by year (the promised regime view)
    dep = pd.DataFrame({
        "headline": weights["VA_headline"]["DEPOSIT_TL"],
        "variant": weights["VA_hurdle"]["DEPOSIT_TL"]})
    dep_yr = dep.groupby(dep.index.year).mean()

    os.makedirs(RESULTS, exist_ok=True)
    table.to_csv(os.path.join(RESULTS, "robustness_hurdle_stats_TL_real.csv"))
    gap.to_csv(os.path.join(RESULTS, "robustness_hurdle_gap.csv"))
    dep_yr.to_csv(os.path.join(RESULTS, "robustness_hurdle_deposit_weight.csv"))

    return dict(table=table, gap=gap, dep_yr=dep_yr, curves=out,
                weights=weights, cpi_last=str(cpi.index[-1].date()))


if __name__ == "__main__":
    res = run(refresh="--refresh" in sys.argv)
    pd.set_option("display.float_format", lambda x: "%0.4f" % x)
    print("=== TL real, headline vs risk-free-hurdle variant (to CPI %s) ==="
          % res["cpi_last"])
    print(res["table"].to_string())
    print("\n=== A-B gap, real-TL annualized (%), both rules ===")
    print((res["gap"] * 100).round(1).to_string())
    print("\n=== Version A deposit sleeve weight by year (%) ===")
    print((res["dep_yr"] * 100).round(1).to_string())
    print("\nturnover (wk, one-way): VA head %.3f -> var %.3f | VB head %.3f -> var %.3f"
          % (res["weights"]["VA_headline_turnover"], res["weights"]["VA_hurdle_turnover"],
             res["weights"]["VB_headline_turnover"], res["weights"]["VB_hurdle_turnover"]))
