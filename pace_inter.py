import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"pace_panel.csv"); G["date"]=pd.to_datetime(G.date).dt.strftime("%Y-%m-%d")
L=pd.read_csv(SP+"ladder_sigma.csv"); L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(G[["date","TEAM_H","pp","close","dev","is_ot"]],left_on=["date","home_n"],
          right_on=["date","TEAM_H"],how="inner").dropna(subset=["pp"])
def reg(y,cols,X_,lbl):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<40}"+"  ".join(f"{c} {b[i+1]:+9.4f}(t={b[i+1]/se[i+1]:+5.2f})"
                                   for i,c in enumerate(cols)))
    return b,se
for D in (G,M):
    D["pc"]=D.pp-G.pp.mean(); D["cc"]=D.close-G.close.mean(); D["ix"]=D.pc*D.cc
print("THE INTERACTION, tested directly (centred)")
print(" REALITY:")
reg((G.dev**2).values,["pc","cc","ix"],G,f"dev^2 ~ pace*close  [n={len(G):,}]")
NO=G[G.is_ot==0]
b,se=reg((NO.dev**2).values,["pc","cc","ix"],NO,f"dev^2 ~ pace*close  [no OT n={len(NO):,}]")
print(f"   interaction 95% CI [{b[3]-1.96*se[3]:+.4f}, {b[3]+1.96*se[3]:+.4f}]"
      f"   {'EXCLUDES' if (b[3]-1.96*se[3])*(b[3]+1.96*se[3])>0 else 'INCLUDES'} zero")
print(" LADDER:")
reg(M.sig.values,["pc","cc","ix"],M,f"implied_sigma ~ pace*close [n={len(M):,}]")

print("\nMULTIPLE-COMPARISON HONESTY")
print("  the tercile pattern was 6 looks (3 terciles x 2 OT specs); best was t=-1.92.")
print(f"  the FORMAL interaction above is the single pre-specified version of it.")
print("\nSEASON-BY-SEASON STABILITY of the interaction (is it one season?)")
G["yr"]=G.yr.astype(int)
for y,s in G.groupby("yr"):
    if len(s)<500: continue
    X=np.column_stack([np.ones(len(s)),s.pc,s.cc,s.pc*s.cc]); yy=(s.dev**2).values
    bb,*_=np.linalg.lstsq(X,yy,rcond=None); rr=yy-X@bb
    ss=np.sqrt(np.diag((rr@rr/(len(yy)-4))*np.linalg.pinv(X.T@X)))
    print(f"   {y}  n={len(s):>5}  interaction {bb[3]:+8.4f} (t={bb[3]/ss[3]:+5.2f})")
