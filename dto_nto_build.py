"""Build the Q4 DTO/NTO panel. Structural only -- no market variable."""
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

DTO = {4, 37}          # traveling, offensive foul   (Price/Remer/Stone "discretionary")
NTO = {1, 2}           # bad pass, lost ball         ("non-discretionary")


def build():
    cols = ["GAME_ID", "PERIOD", "EVENTMSGTYPE", "EVENTMSGACTIONTYPE",
            "HOMEDESCRIPTION", "VISITORDESCRIPTION", "PLAYER1_TEAM_ID",
            "SEASON", "SEASON_TYPE"]
    p = pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet", columns=cols)
    p = p[(p.SEASON_TYPE == "RegularSeason") & (p.EVENTMSGTYPE == 5)]
    p = p.drop_duplicates(["GAME_ID", "PERIOD", "EVENTMSGACTIONTYPE",
                           "HOMEDESCRIPTION", "VISITORDESCRIPTION"])
    p = p[p.PERIOD == 4].copy()
    p["kind"] = np.where(p.EVENTMSGACTIONTYPE.isin(DTO), "DTO",
                np.where(p.EVENTMSGACTIONTYPE.isin(NTO), "NTO", None))
    p = p.dropna(subset=["kind", "PLAYER1_TEAM_ID"])
    p = p[p.PLAYER1_TEAM_ID > 0]
    p["gid"] = p.GAME_ID.astype(str).str.strip()
    ct = (p.groupby(["gid", "PLAYER1_TEAM_ID", "kind"]).size()
          .unstack(fill_value=0).reset_index()
          .rename(columns={"PLAYER1_TEAM_ID": "team_id"}))
    for c in ("DTO", "NTO"):
        if c not in ct: ct[c] = 0

    from prepare_data import read_master, season_label
    raw = read_master(verbose=False)
    raw["season"] = season_label(raw).astype(str)
    raw = raw[raw.season.str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(raw[c], errors="coerce")
    g = pd.DataFrame({
        "gid": raw["GAME-ID"].astype(str).str.strip(),
        "season": raw.season.values,
        "h3": n("1Q_H") + n("2Q_H") + n("3Q_H"),
        "r3": n("1Q_R") + n("2Q_R") + n("3Q_R"),
        "h4": n("4Q_H"), "r4": n("4Q_R"),
        "th": raw["TEAM_H"].astype(str).str.strip(),
        "tr": raw["TEAM_R"].astype(str).str.strip()}).dropna()
    tm = pd.read_csv("team_mapping.csv")
    m = dict(zip(tm.bigdataball_name, tm.team_id))
    g["hid"] = g.th.map(m); g["rid"] = g.tr.map(m)
    g = g.dropna(subset=["hid", "rid"])

    ch = ct.rename(columns={"team_id": "hid", "DTO": "DTO_h", "NTO": "NTO_h"})
    cr = ct.rename(columns={"team_id": "rid", "DTO": "DTO_r", "NTO": "NTO_r"})
    g = g.merge(ch, on=["gid", "hid"], how="inner").merge(cr, on=["gid", "rid"], how="inner")

    g["lead3"] = g.h3 - g.r3                       # home lead after 3
    g = g[g.lead3 != 0].copy()                     # a leader must exist
    home_leads = g.lead3 > 0
    g["D"] = g.lead3.abs()                         # deficit size
    # orient to LEADING minus TRAILING
    g["dDTO"] = np.where(home_leads, g.DTO_h - g.DTO_r, g.DTO_r - g.DTO_h)
    g["dNTO"] = np.where(home_leads, g.NTO_h - g.NTO_r, g.NTO_r - g.NTO_h)
    g["q4_trail_margin"] = np.where(home_leads, g.r4 - g.h4, g.h4 - g.r4)
    g["tot_to"] = g[["DTO_h", "DTO_r", "NTO_h", "NTO_r"]].sum(axis=1)
    return g


if __name__ == "__main__":
    g = build()
    print(f"games with Q4 turnover data and a Q3 leader: {len(g):,}")
    print(f"seasons: {sorted(set(s[:8] for s in g.season))}")
    print(f"\nQ3 deficit D: median {g.D.median():.0f}  "
          f"p90 {g.D.quantile(.9):.0f}  max {g.D.max():.0f}")
    print(f"  D>=12 on {int((g.D>=12).sum()):,} games ({100*(g.D>=12).mean():.1f}%)")
    print(f"\nQ4 turnover counts per game: DTO {g[['DTO_h','DTO_r']].sum(axis=1).mean():.2f}  "
          f"NTO {g[['NTO_h','NTO_r']].sum(axis=1).mean():.2f}")
    print(f"  DTO share of the two: "
          f"{100*g[['DTO_h','DTO_r']].sum(axis=1).sum()/g.tot_to.sum():.1f}%")
    print(f"\nERA CHECK - DTO share of (DTO+NTO) by season:")
    for s, x in g.groupby(g.season.str[:8]):
        d = x[['DTO_h','DTO_r']].sum(axis=1).sum(); t = x.tot_to.sum()
        print(f"   {s}  n={len(x):>5,}  DTO share {100*d/t:5.1f}%  "
              f"mean dDTO {x.dDTO.mean():+.3f}  mean dNTO {x.dNTO.mean():+.3f}")
