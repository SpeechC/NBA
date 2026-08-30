import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"stageB_panel.csv"); G["date"]=pd.to_datetime(G.date); G["yr"]=G.yr.astype(int)
A=pd.read_csv(SP+"stageA_fits.csv")
A=A[A.maxe<=0.10]                                  # Stage A7: drop junk books
A["mu_lad"]=(A.mu_w+A.mu_i)/2; A["sg_lad"]=(A.s_w+A.s_i)/2
A["home"]=A.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); A["TEAM_H"]=A.home.map(dict(zip(tm.abbr,tm.bigdataball_name)))
A["date"]=pd.to_datetime(A.date)
M=G.merge(A[["date","TEAM_H","mu_lad","sg_lad","wbar"]],on=["date","TEAM_H"],how="inner")
print(f"LADDER-mu VALIDATION SEASON: n={len(M):,}  (2025-26, the only season with ladders)")
def met(pred,y,lbl):
    m=pd.notna(pred)&pd.notna(y); e=y[m]-pred[m]
    print(f"  {lbl:<34}{np.sqrt((e**2).mean()):>8.3f}{e.abs().mean():>8.3f}"
          f"{1-e.var()/y[m].var():>9.4f}{e.abs().median():>9.3f}"
          f"{100*(e.abs()<=0.5).mean():>8.1f}{100*(e.abs()<=1).mean():>8.1f}{100*(e.abs()<=2).mean():>8.1f}")
print(f"\n  {'predictor of LADDER mu':<34}{'RMSE':>8}{'MAE':>8}{'R2':>9}{'medAE':>9}{'<=0.5':>8}{'<=1':>8}{'<=2':>8}")
met(M.open,M.mu_lad,"the OPENING TOTAL itself")
met(M.close,M.mu_lad,"the CLOSING TOTAL itself")
BL=["H_oeff","R_oeff","H_deff","R_deff","H_pace","R_pace"]
REC=["Hs_pace","Rs_pace","Hs_oeff","Rs_oeff","Hs_deff","Rs_deff"]
ALL={"M2 (strength+pace)":BL,"M6 full":BL+["H_efg","R_efg","H_tov","R_tov","H_ftr","R_ftr",
     "H_reb","R_reb","H_t3r","R_t3r","H_t3p","R_t3p","restH","restR","b2bH","b2bR","doy"]+REC,
     "struct + recent state":["struct"]+REC}
tr=G[G.yr<2025]; te=M
for lbl,cols in ALL.items():
    Atr=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
    ok=np.isfinite(Atr).all(1)
    b,*_=np.linalg.lstsq(Atr[ok],tr.open.values[ok],rcond=None)
    Bte=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
    met(pd.Series(Bte@b,index=te.index),te.mu_lad,"  "+lbl+" (trained <=2024-25)")
print("\nHOW FAR IS THE MARKET'S OWN OPENER FROM LADDER mu?")
print(f"  corr(open, ladder mu) {M.open.corr(M.mu_lad):.4f}   mean(mu_lad - open) {(M.mu_lad-M.open).mean():+.3f}"
      f"   sd {(M.mu_lad-M.open).std():.3f}")
print(f"  corr(close, ladder mu) {M.close.corr(M.mu_lad):.4f}  mean(mu_lad - close) {(M.mu_lad-M.close).mean():+.3f}"
      f"   sd {(M.mu_lad-M.close).std():.3f}")
print("  => the ladder centre tracks the CLOSE, not the opener; that is the reachable floor")
print("\nSTAGE C PREVIEW ONLY — sigma vs quote width on the canonical estimate")
print(f"  corr(sigma_ladder, quote width) = {M.sg_lad.corr(M.wbar):+.4f}"
      "   (Stage A: must be controlled)")
