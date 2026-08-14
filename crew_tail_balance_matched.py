import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crew_team_diag as ctd, ref_features as rf, ref_regime as rg
from data_split import SPLIT_DATE
from crew_tail_balance import AVG, label
NPERM=400; RNG=np.random.default_rng(31337)
rgd,_,_=rg.build(); dv=rgd[rgd["date"]<SPLIT_DATE]
q85,q15=dv["CrewShock"].quantile(0.85),dv["CrewShock"].quantile(0.15)
d=ctd.build(); STATES=list(ctd.STATES)
s=d.dropna(subset=["CrewShock"]+STATES).reset_index(drop=True)
for nm,(a,b) in AVG.items(): s[nm]=(s[a]+s[b])/2.0
COLS=STATES+list(AVG)
hi=(s["CrewShock"]>=q85).values; lo=(s["CrewShock"]<=q15).values
nH,nL=int(hi.sum()),int(lo.sum())
X=s[COLS].values
def smds(mask_h,mask_l):
    a,b=X[mask_h],X[mask_l]
    p=np.sqrt((a.std(0,ddof=1)**2+b.std(0,ddof=1)**2)/2)
    return np.divide(a.mean(0)-b.mean(0),p,out=np.zeros(len(COLS)),where=p>0)
obs=smds(hi,lo)
teams=sorted(set(s["TEAM_H"])|set(s["TEAM_R"])); ti={t:i for i,t in enumerate(teams)}
A=np.zeros((len(s),len(teams)))
for r,(th,ta) in enumerate(zip(s["TEAM_H"],s["TEAM_R"])): A[r,ti[th]]=1; A[r,ti[ta]]=1
cA=A.sum(0); obs_hi=A[hi].sum(0)/cA
uni,k,crew,blocks,keep=ctd.perm_setup(s); sub=uni.copy()
nS=np.empty((NPERM,len(COLS))); nT=np.empty((NPERM,len(teams))); sz=[]
for j in range(NPERM):
    perm=crew.copy()
    for b in blocks:
        if len(b)>1: perm[b]=crew[b][RNG.permutation(len(b))]
    sub["ref1"],sub["ref2"],sub["ref3"]=perm[:,0],perm[:,1],perm[:,2]
    c=rf.matched_ref_effect(sub,k)["CrewShock"].values[keep]
    o=np.argsort(c); mh=np.zeros(len(s),bool); ml=np.zeros(len(s),bool)
    mh[o[-nH:]]=True; ml[o[:nL]]=True
    sz.append(((c>=q85).sum(),(c<=q15).sum()))
    nS[j]=smds(mh,ml); nT[j]=A[mh].sum(0)/cA
fw=np.abs(nS).max(1); m=np.abs(obs).max()
sz=np.array(sz)
print("MATCHED-SIZE PERMUTATION (tails of size %d / %d, as observed)"%(nH,nL))
print("  frozen-threshold null would have selected median HIGH %d / LOW %d"
      "  -> that is why the first pass was broken"%(np.median(sz[:,0]),np.median(sz[:,1])))
print("\n  observed max |SMD|              %.4f (%s)"%(m,COLS[int(np.argmax(np.abs(obs)))]))
print("  permutation-null mean max |SMD| %.4f"%fw.mean())
print("  permutation SD                  %.4f"%fw.std())
print("  permutation 95th percentile     %.4f"%np.percentile(fw,95))
print("  FAMILY-WISE empirical p         %.4f"%((1+(fw>=m).sum())/(NPERM+1)))
print("\n  per-variable permutation p, top 8 by |SMD|:")
order=np.argsort(-np.abs(obs))
for i in order[:8]:
    p=(1+(np.abs(nS[:,i])>=abs(obs[i])).sum())/(NPERM+1)
    print("    %-20s SMD %+.4f   perm p %.4f   %s"%(COLS[i],obs[i],p,label(obs[i])))
z=(obs_hi-nT.mean(0))/nT.std(0); fwT=np.abs((nT-nT.mean(0))/nT.std(0)).max(1)
T=pd.DataFrame({"Team":teams,"games":cA.astype(int),
  "HIGH share %":(100*obs_hi).round(2),"LOW share %":(100*A[lo].sum(0)/cA).round(2),
  "perm z":z.round(2),"FWER p":[(1+(fwT>=abs(v)).sum())/(NPERM+1) for v in z]})
T=T.sort_values("HIGH share %",ascending=False)
print("\nTEAM COMPOSITION, matched-size null")
print(T.head(5).to_string(index=False)); print("  ...")
print(T.tail(5).to_string(index=False))
print("\n  max |z| %.2f   family-wise p = %.4f"%(np.abs(z).max(),
      (1+(fwT>=np.abs(z).max()).sum())/(NPERM+1)))
