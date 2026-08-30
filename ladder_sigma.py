import sqlite3,warnings,numpy as np,pandas as pd
from scipy.stats import norm
warnings.filterwarnings("ignore")
C="file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro"
c=sqlite3.connect(C,uri=True)
m=pd.read_sql("SELECT event_ticker,floor_strike,pregame_mid,pregame_yes_bid,"
              "pregame_yes_ask,strike_type,result,game_date FROM markets",c)
e=pd.read_sql("SELECT event_ticker,away_team,home_team,game_date FROM events",c); c.close()
for col in("floor_strike","pregame_mid","pregame_yes_bid","pregame_yes_ask"):
    m[col]=pd.to_numeric(m[col],errors="coerce")
print("strike_type:",m.strike_type.value_counts().head(4).to_dict())
print("pregame_mid range: %.3f .. %.3f  (cents if >1)"%(m.pregame_mid.min(),m.pregame_mid.max()))
m=m[m.strike_type.astype(str).str.lower().str.contains("greater",na=False)|m.floor_strike.notna()]
sc=100.0 if m.pregame_mid.max()>1.5 else 1.0
m["p"]=m.pregame_mid/sc
m=m.dropna(subset=["floor_strike","p"])
m=m[(m.p>0.03)&(m.p<0.97)&m.floor_strike.between(150,300)]
m["sprd"]=(m.pregame_yes_ask-m.pregame_yes_bid)/sc
print(f"usable rungs {len(m):,} over {m.event_ticker.nunique():,} events\n")

rows=[]
for ev,g in m.groupby("event_ticker"):
    g=g.drop_duplicates("floor_strike").sort_values("floor_strike")
    if len(g)<5: continue
    K=g.floor_strike.values; z=norm.ppf(1.0-g.p.values)
    if not np.all(np.diff(K)>0): continue
    A=np.column_stack([np.ones(len(K)),K]); b,*_=np.linalg.lstsq(A,z,rcond=None)
    if b[1]<=0: continue
    sig=1.0/b[1]; mu=-b[0]*sig
    r=z-A@b
    rows.append((ev,g.game_date.iloc[0],len(K),mu,sig,np.abs(r).max(),g.sprd.mean()))
L=pd.DataFrame(rows,columns=["ev","date","nrung","mu","sig","maxres","sprd"])
L=L[(L.sig.between(8,40))&(L.mu.between(150,300))]
print(f"LADDERS FITTED: {len(L):,} games   median rungs {L.nrung.median():.0f}")
print(f"  implied mu   mean {L.mu.mean():.2f}   sd {L.mu.std():.2f}")
print(f"  implied SIGMA mean {L.sig.mean():.3f}  sd {L.sig.std():.3f}  "
      f"IQR {L.sig.quantile(.25):.2f}-{L.sig.quantile(.75):.2f}")
print(f"  mean |probit residual| (fit quality) {L.maxres.median():.4f}\n")

print("DOES THE LADDER SCALE ITS SIGMA WITH THE LINE?")
X=np.column_stack([np.ones(len(L)),L.mu.values]); y=L.sig.values
b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
se=np.sqrt(np.diag((r@r/(len(y)-2))*np.linalg.pinv(X.T@X)))
print(f"  implied_sigma ~ implied_mu    slope {b[1]:+.5f}  (t={b[1]/se[1]:+.2f})"
      f"   95% CI [{b[1]-1.96*se[1]:+.5f}, {b[1]+1.96*se[1]:+.5f}]")
print(f"  POISSON benchmark  dsigma/dmu = sigma/(2mu) = {L.sig.mean()/(2*L.mu.mean()):+.5f}")
print(f"  TRUE benchmark measured on 9,489 games      = +0.04030   (17.58@206 -> 19.01@241)")
print(f"  corr(sigma, mu) = {L.sig.corr(L.mu):+.4f}\n")
print(f"  {'mu quintile':<13}{'n':>6}{'mean mu':>10}{'mean implied sig':>19}{'Poisson-scaled':>16}")
q=pd.qcut(L.mu,5,labels=False); base=None
for i in range(5):
    s=L[q==i]
    if base is None: base=(s.mu.mean(),s.sig.mean())
    print(f"  {i+1:<13}{len(s):>6}{s.mu.mean():>10.1f}{s.sig.mean():>19.3f}"
          f"{base[1]*np.sqrt(s.mu.mean()/base[0]):>16.3f}")
L.to_csv("/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/ladder_sigma.csv",index=False)
