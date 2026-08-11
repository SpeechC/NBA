"""Do mismatch games under-run the total? The "just strong enough to win" idea.

The perception: a very strong team facing a very weak one produces a blowout, so
mismatches should be high-scoring. The counter-claim is that the favourite coasts
-- plays to the margin it needs, empties the bench once the game is decided --
so the total comes in UNDER what the mismatch implies.

The framing that makes this worth testing is the split between what the public
sees and what the market prices:

    perception is driven by W-L RECORDS
    pricing is driven by the SPREAD

If those diverge, the gap is where an edge would live. So W-L mismatch is tested
BOTH raw and orthogonalised against the spread -- the second is the real test,
because a raw W-L effect that the spread already captures is not tradable.

W-L records are built walk-forward within each season: a team's record entering a
game counts only games it had already played. Teams need >= 10 games played, so
the first few weeks of each season drop out.

Four questions:
  1. do mismatches actually produce higher totals? (is the perception even true)
  2. does the market price that correctly? (actual vs closing total)
  3. does the FAVOURITE cover? ("just strong enough to win")
  4. does W-L mismatch add anything the spread does not already know?
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

RAW = "/mnt/c/NBA2/dfMaster_OT_2017-2026.csv"
MIN_GP = 10


def build():
    from prepare_data import season_label
    cols = ["GAME-ID", "DATE", "TEAM_H", "TEAM_R", "PTS_H", "PTS_R",
            "OPENING TOTAL_H", "CLOSING TOTAL_H",
            "OPENING SPREAD_H", "CLOSING SPREAD_H"]
    raw = pd.read_csv(RAW, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)][
        cols + ["season"]].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d = d.dropna(subset=["PTS_H", "PTS_R", "CLOSING TOTAL_H", "CLOSING SPREAD_H"])
    d = d.sort_values("date").reset_index(drop=True)
    d["total_pts"] = d["PTS_H"] + d["PTS_R"]
    d["home_win"] = (d["PTS_H"] > d["PTS_R"]).astype(int)

    # walk-forward W-L: record ENTERING each game, within season
    recs = []
    st = {}
    for r in d.itertuples(index=False):
        for team, won in ((r.TEAM_H, r.home_win), (r.TEAM_R, 1 - r.home_win)):
            st.setdefault((r.season, team), [0, 0])
        h = st[(r.season, r.TEAM_H)]
        a = st[(r.season, r.TEAM_R)]
        recs.append((h[0], h[1], a[0], a[1]))
        h[0] += r.home_win; h[1] += 1 - r.home_win
        a[0] += 1 - r.home_win; a[1] += r.home_win
    rec = pd.DataFrame(recs, columns=["hW", "hL", "aW", "aL"])
    d = pd.concat([d.reset_index(drop=True), rec], axis=1)
    d["h_gp"] = d["hW"] + d["hL"]
    d["a_gp"] = d["aW"] + d["aL"]
    d["h_pct"] = d["hW"] / d["h_gp"].replace(0, np.nan)
    d["a_pct"] = d["aW"] / d["a_gp"].replace(0, np.nan)
    d = d[(d["h_gp"] >= MIN_GP) & (d["a_gp"] >= MIN_GP)].copy()

    d["wl_gap"] = (d["h_pct"] - d["a_pct"]).abs()     # perception of mismatch
    d["spread_gap"] = d["CLOSING SPREAD_H"].abs()      # market's view
    d["fav_is_home"] = d["CLOSING SPREAD_H"] < 0
    # did the favourite cover?
    marg = d["PTS_H"] - d["PTS_R"]
    d["fav_margin"] = np.where(d["fav_is_home"], marg, -marg)
    d["fav_cover"] = d["fav_margin"] - d["spread_gap"]
    d["over"] = d["total_pts"] - d["CLOSING TOTAL_H"]
    return d


def strat(d, col, label):
    q = pd.qcut(d[col], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    rows = []
    for g, s in d.groupby(q, observed=True):
        live = s[s["total_pts"] != s["CLOSING TOTAL_H"]]
        push_f = s[s["fav_cover"] != 0]
        rows.append({
            "quintile": g, "n": len(s),
            f"mean {label}": round(s[col].mean(), 3),
            "mean total": round(s["total_pts"].mean(), 2),
            "mean close": round(s["CLOSING TOTAL_H"].mean(), 2),
            "actual-close": round(s["over"].mean(), 3),
            "over %": round(100 * (live["over"] > 0).mean(), 2),
            "fav margin": round(s["fav_margin"].mean(), 2),
            "fav cover %": round(100 * (push_f["fav_cover"] > 0).mean(), 2),
        })
    return pd.DataFrame(rows)


def main():
    d = build()
    print(f"{len(d):,} games with both teams at {MIN_GP}+ games played, "
          f"{d['date'].min().date()} .. {d['date'].max().date()}\n")

    print("=" * 104)
    print("1-3. Stratified by W-L GAP (what the public sees)")
    print("=" * 104)
    print(strat(d, "wl_gap", "wl gap").to_string(index=False))

    print("\n" + "=" * 104)
    print("Stratified by |SPREAD| (what the market prices)")
    print("=" * 104)
    print(strat(d, "spread_gap", "|spread|").to_string(index=False))

    print("\n" + "=" * 104)
    print("4. Does W-L gap add anything BEYOND the spread?")
    print("=" * 104)
    # residualise wl_gap on |spread|, then stratify the total residual by it
    X = np.c_[np.ones(len(d)), d["spread_gap"], d["CLOSING TOTAL_H"]]
    beta, *_ = np.linalg.lstsq(X, d["wl_gap"].values, rcond=None)
    d["wl_orth"] = d["wl_gap"] - X @ beta
    print(f"corr(wl_gap, |spread|) = "
          f"{np.corrcoef(d['wl_gap'], d['spread_gap'])[0,1]:.4f}")
    q = pd.qcut(d["wl_orth"], 5, labels=[1, 2, 3, 4, 5])
    rows = []
    for g, s in d.groupby(q, observed=True):
        live = s[s["total_pts"] != s["CLOSING TOTAL_H"]]
        pf = s[s["fav_cover"] != 0]
        rows.append({"quintile": g, "n": len(s),
                     "mean wl_orth": round(s["wl_orth"].mean(), 3),
                     "actual-close": round(s["over"].mean(), 3),
                     "over %": round(100 * (live["over"] > 0).mean(), 2),
                     "fav cover %": round(100 * (pf["fav_cover"] > 0).mean(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 104)
    print("Extreme mismatches only")
    print("=" * 104)
    for name, sub in (("wl gap > 0.35", d[d["wl_gap"] > 0.35]),
                      ("wl gap > 0.45", d[d["wl_gap"] > 0.45]),
                      ("|spread| >= 10", d[d["spread_gap"] >= 10]),
                      ("|spread| >= 12", d[d["spread_gap"] >= 12]),
                      ("wl>0.35 AND |spread|>=10",
                       d[(d["wl_gap"] > 0.35) & (d["spread_gap"] >= 10)])):
        live = sub[sub["total_pts"] != sub["CLOSING TOTAL_H"]]
        pf = sub[sub["fav_cover"] != 0]
        if len(live) < 40:
            print(f"{name:28} n={len(sub):5d}  (too few)")
            continue
        ov = (live["over"] > 0).mean()
        cv = (pf["fav_cover"] > 0).mean()
        t, p = stats.ttest_1samp(sub["over"], 0.0)
        print(f"{name:28} n={len(sub):5d}  actual-close {sub['over'].mean():+6.3f}"
              f"  over {100*ov:5.2f}%  fav cover {100*cv:5.2f}%"
              f"  t={t:+5.2f} p={p:.3f}")


if __name__ == "__main__":
    main()
