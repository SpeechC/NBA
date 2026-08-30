import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
def canon(s):
    return (pd.Series(s,dtype="object").astype(str)
            .str.replace(r"\b(Jr|Sr|II|III|IV)\b\.?","",regex=True)
            .str.replace(r"[.\-'`]","",regex=True)
            .str.replace(r"\s+"," ",regex=True).str.strip().str.lower())
# 1. pid -> canonical name, from PBP
pb=pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet",
                   columns=["PLAYER1_ID","PLAYER1_NAME","GAMEDATE","SEASON"])
pb=pb.dropna(subset=["PLAYER1_ID","PLAYER1_NAME"])
nm=pb.groupby("PLAYER1_ID").PLAYER1_NAME.agg(lambda s:s.mode().iloc[0]).reset_index()
nm.columns=["pid","name"]; nm["key"]=canon(nm.name)
print(f"pid->name map: {len(nm):,} players")
# 2. player scoring rate, PRIOR-ONLY (prior season mean, shrunk to league)
pg=pd.read_parquet("/home/dpope/data/player_game_pts.parquet")
print(f"player-game pts: {len(pg):,}  seasons {pg.season.min()}..{pg.season.max()}")
ps=pg.groupby(["pid","season"]).pts.agg(["mean","size"]).reset_index()
ps.columns=["pid","season","ppg","gp"]
ps["yr"]=ps.season.str.slice(0,4).astype(int)
ps["yr_use"]=ps.yr+1                       # prior season -> use in the NEXT season
lg=ps.ppg.mean()
ps["ppg_sh"]=(ps.gp*ps.ppg+8*lg)/(ps.gp+8)  # shrink thin samples toward league mean
rate=ps.set_index(["pid","yr_use"]).ppg_sh
# 3. injury panel -> EARLIEST report per game (most likely to precede the opener)
inj=pd.read_csv("injury_status_panel.csv")
inj["gd"]=pd.to_datetime(inj.game_date,errors="coerce")
inj["ts"]=pd.to_datetime(inj.report_ts,errors="coerce")
inj=inj.dropna(subset=["gd","ts","player","team_raw","status"])
# strip GLUED suffixes on the surname: "WilliamsIII,Robert" / "DukeJr.,David"
_last=inj.player.str.extract(r"^([^,]+),")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
_first=inj.player.str.extract(r",\s*(.+)$")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
inj["key"]=canon(_first.fillna("")+" "+_last.fillna(""))
first_ts=inj.groupby(["gd","team_raw"]).ts.transform("min")
E=inj[inj.ts==first_ts].copy()             # EARLIEST report for that team-game
L=inj[inj.ts==inj.groupby(["gd","team_raw"]).ts.transform("max")].copy()  # LATEST
print(f"injury rows {len(inj):,}  -> earliest-report rows {len(E):,}, latest {len(L):,}")
# 4. NAME MATCH DIAGNOSTIC — the JT Orr lesson
keys=set(nm.key)
mr=E.key.isin(keys)
print(f"\nNAME MATCH: {100*mr.mean():.2f}% of earliest-report rows match a pid")
un=E[~mr].player.value_counts().head(8)
print("  top UNMATCHED:",{k:int(v) for k,v in un.items()})
E=E.merge(nm[["pid","key"]],on="key",how="left")
L=L.merge(nm[["pid","key"]],on="key",how="left")
def feat(D,tag):
    D=D.dropna(subset=["pid"]).copy(); D["yr"]=np.where(D.gd.dt.month>=8,D.gd.dt.year,D.gd.dt.year-1)
    D["rate"]=[rate.get((p,y+1),np.nan) for p,y in zip(D.pid,D.yr)]
    D["rate"]=D["rate"].fillna(lg*0.35)
    w={"Out":1.0,"Doubtful":0.75,"Questionable":0.35,"Probable":0.10,"Available":0.0}
    D["wt"]=D.status.map(w).fillna(0.0)
    g=D.groupby(["gd","team_raw"]).apply(lambda x: pd.Series({
        f"{tag}_n_out":(x.status=="Out").sum(),
        f"{tag}_n_q":(x.status.isin(["Questionable","Doubtful"])).sum(),
        f"{tag}_pts_out":(x.rate*x.wt).sum()}),include_groups=False).reset_index()
    return g
FE=feat(E,"e"); FL=feat(L,"l")
F=FE.merge(FL,on=["gd","team_raw"],how="outer").sort_values(["team_raw","gd"])
# CHANGE features: a season-long absentee is already inside the latent rating.
# Only the NEWS is informative, so difference against the team's PREVIOUS game.
g=F.groupby("team_raw")
for c in ["e_n_out","e_n_q","e_pts_out","l_pts_out"]:
    F["d_"+c]=F[c]-g[c].shift(1)
F["d_days"]=(F.gd-g.gd.shift(1)).dt.days
# late-vs-early within the same game = information arriving AFTER the first report
F["late_news"]=F.l_pts_out-F.e_pts_out
print(f"\nteam-game injury features: {len(F):,}")
print(f"  mean players Out {F.e_n_out.mean():.2f}   mean expected points removed {F.e_pts_out.mean():.2f}")
print(f"  p90 points removed {F.e_pts_out.quantile(.9):.2f}   max {F.e_pts_out.max():.1f}")
print(f"  CHANGE vs previous game: sd(d_pts_out) {F.d_e_pts_out.std():.2f}"
      f"   p10/p90 {F.d_e_pts_out.quantile(.1):.1f}/{F.d_e_pts_out.quantile(.9):.1f}")
print(f"  LATE news (last report - first report): sd {F.late_news.std():.2f},"
      f" nonzero on {100*(F.late_news.abs()>0.5).mean():.1f}% of team-games")
F.to_csv(SP+"injury_features.csv",index=False)
print("saved")
