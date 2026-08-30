import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"eff_panel.csv"); G["date"]=pd.to_datetime(G.date).dt.strftime("%Y-%m-%d")
L=pd.read_csv(SP+"ladder_sigma.csv"); L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(G[["date","TEAM_H","TEAM_R","t3r","pace","close"]],left_on=["date","home_n"],
          right_on=["date","TEAM_H"],how="inner").dropna(subset=["t3r"])
y=M.sig.values
print(f"n={len(M):,}   implied sigma: mean {y.mean():.3f}  sd {y.std():.3f}\n")

def fit(cols,lbl,X_=None):
    X_=M if X_ is None else X_
    X=np.column_stack([np.ones(len(X_))]+[np.asarray(c[1]) for c in cols])
    b,*_=np.linalg.lstsq(X,X_.sig.values,rcond=None); r=X_.sig.values-X@b
    R2=1-r.var()/X_.sig.values.var()
    print(f"  {lbl:<40} R2 {R2:6.4f}   residual sd {r.std():.4f}")
    return b,r,R2
print("HOW MUCH OF THE LADDER'S SIGMA DO WE ACTUALLY EXPLAIN?")
fit([("mu",M.mu)],"sigma ~ mu")
fit([("pace",M.pace)],"sigma ~ pace")
fit([("mu",M.mu),("pace",M.pace)],"sigma ~ mu + pace")
b3,r3,R23=fit([("mu",M.mu),("pace",M.pace),("3PA",M.t3r)],"sigma ~ mu + pace + 3PArate  <- OUR MODEL")
print(f"\n  => our 3-variable model leaves {100*(1-R23):.1f}% of the ladder's sigma UNEXPLAINED")

print("\nIS THE UNEXPLAINED PART NOISE, OR THEIR MODEL DOING MORE?")
print(f"  probit-fit quality: median max|residual| {M.maxres.median():.4f} on the ladder mids")
appx=(M.maxres/2).median()*M.sig.mean()/0.4
print(f"  crude estimate of sigma ESTIMATION error from the rung fit: ~{appx:.3f} pts")
print(f"  observed residual sd {r3.std():.3f}")
print(f"  -> {'much of the residual could be fit noise' if appx>0.5*r3.std() else 'residual EXCEEDS plausible fit noise: their model does more than ours'}")

print("\nFUNCTIONAL FORM — is it the POISSON shape or just linear?")
for lbl,v in [("sigma ~ sqrt(2*pace) [pure Poisson]",np.sqrt(2*M.pace)),
              ("sigma ~ sqrt(mu)     [pure Poisson in total]",np.sqrt(M.mu)),
              ("sigma ~ pace         [linear]",M.pace),
              ("sigma ~ mu           [linear]",M.mu)]:
    fit([("x",v)],lbl)
print("  (over these narrow ranges sqrt and linear are near-collinear; this CANNOT separate them)")
lo,hi=np.sqrt(M.mu.min()),np.sqrt(M.mu.max())
print(f"  corr(sqrt(mu), mu) = {np.corrcoef(np.sqrt(M.mu),M.mu)[0,1]:.6f}  <- that is why")

print("\nSTRUCTURE IN THE RESIDUAL — do they adjust per TEAM?")
M["res"]=r3
for c in ["TEAM_H","TEAM_R"]:
    g=M.groupby(c).res.agg(["mean","size"]); g=g[g["size"]>=15]
    F=g["mean"].std()/ (r3.std()/np.sqrt(g["size"].mean()))
    print(f"  {c}: {len(g)} teams, between-team sd of residual {g['mean'].std():.4f}"
          f"  vs noise-only {r3.std()/np.sqrt(g['size'].mean()):.4f}  ratio {F:.2f}")
print("\n  most extreme team residuals (ladder sigma vs our model):")
g=M.groupby("TEAM_H").res.agg(["mean","size"]); g=g[g["size"]>=15].sort_values("mean")
print("   ",{k:round(v,3) for k,v in g["mean"].head(3).items()},"...",
      {k:round(v,3) for k,v in g["mean"].tail(3).items()})
