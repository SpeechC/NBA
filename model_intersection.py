import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"v5_panel.csv"); S["date"]=pd.to_datetime(S.date); S=S.sort_values("date").reset_index(drop=True)
teams=sorted(set(S.TEAM_H)|set(S.TEAM_R)); ti={t:i for i,t in enumerate(teams)}; NT=len(teams)
H=S.TEAM_H.map(ti).values; A=S.TEAM_R.map(ti).values; dates=S.date.values; yr=S.yr.values; N=len(S)
# ---- MODEL B = their Layer 2: structural + per-team EWMA of the structural residual ----
st=S.struct5.values; op=S.open.values
def modelB(alpha,lam):
    M=np.zeros(NT); pr=np.empty(N); mh=np.empty(N); mr=np.empty(N); yp=None; i=0
    while i<N:
        j=i
        while j<N and dates[j]==dates[i]: j+=1
        if yp is not None and yr[i]!=yp: M*=lam
        yp=yr[i]
        for q in range(i,j): mh[q]=M[H[q]]; mr[q]=M[A[q]]
        for q in range(i,j):
            r=op[q]-st[q]
            M[H[q]]+=alpha*(r/2-M[H[q]]); M[A[q]]+=alpha*(r/2-M[A[q]])
        i=j
    return mh,mr
best=None
for al in [0.05,0.10,0.15,0.20,0.30]:
    for lm in [0.4,0.6,0.8]:
        mh,mr=modelB(al,lm)
        d=pd.DataFrame({"yr":yr,"st":st,"mh":mh,"mr":mr,"open":op})
        dev=d[d.yr<=2021]
        X=np.column_stack([np.ones(len(dev)),dev.st,dev.mh,dev.mr])
        b,*_=np.linalg.lstsq(X,dev.open.values,rcond=None); r=dev.open.values-X@b
        v=1-r.var()/dev.open.var()
        if best is None or v>best[0]: best=(v,al,lm)
_,AL,LM=best; mh,mr=modelB(AL,LM)
S["mh"]=mh; S["mr"]=mr
def xfit(cols):
    pr=np.full(len(S),np.nan)
    for y in sorted(S.yr.unique())[1:]:
        tr=S[S.yr<y]; te=S[S.yr==y]
        if len(tr)<300 or not len(te): continue
        X=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        B=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(X).all(1)
        b,*_=np.linalg.lstsq(X[ok],tr.open.values[ok],rcond=None); pr[te.index]=B@b
    return pr
S["predA"]=xfit(["lineD2","lineD4"])                 # MY architecture
S["predB"]=xfit(["struct5","mh","mr"])               # THEIR architecture (Layer1 + Layer2)
T=S[(S.yr>=2022)&S.predA.notna()&S.predB.notna()].copy()
for m in "AB":
    T["e"+m]=T.open-T["pred"+m]; T["a"+m]=T["e"+m].abs()
print(f"TWO INDEPENDENT ARCHITECTURES   n={len(T):,}   (alpha={AL}, lambda={LM})")
for m,lbl in [("A","MINE: two-way line state"),("B","THEIRS: structural + market-residual EWMA")]:
    e=T["e"+m]; print(f"  {lbl:<44}RMSE {np.sqrt((e**2).mean()):.3f}  R2 {1-e.var()/T.open.var():.4f}")
print(f"  corr(errA, errB) = {T.eA.corr(T.eB):+.4f}   corr(|errA|,|errB|) = {T.aA.corr(T.aB):+.4f}")
V=pd.read_csv(SP+"inj_disagg.csv"); V["date"]=pd.to_datetime(V.date)
FE=["v_sum","v_max","v_top2","v_hhi","v_conc","n_out","min_out","starters_out"]
T=T.merge(V[["date","team"]+FE].rename(columns={"team":"TEAM_H"}),on=["date","TEAM_H"],how="left")
T=T.merge(V[["date","team"]+FE].rename(columns={"team":"TEAM_R",**{c:c+"_R" for c in FE}}),
          on=["date","TEAM_R"],how="left")
T=T.dropna(subset=["v_sum","v_sum_R"])
T=T.reset_index(drop=True)
tA,tB=T.aA.quantile(0.9),T.aB.quantile(0.9)
T["bA"]=T.aA>=tA; T["bB"]=T.aB>=tB
G={"A both bad":T.bA&T.bB,"B mine bad only":T.bA&~T.bB,
   "C theirs bad only":~T.bA&T.bB,"D both good":~T.bA&~T.bB}
for c in FE: T[c+"_g"]=T[c]+T[c+"_R"]
T["v_max_g"]=T[["v_max","v_max_R"]].max(axis=1); T["hhi_g"]=T[["v_hhi","v_hhi_R"]].max(axis=1)
T["asym"]=(T.v_sum-T.v_sum_R).abs()
print(f"\nFOUR-GROUP INTERSECTION  (n={len(T):,} with injury data)")
print(f"  {'group':<20}{'n':>6}{'share':>8}{'chance':>8}{'mean eA':>9}{'mean eB':>9}{'corr(eA,eB)':>13}")
for k,m in G.items():
    s=T[m]
    ch={"A both bad":1.0,"B mine bad only":9.0,"C theirs bad only":9.0,"D both good":81.0}[k]
    print(f"  {k:<20}{len(s):>6}{100*len(s)/len(T):>7.1f}%{ch:>7.1f}%{s.eA.mean():>+9.3f}{s.eB.mean():>+9.3f}"
          f"{s.eA.corr(s.eB):>13.4f}")
print(f"\nINJURY PROFILE BY GROUP  (mean)")
print(f"  {'feature':<18}"+"".join(f"{k.split()[0]:>10}" for k in G))
for nm,c in [("total VORP","v_sum_g"),("max single","v_max_g"),("top-2","v_top2_g"),
             ("HHI (max side)","hhi_g"),("n players out","n_out_g"),("starters out","starters_out_g"),
             ("minutes out","min_out_g"),("H-R asymmetry","asym")]:
    print(f"  {nm:<18}"+"".join(f"{T[G[k]][c].mean():>10.2f}" for k in G))
a=T[G["A both bad"]]; d=T[G["D both good"]]
print(f"\n  A vs D t-stats:")
for nm,c in [("total VORP","v_sum_g"),("max single","v_max_g"),("HHI","hhi_g"),
             ("n out","n_out_g"),("starters out","starters_out_g"),("asymmetry","asym")]:
    t,p=stats.ttest_ind(a[c].dropna(),d[c].dropna(),equal_var=False)
    print(f"    {nm:<14}{a[c].mean():>8.2f} vs {d[c].mean():>7.2f}   t={t:>+6.2f}")
T.to_csv(SP+"intersect_panel.csv",index=False)
