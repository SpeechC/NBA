"""Fixed validation of the 3-day pre-All-Star window. No window search.

The hypothesis is the FINAL 3 CALENDAR DAYS before the All-Star break, fixed in
advance. The same five-part battery that made the final-week result credible:

  1 OPENER vs CLOSE   actual-open, close-open, actual-close. Little correction
                      would mirror the final-week finding.
  2 CENTRAL vs TAIL   mean, median, 10% trimmed mean, residual quantiles. A
                      payoff-relevant shift moves the median, not just the mean.
  3 SEASON BLOCKS     per-season residual and over rate, with a season-block
                      bootstrap -- inference, not optimisation.
  4 MATCHED-WINDOW PERMUTATION. The important control. Rather than shuffling the
                      flag across the whole season -- February's scoring
                      environment differs from November's -- draw random
                      contiguous 3-day windows from the 4 weeks PRECEDING the
                      break, in the same season, and ask how often one is at
                      least as strong. That holds the calendar period roughly
                      fixed.
  5 PRICE             ROI at -110. The vendor's odds columns are 17-24% populated
                      and carry the same swap corruption as the HALFTIME fields,
                      so real juice is unavailable and -110 is assumed.

The break is located as the largest mid-season date gap (6-7 days every season).
Reference row: final week at days_left <= 7, the definition the LOSO test used
(537 games, 8 calendar days).
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

PRE_DAYS = 3          # FIXED. not searched.
DONOR_WEEKS = 4
BE = 110 / 210


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "open", "date", "actual"])
    d = d[d["close"].between(150, 300)].copy()
    d["r_close"] = d["actual"] - d["close"]
    d["r_open"] = d["actual"] - d["open"]
    d["move"] = d["close"] - d["open"]
    d["days_left"] = (d.groupby("lbl")["date"].transform("max")
                      - d["date"]).dt.days

    breaks = {}
    for lbl, g in d.groupby("lbl"):
        dts = np.sort(g["date"].dropna().unique())
        gaps = np.diff(dts).astype("timedelta64[D]").astype(int)
        i = int(np.argmax(gaps))
        breaks[lbl] = pd.Timestamp(dts[i])
    d["break_day"] = d["lbl"].map(breaks)
    d["days_to_break"] = (d["break_day"] - d["date"]).dt.days
    d["pre_asb"] = d["days_to_break"].between(0, PRE_DAYS - 1)
    d["final7"] = d["days_left"] <= 7
    return d, breaks


def blk(s, col, lab):
    live = s[s[col] != 0]
    ov = (live[col] > 0).mean()
    se = np.sqrt(ov * (1 - ov) / len(live))
    return {"price": lab, "n": len(s), "push": int((s[col] == 0).sum()),
            "mean": round(s[col].mean(), 3),
            "median": round(s[col].median(), 2),
            "trim10%": round(stats.trim_mean(s[col], 0.1), 3),
            "over %": round(100 * ov, 2),
            "95% CI": f"[{100*(ov-1.96*se):.2f}, {100*(ov+1.96*se):.2f}]",
            "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)}


def main():
    d, breaks = load()
    A = d[d["pre_asb"]]
    F = d[d["final7"]]
    print(f"pre-ASB window = final {PRE_DAYS} calendar days before the break")
    print(f"  n={len(A)}   {A['lbl'].nunique()} seasons")
    print(f"reference final week (days_left<=7): n={len(F)}\n")

    print("=" * 100)
    print("1/2. OPENER vs CLOSE, and central vs tail")
    print("=" * 100)
    print(pd.DataFrame([blk(A, "r_open", "pre-ASB @OPEN"),
                        blk(A, "r_close", "pre-ASB @CLOSE"),
                        blk(F, "r_close", "final week @CLOSE [ref]"),
                        blk(d[~d["pre_asb"] & ~d["final7"]], "r_close",
                            "all other games")]).to_string(index=False))
    ao, co, ac = A["r_open"].mean(), A["move"].mean(), A["r_close"].mean()
    print(f"\n  attribution:  opening error {ao:+.3f}  =  market correction "
          f"{co:+.3f} ({100*co/ao:.1f}%)  +  remaining {ac:+.3f}")
    print(f"  residual quantiles @close: " + "  ".join(
        f"p{q}={A['r_close'].quantile(q/100):+.1f}" for q in (10, 25, 50, 75, 90)))

    print("\n" + "=" * 100)
    print("3. SEASON BLOCKS")
    print("=" * 100)
    rows = []
    for lbl, g in A.groupby("lbl"):
        live = g[g["r_close"] != 0]
        rows.append({"season": lbl[4:13], "n": len(g),
                     "resid": round(g["r_close"].mean(), 2),
                     "median": round(g["r_close"].median(), 2),
                     "over %": round(100 * (live["r_close"] > 0).mean(), 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print(f"\n  seasons above break-even: "
          f"{int((t['over %'] > 100*BE).sum())}/{len(t)}")
    seas = t["season"].values
    boot = [np.mean(RNG.choice(t["over %"].values, len(t), replace=True))
            for _ in range(10000)]
    print(f"  season-block bootstrap of the mean over rate: "
          f"{np.mean(boot):.2f}%  95% CI "
          f"[{np.percentile(boot,2.5):.2f}, {np.percentile(boot,97.5):.2f}]")

    print("\n" + "=" * 100)
    print(f"4. MATCHED-WINDOW PERMUTATION — random {PRE_DAYS}-day windows from "
          f"the {DONOR_WEEKS} weeks before the break")
    print("=" * 100)
    live_all = d[d["r_close"] != 0]
    obs = (A[A["r_close"] != 0]["r_close"] > 0).mean()
    obs_resid = A["r_close"].mean()
    null_ov, null_rs = [], []
    donors = {}
    for lbl, bd in breaks.items():
        pool = live_all[(live_all["lbl"] == lbl)
                        & (live_all["date"] < bd - pd.Timedelta(days=PRE_DAYS - 1))
                        & (live_all["date"] >= bd - pd.Timedelta(days=7 * DONOR_WEEKS))]
        donors[lbl] = np.sort(pool["date"].unique())
    for _ in range(5000):
        picks = []
        for lbl, dts in donors.items():
            if len(dts) < PRE_DAYS + 1:
                continue
            i = RNG.integers(0, len(dts) - PRE_DAYS + 1)
            win = dts[i:i + PRE_DAYS]
            picks.append(live_all[(live_all["lbl"] == lbl)
                                  & (live_all["date"].isin(win))])
        if not picks:
            continue
        s = pd.concat(picks)
        null_ov.append((s["r_close"] > 0).mean())
        null_rs.append(s["r_close"].mean())
    null_ov, null_rs = np.array(null_ov), np.array(null_rs)
    print(f"  observed over %          {100*obs:.2f}")
    print(f"  matched null over %      {100*null_ov.mean():.2f} "
          f"± {100*null_ov.std():.2f}   "
          f"95th pct {100*np.percentile(null_ov,95):.2f}")
    print(f"  p (null >= observed)     {np.mean(null_ov >= obs):.4f}")
    print(f"\n  observed mean residual   {obs_resid:+.3f}")
    print(f"  matched null residual    {null_rs.mean():+.3f} ± {null_rs.std():.3f}"
          f"   95th pct {np.percentile(null_rs,95):+.3f}")
    print(f"  p (null >= observed)     {np.mean(null_rs >= obs_resid):.4f}")

    print("\n" + "=" * 100)
    print("5. PRICE — $100 flat at -110 (real juice unavailable)")
    print("=" * 100)
    live = A[A["r_close"] != 0]
    ov = (live["r_close"] > 0).mean()
    ns = A["lbl"].nunique()
    roi = ov * (100 / 110) - (1 - ov)
    print(f"  {len(live)} graded bets over {ns} seasons "
          f"({len(live)/ns:.1f}/season), {int((A['r_close']==0).sum())} pushes")
    print(f"  over {100*ov:.2f}%   ROI {100*roi:+.2f}%   "
          f"${100*roi*len(live)/ns:+,.0f}/season on ${100*len(live)/ns:,.0f} risked")


if __name__ == "__main__":
    main()
