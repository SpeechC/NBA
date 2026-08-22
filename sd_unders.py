"""Does betting the UNDER pay on totals ~1 and ~2 SD above the mean?

The claim (Paul & Weinbach and successors): win rates above the 52.38%
break-even for the under when the posted total sits about one standard
deviation above the mean total.

TWO WAYS OF MEASURING "ABOVE THE MEAN", because they are not the same test:

  z_full  full-sample mean and sd. This is what the literature computed, and it
          has LOOK-AHEAD: in November you cannot know the mean of a season that
          has not finished, still less of a ten-year sample. Reported because it
          is the claim as stated.

  z_wf    walk-forward season-to-date expanding mean and sd, minimum 100 games,
          the convention already used in extreme_totals.py. This is the only
          version that could actually be bet.

Cumulative thresholds (>= +1 SD, >= +2 SD), not bands, since the claim is about
a cutoff. The symmetric low tail is reported as a falsification: a reversion
story predicts high totals come in UNDER and low totals come in OVER, so the two
tails must behave oppositely. If both tails favour the same side, it is not
reversion.

Pushes (actual == closing) are excluded from win rates and counted separately.
Development 2017-18..2023-24; holdout 2024-25 and 2025-26.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from data_split import SPLIT_DATE
from prepare_data import CSV, season_label

MIN_N = 100
BE = 100 * 11 / 21          # 52.381% break-even at -110


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["season"].str.extract(r"(\d{4})")[0].astype(int)
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["actual"] = (pd.to_numeric(d["PTS_H"], errors="coerce")
                   + pd.to_numeric(d["PTS_R"], errors="coerce"))
    d = d.dropna(subset=["close", "actual", "date"])
    d = d[d["close"].between(150, 300)].sort_values("date").reset_index(
        drop=True)
    d["e"] = d["actual"] - d["close"]

    # (a) full-sample z -- look-ahead, the literature's construction
    d["z_full"] = (d["close"] - d["close"].mean()) / d["close"].std()
    # (b) walk-forward season-to-date z -- implementable
    parts = []
    for _, g in d.groupby("yr"):
        g = g.sort_values("date").copy()
        mu = g["close"].expanding().mean().shift(1)
        sd = g["close"].expanding().std().shift(1)
        cnt = g["close"].expanding().count().shift(1)
        g["z_wf"] = np.where(cnt >= MIN_N, (g["close"] - mu) / sd, np.nan)
        parts.append(g)
    return pd.concat(parts).sort_values("date").reset_index(drop=True)


def rate(s, side):
    """Win rate on `side`, pushes excluded. Returns (n_bets, pct, n_push)."""
    push = int((s["e"] == 0).sum())
    live = s[s["e"] != 0]
    if not len(live):
        return 0, np.nan, push
    w = (live["e"] > 0) if side == "over" else (live["e"] < 0)
    return len(live), 100 * w.mean(), push


def zt(pct, n, ref):
    if not n or np.isnan(pct):
        return np.nan
    return (pct / 100 - ref / 100) / np.sqrt(0.25 / n)


def report(d, zcol, label):
    print("\n" + "=" * 100)
    print(f"{label}   (z = {zcol})")
    print("=" * 100)
    x = d.dropna(subset=[zcol])
    print(f"  n={len(x):,}   closing total mean {x['close'].mean():.2f} "
          f"sd {x['close'].std():.2f}")
    if zcol == "z_full":
        mu, sd = x["close"].mean(), x["close"].std()
        print(f"  +1 SD = {mu+sd:.1f} points, +2 SD = {mu+2*sd:.1f} points")
    print(f"\n  {'threshold':16}{'window':14}{'n bets':>8}{'push':>6}"
          f"{'UNDER %':>10}{'vs 52.38':>11}{'z vs BE':>10}{'z vs 50':>10}")
    for lab, mask in ((">= +1 SD", x[zcol] >= 1.0),
                      (">= +2 SD", x[zcol] >= 2.0),
                      ("<= -1 SD  [falsif]", x[zcol] <= -1.0),
                      ("<= -2 SD  [falsif]", x[zcol] <= -2.0)):
        s0 = x[mask]
        for wl, w in (("development", s0[s0["date"] < SPLIT_DATE]),
                      ("holdout", s0[s0["date"] >= SPLIT_DATE]),
                      ("pooled", s0)):
            n_, p, pu = rate(w, "under")
            if not n_:
                continue
            print(f"  {lab if wl=='development' else '':16}{wl:14}{n_:8,}"
                  f"{pu:6}{p:10.2f}%{p-BE:+11.2f}{zt(p,n_,BE):10.2f}"
                  f"{zt(p,n_,50.0):10.2f}")
        print()


def main():
    d = build()
    print(f"  {len(d):,} regular-season games with a closing total, "
          f"seasons {sorted(d['yr'].unique())}")
    print(f"  break-even at -110 = {BE:.3f}%")

    report(d, "z_full", "A — FULL-SAMPLE z (the literature's construction; "
                        "contains look-ahead)")
    report(d, "z_wf", "B — WALK-FORWARD season-to-date z (implementable)")

    print("\n" + "=" * 100)
    print("C — IS THERE ANY MONOTONE STRUCTURE?  under rate by walk-forward z")
    print("=" * 100)
    x = d.dropna(subset=["z_wf"]).copy()
    bins = [-9, -2, -1.5, -1, -0.5, 0.5, 1, 1.5, 2, 9]
    x["b"] = pd.cut(x["z_wf"], bins)
    print(f"  {'band':16}{'n':>7}{'mean total':>12}{'mean e':>10}"
          f"{'UNDER %':>10}{'vs 52.38':>11}")
    for b, g in x.groupby("b", observed=True):
        n_, p, _ = rate(g, "under")
        print(f"  {str(b):16}{n_:7,}{g['close'].mean():12.2f}"
              f"{g['e'].mean():+10.3f}{p:10.2f}%{p-BE:+11.2f}")

    print("\n" + "=" * 100)
    print("D — POWER: what edge could this sample even detect?")
    print("=" * 100)
    for lab, mask in ((">= +1 SD (walk-forward)", x["z_wf"] >= 1.0),
                      (">= +2 SD (walk-forward)", x["z_wf"] >= 2.0)):
        s = x[mask]
        n_ = int((s["e"] != 0).sum())
        se = 100 * np.sqrt(0.25 / n_) if n_ else np.nan
        print(f"  {lab:26} n={n_:5,}   SE {se:5.2f}pp   "
              f"detectable at 80% power: {2.8*se:5.2f}pp   "
              f"bets needed for a 2.4pp edge: "
              f"{7.84*0.25/0.024**2:,.0f}")


if __name__ == "__main__":
    main()
