"""MINER PASS 2 — wider inventory. Same frozen selection rules as pass 1
(dev win%>=53.5, dev n>=600, stability = win%>50 in all-but-one covered dev
season, coverage >=4 seasons), same 200-phantom FDR evaluated on the REAL
holdout. Adds: singles ~45, pairs AND TRIPLES with dev n>=600.
"""
import warnings; warnings.filterwarnings("ignore")
import itertools
import numpy as np, pandas as pd
import opening_line_error_decomposition as OLE

RNG = np.random.default_rng(20260823); NREP = 200; DEVMAX = 2023

g = OLE.load(); g["gid"]=g.gid.astype(str).str.strip()
g = g.dropna(subset=["ot_close","total"]).sort_values("date").reset_index(drop=True)
g["e"] = g.total - g.ot_close
from prepare_data import CSV, season_label
raw = pd.read_csv(CSV, low_memory=False); raw["gid"]=raw["GAME-ID"].astype(str).str.strip()
r1 = raw.drop_duplicates("gid").set_index("gid")
g["osp_raw"] = pd.to_numeric(g.gid.map(r1["OPENING SPREAD_H"]), errors="coerce")
g["osp"] = g.osp_raw.abs()

# ---- team panel -------------------------------------------------------------
hp=pd.to_numeric(g.set_index("gid").hpts,errors="coerce"); ap=pd.to_numeric(g.set_index("gid").apts,errors="coerce")
L = pd.concat([g[["gid","season","date","home"]].rename(columns={"home":"team"}).assign(side="h"),
               g[["gid","season","date","away"]].rename(columns={"away":"team"}).assign(side="a")])
L["m"] = np.where(L.side=="h", L.gid.map(hp-ap), L.gid.map(ap-hp))
L["ov"] = np.sign(L.gid.map(g.set_index("gid").e))
for st,src in (("pace","PACE"),("oe","OEFF"),("de","DEFF")):
    pc = pd.concat([pd.DataFrame({"gid":raw["gid"],st:pd.to_numeric(raw[src+"_H"],errors="coerce"),"side":"h"}),
                    pd.DataFrame({"gid":raw["gid"],st:pd.to_numeric(raw[src+"_R"],errors="coerce"),"side":"a"})]).drop_duplicates(["gid","side"])
    L = L.merge(pc, on=["gid","side"], how="left")
L = L.sort_values(["season","team","date"]).reset_index(drop=True)
grp = L.groupby(["season","team"])
L["gap"] = grp["date"].diff().dt.days
L["b2b"] = (L.gap==1).astype(float)
d6=[]; rt=[]; hs=[]
for _,x in L.groupby(["season","team"]):
    dd=x.date.values; away=(x.side=="a").values
    d6 += [int(((dd[i]-dd[max(0,i-5):i])<=np.timedelta64(5,"D")).sum()>=3) for i in range(len(dd))]
    c=0; rr=[]
    for a in away: c = c+1 if a else 0; rr.append(c)
    rt += rr
    c=0; hh=[]
    for a in away: c = 0 if a else c+1; hh.append(c)
    hs += hh
L["in4of6"]=d6; L["roadtrip"]=rt; L["homestand"]=hs
L["mtd"]=grp["m"].transform(lambda s: s.shift(1).expanding().mean()); L["np_"]=grp.cumcount()
L["ov10"]=grp["ov"].transform(lambda s: s.shift(1).rolling(10,min_periods=5).apply(lambda v:(v>0).mean()))
L["wl4"]=grp["m"].transform(lambda s: (s>0).shift(1).rolling(4,min_periods=4).sum())
for st in ("pace","oe","de"):
    L[st+"_td"]=grp[st].transform(lambda s: s.shift(1).expanding().mean())
    L[st+"_z"]=L[st+"_td"]-L.groupby("season")[st+"_td"].transform("mean")
L["tilt"]=L.oe_z+L.de_z
W = L.pivot_table(index="gid", columns="side", aggfunc="first",
    values=["b2b","in4of6","roadtrip","homestand","mtd","np_","ov10","wl4","pace_z","tilt","gap"])
W.columns=[f"{a}_{b}" for a,b in W.columns]
g = g.merge(W,left_on="gid",right_index=True,how="left")
rs = pd.read_csv("/mnt/c/NBA2/referee_game_states.csv"); rs["gid"]=rs["GAME-ID"].astype(str).str.strip()
g = g.merge(rs[["gid","CrewShock","REF_LEAGUE_FOUL_STATE","REF_MIN_PRIOR"]],on="gid",how="left")
# injuries: unweighted late-OUT count from the panel (fast, no duckdb)
P = pd.read_csv("injury_status_panel.csv", parse_dates=["report_ts","game_date"])
P["gk"]=P.game_date.dt.strftime("%Y-%m-%d")+"|"+P.matchup
gg=P.groupby(["gk","player"])["status"]
first=gg.first(); last_=gg.last()
lateout=((first!="Out")&(last_=="Out")).groupby("gk").sum()
mp = pd.read_csv("team_mapping.csv").set_index("bigdataball_name")["abbr"].to_dict()
g["gk"]=g.date.dt.strftime("%Y-%m-%d")+"|"+g.away.map(mp)+"@"+g.home.map(mp)
g["n_late"]=g.gk.map(lateout)
g["lvl"]=g.ot_close-g.groupby("season")["ot_close"].transform("mean")
g["frac"]=g.groupby("season")["date"].rank(pct=True)
last = g.groupby("season")["date"].transform("max")
ok10=(g.np__h>=10)&(g.np__a>=10)

B={}
B["b2b_home"]=(g.b2b_h==1); B["b2b_away"]=(g.b2b_a==1); B["b2b_both"]=(g.b2b_h==1)&(g.b2b_a==1)
B["4in6_either"]=(g.in4of6_h==1)|(g.in4of6_a==1); B["4in6_both"]=(g.in4of6_h==1)&(g.in4of6_a==1)
B["roadtrip4"]=(g.roadtrip_a>=4); B["homestand4"]=(g.homestand_h>=4)
B["rest_both3"]=(g.gap_h>=3)&(g.gap_a>=3); B["rest_gap3"]=((g.gap_h-g.gap_a).abs()>=3)
B["weekend"]=g.date.dt.dayofweek.isin([5,6]); B["monday"]=g.date.dt.dayofweek==0
B["final_week"]=((last-g.date).dt.days<=7); B["early_season"]=(g.frac<=0.2)
B["late_season"]=(g.frac>=0.8); B["mid_season"]=(g.frac>0.35)&(g.frac<0.65)
B["december"]=g.date.dt.month==12; B["march"]=g.date.dt.month==3
B["lvl_hi"]=(g.lvl>=g.lvl.quantile(0.9)); B["lvl_lo"]=(g.lvl<=g.lvl.quantile(0.1))
B["sp_close"]=(g.osp<=3); B["sp_blowout"]=(g.osp>=9); B["home_dog"]=(g.osp_raw>0)
B["big_home_fav"]=(g.osp_raw<=-8)
B["moved_up"]=(g.tmove>=1.5); B["moved_down"]=(g.tmove<=-1.5); B["no_move"]=(g.tmove.abs()<=0.5)
B["moved_up_big"]=(g.tmove>=2.5); B["moved_down_big"]=(g.tmove<=-2.5)
B["both_fast"]=ok10&(g.pace_z_h>=1)&(g.pace_z_a>=1); B["both_slow"]=ok10&(g.pace_z_h<=-1)&(g.pace_z_a<=-1)
B["pace_clash"]=ok10&(((g.pace_z_h>=1)&(g.pace_z_a<=-1))|((g.pace_z_h<=-1)&(g.pace_z_a>=1)))
B["both_offtilt"]=ok10&(g.tilt_h>=2)&(g.tilt_a>=2); B["both_deftilt"]=ok10&(g.tilt_h<=-2)&(g.tilt_a<=-2)
B["off_meets_def"]=ok10&(((g.tilt_h>=2)&(g.tilt_a<=-2))|((g.tilt_h<=-2)&(g.tilt_a>=2)))
B["both_strong"]=ok10&(g.mtd_h>=4)&(g.mtd_a>=4); B["both_weak"]=ok10&(g.mtd_h<=-4)&(g.mtd_a<=-4)
B["mismatch8"]=ok10&((g.mtd_h-g.mtd_a).abs()>=8)
B["both_ov_hot"]=(g.ov10_h>=0.6)&(g.ov10_a>=0.6); B["both_ov_cold"]=(g.ov10_h<=0.4)&(g.ov10_a<=0.4)
B["either_streak4"]=(g.wl4_h==4)|(g.wl4_a==4); B["either_skid4"]=(g.wl4_h==0)|(g.wl4_a==0)
B["cs_high"]=(g.CrewShock>=g.CrewShock.quantile(0.9)); B["cs_low"]=(g.CrewShock<=g.CrewShock.quantile(0.1))
B["ref_foul_hi"]=(g.REF_LEAGUE_FOUL_STATE>=g.REF_LEAGUE_FOUL_STATE.quantile(0.8))
B["ref_thin"]=(g.REF_MIN_PRIOR<=g.REF_MIN_PRIOR.quantile(0.2))
B["inj_late1"]=(g.n_late>=1); B["inj_late3"]=(g.n_late>=3)

names=list(B)
M=np.column_stack([B[n].fillna(False).values.astype(bool) for n in names])
dev=(g.season<=DEVMAX).values; hold=(g.season>=2024).values
seas=g.season.values; e=g.e.values; nonpush=e!=0
devnp = dev&nonpush
base_n = (M & devnp[:,None]).sum(0)

cells=[(i,) for i in range(len(names))]
for i,j in itertools.combinations(range(len(names)),2):
    if (M[:,i]&M[:,j]&devnp).sum()>=600: cells.append((i,j))
pair_cells=[c for c in cells if len(c)==2]
for i,j in pair_cells:
    for k in range(len(names)):
        if k<=j: continue
        if (M[:,i]&M[:,j]&M[:,k]&devnp).sum()>=600: cells.append((i,j,k))
CM=np.column_stack([np.logical_and.reduce([M[:,i] for i in c]) for c in cells])
labels=[" & ".join(names[i] for i in c) for c in cells]
print(f"cells: {CM.shape[1]:,}  (singles {len(names)}, pairs {len(pair_cells)}, "
      f"triples {CM.shape[1]-len(names)-len(pair_cells)})   games {len(g):,}")

devseasons=np.unique(seas[dev])
NS=np.stack([(CM & (dev&(seas==s)&nonpush)[:,None]).sum(0) for s in devseasons])  # S x C
covered = NS>=30
navail = covered.sum(0)
def scan(evec):
    out={}
    for side in ("O","U"):
        w = ((evec>0) if side=="O" else (evec<0)) & nonpush
        wins=(CM & (w&dev)[:,None]).sum(0).astype(float)
        n=(CM & devnp[:,None]).sum(0).astype(float)
        wr=np.divide(wins,n,out=np.zeros_like(wins),where=n>0)
        stab=np.zeros(CM.shape[1])
        for si,s in enumerate(devseasons):
            ws=(CM & (w&dev&(seas==s))[:,None]).sum(0)
            frac_=np.divide(ws,NS[si],out=np.zeros(CM.shape[1]),where=NS[si]>0)
            stab += (frac_>0.5)&covered[si]
        out[side]=(wr,n,stab)
    return out
def select(sc):
    picks=[]
    for side in ("O","U"):
        wr,n,stab=sc[side]
        ok=(wr>=0.535)&(n>=600)&(navail>=4)&(stab>=navail-1)
        for k in np.where(ok)[0]: picks.append((wr[k],k,side))
    picks.sort(reverse=True); return picks[:15]
def hold_eval(picks,evec):
    Wn=Nn=0
    for wr,k,side in picks:
        w=((evec>0) if side=="O" else (evec<0))&nonpush
        Wn+=int((CM[:,k]&w&hold).sum()); Nn+=int((CM[:,k]&nonpush&hold).sum())
    return (Wn/Nn if Nn else np.nan),Nn

sc=scan(e); book=select(sc)
nq=len([1 for side in ("O","U") for k in np.where((sc[side][0]>=0.535)&(sc[side][1]>=600)&(navail>=4)&(sc[side][2]>=navail-1))[0]])
print(f"\nFROZEN BOOK — {len(book)} of {nq} qualifying")
print(f"  {'cell':52}{'side':>5}{'dev n':>7}{'dev%':>7}{'hold n':>7}{'hold%':>7}")
ov=(e>0)&nonpush; un=(e<0)&nonpush
for wr,k,side in book:
    w=ov if side=="O" else un
    hw=int((CM[:,k]&w&hold).sum()); hn=int((CM[:,k]&nonpush&hold).sum())
    print(f"  {labels[k][:52]:52}{side:>5}{int(sc[side][1][k]):>7,}{100*wr:>6.2f}%"
          f"{hn:>7,}{100*hw/hn if hn else 0:>6.2f}%")
wrH,nH=hold_eval(book,e)
print(f"  PORTFOLIO holdout: {100*wrH:.2f}% on {nH:,} bets" if book else "  none")

print(f"\nFDR — {NREP} phantom pipelines on the wide inventory")
res=[];qc=[]
for r in range(NREP):
    ep=e.copy()
    for s in devseasons:
        ix=np.where(dev&(seas==s))[0]; ep[ix]=e[ix][RNG.permutation(len(ix))]
    scp=scan(ep); bp=select(scp)
    qc.append(len([1 for side in ("O","U") for k in np.where((scp[side][0]>=0.535)&(scp[side][1]>=600)&(navail>=4)&(scp[side][2]>=navail-1))[0]]))
    if bp:
        w,_=hold_eval(bp,e); res.append(w)
res=np.array([x for x in res if np.isfinite(x)])
print(f"  phantom qualifying cells: mean {np.mean(qc):.1f}  p95 {np.percentile(qc,95):.0f}   (real: {nq})")
print(f"  phantom books with >=1 seat: {len(res)} of {NREP}")
if len(res):
    print(f"  phantom-book holdout win%: mean {100*res.mean():.2f}  p95 {100*np.percentile(res,95):.2f}"
          f"   real: {100*wrH:.2f}  -> {100*(res<wrH).mean():.0f}th pctile")
