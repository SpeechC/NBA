import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy(); d["ph"]=n("PTS_H"); d["pr"]=n("PTS_R"); d["close"]=n("CLOSING TOTAL_H")
d["total"]=d.ph+d.pr; d["date"]=pd.to_datetime(d["DATE"],errors="coerce").dt.strftime("%Y-%m-%d")
d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
d=d[d.season.str.contains("Regular Season",na=False)]            # <-- THE FIX
d=d.dropna(subset=["total","close","yr"]); d=d[d.close.between(150,300)]
d=d.reset_index(drop=True); d["gi"]=d.index; d["dev"]=d.total-d.close
print(f"regular-season panel {len(d):,}  (matches matchup_var.py)")

T=pd.concat([d[["gi","yr","TEAM_H","ph"]].rename(columns={"TEAM_H":"t","ph":"p"}),
             d[["gi","yr","TEAM_R","pr"]].rename(columns={"TEAM_R":"t","pr":"p"})])
ag=T.groupby(["t","yr"]).p.agg(N="count",S="sum",Q=lambda s:(s**2).sum())
T=T.join(ag,on=["t","yr"]); T=T[T.N>=40]
Np,Sp,Qp=T.N-1,T.S-T.p,T.Q-T.p**2
T["loo"]=np.sqrt(((Qp-Sp**2/Np)/(Np-1)).clip(lower=1))
T["z"]=T.groupby("yr").loo.transform(lambda s:(s-s.mean())/s.std())   # per-GAME LOO z
pg=T.groupby("gi").agg(zmin=("z","min"),zmax=("z","max"),
                       lmin=("loo","min"),lmax=("loo","max"),k=("z","size"))
pg=pg[pg.k==2]; G=d.set_index("gi").join(pg,how="inner")
G["comb"]=np.sqrt(G.lmin**2+G.lmax**2)
thi,tlo=T.z.quantile(2/3),T.z.quantile(1/3)
HH=G[G.zmin>=thi]; LL=G[G.zmax<=tlo]
print(f"\nREALITY, regular season only  (HH n={len(HH)}, LL n={len(LL)})")
print(f"  HH sd(dev) {HH.dev.std():.3f}   LL sd(dev) {LL.dev.std():.3f}   ALL {G.dev.std():.3f}")
F=HH.dev.var()/LL.dev.var()
print(f"  HH/LL ratio {np.sqrt(F):.4f}  F p="
      f"{2*min(stats.f.cdf(F,len(HH)-1,len(LL)-1),1-stats.f.cdf(F,len(HH)-1,len(LL)-1)):.4f}"
      "   <-- reconciles with matchup_var.py")

# ---- ladder side, same filter ----
L=pd.read_csv(SP+"ladder_sigma.csv")
L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(G.reset_index()[["date","TEAM_H","TEAM_R","dev","close","comb","zmin","zmax"]],
          left_on=["date","home_n"],right_on=["date","TEAM_H"],how="inner")
print(f"\nladder x matchup, REGULAR SEASON: {len(M):,} games")

def reg(y,cols,X_,lbl):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<42}"+"   ".join(f"{c} {b[i+1]:+8.4f} (t={b[i+1]/se[i+1]:+5.2f})"
                                    for i,c in enumerate(cols)))

print("\nQ1. DOES THE LADDER WIDEN FOR HIGH-VARIANCE MATCHUPS?")
reg(M.sig.values,["comb"],M,"implied_sigma ~ comb")
reg(M.sig.values,["comb","mu"],M,"implied_sigma ~ comb + implied_mu")
print("\nQ2. DOES REALITY?")
reg((G.dev**2).values,["comb","close"],G,f"dev^2 ~ comb + close  [ALL n={len(G)}]")

print("\nQ3. THE DIRECT ANSWER")
mh,ml=M[M.zmin>=thi],M[M.zmax<=tlo]
print(f"  {'bucket':<22}{'n_lad':>7}{'LADDER sigma':>14}{'mean mu':>9}{'|':>4}"
      f"{'n_all':>7}{'REALISED sd(dev)':>18}")
for lab,a,b in [("HH both high-var",mh,HH),("LL both low-var",ml,LL),("ALL games",M,G)]:
    print(f"  {lab:<22}{len(a):>7}{a.sig.mean():>14.3f}{a.mu.mean():>9.1f}{'|':>4}"
          f"{len(b):>7}{b.dev.std():>18.3f}")
t_,p_=stats.ttest_ind(mh.sig,ml.sig,equal_var=False)
print(f"\n  LADDER  HH-LL implied sigma {mh.sig.mean()-ml.sig.mean():+.4f}  (t={t_:+.2f}, p={p_:.4f})")
print(f"  se on that difference {np.sqrt(mh.sig.var()/len(mh)+ml.sig.var()/len(ml)):.4f}"
      f"  -> MDE {1.96*np.sqrt(mh.sig.var()/len(mh)+ml.sig.var()/len(ml)):.4f} pts")
