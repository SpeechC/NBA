import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
R=pd.read_parquet(SP+"player_states.parquet")
def canon(s):
    return (pd.Series(s,dtype="object").astype(str).str.replace(r"[.\-'`]","",regex=True)
            .str.replace(r"\s+"," ",regex=True).str.strip().str.lower())
pb=pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet",columns=["PLAYER1_ID","PLAYER1_NAME"]).dropna()
nm=pb.groupby("PLAYER1_ID").PLAYER1_NAME.agg(lambda s:s.mode().iloc[0]).reset_index()
nm.columns=["pid","name"]; k2p=dict(zip(canon(nm.name),nm.pid))
inj=pd.read_csv("injury_status_panel.csv")
inj["gd"]=pd.to_datetime(inj.game_date,errors="coerce"); inj["ts"]=pd.to_datetime(inj.report_ts,errors="coerce")
inj=inj.dropna(subset=["gd","ts","player","team_raw","status"])
last=inj.player.str.extract(r"^([^,]+),")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
first=inj.player.str.extract(r",\s*(.+)$")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
inj["pid"]=canon(first.fillna("")+" "+last.fillna("")).map(k2p)
inj=inj[inj.ts==inj.groupby(["gd","team_raw"]).ts.transform("min")]
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
OUT={}
for (t,dt),g in inj.groupby(["team","gd"]): OUT[(t,dt)]=dict(zip(g.pid,g.wt))
rows=[]
for team,G in R.groupby("team"):
    G=G.sort_values("date"); dts=G.date.values
    for d in sorted(set(dd for (tt,dd) in OUT if tt==team)):
        d64=np.datetime64(d)
        lo=np.searchsorted(dts,d64-np.timedelta64(30,"D")); hi=np.searchsorted(dts,d64)
        if hi-lo<8: continue
        sl=G.iloc[lo:hi].drop_duplicates("pid",keep="last")
        om=OUT[(team,d)]; sl=sl.assign(w=sl.pid.map(om).fillna(0.0))
        avail=sl[sl.w<0.5].sort_values("proj_min",ascending=False)
        if len(avail)<9: continue
        repl=avail.iloc[8:12].ppm.mean()
        if not np.isfinite(repl): repl=avail.ppm.min()
        o=sl[sl.w>0].copy()
        o["v"]=((o.ppm-repl).clip(lower=0)*o.proj_min*o.w)
        v=o.v.values; s=v.sum(); vs=np.sort(v)[::-1]
        rows.append(dict(team=team,date=d,
            v_sum=s,
            v_max=vs[0] if len(vs) else 0.0,
            v_top2=vs[:2].sum() if len(vs) else 0.0,
            v_hhi=float((v/s)**2 @ np.ones(len(v))) if s>0 else 0.0,
            v_conc=(vs[0]/s) if s>0 else 0.0,
            n_out=int((o.w>0.5).sum()),
            min_out=float((o.proj_min*o.w).sum()),
            starters_out=int(((o.proj_min>=24)&(o.w>0.5)).sum()),
            repl_ppm=repl))
V=pd.DataFrame(rows)
print(f"disaggregated injury features: {len(V):,} team-games")
print(f"  v_sum  mean {V.v_sum.mean():6.2f}   v_max mean {V.v_max.mean():6.2f}   v_top2 {V.v_top2.mean():6.2f}")
print(f"  HHI    mean {V.v_hhi.mean():.3f}  (1.0 = one player carries all the loss)")
print(f"  concentration (max/sum) mean {V.v_conc.mean():.3f}   starters out mean {V.starters_out.mean():.2f}")
print("\n  SAME BURDEN, DIFFERENT SHAPE — games with v_sum in [12,20]:")
b=V[(V.v_sum>=12)&(V.v_sum<=20)]
print(f"    n={len(b):,}   HHI p10 {b.v_hhi.quantile(.1):.3f}  p90 {b.v_hhi.quantile(.9):.3f}"
      f"   n_out p10 {b.n_out.quantile(.1):.0f} p90 {b.n_out.quantile(.9):.0f}")
print(f"    -> a 12-20 pt burden ranges from ~1 concentrated absence to broad depth erosion")
V.to_csv(SP+"inj_disagg.csv",index=False)
