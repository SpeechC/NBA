"""Walk-forward H1 amplification: trade the book's own under-dispersed signal.

The one calibration defect identified rather than merely hypothesised:

    actual_share = -0.100 + 1.197 * market_share      (t = 11.01)

The book's H1 allocation is INFORMATIVE (its deviations from a constant share
predict the actual allocation at t = 6.28) but UNDER-DISPERSED: its share moves
too little relative to how much the true share moves. So the market itself says
which direction to move; the question is whether it moves far enough.

Unlike the visitor-pace and rematch signals, where the pricing residual vanished,
here the residual is the market's own shrinkage. That is a different object and
deserves one clean out-of-sample test.

THE RULE, frozen:

    using ONLY games before t, estimate mu_A, mu_M and beta by OLS
    predicted_share_t = mu_A + beta * (market_share_t - mu_M)
    H1_pred_t         = FG_line_t * predicted_share_t
    Edge_t            = H1_pred_t - H1_line_t

    Edge > +threshold -> H1 OVER      Edge < -threshold -> H1 UNDER
    thresholds fixed in advance at 0, 0.5, 1.0 points
    P&L at DraftKings' actual closing price, pushes return zero

Because H1_line = FG_line * market_share identically, the rule reduces to

    Edge = FG_line * (alpha + (beta - 1) * market_share)

i.e. it amplifies the book's deviation from a pivot share of alpha/(1-beta). No
sports model enters. The only input is the book's own pair of prices.

DECISIVE RESULT is not whether beta stays near 1.20. It is whether
P(win | |Edge| large) rises monotonically and crosses the actual vig hurdle.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

DK = "/mnt/c/NBA/nba_draftkings_totals_historical.csv"
BURN = 250          # games used to seed the estimate before any bet is placed
THRESH = (0.0, 0.5, 1.0)


def american_profit(p):
    p = pd.to_numeric(p, errors="coerce")
    return np.where(p < 0, 100.0 / np.abs(p), p / 100.0)


def build():
    from halves import period_scores
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    o = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    o["gid"] = o["GAME-ID"].astype(str).str.zfill(10)
    o["date"] = pd.to_datetime(o["DATE"], errors="coerce")
    o["actual_full"] = o["PTS_H"] + o["PTS_R"]
    ps = period_scores("RegularSeason")
    o = o.merge(ps[["gid", "q1", "q2"]], on="gid", how="inner")
    o["actual_h1"] = o["q1"] + o["q2"]
    tm = pd.read_csv("team_mapping.csv")
    ab = dict(zip(tm["bigdataball_name"], tm["abbr"]))
    o["key"] = (o["date"].dt.strftime("%Y-%m-%d") + "_" + o["TEAM_R"].map(ab)
                + "_" + o["TEAM_H"].map(ab))

    dk = pd.read_csv(DK)
    dk["key"] = dk["game_date_et"] + "_" + dk["away_abbr"] + "_" + dk["home_abbr"]
    cols = ["key", "full_game_total_close", "h1_total_close",
            "h1_over_price_close", "h1_under_price_close"]
    dk = dk[cols].dropna(subset=["h1_total_close", "full_game_total_close",
                                 "h1_over_price_close", "h1_under_price_close"])
    j = o.merge(dk, on="key", how="inner").sort_values("date").reset_index(drop=True)
    j["mkt_share"] = j["h1_total_close"] / j["full_game_total_close"]
    j["act_share"] = j["actual_h1"] / j["actual_full"]
    return j


def main():
    j = build()
    print(f"{len(j)} DK games joined, {j['date'].min().date()} .. "
          f"{j['date'].max().date()}")
    print(f"burn-in {BURN} -> {len(j)-BURN} tradeable games\n")

    # ---- walk-forward estimation -------------------------------------------
    preds, betas = [], []
    for i in range(BURN, len(j)):
        tr = j.iloc[:i]
        b, a = np.polyfit(tr["mkt_share"], tr["act_share"], 1)
        ms = j["mkt_share"].iloc[i]
        pred_share = a + b * ms
        h1_pred = j["full_game_total_close"].iloc[i] * pred_share
        preds.append({"i": i, "beta": b, "alpha": a,
                      "edge": h1_pred - j["h1_total_close"].iloc[i]})
        betas.append(b)
    P = pd.DataFrame(preds).set_index("i")
    T = j.loc[P.index].join(P)
    print(f"walk-forward beta: first {betas[0]:.3f}  last {betas[-1]:.3f}  "
          f"mean {np.mean(betas):.3f}  sd {np.std(betas):.3f}")
    print(f"edge: mean {T['edge'].mean():+.3f}  sd {T['edge'].std():.3f}  "
          f"range [{T['edge'].min():+.2f}, {T['edge'].max():+.2f}]\n")

    T["h1_resid"] = T["actual_h1"] - T["h1_total_close"]
    T["side"] = np.where(T["edge"] > 0, "OVER", "UNDER")
    T["price"] = np.where(T["edge"] > 0, T["h1_over_price_close"],
                          T["h1_under_price_close"])
    T["push"] = T["h1_resid"] == 0
    T["won"] = np.where(T["edge"] > 0, T["h1_resid"] > 0, T["h1_resid"] < 0)
    T["profit"] = np.where(T["push"], 0.0,
                           np.where(T["won"], american_profit(T["price"]), -1.0))

    print("=" * 92)
    print("DOES THE EDGE PREDICT? (the Stage-2 question, out of sample)")
    print("=" * 92)
    r = np.corrcoef(T["edge"], T["h1_resid"])[0, 1]
    t = r * np.sqrt(len(T) - 2) / np.sqrt(1 - r * r)
    print(f"  corr(edge, H1 residual) {r:+.4f}   t={t:+.2f}   n={len(T)}")

    print("\n" + "=" * 92)
    print("MONOTONICITY — win rate by |edge| quintile")
    print("=" * 92)
    live = T[~T["push"]].copy()
    live["q"] = pd.qcut(live["edge"].abs(), 5, labels=[1, 2, 3, 4, 5])
    rows = []
    for q, s in live.groupby("q", observed=True):
        w = s["won"].mean()
        se = np.sqrt(w * (1 - w) / len(s))
        be = 1 / (1 + american_profit(s["price"]).mean())
        rows.append({"quintile": q, "n": len(s),
                     "mean |edge|": round(s["edge"].abs().mean(), 2),
                     "win %": round(100 * w, 2),
                     "95% CI": f"[{100*(w-1.96*se):.1f}, {100*(w+1.96*se):.1f}]",
                     "break-even %": round(100 * be, 2),
                     "ROI %": round(100 * s["profit"].sum() / len(s), 2)})
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False))
    mono = tab["win %"].is_monotonic_increasing
    rc = np.corrcoef(np.arange(5), tab["win %"])[0, 1]
    print(f"\n  monotone in win %: {mono}    rank corr {rc:+.3f}")

    print("\n" + "=" * 92)
    print("THRESHOLDS — fixed in advance at 0 / 0.5 / 1.0 points")
    print("=" * 92)
    for th in THRESH:
        s = T[T["edge"].abs() > th]
        sl = s[~s["push"]]
        if len(sl) < 30:
            print(f"  |edge| > {th}: too few bets")
            continue
        w = sl["won"].mean()
        se = np.sqrt(w * (1 - w) / len(sl))
        be = 1 / (1 + american_profit(sl["price"]).mean())
        print(f"  |edge| > {th:<4} n={len(sl):4d}  win {100*w:5.2f}%  "
              f"95% CI [{100*(w-1.96*se):5.2f}, {100*(w+1.96*se):5.2f}]  "
              f"break-even {100*be:.2f}%  "
              f"ROI {100*s['profit'].sum()/len(sl):+6.2f}%")

    print("\n  by side:")
    for sd, g in T.groupby("side"):
        gl = g[~g["push"]]
        print(f"    {sd:5} n={len(g):4d}  win {100*gl['won'].mean():5.2f}%  "
              f"ROI {100*g['profit'].sum()/len(gl):+6.2f}%")


if __name__ == "__main__":
    main()
