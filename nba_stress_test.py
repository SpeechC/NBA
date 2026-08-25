"""
===============================================================================
 NBA 0.85 UNDER-REACTION — FULL ADVERSARIAL STRESS TEST
===============================================================================
 The WNBA finding died under this battery; the NBA's survived a lighter one.
 This applies the same pressure. Each section is a way the 0.85 could be an
 artifact rather than a market fact.

 A. BENCHMARK PRECISION. s is judged against "efficient ~1.0", estimated on
    one season. Re-estimate on all 8 master seasons: if the true efficient
    value is 0.95, a 0.85 is far less impressive than against 1.07.

 B. BLOWOUT DYNAMICS — the most dangerous alternative. The naive benchmark
    conditions only on (pre, H1). The MARKET can also see the halftime
    MARGIN, and blowouts collapse scoring (starters sit, clock runs). If the
    market correctly prices that and the naive model cannot, the market's
    lower H1 loading is CORRECT and "under-reaction" is our blindness.
    Test: add margin to both sides. If the gap closes, the finding dies.

 C. ATTRITION / RANGE RESTRICTION. ~20% of games drop when the ladder does
    not bracket, skewed to blowouts. Compare kept vs dropped, and bound the
    bias.

 D. `pre` MEASUREMENT. The book closing total is measured with error, which
    under EIV can bias the H1 coefficient. Re-run using Kalshi's OWN pregame
    line instead.

 E. WHO FORECASTS BETTER. If the market truly under-weights banked points, a
    model correcting that should beat the market's own line out of sample.
    If instead the market's line has lower error, s<1 means the model is
    missing information, not that the market is wrong.

 RESULTS (2026-08-25) — the finding is DOWNGRADED, not confirmed:

   A  benchmark is 0.998 (se .012) on 9,489 games. The bar is exactly 1.0.
   B  blowout explanation ELIMINATED. Adding |margin| moves s not at all
      (0.862 -> 0.862) and the market's own |margin| coefficient is
      +0.007 (.025) — the market is NOT pricing blowout risk, so its lower
      H1 loading is not sophistication we failed to model.
   D  `pre` measurement is NOT the cause: Kalshi's own pregame L gives the
      same picture (s=0.863, gap -0.084).
   C  ATTRITION IS SEVERE AND UNRESOLVED. The 82 dropped games have
      sd(H1) 19.9-20.7 vs 9.2 for kept ones: the estimator systematically
      discards the games where the halftime line moved MOST. Excluding
      large-move games biases s DOWNWARD, i.e. toward finding
      under-reaction.
   E  THE MARKET FORECASTS BETTER than the naive model (RMSE 13.52 vs
      13.70). A market under-weighting banked points should be beaten by a
      model that does not. It is not.

 Three attempts to resolve C all failed, recorded so they are not retried
 blind: (F) splitting by ladder headroom is confounded — a line that moved
 far IS near an edge, so headroom is endogenous; (G) pinning censored games
 at their ladder edge yields only a LOWER bound (0.761), uninformative about
 direction; (H/I) logit extrapolation of the crossing is too noisy to use —
 it disagrees with the crossing estimator on the very same bracketed games
 (1.053 vs 0.868) and its standard errors balloon 4-15x, because ladder
 saturation correlates with extreme H1.

 HONEST STANDING CLAIM: on the bracketed sample the NBA halftime line loads
 banked first-half points at ~0.86 against an efficient 1.0, robust to the
 blowout and `pre`-measurement explanations. But the sample excludes ~20% of
 games precisely where the line moved most, with the exclusion biasing toward
 the finding, and the market still out-forecasts the corrected model. The
 under-reaction is real IN THE MEASURED SAMPLE; its magnitude is NOT
 established and it confers no forecasting advantage.

 Read-only.
===============================================================================
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402
import clock_validation as CV                                # noqa: E402
import nba_anchor_audit as N                                 # noqa: E402
from prepare_data import CSV, season_label                   # noqa: E402

ENTRY_OFF = 3 * 60          # sample at the real buzzer +3 min (mid-break)


def ols_full(y, cols, names):
    b, se = A.ols(y, cols, names)
    return b, se


def show(lab, b, se, keys=("h1",)):
    bits = "  ".join(f"{k}={b[k]:+.3f}({se[k]:.3f})" for k in keys)
    print(f"   {lab:<46} {bits}")


def build():
    series, meta = N.build_series()
    m = N.load_master(meta)
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    r = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    for c in ("1Q_H", "2Q_H", "1Q_R", "2Q_R"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["gid"] = r["GAME-ID"].astype(str)
    marg = dict(zip(r.gid, (r["1Q_H"] + r["2Q_H"]) - (r["1Q_R"] + r["2Q_R"])))
    m["gid"] = m["GAME-ID"].astype(str)
    m["margin"] = m.gid.map(marg)
    ck = CV.load_clocks("espn_clocks_nba.csv", CV.ESPN_NBA)
    ds = ck.date.astype(str)
    ck["key"] = (ds.str[:4] + "-" + ds.str[4:6] + "-" + ds.str[6:8] + "|"
                 + ck.ac + "@" + ck.hc)
    m["key"] = m.date.dt.strftime("%Y-%m-%d") + "|" + m.ac + "@" + m.hc
    m = m.merge(ck[["key", "tip_ts", "half_ts"]], on="key", how="inner")
    m = m.dropna(subset=["event", "half_ts", "margin"])
    m["L"] = [A.L_at(series[e], h + ENTRY_OFF) if e in series else np.nan
              for e, h in zip(m.event, m.half_ts)]
    m["kpre"] = [A.L_at(series[e], t - 20 * 60) if e in series else np.nan
                 for e, t in zip(m.event, m.tip_ts)]
    return m


def main():
    m = build()
    kept = m.dropna(subset=["L", "pre", "h1", "total", "margin"])
    print(f"[nba] {len(m)} games on the true clock; {len(kept)} with a "
          f"bracketed halftime ladder ({len(m) - len(kept)} dropped)\n")

    # ---- A. benchmark on 8 seasons ------------------------------------
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d8 = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    for c in ("1Q_H", "2Q_H", "1Q_R", "2Q_R", "PTS_H", "PTS_R",
              "CLOSING TOTAL_H"):
        d8[c] = pd.to_numeric(d8[c], errors="coerce")
    d8["h1"] = d8["1Q_H"] + d8["2Q_H"] + d8["1Q_R"] + d8["2Q_R"]
    d8["total"] = d8["PTS_H"] + d8["PTS_R"]
    d8["pre"] = d8["CLOSING TOTAL_H"]
    d8 = d8.dropna(subset=["h1", "total", "pre"])
    b, se = ols_full(d8.total.values, [d8.pre.values, d8.h1.values],
                     ["pre", "h1"])
    print("A. EFFICIENT BENCHMARK — how precisely do we know the target?")
    show(f"8 seasons, n={len(d8)}", b, se)
    b1, se1 = ols_full(kept.total.values, [kept.pre.values, kept.h1.values],
                       ["pre", "h1"])
    show(f"this sample only, n={len(kept)}", b1, se1)
    print("   [the wide-sample value is the honest bar for s]\n")

    # ---- B. blowout dynamics ------------------------------------------
    print("B. BLOWOUT DYNAMICS — does the market know something the model "
          "does not?")
    am = kept.margin.abs().values
    bM, seM = ols_full(kept.L.values, [kept.pre.values, kept.h1.values,
                                       am], ["pre", "h1", "absmargin"])
    bR, seR = ols_full(kept.total.values, [kept.pre.values, kept.h1.values,
                                           am], ["pre", "h1", "absmargin"])
    b0, se0 = ols_full(kept.L.values, [kept.pre.values, kept.h1.values],
                       ["pre", "h1"])
    print(f"   market line, no margin      s={b0['h1']:.3f} ({se0['h1']:.3f})")
    print(f"   market line, + |margin|     s={bM['h1']:.3f} ({seM['h1']:.3f})"
          f"   coef |margin| {bM['absmargin']:+.3f} ({seM['absmargin']:.3f})")
    print(f"   REALIZED, + |margin|        s={bR['h1']:.3f} ({seR['h1']:.3f})"
          f"   coef |margin| {bR['absmargin']:+.3f} ({seR['absmargin']:.3f})")
    gap0 = b0["h1"] - b1["h1"]
    gapM = bM["h1"] - bR["h1"]
    print(f"   GAP (market - realized):  without margin {gap0:+.3f}, "
          f"with margin {gapM:+.3f}")
    print("   -> if the gap collapses toward 0, the market was pricing "
          "blowout risk\n      and the 'under-reaction' was the naive model's "
          "blind spot.\n")

    # ---- C. attrition --------------------------------------------------
    print("C. ATTRITION / RANGE RESTRICTION")
    drop = m[m.L.isna() & m.pre.notna() & m.h1.notna()]
    if len(drop):
        print(f"   kept  n={len(kept):>3}  sd(H1) {kept.h1.std():.1f}  "
              f"sd(total) {kept.total.std():.1f}  "
              f"mean |margin| {kept.margin.abs().mean():.1f}")
        print(f"   drop  n={len(drop):>3}  sd(H1) {drop.h1.std():.1f}  "
              f"sd(total) {drop.total.std():.1f}  "
              f"mean |margin| {drop.margin.abs().mean():.1f}")
    q = kept.margin.abs().quantile(.75)
    close = kept[kept.margin.abs() <= q]
    bc, sec = ols_full(close.L.values, [close.pre.values, close.h1.values],
                       ["pre", "h1"])
    brc, _ = ols_full(close.total.values, [close.pre.values, close.h1.values],
                      ["pre", "h1"])
    print(f"   close games only (|margin|<={q:.0f}, n={len(close)}): "
          f"market s={bc['h1']:.3f} ({sec['h1']:.3f}) vs realized "
          f"{brc['h1']:.3f}  gap {bc['h1']-brc['h1']:+.3f}\n")

    # ---- D. pre measurement --------------------------------------------
    print("D. `pre` MEASUREMENT — book closing total vs Kalshi's own pregame L")
    k2 = kept.dropna(subset=["kpre"])
    bk, sek = ols_full(k2.L.values, [k2.kpre.values, k2.h1.values],
                       ["pre", "h1"])
    brk, _ = ols_full(k2.total.values, [k2.kpre.values, k2.h1.values],
                      ["pre", "h1"])
    print(f"   using Kalshi pregame L (n={len(k2)}): market s={bk['h1']:.3f} "
          f"({sek['h1']:.3f}) vs realized {brk['h1']:.3f}  "
          f"gap {bk['h1']-brk['h1']:+.3f}\n")

    # ---- E. who forecasts better ---------------------------------------
    print("E. WHO FORECASTS THE TOTAL BETTER, THE MARKET OR THE MODEL?")
    X = np.column_stack([np.ones(len(kept)), kept.pre.values, kept.h1.values])
    y = kept.total.values
    E = np.empty(len(kept))
    for i in range(len(kept)):
        msk = np.ones(len(kept), bool)
        msk[i] = False
        bb, *_ = np.linalg.lstsq(X[msk], y[msk], rcond=None)
        E[i] = X[i] @ bb
    rm = np.sqrt(np.mean((y - kept.L.values) ** 2))
    re_ = np.sqrt(np.mean((y - E) ** 2))
    print(f"   RMSE of the MARKET's halftime line : {rm:.2f} pts")
    print(f"   RMSE of the naive model (LOO)      : {re_:.2f} pts")
    print(f"   -> {'MARKET' if rm < re_ else 'MODEL'} forecasts better by "
          f"{abs(rm - re_):.2f} pts")
    print("   A market that under-weights banked points should be BEATEN by")
    print("   a model that does not. If it wins anyway, s<1 is measuring the")
    print("   model's missing information, not the market's error.")


if __name__ == "__main__":
    main()
