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
tm=pd.read_csv("team_mapping.csv")
cn=lambda s: pd.Series(s,dtype="object").astype(str).str.replace(r"[^A-Za-z]","",regex=True).str.lower()
inj["tk"]=cn(inj.team_raw); mp={}
for _,r in tm.iterrows():
    pref=cn([r.bigdataball_name]).iloc[0]
    for h in inj.tk[inj.tk.str.startswith(pref)].unique(): mp[h]=r.bigdataball_name
inj["team"]=inj.tk.map(mp); inj=inj.dropna(subset=["team","pid"]); inj["pid"]=inj.pid.astype("int64")
FIRST=inj[inj.ts==inj.groupby(["gd","team"]).ts.transform("min")]
LAST =inj[inj.ts==inj.groupby(["gd","team"]).ts.transform("max")]
outF=FIRST[FIRST.status=="Out"].groupby(["team","gd"]).pid.apply(set)
outL=LAST [LAST.status=="Out" ].groupby(["team","gd"]).pid.apply(set)
qF  =FIRST[FIRST.status.isin(["Questionable","Doubtful"])].groupby(["team","gd"]).pid.apply(set)
# ---- STRICTLY-KNOWABLE state: the team's PREVIOUS game's FINAL report ----
prev_out={}
for team,g in outL.reset_index().groupby("team"):
    g=g.sort_values("gd"); ds=list(g.gd); ps=list(g.pid)
    for i in range(1,len(ds)): prev_out[(team,ds[i])]=ps[i-1]
print(f"built: first-report OUT sets {len(outF):,}, last-report {len(outL):,}, prior-game {len(prev_out):,}")
def vorp_from(getset,tag):
    if not isinstance(getset,dict): getset={k:v for k,v in getset.items()}
    byteam={}
    for (t,d),v in getset.items(): byteam.setdefault(t,[]).append((d,v))
    rows=[]
    for team,G in R.groupby("team"):
        if team not in byteam: continue
        G=G.sort_values("date"); dts=G.date.values
        pid=G.pid.values; pmin=G.proj_min.values; ppm=G.ppm.values
        for d,s_ in sorted(byteam[team]):
            d64=np.datetime64(d)
            lo=np.searchsorted(dts,d64-np.timedelta64(30,"D")); hi=np.searchsorted(dts,d64)
            if hi-lo<8: continue
            P=pid[lo:hi]; M=pmin[lo:hi]; Q=ppm[lo:hi]
            _,ix=np.unique(P[::-1],return_index=True); ix=len(P)-1-ix
            P,M,Q=P[ix],M[ix],Q[ix]
            w=np.isin(P,list(s_))
            av=np.argsort(-M[~w])
            if av.size<9: continue
            rp=Q[~w][av[8:12]].mean()
            if not np.isfinite(rp): rp=Q[~w].min()
            rows.append((team,d,float(np.clip(Q[w]-rp,0,None).dot(M[w]))))
    return pd.DataFrame(rows,columns=["team","date",tag])
VP=vorp_from(prev_out,"v_prior")          # STRICTLY knowable
VF=vorp_from(outF,"v_first")              # first report (my original, timing uncertain)
VL=vorp_from(outL,"v_last")               # final report (definitely post-open)
V=VP.merge(VF,on=["team","date"],how="outer").merge(VL,on=["team","date"],how="outer")
print(f"\nVORP under three information sets  n={len(V):,}")
for c in ["v_prior","v_first","v_last"]:
    print(f"  {c:<10} mean {V[c].mean():6.2f}  sd {V[c].std():6.2f}  nonnull {V[c].notna().sum():,}")
print(f"  corr(prior, first) {V.v_prior.corr(V.v_first):.4f}   corr(first, last) {V.v_first.corr(V.v_last):.4f}")
V.to_csv(SP+"vorp_timing.csv",index=False)
