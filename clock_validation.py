"""
===============================================================================
 CLOCK VALIDATION — check both halftime audits against ESPN ground truth
===============================================================================
 Everything so far used an INFERRED clock. This uses the real one: ESPN
 play-by-play wallclocks give the actual tipoff (first period-1 play) and the
 actual halftime buzzer (last period-2 play) for every game.

 Four questions:
   1. How late do games really tip vs their scheduled time? (the NBA bug)
   2. Where did the published windows actually land relative to the real
      halftime? (how bad was each method)
   3. Re-estimate s(H1) sampling at the REAL halftime break — no inference.
   4. Does that confirm or refute the corrected estimates (WNBA ~0.96,
      NBA ~0.88)?
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
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import wnba_anchor_audit as A                                # noqa: E402
import wnba_reconcile as R                                   # noqa: E402
import nba_anchor_audit as N                                 # noqa: E402

# ESPN abbreviation -> Kalshi ticker code, where they differ
ESPN_NBA = {"GS": "GSW", "NY": "NYK", "SA": "SAS", "NO": "NOP", "UTAH": "UTA",
            "WSH": "WAS", "PHX": "PHX", "NOP": "NOP"}
ESPN_WNBA = {"GS": "GS", "GSV": "GS", "NY": "NY", "LV": "LV", "LA": "LA",
             "CONN": "CONN", "WSH": "WSH", "PHX": "PHX", "SEA": "SEA",
             "MIN": "MIN", "IND": "IND", "DAL": "DAL", "CHI": "CHI",
             "ATL": "ATL", "TOR": "TOR", "POR": "PDX", "PDX": "PDX"}


def load_clocks(path, mapping):
    d = pd.read_csv(os.path.join(REPO, path))
    d = d.dropna(subset=["tip_utc", "half_utc"]).copy()
    for c in ("tip_utc", "half_utc", "sched_utc"):
        d[c] = pd.to_datetime(d[c], utc=True, errors="coerce")
    d["ac"] = d.away.map(lambda x: mapping.get(str(x), str(x)))
    d["hc"] = d.home.map(lambda x: mapping.get(str(x), str(x)))
    # Unit-agnostic: pandas 3 parses these as datetime64[us], so a fixed
    # //10**9 silently divides by 1000x too much and lands in 1976.
    EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
    d["tip_ts"] = (d.tip_utc - EPOCH).dt.total_seconds()
    d["half_ts"] = (d.half_utc - EPOCH).dt.total_seconds()
    d["sched_lag"] = (d.tip_utc - d.sched_utc).dt.total_seconds() / 60
    d["h1_len"] = (d.half_utc - d.tip_utc).dt.total_seconds() / 60
    return d


def report_clocks(d, league, sched_window):
    print(f"\n{league}: real tipoff vs scheduled, and first-half length")
    print(f"   games with a real clock: {len(d)}")
    print(f"   tip LATER than scheduled by: median {d.sched_lag.median():+.1f} "
          f"min  IQR {d.sched_lag.quantile(.25):+.1f} to "
          f"{d.sched_lag.quantile(.75):+.1f}  (10-90pct "
          f"{d.sched_lag.quantile(.10):+.1f} to {d.sched_lag.quantile(.90):+.1f})")
    print(f"   tip -> halftime buzzer: median {d.h1_len.median():.1f} min  "
          f"IQR {d.h1_len.quantile(.25):.1f}-{d.h1_len.quantile(.75):.1f}")
    real = d.sched_lag + d.h1_len
    print(f"   => real halftime sits at scheduled +{real.median():.1f} min "
          f"(IQR {real.quantile(.25):.1f}-{real.quantile(.75):.1f})")
    print(f"   the published window used scheduled +{sched_window}")
    early = (real - sched_window)
    print(f"   so it sampled {early.median():.1f} min BEFORE the buzzer "
          f"(before it in {(early > 0).mean():.0%} of games)")


def fit(p, col, lab):
    c = p.dropna(subset=[col, "pre", "h1"])
    if len(c) < 25:
        return None
    b, se = A.ols(c[col].values, [c.pre.values, c.h1.values], ["pre", "h1"])
    print(f"   {lab:<44} s={b['h1']:.3f} (se {se['h1']:.3f})  "
          f"b(pre)={b['pre']:.3f}  n={len(c)}")
    return b["h1"]


def main():
    # ---------------- NBA ----------------
    print("=" * 76)
    print("NBA")
    print("=" * 76)
    ck = load_clocks("espn_clocks_nba.csv", ESPN_NBA)
    report_clocks(ck, "NBA", 70)
    series, meta = N.build_series()
    m = N.load_master(meta)
    ck["key"] = ck.date.astype(str).str[:4] + "-" + ck.date.astype(str).str[4:6] \
        + "-" + ck.date.astype(str).str[6:8] + "|" + ck.ac + "@" + ck.hc
    m["key"] = m.date.dt.strftime("%Y-%m-%d") + "|" + m.ac + "@" + m.hc
    m = m.merge(ck[["key", "tip_ts", "half_ts", "sched_lag", "h1_len"]],
                on="key", how="inner")
    print(f"\n   panel joined to a real clock: {len(m)} games")
    rows = []
    for _, r in m.dropna(subset=["event"]).iterrows():
        s = series.get(r.event)
        if s is None:
            continue
        rec = {"pre": r.pre, "h1": r.h1, "total": r.total}
        for o in (0, 3, 6, 9, 12):        # minutes past the REAL buzzer
            rec[f"H{o}"] = A.L_at(s, r.half_ts + o * 60)
        rec["pub"] = A.L_at(s, r["T"] + 70 * 60)      # published window
        rec["corr"] = A.L_at(s, r["T"] + 84 * 60)     # audit's corrected guess
        rows.append(rec)
    p = pd.DataFrame(rows)
    b0, se0 = A.ols(p.total.values, [p.pre.values, p.h1.values], ["pre", "h1"])
    print(f"\n   {'REALIZED benchmark (efficient value)':<44} "
          f"s={b0['h1']:.3f} (se {se0['h1']:.3f})")
    fit(p, "pub", "published: scheduled tip +70")
    fit(p, "corr", "audit's inferred correction: scheduled +84")
    for o in (0, 3, 6, 9, 12):
        fit(p, f"H{o}", f"TRUE halftime buzzer +{o} min")

    # ---------------- WNBA ----------------
    print("\n" + "=" * 76)
    print("WNBA")
    print("=" * 76)
    ckw = load_clocks("espn_clocks_wnba.csv", ESPN_WNBA)
    print(f"\nWNBA: real tipoff vs scheduled, and first-half length")
    print(f"   games with a real clock: {len(ckw)}")
    print(f"   tip later than scheduled: median {ckw.sched_lag.median():+.1f} min")
    print(f"   tip -> halftime buzzer: median {ckw.h1_len.median():.1f} min "
          f"(IQR {ckw.h1_len.quantile(.25):.1f}-{ckw.h1_len.quantile(.75):.1f})")
    cache = "/tmp/claude-1000/wnba_L.pkl"
    ser = pickle.load(open(cache, "rb")) if os.path.exists(cache) \
        else A.build_L_series("/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite")
    bref = R.bref_totals(R.BREF)
    panel = pd.read_csv(A.PANEL)
    pre_by = dict(zip(panel.event_ticker, panel.L_pre))
    ckw["k2"] = (ckw.date.astype(str).str[:4] + "-" + ckw.date.astype(str).str[4:6]
                 + "-" + ckw.date.astype(str).str[6:8] + "|" + ckw.ac + ckw.hc)
    cw = {r.k2: r for _, r in ckw.iterrows()}
    rows = []
    for e, s in ser.items():
        hit = R.bref_lookup(e, bref)
        if not hit or e not in pre_by:
            continue
        total, h1, n_ot = hit
        key = f"{R.event_date(e)}|{e.rsplit('-', 1)[-1][7:]}"
        c = cw.get(key)
        if c is None:
            continue
        a1 = A.convergence_anchor(s, total)
        bad = np.where((s.L - total).abs().values > 2.5)[0]
        a2 = int(s.ts.values[bad[-1] + 1]) if len(bad) and bad[-1] + 1 < len(s) else None
        rec = {"pre": pre_by[e], "h1": h1, "total": total,
               "settled_vs_half": (a2 - c.half_ts) / 60.0 if a2 else np.nan}
        rec["pub"] = A.L_at(s, a1 - 58 * 60) if a1 else np.nan
        rec["settled"] = A.L_at(s, a2 - 58 * 60) if a2 else np.nan
        for o in (0, 3, 6, 9, 12):
            rec[f"H{o}"] = A.L_at(s, int(c.half_ts) + o * 60)
        rows.append(rec)
    q = pd.DataFrame(rows)
    print(f"   panel joined to a real clock: {len(q)} games")
    b1, se1 = A.ols(q.total.values, [q.pre.values, q.h1.values], ["pre", "h1"])
    print(f"\n   {'REALIZED benchmark (efficient value)':<44} "
          f"s={b1['h1']:.3f} (se {se1['h1']:.3f})")
    fit(q, "pub", "published: convergence anchor -58")
    fit(q, "settled", "audit's corrected settled anchor -58")
    for o in (0, 3, 6, 9, 12):
        fit(q, f"H{o}", f"TRUE halftime buzzer +{o} min")
    sv = q.settled_vs_half.dropna()
    if len(sv):
        print(f"\n   settled anchor sits {sv.median():.0f} min after the real "
              f"halftime buzzer (a WNBA second half is ~55-60 min, so ~55-60 "
              f"means it really is finding game end)")
    return p, q


if __name__ == "__main__":
    main()
