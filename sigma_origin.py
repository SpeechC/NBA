import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"stageB_panel.csv"); G["date"]=pd.to_datetime(G.date)
A=pd.read_csv(SP+"stageA_fits.csv"); A=A[A.maxe<=0.10]
A["mu_lad"]=(A.mu_w+A.mu_i)/2; A["sg_lad"]=(A.s_w+A.s_i)/2
A["home"]=A.ev.str.extract(r"([A-Z]{3})$"); A["date"]=pd.to_datetime(A.date)
tm=pd.read_csv("team_mapping.csv"); A["TEAM_H"]=A.home.map(dict(zip(tm.abbr,tm.bigdataball_name)))
M=G.merge(A[["date","TEAM_H","mu_lad","sg_lad","s_w","s_i","wbar","n","vol"]],
          on=["date","TEAM_H"],how="inner")
M["mv"]=(M.close-M.open).abs(); M["aspd"]=M.ospread.abs()
M["t3r_g"]=(M.H_t3r+M.R_t3r)/2; M["pace_g"]=(M.H_pace+M.R_pace)/2
M=M.dropna(subset=["sg_lad","mu_lad","wbar","mv","aspd","t3r_g","pace_g"])
print(f"n = {len(M):,}   sd(sigma_ladder) = {M.sg_lad.std():.4f}\n")
def r2(cols,tgt="sg_lad"):
    X=np.column_stack([np.ones(len(M))]+[M[c].values.astype(float) for c in cols])
    y=M[tgt].values; b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    return 1-r.var()/y.var()
print("1. WHERE DOES LADDER SIGMA'S VARIATION COME FROM?")
for lbl,c in [("mu (the total level) alone",["mu_lad"]),
              ("QUOTE WIDTH alone",["wbar"]),
              ("mu + quote width",["mu_lad","wbar"]),
              ("+ n rungs, volume",["mu_lad","wbar","n","vol"])]:
    print(f"   {lbl:<34} R2 {r2(c):.4f}")
print("\n2. MEASUREMENT NOISE in the canonical sigma (split-half, disjoint rungs)")
try:
    SH=pd.read_csv(SP+"sigma_fixed.csv")
except Exception: SH=None
dis=(M.s_w-M.s_i)
print(f"   WLS-vs-INTERVAL disagreement sd {dis.std():.4f}  -> per-estimator noise ~{dis.std()/np.sqrt(2):.4f}")
print(f"   canonical (mean of two) noise    ~{dis.std()/2:.4f}   (shared quotes => LOWER BOUND)")
nv=(dis.std()/2)**2; tv=M.sg_lad.var()
print(f"   so >= {100*nv/tv:.1f}% of sigma variance is estimator noise; <= {100*(1-nv/tv):.1f}% is real")
print("\n3. HEAD TO HEAD — SPORTSBOOK-SIDE vs BASKETBALL-SIDE, width always controlled")
SB=["mu_lad","mv","aspd"]; BK=["pace_g","t3r_g"]
base=r2(["wbar"])
print(f"   {'block':<40}{'R2':>8}{'dR2 over width':>16}")
print(f"   {'quote width only (the artifact floor)':<40}{base:>8.4f}{'':>16}")
for lbl,c in [("+ SPORTSBOOK block (mu, |move|, |spread|)",["wbar"]+SB),
              ("+ BASKETBALL block (pace, 3PA rate)",["wbar"]+BK),
              ("+ BOTH",["wbar"]+SB+BK)]:
    print(f"   {lbl:<40}{r2(c):>8.4f}{r2(c)-base:>+16.4f}")
print(f"   {'BASKETBALL incremental over width+sportsbook':<40}"
      f"{r2(['wbar']+SB+BK)-r2(['wbar']+SB):>+24.4f}")
print("\n4. THE LINK 6/7 CLAIM RE-RUN UNDER THE STAGE-A PROTOCOL")
print("   (3PA rate -> sigma, both estimators, with and without a quote-width control)")
def coef(tgt,cols):
    X=np.column_stack([np.ones(len(M))]+[M[c].values.astype(float) for c in cols])
    y=M[tgt].values; b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    return b[1],se[1]
print(f"   {'estimator':<14}{'width ctrl':<12}{'3PA coef':>11}{'t':>8}{'95% CI':>22}")
for est,nm in [("s_w","WLS"),("s_i","INTERVAL"),("sg_lad","canonical")]:
    for ctl,lab in [([ "t3r_g","pace_g","mu_lad"],"no"),
                    (["t3r_g","pace_g","mu_lad","wbar"],"YES")]:
        b,se=coef(est,ctl)
        print(f"   {nm:<14}{lab:<12}{b:>+11.4f}{b/se:>8.2f}   [{b-1.96*se:>+7.4f},{b+1.96*se:>+7.4f}]")
print("\n5. IS SIGMA JUST A FUNCTION OF THE TOTAL? (the 'mechanically derived' test)")
print(f"   corr(sigma, mu) = {M.sg_lad.corr(M.mu_lad):+.4f}   R2 {r2(['mu_lad']):.4f}")
q=pd.qcut(M.mu_lad,6,labels=False)
print(f"   {'mu sextile':<12}{'mean mu':>10}{'mean sigma':>12}{'sd sigma':>10}")
for i in range(6):
    s=M[q==i]; print(f"   {i+1:<12}{s.mu_lad.mean():>10.1f}{s.sg_lad.mean():>12.3f}{s.sg_lad.std():>10.3f}")
