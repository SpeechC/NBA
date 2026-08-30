import warnings,numpy as np,pandas as pd
from scipy.stats import norm
warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
R=pd.read_csv(SP+"stageA_rungs.csv"); L=pd.read_csv(SP+"stageA_fits.csv")
print("LADDER SPAN LIMITATION — stated before any tail claim")
print(f"  z range covered: p1 {R.z.quantile(.01):+.2f}  p99 {R.z.quantile(.99):+.2f}"
      f"   |z|>1.5: {100*(R.z.abs()>1.5).mean():.2f}%   |z|>2: {100*(R.z.abs()>2).mean():.3f}%")
print("  => the ladder spans ~+-1.7 sigma. TAIL SHAPE IS NOT TESTABLE on this data.")

print("\nA5 — UNIVERSAL COLLAPSE:  does every rung from every game lie on ONE curve?")
b=pd.cut(R.z,np.arange(-2.25,2.26,0.25))
t=R.groupby(b).agg(n=("mid","size"),zbar=("z","mean"),mkt=("mid","mean"),
                   sd=("mid","std"),bid=("bid","mean"),ask=("ask","mean"))
t=t[t.n>=30]; t["normal"]=1-norm.cdf(t.zbar); t["gap_c"]=(t.mkt-t.normal)*100
t["resid_sd_c"]=t.sd*100
print(f"  {'z bin':<16}{'n':>6}{'market':>9}{'Normal':>9}{'gap(c)':>9}{'within-bin sd(c)':>18}")
for i,r in t.iterrows():
    print(f"  {str(i):<16}{int(r.n):>6}{r.mkt:>9.4f}{r.normal:>9.4f}{r.gap_c:>+9.3f}{r.resid_sd_c:>18.3f}")
print(f"\n  POOLED: sd of (market - Normal(z)) across ALL {len(R):,} rungs ="
      f" {100*(R.mid-(1-norm.cdf(R.z))).std():.3f}c")
print(f"  for comparison, sd of the raw market probabilities = {100*R.mid.std():.3f}c")
print(f"  => the z-transform removes {100*(1-((R.mid-(1-norm.cdf(R.z))).std()/R.mid.std())**2):.2f}% of rung-price variance")

print("\nIS THE A4 OVER-SIDE GAP REAL SKEW, OR A QUOTE ARTIFACT?")
print("  if genuine skew, it survives in the BID and the ASK separately;")
print("  if a minimum-tick/overround artifact, it lives in the mid only.")
R["pn"]=1-norm.cdf(R.z)
for lab,lo,hi in [("cheap  (mid<0.30)",0,0.30),("mid    (0.30-0.70)",0.30,0.70),
                  ("rich   (mid>0.70)",0.70,1.01)]:
    s=R[(R.mid>=lo)&(R.mid<hi)]
    print(f"  {lab:<20} n={len(s):>6,}  bid-model {100*(s.bid-s.pn).mean():+7.3f}c"
          f"  mid-model {100*(s.mid-s.pn).mean():+7.3f}c  ask-model {100*(s.ask-s.pn).mean():+7.3f}c"
          f"  width {100*(s.ask-s.bid).mean():5.2f}c")
print("\n  the SAME cut, but only tight books (width <= 2c), where the artifact is smallest:")
Rt=R[(R.ask-R.bid)<=0.02]
for lab,lo,hi in [("cheap",0,0.30),("mid",0.30,0.70),("rich",0.70,1.01)]:
    s=Rt[(Rt.mid>=lo)&(Rt.mid<hi)]
    if len(s)<50: continue
    print(f"    {lab:<8} n={len(s):>6,}  mid-model {100*(s.mid-s.pn).mean():+7.3f}c")

print("\nWORST-FIT LADDERS — is the 38.7c max error a real ladder or a data fault?")
w=L.sort_values("maxe",ascending=False).head(5)
print(w[["ev","n","span","wbar","mu_w","s_w","maxe"]].to_string(index=False))
print(f"\n  ladders with max|error| > 10c: {(L.maxe>0.10).sum()} of {len(L):,}"
      f" ({100*(L.maxe>0.10).mean():.2f}%)")
print(f"  excluding them, per-rung MAE = "
      f"{100*R[~R.ev.isin(L[L.maxe>0.10].ev)].e.abs().mean():.3f}c")
