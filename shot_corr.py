import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy()
for c in ["FG_H","FGA_H","3P_H","3PA_H","FT_H","FTA_H","PTS_H",
          "FG_R","FGA_R","3P_R","3PA_R","FT_R","FTA_R","PTS_R","CLOSING TOTAL_H","MIN_H"]:
    d[c]=n(c)
d["season"]=raw["season"]; d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
d=d[d.season.str.contains("Regular Season",na=False)].dropna(subset=["FG_H","3PA_H","FTA_H","yr"])
T=pd.concat([
 d[["yr","TEAM_H","FG_H","FGA_H","3P_H","3PA_H","FT_H","FTA_H","PTS_H"]].rename(columns=
   {"TEAM_H":"t","FG_H":"fg","FGA_H":"fga","3P_H":"x3","3PA_H":"n3","FT_H":"xf","FTA_H":"nf","PTS_H":"pts"}),
 d[["yr","TEAM_R","FG_R","FGA_R","3P_R","3PA_R","FT_R","FTA_R","PTS_R"]].rename(columns=
   {"TEAM_R":"t","FG_R":"fg","FGA_R":"fga","3P_R":"x3","3PA_R":"n3","FT_R":"xf","FTA_R":"nf","PTS_R":"pts"})])
T["x2"]=T.fg-T.x3; T["n2"]=T.fga-T.n3
T=T[(T.n3>0)&(T.n2>0)&(T.nf>0)].copy()
chk=(2*T.x2+3*T.x3+T.xf-T.pts).abs()
print(f"IDENTITY CHECK 2*2PM+3*3PM+FTM == PTS : max|err| {chk.max():.0f}, "
      f"exact on {100*(chk==0).mean():.1f}% of {len(T):,} team-games")
T=T[chk==0]

print("\nWITHIN-TEAM-SEASON OVERDISPERSION (cross-team quality removed)")
print(f"  {'shot':<6}{'p_hat':>8}{'mean n':>9}{'phi (disp)':>12}{'rho (ICC)':>12}{'var/attempt':>14}{'binomial':>11}")
out={}
for lab,xc,nc,pv in [("3PT","x3","n3",9.0),("2PT","x2","n2",4.0),("FT","xf","nf",1.0)]:
    num=den=0.0; k=0; ns=[]
    for (t,y),g in T.groupby(["t","yr"]):
        if len(g)<40: continue
        p=g[xc].sum()/g[nc].sum(); v=g[nc]*p*(1-p)
        num+=(((g[xc]-g[nc]*p)**2)/v).sum(); k+=len(g)-1; ns.append(g[nc].mean())
    phi=num/k; nb=np.mean(ns); rho=(phi-1)/(nb-1)
    p=T[xc].sum()/T[nc].sum(); vpa=pv*p*(1-p)*phi
    out[lab]=dict(p=p,phi=phi,rho=rho,vpa=vpa,binom=pv*p*(1-p),nbar=nb)
    print(f"  {lab:<6}{p:>8.4f}{nb:>9.1f}{phi:>12.4f}{rho:>12.5f}{vpa:>14.4f}{pv*p*(1-p):>11.4f}")

print("\nCROSS-CHANNEL CORRELATION WITHIN A GAME (is a hot night hot everywhere?)")
R={}
for lab,xc,nc in [("3PT","x3","n3"),("2PT","x2","n2"),("FT","xf","nf")]:
    g=T.groupby(["t","yr"]); p=g[xc].transform("sum")/g[nc].transform("sum")
    R[lab]=(T[xc]-T[nc]*p)/np.sqrt(T[nc]*p*(1-p))
RD=pd.DataFrame(R)
print(RD.corr().round(4).to_string())

print("\nREBUILD THE VARIANCE AND VALIDATE AGAINST THE OBSERVED TOTAL")
p3,p2,pf=out["3PT"],out["2PT"],out["FT"]
n3,n2,nf=T.n3.mean(),T.n2.mean(),T.nf.mean()
v3=9*p3["p"]*(1-p3["p"])*p3["phi"]*n3
v2=4*p2["p"]*(1-p2["p"])*p2["phi"]*n2
vf=1*pf["p"]*(1-pf["p"])*pf["phi"]*nf
c32=RD["3PT"].corr(RD["2PT"])*np.sqrt(v3*v2)*(3*2/(3*2))
cov=2*(3*2*RD["3PT"].corr(RD["2PT"])*np.sqrt(v3/9*v2/4)*3*2
      +3*1*RD["3PT"].corr(RD["FT"])*np.sqrt(v3/9*vf/1)*3*1
      +2*1*RD["2PT"].corr(RD["FT"])*np.sqrt(v2/4*vf/1)*2*1)/2
vteam_shoot=v3+v2+vf+2*(RD["3PT"].corr(RD["2PT"])*np.sqrt(v3*v2)
                        +RD["3PT"].corr(RD["FT"])*np.sqrt(v3*vf)
                        +RD["2PT"].corr(RD["FT"])*np.sqrt(v2*vf))
print(f"  per-team shooting variance (attempts FIXED): 3PT {v3:.1f} + 2PT {v2:.1f} + FT {vf:.1f}"
      f" + cov -> {vteam_shoot:.1f}  (sd {np.sqrt(vteam_shoot):.2f})")
gm=T.groupby(["t","yr"])
print(f"  DIRECT check: within-team-season sd of team points = "
      f"{np.sqrt((T.pts-gm.pts.transform('mean')).pow(2).mean()):.2f}"
      f"   (includes attempt/pace variation, so must be LARGER)")
tot2=2*vteam_shoot
print(f"  two independent teams -> game-total shooting sd {np.sqrt(tot2):.2f}"
      f"   vs OBSERVED sd(dev) 18.06")

print("\nTHE CORRECTED BENCHMARK")
ex_b=9*p3["p"]*(1-p3["p"])-4*p2["p"]*(1-p2["p"])
ex_c=p3["vpa"]-p2["vpa"]
fga=(d.FGA_H+d.FGA_R).mean(); sg=18.10
print(f"  excess var per shot converted 2->3   BINOMIAL {ex_b:.4f}   CORRELATION-CORRECTED {ex_c:.4f}"
      f"   ({ex_c/ex_b:.2f}x)")
print(f"  d(sigma)/d(3PArate) = FGA*excess/(2*sigma):"
      f"   BINOMIAL {fga*ex_b/(2*sg):.2f}  ->  CORRECTED {fga*ex_c/(2*sg):.2f}")
print(f"\n  LADDER MEASURED  +3.259   95% CI [+1.11, +5.41]")
for nm,v in [("binomial benchmark",fga*ex_b/(2*sg)),("corrected benchmark",fga*ex_c/(2*sg))]:
    print(f"    {nm:<22}{v:+.2f}   {'INSIDE the CI' if 1.11<=v<=5.41 else 'OUTSIDE the CI'}"
          f"   ladder is {100*3.259/v:.0f}% of it")
