# Dual Momentum GTAA for a Turkish Retail Investor

**status:** active
**started:** 2026-08-22
**family:** dual_momentum
**descends from:** [[dual_momentum]] — same Quantpedia "Active Dual Momentum GTAA" anchor and engine mechanics; that study's futures implementation was promoted to production `futures_momentum1`
**feeds:** public essay (English, ship before 2026-09-15); later a personal IBKR implementation candidate (out of scope this phase)

## Question

Would a simple Antonacci-style dual-momentum GTAA (relative top-3 ranking + absolute
filter, L ∈ {10, 25}w blend, weekly Wednesday), applied to a universe realistically
accessible to a Turkish retail investor, have protected and grown REAL purchasing power
through 2013–2026 (2018 crisis, 2021–2023 inflation surge, post-2023 high-rate regime)
— and what is the A−B gap (full saver's menu vs USD-only implementable portfolio) worth?

Full pre-registration: [SPEC.md](SPEC.md) — universe, rules, and phase gates locked
ex ante; no result-driven edits.

## Data

- USD ETF sleeves: yfinance adjusted closes (SHY, IEF, GLD, XLE, SPY, QQQ, EFA, EEM, MCHI, INDA; validation run adds UUP, USO)
- TL layer: TCMB EVDS API (deposit rates, USDTRY, CPI/TÜFE); BIST 100 TR via EVDS if present, else documented alternative
- **EVDS series codes (verified + cached 2026-08-22, `data_evds.py`):**
  - `TP.TRY.MT02` — TL deposit rate, flow, up-to-3-months, weekly Friday, 2002-> (robustness alt: `TP.TRYTAS.MT02` savings-only 2012->; stock twin `TP.MT210AGS.*` NOT used)
  - `TP.TUKFIY2025.GENEL` — CPI general index **2025=100, backcast to 2005-01** (TUIK rebased 2026; old 2003=100 `TP.FG.J0` frozen at 2026-01 — do not use). Chained growth identical to IMF provisional deflator (0.00% drift over 5y overlap)
  - `TP.DK.USD.A.YTL` / `TP.DK.USD.S.YTL` — daily USDTRY buy/sell; we use mid
  - `TP.MK.G.BILESIK` — BIST-100 RETURN index (XU100 total return), daily, 1997-> (spec's preferred XU100T; `TP.MK.F.BILESIK` is the price twin)
  - API: base `https://evds3.tcmb.gov.tr/igmevdsms-dis/`, key in `key:` HTTP header (from .env, not committed); responses cap near 1000 rows -> chunked 2-year fetching in `data_evds.py`
- EVDS migrated to **evds3.tcmb.gov.tr** (evds2 redirects there; verified 2026-08-22).
  Free API key via registration -> profile page; key now goes in an HTTP header.
  Use the `evdspy` package (v3-aware, EVDS_API_KEY in .env, handles TCMB legacy SSL);
  SPEC 8's `evds` package reference is stale. Docs: evds3.tcmb.gov.tr/dokumanlar.
  Verify v2->v3 series-code continuity (deposit rates, TUFE, BIST) at Phase 2 start.

## Implementation clarifications (pinned ex ante, 2026-08-22)

1. **Hatch signal currency:** SPEC §2 (nominal TL) is canonical; §4's "real TL terms"
   wording is equivalent under a shared deflator — nominal is used in code.
2. **EM concentration gate** applies within each sub-strategy's top-3 independently
   (10w and 25w separately), before blending.
3. **Version A deposit sleeve** is both a rankable sleeve and the hatch destination;
   its absolute filter (nominal RoC > 0) is trivially always-on at positive rates — by design.
4. **Code lives in this folder** (engine + notebooks + Phase 0 validation run as the
   permanent regression test). Promotion out of the folder (Argentina/Brazil reuse,
   live implementation) is a later, separate decision.

## Conventions

- cache/ holds regenerable intermediates only — safe to delete at any time.
- Anything NOT regenerable gets noted here before it lands in the folder.
- On conclusion: verdict below AND a decision note in the vault; folder to _archive/.

## Log

- 2026-08-22 — Study created. Spec (locked pre-registration) moved in from
  `raw/gtaa_turkish_investor_research_spec.md` as SPEC.md. Four implementation
  ambiguities resolved and pinned above before any engine code. Next: Phase 0
  validation run (Quantpedia 9-ETF universe, pass gate per SPEC §6a).

- 2026-08-22 — **Phase 0 PASSED** on first run, no tuning. Engine (`engine.py`,
  country-parameterized) + permanent regression test (`phase0_validation.py`) +
  executed `phase0_validation.ipynb`. Quantpedia 9-ETF setup, yfinance data:
  blend Sharpe 0.89 (0.85 on their exact window to 2026-03-25) vs published ~0.9;
  max-DD -12.4% vs EW -32.8%; subs 0.80/0.84 vs EW 0.58. Turnover 0.30/wk one-way
  (~1.6%/yr at 10 bps — Phase 1 cost preview). Data cached in cache/ (regenerable,
  --refresh to re-download). Next: Phase 1 (Version B, costs on).

- 2026-08-22 — **Bridge ablation step 2 (USO->XLE)**, diagnostic/appendix only
  (`bridge_ablation.py`; universe stays locked regardless of results): blend
  Sharpe 0.888 -> 1.033, perf 10.8% -> 11.8%, vol 12.2% -> 11.4%, max-DD ~flat
  (-12.4% -> -12.1%). EW benchmark moved almost as much (0.58 -> 0.70), so the
  gain is mostly vehicle quality (USO roll decay), not selection interaction —
  the momentum filter did NOT protect against decay (USO held 51.6% of weeks,
  same frequency as XLE's 52.9%). Holdings divergence: XLE-only weeks cluster
  2010-2016 + 2022 (contango decade / energy-equity runs), USO-only 2019 +
  2024-25. Remaining ladder: drop UUP -> +MCHI/INDA+gate -> costs (= Phase 1).

- 2026-08-22 — **Bridge step 3 (drop UUP)**: blend Sharpe 1.033 -> 0.977
  (perf 11.8% -> 11.6%, vol 11.4% -> 11.9%, DD -12.1% -> -12.8%). The entire
  cost is ONE year: 2022 (+4.3% with UUP vs -3.1% without, -7.5 pts; UUP held
  46/52 weeks that year — the only positive-momentum asset while stocks AND
  bonds fell). Excluding 2022, no-UUP is cumulatively ~+6 pts BETTER (UUP was
  dead weight displacing better sleeves in 2015/2018/2023/2025). Essay point:
  the USD-only implementable universe has no pure-FX crisis sleeve; its 2022-
  shaped hole is what Version A's two-way hatch must cover in TL terms. Universe
  stays locked. Next ladder steps: +MCHI/INDA+gate, then costs (= Phase 1).

- 2026-08-22 — **Bridge steps 4/5a/5b — ladder complete** (`bridge_ablation.py`).
  Full bridge: QP baseline 0.888 -> +XLE 1.033 -> -UUP 0.977 -> +MCHI/INDA+gate
  0.844 -> SHY hatch 0.851 -> costs 10bps 0.697 (= Version B config, USD terms;
  EW benchmark 0.580, DD -32.8%). **Step 4 is the expensive deviation**: country
  sleeves cost ~0.13 Sharpe and deepen DD -12.8% -> -17.5%; damage in momentum
  head-fake years (2013 taper -4.4, 2019 -3.7, 2020 -4.2, 2022 -3.2, 2023 China
  chase -4.8) vs gains 2014/2017; each sleeve held ~33% of weeks, gate bound 149
  weeks (~15% of EM-held weeks) — the regime-expression thesis has a quantified
  price. Step 5a (SHY hatch) ~wash (+1.4 in 2008, -0.8 in 2022 when SHY fell).
  Step 5b costs ~-2.0%/yr (> the 1.6% preview — EM sleeves + hatch churn more),
  -0.15 Sharpe. All diagnostic; universe locked. Next: Phase 1 proper (Version B
  tri-numeraire reporting + SPEC section 7 outputs).

- 2026-08-22 — **Phase 1 COMPLETE** (`phase1_version_b.py` + executed notebook;
  outputs in results/). Version B tri-numeraire, 2013 -> latest. Headline real-TL:
  VB net10 11.1%/yr (3.9x, Sharpe 0.55) ~ TIES B5 EW (11.2%, 3.9x) — active edge
  net of 10bps is shape (USD DD -18.6% vs -24.3%; 2018 crisis +10.7% vs +6.3%
  real), not growth; at 25bps VB falls BELOW EW (8.1%/yr real) — costs are
  existential at retail levels. B2 hold-dollars made only 1.8x real (half of VB)
  but 2023H2-> is the pivot: B2 -10.3%/yr real, VB -2.3%, only gold positive —
  no USD-only allocation solves the orthodox regime; that's B1/Version A's slot
  (A-B gap setup). Turnover 0.34/wk, 4.2 sleeves avg, hatch active 12.1% of wks.
  DATA: TL-real deflator PROVISIONAL (IMF PCPI_IX via DBnomics, ends 2025-07,
  cache tr_cpi_monthly_provisional.pkl) — swap to TUIK/EVDS in Phase 2 (needs
  free EVDS API key, USER action); USDTRY from Yahoo. Next: Phase 2 (Version A,
  EVDS layer, B1/B4/B6, A-B gap).

- 2026-08-22 — **EVDS data layer LIVE** (`data_evds.py`, key in .env). All four
  TL-side series verified against the evds3 catalog, full history cached:
  deposit flow 3m weekly 2002->, CPI 2025=100 monthly 2005-> (current to
  2026-07, YoY 31.8%), USDTRY mid daily 2002->, BIST-100 total-return daily
  2002->. Gotchas found: evds3 API base is /igmevdsms-dis/ (not /service/evds),
  ~1000-row response cap (chunked fetching), TUIK 2026 CPI rebase froze the old
  2003=100 series. User's two Excel exports identified: (1).xlsx = flow weekly
  TP.TRY.MT02 etc, plain .xlsx = stock monthly TP.MT210AGS. Phase 2 analysis
  can start: B1/B4/B6 benchmarks, Version A, A-B gap.

- 2026-08-22 — **Phase 2 COMPLETE** (`phase2_version_a.py` + executed notebook;
  results/ has stats, gap CSV, weights, 2 PNGs). Version A real-TL headline:
  **4.7x / 11.7%/yr net10 (Sharpe 0.61)** vs VB 4.3x/11.2%; ENTIRE naive menu
  1.1-1.6x over 13y (B1 deposits 1.1x, real DD -49%; B2 dollars 1.6x; B4 BIST
  1.3x; B6 1.3x) — rotation, not any sleeve, was the value. **A-B gap: +0.5/yr
  full period; +5.0 (2018), +6.0 (2021-23H1), -3.3 (2023H2->)** — regime
  insurance, not constant edge. SURPRISE: VA underperforms VB in the orthodox
  regime (-1.5 vs +1.9 real) despite B1 +19.1 — nominal-TL momentum held only
  ~20% deposits (vs 100% optimal) and BIST dragged; signal-lag caveat concrete.
  Two-way hatch nearly moot (fires 2.8% of weeks — TL depreciation keeps RoC
  positive; deposits enter via RANKING, 29.6% of weeks). At 25bps VA still 9.0%
  real (beats all naive; unlike VB). Deposit weight by year: ~0 pre-2018, 16%
  2019, 20-22% 2024-26. Next: Phase 3 essay.

- 2026-08-24 — **ROBUSTNESS VARIANT: risk-free hurdle** (`phase3_robustness_deposit_hurdle.py`,
  appendix only — headline untouched; provenance stated in the module docstring:
  conceived AFTER seeing Phase 2's orthodox-regime result, so post-hoc by
  construction). ONE change: absolute filter `RoC > 0` -> `RoC > risk-free RoC
  at same lookback` (A: DEPOSIT_TL, B: SHY) — Antonacci's original
  excess-over-riskfree definition; the zero bar rejected only 0.9%/0.4% (10w/25w)
  of top-3 slots, i.e. the absolute leg was INERT. Both versions treated
  identically so the A-B gap keeps measuring deposit INTEGRATION. Engine gained
  `hurdle=` param (default None = old behaviour); **Phase 0 regression re-run,
  PASS, numbers identical (0.8880)**.
  RESULTS (real TL): VA 11.74->12.08%/yr, vol 19.15->18.86, DD -27.1->-26.0,
  Sharpe 0.613->0.641 — better return AND lower risk. **VB gets slightly WORSE**
  (11.25->10.99, Sharpe 0.571->0.557) — perfect control: in USD the SHY bar
  ~= zero during ZIRP, so the gain in A is specifically the TL carry regime,
  not "hurdles are generically better". **A-B gap DOUBLES: +0.5 -> +1.1/yr**
  full period; orthodox regime gap -3.3 -> -1.2. Deposit weight 2024
  21.8%->50.0%, 2025 20.1->39.6, 2026 17.2->29.4. Turnover ~flat (0.353->0.364).
  Predictions scored (made before running): orthodox turns positive CORRECT
  (-1.5 -> +0.2), deposit weight to 50-70% CORRECT, surge unchanged CORRECT
  (23.5->23.3), full-period improves CORRECT (+0.4), gap row flips PARTIAL
  (shrank, didn't flip).
  **KEY: the Phase 2 signal-lag finding SURVIVES the fix.** Even holding 50%
  deposits, VA_hurdle earns +0.2%/yr real in the orthodox regime vs B1 deposits
  alone at +19.1 — mitigated, not rescued. Also honest: the +0.4/yr full-period
  gain is within noise; what is meaningful is the mechanism and the regime
  behaviour, not the headline delta. CSVs: robustness_hurdle_{stats_TL_real,
  gap,deposit_weight}.csv

- 2026-08-24 — **Numeraire/vol finding (essay material; forecloses an obvious
  'future work' direction).** Deposit sleeve risk is entirely numeraire-dependent:
  same asset 2013->, ann vol 2.4% / 8.6% / 14.6% and max DD 0.0% / -49.3% /
  -70.2% in TL-nominal / TL-real / USD. In nominal TL the series is monotonically
  increasing (worst week +0.1%) — the numeraire CANNOT express the deposit's only
  real risk (lira buying less); devaluation instead shows up as UPSIDE in the
  dollar sleeves, so the strategy perceives deposit risk only indirectly and with
  lag. **Consequence: vol-scaling the momentum signal (Sharpe-like ranking) in
  nominal TL is CATASTROPHIC — deposits rank 1.0 and sit top-3 in 100% of weeks
  in BOTH regimes, including the 2021-23 surge when they lost 16.8%/yr real.
  Do not "fix" the ranking that way.** The order-statistic account of why
  deposits rank 4.2nd (3 of 11 noisy sleeves clear a smooth one most weeks)
  stands; calling deposits "low-risk" does not. Untested candidate principle:
  return in the transaction currency (nominal TL) but RISK in the consumption
  currency (real TL, deposits ~8.6% vol vs sleeves ~20%) — caveats: our real-TL
  vol is lumpy (monthly CPI => ~12 jumps/yr) and CPI in a SIGNAL introduces
  publication-lag look-ahead the current design avoids.

- 2026-08-24 — **SIGNIFICANCE AUDIT — materially changes the conclusions.**
  Naive t-tests on weekly real-TL return differences, full period n=707:
  **The A-B gap is NOT distinguishable from zero in ANY window** — full period
  +0.9%/yr t=0.53 CI[-2.4,+4.2]; 2018 +4.3 t=0.92 CI[-4.8,+13.3]; 2021-23H1
  +5.4 t=1.07 CI[-4.5,+15.3]; orthodox -1.7 t=-0.36 CI[-10.7,+7.4]. The earlier
  "regime insurance / +5 / +6 / -3.3" narration was POINT ESTIMATES ONLY and
  should not be reported as findings. Structural cause: **VA vs VB weekly real
  returns correlate 0.962** (10 of 12 sleeves shared, both dominated by the same
  USD x devaluation factor) — differencing them cannot resolve a few-%/yr effect
  in one country's 13 years (~2 centuries needed for t=2). SPEC's "single most
  product-relevant result" is therefore UNANSWERABLE by this design; say so.
  WHAT SURVIVES (VA vs benchmark, real TL, full period): **B1 deposits +11.6%/yr
  t=2.36; B2 dollars +7.9 t=2.22** (the essay's hook — significant). NOT
  significant: B6 +9.7 t=1.85, B4 BIST +7.9 t=1.06, **B5 EW +2.7 t=1.10 (momentum
  SELECTION unproven vs equal weight)**, **B3 gold alone +2.3 t=0.51 — altin
  nearly matched the whole apparatus; must appear in the essay, not be omitted.**
  Caveats both ways: naive t-tests, fat tails/autocorrelation => true CIs likely
  WIDER; and underpowered != disproven (52wk regimes can't detect real effects).
  **Forward agenda: pooling across countries (Argentina/Brazil/Egypt) is the only
  route to power on the integration question — vindicates SPEC 8's parameterized
  engine, now a necessity rather than a nice-to-have.**

- 2026-08-24 — **Orthodox-window failure decomposed (essay section 9.7 material).**
  Window 2023-07 -> 2026-07: inflation 41.7%/yr, deposits 67.0% nominal (+17.9%
  real), VA_headline 40.4% nominal (= real ~0), VA_hurdle 42.3%. Cause is
  STRUCTURAL, not signal: with N=3 equal 1/3 slots a sleeve cannot exceed 33%
  from ranking, and under the zero hurdle the hatch never fired — **headline max
  deposit weight was exactly 33% in ALL 161 weeks** (mean 18%). Dual momentum
  with N=3 is a diversification device that mathematically cannot concentrate
  into a single winner; the orthodox regime had exactly one right answer. The
  other ~2/3 sat in sleeves rising in TL but SLOWER than prices — nominal TL
  returns QQQ ~35, INDA ~39, SPY ~38, MCHI ~37, XLE ~25, EFA ~21, EEM ~10, all
  under 41.7% inflation; only deposits (67) and GOLD (~50) beat it. A zero
  threshold cannot distinguish "going up" from "going up fast enough to keep
  purchasing power". **Why the hurdle variant works: in an orthodox-policy regime
  the deposit rate IS a de facto inflation hurdle (67 > 41.7), so RoC > deposit
  RoC implicitly demands beating inflation.** Variant also lifted the ceiling
  (max 100%, >=90% deposits in 15/161 weeks) but ranking held the mean to 36%.
  Mirror image: in 2021-23 the suppressed deposit rate was a POOR inflation proxy
  — but real assets were obviously winning then, so it didn't need to be. Fix is
  not a better signal, it is permitting concentration.

- 2026-08-25 — **"Does the variant do better lately?" — paired test.** Yes in
  point terms, 2024 (+4.4 real pts: -3.5 vs -7.9) and 2025 (+2.0), via the
  claimed mechanism; 2026 YTD slightly behind (-0.9), small persistent cost
  pre-2019 (2015 -0.6, 2016 -1.3). Even PAIRED testing fails to certify:
  strategies correlate 0.9889 overall but are identical in 43% of orthodox
  weeks and differ by a 1/3-portfolio deposit-vs-equity swap in the rest, so
  the difference series is sparse + equity-vol -> orthodox diff +1.49%/yr
  t=0.46 CI[-4.8,+7.8]; full period +0.25%/yr t=0.32. Verdict: variant's case
  is mechanism + Antonacci lineage, not scoreboard (2yr sample that inspired
  the rule can't certify it). Essay: headline numbers, variant in footnote.
  Personal implementation later: USE the variant (theoretically correct rule,
  known cost elsewhere ~fraction of a point).

- 2026-08-25 — **Phase 3: essay draft v1 written** (`essay_draft.md`, ~2,300
  words + 3 figures; new hook chart `results/fig1_faiz_mi_dolar_mi.png`).
  Structure per SPEC 9 updated by the audits: headline-run numbers only;
  significant claims asserted (beat deposits/dollars), unproven ones explicitly
  labeled (selection vs EW, gold, A-B gap "unmeasurable from one country");
  33%-ceiling story as the centerpiece of the limitations section; hurdle
  variant + pre-registration + stats each ONE footnote. Remaining before
  publication: user edit pass (voice), repo/appendix link, optional FXI
  robustness, Turkish version later per SPEC 10.

- 2026-08-25 — Essay: B2 assumption made explicit. B2 is SHY-in-TL per SPEC
  (dollar-holder credited with T-bill yield); "simply dollars" (USDTRY only,
  the actual mom-and-pop practice) ends 1.36x real vs 1.64x, and -13.5%/yr vs
  -9.9%/yr in 2023H2->. Essay section 1 now states the charitable assumption and
  gives the mattress number; benchmark itself unchanged (pre-registered).

- 2026-08-25 — Essay figures made publication-grade (`make_essay_figures.py`):
  fig1 (proper "mı"), fig2_menu_vs_strategy.png, fig3_holdings_timeline.png —
  reader-facing labels only (no Version A/B, no B1..B6 codes, no DEPOSIT_TL-style
  variable names); essay links updated. Notebook lab figures unchanged. Rerun
  the script after any data refresh. Essay copyedits this session: mattress-
  dollar clause, plain-language data footnote, L/N notation removed, "muster"/
  scrutiny sentence rewritten in plain terms.

- 2026-08-25 — Essay voice pass per author direction ("cut the uncles, less
  clever"): 15 edits. Two-uncles opening replaced with plain statement; gendered
  generic saver removed; flattened flourishes (discipline-for-nothing, asterisk-
  paying, dinner-table motif, rotation machine, grandmothers, statistical
  shouting distance, insurance-invoice, humbler-promise, closing rhetorical
  question); section 6 retitled "What the strategy did not do"; "machine" motif
  removed throughout. Body ~2,090 words.

- 2026-08-26 — **Public repo package built** (`public_repo/`, 1.6 MB, for
  GitHub repo `dual-momentum-turkey`): SPEC, study README as STUDY_LOG.md,
  all engine/phase/figure scripts, 3 executed notebooks, results CSVs + essay
  figures, repo README (repro instructions, EVDS key setup, data notes; no
  roadmap promises per author), .gitignore (cache/, .env). Scrubbed: API key
  never in files; one stderr stream with local paths stripped from phase2
  notebook; rescan clean. Awaiting: user creates GitHub repo + push, then fill
  the two essay repo-link placeholders. Essay content edits this session: gold
  2.9x->3.1x (stale phase1 deflator number caught when gold added to fig2),
  2021-23 holdings sentence corrected to actual weights (BIST 15% surprise),
  closing purchasing-power line unpacked, strategy walkthrough expanded, menu
  metaphor removed, orthodox jargon removed, deposit sentence simplified.

- 2026-08-26 — **Public repo LIVE**: github.com/chitown2016/dual-momentum-turkey
  (initial commit pushed from public_repo/, STUDY_LOG refreshed at commit time).
  Essay's four repository references now link to it. Remaining before
  publication: venue choice, CPI-refresh timing call (~Sep 3 print), author
  read-aloud + tax paragraph sign-off. On future pushes: re-copy study README
  to public_repo/STUDY_LOG.md first.

- 2026-08-28 — Notebook headers gained a Terminology block (Version A/B, A-B
  gap, B1-B6 defined inline with SPEC pointer) after author found the taxonomy
  undefined for repo visitors entering via a notebook; markdown-cell edit only,
  outputs untouched; pushed (f107059). Earlier same session: engine hatch
  docstring clarified re SPEC 2-vs-4 signal-currency wording, rebased over
  user's MIT license commit and pushed.

- 2026-08-28 — Author caught an UNBACKED claim in the phase1 notebook ("EM gate
  active as designed" — nothing measured it; blend weights cannot show bindings
  since the two legs can hold MCHI and INDA separately). Added a diagnostic
  cell: ungated top-3 contains both MCHI+INDA in 7.6% (10w) / 9.8% (25w) of
  weeks, clustered 2014/2017/2020 — the gate genuinely binds. Interpretation
  sentence now cites the measurement. Incidental find: notebook has a trailing
  empty markdown cell (likely from a Jupyter open/save) — left alone, but
  position-based cell targeting (cells[-1]) is no longer safe on these
  notebooks; target by content. Re-executed, pushed.

- 2026-08-29 — Notebook interpretations REWRITTEN (author: "rewrite the
  history; too verbose") — phase1 + phase2 summary cells replaced with concise
  post-audit versions (~1/3 length): significance audit now reflected, regime-
  level A-B gap point estimates no longer narrated as findings, orthodox-
  failure mechanics kept with pointer to hurdle variant, stale "exactly the
  pattern predicted" framing removed. Session history remains here in the log;
  summary cells are current-best-statement only. Pushed (77db248).

- 2026-08-29 — **PUBLISHED**: https://miktul.substack.com/p/dual-momentum-for-a-collapsing-currency
  (Substack, public, comments open to everyone, endnote-style notes; live page
  verified). SPEC definition of done MET, ~1 week elapsed vs 3 budgeted.
  INCIDENT during link backfill: repo README.md had been silently DELETED from
  GitHub — the 08-28 terminology sync cp/mv clobbered it and 08-29's `git add
  -A` committed the deletion; restored from initial commit d4c91ce + essay link
  added. Lesson: never route the study-README->STUDY_LOG copy through the repo
  README's filename; sync script needed. Remaining: distribution, then study
  conclusion (ask before archive).

- 2026-08-29 — **Authorship disclosure added** (author flagged AI-detection
  concern pre-Quantocracy; repo SPEC already publicly said "Implementing agent:
  Claude Code" so essay/repo were asymmetric). One-paragraph note added to
  essay Notes (essay_draft.md) + one line in repo README (pushed); user to
  paste the note into the live Substack post. Detector-evasion rewriting
  declined on principle; disclosure chosen as consistent with the piece's
  transparency ethos.

- 2026-08-29 — **Attribution record.** Added when the essay's authorship note
  began pointing readers at this log: earlier entries record several analytical
  turns in passive voice, under-crediting the author. Principal contributions
  of MT (author/PI), beyond the locked SPEC (design, universe, rules, phase
  plan, essay skeleton):
  - Proposed the risk-free momentum hurdle ("we should have compared to
    deposit returns", 08-24) -> the phase-3 robustness variant; then falsified
    the implementing agent's claim that the two-way hatch collapses under it
    ("maybe SHY is passing the filter"), confirmed by the decoupled-lookback
    test.
  - Objected that deposit "low volatility" was a numeraire artifact -> the
    numeraire-dependence finding and the discovery that vol-scaling the signal
    is catastrophic (killing a proposed "fix").
  - Challenged the regime-gap narration ("is it?", 08-24) -> the significance
    audit that demoted all regime-level A-B claims to noise.
  - Asked the orthodox-failure question -> the 33%-ceiling decomposition; the
    mattress-dollars realism point on B2; the flow-vs-stock deposit-series
    identification; spotted gold missing from fig2 (exposing a stale number);
    caught the unbacked EM-gate claim.
  - All editorial direction, publication decisions, EVDS registration, MIT
    license, and the authorship-disclosure decision.
  The implementing agent (Claude Code) built the engine, data layer, backtests,
  diagnostics, figures, drafts, and this log.

## Verdict

(open)
