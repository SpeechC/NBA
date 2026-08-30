import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy()
for c in ["PTS_H","PTS_R","CLOSING TOTAL_H","PACE_H","PACE_R","POSS_H","POSS_R","MIN_H"]:
    d[c]=n(c)
d["total"]=d["PTS_H"]+d["PTS_R"]; d["close"]=d["CLOSING TOTAL_H"]
d["date"]=pd.to_datetime(d["DATE"],errors="coerce")
d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
d["is_ot"]=(d["MIN_H"]>250).astype(int)
d=d[d.season.str.contains("Regular Season",na=False)]
d=d.dropna(subset=["total","close","PACE_H","PACE_R","yr"]).sort_values("date")
d=d.reset_index(drop=True); d["gi"]=d.index; d["dev"]=d.total-d.close

# ---- PRIOR-ONLY team pace: shift(1).rolling(20,min_periods=10) within season ----
T=pd.concat([d[["gi","yr","date","TEAM_H","PACE_H"]].rename(columns={"TEAM_H":"t","PACE_H":"pace"}),
             d[["gi","yr","date","TEAM_R","PACE_R"]].rename(columns={"TEAM_R":"t","PACE_R":"pace"})])
T=T.sort_values(["t","yr","date"])
gb=T.groupby(["t","yr"]).pace
T["ppace"]=gb.transform(lambda s: s.shift(1).rolling(20,min_periods=10).mean())
T["ppsd"] =gb.transform(lambda s: s.shift(1).rolling(20,min_periods=10).std())
w=T.groupby("gi").agg(pp=("ppace","mean"),ppn=("ppace","size"),
                      ppsd=("ppsd","mean"),ppok=("ppace","count"))
w=w[(w.ppn==2)&(w.ppok==2)]
G=d.set_index("gi").join(w,how="inner")
print(f"PANEL {len(G):,} games with prior-only pace on BOTH teams  ({100*len(G)/len(d):.0f}% of {len(d):,})")

print("\nSTAGE 0 — is there pace variation ORTHOGONAL to the line?")
print(f"  exp_pace mean {G.pp.mean():.2f}  sd {G.pp.std():.3f}  range {G.pp.min():.1f}..{G.pp.max():.1f}")
print(f"  corr(exp_pace, closing line) = {G.pp.corr(G.close):+.4f}"
      f"   -> R2 {G.pp.corr(G.close)**2:.3f}, so {100*(1-G.pp.corr(G.close)**2):.0f}% of pace is orthogonal")
res=G.pp-np.polyval(np.polyfit(G.close,G.pp,1),G.close)
print(f"  residual pace sd given the line = {res.std():.3f} possessions")

print("\nPOWER, PRICED FIRST")
sg=G.dev.std(); pv=sg**2/(2*G.pp.mean())
print(f"  Poisson: sigma^2 = P*v with P=2*pace.  sigma {sg:.2f} -> v {pv:.4f}")
print(f"  d(sigma^2)/d(exp_pace) = 2*v = {2*pv:.3f}   <- the PREDICTED coefficient")
X=np.column_stack([np.ones(len(G)),G.pp.values,G.close.values]); y=(G.dev**2).values
b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
se=np.sqrt(np.diag((r@r/(len(y)-3))*np.linalg.pinv(X.T@X)))
print(f"  se on that coefficient at n={len(G):,} is {se[1]:.3f} -> MDE {1.96*se[1]:.3f}")
print(f"  {'POWERED' if 1.96*se[1]<2*pv else 'UNDERPOWERED'} for the Poisson prediction")

print("\nQ1. REALITY — does dev^2 load on expected pace, net of the line?")
def reg(y,cols,X_,lbl,ddof=None):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    bb,*_=np.linalg.lstsq(X,y,rcond=None); rr=y-X@bb
    ss=np.sqrt(np.diag((rr@rr/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<46}"+"   ".join(f"{c} {bb[i+1]:+8.3f} (t={bb[i+1]/ss[i+1]:+5.2f})"
                                    for i,c in enumerate(cols)))
    return bb,ss
reg((G.dev**2).values,["pp"],G,"dev^2 ~ exp_pace")
reg((G.dev**2).values,["pp","close"],G,"dev^2 ~ exp_pace + close")
NO=G[G.is_ot==0]
reg((NO.dev**2).values,["pp","close"],NO,f"dev^2 ~ exp_pace + close  [no OT, n={len(NO):,}]")

print("\nQ2. THE 'SAME TOTAL, DIFFERENT PACE' CUT — within line terciles")
G["lq"]=pd.qcut(G.close,3,labels=False)
print(f"  {'line tercile':<14}{'pace half':<11}{'n':>6}{'mean line':>10}{'mean pace':>10}{'sd(dev)':>10}{'+-':>7}")
for i in range(3):
    s=G[G.lq==i]; med=s.pp.median()
    for lab,ss in [("LOW pace",s[s.pp<=med]),("HIGH pace",s[s.pp>med])]:
        print(f"  {i+1:<14}{lab:<11}{len(ss):>6}{ss.close.mean():>10.1f}{ss.pp.mean():>10.2f}"
              f"{ss.dev.std():>10.3f}{ss.dev.std()/np.sqrt(2*len(ss)):>7.3f}")
G.reset_index().to_csv(SP+"pace_panel.csv",index=False)
