"""PREREG_variance_audit.md stage 1 -- run once. e^2 ~ conditioner, dev,
within-season permutation, BH q=0.10 across the fixed 12."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import opening_line_error_decomposition as OLE

RNG = np.random.default_rng(20260823); NPERM = 2000

g = OLE.load()
g["gid"] = g.gid.astype(str).str.strip()
g["e"] = g.total - g.ot_close
g["e2"] = g.e**2
g["ae"] = g.e.abs()

# ---- conditioners -----------------------------------------------------------
C = {}
C["level"] = g.ot_close
C["abs_spread"] = pd.to_numeric(g.os_close if "os_close" in g else g["sp_close"] if "sp_close" in g else np.nan, errors="coerce").abs() if ("os_close" in g or "sp_close" in g) else None
# find the closing spread column defensively
spr = [c for c in g.columns if "close" in c and "s" in c and c not in ("ot_close",)]
if C["abs_spread"] is None or C["abs_spread"].isna().all():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["gid"] = raw["GAME-ID"].astype(str).str.strip()
    sp = raw.drop_duplicates("gid").set_index("gid")["CLOSING SPREAD_H"]
    C["abs_spread"] = pd.to_numeric(g.gid.map(sp), errors="coerce").abs()

# prior-only expanding pace sum
from prepare_data import CSV, season_label
raw = pd.read_csv(CSV, low_memory=False); raw["gid"]=raw["GAME-ID"].astype(str).str.strip()
r1 = raw.drop_duplicates("gid").set_index("gid")
n_ = lambda c: pd.to_numeric(r1[c], errors="coerce")
Lp = pd.concat([pd.DataFrame({"gid":g.gid,"season":g.season,"date":g.date,"team":g.home,"pace":g.gid.map(n_("PACE_H"))}),
                pd.DataFrame({"gid":g.gid,"season":g.season,"date":g.date,"team":g.away,"pace":g.gid.map(n_("PACE_R"))})]).sort_values("date")
grp = Lp.groupby(["season","team"])
Lp["p_td"] = grp["pace"].transform(lambda s: s.shift(1).expanding().mean())
Lp["np_"] = grp.cumcount()
Lp["ok"] = np.where(Lp.np_>=10, Lp.p_td, np.nan)
C["pace_prior"] = g.gid.map(Lp.groupby("gid")["ok"].sum(min_count=2))

# b2b derived from the schedule (master rest column only carries {1,2} --
# a back-to-back is never coded 0 -- so it is computed from date gaps instead)
Lb = pd.concat([g[["gid","season","date","home"]].rename(columns={"home":"team"}),
                g[["gid","season","date","away"]].rename(columns={"away":"team"})]) \
       .sort_values("date")
Lb["gap"] = Lb.groupby(["season","team"])["date"].diff().dt.days
Lb["b2b"] = (Lb.gap==1).astype(float)
C["b2b_either"] = g.gid.map(Lb.groupby("gid")["b2b"].max())
C["season_frac"] = g.groupby("season")["date"].rank(pct=True)
C["weekend"] = g.date.dt.dayofweek.isin([5,6]).astype(float)
last = g.groupby("season")["date"].transform("max")
C["final_week"] = ((last-g.date).dt.days<=7).astype(float)

# walk-forward NC involvement (frozen -5.409)
hp=pd.to_numeric(g.hpts,errors="coerce"); ap=pd.to_numeric(g.apts,errors="coerce")
Lm = pd.concat([pd.DataFrame({"gid":g.gid,"season":g.season,"date":g.date,"team":g.home,"m":hp-ap}),
                pd.DataFrame({"gid":g.gid,"season":g.season,"date":g.date,"team":g.away,"m":ap-hp})]).sort_values("date")
gm2=Lm.groupby(["season","team"])
Lm["mtd"]=gm2["m"].transform(lambda s: s.shift(1).expanding().mean()); Lm["np_"]=gm2.cumcount()
Lm["nc"]=np.where(Lm.np_>=10,(Lm.mtd<=-5.409).astype(float),np.nan)
ncg=Lm.groupby("gid")["nc"].agg(["sum","count"])
C["nc_involved"] = np.where(g.gid.map(ncg["count"])==2,
                            (g.gid.map(ncg["sum"])>=1).astype(float), np.nan)

sc = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv"); sc["gid"]=sc["GAME-ID"].astype(str).str.strip()
C["abs_move_combined"] = g.gid.map(sc.set_index("gid")["MOVE_COMBINED_OOS"]).abs()
try:
    import injury_surprise as ISU
    d_s,_ = ISU.build()
    C["n_late"] = g.gid.map(d_s.set_index("gid")["N_LATE"])
except Exception as ex:
    C["n_late"] = None; print("n_late unavailable:", ex)
rf = pd.read_csv("ref_features.csv"); rf["gid"]=rf["gid"].astype(str).str.strip()
C["abs_crewshock"] = g.gid.map(rf.set_index("gid")["CrewShock"]).abs()
C["abs_tmove"] = g.tmove.abs()

# ---- stage 1 ----------------------------------------------------------------
def perm_test(x):
    x = x.dropna(subset=["c", "e2"])
    dev = x[x.season<=2023]; hold = x[x.season>=2024]
    if len(dev)<500 or dev.c.std()==0: return None
    c = (dev.c - dev.c.mean())/ (dev.c.std() if dev.c.std()>0 else 1)
    y = dev.e2.values
    b = np.polyfit(c,y,1)[0]
    yrs=dev.season.values; blocks=[np.where(yrs==u)[0] for u in np.unique(yrs)]
    cv=c.values; null=np.empty(NPERM)
    for i in range(NPERM):
        p=cv.copy()
        for bl in blocks: p[bl]=cv[bl][RNG.permutation(len(bl))]
        null[i]=np.polyfit(p,y,1)[0]
    pv=(1+np.sum(np.abs(null)>=abs(b)))/(NPERM+1)
    ch=(hold.c-hold.c.mean())/(hold.c.std() if hold.c.std()>0 else 1)
    bh=np.polyfit(ch,hold.e2.values,1)[0] if len(hold)>200 else np.nan
    # descriptive rmse by tercile/half
    if x.c.nunique()<=2:
        r0=np.sqrt(dev[dev.c==0].e2.mean()); r1=np.sqrt(dev[dev.c==1].e2.mean())
        desc=f"RMSE {r0:.2f}|{r1:.2f}"
    else:
        q=pd.qcut(dev.c,3,duplicates="drop")
        rs=[np.sqrt(v) for v in dev.groupby(q).e2.mean()]
        desc="RMSE " + "|".join(f"{v:.2f}" for v in rs)
    return len(dev), b, pv, bh, desc

print(f"\n{'conditioner':20}{'n_dev':>7}{'slope(e2)':>11}{'perm p':>8}{'hold slope':>11}   RMSE by class")
res={}
for nm, col in C.items():
    if col is None: print(f"{nm:20}  unavailable"); continue
    x = pd.DataFrame({"season":g.season,"e2":g.e2,"c":np.asarray(col,dtype=float)})
    out = perm_test(x)
    if out is None: print(f"{nm:20}  insufficient"); continue
    n,b,pv,bh,desc = out; res[nm]=(b,pv,bh)
    print(f"{nm:20}{n:>7,}{b:>+11.1f}{pv:>8.4f}{bh:>+11.1f}   {desc}")

# BH q=0.10
ps = sorted([(pv,nm) for nm,(b,pv,bh) in res.items()])
m=len(ps); passed=[]
for i,(pv,nm) in enumerate(ps,1):
    if pv <= 0.10*i/m: passed.append(nm)
print(f"\nBH q=0.10 over {m} tests -> survivors: {passed if passed else 'NONE'}")
for nm in passed:
    b,pv,bh=res[nm]
    print(f"  {nm}: dev slope {b:+.1f} (p={pv:.4f})  holdout slope {bh:+.1f}  "
          f"same sign: {np.sign(b)==np.sign(bh)}")
