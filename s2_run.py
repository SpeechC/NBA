import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"s2_panel.csv")
G["total"]=G.PTS_H+G.PTS_R; G["open"]=G["OPENING TOTAL_H"]; G["close"]=G["CLOSING TOTAL_H"]
G=G.dropna(subset=["total","open","close","That"])
G["Y"]=G.total-G.close; G["MV"]=G.close-G.open
D=pd.get_dummies(G.season,prefix="s",drop_first=True).astype(float)
def ols(y,X):
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-X.shape[1]))*np.linalg.pinv(X.T@X)))
    return b,se
print(f"CONFIRMATORY RUN — n(H1,H3)={G.Z_H1.notna().sum():,}  n(H2)={G.Z_H2.notna().sum():,}")
print(f"sd(Y = actual - close) = {G.Y.std():.3f}")
print("POWER (corrected): MDE at 80% power, one-sided alpha=.05, is (z.95+z.80)*SE = 2.487*SE")
print("  and under Holm the earliest threshold uses alpha/3, giving 2.970*SE\n")
res={}
for k in ["Z_H1","Z_H2","Z_H3"]:
    s=G[G[k].notna()].copy(); Z=(s[k]-s[k].mean())/s[k].std()      # per-SD units
    d=pd.get_dummies(s.season,prefix="s",drop_first=True).astype(float)
    # 5. MARKET INCORPORATION  open ~ That + Z
    Xm=np.column_stack([np.ones(len(s)),s.That.values,Z.values])
    bm,sem=ols(s.open.values,Xm); bl,sl=bm[2],sem[2]
    lo90,hi90=bl-1.645*sl,bl+1.645*sl
    equiv=(lo90>-0.25)and(hi90<0.25)
    incorp=(abs(bl)-1.96*sl>0)and(abs(bl)>0.25)
    cls="Equivalent to zero" if equiv else ("Incorporated" if incorp else "Indeterminate")
    # 6. PRIMARY OUTCOME  Y ~ Z + season + close
    Xo=np.column_stack([np.ones(len(s)),Z.values,s.close.values,d.values])
    bo,seo=ols(s.Y.values,Xo); bt,st=bo[1],seo[1]
    p1=stats.norm.sf(bt/st)                                        # one-sided, predicted POSITIVE
    # 10. MOVEMENT (diagnostic only)
    Xv=np.column_stack([np.ones(len(s)),Z.values,d.values])
    bv,sev=ols(s.MV.values,Xv)
    res[k]=dict(n=len(s),bl=bl,sl=sl,lo=lo90,hi=hi90,cls=cls,bt=bt,st=st,p1=p1,
                bv=bv[1],tv=bv[1]/sev[1],Z=Z,s=s)
print(f"  {'H':<4}{'se_out':>9}{'MDE 80%':>10}{'MDE Holm':>11}{'vs 0.460 target':>18}")
for i,k in enumerate(["Z_H1","Z_H2","Z_H3"],1):
    se_=res[k]["st"]; m1,m2=2.4866*se_,2.9696*se_
    print(f"  H{i:<3}{se_:>9.4f}{m1:>10.4f}{m2:>11.4f}"
          f"{('powered pre-Holm' if m1<=0.460 else 'UNDERPOWERED'):>18}")
print()
print("5. MARKET-INCORPORATION TEST  (TOST, 90% CI vs +-0.25 pts/SD)")
print(f"  {'H':<4}{'beta_line':>11}{'se':>7}{'90% CI':>22}{'classification':>22}")
for i,k in enumerate(res,1):
    r=res[k]; print(f"  H{i:<3}{r['bl']:>+11.4f}{r['sl']:>7.4f}   [{r['lo']:>+7.4f},{r['hi']:>+7.4f}]{r['cls']:>22}")
print("\n6+7. PRIMARY OUTCOME  Y = actual - close   (one-sided positive, HOLM at 0.05)")
order=sorted(res,key=lambda k:res[k]["p1"]); m=len(order)
holm={}
for j,k in enumerate(order):
    adj=(m-j)*res[k]["p1"]; adj=max(adj,holm[order[j-1]] if j else 0); holm[k]=min(adj,1.0)
print(f"  {'H':<4}{'n':>7}{'beta_out':>11}{'se':>7}{'t':>7}{'p(1-sided)':>12}{'Holm p':>9}{'sig':>6}")
for i,k in enumerate(["Z_H1","Z_H2","Z_H3"],1):
    r=res[k]
    print(f"  H{i:<3}{r['n']:>7,}{r['bt']:>+11.4f}{r['st']:>7.4f}{r['bt']/r['st']:>+7.2f}"
          f"{r['p1']:>12.4f}{holm[k]:>9.4f}{'YES' if holm[k]<0.05 else 'no':>6}")
print("\n10. MOVEMENT (DIAGNOSTIC ONLY — cannot advance a hypothesis)")
for i,k in enumerate(["Z_H1","Z_H2","Z_H3"],1):
    print(f"  H{i}  close-open ~ Z : {res[k]['bv']:+.4f} (t={res[k]['tv']:+.2f})")
print("\n9. ECONOMIC MATERIALITY — top quintile vs rest, matched on close within season")
print(f"  {'H':<4}{'n top':>7}{'mean Y top':>12}{'mean Y rest':>13}{'diff':>9}{'>=0.75?':>9}")
for i,k in enumerate(["Z_H1","Z_H2","Z_H3"],1):
    r=res[k]; s=r["s"].copy(); s["Zq"]=r["Z"].values
    s["adj"]=s.Y-s.groupby([s.season,pd.qcut(s.close,5,labels=False,duplicates="drop")]).Y.transform("mean")
    thr=s.Zq.quantile(0.8); a,b=s[s.Zq>=thr],s[s.Zq<thr]
    diff=a.adj.mean()-b.adj.mean()
    print(f"  H{i:<3}{len(a):>7,}{a.adj.mean():>+12.4f}{b.adj.mean():>+13.4f}{diff:>+9.4f}"
          f"{('YES' if abs(diff)>=0.75 else 'no'):>9}")
print("\n8. CLASSIFICATION")
for i,k in enumerate(["Z_H1","Z_H2","Z_H3"],1):
    r=res[k]; oe=holm[k]<0.05
    tab={("Equivalent to zero",True):"CANDIDATE OMITTED MATCHUP STATE",
         ("Equivalent to zero",False):"IRRELEVANT TO MEAN PRICING",
         ("Incorporated",True):"MARKET RECOGNIZES BUT MISPRICES",
         ("Incorporated",False):"MARKET PRICES INTERACTION",
         ("Indeterminate",True):"UNRESOLVED",("Indeterminate",False):"UNRESOLVED"}
    print(f"  H{i}  {r['cls']:<20} + {'outcome effect' if oe else 'no outcome effect':<18} -> {tab[(r['cls'],oe)]}")
