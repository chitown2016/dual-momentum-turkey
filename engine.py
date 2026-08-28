"""
Country-parameterized dual-momentum GTAA engine.

Study: dual_momentum_turkish_investor (see SPEC.md — rules locked ex ante).
Anchor: Quantpedia "Active Dual Momentum GTAA Strategy" (2026-05-22).

Mechanics (per anchor + SPEC):
- Weekly series (Wednesday close), signal = RoC: P_t / P_{t-L} - 1.
- Relative momentum: rank sleeves by RoC at each rebalance, select top N.
- Absolute filter: a selected slot (weight 1/N) is held only if its RoC > 0;
  otherwise the slot goes to the escape hatch (Quantpedia: 0% cash).
- Weights decided at Wednesday close t earn sleeve returns over t -> t+1.
- Final strategy = 50/50 average of the L=10w and L=25w sub-strategy weights.

Everything country-specific (universe, hatch, single-country gate, costs) is
an input — Turkey is study #1; the engine must run other countries unchanged.
"""

import numpy as np
import pandas as pd

WEEKS_PER_YEAR = 52


def to_weekly(prices_daily, day="W-WED", ffill_limit=5):
    """Daily adjusted closes -> weekly (Wednesday) closes.

    Forward-fills up to `ffill_limit` calendar days so a holiday Wednesday
    takes the prior trading day's close (SPEC 8). Weeks with no price within
    the limit stay NaN.
    """
    filled = prices_daily.ffill(limit=ffill_limit)
    return filled.resample(day).last()


def roc(prices_weekly, lookback):
    return prices_weekly / prices_weekly.shift(lookback) - 1


def dual_momentum_weights(prices_weekly, lookback, n_select,
                          hatch=None, single_country_group=None,
                          hatch_lookback=None, hurdle=None):
    """Weekly target weight vectors for one sub-strategy.

    prices_weekly : DataFrame, weekly closes in the SIGNAL currency
                    (SPEC 2 signal-currency rule: signal series == accounting
                    series). Columns = sleeves. A sleeve is eligible at t only
                    when its RoC at t is computable (universe membership
                    expands at inception — SPEC 3, no splicing).
    lookback      : L in weeks.
    n_select      : N slots, each of weight 1/N.
    hatch         : destination of slots failing the absolute filter.
                    None          -> 0% cash (Quantpedia validation setup)
                    str           -> that sleeve, always (Version B: 'SHY')
                    (a, b)        -> two-way hatch (Version A): whichever of
                                     the two sleeves has higher RoC over
                                     `hatch_lookback` weeks. Computed on the
                                     same nominal-TL series as every other
                                     signal, per SPEC 2. (SPEC 4 says "real
                                     TL" for this comparison; the two are
                                     equivalent — a shared deflator cancels
                                     out of a two-way ranking — and SPEC 2
                                     is the operative wording, pinned before
                                     implementation: see STUDY_LOG.md.)
    single_country_group : list of sleeve names of which at most ONE may be
                    held at a time (SPEC 6 rule 2, EM gate). Applied within
                    this sub-strategy's top-N, before blending (pinned in
                    README). Lower-ranked group members are replaced by the
                    next-ranked non-group sleeve.
    hatch_lookback: L for the two-way hatch comparison (SPEC: short, 10w).
    hurdle        : absolute-momentum hurdle. None (default) = RoC > 0, the
                    pre-registered Quantpedia rule. A sleeve name = that
                    sleeve's RoC over the SAME lookback is the bar (Antonacci's
                    original excess-over-risk-free definition; robustness
                    variant only — see phase3_robustness_deposit_hurdle.py).
                    The hurdle sleeve itself always passes (it ties).

    Returns DataFrame of weights, columns = sleeves + 'CASH'. Row t is the
    target held from t close to t+1 close. Rows where no sleeve is eligible
    are all-NaN (before backtest start).
    """
    mom = roc(prices_weekly, lookback)
    group = set(single_country_group or [])
    hatch_mom = None
    if isinstance(hatch, tuple):
        if hatch_lookback is None:
            raise ValueError("two-way hatch requires hatch_lookback")
        hatch_mom = roc(prices_weekly[list(hatch)], hatch_lookback)

    cols = list(prices_weekly.columns) + ["CASH"]
    out = pd.DataFrame(np.nan, index=prices_weekly.index, columns=cols)
    slot_w = 1.0 / n_select

    for t in prices_weekly.index:
        m = mom.loc[t].dropna()
        if m.empty:
            continue
        ranked = m.sort_values(ascending=False).index.tolist()

        # top-N with the single-country gate
        selected, group_taken = [], False
        for name in ranked:
            if len(selected) == n_select:
                break
            if name in group:
                if group_taken:
                    continue
                group_taken = True
            selected.append(name)

        if hurdle is None:
            bar = 0.0
        else:
            bar = mom.loc[t].get(hurdle, np.nan)
            if np.isnan(bar):
                bar = 0.0

        w = dict.fromkeys(cols, 0.0)
        for name in selected:
            if name == hurdle or m[name] > bar:
                w[name] += slot_w
            else:  # absolute filter -> escape hatch
                if hatch is None:
                    w["CASH"] += slot_w
                elif isinstance(hatch, str):
                    w[hatch] += slot_w
                else:
                    a, b = hatch
                    hm = hatch_mom.loc[t]
                    dest = a if hm.get(a, -np.inf) >= hm.get(b, -np.inf) else b
                    w[dest] += slot_w
        # if fewer than n_select sleeves eligible, remainder stays in cash
        w["CASH"] += slot_w * (n_select - len(selected))
        out.loc[t] = pd.Series(w)

    return out


def blend_weights(weight_frames, blend_weights_=None):
    """Average sub-strategy weight frames (Quantpedia final blend: 50/50)."""
    if blend_weights_ is None:
        blend_weights_ = [1.0 / len(weight_frames)] * len(weight_frames)
    aligned = [wf.dropna(how="all") for wf in weight_frames]
    idx = aligned[0].index
    for wf in aligned[1:]:
        idx = idx.intersection(wf.index)
    return sum(b * wf.loc[idx] for b, wf in zip(blend_weights_, aligned))


def backtest(weights, prices_weekly, cost_bps=None):
    """Weekly portfolio returns from target weights.

    weights       : output of dual_momentum_weights/blend_weights.
                    Row t is held over t -> t+1. 'CASH' earns 0.
    prices_weekly : same currency/series as the signal (SPEC 2 rule).
    cost_bps      : None or dict sleeve -> one-way bps on traded weight
                    (deposit sleeve 0 per SPEC 2). Turnover measured
                    target-vs-target (drift within a week ignored; noted
                    in SPEC outputs as turnover-adjusted approximation).

    Returns (returns Series, gross Series, turnover Series).
    """
    w = weights.dropna(how="all")
    sleeves = [c for c in w.columns if c != "CASH"]
    rets = prices_weekly[sleeves].pct_change()

    held = w[sleeves].shift(1)          # decided at t-1, earns t-1 -> t
    gross = (held * rets).sum(axis=1, min_count=1).dropna()

    dw = w[sleeves].diff().abs()
    turnover = dw.sum(axis=1, min_count=1)
    if cost_bps:
        cost_vec = pd.Series({s: cost_bps.get(s, 0.0) for s in sleeves})
        costs = (dw * cost_vec * 1e-4).sum(axis=1, min_count=1)
    else:
        costs = pd.Series(0.0, index=w.index)
    net = (gross - costs.reindex(gross.index).fillna(0.0)).dropna()
    return net, gross, turnover


def equal_weight_returns(prices_weekly):
    """EW benchmark: weekly-rebalanced equal weight of eligible sleeves."""
    rets = prices_weekly.pct_change()
    return rets.mean(axis=1).dropna()


def stats(returns, name=""):
    """Quantpedia-convention stats: perf (ann.), st dev (ann.), max dd,
    Sharpe = perf/stdev, Calmar = perf/maxdd."""
    r = returns.dropna()
    curve = (1 + r).cumprod()
    years = len(r) / WEEKS_PER_YEAR
    perf = curve.iloc[-1] ** (1 / years) - 1
    stdev = r.std() * np.sqrt(WEEKS_PER_YEAR)
    dd = (curve / curve.cummax() - 1).min()
    return pd.Series(
        {"perf": perf, "st_dev": stdev, "max_dd": dd,
         "sharpe": perf / stdev, "calmar": perf / abs(dd),
         "weeks": len(r)}, name=name)
