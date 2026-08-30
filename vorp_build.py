import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
st=pd.read_csv("/mnt/c/NBA2/advanced_stats/lineup_stints.csv",
   usecols=["GAMEID","TEAM_ABBREVIATION","STINT_SECONDS"]+[f"PLAYER{i}_ID" for i in range(1,6)])
m=st.melt(id_vars=["GAMEID","TEAM_ABBREVIATION","STINT_SECONDS"],
          value_vars=[f"PLAYER{i}_ID" for i in range(1,6)],value_name="pid").dropna(subset=["pid"])
PM=m.groupby(["GAMEID","TEAM_ABBREVIATION","pid"]).STINT_SECONDS.sum().reset_index()
PM["min"]=PM.STINT_SECONDS/60.0; PM["pid"]=PM.pid.astype("int64")
pg=pd.read_parquet("/home/dpope/data/player_game_pts.parquet")
pg["GAMEID"]=pg.gid.astype(str).str.zfill(10); PM["GAMEID"]=PM.GAMEID.astype(str).str.zfill(10)
PM=PM.merge(pg[["GAMEID","pid","pts","season"]],on=["GAMEID","pid"],how="left")
print(f"player-games {len(PM):,}   pts joined {100*PM.pts.notna().mean():.1f}%")
pb=pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet",columns=["GAME_ID","GAMEDATE","SEASON_TYPE"])
pb=pb[pb.SEASON_TYPE.astype(str).str.contains("Regular",na=False)]
gd=pb.groupby("GAME_ID").GAMEDATE.first(); gd.index=gd.index.astype(str).str.zfill(10)
PM["date"]=pd.to_datetime(PM.GAMEID.map(gd),errors="coerce")
PM=PM.dropna(subset=["date","pts"]).sort_values("date")
PM["yr"]=np.where(PM.date.dt.month>=8,PM.date.dt.year,PM.date.dt.year-1)
tm=pd.read_csv("team_mapping.csv"); PM["team"]=PM.TEAM_ABBREVIATION.map(dict(zip(tm.abbr,tm.bigdataball_name)))
PM=PM.dropna(subset=["team"])
print(f"after date/team join: {len(PM):,} player-games, {PM.date.min().date()}..{PM.date.max().date()}")
# ---- PRIOR-ONLY player states: projected minutes and points per minute ----
PM=PM.sort_values(["pid","date"]); g=PM.groupby(["pid","yr"])
PM["p_min"]=g["min"].transform(lambda s:s.shift(1).expanding(min_periods=1).mean())
PM["p_pts"]=g["pts"].transform(lambda s:s.shift(1).expanding(min_periods=1).mean())
PM["p_n"]=g["min"].transform(lambda s:s.shift(1).expanding(min_periods=1).count())
prev=PM.groupby(["pid","yr"]).agg(pv_min=("min","mean"),pv_pts=("pts","mean")).reset_index()
prev["yr"]=prev.yr+1
PM=PM.merge(prev,on=["pid","yr"],how="left")
K=8.0
PM["proj_min"]=((PM.p_n.fillna(0)*PM.p_min.fillna(0)+K*PM.pv_min.fillna(PM["min"].mean()))/(PM.p_n.fillna(0)+K))
PM["proj_pts"]=((PM.p_n.fillna(0)*PM.p_pts.fillna(0)+K*PM.pv_pts.fillna(PM["pts"].mean()))/(PM.p_n.fillna(0)+K))
PM["ppm"]=PM.proj_pts/PM.proj_min.clip(lower=4.0)
print(f"  proj minutes mean {PM.proj_min.mean():.1f}   ppm mean {PM.ppm.mean():.3f}")
# ---- roster snapshot per team-date: who is on the team, with prior states ----
R=PM[["date","team","pid","proj_min","proj_pts","ppm"]].copy()
R.to_parquet(SP+"player_states.parquet")
# ---- REPLACEMENT LEVEL: among AVAILABLE players, ranks 9-12 by projected minutes ----
inj=pd.read_csv(SP+"injury_features_rows.csv") if False else None
print("saved player states")
