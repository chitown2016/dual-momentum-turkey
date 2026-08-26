"""
EVDS (TCMB) data layer — Phase 2 (SPEC 3 TL-side sleeves).

API: evds3.tcmb.gov.tr, base path /igmevdsms-dis/, key in HTTP header "key".
(evds2 is dead — redirects to evds3. Endpoint discovered from evdspy source.)
Key: EVDS_API_KEY in .env next to this file.

Series (verified against the evds3 catalog 2026-08-22):
  TP.TRY.MT02      weekly Friday, from 2002-01-04 — "Up to 3 Months (TRY
                   Deposits, Flow, %)" == SPEC's deposit sleeve rate.
                   (Robustness alt: TP.TRYTAS.MT02, retail savings-only, 2012->.
                   Stock-data twin lives in bie_mt210ags — NOT used.)
  TP.TUKFIY2025.GENEL  monthly CPI (TUFE) general index, 2025=100, backcast to
                   2005-01 == SPEC deflator. (TUIK rebased in 2026; the old
                   2003=100 series TP.FG.J0 is FROZEN at 2026-01 — do not use.)
  TP.DK.USD.A.YTL  daily USDTRY buying;  TP.DK.USD.S.YTL selling; mid = avg.
  TP.MK.G.BILESIK  daily BIST-100 RETURN index (XU100 total return), 1997-> ==
                   SPEC's preferred XU100T (dividends included; F=price twin).
"""

import io
import json
import os
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"

SERIES = {
    "deposit_flow_3m": "TP.TRY.MT02",
    "cpi": "TP.TUKFIY2025.GENEL",
    "usdtry_buy": "TP.DK.USD.A.YTL",
    "usdtry_sell": "TP.DK.USD.S.YTL",
    "bist100_tr": "TP.MK.G.BILESIK",
}


def _api_key():
    env = os.path.join(HERE, ".env")
    if os.path.exists(env):
        for line in io.open(env, encoding="utf-8"):
            if line.strip().startswith("EVDS_API_KEY="):
                return line.strip().split("=", 1)[1]
    key = os.environ.get("EVDS_API_KEY")
    if not key:
        raise RuntimeError("EVDS_API_KEY not found in .env or environment")
    return key


def _fetch_window(series_code, start, end):
    url = (BASE + "series=" + series_code + "&startDate=" + start
           + "&endDate=" + end + "&type=json")
    req = urllib.request.Request(
        url, headers={"key": _api_key(), "User-Agent": "Mozilla/5.0"})
    j = json.load(urllib.request.urlopen(req, timeout=120))
    col = series_code.replace(".", "_")
    return [(it["Tarih"], it.get(col)) for it in j["items"]]


def fetch(series_code, start="01-01-2002", end="31-12-2030"):
    """One series -> pd.Series indexed by timestamp. Dates DD-MM-YYYY.

    The evds3 API silently caps a response near 1000 observations, so daily
    and weekly histories are fetched in 2-year windows and concatenated."""
    y0 = int(start.split("-")[2])
    y1 = min(int(end.split("-")[2]), 2030)
    rows = []
    for ya in range(y0, y1 + 1, 2):
        a = start if ya == y0 else "01-01-%d" % ya
        b = end if ya + 1 >= y1 else "31-12-%d" % (ya + 1)
        rows += _fetch_window(series_code, a, b)
    s = pd.Series(dict(rows), name=series_code)
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        raise RuntimeError("no data for " + series_code)
    # Tarih is DD-MM-YYYY for daily/weekly, YYYY-M for monthly
    if "-" in s.index[0] and len(s.index[0].split("-")[0]) == 4:
        idx = pd.PeriodIndex(s.index, freq="M").to_timestamp()
    else:
        idx = pd.to_datetime(s.index, format="%d-%m-%Y")
    s.index = idx
    return s[~s.index.duplicated()].sort_index()


def load(name, refresh=False):
    """Cached loader for a SERIES entry ('usdtry' -> mid of buy/sell)."""
    path = os.path.join(CACHE_DIR, "evds_" + name + ".pkl")
    if os.path.exists(path) and not refresh:
        return pd.read_pickle(path)
    if name == "usdtry":
        s = (fetch(SERIES["usdtry_buy"]) + fetch(SERIES["usdtry_sell"])) / 2
        s.name = "USDTRY_mid"
    else:
        s = fetch(SERIES[name])
    os.makedirs(CACHE_DIR, exist_ok=True)
    s.to_pickle(path)
    return s


if __name__ == "__main__":
    import sys
    refresh = "--refresh" in sys.argv
    for name in ["deposit_flow_3m", "cpi", "usdtry", "bist100_tr"]:
        s = load(name, refresh=refresh)
        print("%-16s %s -> %s  n=%d  last=%.4f"
              % (name, s.index[0].date(), s.index[-1].date(), len(s),
                 s.iloc[-1]))
