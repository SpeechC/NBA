"""The first real pricing test: does the visitor pace-allocation signal beat
DraftKings' H1 total?

DATA. 513 DraftKings games, 2023-10-24 to 2023-12-31, with closing full-game and
H1 totals and the actual over/under prices. The tradable security is the H1
total, so P&L uses DK's own closing price, not an assumed -110.

SIGNAL, strictly out of sample. These games are 2023-24; the signal uses ONLY
seasons before it (2017-18 .. 2022-23):

    S_i = (visitor's mean road H2-H1 over prior seasons) - (league mean)

    S > 0  visitor historically shifts scoring INTO H2  -> bet H1 UNDER
    S < 0  visitor historically shifts scoring INTO H1  -> bet H1 OVER

The cutoff is sign(S). Nothing is optimised on these 513 games.

THREE TESTS

  1 tradable      H1_actual - H1_line = a + b*S,        hypothesis b < 0
  2 mechanism     AllocationError     = a + b*S,        hypothesis b > 0
                  where AllocationError = actual(H2-H1) - market(H2-H1)
                  and market(H2-H1) = full_game_line - 2*H1_line
  3 betting       sign(S) rule at DK's closing price, one unit per game

  plus TERCILES of S, formed without reference to returns: H1 outcomes should
  move monotonically from the H1-heavy visitor group to the H2-heavy group. That
  is more convincing than an aggregate betting record.

H2 actual is (full-game actual - H1 actual) so it includes overtime, matching how
the market's implied H2 is constructed from its full-game line.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

DK = "/mnt/c/NBA/nba_draftkings_totals_historical.csv"
MIN_PRIOR = 60
TARGET_SEASON = 2023          # the DK sample's season; signal uses < this


def american_profit(price):
    """Profit per 1 unit risked on a winning bet."""
    p = pd.to_numeric(price, errors="coerce")
    return np.where(p < 0, 100.0 / np.abs(p), p / 100.0)


def build():
    from bench_oos import build as bench_build
    from halves import period_scores
    from prepare_data import CSV, season_label

    # ---- our game data, 2023-24 --------------------------------------------
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    o = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    o["gid"] = o["GAME-ID"].astype(str).str.zfill(10)
    o["date"] = pd.to_datetime(o["DATE"], errors="coerce")
    o["actual_full"] = o["PTS_H"] + o["PTS_R"]
    ps = period_scores("RegularSeason")
    o = o.merge(ps[["gid", "q1", "q2"]], on="gid", how="inner")
    o["actual_h1"] = o["q1"] + o["q2"]
    o["actual_h2"] = o["actual_full"] - o["actual_h1"]

    tm = pd.read_csv("team_mapping.csv")
    m = dict(zip(tm["bigdataball_name"], tm["abbr"]))
    o["home_abbr"] = o["TEAM_H"].map(m)
    o["away_abbr"] = o["TEAM_R"].map(m)
    assert o["home_abbr"].notna().all() and o["away_abbr"].notna().all()
    o["key"] = (o["date"].dt.strftime("%Y-%m-%d") + "_" + o["away_abbr"]
                + "_" + o["home_abbr"])

    # ---- DraftKings ---------------------------------------------------------
    dk = pd.read_csv(DK)
    dk["key"] = (dk["game_date_et"] + "_" + dk["away_abbr"] + "_"
                 + dk["home_abbr"])
    keep = ["key", "game_date_et", "away_abbr", "home_abbr",
            "full_game_total_close", "h1_total_close",
            "h1_over_price_close", "h1_under_price_close",
            "market_h2_minus_h1_close"]
    dk = dk[keep].dropna(subset=["h1_total_close", "full_game_total_close"])
    print(f"DK rows with both closing lines: {len(dk)}")

    j = dk.merge(o[["key", "gid", "date", "actual_h1", "actual_h2",
                    "actual_full", "TEAM_R"]], on="key", how="inner")
    print(f"joined to our data on (date, away, home): {len(j)}  "
          f"({100*len(j)/len(dk):.1f}% of DK rows)")

    # ---- strictly OOS visitor signal ---------------------------------------
    gg, L = bench_build()
    road = L[L["road"] & (L["yr"] < TARGET_SEASON)]
    sig = road.groupby("team").agg(S_raw=("h21", "mean"),
                                   n=("h21", "size")).reset_index()
    sig = sig[sig["n"] >= MIN_PRIOR]
    league = road["h21"].mean()
    sig["S"] = sig["S_raw"] - league
    print(f"signal from seasons < {TARGET_SEASON}: "
          f"{sig['n'].sum():,} prior road games, league mean H2-H1 {league:+.3f}")
    sig["abbr"] = sig["team"].map(dict(zip(
        pd.read_csv("team_mapping.csv")["bigdataball_name"],
        pd.read_csv("team_mapping.csv")["abbr"])))
    j = j.merge(sig[["abbr", "S"]].rename(columns={"abbr": "away_abbr"}),
                on="away_abbr", how="inner")
    print(f"with a visitor signal: {len(j)}\n")

    j["h1_resid"] = j["actual_h1"] - j["h1_total_close"]
    j["market_alloc"] = j["full_game_total_close"] - 2 * j["h1_total_close"]
    j["actual_alloc"] = j["actual_h2"] - j["actual_h1"]
    j["alloc_err"] = j["actual_alloc"] - j["market_alloc"]
    return j


def main():
    j = build()
    print("=" * 96)
    print("TEST 1 (tradable) — H1_actual - H1_line = a + b*S,  hypothesis b < 0")
    print("=" * 96)
    for col, lab, want in (("h1_resid", "H1 residual", "b < 0"),
                           ("alloc_err", "allocation error", "b > 0")):
        r = np.corrcoef(j["S"], j[col])[0, 1]
        b, a = np.polyfit(j["S"], j[col], 1)
        t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
        print(f"  {lab:18} corr {r:+.4f}   slope {b:+.4f}   t={t:+.2f}   "
              f"(hypothesis {want})")
    print("\n  sanity: market alloc mean "
          f"{j['market_alloc'].mean():+.3f}   actual alloc mean "
          f"{j['actual_alloc'].mean():+.3f}   error {j['alloc_err'].mean():+.3f}")

    print("\n" + "=" * 96)
    print("TERCILES of S (formed without reference to returns)")
    print("=" * 96)
    j["terc"] = pd.qcut(j["S"], 3, labels=["H1-heavy (S<0)", "middle",
                                           "H2-heavy (S>0)"])
    rows = []
    for g, s in j.groupby("terc", observed=True):
        live = s[s["h1_resid"] != 0]
        rows.append({"tercile": g, "n": len(s), "mean S": round(s["S"].mean(), 3),
                     "H1 resid": round(s["h1_resid"].mean(), 3),
                     "H1 over %": round(100 * (live["h1_resid"] > 0).mean(), 2),
                     "alloc err": round(s["alloc_err"].mean(), 3)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print(f"\n  H1 residual monotone DECREASING across terciles: "
          f"{list(t['H1 resid']) == sorted(t['H1 resid'], reverse=True)}")
    print(f"  allocation error monotone INCREASING: "
          f"{list(t['alloc err']) == sorted(t['alloc err'])}")

    print("\n" + "=" * 96)
    print("TEST 3 (betting) — sign(S) rule at DK closing prices, 1u per game")
    print("=" * 96)
    j["side"] = np.where(j["S"] > 0, "UNDER", "OVER")
    j["price"] = np.where(j["S"] > 0, j["h1_under_price_close"],
                          j["h1_over_price_close"])
    j = j.dropna(subset=["price"])
    won = np.where(j["S"] > 0, j["h1_resid"] < 0, j["h1_resid"] > 0)
    push = j["h1_resid"] == 0
    j["won"], j["push"] = won, push
    j["profit"] = np.where(push, 0.0,
                           np.where(won, american_profit(j["price"]), -1.0))
    live = j[~push]
    risked = len(live)
    print(f"  {len(j)} bets  ({int(push.sum())} pushes)   "
          f"UNDER {int((j['side']=='UNDER').sum())} / "
          f"OVER {int((j['side']=='OVER').sum())}")
    wr = live["won"].mean()
    se = np.sqrt(wr * (1 - wr) / len(live))
    print(f"  win rate {100*wr:.2f}%  95% CI "
          f"[{100*(wr-1.96*se):.2f}, {100*(wr+1.96*se):.2f}]")
    print(f"  mean DK price: {j['price'].mean():.1f}   "
          f"break-even at that price ~{100*(1/(1+american_profit(j['price']).mean())):.2f}%")
    print(f"  profit {j['profit'].sum():+.2f}u on {risked} risked   "
          f"ROI {100*j['profit'].sum()/risked:+.2f}%")

    print("\n  by side:")
    for s, g in j.groupby("side"):
        gl = g[~g["push"]]
        print(f"    {s:5} n={len(g):3d}  win {100*gl['won'].mean():5.2f}%  "
              f"profit {g['profit'].sum():+7.2f}u  "
              f"ROI {100*g['profit'].sum()/len(gl):+6.2f}%")

    print("\n  by |S| quartile (magnitude of the signal):")
    j["mag"] = pd.qcut(j["S"].abs(), 4, labels=[1, 2, 3, 4])
    for q, g in j.groupby("mag", observed=True):
        gl = g[~g["push"]]
        print(f"    Q{q} |S| mean {g['S'].abs().mean():.2f}  n={len(g):3d}  "
              f"win {100*gl['won'].mean():5.2f}%  "
              f"ROI {100*g['profit'].sum()/len(gl):+6.2f}%")


if __name__ == "__main__":
    main()
