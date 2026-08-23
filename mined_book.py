"""THE MINER — unrestricted cell generation, frozen selection rules, empirical
FDR calibration, two-season holdout evaluation.

Mine dev (<=2023-24, six seasons). Cells = {binary condition or pair} x {O,U},
bet at the CLOSE (-110), pushes void. Selection (FROZEN BEFORE RUNNING):
  dev win% >= 53.5, dev nonpush n >= 600, win%>50 in >=5 of 6 dev seasons.
Book = top 15 by dev win%. Evaluate on 2024-25 + 2025-26.
FDR: 200 permuted-dev pipelines (e shuffled within season), each phantom
book evaluated on the REAL holdout -> the noise-book distribution.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import opening_line_error_decomposition as OLE

RNG = np.random.default_rng(20260823); NREP = 200
DEVMAX = 2023

g = OLE.load(); g["gid"]=g.gid.astype(str).str.strip()
g = g.dropna(subset=["ot_close","total"]).sort_values("date").reset_index(drop=True)
g["e"] = g.total - g.ot_close
from prepare_data import CSV, season_label
raw = pd.read_csv(CSV, low_memory=False); raw["gid"]=raw["GAME-ID"].astype(str).str.strip()
r1 = raw.drop_duplicates("gid").set_index("gid")
g["osp"] = pd.to_numeric(g.gid.map(r1["OPENING SPREAD_H"]), errors="coerce").abs()

# ---------------- team-level rolling states ----------------------------------
L = pd.concat([g[["gid","season","date","home"]].rename(columns={"home":"team"}).assign(side="h"),
               g[["gid","season","date","away"]].rename(columns={"away":"team"}).assign(side="a")]).sort_values("date")
hp=pd.to_numeric(g.set_index("gid").hpts,errors="coerce"); ap=pd.to_numeric(g.set_index("gid").apts,errors="coerce")
L["m"] = np.where(L.side=="h", L.gid.map(hp-ap), L.gid.map(ap-hp))
L["ov"] = np.sign(L.gid.map(g.set_index("gid").e))
pace = pd.concat([pd.DataFrame({"gid":raw["gid"],"pace":pd.to_numeric(raw["PACE_H"],errors="coerce"),"side":"h"}),
                  pd.DataFrame({"gid":raw["gid"],"pace":pd.to_numeric(raw["PACE_R"],errors="coerce"),"side":"a"})])
pace = pace.drop_duplicates(["gid","side"])
L = L.merge(pace, on=["gid","side"], how="left")
L = L.sort_values(["season","team","date"]).reset_index(drop=True)
grp = L.groupby(["season","team"])
L["gap"] = grp["date"].diff().dt.days
L["b2b"] = (L.gap==1).astype(float)
d6 = []
for _,x in L.groupby(["season","team"]):
    dd = x.date.values
    d6 += [int(((dd[i]-dd[max(0,i-5):i]) <= np.timedelta64(5,"D")).sum()>=3) for i in range(len(dd))]
L["in4of6"] = d6
L["mtd"] = grp["m"].transform(lambda s: s.shift(1).expanding().mean())
L["np_"] = grp.cumcount()
L["ov10"] = grp["ov"].transform(lambda s: s.shift(1).rolling(10,min_periods=5).apply(lambda v:(v>0).mean()))
L["pace_td"] = grp["pace"].transform(lambda s: s.shift(1).expanding().mean())
L["pace_z"] = L.pace_td - L.groupby("season")["pace_td"].transform("mean")

W = L.pivot_table(index="gid", columns="side",
                  values=["b2b","in4of6","mtd","np_","ov10","pace_z","gap"], aggfunc="first")
W.columns = [f"{a}_{b}" for a,b in W.columns]
g = g.merge(W, left_on="gid", right_index=True, how="left")
rf = pd.read_csv("ref_features.csv"); rf["gid"]=rf["gid"].astype(str).str.strip()
g["cs"] = g.gid.map(rf.set_index("gid")["CrewShock"])
g["lvl"] = g.ot_close - g.groupby("season")["ot_close"].transform("mean")
g["frac"] = g.groupby("season")["date"].rank(pct=True)
last = g.groupby("season")["date"].transform("max")

ok10 = (g.np__h>=10)&(g.np__a>=10)
B = {}   # name -> (mask, glimpsed_flag)
B["b2b_either"]   = ((g.b2b_h==1)|(g.b2b_a==1), True)
B["b2b_both"]     = ((g.b2b_h==1)&(g.b2b_a==1), False)
B["4in6_either"]  = ((g.in4of6_h==1)|(g.in4of6_a==1), False)
B["rest_gap3"]    = ((g.gap_h-g.gap_a).abs()>=3, False)
B["weekend"]      = (g.date.dt.dayofweek.isin([5,6]), True)
B["final_week"]   = ((last-g.date).dt.days<=7, True)
B["early_season"] = (g.frac<=0.2, True)
B["late_season"]  = (g.frac>=0.8, True)
B["lvl_hi"]       = (g.lvl>=g.lvl.quantile(2/3), True)
B["lvl_lo"]       = (g.lvl<=g.lvl.quantile(1/3), True)
B["sp_close_game"]= (g.osp<=3, True)
B["sp_blowout"]   = (g.osp>=9, True)
B["moved_up"]     = (g.tmove>=1.5, True)
B["moved_down"]   = (g.tmove<=-1.5, True)
B["both_fast"]    = (ok10&(g.pace_z_h>=1)&(g.pace_z_a>=1), True)
B["both_slow"]    = (ok10&(g.pace_z_h<=-1)&(g.pace_z_a<=-1), True)
B["pace_clash"]   = (ok10&(((g.pace_z_h>=1)&(g.pace_z_a<=-1))|((g.pace_z_h<=-1)&(g.pace_z_a>=1))), True)
B["both_strong"]  = (ok10&(g.mtd_h>=4)&(g.mtd_a>=4), False)
B["both_weak"]    = (ok10&(g.mtd_h<=-4)&(g.mtd_a<=-4), True)
B["mismatch8"]    = (ok10&((g.mtd_h-g.mtd_a).abs()>=8), False)
B["both_ov_hot"]  = ((g.ov10_h>=0.6)&(g.ov10_a>=0.6), False)
B["both_ov_cold"] = ((g.ov10_h<=0.4)&(g.ov10_a<=0.4), False)
B["cs_high"]      = (g.cs>=g.cs.quantile(0.9), True)
B["cs_low"]       = (g.cs<=g.cs.quantile(0.1), True)

names = list(B)
M = np.column_stack([B[n][0].fillna(False).values for n in names])
cells = [(i,-1) for i in range(len(names))]
for i in range(len(names)):
    for j in range(i+1,len(names)):
        if (M[:,i]&M[:,j]).sum() >= 900: cells.append((i,j))
CM = np.column_stack([M[:,i] if j<0 else (M[:,i]&M[:,j]) for i,j in cells])
labels = [names[i] if j<0 else f"{names[i]} & {names[j]}" for i,j in cells]
glim = [B[names[i]][1] if j<0 else (B[names[i]][1] or B[names[j]][1]) for i,j in cells]
print(f"cells: {CM.shape[1]}  ({len(names)} singles, {CM.shape[1]-len(names)} pairs)  games {len(g):,}")

dev = (g.season<=DEVMAX).values; hold = (g.season>=2024).values
seas = g.season.values; e = g.e.values; nonpush = e!=0
def scan(evec):
    """dev win% per cell per side, + per-season stability count."""
    ov = (evec>0)&nonpush; un = (evec<0)&nonpush
    out = {}
    for side, w in (("O",ov),("U",un)):
        wins = (CM & w[:,None] & dev[:,None]).sum(0).astype(float)
        n = (CM & nonpush[:,None] & dev[:,None]).sum(0).astype(float)
        wr = np.divide(wins, n, out=np.zeros_like(wins), where=n>0)
        stab = np.zeros(CM.shape[1])
        for s in np.unique(seas[dev]):
            m = dev & (seas==s)
            ws = (CM & w[:,None] & m[:,None]).sum(0)
            ns = (CM & nonpush[:,None] & m[:,None]).sum(0)
            stab += (np.divide(ws,ns,out=np.zeros_like(wr),where=ns>0) > 0.5)
        out[side] = (wr, n, stab)
    return out

def select(sc):
    picks = []
    for side in ("O","U"):
        wr, n, stab = sc[side]
        ok = (wr>=0.535)&(n>=600)&(stab>=5)
        for k in np.where(ok)[0]: picks.append((wr[k], k, side))
    picks.sort(reverse=True)
    return picks[:15]

def hold_eval(picks, evec):
    ov=(evec>0)&nonpush; un=(evec<0)&nonpush
    W_=Nn=0
    for wr,k,side in picks:
        w = ov if side=="O" else un
        W_ += int((CM[:,k]&w&hold).sum()); Nn += int((CM[:,k]&nonpush&hold).sum())
    return (W_/Nn if Nn else np.nan), Nn

sc = scan(e); book = select(sc)
print(f"\nFROZEN BOOK — {len(book)} seats (dev-selected)")
print(f"  {'cell':44}{'side':>5}{'dev n':>7}{'dev win%':>9}{'stab':>5}{'glimpsed':>9}")
for wr,k,side in book:
    print(f"  {labels[k][:44]:44}{side:>5}{int(sc[side][1][k]):>7,}{100*wr:>8.2f}%"
          f"{int(sc[side][2][k]):>5}{'YES' if glim[k] else 'no':>9}")
qual_count = len([1 for side in ('O','U') for k in np.where((sc[side][0]>=0.535)&(sc[side][1]>=600)&(sc[side][2]>=5))[0]])
print(f"  total qualifying cells (before top-15 cut): {qual_count}")

wrH, nH = hold_eval(book, e)
print(f"\nHOLDOUT (2024-25 + 2025-26): portfolio win% {100*wrH:.2f} on {nH:,} bets"
      if book else "\nno cells qualified")

# per-cell holdout
if book:
    print(f"  {'cell':44}{'side':>5}{'hold n':>8}{'hold win%':>10}")
    ov=(e>0)&nonpush; un=(e<0)&nonpush
    for wr,k,side in book:
        w = ov if side=="O" else un
        ww=int((CM[:,k]&w&hold).sum()); nn=int((CM[:,k]&nonpush&hold).sum())
        print(f"  {labels[k][:44]:44}{side:>5}{nn:>8,}{100*ww/nn if nn else 0:>9.2f}%")

# ---------------- empirical FDR: 200 phantom books --------------------------
print(f"\nFDR CALIBRATION — {NREP} permuted-dev pipelines, phantom books on REAL holdout")
res=[]
qc=[]
for r in range(NREP):
    ep = e.copy()
    for s in np.unique(seas[dev]):
        ix = np.where(dev&(seas==s))[0]; ep[ix] = e[ix][RNG.permutation(len(ix))]
    scp = scan(ep); bp = select(scp)
    qc.append(len([1 for side in ('O','U') for k in np.where((scp[side][0]>=0.535)&(scp[side][1]>=600)&(scp[side][2]>=5))[0]]))
    if bp:
        w,nn = hold_eval(bp, e)   # evaluate phantom book on REAL outcomes
        res.append(w)
res=np.array([x for x in res if np.isfinite(x)])
print(f"  phantom qualifying cells: mean {np.mean(qc):.1f}  p95 {np.percentile(qc,95):.0f}   (real: {qual_count})")
if len(res):
    print(f"  phantom-book holdout win%: mean {100*res.mean():.2f}  p5 {100*np.percentile(res,5):.2f}"
          f"  p95 {100*np.percentile(res,95):.2f}   (real book: {100*wrH:.2f})")
    print(f"  real book percentile among phantoms: {100*(res<wrH).mean():.0f}th")
pd.DataFrame([{ "cell":labels[k],"side":side,"dev_win":wr,"glimpsed":glim[k]} for wr,k,side in book]).to_csv("mined_book_2026.csv",index=False)
