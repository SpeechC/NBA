import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
R=pd.read_parquet(SP+"player_states.parquet")     # date, team, pid, proj_min, proj_pts, ppm
def canon(s):
    return (pd.Series(s,dtype="object").astype(str).str.replace(r"[.\-'`]","",regex=True)
            .str.replace(r"\s+"," ",regex=True).str.strip().str.lower())
pb=pd.read_parquet("/mnt/c/NBA2/out/pbp_lineups_all.parquet",columns=["PLAYER1_ID","PLAYER1_NAME"]).dropna()
nm=pb.groupby("PLAYER1_ID").PLAYER1_NAME.agg(lambda s:s.mode().iloc[0]).reset_index()
nm.columns=["pid","name"]; k2p=dict(zip(canon(nm.name),nm.pid))
inj=pd.read_csv("injury_status_panel.csv")
inj["gd"]=pd.to_datetime(inj.game_date,errors="coerce"); inj["ts"]=pd.to_datetime(inj.report_ts,errors="coerce")
inj=inj.dropna(subset=["gd","ts","player","team_raw","status"])
lst=inj.player.str.extract(r"^([^,]+),")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
fst=inj.player.str.extract(r",\s*(.+)$")[0].str.replace(r"(Jr|Sr|III|II|IV)\.?$","",regex=True)
inj["pid"]=canon(fst.fillna("")+" "+lst.fillna("")).map(k2p)
tm=pd.read_csv("team_mapping.csv")
cn=lambda s: pd.Series(s,dtype="object").astype(str).str.replace(r"[^A-Za-z]","",regex=True).str.lower()
inj["tk"]=cn(inj.team_raw); mp={}
for _,r in tm.iterrows():
    pref=cn([r.bigdataball_name]).iloc[0]
    for h in inj.tk[inj.tk.str.startswith(pref)].unique(): mp[h]=r.bigdataball_name
inj["team"]=inj.tk.map(mp); inj=inj.dropna(subset=["team","pid"]); inj["pid"]=inj.pid.astype("int64")
LAST=inj[inj.ts==inj.groupby(["gd","team"]).ts.transform("max")]
outL=LAST[LAST.status=="Out"].groupby(["team","gd"]).pid.apply(set)
# STRICTLY KNOWABLE: the team's PREVIOUS game's final report
prior={}
for team,g in outL.reset_index().groupby("team"):
    g=g.sort_values("gd"); ds=list(g.gd); ps=list(g.pid)
    for i in range(1,len(ds)): prior[(team,ds[i])]=ps[i-1]
print(f"strictly-knowable OUT sets: {len(prior):,}")
MIN_TOT=240.0; CAP=38.0
rows=[]
byteam={}
for (t,d),s in prior.items(): byteam.setdefault(t,[]).append((d,s))
for team,G in R.groupby("team"):
    if team not in byteam: continue
    G=G.sort_values("date"); dts=G.date.values
    pid=G.pid.values; pmin=G.proj_min.values; ppm=G.ppm.values
    for d,outset in sorted(byteam[team]):
        d64=np.datetime64(d)
        lo=np.searchsorted(dts,d64-np.timedelta64(30,"D")); hi=np.searchsorted(dts,d64)
        if hi-lo<8: continue
        P=pid[lo:hi]; M=pmin[lo:hi]; Q=ppm[lo:hi]
        _,ix=np.unique(P[::-1],return_index=True); ix=len(P)-1-ix
        P,M,Q=P[ix],M[ix],Q[ix]
        if len(P)<9: continue
        # HEALTHY baseline: reallocate 240 min over the whole roster by prior minutes
        def realloc(mask):
            m=M[mask].copy()
            if m.sum()<=0 or mask.sum()<5: return None,None
            for _ in range(6):
                sc=MIN_TOT/m.sum(); m=np.minimum(m*sc,CAP)
                if abs(m.sum()-MIN_TOT)<0.5: break
            return m,Q[mask]
        allm=np.ones(len(P),bool)
        mh,qh=realloc(allm)
        av=~np.isin(P,list(outset))
        ma,qa=realloc(av)
        if mh is None or ma is None: continue
        off_h=float(mh@qh); off_a=float(ma@qa)
        # rotation continuity: normal top-8 by prior minutes vs available top-8
        top8=set(P[np.argsort(-M)[:8]]); avail_top8=set(P[av][np.argsort(-M[av])[:8]])
        rot_min=M[np.argsort(-M)[:8]].sum()
        out_top8=len(top8-set(P[av]))
        rows.append(dict(team=team,date=d,
            roster_off=off_a-off_h,                       # net available-roster offence delta
            off_healthy=off_h, off_avail=off_a,
            top8_out=out_top8,
            top8_out_share=out_top8/8.0,
            rot_min_out_share=float(M[np.isin(P,list(outset))].sum()/max(rot_min,1)),
            continuity=len(top8&avail_top8)/8.0,
            n_subs=len(avail_top8-top8),
            n_avail=int(av.sum())))
V=pd.DataFrame(rows)
print(f"roster-state features: {len(V):,} team-games")
print(f"  roster_off (net offence delta)  mean {V.roster_off.mean():+.3f}  sd {V.roster_off.std():.3f}"
      f"  p10 {V.roster_off.quantile(.1):+.2f}")
print(f"  top-8 players out  mean {V.top8_out.mean():.2f}   continuity mean {V.continuity.mean():.3f}")
print(f"  rotation-minutes-out share mean {V.rot_min_out_share.mean():.3f}   subs required mean {V.n_subs.mean():.2f}")
V.to_csv(SP+"roster_state.csv",index=False)
