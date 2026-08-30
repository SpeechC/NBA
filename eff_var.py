import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy()
need=["PTS_H","PTS_R","CLOSING TOTAL_H","PACE_H","PACE_R","OEFF_H","OEFF_R",
      "3PA_H","3PA_R","FGA_H","FGA_R","MIN_H"]
for c in need:
    d[c]=n(c) if c in raw.columns else np.nan
print("missing:",[c for c in need if c not in raw.columns])
d["total"]=d["PTS_H"]+d["PTS_R"]; d["close"]=d["CLOSING TOTAL_H"]
d["date"]=pd.to_datetime(d["DATE"],errors="coerce"); d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
d["is_ot"]=(d["MIN_H"]>250).astype(int)
d=d[d.season.str.contains("Regular Season",na=False)]
d=d.dropna(subset=["total","close","PACE_H","PACE_R","OEFF_H","OEFF_R","3PA_H","3PA_R","FGA_H","FGA_R","yr"])
d=d.sort_values("date").reset_index(drop=True); d["gi"]=d.index; d["dev"]=d.total-d.close
print(f"base panel {len(d):,}")

T=pd.concat([d[["gi","yr","date","TEAM_H","PACE_H","OEFF_H","3PA_H","FGA_H"]]
             .rename(columns={"TEAM_H":"t","PACE_H":"pace","OEFF_H":"oeff","3PA_H":"tpa","FGA_H":"fga"}),
             d[["gi","yr","date","TEAM_R","PACE_R","OEFF_R","3PA_R","FGA_R"]]
             .rename(columns={"TEAM_R":"t","PACE_R":"pace","OEFF_R":"oeff","3PA_R":"tpa","FGA_R":"fga"})])
T["t3r"]=T.tpa/T.fga
T=T.sort_values(["t","yr","date"]); g=T.groupby(["t","yr"])
T["p_pace"]=g.pace.transform(lambda s:s.shift(1).rolling(20,min_periods=10).mean())
T["p_3r"]  =g.t3r .transform(lambda s:s.shift(1).rolling(20,min_periods=10).mean())
T["p_esd"] =g.oeff.transform(lambda s:s.shift(1).rolling(20,min_periods=10).std())
T["p_eff"] =g.oeff.transform(lambda s:s.shift(1).rolling(20,min_periods=10).mean())
w=T.groupby("gi").agg(pace=("p_pace","mean"),t3r=("p_3r","mean"),esd=("p_esd","mean"),
                      eff=("p_eff","mean"),k=("p_pace","size"),ok=("p_esd","count"))
G=d.set_index("gi").join(w[(w.k==2)&(w.ok==2)],how="inner").dropna(subset=["pace","t3r","esd"])
print(f"PANEL {len(G):,} games with prior-only pace + 3PA rate + efficiency sd\n")

print("STAGE 0 — WHICH CONDITIONER IS ACTUALLY MEASURABLE?")
ts=T.groupby(["t","yr"]).agg(esd=("oeff","std"),t3r=("t3r","mean"),N=("oeff","size"))
ts=ts[ts.N>=40]
for nm,col in [("efficiency sd (a VARIANCE)","esd"),("3PA rate (a MEAN)","t3r")]:
    z=ts[col].groupby(level=1).transform(lambda s:(s-s.mean())/s.std())
    pv=z.unstack(); ys=sorted(pv.columns)
    rs=[pv[[a,b]].dropna().corr().iloc[0,1] for a,b in zip(ys,ys[1:]) if len(pv[[a,b]].dropna())>20]
    med=ts.groupby(level=1)[col].median().median()
    nf=(ts[col].median()/np.sqrt(2*ts.N.median())) if col=="esd" else np.nan
    print(f"  {nm:<28} adjacent-season r = {np.mean(rs):+.4f}   cross-team sd {ts[col].std():.4f}"
          + (f"   noise floor {nf:.4f}" if col=="esd" else "   (means are measured precisely)"))
print(f"  3PA rate range across team-seasons: {ts.t3r.min():.3f} .. {ts.t3r.max():.3f}")

print("\nPOWER, PRICED FIRST — the 3PA mechanism has a computable prediction")
p3,p2=0.36,0.53
v3,v2=9*p3*(1-p3),4*p2*(1-p2)
print(f"  var per 3PA {v3:.3f} vs per 2PA {v2:.3f}  -> excess {v3-v2:.3f} per shot converted")
fga=(d.FGA_H+d.FGA_R).mean(); rng=G.t3r.max()-G.t3r.min()
dvar=fga*rng*(v3-v2); sg=G.dev.std()
print(f"  combined FGA {fga:.1f}, matchup 3PA-rate range {rng:.3f}"
      f"  -> d(var) {dvar:.1f} over the range")
print(f"  = {np.sqrt(sg**2+dvar/2)-np.sqrt(sg**2-dvar/2):.3f} pts of SIGMA across the observed range")
print(f"  PREDICTED coefficient d(dev^2)/d(3PArate) = {fga*(v3-v2):.1f}")
X=np.column_stack([np.ones(len(G)),G.t3r,G.pace,G.close]); y=(G.dev**2).values
b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
se=np.sqrt(np.diag((r@r/(len(y)-4))*np.linalg.pinv(X.T@X)))
print(f"  se at n={len(G):,} is {se[1]:.1f} -> MDE {1.96*se[1]:.1f}"
      f"   {'POWERED' if 1.96*se[1]<fga*(v3-v2) else 'UNDERPOWERED'}")

def reg(y,cols,X_,lbl):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<42}"+"  ".join(f"{c} {b[i+1]:+8.3f}(t={b[i+1]/se[i+1]:+5.2f})"
                                   for i,c in enumerate(cols)))
    return b,se
print("\nQ1. REALITY — does efficiency variance widen the distribution?")
reg((G.dev**2).values,["t3r"],G,"dev^2 ~ 3PArate")
reg((G.dev**2).values,["t3r","pace","close"],G,"dev^2 ~ 3PArate + pace + close")
reg((G.dev**2).values,["esd","pace","close"],G,"dev^2 ~ prior_eff_SD + pace + close")
G.reset_index().to_csv(SP+"eff_panel.csv",index=False)
