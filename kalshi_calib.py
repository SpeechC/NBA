"""Is the Kalshi NBA totals LADDER well calibrated?

This is a MEASUREMENT, not a fitted model, so it uses every matched game and
takes no train/test split. Nothing here is tuned; there is nothing to overfit.

DATA. kalshi_nba_totals.sqlite / nba_totals_pregame_ladders.csv, 2025-26 only.
The `pregame_*` quote is captured a median of 1 minute before tipoff (IQR 1-2),
so it is effectively a closing quote. The `close_*` columns are captured AFTER
settlement -- 71.5% of close_yes_bid values are 0 or 100 -- and are NOT used.

Joined to our NBA panel on date + unordered team pair via team_mapping.csv
(city name -> abbreviation). 1,314 of 1,324 events match.

WHAT IS MEASURED
  1. sanity: rung counts, spreads, degenerate quotes, settlement cross-check
  2. calibration of the implied probability against realised frequency,
     by probability decile and by rung position
  3. per-game implied distribution: fit z = Phi^-1(1-p) on strike to recover
     the ladder's implied MEAN and SD
  4. THE KEY TEST -- is the implied SD equal to the realised dispersion of
     (actual - implied mean)?  implied > realised means the ladder overprices
     the wings; implied < realised means it underprices them. This is the
     dispersion question asked directly, on an instrument that can express it.
  5. is the ladder's implied mean sharper than the sportsbook closing total?
  6. shape: are the residuals from a normal fit systematically curved?

Buckets are reported separately (regular season / IST / play-in / playoffs)
because the postseason is a different population, but no bucket is used to
select anything.
"""
import sqlite3
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label

DB = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite"
MINRUNG = 4          # rungs needed to fit a per-game distribution


def load():
    con = sqlite3.connect(DB)
    m = pd.read_sql("""SELECT event_ticker, game_date, away_team, home_team,
                              floor_strike, pregame_yes_bid, pregame_yes_ask,
                              result, volume, tipoff_ts, pregame_bar_ts
                       FROM markets WHERE pregame_yes_bid IS NOT NULL""", con)
    for c in ("floor_strike", "pregame_yes_bid", "pregame_yes_ask", "volume",
              "tipoff_ts", "pregame_bar_ts"):
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m["bid"] = m["pregame_yes_bid"] / 100.0
    m["ask"] = m["pregame_yes_ask"] / 100.0
    m["mid"] = (m["bid"] + m["ask"]) / 2.0
    m["spread"] = m["ask"] - m["bid"]

    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    raw["d"] = pd.to_datetime(raw["DATE"], errors="coerce")
    g = raw[raw["d"] >= pd.Timestamp("2025-10-01")].copy()
    g["H"] = g["TEAM_H"].map(mp)
    g["R"] = g["TEAM_R"].map(mp)
    g["actual"] = (pd.to_numeric(g["PTS_H"], errors="coerce")
                   + pd.to_numeric(g["PTS_R"], errors="coerce"))
    g["book"] = pd.to_numeric(g["CLOSING TOTAL_H"], errors="coerce")
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-" + np.where(a < b, b, a))
    g["k"] = mk(g["d"], g["H"], g["R"])
    m["d"] = pd.to_datetime(m["game_date"])
    m["k"] = mk(m["d"], m["home_team"].values, m["away_team"].values)
    keep = ["k", "lbl", "actual", "book"]
    m = m.merge(g[keep].drop_duplicates("k"), on="k", how="inner")

    m["bucket"] = np.select(
        [m["lbl"].str.contains("Regular Season"),
         m["lbl"].str.contains("In-Season"),
         m["lbl"].str.contains("Play-In")],
        ["regular", "IST", "play-in"], default="playoffs")
    m["win"] = (m["actual"] > m["floor_strike"]).astype(int)
    return m.dropna(subset=["floor_strike", "mid", "actual"])


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def fit_ladder(g):
    """Recover implied mean and sd from one game's ladder."""
    s = g[(g["mid"] > 0.02) & (g["mid"] < 0.98)]
    if len(s) < MINRUNG or s["floor_strike"].nunique() < MINRUNG:
        return None
    z = norm.ppf(1.0 - s["mid"].values)          # z = (K - mu)/sigma
    K = s["floor_strike"].values
    A = np.column_stack([np.ones(len(K)), K])
    try:
        c, *_ = np.linalg.lstsq(A, z, rcond=None)
    except Exception:
        return None
    if not np.isfinite(c).all() or c[1] <= 0:
        return None
    sd = 1.0 / c[1]
    mu = -c[0] * sd
    resid = z - A @ c
    return mu, sd, len(s), float(np.sqrt(np.mean(resid ** 2)))


def main():
    m = load()
    print("=" * 100)
    print("1 — SANITY")
    print("=" * 100)
    print(f"  {len(m):,} rungs across {m['event_ticker'].nunique():,} games")
    print(f"  rungs per game: mean "
          f"{m.groupby('event_ticker').size().mean():.1f}  "
          f"min {m.groupby('event_ticker').size().min()}  "
          f"max {m.groupby('event_ticker').size().max()}")
    print(f"  by bucket: " + "  ".join(
        f"{b}: {g['event_ticker'].nunique()}g/{len(g)}r"
        for b, g in m.groupby("bucket")))
    deg = (m["bid"] <= 0) & (m["ask"] >= 1.0)
    print(f"  degenerate quotes (bid 0 AND ask 100): {int(deg.sum()):,} "
          f"({100*deg.mean():.2f}%)")
    print(f"  spread: median {100*m['spread'].median():.1f}c   "
          f"mean {100*m['spread'].mean():.2f}c")
    # settlement cross-check against Kalshi's own result field
    r = m.dropna(subset=["result"])
    r = r[r["result"].isin(["yes", "no"])]
    agree = (r["win"] == (r["result"] == "yes").astype(int)).mean()
    print(f"  settlement cross-check: our (actual > strike) agrees with "
          f"Kalshi `result` on {100*agree:.2f}% of {len(r):,} rungs")

    u = m[~deg].copy()
    print(f"\n  usable rungs after dropping degenerate quotes: {len(u):,}")

    print("\n" + "=" * 100)
    print("2 — CALIBRATION OF THE IMPLIED PROBABILITY")
    print("=" * 100)
    for lab, x in (("ALL", u), ("regular season", u[u["bucket"] == "regular"]),
                   ("playoffs", u[u["bucket"] == "playoffs"])):
        print(f"\n  {lab}   n={len(x):,}")
        print(f"    mean implied {x['mid'].mean():.4f}   "
              f"realised {x['win'].mean():.4f}   "
              f"bias {x['mid'].mean()-x['win'].mean():+.4f}")
        print(f"    Brier {brier(x['mid'].values, x['win'].values):.4f}   "
              f"(a constant 0.5 forecast scores 0.2500)")
        if lab != "ALL":
            continue
        x = x.copy()
        x["dec"] = pd.qcut(x["mid"], 10, duplicates="drop")
        t = x.groupby("dec", observed=True).agg(
            n=("win", "size"), implied=("mid", "mean"),
            realised=("win", "mean"))
        t["diff"] = t["realised"] - t["implied"]
        t["se"] = np.sqrt(t["realised"] * (1 - t["realised"]) / t["n"])
        t["z"] = t["diff"] / t["se"]
        print(f"    {'implied decile':>22}{'n':>7}{'implied':>10}"
              f"{'realised':>10}{'diff':>9}{'z':>7}")
        for k, row in t.iterrows():
            print(f"    {str(k):>22}{int(row['n']):>7}{row['implied']:>10.4f}"
                  f"{row['realised']:>10.4f}{row['diff']:>+9.4f}"
                  f"{row['z']:>7.2f}")

    print("\n" + "=" * 100)
    print("3 — PER-GAME IMPLIED DISTRIBUTION")
    print("=" * 100)
    rows = []
    for ev, g in u.groupby("event_ticker"):
        f = fit_ladder(g)
        if f is None:
            continue
        mu, sd, nr, rmse = f
        rows.append({"event_ticker": ev, "mu": mu, "sd": sd, "nr": nr,
                     "fit_rmse": rmse, "actual": g["actual"].iloc[0],
                     "book": g["book"].iloc[0], "bucket": g["bucket"].iloc[0]})
    G = pd.DataFrame(rows)
    G["e_kalshi"] = G["actual"] - G["mu"]
    G["e_book"] = G["actual"] - G["book"]
    print(f"  fitted {len(G):,} games (needed >={MINRUNG} informative rungs)")
    print(f"  implied mean: {G['mu'].mean():.2f}   implied sd: "
          f"{G['sd'].mean():.2f} (sd of that {G['sd'].std():.2f})")
    print(f"  normal-fit RMSE in z units: median {G['fit_rmse'].median():.4f}"
          f"   -> the ladder is very close to Gaussian")

    print("\n" + "=" * 100)
    print("4 — KEY TEST: IS THE IMPLIED SD RIGHT?")
    print("=" * 100)
    print(f"  {'bucket':14}{'n':>6}{'implied sd':>12}{'realised sd':>13}"
          f"{'ratio':>8}{'F-test p':>10}")
    from scipy.stats import chi2
    for lab, x in (("ALL", G), ("regular", G[G["bucket"] == "regular"]),
                   ("IST", G[G["bucket"] == "IST"]),
                   ("playoffs", G[G["bucket"] == "playoffs"])):
        if len(x) < 20:
            continue
        imp = x["sd"].mean()
        real = x["e_kalshi"].std(ddof=1)
        n = len(x)
        stat = (n - 1) * real ** 2 / imp ** 2
        p = 2 * min(chi2.cdf(stat, n - 1), 1 - chi2.cdf(stat, n - 1))
        print(f"  {lab:14}{n:>6}{imp:>12.2f}{real:>13.2f}"
              f"{real/imp:>8.3f}{p:>10.4f}")
    print("\n  ratio > 1: the ladder UNDERSTATES dispersion (wings too cheap)")
    print("  ratio < 1: the ladder OVERSTATES dispersion (wings too rich)")
    print(f"  our NBA benchmark, measured on 2017-2026 sportsbook closes: "
          f"sd 18.08")

    print("\n" + "=" * 100)
    print("5 — IS KALSHI'S IMPLIED MEAN SHARPER THAN THE BOOK'S CLOSING TOTAL?")
    print("=" * 100)
    s = G.dropna(subset=["book"])
    print(f"  n={len(s):,}")
    print(f"  {'source':16}{'RMSE':>9}{'MAE':>9}{'mean resid':>12}")
    for lab, col in (("Kalshi implied", "e_kalshi"), ("book closing", "e_book")):
        print(f"  {lab:16}{np.sqrt((s[col]**2).mean()):>9.3f}"
              f"{s[col].abs().mean():>9.3f}{s[col].mean():>+12.3f}")
    d = s["mu"] - s["book"]
    print(f"\n  Kalshi implied mean minus book total: mean {d.mean():+.3f}   "
          f"sd {d.std():.3f}   corr {np.corrcoef(s['mu'], s['book'])[0,1]:.4f}")
    # does either contain information the other lacks?
    A = np.column_stack([np.ones(len(s)), s["book"], s["mu"]])
    b, *_ = np.linalg.lstsq(A, s["actual"], rcond=None)
    res = s["actual"] - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (res @ res) / (len(s) - 3))
    print(f"  actual ~ book + kalshi:  book {b[1]:+.4f} (t={b[1]/se[1]:+.2f})"
          f"   kalshi {b[2]:+.4f} (t={b[2]/se[2]:+.2f})")
    print(f"    [whichever carries a significant coefficient holds information"
          f" the other lacks]")

    print("\n" + "=" * 100)
    print("6 — SHAPE: residuals from the normal fit by position on the ladder")
    print("=" * 100)
    u2 = u.merge(G[["event_ticker", "mu", "sd"]], on="event_ticker")
    u2["zpos"] = (u2["floor_strike"] - u2["mu"]) / u2["sd"]
    u2["fit"] = 1.0 - norm.cdf(u2["zpos"])
    u2["bin"] = pd.cut(u2["zpos"], [-9, -1.5, -1, -0.5, 0, .5, 1, 1.5, 9])
    t = u2.groupby("bin", observed=True).agg(
        n=("win", "size"), implied=("mid", "mean"), normal=("fit", "mean"),
        realised=("win", "mean"))
    print(f"  {'z position':>16}{'n':>7}{'implied':>10}{'normal fit':>12}"
          f"{'realised':>10}{'real-impl':>11}")
    for k, r in t.iterrows():
        print(f"  {str(k):>16}{int(r['n']):>7}{r['implied']:>10.4f}"
              f"{r['normal']:>12.4f}{r['realised']:>10.4f}"
              f"{r['realised']-r['implied']:>+11.4f}")


if __name__ == "__main__":
    main()
