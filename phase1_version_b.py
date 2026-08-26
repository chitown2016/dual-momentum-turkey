"""
Phase 1 — Version B: the implementable USD portfolio (SPEC 3a, 6a).

Universe (locked): SHY IEF GLD XLE SPY QQQ EFA EEM MCHI INDA
  - MCHI/INDA enter at actual inception (no splicing)
  - EM gate: at most one of {MCHI, INDA} held, per sub-strategy top-3
  - hatch = SHY; L in {10,25}, N=3, 50/50 blend; weekly Wednesday
  - costs 10 bps one-way on ETF sleeves (gross also reported; 25 bps sensitivity)
Signals: USD price series ONLY. Reporting: three numeraires (SPEC 4):
  USD | TL nominal (x USDTRY) | TL real (CPI-deflated; PROVISIONAL deflator =
  IMF IFS PCPI_IX via DBnomics until the EVDS/TUIK layer lands in Phase 2 —
  TL-real series truncates at the CPI's last month; publication lag ignored).
Benchmarks computable in Phase 1: B2 = 100% SHY, B3 = 100% GLD,
  B5 = EW of the Version B universe. (B1/B4/B6 need EVDS -> Phase 2.)
Primary window 2013-01-01 -> latest; secondary (USD, crisis) 2008-02-21 ->.
"""

import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import (dual_momentum_weights, blend_weights, backtest,
                    equal_weight_returns, stats, to_weekly)
from bridge_ablation import load_prices

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FX = os.path.join(HERE, "cache", "usdtry_daily.pkl")
CACHE_CPI = os.path.join(HERE, "cache", "tr_cpi_monthly_provisional.pkl")
RESULTS = os.path.join(HERE, "results")

UNIVERSE_B = ["SHY", "IEF", "GLD", "XLE", "SPY", "QQQ", "EFA", "EEM", "MCHI", "INDA"]
EM_GATE = ["MCHI", "INDA"]
HATCH = "SHY"
PRIMARY_START = "2013-01-01"
SECONDARY_START = "2008-02-21"

REGIMES = [
    ("2013-2017 pre-crisis", "2013-01-01", "2017-12-31"),
    ("2018 crisis", "2018-01-01", "2018-12-31"),
    ("2019-2020 COVID", "2019-01-01", "2020-12-31"),
    ("2021-2023H1 infl. surge", "2021-01-01", "2023-06-30"),
    ("2023H2-present orthodox", "2023-07-01", None),
]


def load_fx(refresh=False):
    if os.path.exists(CACHE_FX) and not refresh:
        return pd.read_pickle(CACHE_FX)
    import yfinance as yf
    fx = yf.download("USDTRY=X", start="2007-01-01", auto_adjust=True,
                     progress=False)["Close"].squeeze()
    fx.name = "USDTRY"
    fx.to_pickle(CACHE_FX)
    return fx


def load_cpi(refresh=False):
    """PROVISIONAL Turkish CPI (IMF IFS PCPI_IX via DBnomics), monthly index.
    Replace with TUIK/EVDS in Phase 2."""
    if os.path.exists(CACHE_CPI) and not refresh:
        return pd.read_pickle(CACHE_CPI)
    url = "https://api.db.nomics.world/v22/series/IMF/CPI/M.TR.PCPI_IX?observations=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    j = json.load(urllib.request.urlopen(req, timeout=60))
    doc = j["series"]["docs"][0]
    cpi = pd.Series(doc["value"],
                    index=pd.PeriodIndex(doc["period"], freq="M"),
                    name="TR_CPI").astype(float).dropna()
    cpi.to_pickle(CACHE_CPI)
    return cpi


def numeraire_curves(usd_returns, fx_weekly, cpi_monthly, start):
    """Value curves (start = 1.0) in USD, TL nominal, TL real.
    TL real truncates at the last CPI month (no stale-deflator tail)."""
    r = usd_returns.loc[start:]
    usd = (1 + r).cumprod()
    fx = fx_weekly.reindex(usd.index).ffill()
    tl = usd * fx / fx.iloc[0]
    months = usd.index.to_period("M")
    cpi_w = pd.Series([cpi_monthly.get(m, np.nan) for m in months],
                      index=usd.index)
    real = (tl / (cpi_w / cpi_w.dropna().iloc[0])).dropna()
    return {"USD": usd, "TL_nominal": tl, "TL_real": real}


def run_phase1(refresh=False):
    weekly = to_weekly(load_prices(refresh))
    pw = weekly[UNIVERSE_B]
    fx_weekly = to_weekly(load_fx(refresh).to_frame()).squeeze()
    cpi = load_cpi(refresh)

    def make(hatch, cost):
        w10 = dual_momentum_weights(pw, 10, 3, hatch=hatch, single_country_group=EM_GATE)
        w25 = dual_momentum_weights(pw, 25, 3, hatch=hatch, single_country_group=EM_GATE)
        wbl = blend_weights([w10, w25])
        cost_bps = {t: cost for t in UNIVERSE_B} if cost else None
        net, gross, turnover = backtest(wbl, pw, cost_bps=cost_bps)
        return wbl, net, gross, turnover

    wbl, net10, gross, turnover = make(HATCH, 10.0)
    _, net25, _, _ = make(HATCH, 25.0)
    wcash, _, _, _ = make(None, 0)          # CASH column == hatch activity

    strategies = {
        "VB_gross": gross.dropna(), "VB_net10": net10, "VB_net25": net25,
        "B2_SHY": weekly["SHY"].pct_change().dropna(),
        "B3_GLD": weekly["GLD"].pct_change().dropna(),
        "B5_EW": equal_weight_returns(pw),
    }

    curves = {n: numeraire_curves(r, fx_weekly, cpi, PRIMARY_START)
              for n, r in strategies.items()}

    tables = {}
    for num in ["USD", "TL_nominal", "TL_real"]:
        tables[num] = pd.DataFrame(
            [stats(curves[n][num].pct_change().dropna(), n) for n in strategies])

    reg_rows = []
    for label, a, b in REGIMES:
        for n in ["VB_net10", "B2_SHY", "B3_GLD", "B5_EW"]:
            for num in ["USD", "TL_nominal", "TL_real"]:
                c = curves[n][num].loc[a:b]
                if len(c) < 8:
                    continue
                total = c.iloc[-1] / c.iloc[0] - 1
                yrs = len(c) / 52
                reg_rows.append({"regime": label, "strategy": n, "numeraire": num,
                                 "ann_return": (1 + total) ** (1 / yrs) - 1,
                                 "total_return": total})
    regimes = pd.DataFrame(reg_rows)

    w = wbl.dropna(how="all").loc[PRIMARY_START:]
    wc = wcash.dropna(how="all").loc[PRIMARY_START:]
    hatch_active = wc["CASH"] > 1e-9
    holdings = {
        "mean_weekly_oneway_turnover": float(turnover.loc[PRIMARY_START:].mean()),
        "avg_sleeves_held": float((w[UNIVERSE_B] > 1e-9).sum(axis=1).mean()),
        "pct_weeks_hatch_active": float(hatch_active.mean()),
        "avg_hatch_weight_when_active": float(wc.loc[hatch_active, "CASH"].mean()),
    }

    secondary = pd.DataFrame(
        [stats(strategies[n].loc[SECONDARY_START:], n)
         for n in ["VB_gross", "VB_net10", "B5_EW"]])

    os.makedirs(RESULTS, exist_ok=True)
    w.round(6).to_csv(os.path.join(RESULTS, "version_b_weekly_weights.csv"))
    for num, t in tables.items():
        t.to_csv(os.path.join(RESULTS, "version_b_stats_" + num + ".csv"))
    regimes.to_csv(os.path.join(RESULTS, "version_b_regimes.csv"), index=False)

    return dict(tables=tables, regimes=regimes, holdings=holdings,
                secondary=secondary, curves=curves, weights=w,
                cpi_last=str(cpi.index[-1]), fx_weekly=fx_weekly)


if __name__ == "__main__":
    res = run_phase1(refresh="--refresh" in sys.argv)
    pd.set_option("display.float_format", lambda x: "%0.4f" % x)
    for num in ["USD", "TL_nominal", "TL_real"]:
        tail = " CPI " + res["cpi_last"] if num == "TL_real" else " latest"
        print("\n=== " + num + " (primary window " + PRIMARY_START + " ->" + tail + ") ===")
        print(res["tables"][num].to_string())
    print("\n=== holdings/turnover (primary) ===")
    for k, v in res["holdings"].items():
        print("  %s: %0.3f" % (k, v))
    print("\n=== secondary USD window (2008-02-21 ->) ===")
    print(res["secondary"].to_string())
    for num in ["TL_real", "USD"]:
        piv = res["regimes"][res["regimes"]["numeraire"] == num].pivot(
            index="regime", columns="strategy", values="ann_return")
        print("\n=== regimes, " + num + " annualized return ===")
        print((piv * 100).round(1).to_string())
