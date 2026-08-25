"""
===============================================================================
 #2 — ATTENTION DILUTION: does pricing quality degrade on busy nights?
===============================================================================
 This tests H0 directly, the meta-hypothesis under the whole target list:
 a market prices information in proportion to the ATTENTION it receives.
 If that is true, the same league's boards should be priced WORSE on nights
 with many concurrent games than on nights with few — because the same pool
 of attention is spread thinner.

 It matters more than any single edge, because it says WHEN to look rather
 than only where.

 Measures, ordered by statistical power (the binding constraint all day):

   1. SPREAD vs concurrency        — thousands of bar-minutes; spread is the
                                     market's own attention signal (the law
                                     from target 3)
   2. VOLUME vs concurrency        — same power; is flow diluted or just split
   3. RUNG CALIBRATION vs concur.  — 8,758 settled rungs; the payoff measure:
                                     are prices actually less accurate
   4. LINE FORECAST ERROR          — |total - pregame L|; honest but weak,
                                     since game noise (sd ~21) swamps it

 Concurrency is measured two ways: games on the same DATE, and games whose
 tip is within +/-2h (true overlap, using the ESPN clocks).

 Read-only.
===============================================================================
"""
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402
import wnba_reconcile as R                                   # noqa: E402
import clock_validation as CV                                # noqa: E402

FULLDB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"


def concurrency():
    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ck["dstr"] = ck.date.astype(str)
    M = {f"{i:02d}": m for i, m in enumerate(
        ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
         "OCT", "NOV", "DEC"])}
    ck["key"] = (ck.dstr.str[2:4] + ck.dstr.str[4:6].map(M)
                 + ck.dstr.str[6:8] + ck.ac + ck.hc)
    ck["n_date"] = ck.groupby("dstr").key.transform("size")
    ov = []
    for _, r in ck.iterrows():
        ov.append(int(((ck.tip_ts - r.tip_ts).abs() <= 2 * 3600).sum()))
    ck["n_overlap"] = ov
    return ck[["key", "dstr", "tip_ts", "half_ts", "n_date", "n_overlap"]]


def cluster_ci(df, val, grp, rng, B=3000):
    g = df[grp].unique()
    by = {k: df.loc[df[grp] == k, val].values for k in g}
    out = [np.concatenate([by[x] for x in rng.choice(g, len(g), True)]).mean()
           for _ in range(B)]
    return np.percentile(out, [2.5, 97.5])


def main():
    ck = concurrency()
    print(f"games with clocks {len(ck)}; games per date: median "
          f"{ck.n_date.median():.0f}, range {ck.n_date.min()}-{ck.n_date.max()}")
    print(f"  concurrent (tip within 2h): median {ck.n_overlap.median():.0f}, "
          f"max {ck.n_overlap.max()}\n")

    con = sqlite3.connect(FULLDB)
    cd = pd.read_sql(
        "select ticker, event_ticker e, end_period_ts ts, yes_bid_close b, "
        "yes_ask_close a, volume v from candles where period_interval=1 "
        "and ticker like 'KXWNBATOTAL%'", con)
    mk = pd.read_sql("select ticker, result from markets where result in "
                     "('yes','no') and ticker like 'KXWNBATOTAL%'", con)
    con.close()
    cd = cd.dropna(subset=["b", "a"])
    cd["mid"] = (cd.b + cd.a) / 200.0
    cd["sp"] = cd.a - cd.b
    cd["key"] = cd.e.str.split("-").str[1]
    d = cd.merge(ck, on="key", how="inner")
    d = d[(d.mid > 0.2) & (d.mid < 0.8)]
    d["phase"] = np.where(d.ts < d.tip_ts - 60, "pregame", "in-game")
    d["busy"] = np.where(d.n_overlap >= 3, "busy (3+)", "quiet (1-2)")
    rng = np.random.default_rng(11)

    print("1. SPREAD vs CONCURRENCY  (the market's own attention signal)")
    print(f"   {'phase':>9} {'concurrency':>13} {'bars':>8} {'med spread':>11} "
          f"{'mean spread':>12}")
    for ph in ["pregame", "in-game"]:
        for lab in ["quiet (1-2)", "busy (3+)"]:
            s = d[(d.phase == ph) & (d.busy == lab)]
            if len(s) < 200:
                continue
            print(f"   {ph:>9} {lab:>13} {len(s):>8,} {s.sp.median():>10.1f}c "
                  f"{s.sp.mean():>11.2f}c")
    for ph in ["pregame", "in-game"]:
        s = d[d.phase == ph]
        if len(s) < 500:
            continue
        b, se = A.ols(s.sp.values, [s.n_overlap.values], ["n"])
        print(f"   {ph}: spread ~ n_concurrent  coef {b['n']:+.3f}c per extra "
              f"game (se {se['n']:.3f})")

    print("\n2. VOLUME vs CONCURRENCY  (is flow diluted, or just split?)")
    for ph in ["pregame", "in-game"]:
        for lab in ["quiet (1-2)", "busy (3+)"]:
            s = d[(d.phase == ph) & (d.busy == lab)]
            if len(s) < 200:
                continue
            pg = s.groupby("key").v.sum()
            print(f"   {ph:>9} {lab:>13} median {pg.median():>9,.0f} "
                  f"contracts/game")

    print("\n3. RUNG CALIBRATION vs CONCURRENCY  (the payoff measure)")
    s = d.merge(mk, on="ticker", how="inner")
    s["win"] = (s.result == "yes").astype(float)
    pre = s[s.phase == "pregame"].copy()
    idx = pre.groupby("ticker").ts.idxmax()          # last pregame quote/rung
    q = pre.loc[idx].copy()
    q["err"] = q.win - q.mid
    print(f"   settled rungs with a last-pregame quote: {len(q):,}")
    print(f"   {'concurrency':>13} {'rungs':>7} {'games':>6} {'mean err':>10} "
          f"{'|err|':>8} {'95% CI on err':>22}")
    for lab in ["quiet (1-2)", "busy (3+)"]:
        t = q[q.busy == lab]
        if len(t) < 50:
            continue
        lo, hi = cluster_ci(t, "err", "key", rng)
        print(f"   {lab:>13} {len(t):>7,} {t.key.nunique():>6} "
              f"{t.err.mean():>+10.4f} {t.err.abs().mean():>8.4f} "
              f"[{lo:+.4f},{hi:+.4f}]")
    b, se = A.ols(q.err.abs().values, [q.n_overlap.values], ["n"])
    print(f"   |err| ~ n_concurrent: coef {b['n']:+.4f} per extra game "
          f"(se {se['n']:.4f}, t={b['n']/se['n']:+.1f})")

    print("\n4. LINE FORECAST ERROR vs CONCURRENCY  (weak by construction)")
    bref = R.bref_totals(R.BREF)
    panel = pd.read_csv(A.PANEL)
    pre_by = {}
    for e, p in zip(panel.event_ticker, panel.L_pre):
        dt = R.event_date(e)
        if dt:
            pre_by[e.rsplit("-", 1)[-1]] = p
    rows = []
    for _, r in ck.iterrows():
        pl = pre_by.get(r.key)
        hit = R.bref_lookup("KXWNBATOTAL-" + r.key, bref)
        if pl is None or not hit:
            continue
        rows.append({"key": r.key, "n": r.n_overlap,
                     "err": abs(hit[0] - pl)})
    f = pd.DataFrame(rows)
    if len(f) > 30:
        print(f"   games with a pregame line and a final: {len(f)}")
        for lab, t in (("quiet (1-2)", f[f.n <= 2]), ("busy (3+)", f[f.n >= 3])):
            if len(t) < 10:
                continue
            print(f"   {lab:>13} n={len(t):>3}  mean |total - L_pre| "
                  f"{t.err.mean():.2f} pts")
        b, se = A.ols(f.err.values, [f.n.values], ["n"])
        print(f"   |error| ~ n_concurrent: {b['n']:+.3f} pts per extra game "
              f"(se {se['n']:.3f})")


if __name__ == "__main__":
    main()
