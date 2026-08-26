# dual-momentum-turkey

Backtest and full audit trail for the essay **"Dual Momentum for a Collapsing
Currency: what rules-based allocation would have done for a Turkish saver,
2013–2026"** *(link added at publication)*.

A weekly dual-momentum strategy (Antonacci-style relative ranking + absolute
filter, per Quantpedia's May 2026 "Active Dual Momentum GTAA") applied to the
assets a Turkish retail investor can actually hold — ten USD ETFs plus rolled
TL time deposits and the BIST-100 total-return index — with all results
reported in three numeraires: nominal TL, **CPI-deflated real TL (headline)**,
and USD.

## Pre-registration

The design was frozen before any backtest ran: universe, parameters
(lookbacks 10 and 25 weeks, top-3 selection, weekly Wednesday), costs, and
reporting conventions are locked in [`SPEC.md`](SPEC.md). The dated working
log, including every finding and every rule change tried after seeing
results (each labeled as such), is [`STUDY_LOG.md`](STUDY_LOG.md). The one
post-hoc variant (the risk-free momentum hurdle) lives in
[`phase3_robustness_deposit_hurdle.py`](phase3_robustness_deposit_hurdle.py)
with its provenance stated in the module docstring; it is reported as a
robustness appendix, never as the headline.

## Layout

| file | what it is |
|---|---|
| `SPEC.md` | the pre-registration — read this first |
| `STUDY_LOG.md` | dated audit trail of the whole study |
| `engine.py` | the strategy engine (country-parameterized: universe, hatch, gate, costs are inputs) |
| `data_evds.py` | TCMB EVDS data layer (deposit rates, USDTRY, BIST-100 TR, CPI) |
| `phase0_validation.py` / `.ipynb` | validation gate: reproduces Quantpedia's 9-ETF result before any Turkish data enters; permanent regression test |
| `bridge_ablation.py` | one-deviation-at-a-time ladder from the Quantpedia setup to the implementable universe |
| `phase1_version_b.py` / `.ipynb` | the implementable USD-ETF portfolio, tri-numeraire |
| `phase2_version_a.py` / `.ipynb` | the full portfolio including the TL layer; benchmarks B1–B6; the A−B gap |
| `phase3_robustness_deposit_hurdle.py` | post-hoc robustness variant (labeled) |
| `make_essay_figures.py` | regenerates the essay's figures |
| `results/` | stats tables (CSV, per numeraire), regime and gap tables, weekly weight audit CSVs, figures |

## Reproducing

Python with pandas, numpy, matplotlib, yfinance. Turkish data comes from the
central bank's free EVDS API — register at evds3.tcmb.gov.tr, take the API
key from your profile page, and put `EVDS_API_KEY=<key>` in a `.env` file
next to the scripts (never commit it).

```
python phase0_validation.py --refresh   # validation gate (must PASS)
python phase1_version_b.py
python phase2_version_a.py
python phase3_robustness_deposit_hurdle.py
python make_essay_figures.py
```

Downloads are cached in `cache/` (gitignored); pass `--refresh` to re-pull.
Real-TL results end at the last published CPI month.

## Data notes

- Deposit rate: `TP.TRY.MT02` — weighted average on newly opened TL deposits
  up to 3 months (flow, weekly). CPI: `TP.TUKFIY2025.GENEL` (2025=100,
  backcast to 2005; the old 2003=100 series froze at 2026-01 after TÜİK's
  rebase). BIST: `TP.MK.G.BILESIK` (total return). USDTRY: mid of
  `TP.DK.USD.A.YTL` / `TP.DK.USD.S.YTL`.
- The evds3 API caps responses near 1,000 rows; `data_evds.py` fetches in
  2-year chunks.
- US ETF prices: Yahoo Finance dividend-adjusted closes.

Nothing here is investment or tax advice.
