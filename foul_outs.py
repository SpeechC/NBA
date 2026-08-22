"""TEST 2 — do disqualifications carry CrewShock into the MARGIN market?

CrewTilt failed: officials do not differ in WHOM they whistle (no trait,
between-official true SD = 0). But disqualification is a RULES DISCONTINUITY
that tilt-neutral officiating still activates: six personal fouls removes a
player, and favourites depend on their stars more than underdogs do. So a
whistle-heavy crew could raise margin variance and/or favour underdogs through
a channel CrewTilt never tested.

CHAIN, tested link by link:
  1  CrewShock -> foul-outs per game                (does the institution bind?)
  2  foul-outs -> |margin| and the favourite's cover (does the rule matter?)
  3  CrewShock -> favourite cover / |margin|         (does it reach the market?)
  4  is it PRICED?  c_true vs c_market on the spread

Foul-outs are counted from the play-by-play: personal fouls per (game, player),
excluding technicals (which do not count toward the six). PBP runs
2017-18..2024-25.

Everything uses the FROZEN CrewShock from ref_features.csv. Nothing is retuned.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
THR = 0.8682

SQL = f"""
SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0')  AS gid,
       PLAYER1_ID                              AS pid,
       PLAYER1_TEAM_ABBREVIATION               AS abbr,
       count(*)                                AS pf
FROM read_parquet('{PBP}')
WHERE SEASON_TYPE='RegularSeason' AND EVENTMSGTYPE=6
  AND PLAYER1_ID > 0 AND PLAYER1_TEAM_ABBREVIATION IS NOT NULL
  AND upper(coalesce(HOMEDESCRIPTION,'')||' '||coalesce(NEUTRALDESCRIPTION,'')
            ||' '||coalesce(VISITORDESCRIPTION,'')) NOT LIKE '%TECHNICAL%'
GROUP BY gid, pid, abbr
"""


def build():
    p = duckdb.connect().execute(SQL).fetchdf()
    p["gid"] = p["gid"].astype(str)
    p["dq"] = (p["pf"] >= 6).astype(int)
    per = p.groupby(["gid", "abbr"], as_index=False).agg(
        dq=("dq", "sum"), max_pf=("pf", "max"), five=("pf", lambda s:
                                                      int((s >= 5).sum())))
    g = per.groupby("gid", as_index=False).agg(dq_game=("dq", "sum"),
                                              five_game=("five", "sum"))
    g = g.rename(columns={"gid": "gidz"})

    m = refs.build()
    m["gidz"] = m["GAME-ID"].astype(str).str.strip().str.zfill(10)
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["margin"] = n("PTS_H") - n("PTS_R")
    m["sres"] = m["margin"] + m["spread"]
    # favourite cover: sign(sres) opposite to sign(spread)
    fav = np.where(m["spread"] < 0, m["sres"],
                   np.where(m["spread"] > 0, -m["sres"], np.nan))
    m["fav_cover"] = np.where(fav > 0, 1.0, np.where(fav < 0, 0.0, np.nan))
    m["abs_margin"] = m["margin"].abs()
    m["abs_spread"] = m["spread"].abs()

    f = pd.read_csv("ref_features.csv")
    f["gidz"] = f["gid"].astype(str).str.strip().str.zfill(10)
    m = m.merge(f[["gidz", "CrewShock", "pf_rate"]], on="gidz", how="left")
    d = m.merge(g, on="gidz", how="inner")
    d["z"] = (d["CrewShock"] - 0.0047) / 0.8233        # per pooled SD, frozen
    # per-team panel for the "whose star" question
    return d.dropna(subset=["CrewShock", "spread", "margin"]), per


def reg(x, y, X):
    s = x.dropna(subset=[y] + X)
    b, se, t = ols(s[y].values, np.column_stack([s[c].values for c in X]))
    return b, t, len(s)


def main():
    d, per = build()
    print(f"  {len(d):,} games with PBP fouls and frozen CrewShock   "
          f"seasons {sorted(d['yr'].unique())}")
    print(f"  disqualifications per game: mean {d['dq_game'].mean():.3f}   "
          f"share of games with >=1: {100*(d['dq_game']>0).mean():.2f}%")
    print(f"  players reaching 5 fouls per game: "
          f"{d['five_game'].mean():.2f}")

    print("\n" + "=" * 92)
    print("LINK 1 — does CrewShock produce foul-outs?")
    print("=" * 92)
    for lab, x in (("development", d[d["date"] < SPLIT_DATE]),
                   ("holdout", d[d["date"] >= SPLIT_DATE])):
        for y, nm in (("dq_game", "disqualifications"),
                      ("five_game", "players at 5 fouls")):
            b, t, n = reg(x, y, ["z"])
            print(f"  {lab:12} CrewShock -> {nm:22} {b[1]:+.4f} "
                  f"(t={t[1]:+.2f})  n={n:,}")

    print("\n" + "=" * 92)
    print("LINK 2 — do foul-outs move the margin?")
    print("=" * 92)
    print(f"  {'dq in game':>12}{'n':>7}{'|margin|':>10}{'fav cover %':>13}")
    for k in (0, 1, 2, 3):
        s = d[d["dq_game"] == k] if k < 3 else d[d["dq_game"] >= 3]
        if len(s) < 20:
            continue
        lab = f">={k}" if k == 3 else str(k)
        print(f"  {lab:>12}{len(s):>7,}{s['abs_margin'].mean():>10.3f}"
              f"{100*s['fav_cover'].mean():>13.2f}")
    b, t, n = reg(d, "abs_margin", ["dq_game", "abs_spread"])
    print(f"\n  |margin| ~ dq + |spread|:  dq {b[1]:+.4f} (t={t[1]:+.2f})")
    b, t, n = reg(d, "fav_cover", ["dq_game", "abs_spread"])
    print(f"  fav_cover ~ dq + |spread|: dq {b[1]:+.4f} (t={t[1]:+.2f})")

    print("\n" + "=" * 92)
    print("LINK 3 — does CrewShock reach the margin market?")
    print("=" * 92)
    for lab, x in (("development", d[d["date"] < SPLIT_DATE]),
                   ("holdout", d[d["date"] >= SPLIT_DATE]), ("pooled", d)):
        b1, t1, _ = reg(x, "abs_margin", ["z", "abs_spread"])
        b2, t2, n = reg(x, "fav_cover", ["z", "abs_spread"])
        print(f"  {lab:12} CrewShock -> |margin| {b1[1]:+.4f} (t={t1[1]:+.2f})"
              f"   -> fav cover {b2[1]:+.4f} (t={t2[1]:+.2f})  n={n:,}")

    print("\n" + "=" * 92)
    print("LINK 4 — is it priced?  c_true vs c_market on the SPREAD")
    print("=" * 92)
    d["imp_margin"] = -d["spread"]
    for lab, x in (("development", d[d["date"] < SPLIT_DATE]),
                   ("holdout", d[d["date"] >= SPLIT_DATE])):
        bt, tt, _ = reg(x, "margin", ["z"])
        bm, tm, _ = reg(x, "imp_margin", ["z"])
        be, te, n = reg(x, "sres", ["z"])
        print(f"  {lab:12} c_true {bt[1]:+.4f} (t={tt[1]:+.2f})   "
              f"c_market {bm[1]:+.4f} (t={tm[1]:+.2f})   "
              f"gap {be[1]:+.4f} (t={te[1]:+.2f})")

    print("\n" + "=" * 92)
    print("THE FROZEN-THRESHOLD CELL: CrewShock >= Q85")
    print("=" * 92)
    hi = d[d["CrewShock"] >= THR]
    lo = d[d["CrewShock"] < THR]
    print(f"  {'cell':10}{'n':>7}{'dq/game':>10}{'|margin|':>10}"
          f"{'fav cover %':>13}{'underdog cover %':>18}")
    for lab, s in (("HIGH", hi), ("rest", lo)):
        print(f"  {lab:10}{len(s):>7,}{s['dq_game'].mean():>10.3f}"
              f"{s['abs_margin'].mean():>10.3f}"
              f"{100*s['fav_cover'].mean():>13.2f}"
              f"{100*(1-s['fav_cover'].mean()):>18.2f}")


if __name__ == "__main__":
    main()
