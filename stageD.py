import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"stageB_panel.csv"); G["date"]=pd.to_datetime(G.date); G["yr"]=G.yr.astype(int)
G=G.sort_values("date").reset_index(drop=True)
G["M"]=-G.ospread                      # implied home margin
G["impH"]=(G.open+G.M)/2; G["impR"]=(G.open-G.M)/2
G=G.dropna(subset=["impH","impR","open"]).reset_index(drop=True)
teams=sorted(set(G.TEAM_H)|set(G.TEAM_R)); ti={t:i for i,t in enumerate(teams)}
print(f"STAGE D — LATENT MARKET RATINGS FROM THE LINES  n={len(G):,}  teams={len(teams)}")
print("  ratings are updated ONLY from past games; every prediction precedes its own update\n")
def run(k,lam,pace=False):
    """recursive two-way ratings: impH = base + Off[H] + Def[R] + hfa ; impR = base + Off[R] + Def[H]"""
    Off=np.zeros(len(teams)); Def=np.zeros(len(teams))
    base=G.impH.mean(); hfa=(G.impH-G.impR).mean()/2
    pred=np.full(len(G),np.nan); yr_prev=None
    for i,r in enumerate(G.itertuples()):
        if yr_prev is not None and r.yr!=yr_prev:      # season carry-over shrinkage
            Off*=lam; Def*=lam
        yr_prev=r.yr
        h,a=ti[r.TEAM_H],ti[r.TEAM_R]
        pH=base+Off[h]+Def[a]+hfa; pR=base+Off[a]+Def[h]-hfa
        pred[i]=pH+pR                                   # PREDICT FIRST
        eH=r.impH-pH; eR=r.impR-pR                      # then update
        Off[h]+=k*eH; Def[a]+=k*eH
        Off[a]+=k*eR; Def[h]+=k*eR
    return pred
def sc(pred,mask,lbl):
    y=G.open.values; m=mask&~np.isnan(pred)
    e=y[m]-pred[m]; r2=1-e.var()/y[m].var()
    print(f"  {lbl:<40}{np.sqrt((e**2).mean()):>8.3f}{np.abs(e).mean():>8.3f}{r2:>9.4f}"
          f"{100*(np.abs(e)<=1).mean():>8.1f}{100*(np.abs(e)<=2).mean():>8.1f}")
    return r2
DEV=(G.yr<=2021).values; TEST=(G.yr>=2022).values
print("  TUNING (k, lambda) on 2017-2021 ONLY, then applied unchanged to 2022-2026")
best=None
for k in [0.02,0.05,0.10,0.15,0.20,0.30]:
    for lam in [0.4,0.6,0.8,1.0]:
        p=run(k,lam); y=G.open.values; m=DEV&~np.isnan(p)
        r2=1-((y[m]-p[m]).var()/y[m].var())
        if best is None or r2>best[0]: best=(r2,k,lam)
print(f"  selected k={best[1]}, lambda={best[2]}  (dev R2 {best[0]:.4f})\n")
print(f"  {'model  (HELD-OUT 2022-2026)':<40}{'RMSE':>8}{'MAE':>8}{'R2':>9}{'<=1':>8}{'<=2':>8}")
pD=run(best[1],best[2]); sc(pD,TEST,"D2 latent Off/Def ratings (lines only)")
# --- Stage B comparators on the SAME held-out window, same chronological protocol ---
def xfit(cols):
    pr=np.full(len(G),np.nan)
    for y in sorted(G.yr.unique())[1:]:
        tr=G[(G.yr<y)]; te=G[G.yr==y]
        A=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        B=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(A).all(1)
        b,*_=np.linalg.lstsq(A[ok],tr.open.values[ok],rcond=None); pr[te.index]=B@b
    return pr
REC=["Hs_pace","Rs_pace","Hs_oeff","Rs_oeff","Hs_deff","Rs_deff"]
ALL=["H_oeff","R_oeff","H_deff","R_deff","H_pace","R_pace","H_efg","R_efg","H_tov","R_tov",
     "H_ftr","R_ftr","H_reb","R_reb","H_t3r","R_t3r","H_t3p","R_t3p","restH","restR",
     "b2bH","b2bR","doy"]+REC
sc(xfit(["struct"]+REC),TEST,"Stage B best: struct + recent state")
sc(xfit(ALL),TEST,"Stage B M6 full")
G["ratD"]=pD
sc(xfit(["struct"]+REC+["ratD"]),TEST,"struct + recent + LATENT RATINGS")
sc(xfit(["ratD"]),TEST,"latent ratings, refit scale only")
print()
print("  SENSITIVITY of the latent system to its two parameters (held-out window)")
print(f"  {'k':>6}{'lambda':>8}{'R2':>9}")
for k in [0.05,0.10,0.20]:
    for lam in [0.6,0.8,1.0]:
        p=run(k,lam); y=G.open.values; m=TEST&~np.isnan(p)
        print(f"  {k:>6.2f}{lam:>8.1f}{1-((y[m]-p[m]).var()/y[m].var()):>9.4f}")

print("\n" + "="*78)
print("CHECK 1 — extend the k grid; the optimum sat at the boundary (k=0.30)")
print(f"  {'k':>6}{'lam':>6}{'dev R2':>10}{'TEST R2':>10}")
for k in [0.30,0.40,0.50,0.65,0.80,1.00]:
    p=run(k,0.6); y=G.open.values
    md=DEV&~np.isnan(p); mt=TEST&~np.isnan(p)
    print(f"  {k:>6.2f}{0.6:>6.1f}{1-((y[md]-p[md]).var()/y[md].var()):>10.4f}"
          f"{1-((y[mt]-p[mt]).var()/y[mt].var()):>10.4f}")
print("\nCHECK 2 — is the gain the OPPONENT ADJUSTMENT, or just line autocorrelation?")
def run1(k,lam):
    """own-rating ONLY: no Def state, so no opponent adjustment"""
    Off=np.zeros(len(teams)); base=G.impH.mean(); hfa=(G.impH-G.impR).mean()/2
    pred=np.full(len(G),np.nan); yp=None
    for i,r in enumerate(G.itertuples()):
        if yp is not None and r.yr!=yp: Off*=lam
        yp=r.yr; h,a=ti[r.TEAM_H],ti[r.TEAM_R]
        pH=base+Off[h]+hfa; pR=base+Off[a]-hfa
        pred[i]=pH+pR
        Off[h]+=k*(r.impH-pH); Off[a]+=k*(r.impR-pR)
    return pred
def lastline(lam=1.0):
    """crudest baseline: each team's MOST RECENT implied points, summed"""
    last={}; pred=np.full(len(G),np.nan); base=G.impH.mean()
    for i,r in enumerate(G.itertuples()):
        h,a=r.TEAM_H,r.TEAM_R
        pred[i]=last.get(h,base)+last.get(a,base)
        last[h]=r.impH; last[a]=r.impR
    return pred
print(f"  {'model (HELD-OUT 2022-2026)':<40}{'RMSE':>8}{'MAE':>8}{'R2':>9}{'<=1':>8}{'<=2':>8}")
sc(lastline(),TEST,"last observed implied points (crudest)")
bk=0.30
sc(run1(bk,0.6),TEST,f"D1 own-rating only, no opp adj (k={bk})")
sc(run(bk,0.6),TEST,f"D2 two-way Off/Def       (k={bk})")
print("\nCHECK 3 — do the recovered ratings behave like real team quality?")
Off=np.zeros(len(teams)); Def=np.zeros(len(teams))
base=G.impH.mean(); hfa=(G.impH-G.impR).mean()/2; yp=None
hist=[]
for r in G.itertuples():
    if yp is not None and r.yr!=yp: Off*=0.6; Def*=0.6
    yp=r.yr; h,a=ti[r.TEAM_H],ti[r.TEAM_R]
    pH=base+Off[h]+Def[a]+hfa; pR=base+Off[a]+Def[h]-hfa
    Off[h]+=0.30*(r.impH-pH); Def[a]+=0.30*(r.impH-pH)
    Off[a]+=0.30*(r.impR-pR); Def[h]+=0.30*(r.impR-pR)
    hist.append((r.yr,r.TEAM_H,Off[h],Def[h]))
H=pd.DataFrame(hist,columns=["yr","t","off","def"])
fin=H.groupby(["yr","t"]).last().reset_index()
z=fin[fin.yr==2024].sort_values("off",ascending=False)
print("  2024-25 end-of-season LATENT OFFENSIVE ratings (pts above league base):")
print("   top 4:", {r.t: round(r.off,2) for r in z.head(4).itertuples()})
print("   bot 4:", {r.t: round(r.off,2) for r in z.tail(4).itertuples()})
print(f"  cross-team sd of latent OFF {fin.off.std():.3f}   DEF {fin['def'].std():.3f}")
