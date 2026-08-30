import sqlite3,warnings,numpy as np,pandas as pd
from scipy.stats import norm
warnings.filterwarnings("ignore")
c=sqlite3.connect("file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro",uri=True)
m=pd.read_sql("SELECT event_ticker,floor_strike,pregame_mid,game_date FROM markets",c); c.close()
for col in("floor_strike","pregame_mid"): m[col]=pd.to_numeric(m[col],errors="coerce")
m["p"]=m.pregame_mid/100.0
m=m.dropna(subset=["floor_strike","p"]); m=m[(m.p>0.03)&(m.p<0.97)&m.floor_strike.between(150,300)]
def fitsig(K,p):
    if len(K)<4: return np.nan
    z=norm.ppf(1.0-p); A=np.column_stack([np.ones(len(K)),K])
    b,*_=np.linalg.lstsq(A,z,rcond=None)
    return 1.0/b[1] if b[1]>0 else np.nan
rows=[]
for ev,g in m.groupby("event_ticker"):
    g=g.drop_duplicates("floor_strike").sort_values("floor_strike")
    if len(g)<8: continue
    K=g.floor_strike.values; p=g.p.values
    sa=fitsig(K[0::2],p[0::2]); sb=fitsig(K[1::2],p[1::2]); sf=fitsig(K,p)
    rows.append((ev,len(K),sf,sa,sb))
S=pd.DataFrame(rows,columns=["ev","n","sig","sa","sb"]).dropna()
S=S[(S.sig.between(8,40))&(S.sa.between(8,40))&(S.sb.between(8,40))]
print(f"SPLIT-HALF on {len(S):,} ladders (odd rungs vs even rungs, same quotes)")
d=S.sa-S.sb
vhalf=d.var()/2
vfull=vhalf/2
print(f"  sd(odd-half sigma - even-half sigma) = {d.std():.4f}")
print(f"  => noise var of a HALF ladder {vhalf:.4f} (sd {np.sqrt(vhalf):.4f})")
print(f"  => noise var of the FULL ladder {vfull:.4f} (sd {np.sqrt(vfull):.4f})")
tot=S.sig.var()
print(f"\n  observed var(implied sigma) = {tot:.4f}  (sd {S.sig.std():.4f})")
true=tot-vfull
print(f"  measurement noise           = {vfull:.4f}")
print(f"  => TRUE ladder-sigma var    = {true:.4f}  (sd {np.sqrt(max(true,0)):.4f})")
print(f"  reliability of one implied sigma = {true/tot:.3f}")
print(f"\n  our 3-variable model explained R2 0.0771 of the OBSERVED variance = {0.0771*tot:.4f}")
print(f"  as a share of TRUE variation: {100*0.0771*tot/max(true,1e-9):.1f}%")
print(f"  => the ladder's sigma still has {100*(1-0.0771*tot/max(true,1e-9)):.0f}% of its REAL"
      f" variation unexplained by pace + 3PA + mu")
