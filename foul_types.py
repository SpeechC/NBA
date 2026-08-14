"""Foul-event classification from the raw play-by-play, cached once.

Classification uses EVENTMSGACTIONTYPE (the NBA's own foul-type code on
EVENTMSGTYPE = 6 events), not description-text regex:

    offensive        4 offensive, 26 charge
    def shooting     2 shooting, 29 shooting-block
    def nonshooting  1 personal, 27 personal-block, 28 take,
                     6 away-from-play, 9 clear-path, 17 def-3-second
    other/unknown    everything else: 3 loose ball (side not identifiable),
                     technicals, flagrants, doubles, inbound, ...

Loose-ball fouls are deliberately UNKNOWN: the PBP does not identify which
side was on offense, and the instruction is not to infer what the data does
not support.

FT linkage: every free-throw event (EVENTMSGTYPE = 3) is attributed to the
most recent foul in the same game, period and clock time with a smaller
EVENTNUM. FTs with no matching foul stay unattributed and are reported.

Committing side (home/away) comes from PLAYER1_TEAM_ABBREVIATION mapped
through ADV_TEAM_ABBR_H/R in the advanced game file.

Bonus state is NOT classified separately: penalty status is not carried
reliably at the event level. "Non-shooting defensive fouls that produced FTA"
is the operational equivalent and is what gets reported.
"""
import os
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
OUT = "foul_types_game.csv"

OFFENSIVE = {4, 26}
DEF_SHOOT = {2, 29}
DEF_NONSH = {1, 27, 28, 6, 9, 17}


def extract():
    con = duckdb.connect()
    q = f"""
    SELECT lpad(CAST(GAME_ID AS VARCHAR), 10, '0')      AS gid,
           EVENTNUM, EVENTMSGTYPE  AS msg,
           EVENTMSGACTIONTYPE      AS act,
           PERIOD                  AS period,
           PCTIMESTRING            AS clock,
           PLAYER1_TEAM_ABBREVIATION AS team,
           upper(coalesce(HOMEDESCRIPTION,'') || ' ' ||
                 coalesce(VISITORDESCRIPTION,'')) AS descr
    FROM read_parquet('{PBP}')
    WHERE SEASON_TYPE = 'RegularSeason' AND EVENTMSGTYPE IN (3, 6)
    ORDER BY gid, EVENTNUM
    """
    return con.execute(q).fetchdf()


def classify(e):
    f = e[e["msg"] == 6].copy()
    f["cls"] = "other_unknown"
    f.loc[f["act"].isin(OFFENSIVE), "cls"] = "offensive"
    f.loc[f["act"].isin(DEF_SHOOT), "cls"] = "def_shooting"
    f.loc[f["act"].isin(DEF_NONSH), "cls"] = "def_nonshooting"

    ft = e[e["msg"] == 3].copy()
    ft["made"] = ~ft["descr"].str.contains("MISS", regex=False)

    # merge_asof needs the ON key globally sorted; `by` handles grouping
    f = f.sort_values("EVENTNUM", kind="stable")
    ft = ft.sort_values("EVENTNUM", kind="stable")
    j = pd.merge_asof(
        ft[["gid", "period", "clock", "EVENTNUM", "made"]],
        f[["gid", "period", "clock", "EVENTNUM", "cls"]].rename(
            columns={"EVENTNUM": "foul_num"}),
        left_on="EVENTNUM", right_on="foul_num",
        by=["gid", "period", "clock"], direction="backward")
    unattr = j["cls"].isna().mean()
    fta_by = (j.dropna(subset=["cls"])
               .groupby(["gid", "foul_num", "cls"])
               .agg(fta=("EVENTNUM", "size"), ftm=("made", "sum"))
               .reset_index())
    return f, fta_by, unattr


def build(force=False):
    if os.path.exists(OUT) and not force:
        return pd.read_csv(OUT, dtype={"gid": str})
    e = extract()
    print(f"  {len(e):,} foul/FT events pulled")
    f, fta_by, unattr = classify(e)
    print(f"  {len(f):,} fouls   FT rows unattributed to any foul: "
          f"{100*unattr:.2f}%")

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip().str.zfill(10)
    side = adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R"]]
    f = f.merge(side, on="gid", how="left")
    f["side"] = np.where(f["team"] == f["ADV_TEAM_ABBR_H"], "H",
                np.where(f["team"] == f["ADV_TEAM_ABBR_R"], "R", "?"))
    print(f"  committing side resolved: "
          f"{100*(f['side'] != '?').mean():.2f}%")

    fq = fta_by.groupby(["gid", "cls"])[["fta", "ftm"]].sum().reset_index()
    cnt = (f.groupby(["gid", "cls"]).size().rename("n").reset_index())
    cnt_s = (f[f["side"] != "?"]
             .groupby(["gid", "side", "cls"]).size().rename("n").reset_index())

    g = cnt.pivot(index="gid", columns="cls", values="n").fillna(0)
    g.columns = [f"n_{c}" for c in g.columns]
    q = fq.pivot(index="gid", columns="cls", values=["fta", "ftm"]).fillna(0)
    q.columns = [f"{a}_{b}" for a, b in q.columns]
    hs = cnt_s.pivot_table(index="gid", columns=["side", "cls"], values="n",
                           fill_value=0)
    hs.columns = [f"n_{c}_{s}" for s, c in hs.columns]
    W = g.join(q, how="left").join(hs, how="left").fillna(0).reset_index()
    W["defensive_fouls"] = W["n_def_shooting"] + W["n_def_nonshooting"]
    W["offensive_fouls"] = W["n_offensive"]
    W["total_fouls"] = (W["defensive_fouls"] + W["offensive_fouls"]
                        + W["n_other_unknown"])
    W["fta_def"] = W["fta_def_shooting"] + W["fta_def_nonshooting"]
    W["ftm_def"] = W["ftm_def_shooting"] + W["ftm_def_nonshooting"]
    for s in ("H", "R"):
        W[f"def_fouls_{s}"] = (W.get(f"n_def_shooting_{s}", 0)
                               + W.get(f"n_def_nonshooting_{s}", 0))
    W.to_csv(OUT, index=False)
    return W


def main():
    W = build(force=True)
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip().str.zfill(10)
    adv["yr"] = pd.to_datetime(adv["DATE"]).dt.year
    adv["yr"] = np.where(pd.to_datetime(adv["DATE"]).dt.month >= 8,
                         adv["yr"], adv["yr"] - 1)
    adv["fta_box"] = (pd.to_numeric(adv["EV_FTA_H"], errors="coerce")
                      + pd.to_numeric(adv["EV_FTA_R"], errors="coerce"))
    m = W.merge(adv[["gid", "yr", "fta_box"]], on="gid", how="inner")

    print("\n" + "=" * 100)
    print("CLASSIFICATION AUDIT, BY SEASON — before any CrewShock contact")
    print("=" * 100)
    rows = []
    for y, g in m.groupby("yr"):
        tot = g["total_fouls"].sum()
        fta_link = (g["fta_def"] + g["fta_offensive"].fillna(0)
                    if "fta_offensive" in g else g["fta_def"])
        rows.append({
            "season": y, "games": len(g),
            "fouls/gm": round(g["total_fouls"].mean(), 2),
            "% def": round(100 * g["defensive_fouls"].sum() / tot, 2),
            "% off": round(100 * g["offensive_fouls"].sum() / tot, 2),
            "% unk": round(100 * g["n_other_unknown"].sum() / tot, 2),
            "shoot/gm": round(g["n_def_shooting"].mean(), 2),
            "nonsh/gm": round(g["n_def_nonshooting"].mean(), 2),
            "FTA def/gm": round(g["fta_def"].mean(), 2),
            "FTA box/gm": round(g["fta_box"].mean(), 2),
            "% FTA expl": round(100 * g["fta_def"].sum()
                                / g["fta_box"].sum(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  identity check: def + off + unknown == total on "
          f"{100*np.isclose(m['defensive_fouls']+m['offensive_fouls']+m['n_other_unknown'], m['total_fouls']).mean():.1f}% of games")


if __name__ == "__main__":
    main()
