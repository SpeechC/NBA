import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
R=pd.read_parquet(SP+"player_states.parquet")          # date, team, pid, proj_min, proj_pts, ppm
def canon(s):
    return (pd.Series(s,dtype="object").astype(str).str.replace(r"[.\-'`]","",regex=True)
            .str.replace(r"\s+"," ",regex=True).str.strip().str.lower())
pb=pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet",columns=["PLAYER1_ID","PLAYER1_NAME"]).dropna()
nm=pb.groupby("PLAYER1_ID").PLAYER1_NAME.agg(lambda s:s.mode().iloc[0]).reset_index()
nm.columns=["pid","name"]; nm["key"]=canon(nm.name); k2p=dict(zip(nm.key,nm.pid))
inj=pd.read_csv("injury_status_panel.csv")
inj["gd"]=pd.to_datetime(inj.game_date,errors="coerce"); inj["ts"]=pd.to_datetime(inj.report_ts,errors="coerce")
inj=inj.dropna(subset=["gd","ts","player","team_raw","status"])
last=inj.player.str.extract(r"^([^,]+),")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
first=inj.player.str.extract(r",\s*(.+)$")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
inj["key"]=canon(first.fillna("")+" "+last.fillna("")); inj["pid"]=inj.key.map(k2p)
inj=inj[inj.ts==inj.groupby(["gd","team_raw"]).ts.transform("min")]      # EARLIEST report
tm=pd.read_csv("team_mapping.csv")
cn=lambda s: pd.Series(s,dtype="object").astype(str).str.replace(r"[^A-Za-z]","",regex=True).str.lower()
inj["tk"]=cn(inj.team_raw); mp={}
for _,r in tm.iterrows():
    pref=cn([r.bigdataball_name]).iloc[0]
    for h in inj.tk[inj.tk.str.startswith(pref)].unique(): mp[h]=r.bigdataball_name
inj["team"]=inj.tk.map(mp)
inj=inj.dropna(subset=["team","pid"]); inj["pid"]=inj.pid.astype("int64")
W={"Out":1.0,"Doubtful":0.75,"Questionable":0.35,"Probable":0.10,"Available":0.0}
inj["wt"]=inj.status.map(W).fillna(0.0)
print(f"injury rows with pid+team: {len(inj):,}")
OUT={}                                    # (team, date) -> {pid: weight}
for (t,dt),g in inj.groupby(["team","gd"]):
    OUT[(t,dt)]=dict(zip(g.pid,g.wt))
rows=[]
for team,G in R.groupby("team"):
    G=G.sort_values("date"); dts=G.date.values
    tgts=sorted(set(d for (tt,d) in OUT if tt==team))
    for d in tgts:
        d64=np.datetime64(d)
        lo=np.searchsorted(dts,d64-np.timedelta64(30,"D")); hi=np.searchsorted(dts,d64)
        if hi-lo<8: continue
        sl=G.iloc[lo:hi].drop_duplicates("pid",keep="last")   # latest prior state per player
        om=OUT[(team,d)]
        sl=sl.assign(w=sl.pid.map(om).fillna(0.0))
        avail=sl[sl.w<0.5].sort_values("proj_min",ascending=False)
        if len(avail)<9: continue
        repl=avail.iloc[8:12].ppm.mean()                       # ranks 9-12 = replacement level
        if not np.isfinite(repl): repl=avail.ppm.min()
        outp=sl[sl.w>0]
        # VORP: (player rate - replacement rate) * projected minutes, weighted by status
        vorp=float(((outp.ppm-repl).clip(lower=0)*outp.proj_min*outp.w).sum())
        raw =float((outp.proj_pts*outp.w).sum())
        rows.append((team,d,vorp,raw,repl,len(outp),float((outp.proj_min*outp.w).sum())))
V=pd.DataFrame(rows,columns=["team","date","vorp","raw_pts","repl_ppm","n_out","min_out"])
V=V.sort_values(["team","date"]); V["d_vorp"]=V.groupby("team").vorp.diff()
print(f"\nteam-game VORP features: {len(V):,}   {V.date.min().date()}..{V.date.max().date()}")
print(f"  VORP (net pts lost)  mean {V.vorp.mean():.2f}  sd {V.vorp.std():.2f}  p90 {V.vorp.quantile(.9):.2f}  max {V.vorp.max():.1f}")
print(f"  RAW  (gross pts out) mean {V.raw_pts.mean():.2f}  sd {V.raw_pts.std():.2f}")
print(f"  replacement ppm      mean {V.repl_ppm.mean():.4f}   minutes out mean {V.min_out.mean():.1f}")
print(f"  corr(VORP, RAW) = {V.vorp.corr(V.raw_pts):.4f}   <- if ~1, replacement adds nothing")
V.to_csv(SP+"vorp_features.csv",index=False)
