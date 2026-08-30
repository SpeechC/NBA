import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"],"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"]})
for c in ["PTS_H","PTS_R","FGA_H","3PA_H","FTA_H","PF_H","POSS_H","FGA_R","3PA_R","FTA_R",
          "PF_R","POSS_R","OPENING TOTAL_H","CLOSING TOTAL_H"]:
    d[c]=n(c)
d["date"]=pd.to_datetime(raw["DATE"],errors="coerce")
d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
d=d[d.season.str.contains("Regular Season",na=False)].dropna(subset=["FGA_H","POSS_H","yr","date"])
d=d.sort_values("date").reset_index(drop=True); d["gi"]=d.index
tm=pd.read_csv("team_mapping.csv"); a2n=dict(zip(tm.abbr,tm.bigdataball_name))
pb=pd.read_csv(SP+"s2_pbp_states.csv")
pb["t"]=pb.tm.map(a2n); pb["date"]=pd.to_datetime(pb.GAMEDATE,errors="coerce")
pb=pb.dropna(subset=["t","date"])[["date","t","trans_share","live"]]
def side(s):
    o="R" if s=="H" else "H"
    x=pd.DataFrame({"gi":d.gi,"yr":d.yr,"date":d.date,"t":d[f"TEAM_{s}"]})
    x["off_3par"]=d[f"3PA_{s}"]/d[f"FGA_{s}"]
    x["def_3par"]=d[f"3PA_{o}"]/d[f"FGA_{o}"]
    x["off_ftar"]=100*d[f"FTA_{s}"]/d[f"POSS_{s}"]
    x["def_pf"]  =100*d[f"PF_{s}"]/d[f"POSS_{o}"]
    x["home"]=1.0 if s=="H" else 0.0
    return x
T=pd.concat([side("H"),side("R")]).merge(pb,on=["date","t"],how="left")
T["off_trans"]=T.trans_share; T["def_live"]=T.live
ST=["off_3par","def_3par","off_ftar","def_pf","off_trans","def_live"]
print("STAGE 0 — CONSTRUCTIBILITY  (no outcome examined)")
for c in ST:
    print(f"  {c:<11} nonnull {T[c].notna().sum():>7,}/{len(T):,} ({100*T[c].notna().mean():.1f}%)")
# ---- PIT team state: current-season prior mean shrunk to prior season, k=10 (Stage 1 rule)
T=T.sort_values(["t","date"]); K=10.0
prev=T.groupby(["t","yr"])[ST].mean().reset_index(); prev["yr"]=prev.yr+1
prev=prev.rename(columns={c:c+"_pv" for c in ST})
T=T.merge(prev,on=["t","yr"],how="left"); g=T.groupby(["t","yr"])
for c in ST:
    cs=g[c].transform(lambda s:s.shift(1).expanding(min_periods=1).mean())
    cn=g[c].transform(lambda s:s.shift(1).expanding(min_periods=1).count())
    pv=T[c+"_pv"].fillna(T.groupby("yr")[c].transform("mean"))
    T["p_"+c]=((cn.fillna(0)*cs.fillna(0)+K*pv)/(cn.fillna(0)+K)).fillna(pv)
print("\nPIT PERSISTENCE (adjacent-season r on team means)")
for c in ST:
    ts=T.groupby(["t","yr"])[c].mean().unstack(); ys=sorted(ts.columns)
    rs=[ts[[a,b]].dropna().corr().iloc[0,1] for a,b in zip(ys,ys[1:]) if len(ts[[a,b]].dropna())>20]
    print(f"  {c:<11} r = {np.mean(rs):+.4f}")
# ---- STRICTLY PIT league scaling: z = (X - mu_{season,<t}) / sd_{season,<t}
# expanding over team-games strictly BEFORE t within season; PRIOR-SEASON constants as
# the early fallback. Full-season constants use April data on a December game (not PIT);
# prior-season-only constants leave the league 3PA drift uncentred. This does neither.
T=T.sort_values("date").reset_index(drop=True)
prevc={c:(lambda m: m.set_axis(m.index+1))(T.groupby("yr")["p_"+c].agg(["mean","std"])) for c in ST}
parts=[]
for yv,gg in T.groupby("yr",sort=True):
    o=pd.DataFrame(index=gg.index)
    for c in ST:
        v=gg["p_"+c]
        o["mu_"+c]=v.expanding(min_periods=200).mean().shift(1)
        o["sd_"+c]=v.expanding(min_periods=200).std().shift(1)
        o["mu_"+c]=o["mu_"+c].fillna(prevc[c]["mean"].get(yv,np.nan)).fillna(T["p_"+c].mean())
        o["sd_"+c]=o["sd_"+c].fillna(prevc[c]["std"].get(yv,np.nan)).fillna(T["p_"+c].std())
    parts.append(o)
T=T.join(pd.concat(parts))
T["pbp_ok"]=T.groupby(["t","yr"])["off_trans"].transform(lambda s:s.notna().any())
H=T[T.home==1].set_index("gi"); R=T[T.home==0].set_index("gi"); G=d.set_index("gi").copy()
def zz(F,c): return (F["p_"+c]-F["mu_"+c])/F["sd_"+c]
def mk(a,b): return (zz(H,a)*zz(R,b)+zz(R,a)*zz(H,b))/2.0
ok=H.pbp_ok.reindex(G.index).fillna(False)&R.pbp_ok.reindex(G.index).fillna(False)
G["Z_H1"]=mk("off_3par","def_3par"); G["Z_H2"]=mk("off_trans","def_live").where(ok)
G["Z_H3"]=mk("off_ftar","def_pf")
E=pd.read_csv(SP+"emulator_panel.csv").set_index("gi")
G=G.join(E[["L_M6","open"]].rename(columns={"open":"open_e"}),how="left")
G["That"]=G.open_e-G.L_M6
print("\nINTERACTIONS — distribution, orthogonality, PIT era check")
print(f"  {'Z':<6}{'n':>7}{'mean':>9}{'sd':>8}{'corr That':>12}{'season-mean range':>26}")
for k in ["Z_H1","Z_H2","Z_H3"]:
    s=G[k].dropna(); m=G.groupby("season")[k].mean()
    print(f"  {k:<6}{len(s):>7,}{s.mean():>9.4f}{s.std():>8.4f}{G[k].corr(G.That):>12.4f}"
          f"{f'[{m.min():+.4f}, {m.max():+.4f}]':>26}")
print("\nCROSS-CORRELATION (Holm family independence)")
print(G[["Z_H1","Z_H2","Z_H3"]].corr().round(4).to_string())
G.reset_index().to_csv(SP+"s2_panel.csv",index=False)
print(f"\nsaved; H2 eligible {G.Z_H2.notna().sum():,}")
