"""
===============================================================================
 NBA HALFTIME FINDING — ADVERSARIAL TIMING AUDIT
===============================================================================
 Companion to wnba_anchor_audit.py. The WNBA finding died because its halftime
 was located by convergence anchoring (no tip times exist for the WNBA), which
 sampled the ladder BEFORE tipoff in most games. The NBA does not use that
 method: PREREG_kalshi_halftime.md s1 takes L nearest T+70min within
 [T+63, T+77], where T is `tipoff_ts`.

 But `tipoff_source` is 'schedule', and NBA games tip after their scheduled
 time. If T is the scheduled time, T+70 sits ~10 minutes early — in late Q2
 rather than the break — and s is biased DOWN. The prereg's own attenuation
 caveat guesses exactly this ("true s is plausibly 0.75-0.85 rather than
 0.63-0.74"). This measures where s actually stabilises.

 INPUTS MATTER: the first pass at this used kalshi_halftime_rows.csv, whose h1
 column is the bad HALFTIME_H/R line-like object the prereg itself caught and
 discarded (sd 5.9, corr 0.13 with the total). This uses true H1 = 1Q+2Q both
 sides from the master, and checks the realized benchmark lands near 1.0
 before interpreting anything.

 Read-only.
===============================================================================
"""
import os
import pickle
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402
from prepare_data import CSV, season_label                   # noqa: E402

CANDLES = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_candles.sqlite"
TOTALS = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite.bak-20260823"
CACHE = "/tmp/claude-1000/nba_L.pkl"
WINDOW = ("2025-10-20", "2025-12-23")      # the candle capture's span
PUB_OFFSET = 70

CODE = {"Atlanta": "ATL", "Boston": "BOS", "Brooklyn": "BKN",
        "Charlotte": "CHA", "Chicago": "CHI", "Cleveland": "CLE",
        "Dallas": "DAL", "Denver": "DEN", "Detroit": "DET",
        "Golden State": "GSW", "Houston": "HOU", "Indiana": "IND",
        "LA Clippers": "LAC", "Los Angeles Clippers": "LAC",
        "LA Lakers": "LAL", "Los Angeles Lakers": "LAL",
        "Los Angeles": "LAL", "Memphis": "MEM", "Miami": "MIA",
        "Milwaukee": "MIL", "Minnesota": "MIN", "New Orleans": "NOP",
        "New York": "NYK", "Oklahoma City": "OKC", "Orlando": "ORL",
        "Philadelphia": "PHI", "Phoenix": "PHX", "Portland": "POR",
        "Sacramento": "SAC", "San Antonio": "SAS", "Toronto": "TOR",
        "Utah": "UTA", "Washington": "WAS"}


def build_series(cache=CACHE):
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    con = sqlite3.connect(CANDLES)
    df = pd.read_sql("select event_ticker e, end_period_ts t, strike_label k, "
                     "yes_bid_close b, yes_ask_close a from candles where "
                     "period_interval=1 and strike_label is not null", con)
    meta = pd.read_sql("select distinct event_ticker e, away_team, home_team, "
                       "game_date from markets", con)
    con.close()
    df = df.dropna(subset=["b", "a"])
    df["mid"] = (df.b + df.a) / 200.0
    series = {}
    for e, g in df.groupby("e"):
        rows = [(t, A.median_cross(gg.k.values, gg.mid.values))
                for t, gg in g.groupby("t")]
        rows = [(t, L) for t, L in rows if np.isfinite(L)]
        if len(rows) > 30:
            series[e] = pd.DataFrame(rows, columns=["ts", "L"]).sort_values("ts")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump((series, meta), open(cache, "wb"))
    return series, meta


def load_master(meta):
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d = d[(d.date >= WINDOW[0]) & (d.date <= WINDOW[1])].copy()
    for c in ("1Q_H", "2Q_H", "1Q_R", "2Q_R", "PTS_H", "PTS_R",
              "CLOSING TOTAL_H"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["h1"] = d["1Q_H"] + d["2Q_H"] + d["1Q_R"] + d["2Q_R"]   # TRUE first half
    d["total"] = d["PTS_H"] + d["PTS_R"]
    d["pre"] = d["CLOSING TOTAL_H"]
    d["ac"], d["hc"] = d["TEAM_R"].map(CODE), d["TEAM_H"].map(CODE)
    d = d.dropna(subset=["h1", "total", "pre", "ac", "hc"])
    meta["key"] = (meta.game_date.astype(str) + "|" + meta.away_team + "@"
                   + meta.home_team)
    e_by = dict(zip(meta.key, meta.e))
    d["event"] = (d.date.dt.strftime("%Y-%m-%d") + "|" + d.ac + "@"
                  + d.hc).map(e_by)
    con = sqlite3.connect(TOTALS)
    tp = pd.read_sql("select distinct event_ticker e, tipoff_ts from markets "
                     "where tipoff_ts is not null", con)
    con.close()
    d["T"] = d.event.map(dict(zip(tp.e, tp.tipoff_ts)))
    return d


def settled_end(s, total, tol=2.5):
    bad = np.where((s.L - total).abs().values > tol)[0]
    if len(bad) == 0 or bad[-1] + 1 >= len(s):
        return None
    return int(s.ts.values[bad[-1] + 1])


def main():
    series, meta = build_series()
    d = load_master(meta)
    print(f"[nba] {len(d)} master games in the candle window; joined to an "
          f"event: {d.event.notna().sum()}")
    print(f"[nba] TRUE H1: sd {d.h1.std():.1f}, corr with total "
          f"{np.corrcoef(d.h1, d.total)[0, 1]:.3f}   "
          f"[the discarded HALFTIME_H/R column: sd 5.9, corr 0.13]")

    offs = list(range(45, 126, 5)) + list(range(68, 96, 2))
    offs = sorted(set(offs))
    rows = []
    for _, r in d.dropna(subset=["event", "T"]).iterrows():
        s = series.get(r.event)
        if s is None:
            continue
        end = settled_end(s, r.total)
        rec = {"pre": r.pre, "h1": r.h1, "total": r.total,
               "sched_to_end": (end - r["T"]) / 60.0 if end else np.nan}
        for o in offs:
            rec[f"T{o}"] = A.L_at(s, r["T"] + o * 60)
        if end:
            for o in (65, 75, 85):
                rec[f"E{o}"] = A.L_at(s, end - o * 60)
        rows.append(rec)
    p = pd.DataFrame(rows)
    print(f"[nba] {len(p)} games with a ladder series\n")

    b0, se0 = A.ols(p.total.values, [p.pre.values, p.h1.values], ["pre", "h1"])
    print("A. EFFICIENT BENCHMARK — must land near 1.0 or the inputs are wrong")
    print(f"   realized s' = {b0['h1']:.3f} (se {se0['h1']:.3f})   "
          f"[prereg s7 used 1.001]\n")

    def fit(col):
        c = p.dropna(subset=[col, "pre", "h1"])
        if len(c) < 25:
            return None
        b, se = A.ols(c[col].values, [c.pre.values, c.h1.values], ["pre", "h1"])
        return len(c), b["h1"], se["h1"], b["pre"]

    print("B. OFFSET SWEEP FROM THE SCHEDULED TIP")
    print(f"   {'offset':>8} {'n':>5} {'s(H1)':>8} {'se':>7} {'b(pre)':>8} "
          f"{'vs 1.0':>9}")
    best = None
    for o in offs:
        r = fit(f"T{o}")
        if not r:
            continue
        n, s, se, bp = r
        tag = "  <-- PUBLISHED" if o == PUB_OFFSET else ""
        print(f"   {'T+' + str(o):>8} {n:>5} {s:>8.3f} {se:>7.3f} {bp:>8.3f} "
              f"{(s - 1.0) / se:>+8.1f}s{tag}")
        if best is None or s > best[1]:
            best = (o, s, se)
    print(f"\n   peak: T+{best[0]}, s={best[1]:.3f} (se {best[2]:.3f})")

    print("\nC. IS THE SCHEDULED TIP THE REAL TIP?")
    print(f"   scheduled tip -> settled game end: median "
          f"{p.sched_to_end.median():.0f} min (IQR "
          f"{p.sched_to_end.quantile(.25):.0f}-"
          f"{p.sched_to_end.quantile(.75):.0f}); an NBA game runs ~138, so the "
          f"schedule leads the real tip by ~{p.sched_to_end.median() - 138:.0f} min")

    print("\nD. END-ANCHORED CROSS-CHECK (does not use the tip at all)")
    for o in (65, 75, 85):
        r = fit(f"E{o}")
        if r:
            print(f"   L at end-{o:<3} s={r[1]:.3f} (se {r[2]:.3f})  "
                  f"b(pre)={r[3]:.3f}  n={r[0]}")

    print("\nE. DOES THE SURVIVING GAP CLEAR IN-GAME FRICTION?")
    print("   prereg s3: median spread 15c at ~0.35 pt/c -> round trip ~5 pts")
    for o, lab in ((PUB_OFFSET, f"PUBLISHED T+{PUB_OFFSET}"),
                   (best[0], f"CORRECTED T+{best[0]}")):
        c = p.dropna(subset=[f"T{o}", "pre", "h1"]).copy()
        eff = b0["const"] + b0["pre"] * c.pre + b0["h1"] * c.h1
        dev = (c[f"T{o}"] - eff).abs()
        print(f"   {lab:<18} median |dev| {dev.median():.2f} pts   "
              f">5pts {(dev > 5).mean():.0%}   >7pts {(dev > 7).mean():.0%}   "
              f"n={len(c)}")
    print("   [prereg reported median 3.26, 27% >5, 15% >7 — at the biased "
          "offset, and in-sample against a fitted rule]")
    return p


if __name__ == "__main__":
    main()
