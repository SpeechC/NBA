import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
L=pd.read_csv(SP+"ladder_sigma.csv")
L["away"]=L.ev.str.extract(r"([A-Z]{3})[A-Z]{3}$"); L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv")
print("team_mapping cols:",list(tm.columns))
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy(); d["ph"]=n("PTS_H"); d["pr"]=n("PTS_R"); d["close"]=n("CLOSING TOTAL_H")
d["total"]=d.ph+d.pr; d["date"]=pd.to_datetime(d["DATE"],errors="coerce").dt.strftime("%Y-%m-%d")
d=d.dropna(subset=["total","close"])
# map abbrevs -> master names via mapping file
cand=[c for c in tm.columns]
mp=None
for a in cand:
    for b in cand:
        if a==b: continue
        s=tm[[a,b]].dropna()
        if s[a].astype(str).str.fullmatch(r"[A-Z]{3}").mean()>0.8 and \
           s[b].astype(str).isin(set(d.TEAM_H.dropna())).mean()>0.8:
            mp=dict(zip(s[a],s[b])); print(f"  mapping {a} -> {b}, {len(mp)} teams"); break
    if mp: break
if mp is None: raise SystemExit("no mapping found")
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(d[["date","TEAM_H","total","close"]],left_on=["date","home_n"],
          right_on=["date","TEAM_H"],how="inner")
print(f"\nJOINED {len(M):,} of {len(L):,} ladder games")
M["dev"]=M.total-M.mu
print(f"  implied mu vs sportsbook close: corr {M.mu.corr(M.close):+.4f}  mean diff {(M.mu-M.close).mean():+.3f}")
print(f"  realised sd(total - implied mu) = {M.dev.std():.3f}   mean implied sigma = {M.sig.mean():.3f}")
print(f"  -> ladder is {'TOO WIDE' if M.sig.mean()>M.dev.std() else 'TOO NARROW'} on average by "
      f"{M.sig.mean()-M.dev.std():+.3f} pts ({100*(M.sig.mean()/M.dev.std()-1):+.1f}%)\n")

print("POWER FIRST — can these games resolve the slope question?")
X=np.column_stack([np.ones(len(M)),M.mu.values]); y=(M.dev**2).values
b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
se=np.sqrt(np.diag((r@r/(len(y)-2))*np.linalg.pinv(X.T@X)))
lad=2*M.sig.mean()*0.06061; tru=2*M.sig.mean()*0.04030
print(f"  ladder slope implies d(sig^2)/dmu = {lad:.3f};  true/Poisson implies {tru:.3f}")
print(f"  observed dev^2 ~ mu  beta {b[1]:+.3f} (t={b[1]/se[1]:+.2f})  se {se[1]:.3f}")
print(f"  gap to distinguish = {lad-tru:.3f};  needed se < {(lad-tru)/1.96:.3f}  -> "
      f"{'RESOLVABLE' if se[1]<(lad-tru)/1.96 else 'NOT RESOLVABLE at this n'}")
print(f"  games needed ~ {len(M)*(se[1]/((lad-tru)/1.96))**2:,.0f}\n")

print("SIDE BY SIDE, by implied-mu quintile")
q=pd.qcut(M.mu,5,labels=False)
print(f"  {'q':<4}{'n':>6}{'mean mu':>10}{'ladder sig':>12}{'REALISED sd':>13}{'+-noise':>9}{'ladder-real':>13}")
for i in range(5):
    s=M[q==i]; rs=s.dev.std(); nz=rs/np.sqrt(2*len(s))
    print(f"  {i+1:<4}{len(s):>6}{s.mu.mean():>10.1f}{s.sig.mean():>12.3f}{rs:>13.3f}{nz:>9.3f}{s.sig.mean()-rs:>13.3f}")

print("\nARTIFACT CHECKS on the implied-sigma estimate")
for nm,v in [("mean quoted spread",M.sprd),("n rungs used",M.nrung),("max probit resid",M.maxres)]:
    print(f"  corr({nm:<19}, implied mu) = {v.corr(M.mu):+.4f}")
