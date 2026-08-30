"""Q4 foul differential and the free-throw channel — executes PREREG_foul_q4.md."""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from dto_nto_q4 import ols_t, fl          # reuse the frozen helpers
from prepare_data import read_master, season_label

NTO_CODES = {1, 2}
FOUL_KEEP = {1, 2, 3, 4, 26, 27}          # ordinary personal fouls
FOUL_DROP = {28, 6, 11, 16, 17, 14}       # take, away-from-play, technical, flagrant
FT_PCT = 0.77
LAST3 = 2700                               # elapsed seconds; Q4 ends at 2880


def build(drop_last3=False):
    cols = ["GAME_ID", "PERIOD", "PCTIMESTRING", "EVENTMSGTYPE",
            "EVENTMSGACTIONTYPE", "PLAYER1_TEAM_ID", "SEASON_TYPE"]
    p = pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet", columns=cols)
    p = p[(p.SEASON_TYPE == "RegularSeason") & (p.PERIOD == 4)]
    p = p.drop_duplicates(["GAME_ID", "PERIOD", "PCTIMESTRING", "EVENTMSGTYPE",
                           "EVENTMSGACTIONTYPE", "PLAYER1_TEAM_ID"])
    if drop_last3:
        p = p[p.PCTIMESTRING < LAST3]
    p = p[p.PLAYER1_TEAM_ID > 0].copy()
    p["gid"] = p.GAME_ID.astype(str).str.strip()

    def tag(row_mask, name):
        return (p[row_mask].groupby(["gid", "PLAYER1_TEAM_ID"]).size()
                .rename(name).reset_index())

    foul = tag((p.EVENTMSGTYPE == 6) & p.EVENTMSGACTIONTYPE.isin(FOUL_KEEP), "FOUL")
    take = tag((p.EVENTMSGTYPE == 6) & (p.EVENTMSGACTIONTYPE == 28), "TAKE")
    nto  = tag((p.EVENTMSGTYPE == 5) & p.EVENTMSGACTIONTYPE.isin(NTO_CODES), "NTO")
    fta  = tag(p.EVENTMSGTYPE == 3, "FTA")
    fga  = tag(p.EVENTMSGTYPE.isin([1, 2]), "FGA")
    ct = foul
    for x in (take, nto, fta, fga):
        ct = ct.merge(x, on=["gid", "PLAYER1_TEAM_ID"], how="outer")
    ct = ct.fillna(0).rename(columns={"PLAYER1_TEAM_ID": "tid"})

    raw = read_master(verbose=False); raw["season"] = season_label(raw).astype(str)
    raw = raw[raw.season.str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(raw[c], errors="coerce")
    g = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip(),
        "season": raw.season.values,
        "h3": n("1Q_H")+n("2Q_H")+n("3Q_H"), "r3": n("1Q_R")+n("2Q_R")+n("3Q_R"),
        "h4": n("4Q_H"), "r4": n("4Q_R"),
        "th": raw["TEAM_H"].astype(str).str.strip(),
        "tr": raw["TEAM_R"].astype(str).str.strip()}).dropna()
    tm = pd.read_csv("team_mapping.csv"); m = dict(zip(tm.bigdataball_name, tm.team_id))
    g["hid"] = g.th.map(m); g["rid"] = g.tr.map(m); g = g.dropna(subset=["hid","rid"])
    C = ["FOUL","TAKE","NTO","FTA","FGA"]
    g = g.merge(ct.rename(columns={"tid":"hid", **{c:c+"_h" for c in C}}), on=["gid","hid"])
    g = g.merge(ct.rename(columns={"tid":"rid", **{c:c+"_r" for c in C}}), on=["gid","rid"])
    g["lead3"] = g.h3 - g.r3; g = g[g.lead3 != 0].copy()
    hl = g.lead3 > 0
    g["D"] = g.lead3.abs()
    for c in C:                                    # leading minus trailing
        g["d"+c] = np.where(hl, g[c+"_h"] - g[c+"_r"], g[c+"_r"] - g[c+"_h"])
    g["dFTA"] = -g.dFTA                            # trailing minus leading
    g["dFGA"] = -g.dFGA
    g["q4_trail_margin"] = np.where(hl, g.r4 - g.h4, g.h4 - g.r4)
    g["Y_f"] = g.dFOUL - g.dNTO
    return g


def run(g, tag=""):
    for s in sorted(g.season.unique())[:-1]:
        g[f"S{s[4:8]}"] = (g.season == s).astype(float)
    S = [c for c in g.columns if c.startswith("S2")]
    print(f"\n=== P1 PRIMARY {tag} — Y_f = dFOUL - dNTO ~ D  (predicted > 0) ===")
    b1 = fl(g, g.Y_f.values, "D", S, "Y_f ~ D")
    print(f"    components: dFOUL ~ D", end="  ")
    bF = fl(g, g.dFOUL.values, "D", S, "dFOUL ~ D", one_sided=False)
    print(f"=== P2 {tag} — dFTA ~ D + dFGA  (predicted > 0) ===")
    b2 = fl(g, g.dFTA.values, "D", ["dFGA"] + S, "dFTA ~ D | dFGA")
    return b1, bF, b2, S


g = build()
print(f"n={len(g):,} games   D>=12 on {int((g.D>=12).sum()):,}")
print("\n=== P0 CONFOUND CHECK — take fouls (excluded) by deficit ===")
print(f"    {'D bucket':<10}{'n':>7}{'take fouls/gm':>15}{'dFOUL':>9}{'dNTO':>8}{'dFTA':>8}")
for lo,hi,lab in [(1,6,'1-5'),(6,12,'6-11'),(12,20,'12-19'),(20,99,'20+')]:
    x = g[(g.D>=lo)&(g.D<hi)]
    if len(x)<50: continue
    print(f"    {lab:<10}{len(x):>7,}{(x.TAKE_h+x.TAKE_r).mean():>15.3f}"
          f"{x.dFOUL.mean():>+9.3f}{x.dNTO.mean():>+8.3f}{x.dFTA.mean():>+8.3f}")

b1,bF,b2,S = run(g, "(full Q4)")
mD = float(np.mean(g.D[g.D>=12]))
print(f"\n=== P3 MAGNITUDE — vs the +1.283 pt residual from the turnover test ===")
pts = b2*mD*FT_PCT
print(f"    dFTA slope {b2:+.5f} FTA per point of deficit -> {b2*mD:+.3f} FTA at D={mD:.0f}")
print(f"    -> {pts:+.3f} points at FT%={FT_PCT}")
print(f"    that is {100*pts/1.283:+.1f}% of the +1.283 residual, "
      f"{100*pts/1.65:+.1f}% of the whole +1.65 effect")

print("\n" + "="*66)
print("ROBUSTNESS — excluding the last 3:00 of Q4 (intentional-foul window)")
g3 = build(drop_last3=True)
print(f"n={len(g3):,}")
r1,rF,r2,_ = run(g3, "(no last 3:00)")
pts3 = r2*float(np.mean(g3.D[g3.D>=12]))*FT_PCT
print(f"\n    dFTA -> {pts3:+.3f} pts  = {100*pts3/1.283:+.1f}% of the residual")
