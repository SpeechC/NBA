"""Kalshi implied total vs the sportsbook closing total: which is the better
price to trade against, and what does the ladder's structure cost you?

Step 1 (kalshi_calib.py) established the two prices are 99.2% correlated with
near-identical RMSE. That leaves four questions that actually bear on execution:

  A  SHARPNESS -- calibration slope and RMSE, regular season, and by segment.
  B  DISAGREEMENT -- when the two prices differ, who is right? This is the only
     way either can carry information the other lacks; the encompassing
     regression cannot separate them at r=0.992 because of collinearity, but
     regressing the BOOK's residual on the disagreement can.
  C  PUSHES -- Kalshi strikes are all .5 so nothing pushes. Book totals are
     often integers and do. A push is a returned stake, which is not free: it
     is a bet that consumed capital and produced no edge.
  D  RUNG GRANULARITY AND SPAN -- strikes are ~3 points apart, so you cannot
     express a view at the point you want; you are forced to the nearest rung.
     And the ladder only spans a limited z-range, so the deep tails are not
     quotable at all. Both are real costs and neither appears in a fee table.

Regular season is the primary population; IST and playoffs are reported
separately and never used to select anything.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import kalshi_calib as KC


def ols_t(y, X):
    A = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    dof = max(len(y) - A.shape[1], 1)
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / dof)
    return b, b / se


def build():
    m = KC.load()
    u = m[~((m["bid"] <= 0) & (m["ask"] >= 1.0))].copy()
    rows = []
    for ev, g in u.groupby("event_ticker"):
        f = KC.fit_ladder(g)
        if f is None:
            continue
        mu, sd, nr, rmse = f
        s = g[(g["mid"] > 0.02) & (g["mid"] < 0.98)]
        rows.append({
            "event_ticker": ev, "mu": mu, "sd": sd, "nr": nr,
            "actual": g["actual"].iloc[0], "book": g["book"].iloc[0],
            "bucket": g["bucket"].iloc[0], "date": g["d"].iloc[0],
            "k_lo": g["floor_strike"].min(), "k_hi": g["floor_strike"].max(),
            "q_lo": s["floor_strike"].min(), "q_hi": s["floor_strike"].max(),
            "n_strikes": g["floor_strike"].nunique()})
    G = pd.DataFrame(rows).dropna(subset=["book", "actual"])
    G["e_book"] = G["actual"] - G["book"]
    G["e_kal"] = G["actual"] - G["mu"]
    G["disagree"] = G["mu"] - G["book"]
    return G, u


def main():
    G, u = build()
    R = G[G["bucket"] == "regular"]
    print(f"  {len(G):,} fitted games   regular season {len(R):,}")

    print("\n" + "=" * 96)
    print("A — SHARPNESS (regular season)")
    print("=" * 96)
    print(f"  {'price':18}{'RMSE':>9}{'MAE':>9}{'mean resid':>12}"
          f"{'calib slope':>13}{'t vs 1':>9}")
    for lab, col, pr in (("Kalshi implied", "e_kal", "mu"),
                         ("book closing", "e_book", "book")):
        b, t = ols_t(R["actual"].values, [R[pr].values])
        A = np.column_stack([np.ones(len(R)), R[pr].values])
        r = R["actual"].values - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (len(R) - 2))
        print(f"  {lab:18}{np.sqrt((R[col]**2).mean()):>9.3f}"
              f"{R[col].abs().mean():>9.3f}{R[col].mean():>+12.3f}"
              f"{b[1]:>13.4f}{(b[1]-1)/se[1]:>9.2f}")

    print("\n  by segment (dates only, never used to select)")
    seg = [("Oct-Feb", R["date"] < "2026-03-01"),
           ("March", (R["date"] >= "2026-03-01") & (R["date"] < "2026-04-01")),
           ("April+", R["date"] >= "2026-04-01")]
    print(f"  {'segment':12}{'n':>6}{'Kalshi RMSE':>13}{'book RMSE':>11}"
          f"{'K mean e':>10}{'B mean e':>10}")
    for lab, msk in seg:
        s = R[msk]
        if not len(s):
            continue
        print(f"  {lab:12}{len(s):>6}{np.sqrt((s['e_kal']**2).mean()):>13.3f}"
              f"{np.sqrt((s['e_book']**2).mean()):>11.3f}"
              f"{s['e_kal'].mean():>+10.3f}{s['e_book'].mean():>+10.3f}")

    print("\n" + "=" * 96)
    print("B — WHEN THEY DISAGREE, WHO IS RIGHT?")
    print("=" * 96)
    d = R["disagree"]
    print(f"  Kalshi minus book: mean {d.mean():+.3f}  sd {d.std():.3f}  "
          f"|d|>1 in {100*(d.abs()>1).mean():.1f}% of games")
    b, t = ols_t(R["e_book"].values, [d.values])
    print(f"\n  book residual ~ disagreement:  coef {b[1]:+.4f} "
          f"(t={t[1]:+.2f})")
    print(f"    coef ~ +1 means Kalshi is fully right and the book is wrong")
    print(f"    coef ~  0 means the disagreement is pure noise")
    b2, t2 = ols_t(R["e_kal"].values, [(-d).values])
    print(f"  kalshi residual ~ -disagreement: coef {b2[1]:+.4f} "
          f"(t={t2[1]:+.2f})   [the mirror test]")

    print(f"\n  directional: does the sign of the disagreement predict the "
          f"book's over/under?")
    print(f"  {'cell':22}{'n':>6}{'book over %':>13}{'mean e_book':>13}")
    for lab, msk in (("Kalshi > book +0.5", d > 0.5),
                     ("Kalshi within 0.5", d.abs() <= 0.5),
                     ("Kalshi < book -0.5", d < -0.5)):
        s = R[msk]
        live = s[s["e_book"] != 0]
        print(f"  {lab:22}{len(s):>6}"
              f"{100*(live['e_book']>0).mean():>12.2f}%"
              f"{s['e_book'].mean():>+13.3f}")

    print("\n" + "=" * 96)
    print("C — PUSHES: a structural advantage of the ladder")
    print("=" * 96)
    push = (R["e_book"] == 0)
    print(f"  book total is an integer in "
          f"{100*(R['book'] % 1 == 0).mean():.1f}% of games")
    print(f"  book bets that PUSHED: {int(push.sum())} / {len(R)} "
          f"({100*push.mean():.2f}%)")
    print(f"  Kalshi strikes are all .5 -> push rate 0.00% by construction")
    print(f"  effect: {100*push.mean():.2f}% of book bets consume capital and "
          f"return zero edge;")
    print(f"  on ~233 bets/season that is ~{233*push.mean():.1f} wasted bets, "
          f"i.e. the effective")
    print(f"  sample shrinks by that fraction and the establishment horizon "
          f"lengthens by {1/(1-push.mean()):.3f}x")

    print("\n" + "=" * 96)
    print("D — RUNG GRANULARITY AND LADDER SPAN")
    print("=" * 96)
    sp = u.sort_values(["event_ticker", "floor_strike"]).groupby(
        "event_ticker")["floor_strike"].diff().dropna()
    print(f"  strike spacing: median {sp.median():.1f} points   "
          f"mode {sp.mode().iloc[0]:.1f}   "
          f"share == 3.0: {100*(sp == 3.0).mean():.1f}%")
    print(f"  strikes per game: median {G['n_strikes'].median():.0f}")
    # distance from the book total to the nearest available strike
    st = u.groupby("event_ticker")["floor_strike"].apply(
        lambda s: np.array(sorted(s.unique())))
    R2 = R.join(st.rename("strikes"), on="event_ticker")
    R2 = R2[R2["strikes"].notna()]
    dist = R2.apply(lambda r: np.min(np.abs(r["strikes"] - r["book"])), axis=1)
    print(f"\n  distance from the book total to the NEAREST strike:")
    print(f"    mean {dist.mean():.2f}  median {dist.median():.2f}  "
          f"p90 {dist.quantile(.9):.2f}  max {dist.max():.2f} points")
    print(f"    -> a view expressed at the book's number must be shifted by "
          f"this much")
    print(f"       to reach a tradeable rung. Median {dist.median():.2f} points "
          f"against a")
    print(f"       maker hurdle of ~0.03 points and a CrewShock edge of ~1.4 "
          f"points.")

    q = R2.copy()
    q["z_lo"] = (q["q_lo"] - q["mu"]) / q["sd"]
    q["z_hi"] = (q["q_hi"] - q["mu"]) / q["sd"]
    print(f"\n  QUOTABLE SPAN in sd units (rungs with an informative price):")
    print(f"    low  end: mean {q['z_lo'].mean():+.2f} sd  "
          f"(p10 {q['z_lo'].quantile(.1):+.2f})")
    print(f"    high end: mean {q['z_hi'].mean():+.2f} sd  "
          f"(p90 {q['z_hi'].quantile(.9):+.2f})")
    cov = norm.cdf(q["z_hi"]) - norm.cdf(q["z_lo"])
    print(f"    probability mass inside the quoted range: mean "
          f"{cov.mean():.3f}")
    print(f"    -> roughly {100*(1-cov.mean()):.1f}% of the distribution lies "
          f"OUTSIDE the quoted rungs")
    print(f"       and cannot be traded at any price.")


if __name__ == "__main__":
    main()
