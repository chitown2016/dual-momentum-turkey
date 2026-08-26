# Research Spec: Dual Momentum GTAA for a Turkish Retail Investor

**Working title:** "Dual momentum for a collapsing currency: what rules-based allocation would have done for a Turkish saver, 2013–2026"

**Author / PI:** Michael Emre Tulum
**Implementing agent:** Claude Code on work machine
**Status:** Spec locked before any backtest runs. Universe and design rules are fixed ex ante (see §6). Do not add/remove sleeves or rules after seeing results.

---

## 1. Objective

Test whether a simple dual-momentum GTAA strategy (Antonacci-style: relative momentum ranking + absolute momentum filter), applied to a universe realistically accessible to a Turkish retail investor, would have protected and grown purchasing power through the 2013–2026 period — including the 2018 currency crisis, 2021–2023 inflation surge, and the post-2023 high-rate regime.

Two audiences, one artifact:
1. A public essay (English first, Turkish version later) — the credibility artifact.
2. A personal implementation candidate (later, small size, own IBKR account — out of scope for this phase).

**Methodological anchor:** Quantpedia, "Active Dual Momentum GTAA Strategy" (May 2026). We replicate the mechanics, not the universe. Cite it; deviate deliberately (see §5).

## 2. Core methodology (fixed)

- **Signal:** Rate of change (RoC) only. No moving averages, no vol targeting, no optimization. Keep parameter count minimal.
- **Dual momentum:**
  - Relative: rank sleeves by RoC over lookback L each rebalance date; select top N.
  - Absolute: selected sleeve is held only if its RoC > 0; otherwise that slot goes to the **escape hatch** (below).
- **Escape hatch (Version A):** there is no true risk-free asset for a Turkish saver — TL deposits carry devaluation risk (2018, 2021: double-digit REAL drawdowns), USD cash carries domestic-inflation risk in real-appreciation regimes. So the hatch is itself a two-way momentum decision: when the absolute filter triggers for a slot, that slot goes to whichever of {TL deposit sleeve, SHY-in-TL} has the higher RoC over the SHORT lookback (10w), in nominal TL (same signal convention as everything else — deflating both by the same CPI cannot change the comparison). This encodes the actual Turkish household dilemma ("faiz mi dolar mı?") adaptively. State this rationale in the essay.
- **Escape hatch (Version B):** SHY. (See §3a — Version B is USD-only and fully automatable.)
- **SIGNAL CURRENCY RULE (explicit, for implementation):**
  - Version A: ALL signals (RoC, ranking, absolute filter, hatch comparison) computed on nominal-TL price series. Every USD sleeve is converted first (price × same-date USDTRY Wednesday close), then RoC'd. The sleeve's signal series and its portfolio-accounting series must be the IDENTICAL TL series. Rationale: the investor's decision variable is TL; in a devaluation, a dollar-flat asset rising +40% in TL IS a rising asset for this investor — currency is most of the signal, not noise.
  - Version B: ALL signals computed on USD price series; only REPORTING is translated into the three numeraires.
- **Two sub-strategies, then blend:** L = 10 weeks and L = 25 weeks, N = 3 each; final strategy = 50/50 average of the two sub-strategy weight vectors (mirrors Quantpedia's final blend).
- **Rebalance:** Weekly, Wednesday close (fewer holiday artifacts). If Wednesday is a Turkish or US holiday, use the prior trading day common to both calendars.
- **Costs:** Model per-trade cost of 10 bps one-way on ETF sleeves, 0 on deposit roll. Report gross AND net. Sensitivity at 25 bps.
- **No leverage, long-only, fully invested (into deposit sleeve when filters trigger).**

## 3. Universe (fixed ex ante, with rationale)

USD-side sleeves (data: Yahoo Finance / yfinance, adjusted closes):

| Sleeve | Ticker | Inception | Rationale (stated before results) |
|---|---|---|---|
| Short USD rates / USD cash | SHY | 2002 | USD cash-equivalent; dollar safety leg |
| US Treasuries 7-10y | IEF | 2002 | Duration; the sleeve PTJ's scenario kills — keep it in and let momentum decide |
| Gold | GLD | 2004 | Hard asset, TL-crisis hedge; central to thesis |
| Energy equities | XLE | 1998 | Inflation/energy exposure. Deliberately REPLACES USO (front-month roll decay makes USO a broken vehicle; note this in essay) |
| US large cap | SPY | 1993 | Core US beta |
| US growth/tech | QQQ | 1999 | US concentration expression |
| Developed ex-US | EFA | 2001 | Non-US developed beta |
| Broad EM | EEM | 2003 | Diversified EM beta layer (kept DESPITE country sleeves below — see §6 rule 2) |
| China | MCHI | 2011 | Single-country expression of US→Asia rotation thesis |
| India | INDA | 2012 | Same; India ≠ China, strategy must be able to distinguish |

### 3a. Two nested versions (same engine, one universe flag)

**Version A — the full saver's menu (analytical headline).** All sleeves including the TL layer; escape hatch per §2. Answers "what was possible for a Turkish saver." NOT fully automatable today: TL time deposits live at banks, have maturity mechanics, and cannot be rotated weekly via any brokerage API. That's fine — A is the analysis, not the product.

**Version B — the implementable portfolio.** USD ETF sleeves only (SHY, IEF, GLD, XLE, SPY, QQQ, EFA, EEM, MCHI, INDA); escape hatch = SHY; everything executable at a single broker via API today. Reported in the same three numeraires.

**Required output: the A−B gap** (real-TL terms, full period and per regime window). This number prices what deposit/allocation integration is worth to a Turkish user — the single most product-relevant result of the study. If A ≫ B, the gap IS the product opportunity for a platform that integrates deposit-like yield with allocation. If A ≈ B, the dollar-only version suffices and the essay says so honestly.

Note for essay: weekly deposit rotation is unrealistic, but slow (quarterly-ish, manual) deposit↔USD moves are exactly what Turkish savers already do, and brokerage-held interest-bearing TL/USD balances (e.g., Midas pays yield on idle balances) are a deposit-like sleeve that IS automatable — mention as the bridge between A and B.

TL-side sleeves (Version A):

| Sleeve | Instrument / proxy | Data source | Rationale |
|---|---|---|---|
| TL deposits | 1–3 month TL time deposit, rolled | TCMB EVDS: weighted average deposit rates (flow, up to 3-month bucket) | THE key local sleeve. Note: TL carry has dominated everything in the past ~year at 40–50% rates — the strategy MUST be able to rotate into it. This sleeve is also the "cash" destination of the absolute-momentum filter |
| Turkish equities | BIST 100 total return (XU100T if available; else XU100 + dividend adjustment note) | EVDS / Borsa İstanbul / investing.com export | Local equity beta; huge nominal runs, brutal real drawdowns |
| USD/TRY | Spot | EVDS (TCMB indicative) or Yahoo (USDTRY=X) | Conversion backbone + implicit sleeve (holding USD cash = SHY in TL terms) |
| CPI (TÜFE) | Monthly index | TÜİK / EVDS | Real-terms deflator for all TL results |

**History handling (strict):**
- MCHI/INDA enter the universe at their actual inception. Do NOT splice index data onto ETF history. A universe whose membership expands as instruments become investable is realistic; state this in the essay.
- Optional robustness check only: pre-2011 China proxy via FXI (2004) — clearly labeled as robustness, never in headline results.
- Primary backtest window: 2013-01-01 → latest. Secondary (US-only sleeves): 2008 → latest for crisis behavior.

## 4. The Turkish-investor accounting layer (the novel part)

Everything is computed and reported in THREE numeraires:
1. **TL nominal** — what the account statement shows.
2. **TL real (CPI-deflated)** — the honest number; headline metric of the essay.
3. **USD** — for comparability.

Benchmarks (all three numeraires):
- B1: 100% TL deposits rolled (the "just collect interest" strategy — note: this has worked extremely well in the last ~year; the essay must show when it works and when it catastrophically doesn't, e.g., 2018, 2021)
- B2: 100% USD (SHY)
- B3: 100% gold (GLD in TL)
- B4: 100% BIST total return
- B5: Equal-weight of the full universe
- B6: Classic Turkish retail behavior proxy: 50% TL deposits / 50% BIST (document as stylized)

**The absolute-momentum filter's destination is the two-way escape hatch defined in §2** (TL deposits vs SHY-in-TL, decided by short-lookback momentum in real TL terms) — a deliberate, material deviation from Quantpedia's 0% cash. At Turkish rates and Turkish devaluation risk, this changes everything; call it out explicitly in the essay, including why neither deposits nor USD can be crowned "the" safe asset ex ante.

## 5. Deliberate deviations from the Quantpedia anchor (list these in the essay)

1. USO → XLE (roll-decay pathology; practitioner's substitution).
2. EEM split-but-kept: add MCHI + INDA as sleeves while retaining EEM (regime-expression vs diversification tension, resolved by §6 rule 2).
3. Cash → two-way escape hatch (TL deposits vs SHY-in-TL by short-lookback real-TL momentum), not 0% — because a Turkish saver has no true risk-free asset.
4. Tri-numeraire reporting with CPI-real TL as headline.
5. Universe membership expands at instrument inception (no splicing).
6. Nested A (full menu) / B (implementable, USD-only) versions with the A−B gap as a required output.

## 6. Design rules (locked)

1. **No parameter search.** L ∈ {10, 25}, N = 3, weekly Wednesday — inherited from anchor, not optimized. If someone (including us) is tempted to tune, that goes in a clearly-labeled robustness appendix, never headline.
2. **EM concentration gate:** at most ONE single-country EM sleeve (MCHI or INDA) held at a time. If both rank in top-3, take the higher-ranked; next slot passes to the next-ranked non-single-country-EM sleeve. Rationale: correlated EM positions in risk-off weeks; a practitioner constraint, documented ex ante.
3. **No result-driven universe edits.** The tables in §3 are final for the headline run.

## 6a. Phase plan (sequential, gated)

**Phase 0 — Validation run (mandatory gate).** Implement the engine and reproduce the Quantpedia setup as closely as practical: their exact 9-ETF universe (SHY, IEF, UUP, GLD, USO, SPY, EFA, QQQ, EEM), weekly Wednesday, L ∈ {10, 25}, N = 3, 0% cash, 2007/2008 → present, USD only, no costs.
- PASS criteria (neighborhood, not exact match — data vendor differs): blend Sharpe ≈ 0.8–1.0; blend max-DD visibly better than EW benchmark; both sub-strategies individually reasonable; equity curve shape qualitatively matches their Figure 5.
- If wildly off: debug engine mechanics (look-ahead, week alignment, filter logic, adjusted-close handling) BEFORE any Turkish data enters. Do not tune parameters to force a match.
- Keep the validation run as a permanent test in the repo — it's the regression test for all later engine changes.

**Phase 1 — Version B** (USD implementable universe per §3/§3a, USD signals, costs on). Outputs per §7.

**Phase 2 — Version A** (full Turkish menu, TL signals per §2 rule, EVDS data layer). Outputs per §7 including A−B gap.

**Phase 3 — Essay** (§9) + robustness appendix (only if time: FXI pre-2011 proxy check; cost sensitivity at 25 bps).

Each phase gates the next. If the timeline compresses, Phase 3's appendix is cut first, never Phase 0.

## 7. Outputs required

- `results/` — equity curves (log2 scale), all three numeraires, Versions A and B vs B1–B6.
- **A−B gap table**: real-TL performance difference, full period + each regime window (§7 regime table), with turnover-adjusted note.
- Stats table per Quantpedia convention: ann. return, ann. stdev, max DD, Sharpe (ret/vol), Calmar (ret/maxDD) — computed per numeraire.
- Regime table: performance in 5 hand-labeled windows: 2013–2017 (pre-crisis), 2018 (crisis), 2019–2020 (COVID), 2021–2023 (inflation surge / unorthodox rates), 2023H2–present (orthodox high-rate regime).
- Turnover, avg # of held sleeves, % weeks in deposit sleeve.
- Holdings timeline chart (which sleeve held when) — this is the chart that tells the story.
- One CSV of weekly weights for audit.

## 8. Tech notes for implementation

- Python; pandas + yfinance for USD sleeves; EVDS API (evds package, free key from TCMB) for deposit rates, USDTRY, CPI; BIST TR series via EVDS if present, else document source.
- **Engine must be country-parameterized:** universe table, deposit-rate series, CPI series, and FX pair are inputs, not hardcoded. Turkey is study #1; the same engine should run Argentina/Brazil/etc. later with only data swaps.
- Weekly resample to W-WED on adjusted closes; RoC = P_t / P_{t-L} - 1.
- Deposit sleeve accrual: weekly compounding at (annual rate / 52), rate as-of each week (step function between EVDS observations).
- Careful with TR/US holiday alignment; forward-fill prices max 5 days, else drop week.
- Sanity checks: reproduce Quantpedia-like behavior on their 9-ETF USD universe first (validation run), THEN run the Turkish spec. If the validation run looks wildly off from their published Sharpe ~0.9 blend, debug before proceeding.
- FX conversion: TL value of USD sleeve = USD price × USDTRY (same-date close).

## 9. Essay skeleton (target ~2000–2500 words + charts)

1. Hook — "faiz mi dolar mı?": B1 (roll TL deposits) vs B2 (hold USD) in REAL TL terms, one chart, 2013–2026. Deposits quietly win in calm regimes, incinerate in 2018/2021, win again post-2023. The national dinner-table debate, rendered visible. Then widen to the full naive menu (B3, B4).
2. Why momentum for regime shifts you can't time (2 paragraphs, cite Antonacci + Quantpedia anchor).
3. What a practitioner changes: USO/XLE, the no-risk-free-asset problem and the two-way escape hatch, country sleeves, tri-numeraire honesty (this is the credibility section).
4. Results: Version A headline real-TL curve, regime table, holdings timeline.
5. When "just collect interest" wins — and when it destroys you (the past-year TL carry regime vs 2018/2021, in real terms; how the adaptive hatch handled each, with what lag).
6. The implementable version: Version B, and the A−B gap — what integration of deposit yield with allocation is worth; what that implies for platforms structurally able to offer it.
7. What this doesn't prove: costs/tax reality (foreign-security self-declaration burden, TL-basis gains taxation — one paragraph, flag as unverified current law), overfitting risks, capacity, signal lag in fast collapses (2021 was ~6 weeks; a 25w signal is slow — report honestly).
8. Close: what this implies for how Turkish retail platforms should build allocation products.

## 10. Explicit non-goals (this phase)

- No live trading, no IBKR integration, no product architecture.
- No parameter optimization or ML.
- No tax computation engine — one honest paragraph only.
- No Turkish translation yet — English artifact first, ship before Sep 15.

**Definition of done:** validation run passes; headline run produces §7 outputs; essay draft exists; total elapsed ≤ 3 weeks of ~2h/day.
