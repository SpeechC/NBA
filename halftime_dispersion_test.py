"""
===============================================================================
 PER-GAME DISPERSION TEST — who wins when the model and the market disagree?
===============================================================================
 The audits established the AVERAGE: WNBA prices banked H1 at ~1.0 (efficient),
 NBA at ~0.85. A slope is not a per-game statement — dispersion could hide
 mispriced games that net out. This tests it directly.

 E = leave-one-out fit of total ~ pre + H1 (the deployed rule's form).
 L = market line at the TRUE halftime buzzer +3 min (ESPN clocks).
 Regress (total - L) on (E - L):
   kappa ~ 1  -> disagreements are market error (model wins; tradeable)
   kappa ~ 0  -> disagreements are model blindness (market knows more)
   kappa < 0  -> the LINE's deviation from naive fair value is directionally
                 informative and UNDERWEIGHTED: the outcome continues past L
                 in the market's own direction (fair ~ L + |k|*(L-E)).

 RESULT (2026-08-25):
   WNBA  kappa = -1.02 (se .32, t=-3.2), month-FE -1.00 (t=-3.1),
         halves -0.71/-1.34, driven by the model-says-OVER side (-1.12).
         Tail |E-L|>5 (14% of games): the MODEL side hits 38% -- the market
         side hits 62%. The deployed fade rule bets exactly backwards here.
   NBA   kappa = +0.25 (se .24) -- noise; sign flips across halves
         (-0.33/+0.67); no reliable per-game signal in either direction.

 Noise biases work AGAINST the WNBA finding: LOO-E noise attenuates kappa
 toward 0, and L measurement noise pushes it POSITIVE (shared -u term).
 Nonetheless: one season, n=95, third candidate pattern found on this data
 today -- EXPLORATORY. Promoted only via PREREG_wnba_line_momentum.md's
 forward shadow test. Read-only script.
===============================================================================
"""
import pickle
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/dpope/projects/nba_entropy_replication")
import wnba_anchor_audit as A                                # noqa: E402
import wnba_reconcile as R                                   # noqa: E402
import clock_validation as CV                                # noqa: E402
import nba_anchor_audit as N                                 # noqa: E402


def loo_E(df):
    X = np.column_stack([np.ones(len(df)), df.pre.values, df.h1.values])
    y = df.total.values
    E = np.empty(len(df))
    for i in range(len(df)):
        m = np.ones(len(df), bool)
        m[i] = False
        b, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        E[i] = X[i] @ b
    return E


def battery(d, league):
    d = d.dropna(subset=["L", "pre", "h1", "total", "date"]) \
         .sort_values("date").reset_index(drop=True)
    d["E"] = loo_E(d)
    d["dev"] = d.E - d.L
    d["err"] = d.total - d.L
    d["month"] = pd.to_datetime(d.date).dt.month
    print(f"\n=== {league}  n={len(d)} ===")
    print(f"  |E-L|: median {d.dev.abs().median():.2f} pts, "
          f">3 {(d.dev.abs() > 3).mean():.0%}, >5 {(d.dev.abs() > 5).mean():.0%}")
    b, se = A.ols(d.err.values, [d.dev.values], ["dev"])
    print(f"  kappa raw      {b['dev']:+.3f} (se {se['dev']:.3f}, "
          f"t={b['dev'] / se['dev']:+.1f})")
    mm = pd.get_dummies(d.month, drop_first=True).astype(float)
    Xk = np.column_stack([np.ones(len(d)), d.dev.values, mm.values])
    bb, *_ = np.linalg.lstsq(Xk, d.err.values, rcond=None)
    res = d.err.values - Xk @ bb
    ss = np.sqrt(np.diag(res @ res / (len(d) - Xk.shape[1])
                         * np.linalg.pinv(Xk.T @ Xk)))
    print(f"  kappa month-FE {bb[1]:+.3f} (se {ss[1]:.3f}, t={bb[1] / ss[1]:+.1f})")
    h = len(d) // 2
    for lab, g in (("first half", d.iloc[:h]), ("second half", d.iloc[h:])):
        b2, s2 = A.ols(g.err.values, [g.dev.values], ["dev"])
        print(f"  kappa {lab:<12} {b2['dev']:+.3f} (se {s2['dev']:.3f})  n={len(g)}")
    tail = d[d.dev.abs() > 5]
    if len(tail) >= 8:
        hit = np.mean(np.sign(tail.err) == np.sign(tail.dev))
        print(f"  tail |E-L|>5: n={len(tail)}, model-side hit {hit:.0%}")
    return d


def main():
    ser = pickle.load(open("/tmp/claude-1000/wnba_L.pkl", "rb"))
    bref = R.bref_totals(R.BREF)
    panel = pd.read_csv(A.PANEL)
    pre_by = dict(zip(panel.event_ticker, panel.L_pre))
    ckw = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ds = ckw.date.astype(str)
    ckw["k2"] = (ds.str[:4] + "-" + ds.str[4:6] + "-" + ds.str[6:8]
                 + "|" + ckw.ac + ckw.hc)
    cw = {r.k2: r for _, r in ckw.iterrows()}
    rows = []
    for e in ser:
        hit = R.bref_lookup(e, bref)
        if not hit or e not in pre_by:
            continue
        c = cw.get(f"{R.event_date(e)}|{e.rsplit('-', 1)[-1][7:]}")
        if c is None:
            continue
        rows.append({"date": pd.Timestamp(R.event_date(e)), "pre": pre_by[e],
                     "h1": hit[1], "total": hit[0],
                     "L": A.L_at(ser[e], float(c.half_ts) + 180)})
    battery(pd.DataFrame(rows), "WNBA 2026 (true clock, buzzer+3)")

    series, meta = N.build_series()
    m = N.load_master(meta)
    ck = CV.load_clocks("espn_clocks_nba.csv", CV.ESPN_NBA)
    ds = ck.date.astype(str)
    ck["key"] = (ds.str[:4] + "-" + ds.str[4:6] + "-" + ds.str[6:8]
                 + "|" + ck.ac + "@" + ck.hc)
    m["key"] = m.date.dt.strftime("%Y-%m-%d") + "|" + m.ac + "@" + m.hc
    m = m.merge(ck[["key", "half_ts"]], on="key", how="inner") \
         .dropna(subset=["event"])
    m["L"] = [A.L_at(series[r.event], r.half_ts + 180)
              if r.event in series else np.nan for _, r in m.iterrows()]
    battery(m[["date", "L", "pre", "h1", "total"]],
            "NBA Oct-Dec 2025 (true clock, buzzer+3)")


if __name__ == "__main__":
    main()
